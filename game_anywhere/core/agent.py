from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union

from game_anywhere.protocols import JsonSchema

if TYPE_CHECKING:
    import asyncio
    from typing import Sequence

    from game_anywhere.components import ComponentSlot


T = TypeVar("T")
U = TypeVar("U")


class ChatStream:
    def __aiter__(self):
        return self

    @abstractmethod
    async def __anext__(self) -> str: ...

    def close(self):
        pass


class Agent(ABC):
    class Surrendered(Exception):
        pass

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def message(self, message: str, **kwargs) -> None: ...

    @abstractmethod
    def update(self, diffs: list[Any]):
        """`diffs` should conform to the JSON patch standard."""  # TODO: enforce or type-hint this
        ...

    @abstractmethod
    def query(self, allowedSchema: JsonSchema) -> Any: ...

    @abstractmethod
    def choose_one_component_slot(
        self,
        slots: Sequence["ComponentSlot"],
        indices: Optional[list[T]] = None,
        special_options: Sequence[U] = (),
        message: str | None = None,
    ) -> Union[T, U]: ...

    @abstractmethod
    def text_choice(self, options: list[str]) -> str: ...

    @abstractmethod
    def int_choice(self, mini: int | None = 0, maxi: int | None = None) -> int: ...

    def boolean_choice(self, message: str) -> bool:
        self.message(message + "? [yes/no]")
        return self.text_choice(["yes", "no"]) == "yes"

    @abstractmethod
    def chat_stream(self, event_loop: "asyncio.AbstractEventLoop") -> ChatStream: ...

    def get_2D_choice(self, dimensions: tuple[int, int]):
        return tuple(self.int_choice(mini=0, maxi=dim - 1) for dim in dimensions)
