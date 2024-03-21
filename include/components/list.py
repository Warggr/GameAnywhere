from typing import TypeVar, Generic, Type, Union, List, Tuple, Callable, Iterable, Optional
from abc import ABC
from .component import Component, ComponentSlot
from game_anywhere.include.ui import Html, div, style

T = TypeVar('T', bound=Component)

class List(list, Component, Generic[T]):
    def __init__(self, *args):
        simple_list_of_components = list(*args) # TODO: this is ugly
        simple_list_of_slots = [
            ComponentSlot(id=i, content=component, parent=self)
            for i, component in enumerate(simple_list_of_components)
        ]
        list.__init__(self, simple_list_of_slots)
        Component.__init__(self)

    def html(self) -> Html:
        return Html(
            *(field.html() for field in self)
        )
