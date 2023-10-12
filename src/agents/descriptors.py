import asyncio
from game_anywhere.include.core.agent import Agent
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
        raise NotImplementedError()

    @abstractmethod
    def await_initialization(self, promise : AgentPromise) -> Agent:
        raise NotImplementedError()

GameType = TypeVar('GameType', bound='Game')

class GameDescriptor(Generic[GameType]):
    def __init__(self, GameType : Type[GameType], agents_descriptors: List[AgentDescriptor]):
        self.GameType = GameType
        self.agents_descriptors = agents_descriptors

    def create(self, context) -> GameType:
        promises : List[AgentPromise] = []
        for i, agent in enumerate(self.agents_descriptors):
            promises.append( agent.start_initialization(i, context) )

        agents : List[Agent] = []
        for i, agent in enumerate(self.agents_descriptors):
            agents.append( agent.await_initialization(promises[i]) )

        return self.GameType(agents)
