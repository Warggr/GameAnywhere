from abc import ABC
from game_anywhere.include.core.game import html

class Component(ABC):
    def html(self) -> html:
        return str(self)
