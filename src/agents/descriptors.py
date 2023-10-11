import asyncio
from game_anywhere.include.core.agent import Agent
from abc import abstractmethod, ABC
from typing import List, Any
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

class GameDescriptor:
    def __init__(self, game_class, agents_descriptors: List[AgentDescriptor]):
        self.game_class = game_class
        self.agents_descriptors = agents_descriptors

    def create(self, context) -> 'Game':
        promises : List[AgentPromise] = []
        for i, agent in enumerate(self.agents_descriptors):
            promises.append( agent.start_initialization(i, context) )

        agents : List[Agent] = []
        for i, agent in enumerate(self.agents_descriptors):
            agents.append( agent.await_initialization(promises[i]) )

        return self.game_class(agents)
