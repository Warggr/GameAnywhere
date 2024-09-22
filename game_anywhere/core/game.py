from typing import Optional, Any, NoReturn, Union
from abc import ABC, abstractmethod
from .agent import Agent, AgentId
from ..components.component import ComponentOrGame
from ..components.utils import mask


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
    def parse_config(cls, config: str) -> dict[str, Any]|NoReturn:
        """ Override this to accept configuration options """
        raise NotImplementedError(f'{cls.__name__} does not accept configuration options')

    # override
    def get_game(self):
        return self

    # override
    def get_slot_address(self):
        return ""

    def log_component_update(
        self,
        address,
        data: dict[str, Any],
        hidden: bool = False,
        owner_id: Optional[int] = None,
    ):
        update = {"id": address, **data}
        if hidden:
            masked_update = {"id": address, **data, "hidden": True}
            for key in ["new_value", "append"]:
                if key in data:
                    masked_update[key] = mask(masked_update[key])
        for agent_id, agent in enumerate(self.agents):
            if hidden and owner_id != agent_id:
                agent.update([masked_update])
            if not hidden or owner_id == agent_id:
                agent.update([update])

    # Subclasses might override this if they need to be notified once the real agents are available
    def set_agents(self, agents: list[Agent]):
        self.agents = agents

    @abstractmethod
    def play_game(self) -> GameSummary: ...
