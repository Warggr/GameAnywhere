from abc import ABC, abstractmethod
from game_anywhere.ui import Html, HtmlElement, tag
from itertools import count
from typing import Optional, Type, Any, Generator
from .utils import html as to_html, mask

ComponentId = str


# TODO find a better name
class ComponentOrGame(ABC):
    """
    We're creating a hierarchy with a Game at the top, which can contain multiple ComponentSlots.
    Each ComponentSlot can contain one Component. Components in turn can have multiple ComponentSlots.
    I.e. each Component has a ComponentSlot as a parent/slot, and each ComponentSlot has a ComponentOrGame as a parent.
    """

    @abstractmethod
    def get_game(self) -> "Game": ...

    @abstractmethod
    def get_slot_address(self) -> str: ...

    def html(self, viewer_id=None) -> Html:
        print(f'Getting html for {self} with {viewer_id=}')
        result = Html()
        for slotname, slot in self._slots():
            result += slot.html(viewer_id=viewer_id)
        return result

    # TODO: it would be more efficient if games provided a list of their slots themselves
    def _slots(self) -> Generator[tuple[str, "ComponentSlot"]]:
        for attrname, attr in self.__dict__.items():
            if attrname == "slot":
                continue
            if isinstance(attr, ComponentSlot):
                yield attrname, attr

class Component(ComponentOrGame):
    class NotAttachedToComponentTree(Exception):
        pass

    def __init__(self):
        self.slot: Optional["ComponentSlot"] = None

    def get_game(self):
        if self.slot is None:
            raise Component.NotAttachedToComponentTree()
        return self.slot.parent.get_game()

    def get_slot_address(self):
        if self.slot is None:
            return "(detached)"
        return self.slot.get_address()

    def reveal(self, *args, **kwargs):
        self.slot.reveal(*args, **kwargs)


""" Typically, ComponentTreeNodes are Components. But we also support raw values, e.g. booleans. """
ComponentTreeNode = Any


class WeakComponentSlot:
    def __init__(
        self,
        id: str,
        parent: ComponentOrGame,
        content: Optional[ComponentTreeNode] = None,
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

    def get(self):
        return self._content

    def set(self, content: ComponentTreeNode):
        self._content = content
        if isinstance(content, Component):
            content.slot = self
        # Re-enforce owner ID inheritance
        if self.owner_id is not None:
            self.set_owner_id(self.owner_id)
        try:
            game = self.get_game()
            game.log_component_update(
                self.get_address(),
                {"new_value": content},
                hidden=self.hidden,
                owner_id=self.owner_id,
            )
        except Component.NotAttachedToComponentTree:
            # No need to update the clients then
            pass

    def reveal(self, to: int|None = None):
        try:
            game = self.get_game()
        except Component.NotAttachedToComponentTree:
            return
        if to is not None:
            game.log_component_update(self.get_address(), {"new_value": self._content}, hidden=True, owner_id=to)
        else:
            game.log_component_update(self.get_address(), {"new_value": self._content}, hidden=False)

    @property
    def content(self):
        return self.get()

    @content.setter
    def content(self, content: ComponentTreeNode):
        self.set(content)

    def empty(self) -> bool:
        return self._content is None

    def set_owner_id(self, owner_id: int):
        """ Owner IDs are inherited down the component tree by default, so this is a recursive method """
        self.owner_id = owner_id
        if type(self._content) is Component:
            for child in self._content._slots():
                child.set_owner_id(owner_id)

    def can_be_seen_by(self, viewer_id=None):
        return not self.hidden or viewer_id == self.owner_id

    def html(self, viewer_id=None) -> HtmlElement:
        if self.can_be_seen_by(viewer_id):
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


class ComponentSlotProperty:
    _next_id = count()
    components: dict[ComponentId, Component] = {}

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

    def __get__(self, obj: ComponentOrGame, objtype=None):
        if not hasattr(obj, self.private_name):
            setattr(obj, self.private_name, self.SlotType(self.id, obj, *self.args, **self.kwargs))
        return getattr(obj, self.private_name).get()

    def __set__(self, obj: ComponentOrGame, value: any):
        if not hasattr(obj, self.private_name):
            kwargs = self.kwargs
            if 'owner_id' not in self.kwargs and isinstance(obj, Component):
                kwargs['owner_id'] = obj.slot.owner_id
            slot = self.SlotType(self.id, obj, value, *self.args, **kwargs)
            setattr(obj, self.private_name, slot)
            try:
                obj.get_game().log_component_update(obj.get_slot_address(), {"append": slot})
            except Component.NotAttachedToComponentTree:
                pass
        else:
            getattr(obj, self.private_name).set(value)
        if isinstance(value, Component) and self.SlotType == ComponentSlot:
            assert value.slot == getattr(obj, self.private_name)


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

    def __init__(self, owner: "Agent", owner_id: "AgentId", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        assert self.owner is not None
        self.owner_id = owner_id
    def __str__(self):
        return f'Board of player {self.owner.name}'
    def html(self, viewer_id=None) -> Html:
        html = super().html(viewer_id)
        owner = self.owner.name
        if self.owner_id == viewer_id:
            owner += ' (you)'
        return tag.h2(owner) + html


class PerPlayer(ComponentSlotProperty):
    """
    Usage: use this as an attribute of the class
    then before you use this, you need to write once
    ` game.attr = PerPlayer.INIT `. Then you can do e.g. game.attr[0] = ...
    """

    class INIT:
        pass  # Sentinel value

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
        if value is PerPlayer.INIT:
            from .list import List

            per_player = [self.componentClass(owner=agent, owner_id=i) for i, agent in enumerate(obj.agents)]
            for_all_players = List(per_player)
            for agent_id, slot in enumerate(for_all_players.slots):
                slot.set_owner_id(agent_id)
            slot = ComponentSlot(self.id, obj, for_all_players)
            setattr(obj, self.private_name, slot)
            # Notify the client that we just created another slot.
            obj.log_component_update("screen", {"append": slot})
        else:
            getattr(obj, self.private_name).set(value)
            assert value.slot == getattr(obj, self.private_name)
