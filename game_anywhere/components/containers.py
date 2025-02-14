from typing import TypeVar, Generic, Iterable, Iterator, Generator, MutableSequence, MutableMapping

from game_anywhere.ui import Html
from .component import Component, ComponentSlot

T = TypeVar("T", bound=Component)


class List(Component, Generic[T], MutableSequence[T]):
    def __init__(self, args, slotClass: type[ComponentSlot] = ComponentSlot, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        slots = [
            slotClass(id=str(i), content=component, parent=self, **self.kwargs)
            for i, component in enumerate(args)
        ]
        self.slots = slots

    # Component interface methods

    def get_slots(self) -> Generator[tuple[str, "ComponentSlot"]]:
        for i, slot in enumerate(self.slots):
            yield f"@[{i}]", slot

    def html(self, viewer_id=None) -> Html:
        return Html(*[slot.html(viewer_id=viewer_id) for slot in self.slots])

    # list interface methods - the most basic ones

    def insert(self, index, value):
        raise NotImplementedError()

    def append(self, value: Component):
        slot = ComponentSlot(id=str(len(self.slots)), parent=self, **self.kwargs)
        self.slots.append(slot)
        # log update, see ComponentSlot.set()
        try:
            game = self.get_game()
            game.log_new_slot(self, slot)
        except Component.NotAttachedToComponentTree:
            pass
        # set slot content separately, so that the slot can decide itself how it wants to log the update event (and take e.g. the hidden flag into account).
        # TODO: there might be a cleaner way of doing this
        slot.set(value)

    def __getitem__(self, index):
        return self.slots[index].get()

    def __setitem__(self, index, value):
        self.slots[index].set(value)

    def __delitem__(self, index):
        del self.slots[index]

    def __len__(self):
        return len(self.slots)

    # list interface methods - syntactic sugar

    def __iter__(self) -> Iterator[Component]:
        # When iterating, we can't replace one value. So just dealing with components and ignoring slots is appropriate here
        return (slot._content for slot in self.slots)

    def __iadd__(self, other_list: list[Component]):
        for i in other_list:
            self.append(i)
        return self

    def extend(self, values_iter: Iterable[Component]):
        for i in values_iter:
            self.append(i)

    # useful methods

    def __copy__(self):
        copy = type(self)()
        copy.__dict__.update(self.__dict__)
        copy.slot = None  # copy shouldn't be attached to the component tree
        return copy


Key = TypeVar("Key")


class Dict(Component, Generic[Key, T], MutableMapping[Key, T]):
    def __init__(self, content: dict[Key, T] = {}, slotClass: type[ComponentSlot] = ComponentSlot, **kwargs):
        super().__init__()
        self.slot_constructor = lambda *args, **other_kwargs: slotClass(*args, **other_kwargs, **kwargs)
        slots = {
            key: self.slot_constructor(id=str(key), content=value, parent=self)
            for key, value in content.items()
        }
        self.slots: dict[Key, ComponentSlot] = slots

    # Component interface methods
    def get_slots(self) -> Generator[tuple[str, ComponentSlot]]:
        for key, value in self.slots.items():
            yield str(key), value

    def html(self, viewer_id=None) -> Html:
        return Html(*[slot.html(viewer_id=viewer_id) for slot in self.slots.values()])

    # Dict interface methods - the most basic ones
    def __setitem__(self, __key: Key, __value: T):
        if __key in self.slots:
            slot = self.slots[__key]
        else:
            slot = self.slot_constructor(id=str(__key), parent=self)
            self.slots[__key] = slot
            try:
                self.get_game().log_new_slot(self, slot)
            except Component.NotAttachedToComponentTree:
                pass
        slot.set(__value)

    def __delitem__(self, __key: Key):
        del self.slots[__key]
        try:
            self.get_game().log_delete_slot(self, __key)
        except Component.NotAttachedToComponentTree:
            pass

    def __getitem__(self, __key) -> T:
        return self.slots[__key].get()

    def __len__(self):
        return len(self.slots)

    def __iter__(self) -> Iterator[Key]:
        return iter(self.slots)
