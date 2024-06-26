import asyncio
from game_anywhere.core.agent import Agent
from abc import abstractmethod, ABC
from typing import List, Any, TypeVar, Type, Generic
from contextlib import ExitStack

AgentPromise = Any

class Context(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['exit_stack'] = ExitStack()

class AgentDescriptor(ABC):
    @abstractmethod
    def start_initialization(self, id : 'AgentId', context : Context) -> AgentPromise:
        ...

    @abstractmethod
    def await_initialization(self, promise : AgentPromise) -> Agent:
        ...

GameType = TypeVar('GameType', bound='Game')

class GameDescriptor(Generic[GameType]):
    def __init__(self, GameType : Type[GameType], agents_descriptors: List[AgentDescriptor]):
        self.GameType = GameType
        self.agents_descriptors = agents_descriptors

    def start_initialization(self, context) -> List[AgentPromise]:
        return [ agent.start_initialization(i, context) for i, agent in enumerate(self.agents_descriptors) ]

    def await_initialization(self, promises : List[AgentPromise]) -> List[Agent]:
        return [ agent.await_initialization(promises[i]) for i, agent in enumerate(self.agents_descriptors) ]

    def create_agents(self, context) -> List[Agent]:
        promises = self.start_initialization(context)
        agents = self.await_initialization(promises)
        return agents

    def create_game(self) -> GameType:
        return self.GameType(self.agents_descriptors)
