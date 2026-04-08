from typing import (
    Generic,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    TypeVar,
)

from game_anywhere.ui import Html

from .component import AbstractComponent, ComponentSlot

T = TypeVar("T", bound=AbstractComponent)


class List(AbstractComponent, Generic[T], MutableSequence[T]):
    def __init__(self, args, slotClass: type[ComponentSlot] = ComponentSlot, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        slots = [
            slotClass(id_=str(i), content=component, parent=self, **self.kwargs)
            for i, component in enumerate(args)
        ]
        self.slots = slots

    # Component interface methods
    def get_slots(self) -> Mapping[str, "ComponentSlot"]:
        return dict((f"@[{i}]", slot) for i, slot in enumerate(self.slots))

    def html(self, viewer_id=None) -> Html:
        return Html(*[slot.html(viewer_id=viewer_id) for slot in self.slots])

    # list interface methods - the most basic ones

    def insert(self, index, value):
        raise NotImplementedError()

    def append(self, value: T):
        slot = ComponentSlot(id_=str(len(self.slots)), parent=self, **self.kwargs)
        self.slots.append(slot)
        self.log_added_slot(slot)
        # set slot content separately, so that the slot can decide itself how it wants to log the update event (and take e.g. the hidden flag into account).
        # TODO: there might be a cleaner way of doing this
        slot.set(value)

    def __getitem__(self, index) -> T:
        return self.slots[index].get()

    def __setitem__(self, index, value):
        self.slots[index].set(value)

    def __delitem__(self, index):
        del self.slots[index]
        self.log_deleted_slot(str(index))

    def __len__(self):
        return len(self.slots)

    # list interface methods - syntactic sugar

    def __iter__(self) -> Iterator[T]:
        # When iterating, we can't replace one value. So just dealing with components and ignoring slots is appropriate here
        return (slot._content for slot in self.slots)

    def __iadd__(self, other_list: Iterable[T]):
        for i in other_list:
            self.append(i)
        return self

    def extend(self, values: Iterable[T]):
        for i in values:
            self.append(i)

    # useful methods

    def __copy__(self):
        copy = type(self)()
        copy.__dict__.update(self.__dict__)
        copy.slot = None  # copy shouldn't be attached to the component tree
        return copy


Key = TypeVar("Key")


class Dict(AbstractComponent, Generic[Key, T], MutableMapping[Key, T]):
    def __init__(
        self,
        content: dict[Key, T] | None = None,
        slotClass: type[ComponentSlot] = ComponentSlot,
        **kwargs,
    ):
        super().__init__()
        if content is None:
            content = {}
        self.slot_constructor = lambda *args, **other_kwargs: slotClass(
            *args, **other_kwargs, **kwargs
        )
        slots = {
            key: self.slot_constructor(id=str(key), content=value, parent=self)
            for key, value in content.items()
        }
        self.slots: dict[Key, ComponentSlot] = slots

    # Component interface methods
    def get_slots(self) -> Mapping[str, ComponentSlot]:
        return self.slots

    def html(self, viewer_id=None) -> Html:
        return Html(*[slot.html(viewer_id=viewer_id) for slot in self.slots.values()])

    # Dict interface methods - the most basic ones
    def __setitem__(self, __key: Key, __value: T):
        if __key in self.slots:
            slot = self.slots[__key]
        else:
            slot = self.slot_constructor(id_=str(__key), parent=self)
            self.slots[__key] = slot
            self.log_added_slot(slot)
        slot.set(__value)

    def __delitem__(self, __key: Key):
        del self.slots[__key]
        self.log_deleted_slot(__key)

    def __getitem__(self, __key) -> T:
        return self.slots[__key].get()

    def __len__(self):
        return len(self.slots)

    def __iter__(self) -> Iterator[Key]:
        return iter(self.slots)
