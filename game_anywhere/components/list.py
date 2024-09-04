from typing import TypeVar, Generic, Optional, Iterable
from abc import ABC
from .component import Component, ComponentSlot
from game_anywhere.ui import Html, div, style

T = TypeVar("T", bound=Component)


class List(Component, Generic[T]):
    def __init__(self, *args):
        components = list(*args)
        slots = [
            ComponentSlot(id=str(i), content=component, parent=self)
            for i, component in enumerate(components)
        ]
        self.slots = slots
        super().__init__()

    # Component interface methods

    def html(self) -> Html:
        return Html(
            *(field.html() for field in self.slots)
        )

    # list interface methods - the most basic ones

    def append(self, value: Component):
        slot = ComponentSlot(id=str(len(self.slots)), content=value, parent=self)
        self.slots.append(slot)
        # log update, see ComponentSlot.set()
        try:
            game = self.get_game()
            game.log_component_update(self.get_slot_address(), {"append": slot})
        except Component.NotAttachedToComponentTree:
            pass

    def __getitem__(self, index):
        return self.slots[index].get()

    def __setitem__(self, index, value):
        self.slots[index].set(value)

    # list interface methods - syntactic sugar

    def __iter__(self):
        # When iterating, we can't replace one value. So just dealing with components and ignoring slots is appropriate here
        return (slot._content for slot in self.slots)

    def __add__(self, other_list : list[Component]):
        copy = self.__copy__()
        for i in other_list:
            copy.append(i)
        return copy

    def extend(self, values_iter: Iterable[Component]):
        for i in values_iter:
            self.append(i)

    # useful methods

    def __copy__(self):
        copy = type(self)()
        copy.__dict__.update(self.__dict__)
        copy.slot = None  # copy shouldn't be attached to the component tree
        return copy
