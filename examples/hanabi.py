from typing import Union, Any
from dataclasses import dataclass
from enum import Enum, unique, auto

from game_anywhere.components.component import PerPlayerComponent

from game_anywhere.run_game import run_game_from_cmdline
from game_anywhere.components import PerPlayer, ComponentSlotProperty, ComponentSlot, List, Dict
from game_anywhere.core import TurnBasedGame, GameSummary, Agent
from game_anywhere.core.agent import AgentId
from game_anywhere.components.traditional.cards import Deck, DiscardPile

@unique
class Color(Enum):
    WHITE = auto()
    YELLOW = auto()
    RED = auto()
    BLUE = auto()
    GREEN = auto()


@dataclass
class HanabiCard:
    color: Color
    value: int


def default_hanabi_deck() -> list[HanabiCard]:
    deck = []
    for color in Color:
        for value in (1, 2, 3, 4, 5):
            if value == 1:
                deck += [HanabiCard(color, value)] * 3
            elif value == 5:
                deck.append(HanabiCard(color, value))
            else:
                deck += [HanabiCard(color, value)] * 2
    return deck


class EveryoneCanSeeItExceptMyself(ComponentSlot):
    # override
    def can_be_seen_by(self, viewer_id=None):
        return viewer_id is not None and viewer_id != self.owner_id


class HanabiPerPlayerComponent(PerPlayerComponent):
    cards = ComponentSlotProperty[List[HanabiCard]]()


class Hanabi(TurnBasedGame):
    @dataclass
    class Summary(GameSummary):
        cards_played: int

        def get_winner(self) -> AgentId:
            raise NotImplementedError("There is no winner in Hanabi. It's a cooperative game.")

    nb_lives = ComponentSlotProperty[int]()
    nb_hints = ComponentSlotProperty[int]()
    deck = ComponentSlotProperty[Deck[HanabiCard]]()
    players = PerPlayer(HanabiPerPlayerComponent)
    stacks = ComponentSlotProperty[Dict[List[HanabiCard]]]()
    discard_pile = ComponentSlotProperty[DiscardPile[HanabiCard]]()
    MAX_HINTS = 8

    @classmethod
    def parse_config(cls, config: list[str]) -> dict[str, Any]:
        assert len(config) == 1, "Only one configuration option allowed: number of players"
        return {'nb_players': int(config[0])}

    def __init__(self, agent_descriptions, nb_players):
        assert 2 <= nb_players <= 5, "Hanabi can be played only between 2 and 5 players"
        super().__init__(agent_descriptions=agent_descriptions, nb_agents=nb_players)
        self.deck = Deck(default_hanabi_deck(), shuffled=True)
        self.nb_hints = self.MAX_HINTS
        self.nb_lives = 3
        self.stacks = Dict[Color, List]()
        self.discard_pile = DiscardPile()

    def set_agents(self, agents: list[Agent]):
        super().set_agents(agents)
        self.players: List[HanabiPerPlayerComponent] = PerPlayer.INIT  # typing: ignore
        nb_players = len(agents)
        CARDS_PER_PLAYER = 5 if nb_players <= 3 else 4
        for i, player in enumerate(self.players):
            player.cards = List(self.deck.draw(CARDS_PER_PLAYER), slotClass=EveryoneCanSeeItExceptMyself, owner_id=i)

    def turn(self) -> Union['Hanabi.Summary', None]:
        options = ['Place card', 'Cycle card']
        if self.nb_hints > 0:
            options.append('Give hint')
        choice = self.get_current_agent().text_choice(options)
        if choice == 'Place card':
            card = self.get_current_agent().choose_one_component_slot(
                [slot for _, slot in self.players[self.get_current_agent_index()].cards.get_slots()]
            ).content
            self.players[self.get_current_agent_index()].cards.remove(card)
            if card.color not in self.stacks and card.value == 1:
                self.stacks[card.color] = List([card])
            elif card.color in self.stacks and self.stacks[card.color][-1].value == card.value - 1:
                self.stacks[card.color].append(card)
            else:
                self.discard_pile.append(card)
                self.nb_lives -= 1
                if self.nb_lives == 0:
                    return self.Summary(sum(len(stack) for stack in self.stacks))
            self.players[self.get_current_agent_index()].cards.append(self.deck.draw())
        elif choice == 'Cycle card':
            card_slot = self.get_current_agent().choose_one_component_slot(
                [slot for _, slot in self.players[self.get_current_agent_index()].cards.get_slots()]
            )
            card = card_slot.take()
            self.discard_pile.append(card)
            self.players[self.get_current_agent_index()].cards.append(self.deck.draw())
            if self.nb_hints < self.MAX_HINTS:
                self.nb_hints += 1
        elif choice == 'Give hint':
            player_hinted = self.get_current_agent().choose_one_component_slot(
                [slot for i, (_, slot) in enumerate(self.players.get_slots()) if i != self.get_current_agent_index()]
            ).content
            options = {}
            for color in Color:
                options[str(color)] = color
            for i in (1, 2, 3, 4, 5):
                options[str(i)] = i
            hint_key = self.get_current_agent().text_choice(list(options.keys()))
            hint_key = options[hint_key]
            hint_value = []
            for _, slot in player_hinted.cards.get_slots():
                if (
                    type(hint_key) is int and slot.content.value == hint_key
                    or type(hint_key) is Color and slot.content.color == hint_key
                ):
                    hint_value.append({"id": slot.get_address(), "hint": f"is {hint_key}"})
                else:
                    hint_value.append({"id": slot.get_address(), "hint": f"is not {hint_key}"})
            self.agents[player_hinted.owner_id].update(hint_value)

            self.nb_hints -= 1
        else:
            raise AssertionError(f'Unrecognized choice: {choice}')

if __name__ == "__main__":
    run_game_from_cmdline(Hanabi)
