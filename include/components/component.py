from abc import ABC, abstractmethod
from game_anywhere.include.core.game import html

class Component(ABC):
    @staticmethod
    @abstractmethod
    def html() -> html:
        raise NotImplementedError()
