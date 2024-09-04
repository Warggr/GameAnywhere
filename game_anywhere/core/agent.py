from typing import Any, TypeVar, Union, Optional
from abc import ABC, abstractmethod

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

    @abstractmethod
    def message(self, message: str) -> None: ...


    @abstractmethod
    def update(self, diff: list[Any]): ...

    @abstractmethod
    def get_2D_choice(self, dimensions: tuple[int, int]) -> tuple[int, int]: ...

    @abstractmethod
    def choose_one_component_slot(
        self,
        slots: list["ComponentSlot"],
        indices: Optional[list[T]] = None,
        special_options: list[U] = [],
    ) -> Union[T, U]: ...

    @abstractmethod
    def text_choice(self, options: list[str]) -> str: ...

    @abstractmethod
    def int_choice(self, min: int | None = 0, max: int | None = None) -> int: ...

    @abstractmethod
    def chat_stream(self, event_loop: "asyncio.AbstractEventLoop") -> ChatStream: ...
