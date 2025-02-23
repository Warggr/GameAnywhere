from abc import ABC, abstractmethod
from game_anywhere.ui import Html, HtmlElement, tag
from itertools import count
from typing import Optional, Type, Any, Iterator, Generic, TypeVar
from .utils import html as to_html, mask

ComponentId = str


# TODO find a better name
class ComponentOrGame(ABC):
    """
    We're creating a hierarchy with a Game at the top, which can contain multiple ComponentSlots.
    Each ComponentSlot can contain one Component. Components in turn can have multiple ComponentSlots.
    I.e. each Component has a ComponentSlot as a parent/slot, and each ComponentSlot has a ComponentOrGame as a parent.
    """
    def __init__(self):
        # TODO: a lot of subclasses don't need the slots dict - maybe this should be optional or a mixin
        self.slots: dict[str, "WeakComponentSlot"] = {}

    def add_slot(self, slot_name: str, slot: "WeakComponentSlot"):
        self.slots[slot_name] = slot
        try:
            self.get_game().log_new_slot(self, slot)
        except Component.NotAttachedToComponentTree:
            pass

    @abstractmethod
    def get_game(self) -> "Game": ...

    @abstractmethod
    def get_slot_address(self) -> str: ...

    @abstractmethod
    def can_be_seen_by_recursive(self, viewer_id) -> bool:
        """ Whether there's a component higher up in the component hierarchy that blocks visibility of this slot. """
        ...

    def html(self, viewer_id=None) -> Html:
        result = Html()
        for slotname, slot in self.get_slots():
            slot_html = slot.html(viewer_id=viewer_id)
            label = tag.label(slotname, **{ 'for': slot_html.attrs['id'] })
            result += label + slot_html
        return result

    def get_slots(self) -> Iterator[tuple[str, "WeakComponentSlot"]]:
        for slot_name, slot in self.slots.items():
            yield slot_name, slot


class Component(ComponentOrGame):
    class NotAttachedToComponentTree(Exception):
        pass

    def __init__(self):
        super().__init__()
        self.slot: Optional["ComponentSlot"] = None

    def get_game(self) -> "Game":
        if self.slot is None:
            raise Component.NotAttachedToComponentTree()
        return self.slot.parent.get_game()

    def get_slot_address(self):
        if self.slot is None:
            return "(detached)"
        return self.slot.get_address()

    def reveal(self, *args, **kwargs):
        self.slot.reveal(*args, **kwargs)

    def can_be_seen_by_recursive(self, viewer_id) -> bool:
        try:
            return self.slot.can_be_seen_by_recursive(viewer_id)
        except self.NotAttachedToComponentTree:
            raise AssertionError("This method should be called only on components on the tree")


""" Typically, ComponentTreeNodes are Components. But we also support raw values, e.g. booleans. """
ComponentTreeNode = Any
T = TypeVar("T", bound=ComponentTreeNode)


class WeakComponentSlot(Generic[T]):
    def __init__(
        self,
        id: str,
        parent: ComponentOrGame,
        content: Optional[T] = None,
        hidden: bool = False,
        owner_id: Optional[int] = None,
    ):
        self.id = id
        self.parent = parent
        self.hidden = hidden
        self.owner_id = owner_id
        self._content = None
        if content:
            self.set(content)

    def get_address(self):
        return self.parent.get_slot_address() + "/" + self.id

    def get_game(self) -> "Game":
        return self.parent.get_game()

    def get(self) -> T:
        return self._content

    def set(self, content: T):
        self._content = content
        if isinstance(content, Component):
            content.slot = self
        # Re-enforce owner ID inheritance
        if self.owner_id is not None:
            self.set_owner_id(self.owner_id)
        try:
            game = self.get_game()
        except Component.NotAttachedToComponentTree:
            # No need to update the clients then
            return
        game.log_component_update(self, content)

    def reveal(self, to: int|None = None):
        try:
            game = self.get_game()
        except Component.NotAttachedToComponentTree:
            return
        game.log_component_update(self, self.content, force_reveal=True, only_update=to)

    @property
    def content(self) -> T:
        return self.get()

    @content.setter
    def content(self, content: T):
        self.set(content)

    def take(self) -> T:
        result = self._content
        self.set(None)
        return result

    def empty(self) -> bool:
        return self._content is None

    def set_owner_id(self, owner_id: int):
        """ Owner IDs are inherited down the component tree by default, so this is a recursive method """
        self.owner_id = owner_id
        if type(self._content) is Component:
            for child in self._content.get_slots():
                child.set_owner_id(owner_id)

    def can_be_seen_by(self, viewer_id=None):
        return not self.hidden or viewer_id == self.owner_id

    def can_be_seen_by_recursive(self, viewer_id=None) -> bool:
        """ Whether there's a component higher up in the component hierarchy that blocks visibility of this slot. """
        return self.can_be_seen_by(viewer_id) and self.parent.can_be_seen_by_recursive(viewer_id)

    def html(self, viewer_id=None, force_reveal=False) -> HtmlElement:
        if self.can_be_seen_by(viewer_id) or force_reveal:
            html = to_html(self._content, viewer_id=viewer_id)
        else:
            html = mask(self._content)
        html = Html(html).wrap_to_one_element()
        html.attrs["id"] = self.get_address()
        return html

    def __str__(self):
        return 'slot[' + (str(self._content) if self._content is not None else '(empty)') + ']'


class Pointer(WeakComponentSlot):
    pass


class ComponentSlot(WeakComponentSlot):
    def set(self, content: ComponentTreeNode):
        super().set(content)
        if isinstance(content, Component):
            content.slot = self


class ComponentSlotProperty(Generic[T]):
    _next_id = count()
    components: dict[ComponentId, "ComponentSlotProperty"] = {}

    def __init__(self, id: Optional[ComponentId] = None, slotType: type[WeakComponentSlot]=ComponentSlot, *args, **kwargs):
        if id is None:
            while (
                id := hex(next(ComponentSlotProperty._next_id))[2:]
            ) in ComponentSlotProperty.components:
                pass
        else:
            assert id not in ComponentSlotProperty.components
        self.id = id
        ComponentSlotProperty.components[id] = self

        self.SlotType = slotType
        self.args = args
        self.kwargs = kwargs

    def __set_name__(self, owner: Type[ComponentOrGame], name):
        self.private_name = "_" + name

    def __get__(self, obj: ComponentOrGame, objtype=None) -> T:
        if self.private_name not in obj.slots:
            slot = self.SlotType(self.id, obj, *self.args, **self.kwargs)
            obj.add_slot(self.private_name, slot)
        return obj.slots[self.private_name].get()

    def __set__(self, obj: ComponentOrGame, value: T):
        if self.private_name not in obj.slots:
            kwargs = self.kwargs.copy()
            if 'owner_id' not in self.kwargs and isinstance(obj, Component) and obj.slot is not None:
                kwargs['owner_id'] = obj.slot.owner_id
            slot = self.SlotType(self.id, obj, *self.args, **kwargs)
            obj.add_slot(self.private_name, slot)
            slot.set(value) # First set and register the slot, then fill it.
            # Otherwise, it will log its update as soon as it is filled, and the clients will get confused
        else:
            obj.slots[self.private_name].set(value)
        if isinstance(value, Component) and self.SlotType == ComponentSlot:
            assert value.slot == obj.slots[self.private_name]


class PerPlayerComponent(Component):
    """
    PerPlayer(
        **kwargs
    )
    is a shorthand for
    ComponentSlot(component=List(
        Component( **kwargs ),
        Component( **kwargs ),
        ...
    ))
    """

    def __init__(self, owner: "AgentDescriptor", owner_id: "AgentId", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.owner_id = owner_id
    def __str__(self):
        return f'Board of player {self.owner.name or "(not connected)"}'
    def html(self, viewer_id=None) -> Html:
        html = super().html(viewer_id)
        owner = self.owner.name or "(not connected)"
        if self.owner_id == viewer_id:
            owner += ' (you)'
        return tag.h2(owner) + html


class PerPlayer(ComponentSlotProperty):
    """
    Usage: use this as an attribute of the class
    then before you use this, you need to write once
    ` game.attr = PerPlayer.INIT(agent_descriptors) `. Then you can do e.g. game.attr[0] = ...
    """

    class INIT:
        # A sentinel value with some content. TODO: this is ugly.
        # A prettier syntax would be `game.attr.INIT(descriptors)`, but this is not possible
        # as game.attr calls __get__ and returns the property
        def __init__(self, agent_descriptors: list["AgentDescriptor"]):
            self.agent_descriptors = agent_descriptors

    def __init__(
        self,
        componentClass: type[PerPlayerComponent] | None = None,
        /,
        id: Optional[ComponentId] = None,
        **kwargs,
    ):
        super().__init__(id)
        if componentClass is None:
            componentClass = type.__new__(
                type,
                "PerPlayerComponent[" + ",".join(kwargs.keys()) + "]",
                (PerPlayerComponent,),
                kwargs,
            )
        else:
            assert len(kwargs) == 0, (
                "Keyword arguments "
                + ", ".join(kwargs.keys())
                + " ignored when componentClass is provided"
            )
        self.componentClass = componentClass

    def __set__(self, obj: "Game", value: any):
        # TODO: we might attach PerPlayers to something else than the top-level Game
        if type(value) is PerPlayer.INIT:
            from .containers import List

            per_player = [self.componentClass(owner=agent, owner_id=i) for i, agent in enumerate(value.agent_descriptors)]
            for_all_players = List(per_player)
            for agent_id, slot in enumerate(for_all_players.slots):
                slot.set_owner_id(agent_id)
            slot = ComponentSlot(self.id, obj)
            obj.add_slot(self.private_name, slot)
            # Fill the slot only after it is registered. See ComponentSlotProperty for explanation
            slot.set(for_all_players)
        else:
            obj.slots[self.private_name].set(value)
            assert value.slot == obj.slots[self.private_name]
