from abc import ABC, abstractmethod
from contextlib import ExitStack
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Generic, Type, TypedDict, TypeVar

from game_anywhere.core.agent import Agent

if TYPE_CHECKING:
    from typing import Callable

    from game_anywhere.core import Game


AgentPromise = TypeVar("AgentPromise")


class Context(TypedDict):
    game: type["Game"]
    exit_stack: ExitStack


class AgentDescriptor(ABC, Generic[AgentPromise]):
    def __init__(self):
        self.name = None

    @abstractmethod
    def start_initialization(
        self, agent_descriptor_number: int, context: Context
    ) -> AgentPromise: ...

    @abstractmethod
    def is_initialized(self, promise: AgentPromise, /) -> bool: ...

    @abstractmethod
    def await_initialization(self, promise: AgentPromise, /) -> Agent: ...

    def set_game(self, game: Game, context: Context):
        pass

    def resolve_name(self, name: str):
        self.name = name


GameType = TypeVar("GameType", bound="Game")


@dataclass
class GamePromise(Generic[GameType]):
    """
    Can be passed to another thread to be awaited.
    """

    agent_descriptors: list[AgentDescriptor[Any]]
    agent_promises: list[Any]
    game: Callable[[list[Agent]], GameType]
    context: Context

    def resolve(self) -> GameType:
        agents = [
            agent.await_initialization(self.agent_promises[i])
            for i, agent in enumerate(self.agent_descriptors)
        ]
        # We have a bit of a chicken-and-egg problem where a Game needs a list of agents to work properly,
        # but some agents (e.g. NetworkAgent / BaseGameRoom) need a Game to work properly.
        # So we first create the agents, but always call set_game right afterwards
        game = self.game(agents)
        for descriptor in self.agent_descriptors:
            descriptor.set_game(game, self.context)
        return game


class GameDescriptor(Generic[GameType]):
    """
    Created when the game request is successfully parsed.
    """

    def __init__(
        self,
        GameType: Type[GameType],
        agents_descriptors: list[AgentDescriptor[Any]],
        *game_args,
        **game_kwargs,
    ):
        self.agents_descriptors = agents_descriptors
        self.game_type = GameType
        self.game_args, self.game_kwargs = game_args, game_kwargs

    def start_initialization(self, **context_kwargs) -> GamePromise[GameType]:
        context: Context = {"exit_stack": ExitStack(), "game": self.game_type}
        context.update(context_kwargs)
        promises = [
            agent.start_initialization(i, context)
            for i, agent in enumerate(self.agents_descriptors)
        ]
        return GamePromise(
            self.agents_descriptors,
            promises,
            partial(self.game_type, *self.game_args, **self.game_kwargs),
            context,
        )
