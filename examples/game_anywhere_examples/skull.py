import random
from enum import Enum, auto, unique

from game_anywhere.components import Component, ComponentSlotProperty, List, PerPlayer
from game_anywhere.components.component import PerPlayerComponent
from game_anywhere.core import SimpleGameSummary, TurnBasedGame
from game_anywhere.run_game import run_game_from_cmdline


@unique
class SkullCardType(Enum):
    SKULL = auto()
    FLOWER = auto()


class SkullCard(Component):
    def __init__(self, value: SkullCardType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = value

    def __str__(self):
        match self.value:
            case SkullCardType.SKULL:
                return "💀"
            case SkullCardType.FLOWER:
                return "💮"

    HIDDEN_HTML = "🟠"

    def html(self, viewer_id=None) -> str:
        return str(self)


class PlayerBoard(PerPlayerComponent):
    hand_cards = ComponentSlotProperty[List[SkullCard]]()
    played_cards = ComponentSlotProperty[List[SkullCard]]()
    score = ComponentSlotProperty[int]()


class Skull(TurnBasedGame):
    players = PerPlayer(PlayerBoard)

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {"_num_players": {"type": "integer", "minimum": 3, "maximum": 6}},
        "required": ["_num_players"],
    }

    def __init__(self, agent_descriptions, *args, **kwargs):
        if not 3 <= len(agent_descriptions) <= 6:
            raise ValueError("Skull is designed for 3 to 6 players.")
        super().__init__(agent_descriptions, *args, **kwargs)
        self.starting_with = 0

        for player_id, player in zip(self.agent_ids, self.players, strict=True):
            player.hand_cards = List(
                [
                    SkullCard(SkullCardType.SKULL),
                    SkullCard(SkullCardType.FLOWER),
                    SkullCard(SkullCardType.FLOWER),
                    SkullCard(SkullCardType.FLOWER),
                ],
                hidden=True,
                owner_id=player_id,
            )
            player.played_cards = List([], hidden=True, owner_id=player_id)
            player.score = 0

    def turn(self):
        self._play_round()

        for agent_id, player in zip(self.agent_ids, self.players, strict=True):
            if player.score >= 2:
                return SimpleGameSummary(agent_id)

        remaining_players = self._active_players()
        if len(remaining_players) == 1:
            return SimpleGameSummary(list(self.agent_ids)[remaining_players[0]])

        return None

    def _play_round(self):
        self._clear_table()
        active_players = self._active_players()
        self.starting_with = self._next_active_player(
            self.starting_with, active_players
        )
        self.message(
            f"New round. Starting player: {self.players[self.starting_with].owner.name}."
        )

        turn_order = self._turn_order(active_players, self.starting_with)
        for player_index in turn_order:
            self._play_one_card(player_index, mandatory=True)

        highest_bid: int | None = None
        highest_bidder: int | None = None
        passed: set[int] = set()
        current_player = self._next_active_player(
            (turn_order[-1] + 1) % len(self.players), active_players
        )

        while True:
            cards_in_play = self._total_cards_in_play()
            assert cards_in_play > 0

            if highest_bidder is not None and self._remaining_bidders(
                active_players, passed
            ) == [highest_bidder]:
                break

            player = self.players[current_player]
            agent = player.get_owner()

            if highest_bidder is None:
                options = ["Bid"]
                if len(player.hand_cards) > 0:
                    options.insert(0, "Play card")
                action = agent.text_choice(options)
                if action == "Play card":
                    self._play_one_card(current_player)
                    current_player = self._next_active_player(
                        (current_player + 1) % len(self.players), active_players
                    )
                    continue

                highest_bid = agent.int_choice(mini=1, maxi=cards_in_play)
                highest_bidder = current_player
                self.message(
                    f"{player.owner.name} bids {highest_bid}.",
                    sender=player.owner.name,
                )
                if highest_bid == cards_in_play:
                    break
                current_player = self._next_active_player(
                    (current_player + 1) % len(self.players), active_players
                )
                continue

            if current_player == highest_bidder:
                break

            minimum_raise = highest_bid + 1
            can_raise = minimum_raise <= cards_in_play
            options = ["Pass"]
            if can_raise:
                options.append("Raise")
            action = agent.text_choice(options)
            if action == "Raise":
                highest_bid = agent.int_choice(mini=minimum_raise, maxi=cards_in_play)
                highest_bidder = current_player
                self.message(
                    f"{player.owner.name} raises to {highest_bid}.",
                    sender=player.owner.name,
                )
                if highest_bid == cards_in_play:
                    break
            else:
                passed.add(current_player)
                self.message(f"{player.owner.name} passes.", sender=player.owner.name)

            current_player = self._next_active_player(
                (current_player + 1) % len(self.players), active_players
            )

        assert highest_bidder is not None and highest_bid is not None
        self._resolve_challenge(highest_bidder, highest_bid)

    def _resolve_challenge(self, challenger_index: int, target: int):
        challenger = self.players[challenger_index]
        self.message(
            f"{challenger.owner.name} must reveal {target} flower(s).",
            sender=challenger.owner.name,
        )

        revealed = 0
        own_slots = list(reversed(challenger.played_cards.slots))
        for slot in own_slots:
            if revealed >= target:
                break
            card = slot.content
            self._reveal_slot(slot)
            if card.value == SkullCardType.SKULL:
                self.message(
                    f"{challenger.owner.name} revealed their own skull and failed."
                )
                self._on_failed_challenge(challenger_index, challenger_index)
                return
            revealed += 1

        while revealed < target:
            choices = []
            for player_index in self._active_players():
                if player_index == challenger_index:
                    continue
                played_cards = self.players[player_index].played_cards
                if len(played_cards) == 0:
                    continue
                top_slot = self._top_hidden_slot(played_cards)
                if top_slot is None:
                    continue
                choices.append(top_slot)

            chosen_slot = challenger.get_owner().choose_one_component_slot(
                choices,
                choices,
            )
            card = chosen_slot.content
            self._reveal_slot(chosen_slot)
            if card.value == SkullCardType.SKULL:
                skull_owner = chosen_slot.owner_id
                self.message(
                    f"{challenger.owner.name} revealed {self.players[skull_owner].owner.name}'s skull and failed."
                )
                self._on_failed_challenge(challenger_index, skull_owner)
                return
            revealed += 1

        challenger.score += 1
        self.starting_with = challenger_index
        self.message(
            f"{challenger.owner.name} completed the challenge and now has {challenger.score} point(s)."
        )
        self._clear_table()

    def _on_failed_challenge(self, challenger_index: int, next_start_player: int):
        self._collect_played_cards(challenger_index)
        challenger = self.players[challenger_index]
        lost_card = random.choice(list(challenger.hand_cards))
        challenger.hand_cards.remove(lost_card)
        self.starting_with = next_start_player
        self.message(f"{challenger.owner.name} loses one random card.")
        self._clear_table(skip_players={challenger_index})

    def _clear_table(self, skip_players: set[int] | None = None):
        if skip_players is None:
            skip_players = set()
        for player_index in self._active_players(include_empty_hands=True):
            if player_index in skip_players:
                continue
            self._collect_played_cards(player_index)

    def _collect_played_cards(self, player_index: int):
        player = self.players[player_index]
        while len(player.played_cards) > 0:
            card = player.played_cards.pop()
            player.hand_cards.append(card)

    def _play_one_card(self, player_index: int, mandatory: bool = False):
        player = self.players[player_index]
        card = (
            player.get_owner()
            .choose_one_component_slot(
                [slot for slot in player.hand_cards.get_slots().values()]
            )
            .content
        )
        player.hand_cards.remove(card)
        player.played_cards.append(card)
        if mandatory:
            self.message(f"{player.owner.name} places their opening card.")
        else:
            self.message(f"{player.owner.name} adds another face-down card.")

    def _reveal_slot(self, slot):
        slot.hidden = False
        slot.reveal()

    def _active_players(self, include_empty_hands: bool = False) -> list[int]:
        result = []
        for index, player in enumerate(self.players):
            has_cards = len(player.hand_cards) > 0 or len(player.played_cards) > 0
            if include_empty_hands or has_cards:
                result.append(index)
        return result

    def _next_active_player(
        self, current: int, players: list[int] | None = None
    ) -> int:
        if players is None:
            players = self._active_players()
        start = current
        while True:
            if current in players:
                return current
            current = (current + 1) % len(self.players)
            if current == start:
                raise RuntimeError("No active players remain.")

    def _turn_order(self, players: list[int], start: int) -> list[int]:
        order = []
        current = start
        while len(order) < len(players):
            if current in players:
                order.append(current)
            current = (current + 1) % len(self.players)
        return order

    def _remaining_bidders(self, players: list[int], passed: set[int]) -> list[int]:
        return [player for player in players if player not in passed]

    def _total_cards_in_play(self) -> int:
        return sum(len(player.played_cards) for player in self.players)

    def _top_hidden_slot(self, cards: List[SkullCard]):
        for slot in reversed(cards.slots):
            if slot.hidden:
                return slot
        return None


if __name__ == "__main__":
    run_game_from_cmdline(Skull)
