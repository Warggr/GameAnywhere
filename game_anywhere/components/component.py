from abc import ABC, abstractmethod
from itertools import count
from typing import TYPE_CHECKING, Any, Generic, Mapping, Optional, Type, TypeVar

from game_anywhere.ui.ui import Html, HtmlElement, tag

from .utils import html as to_html
from .utils import mask

if TYPE_CHECKING:
    from game_anywhere.agents.descriptors import AgentDescriptor
    from game_anywhere.core import Agent, Game
    from game_anywhere.core.agent import AgentId

    from .containers import List

ComponentId = str


class ComponentOrGame(ABC):
    """We're creating a hierarchy with a Game at the top, which can contain multiple ComponentSlots.
    Each ComponentSlot can contain one Component. Components in turn can have multiple ComponentSlots.
    I.e. each Component has a ComponentSlot as a parent/slot, and each ComponentSlot has a ComponentOrGame as a parent.
    """

    @abstractmethod
    def get_slots(self) -> Mapping[str, "WeakComponentSlot"]:
        """Return a list of slots with names."""
        ...

    def log_added_slot(self, slot: "WeakComponentSlot"):
        try:
            self.get_game().log_new_slot(self, slot)
        except Component.NotAttachedToComponentTree:
            pass

    def log_deleted_slot(self, slot_name: str):
        try:
            self.get_game().log_delete_slot(self, slot_name)
        except Component.NotAttachedToComponentTree:
            pass

    @abstractmethod
    def get_game(self) -> "Game": ...

    @abstractmethod
    def get_slot_address(self) -> str: ...

    def _lookup_slot_nonrecursive(self, slot_id: str) -> "WeakComponentSlot":
        """Overridden by subclasses"""
        slots = [slot for slot in self.slots.values() if slot.slot_id == slot_id]
        if len(slots) == 0:
            raise KeyError(slot_id)
        elif len(slots) >= 2:
            raise AssertionError("Multiple slots with ID " + slot_id)
        return slots[0]

    def lookup_slot_address(self, address: str) -> "WeakComponentSlot":
        address = address.split("/", maxsplit=1)
        match address:
            case toplevel, relative:
                return (
                    self._lookup_slot_nonrecursive(toplevel)
                    .get()
                    .lookup_slot_address(relative)
                )
            case toplevel:
                return self._lookup_slot_nonrecursive(toplevel)

    @abstractmethod
    def can_be_seen_by_recursive(self, viewer_id) -> bool:
        """Whether there's a component higher up in the component hierarchy that blocks visibility of this slot."""
        ...

    def html(self, viewer_id=None) -> Any:
        result = Html()
        for slotname, slot in self.get_slots().items():
            slot_html = slot.html(viewer_id=viewer_id)
            label = tag.label(slotname, **{"for": slot_html.attrs["id"]})
            result += label + slot_html
        return result


class PropertySlotMixin(ComponentOrGame):
    def __init__(self):
        self.slots: dict[str, "WeakComponentSlot"] = {}

    def add_slot(self, slot_name: str, slot: "WeakComponentSlot"):
        self.slots[slot_name] = slot
        self.log_added_slot(slot)

    def remove_slot(self, slot_name: str):
        del self.slots[slot_name]
        self.log_deleted_slot(slot_name)

    def get_slots(self) -> Mapping[str, "WeakComponentSlot"]:
        return self.slots


class AbstractComponent(ComponentOrGame):
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
        except self.NotAttachedToComponentTree as err:
            raise AssertionError(
                "This method should be called only on components on the tree"
            ) from err


class Component(AbstractComponent, PropertySlotMixin):
    pass


""" Typically, ComponentTreeNodes are Components. But we also support raw values, e.g. booleans. """
ComponentTreeNode = Any
T = TypeVar("T", bound=ComponentTreeNode)


class WeakComponentSlot(Generic[T]):
    def __init__(
        self,
        id_: str,
        parent: ComponentOrGame,
        content: Optional[T] = None,
        hidden: bool = False,
        owner_id: Optional[int] = None,
    ):
        self.id = id_
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
        if isinstance(content, AbstractComponent):
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

    def reveal(self, to: int | None = None):
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
        """Owner IDs are inherited down the component tree by default, so this is a recursive method"""
        self.owner_id = owner_id
        if type(self._content) is Component:
            for child in self._content.get_slots().values():
                child.set_owner_id(owner_id)

    def can_be_seen_by(self, viewer_id=None):
        return not self.hidden or viewer_id == self.owner_id

    def can_be_seen_by_recursive(self, viewer_id=None) -> bool:
        """Whether there's a component higher up in the component hierarchy that blocks visibility of this slot."""
        return self.can_be_seen_by(viewer_id) and self.parent.can_be_seen_by_recursive(
            viewer_id
        )

    def html(self, viewer_id=None, force_reveal=False) -> HtmlElement:
        if self.can_be_seen_by(viewer_id) or force_reveal:
            html = to_html(self._content, viewer_id=viewer_id)
        else:
            html = mask(self._content)
        html = Html(html).wrap_to_one_element()
        html.attrs["id"] = self.get_address()
        return html

    def __str__(self):
        return (
            "slot["
            + (str(self._content) if self._content is not None else "(empty)")
            + "]"
        )


class Pointer(WeakComponentSlot):
    pass


class ComponentSlot(WeakComponentSlot):
    def set(self, content: ComponentTreeNode):
        super().set(content)
        if isinstance(content, AbstractComponent):
            content.slot = self


class ComponentSlotProperty(Generic[T]):
    _next_id = count()
    components: dict[ComponentId, "ComponentSlotProperty"] = {}

    def __init__(
        self,
        id_: Optional[ComponentId] = None,
        slotType: type[WeakComponentSlot] = ComponentSlot,
        *args,
        **kwargs,
    ):
        if id_ is None:
            while (
                id_ := hex(next(ComponentSlotProperty._next_id))[2:]
            ) in ComponentSlotProperty.components:
                pass
        else:
            assert id_ not in ComponentSlotProperty.components
        self.id = id_
        ComponentSlotProperty.components[id_] = self

        self.SlotType = slotType
        self.args = args
        self.kwargs = kwargs

    def __set_name__(self, owner: Type[PropertySlotMixin], name):
        assert issubclass(owner, PropertySlotMixin), (
            "The ComponentSlotProperty short-hand only works on PropertySlotMixin"
        )
        self.private_name = "_" + name

    def __get__(self, obj: PropertySlotMixin, objtype=None) -> T:
        if self.private_name not in obj.slots:
            slot = self.SlotType(self.id, obj, *self.args, **self.kwargs)
            obj.add_slot(self.private_name, slot)
        return obj.slots[self.private_name].get()

    def __set__(self, obj: PropertySlotMixin, value: T):
        if self.private_name not in obj.slots:
            kwargs = self.kwargs.copy()
            if (
                "owner_id" not in self.kwargs
                and isinstance(obj, AbstractComponent)
                and obj.slot is not None
            ):
                kwargs["owner_id"] = obj.slot.owner_id
            slot = self.SlotType(self.id, obj, *self.args, **kwargs)
            obj.add_slot(self.private_name, slot)
            slot.set(value)  # First set and register the slot, then fill it.
            # Otherwise, it will log its update as soon as it is filled, and the clients will get confused
        else:
            obj.slots[self.private_name].set(value)
        if isinstance(value, AbstractComponent) and self.SlotType == ComponentSlot:
            assert value.slot == obj.slots[self.private_name]


class PerPlayerComponent(Component):
    def __init__(self, owner: "AgentDescriptor", owner_id: "AgentId", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.owner_id = owner_id

    def __str__(self):
        return f"Board of player {self.owner.name or '(not connected)'}"

    def html(self, viewer_id=None) -> Html:
        html = super().html(viewer_id)
        owner = self.owner.name or "(not connected)"
        if self.owner_id == viewer_id:
            owner += " (you)"
        return tag.h2(owner) + html

    def get_owner(self) -> "Agent":
        return self.get_game().agents[self.owner_id]


PerPlayerComponentType = TypeVar("PerPlayerComponentType", bound=PerPlayerComponent)


class PerPlayer(
    ComponentSlotProperty["List[PerPlayerComponentType]"],
    Generic[PerPlayerComponentType],
):
    """PerPlayer(
        **kwargs
    )
    is a shorthand for
    ComponentSlot(component=List(
        Component( **kwargs ),
        Component( **kwargs ),
        ...
    ))
    """

    def __init__(
        self,
        componentClass: type[PerPlayerComponent] | None = None,
        /,
        id_: Optional[ComponentId] = None,
        **kwargs,
    ):
        super().__init__(id_)
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

    def __get__(
        self, obj: PropertySlotMixin, objtype=None
    ) -> "List[PerPlayerComponentType]":
        if self.private_name not in obj.slots:
            from .containers import List

            per_player = [self.componentClass(owner=agent, owner_id=i) for i, agent in enumerate(obj.get_game().agent_descriptions)]
            for_all_players = List(per_player)
            for agent_id, slot in enumerate(for_all_players.slots):
                slot.set_owner_id(agent_id)
            slot = ComponentSlot(self.id, obj)
            obj.add_slot(self.private_name, slot)
            # Fill the slot only after it is registered. See ComponentSlotProperty for explanation
            slot.set(for_all_players)
        else:
            slot = obj.slots[self.private_name]
        return slot.get()

    def __set__(self, obj: PropertySlotMixin, value: Any):
        raise NotImplementedError("Cannot set a PerPlayer")
