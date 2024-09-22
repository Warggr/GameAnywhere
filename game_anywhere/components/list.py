from typing import TypeVar, Generic, Iterable

from game_anywhere.ui import Html
from .component import Component, ComponentSlot
from .utils import mask, html

T = TypeVar("T", bound=Component)


class List(Component, Generic[T]):
    def __init__(self, *args, **kwargs):
        components = list(*args)
        self.kwargs = kwargs
        slots = [
            ComponentSlot(id=str(i), content=component, parent=self, **self.kwargs)
            for i, component in enumerate(components)
        ]
        self.slots = slots
        super().__init__()

    # Component interface methods

    def html(self, viewer_id=None) -> Html:
        hidden = self.kwargs.get("hidden", False)
        owner_id = self.kwargs.get("owner_id", None)
        if hidden and viewer_id != owner_id:
            function = mask
        else:
            function = html
        return Html(*(function(field, viewer_id=viewer_id) for field in self.slots))

    # list interface methods - the most basic ones

    def append(self, value: Component):
        slot = ComponentSlot(id=str(len(self.slots)), parent=self, **self.kwargs)
        self.slots.append(slot)
        # log update, see ComponentSlot.set()
        try:
            game = self.get_game()
            game.log_component_update(self.get_slot_address(), {"append": slot})
        except Component.NotAttachedToComponentTree:
            pass
        # set slot content separately, so that the slot can decide itself how it wants to log the update event (and take e.g. the hidden flag into account).
        # TODO: there might be a cleaner way of doing this
        slot.set(value)

    def __getitem__(self, index):
        return self.slots[index].get()

    def __setitem__(self, index, value):
        self.slots[index].set(value)

    # list interface methods - syntactic sugar

    def __iter__(self):
        # When iterating, we can't replace one value. So just dealing with components and ignoring slots is appropriate here
        return (slot._content for slot in self.slots)

    def __iadd__(self, other_list: list[Component]):
        for i in other_list:
            self.append(i)

    def extend(self, values_iter: Iterable[Component]):
        for i in values_iter:
            self.append(i)

    # useful methods

    def __copy__(self):
        copy = type(self)()
        copy.__dict__.update(self.__dict__)
        copy.slot = None  # copy shouldn't be attached to the component tree
        return copy
