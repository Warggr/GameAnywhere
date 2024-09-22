from typing import Optional, Any
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
Represents a game in progress. Most often has a gameState attribute.
"""


class Game(
    ComponentOrGame
):  # ComponentOrGame is an ABC, so indirectly Game is also an ABC
    def __init__(self, agent_descriptions: list["AgentDescriptor"]):
        self.agents: Optional[list[Agent]] = [
            None for _ in range(len(agent_descriptions))
        ]

    @classmethod
    def parse_config(cls, config: str) -> dict[str, Any]:
        breakpoint()
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

    @abstractmethod
    def play_game(self) -> GameSummary: ...
