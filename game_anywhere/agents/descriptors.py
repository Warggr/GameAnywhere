from abc import ABC, abstractmethod
from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Type, TypedDict, TypeVar

from game_anywhere.core.agent import Agent

if TYPE_CHECKING:
    from game_anywhere.core import Game
    from game_anywhere.core.agent import AgentId

AgentPromise = Any


class Context(TypedDict):
    game: "Game"
    exit_stack: ExitStack


class AgentDescriptor(ABC):
    def __init__(self):
        self.name = None

    @abstractmethod
    def start_initialization(
        self, agent_id: "AgentId", context: Context
    ) -> AgentPromise: ...

    @abstractmethod
    def await_initialization(self, promise: AgentPromise) -> Agent: ...

    def resolve_name(self, name: str):
        self.name = name


GameType = TypeVar("GameType", bound="Game")


@dataclass
class GamePromise(Generic[GameType]):
    """
    Can be passed to another thread to be awaited.
    """

    agent_descriptors: list[AgentDescriptor]
    agent_promises: list[Any]
    game: GameType

    def resolve(self) -> GameType:
        agents = [
            agent.await_initialization(self.agent_promises[i])
            for i, agent in enumerate(self.agent_descriptors)
        ]
        self.game.set_agents(agents)
        return self.game


class GameDescriptor(Generic[GameType]):
    """
    Created when the game request is successfully parsed.
    """

    def __init__(
        self,
        GameType: Type[GameType],
        agents_descriptors: list[AgentDescriptor],
        *game_args,
        **game_kwargs,
    ):
        self.agents_descriptors = agents_descriptors
        self.game = GameType(
            self.agents_descriptors,
            *game_args,
            **game_kwargs,
        )

    def start_initialization(self, **context_kwargs) -> GamePromise[GameType]:
        context: Context = {"game": self.game, "exit_stack": ExitStack()}
        context.update(context_kwargs)
        promises = [
            agent.start_initialization(i, context)
            for i, agent in enumerate(self.agents_descriptors)
        ]
        if type(self.agents_descriptors) is not list:
            #  sorry for the code duplication with subclasses of Agent
            self.agents_descriptors = [self.agents_descriptors] * len(self.game.agents)
        return GamePromise(self.agents_descriptors, promises, self.game)
