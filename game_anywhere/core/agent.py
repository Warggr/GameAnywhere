from typing import Tuple, List, Any, TypeVar, Union, Optional
from abc import ABC, abstractmethod

AgentId = int

T = TypeVar('T')
U = TypeVar('U')

class Agent(ABC):
    class Surrendered(Exception):
        pass

    @abstractmethod
    def message(self, message: str) -> None:
        ...

    @abstractmethod
    def update(self, diff : List[Any]):
        ...

    @abstractmethod
    def get_2D_choice(self, dimensions: Tuple[int, int]) -> Tuple[int, int]:
        ...

    @abstractmethod
    def choose_one_component_slot(self, slots : List['ComponentSlot'], indices : Optional[List[T]] = None, special_options:List[U]=[]) -> Union[T,U]:
        ...

    @abstractmethod
    def text_choice(self, options: List[str]) -> str:
        ...

    @abstractmethod
    def int_choice(self, min: int|None=0, max: int|None = None) -> int:
        ...
