import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from game_anywhere.run_game import run_game
from game_anywhere.core import Game, GameSummary
from game_anywhere.components import Component, ComponentSlotProperty, PerPlayer, List
from game_anywhere.components.traditional.cards import Deck, PokerCard, fiftytwo_cards

from typing import Protocol, Any, TypeVar, Callable
from enum import Enum, unique, member
from collections import defaultdict
from itertools import combinations, cycle
from abc import abstractmethod


class Poker(Game):
    class EveryoneFolds(Exception):
        def __init__(self, winner_index: int):
            self.winner_index = winner_index

    class PokerSummary(GameSummary):
        def __init__(self, winner_index: int):
            self.winner = winner_index

        # override
        def get_winner(self):
            return self.winner + 1

        # TODO: stakes

    deck = ComponentSlotProperty()
    revealed_cards = ComponentSlotProperty()
    players = PerPlayer(
        hand=ComponentSlotProperty(),
        bet=ComponentSlotProperty(),
        folded=ComponentSlotProperty(),
    )

    def __init__(self, agent_descriptions, *args, small_blind=1, big_blind=2, **kwargs):
        super().__init__(agent_descriptions, *args, **kwargs)
        self.deck = Deck(fiftytwo_cards(), shuffled=True)
        self.revealed_cards : List[PokerCard] = List()
        self.players = PerPlayer.INIT
        for i, player in enumerate(self.players):
            player.hand = List(hidden=True, owner_id=i)
            player.bet = 0
            player.folded = False
        self.big_blind = big_blind
        self.small_blind = small_blind

    # override
    def play_game(self) -> GameSummary:
        for player in self.players:
            player.hand += [self.deck.draw() for i in range(2)]

        try:
            self.betting_round(force_blinds=[self.small_blind, self.big_blind])
            # no need to burn cards
            self.revealed_cards.extend(
                self.deck.draw() for _ in range(3)
            )  # TODO: OPTIM: add a draw_multiple function
            self.betting_round()
            self.revealed_cards.append(self.deck.draw())
            self.betting_round()
            self.revealed_cards.append(self.deck.draw())
        except Poker.EveryoneFolds as win:
            return self.win_game(win.winner_index)

        best_hand = None
        best_hand_index = -1
        for i, player in enumerate(self.players):
            if not player.folded:
                best_hand_for_player = max(
                    PokerHand(cards)
                    for cards in combinations(self.revealed_cards + player.hand, 5)
                )
                if best_hand is None or best_hand < best_hand_for_player:
                    best_hand = best_hand_for_player
                    best_hand_index = i
        return self.win_game(player_index=best_hand_index)

    def betting_round(self, force_blinds: list[int] | None = None) -> None:
        last_raise = None
        maximum_bet = None

        print("Betting round")
        for turn_counter in cycle(range(len(self.agents))):
            if turn_counter == last_raise:
                return
            elif last_raise is None:
                last_raise = turn_counter

            if force_blinds:
                decision = "raise"
                amount = force_blinds.pop(0)
                print("Force blinds", amount)
            elif self.players[turn_counter].folded:
                print("Player folded")
                continue
            else:
                agent = self.agents[turn_counter]
                if maximum_bet is None or self.players[turn_counter].bet == maximum_bet:
                    decision = agent.text_choice(["check", "raise"])
                elif self.players[turn_counter].bet < maximum_bet:
                    decision = agent.text_choice(["fold", "follow", "raise"])

                if decision == "raise":
                    amount = agent.int_choice(min=maximum_bet)

            if decision == "fold":
                self.players[turn_counter].folded = True
                if sum(not player.folded for player in self.players) == 1:
                    # TODO this is ugly. Is there no find_first function in Python?
                    last_remaining_player = next(
                        filter(
                            lambda args: not player[1].folded, enumerate(self.players)
                        )
                    )[0]
                    return self.win_game(player_index=last_remaining_player)
            elif decision == "check":
                continue
            elif decision == "follow":
                self.players[turn_counter].bet = maximum_bet
            else:
                assert decision == "raise"
                self.players[turn_counter].bet = amount
                maximum_bet = amount
                last_raise = turn_counter

    def win_game(self, player_index) -> "Poker.PokerSummary":
        return Poker.PokerSummary(player_index)


# Copied from https://gist.github.com/pawelrubin/a394702e4029809f30515621fc41ab1f

ComparableType = TypeVar("CT", bound="Comparable")


class Comparable(Protocol):
    """Protocol for annotating comparable types."""

    @abstractmethod
    def __lt__(self: ComparableType, other: ComparableType) -> bool: ...


PokerHandFunction = Callable["PokerHand", ComparableType | None]

hand_values_by_name: dict[str, PokerHandFunction] = {}


def hand_value(f: PokerHandFunction) -> PokerHandFunction:
    name = f.__name__
    if name[:3] == "is_":
        name = name[3:]
    hand_values_by_name[name] = f
    return f


hand_value_names_ranked = [
    "high_card",
    "pair",
    "two_pairs",
    "three_of_a_kind",
    "straight",
    "flush",
    "full_house",
    "four_of_a_kind",
    "straight_flush",
]


class PokerHand:
    def __init__(self, cards: list[PokerCard]):
        self.cards = list(cards)
        self.cards.sort(
            key=lambda card: card.value
        )  # already sorting by value because it will be useful for most algorithms
        self.values = self.cards_by_value()

        for i, hand_value_name in sorted(
            enumerate(hand_value_names_ranked), reverse=True
        ):
            self.hand_subvalue = hand_values_by_name[hand_value_name](self)
            if self.hand_subvalue is not None:
                self.hand_value = i
                break
        assert (
            self.hand_subvalue is not None
        )  # at least one hand type (High Card) should have matched

    def __lt__(self, other: "PokerHand") -> bool:
        if not isinstance(other, type(self)):
            raise ValueError(
                f"object of type PokerHand can't be compared with object of other type {type(other)}"
            )
        return (self.hand_value, self.hand_subvalue) < (
            other.hand_value,
            other.hand_subvalue,
        )  # tuple comparison is so convenient

    @hand_value
    def is_flush(self) -> list[PokerCard.Value] | None:
        cards_by_color = sorted(self.cards, key=lambda card: card.color)
        if cards_by_color[0].color == cards_by_color[4].color:
            return list(card.value for card in self.cards)
        else:
            return None

    @hand_value
    def is_straight(self) -> PokerCard.Value | None:
        if self.cards[4].value == int(self.cards[0].value) + 4:
            return self.cards[4]
        elif (
            self.cards[0] == PokerCard.Value.ACE
            and self.cards[1] == 10
            and self.cards[4] == PokerCard.Value.KING
        ):
            # special case for royal straight because aces have technically the value 1
            return PokerCard.Value.ACE
        else:
            return None

    @hand_value
    def is_straight_flush(self) -> PokerCard.Value | None:
        if self.is_flush():
            return self.is_straight()
        # return self.flush() and self.straight() # shorter, but less explicit

    @hand_value
    def is_four_of_a_kind(self) -> tuple[PokerCard.Value, PokerCard.Value] | None:
        if self.values[0][0] == 4:
            return self.values[0][1], self.values[1][1]
        else:
            return None

    @hand_value
    def is_full_house(self) -> tuple[PokerCard.Value, PokerCard.Value] | None:
        if self.values[0][0] == 3 and self.values[1][0] == 2:
            return self.values[0][1], self.values[1][1]
        else:
            return None

    @hand_value
    def is_three_of_a_kind(
        self,
    ) -> tuple[PokerCard.Value, PokerCard.Value, PokerCard.Value] | None:
        if self.values[0][0] == 3:
            return tuple(value[1] for value in self.values)
        else:
            return None

    @hand_value
    def is_two_pairs(
        self,
    ) -> tuple[PokerCard.Value, PokerCard.Value, PokerCard.Value] | None:
        if self.values[0][0] == 2 and self.values[1][0] == 2:
            return tuple(value[1] for value in self.values)
        else:
            return None

    @hand_value
    def is_pair(
        self,
    ) -> (
        tuple[PokerCard.Value, PokerCard.Value, PokerCard.Value, PokerCard.Value] | None
    ):
        if self.values[0][0] == 2:
            return tuple(value[1] for value in self.values)
        else:
            return None

    @hand_value
    def high_card(self) -> list[PokerCard.Value]:
        return [card.value for card in self.cards]

    def cards_by_value(self) -> list[tuple[int, PokerCard.Value]]:
        cards_by_value = defaultdict(int)
        for card in self.cards:
            cards_by_value[card.value] += 1
        return sorted(
            (number, value) for value, number in cards_by_value.items()
        )  # sorted first by number of cards, and then by card value


if __name__ == "__main__":
    from game_anywhere.run_game import run_game

    run_game(Poker)
