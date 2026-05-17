from __future__ import annotations

from itertools import count
from typing import (
    Generic,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    TypeVar,
)

from game_anywhere.ui import Html, tag

from .component import AbstractComponent, AbstractComposite, ComponentSlot
from .utils import html as to_html
from .utils import merge_classes

T = TypeVar("T", bound=AbstractComponent)


class List(AbstractComposite, Generic[T], MutableSequence[T]):
    def __init__(
        self, args=(), *, slotClass: type[ComponentSlot] = ComponentSlot, **kwargs
    ):
        super().__init__()

        # The slot keys are not actually equal to the list indices,
        # instead each slot has a permanent identity that persists across list reorders.
        # This makes syncing more easy.
        self.slot_keys = count()

        def display_as_li(obj, viewer_id=None, visible=True):
            html = to_html(obj, viewer_id=viewer_id, visible=visible)
            html = tag.li(
                html,
                **{
                    "class": merge_classes(
                        "ga-slot",
                        "ga-slot--visible" if visible else "ga-slot--hidden",
                    )
                },
            )
            return html

        def _slot_constructor(**more_kwargs):
            obj = slotClass(
                id_=next(self.slot_keys), parent=self, **kwargs, **more_kwargs
            )
            obj.display_as = display_as_li
            return obj

        self.slot_constructor = _slot_constructor
        slots = [self.slot_constructor(content=component) for component in args]
        self.slots = slots

    # Component interface methods
    def get_slots(self) -> Mapping[int, "ComponentSlot"]:
        return dict((slot.id, slot) for slot in self.slots)

    def html(self, viewer_id=None) -> Html:
        items = [slot.html(viewer_id=viewer_id) for slot in self.slots]
        return tag.ul(*items)

    # list interface methods - the most basic ones

    def insert(self, index, value):
        raise NotImplementedError()

    def append(self, value: T):
        slot = self.slot_constructor()
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
        slot_id = self.slots[index].id
        del self.slots[index]
        self.log_deleted_slot(slot_id)

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
        copy.slots = self.slots[:]
        copy.slot_keys = count(max(int(slot.id) for slot in self.slots))
        copy.slot = None  # copy shouldn't be attached to the component tree
        return copy


Key = TypeVar("Key")


class Dict(AbstractComposite[Key], Generic[Key, T], MutableMapping[Key, T]):
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
    def get_slots(self) -> Mapping[Key, ComponentSlot]:
        return self.slots

    def html(self, viewer_id=None) -> Html:
        items = [
            tag.section(
                tag.div(str(key), **{"class": "ga-dict-key"}),
                tag.div(slot.html(viewer_id=viewer_id), **{"class": "ga-dict-value"}),
                **{"class": "ga-dict-entry"},
            )
            for key, slot in self.slots.items()
        ]
        return tag.div(*items, **{"class": "ga-dict"})

    # Dict interface methods - the most basic ones
    def __setitem__(self, __key: Key, __value: T):
        if __key in self.slots:
            slot = self.slots[__key]
        else:
            slot = self.slot_constructor(id_=__key, parent=self)
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
