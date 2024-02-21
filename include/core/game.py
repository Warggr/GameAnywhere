from typing import List, Optional
from abc import ABC, abstractmethod
from .agent import Agent, AgentId
from ..ui import Html
from ..components import ComponentSlot
from ..components.component import ComponentOrGame

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
class Game(ComponentOrGame): # ComponentOrGame is an ABC, so indirectly Game is also an ABC
    def __init__(self, agent_descriptions : List['AgentDescriptor']):
        self.agents : Optional[List[Agent]] = [ None for _ in range(len(agent_descriptions)) ]

    # override
    def get_game(self):
        return self

    # override
    def get_slot_address(self):
        return ''

    def log_component_update(self, address, new_value : 'Component'):
        for agent in self.agents:
            agent.update([{ 'id': address, 'new_value': new_value }])

    @abstractmethod
    def play_game(self) -> GameSummary:
        ...

    def html(self) -> Html:
        result = Html()
        for attrname, attr in self.__dict__.items(): # TODO: it would be more efficient if games provided a list of their slots themselves
            print("Checking attr", attrname, end='...')
            if isinstance(attr, ComponentSlot):
                print('A ComponentSlot with html', attr.html())
                result += attr.html()
            else:
                print('Not a slot')
        return result
