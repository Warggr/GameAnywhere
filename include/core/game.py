from typing import List, Optional
from abc import ABC, abstractmethod
from .agent import Agent, AgentId
from ..ui import Html
from ..components import Component

class GameSummary(ABC):
    NO_WINNER = 0

    @abstractmethod
    def get_winner(self) -> AgentId:
        ...


class SimpleGameSummary(GameSummary):
    def __init__(self, winner: AgentId):
        self.winner = winner

    def get_winner(self):
        return self.winner


"""
Represents a game in progress. Most often has a gameState attribute.
"""
class Game(ABC):
    def __init__(self):
        self.agents : Optional[List[Agent]] = None

    @abstractmethod
    def play_game(self) -> GameSummary:
        ...

    def html(self) -> Html:
        result = Html()
        for attrname, attr in self.__dict__.items():
            print("Checking attr", attrname, end='...')
            if isinstance(attr, Component):
                print('A Component with html', attr.html())
                result += attr.html()
            else:
                print('Not a component')
        return result
