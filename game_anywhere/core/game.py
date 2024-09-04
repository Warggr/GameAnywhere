from typing import Optional, Any
from abc import ABC, abstractmethod
from .agent import Agent, AgentId
from ..components.component import ComponentOrGame

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
        for agent_id, agent in enumerate(self.agents):
            if hidden and owner_id != agent_id:
                agent.update([{ 'id': address, 'hidden': True }])
            if not hidden or owner_id == agent_id:
                agent.update([{ 'id': address, **data }])

    @abstractmethod
    def play_game(self) -> GameSummary: ...
