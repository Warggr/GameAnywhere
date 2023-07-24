from typing import List
from .agent import Agent

AgentId = int

class GameSummary:
    NO_WINNER = 0

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
class Game:
    def __init__(self, agents: List[Agent]):
        self.agents = agents

    def play_game(self) -> GameSummary:
        raise NotImplementedError()
