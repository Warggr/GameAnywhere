from typing import Union, Any
from dataclasses import dataclass
from enum import Enum, unique, auto

from game_anywhere.components.component import PerPlayerComponent

from game_anywhere.run_game import run_game_from_cmdline
from game_anywhere.components import PerPlayer, ComponentSlotProperty, ComponentSlot, List
from game_anywhere.core import TurnBasedGame, GameSummary, Agent
from game_anywhere.core.agent import AgentId
from game_anywhere.components.traditional.cards import Deck

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
        print(f"can_be_seen_by called with {viewer_id=}, {self.owner_id=}")
        return viewer_id is not None and viewer_id != self.owner_id


class HanabiPerPlayerComponent(PerPlayerComponent):
    cards = ComponentSlotProperty()


class Hanabi(TurnBasedGame):
    @dataclass
    class Summary(GameSummary):
        cards_played: int

        def get_winner(self) -> AgentId:
            raise NotImplementedError("There is no winner in Hanabi. It's a cooperative game.")

    nb_lives = ComponentSlotProperty()
    nb_hints = ComponentSlotProperty()
    deck = ComponentSlotProperty()
    players = PerPlayer(HanabiPerPlayerComponent)
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

    def set_agents(self, agents: list[Agent]):
        super().set_agents(agents)
        self.players = PerPlayer.INIT  # typing: ignore
        print("INIT finished")
        nb_players = len(agents)
        CARDS_PER_PLAYER = 5 if nb_players <= 3 else 4
        for i, player in enumerate(self.players):
            player.cards = List(self.deck.draw(CARDS_PER_PLAYER), slotClass=EveryoneCanSeeItExceptMyself, owner_id=i)

    def turn(self) -> Union['Hanabi.Summary', None]:
        options = ['Place card', 'Cycle card']
        if self.nb_hints > 0:
            options.append('Give hint')
        choice = self.get_current_agent().text_choice(options)


#if __name__ == "__main__":
#    run_game_from_cmdline(Hanabi)
