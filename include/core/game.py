from typing import List
from abc import ABC, abstractmethod
from .agent import Agent, AgentId

html = str

class GameSummary(ABC):
    NO_WINNER = 0

    @abstractmethod
    def get_winner(self) -> AgentId:
        raise NotImplementedError()


class SimpleGameSummary(GameSummary):
    def __init__(self, winner: AgentId):
        self.winner = winner

    def get_winner(self):
        return self.winner


"""
Represents a game in progress. Most often has a gameState attribute.
"""
class Game(ABC):
    def __init__(self, agents: List[Agent]):
        self.agents = agents

    @abstractmethod
    def play_game(self) -> GameSummary:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def html() -> html:
        raise NotImplementedError()
