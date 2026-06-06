from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from game_anywhere.ui.ui import Html, tag

from .utils import html as to_html
from .utils import merge_classes

if TYPE_CHECKING:
    from typing import Mapping, Optional, Sequence

    from game_anywhere.agents.descriptors import AgentDescriptor
    from game_anywhere.core import Agent, AgentId, Game
    from game_anywhere.ui.display_styles import DisplayStyle

    from .containers import List

ComponentId = str


class AbstractComponent(ABC):
    """We're creating a hierarchy with a Game at the top, which can contain multiple ComponentSlots.
    Each ComponentSlot can contain one Component. Components in turn can have multiple ComponentSlots.
    I.e. each Component has a ComponentSlot as a parent/slot, and each ComponentSlot has a ComponentOrGame as a parent.
    """

    class NotAttachedToComponentTree(Exception):
        pass

    def __init__(self):
        super().__init__()
        self.slot: Optional["ComponentSlot"] = None

    def get_game(self) -> "Game":
        """Overridden by Game."""
        if self.slot is None:
            raise self.NotAttachedToComponentTree()
        return self.slot.parent.get_game()

    def get_address(self):
        if self.slot is None:
            return "(detached)"
        return self.slot.get_address()

    def reveal(self, *args, **kwargs):
        self.slot.reveal(*args, **kwargs)

    def can_be_seen_by_recursive(self, viewer_id) -> bool:
        """Whether there's a component higher up in the component hierarchy that blocks visibility of this slot."""
        try:
            return self.slot.can_be_seen_by_recursive(viewer_id)
        except self.NotAttachedToComponentTree as err:
            raise AssertionError(
                "This method should be called only on components on the tree"
            ) from err

    @abstractmethod
    def html(self, viewer_id: AgentId | None = None) -> Any: ...


KeyType = TypeVar("KeyType")


class AbstractComposite(AbstractComponent, Generic[KeyType]):
    @abstractmethod
    def get_slots(self) -> Mapping[KeyType, "WeakComponentSlot"]:
        """Return a list of slots with names."""
        ...

    def log_added_slot(self, slot_name: KeyType, slot: "WeakComponentSlot"):
        try:
            self.get_game().log_new_slot(self, slot_name, slot)
        except self.NotAttachedToComponentTree:
            pass

    def log_deleted_slot(self, slot_name: KeyType):
        try:
            self.get_game().log_delete_slot(self, slot_name)
        except self.NotAttachedToComponentTree:
            pass

    def wrap_slot_html(
        self, slot_html: Any, key: KeyType, is_visible: bool = True
    ) -> Any:
        slot_html = Html(slot_html).wrap_to_one_element()
        slot_html.attrs["data-key"] = key
        slot_html.add_classes(
            "ga-slot",
        )
        slot_html.add_classes("ga-slot--visible" if is_visible else "ga-slot--hidden")
        return slot_html

    def merge_slot_html(self, items: list[Any]) -> Any:
        """
        The direct parent of each item must have the `ga-composite` class in order to be able to receive more slots.
        """
        raise NotImplementedError(
            f"class {type(self)} neither implements merge_slot_html nor html"
        )

    def html(self, viewer_id: AgentId | None = None) -> Any:
        fields = []
        for slotname, slot in self.get_slots().items():
            # No display logic can be added here because it is not contained in the incremental patches.
            slot_html = slot.html(viewer_id=viewer_id)
            is_visible = slot.can_be_seen_by(viewer_id)
            slot_html = self.wrap_slot_html(slot_html, slotname, is_visible=is_visible)
            fields.append(slot_html)

        return self.merge_slot_html(fields)


class Composite(AbstractComposite[str]):
    def __init__(self):
        super().__init__()
        self.slots: dict[str, "WeakComponentSlot"] = {}

    def add_slot(self, slot_name: str, slot: "WeakComponentSlot"):
        self.slots[slot_name] = slot
        self.log_added_slot(slot_name, slot)

    def remove_slot(self, slot_name: str):
        del self.slots[slot_name]
        self.log_deleted_slot(slot_name)

    def get_slots(self) -> Mapping[str, "WeakComponentSlot"]:
        return self.slots

    def wrap_slot_html(self, slot_html: Any, key: str, is_visible: bool = True) -> Html:
        slot_html = Html(slot_html).wrap_to_one_element()
        slot_html.add_classes("ga-field-value")
        slot_html = tag.div(
            tag.label(
                self._display_slot_name(key),
                **{
                    "class": "ga-field-label",
                },
            ),
            slot_html,
            **{"class": "ga-field"},
        )
        return super().wrap_slot_html(slot_html, key, is_visible=is_visible)

    def merge_slot_html(self, items: Sequence[Html]) -> Html:
        return tag.div(*items, **{"class": "ga-composite"})

    @staticmethod
    def _display_slot_name(slot_name: str) -> str:
        if slot_name.startswith("_"):
            slot_name = slot_name.removeprefix("_")
        return slot_name.replace("_", " ").strip().title()


class Component(AbstractComponent):
    pass


""" Typically, ComponentTreeNodes are Components. But we also support raw values, e.g. booleans. """
ComponentTreeNode = Any
T = TypeVar("T", bound=ComponentTreeNode)


class WeakComponentSlot(Generic[T]):
    def __init__(
        self,
        id_: Any,
        parent: AbstractComposite,
        content: Optional[T] = None,
        *,
        hidden: bool = False,
        owner_id: Optional[int] = None,
        display_as: DisplayStyle | None = None,
    ):
        self.id = id_
        self.parent = parent
        self.hidden = hidden
        self.owner_id = owner_id
        self._content = None
        self.display_as = display_as
        if content:
            self.set(content)

    def get_address(self):
        return self.parent.get_address() + "/" + str(self.id)

    def get_game(self) -> "Game":
        return self.parent.get_game()

    def get(self) -> T | None:
        return self._content

    def set(self, content: T | None):
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
        game.log_component_update(self)

    def reveal(self, to: int | None = None):
        try:
            game = self.get_game()
        except AbstractComponent.NotAttachedToComponentTree:
            return
        game.log_component_update(self, force_reveal=True, only_update=to)

    @property
    def content(self) -> T | None:
        return self.get()

    @content.setter
    def content(self, content: T):
        self.set(content)

    def take(self) -> T | None:
        result = self._content
        self.set(None)
        return result

    def empty(self) -> bool:
        return self._content is None

    def set_owner_id(self, owner_id: int):
        """Owner IDs are inherited down the component tree by default, so this is a recursive method"""
        self.owner_id = owner_id
        if isinstance(self._content, AbstractComposite):
            for child in self._content.get_slots().values():
                child.set_owner_id(owner_id)

    def can_be_seen_by(self, viewer_id=None):
        return not self.hidden or (viewer_id is not None and viewer_id == self.owner_id)

    def can_be_seen_by_recursive(self, viewer_id=None) -> bool:
        """Whether there's a component higher up in the component hierarchy that blocks visibility of this slot."""
        return self.can_be_seen_by(viewer_id) and self.parent.can_be_seen_by_recursive(
            viewer_id
        )

    def html(
        self,
        viewer_id=None,
        force_reveal=False,
    ) -> Html:
        is_visible = self.can_be_seen_by(viewer_id) or force_reveal
        if self._content is None:
            html = Html()
        elif self.display_as is None:
            html = to_html(self._content, viewer_id=viewer_id, visible=is_visible)
        else:
            html = self.display_as(
                self._content, viewer_id=viewer_id, visible=is_visible
            )
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
    def __init__(
        self,
        slotType: type[WeakComponentSlot] = ComponentSlot,
        *args,
        **kwargs,
    ):
        self.SlotType = slotType
        self.args = args
        self.kwargs = kwargs

    def __set_name__(self, owner: type[Composite], name):
        assert issubclass(owner, Composite), (
            "The ComponentSlotProperty short-hand only works on Composite"
        )
        self.private_name = name

    def __get__(self, obj: Composite, objtype=None) -> T:
        if self.private_name not in obj.slots:
            slot = self.SlotType(self.private_name, obj, *self.args, **self.kwargs)
            obj.add_slot(self.private_name, slot)
        return obj.slots[self.private_name].get()

    def __set__(self, obj: Composite, value: T):
        if self.private_name not in obj.slots:
            kwargs = self.kwargs.copy()
            if (
                "owner_id" not in self.kwargs
                and isinstance(obj, AbstractComponent)
                and hasattr(obj, "slot")  # filters out Game
                and obj.slot is not None
            ):
                kwargs["owner_id"] = obj.slot.owner_id
            slot = self.SlotType(self.private_name, obj, *self.args, **kwargs)
            obj.add_slot(self.private_name, slot)
            slot.set(value)  # First set and register the slot, then fill it.
            # Otherwise, it will log its update as soon as it is filled, and the clients will get confused
        else:
            obj.slots[self.private_name].set(value)
        if isinstance(value, AbstractComponent) and self.SlotType == ComponentSlot:
            assert value.slot == obj.slots[self.private_name]


class PerPlayerComponent(Composite):
    def __init__(self, owner: "AgentDescriptor", owner_id: "AgentId", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.owner_id = owner_id

    def __str__(self):
        return f"Board of player {self.owner.name or '(not connected)'}"

    def html(self, viewer_id=None) -> Html:
        html = super().html(viewer_id)
        owner = self.owner.name or "(not connected)"
        badge = None
        if self.owner_id == viewer_id:
            badge = tag.span("You", **{"class": "ga-player-badge"})
        return tag.section(
            tag.div(
                tag.div(owner, **{"class": "ga-player-name"}),
                badge if badge is not None else "",
                **{"class": "ga-player-header"},
            ),
            tag.div(html, **{"class": "ga-player-body"}),
            **{
                "class": merge_classes(
                    "ga-player-panel",
                    "ga-player-panel--self"
                    if self.owner_id == viewer_id
                    else "ga-player-panel--other",
                )
            },
        )

    def get_owner(self) -> "Agent":
        return self.get_game().agents[self.owner_id - 1]


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
        componentClass: type[PerPlayerComponentType] | None = None,
        /,
        **kwargs,
    ):
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

    def __get__(self, obj: Composite, objtype=None) -> "List[PerPlayerComponentType]":
        if self.private_name not in obj.slots:
            from .containers import List

            game = obj.get_game()
            per_player = [
                self.componentClass(owner=agent, owner_id=agent_id)
                for agent, agent_id in zip(game.agents, game.agent_ids, strict=True)
            ]
            for_all_players = List(per_player)
            for agent_id, slot in zip(
                game.agent_ids, for_all_players.slots, strict=True
            ):
                slot.set_owner_id(agent_id)
            slot = ComponentSlot(self.private_name, obj)
            obj.add_slot(self.private_name, slot)
            # Fill the slot only after it is registered. See ComponentSlotProperty for explanation
            slot.set(for_all_players)
        else:
            slot = obj.slots[self.private_name]
        return slot.get()

    def __set__(self, obj: Composite, value: Any):
        raise NotImplementedError("Cannot set a PerPlayer")
