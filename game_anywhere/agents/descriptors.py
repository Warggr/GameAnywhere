from game_anywhere.core.agent import Agent
from abc import abstractmethod, ABC
from typing import Any, TypeVar, Type, Generic
from contextlib import ExitStack

AgentPromise = Any


class Context(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["exit_stack"] = ExitStack()


class AgentDescriptor(ABC):
    def __init__(self):
        self.name = None

    @abstractmethod
    def start_initialization(self, id: "AgentId", context: Context) -> AgentPromise: ...

    @abstractmethod
    def await_initialization(self, promise: AgentPromise) -> Agent: ...

    def resolve_name(self, name: str):
        self.name = name


GameType = TypeVar("GameType", bound="Game")


class GameDescriptor(Generic[GameType]):
    def __init__(
        self, GameType: Type[GameType], agents_descriptors: list[AgentDescriptor],
        *game_args, **game_kwargs
    ):
        self.GameType = GameType
        self.agents_descriptors = agents_descriptors
        self.game_args = game_args
        self.game_kwargs = game_kwargs

    def start_initialization(self, context) -> list[AgentPromise]:
        return [
            agent.start_initialization(i, context)
            for i, agent in enumerate(self.agents_descriptors)
        ]

    def await_initialization(self, promises: list[AgentPromise]) -> list[Agent]:
        return [
            agent.await_initialization(promises[i])
            for i, agent in enumerate(self.agents_descriptors)
        ]

    def create_agents(self, context) -> list[Agent]:
        promises = self.start_initialization(context)
        agents = self.await_initialization(promises)
        return agents

    def create_game(self) -> GameType:
        game = self.GameType(self.agents_descriptors, *self.game_args, **self.game_kwargs)
        if type(self.agents_descriptors) is not list:
            #  sorry for the code duplication with subclasses of Agent
            self.agents_descriptors = [self.agents_descriptors] * len(game.agents)
        return game
