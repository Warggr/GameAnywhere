from typing import Optional, Any, NoReturn, Union
from abc import ABC, abstractmethod
from .agent import Agent, AgentId
from ..components.component import ComponentOrGame
from ..components.utils import html


class GameSummary(ABC):
    NO_WINNER = 0

    @abstractmethod
    def get_winner(self) -> AgentId: ...


class SimpleGameSummary(GameSummary):
    def __init__(self, winner: AgentId):
        self.winner = winner

    def get_winner(self):
        return self.winner


"""
Represents a game in progress.
"""


# ComponentOrGame is an ABC, so indirectly Game is also an ABC
class Game(ComponentOrGame):
    def __init__(self, agent_descriptions: Union[list["AgentDescriptor"],"AgentDescriptor"], nb_agents: int|None = None):
        super().__init__()
        if type(agent_descriptions) == list:
            assert nb_agents is None or nb_agents == len(agent_descriptions)
            nb_agents = len(agent_descriptions)
        elif nb_agents is not None:
            pass
        else:
            nb_agents = self.NB_PLAYERS
        self.agents: list[Agent]|list[None] = [None] * nb_agents

    @property
    def NB_PLAYERS(self):
        """ Override this to set the only possible number of players of the game """
        return 2

    @classmethod
    def parse_config(cls, config: list[str]) -> dict[str, Any]|NoReturn:
        """ Override this to accept configuration options """
        if len(config) == 0:
            return {}
        else:
            raise NotImplementedError(f'{cls.__name__} does not accept configuration options')

    # override
    def get_game(self):
        return self

    # override
    def get_slot_address(self):
        return ""

    def message(self, *args, **kwargs):
        for agent in self.agents:
            agent.message(*args, **kwargs)

    def log_component_update(
        self,
        address,
        data: dict[str, Any],
        hidden: bool = False,
        owner_id: Optional[int] = None,
    ):
        if self.agents[0] is None:
            return # Return early if the agents are not initialized yet
        for agent_id, agent in enumerate(self.agents):
            masked_update = {"id": address, **data}
            for key in ["new_value", "append"]:
                if key in data:
                    masked_update[key] = html(masked_update[key], viewer_id=agent_id)
            agent.update([masked_update])

    # Subclasses might override this if they need to be notified once the real agents are available
    # TODO: this is ugly, most overrides do not actually require the agents to be loaded
    def set_agents(self, agents: list[Agent]):
        self.agents = agents

    @abstractmethod
    def play_game(self) -> GameSummary: ...

    def __enter__(self):
        return self

    def __exit__(self, extype, exvalue, traceback):
        pass

# TODO: possible improvements:
# Game could detect automatically when Components exist as class properties
# and translate them to ComponentSlotProperties
