from typing import Tuple, List, Any
from abc import ABC, abstractmethod

AgentId = int

class Agent(ABC):
    class Surrendered(Exception):
        pass

    @abstractmethod
    def message(self, message: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update(self, diff : List[Any]):
        pass

    @abstractmethod
    def get_2D_choice(self, dimensions: Tuple[int, int]) -> Tuple[int, int]:
        raise NotImplementedError()

    @abstractmethod
    def choose_one_component(self, components : List['Component']) -> 'Component':
        raise NotImplementedError()
