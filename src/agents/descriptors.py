import asyncio
from game_anywhere.include.core.agent import Agent
from abc import abstractmethod, ABC
from typing import List

class AgentDescriptor(ABC):
    @abstractmethod
    def start_initialization(self, id : 'AgentId', context):
        raise NotImplementedError()

    @abstractmethod
    def await_initialization(self, promise) -> Agent:
        raise NotImplementedError()

class GameDescriptor:
    def __init__(self, game_class, agents: List[AgentDescriptor]):
        self.game_class = game_class
        self.agents = agents
    def create(self) -> 'Game':
        return self.game_class(self.agents)
