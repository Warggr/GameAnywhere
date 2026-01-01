from typing import Any, TypeVar, Union, Optional
from abc import ABC, abstractmethod

from game_anywhere.protocols import JsonSchema

AgentId = int

T = TypeVar("T")
U = TypeVar("U")


class ChatStream:
    def __aiter__(self):
        return self

    @abstractmethod
    async def __anext__(self) -> str: ...

    @abstractmethod
    def close(self): ...


class Agent(ABC):
    class Surrendered(Exception):
        pass

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def message(self, message: str, **kwargs) -> None: ...

    @abstractmethod
    def update(self, diff: list[Any]):
        """`diff` should conform to the JSON patch standard.""" # TODO: enforce or type-hint this
        ...

    @abstractmethod
    def query(self, allowedSchema: JsonSchema): ...

    @abstractmethod
    def choose_one_component_slot(
        self,
        slots: list["ComponentSlot"],
        indices: Optional[list[T]] = None,
        special_options: list[U] = [],
        message: str|None = None,
    ) -> Union[T, U]: ...

    @abstractmethod
    def text_choice(self, options: list[str]) -> str: ...

    @abstractmethod
    def int_choice(self, min: int | None = 0, max: int | None = None) -> int: ...

    def boolean_choice(self, message: str) -> bool:
        self.message(message + "? [yes/no]")
        return self.text_choice(["yes", "no"]) == "yes"

    @abstractmethod
    def chat_stream(self, event_loop: "asyncio.AbstractEventLoop") -> ChatStream: ...

    def get_2D_choice(self, dimensions: tuple[int, int]):
        return tuple(self.int_choice(min=0, max=dim - 1) for dim in dimensions)
