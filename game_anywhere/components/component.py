from abc import ABC, abstractmethod
from game_anywhere.ui import Html, tag
from itertools import count
from typing import Optional, Type, Any
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
        result = Html()
        # TODO: it would be more efficient if games provided a list of their slots themselves
        for attrname, attr in self.__dict__.items():
            if attrname == "slot":
                continue
            # print("Checking attr", attrname, end='...')
            if isinstance(attr, ComponentSlot):
                #print('A ComponentSlot with html', attr.html())
                result += attr.html(viewer_id=viewer_id)
            else:
                pass #print('Not a slot')
        return result


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
        return self.slot.get_address()

    def reveal(self, *args, **kwargs):
        self.slot.reveal(*args, **kwargs)

ComponentTreeNode = any


class ComponentSlot:
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
        self._content = content
        if isinstance(content, Component):
            content.slot = self

    def get_address(self):
        return self.parent.get_slot_address() + "/" + self.id

    def get_game(self) -> "Game":
        return self.parent.get_game()

    def get(self):
        return self._content

    def set(self, content: any):
        self._content = content
        if isinstance(content, Component):
            content.slot = self
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

    def html(self, viewer_id=None) -> Html:
        if self.hidden and viewer_id != self.owner_id:
            html = mask(self._content)
        else:
            html = to_html(self._content, viewer_id=viewer_id)
        html = Html(html).wrap_to_one_element()
        html.attrs["id"] = self.get_address()
        return html


class ComponentSlotProperty:
    _next_id = count()
    components: dict[ComponentId, "Component"] = {}

    def __init__(self, id: Optional[ComponentId] = None):
        if id is None:
            while (
                id := hex(next(ComponentSlotProperty._next_id))[2:]
            ) in ComponentSlotProperty.components:
                pass
        else:
            assert id not in ComponentSlotProperty.components
        self.id = id
        ComponentSlotProperty.components[id] = self


    def __set_name__(self, owner: Type[ComponentOrGame], name):
        self.private_name = "_" + name

    def __get__(self, obj: ComponentOrGame, objtype=None):
        return getattr(obj, self.private_name).get()

    def __set__(self, obj: ComponentOrGame, value: any):
        if not hasattr(obj, self.private_name):
            setattr(
                obj,
                self.private_name,
                ComponentSlot(self.id, obj, value),
            )
        else:
            getattr(obj, self.private_name).set(value)
        if isinstance(value, Component):
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
        self.owner_id = owner_id
    def __str__(self):
        return f'Board of player {self.owner.name}'
    def html(self, viewer_id=None) -> Html:
        print(f'return HTML with {viewer_id=}')
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

    def __init__(self, id : Optional[ComponentId] = None, **kwargs):
        super().__init__(id)
        self.ComponentClass = type.__new__(type, 'PerPlayerComponent(' + ','.join(kwargs.keys()) + ')', (Component,), kwargs)

    def __set__(self, obj: "Game", value: any):
        if value is PerPlayer.INIT:
            from .list import List

            per_player = [self.componentClass(owner=agent, owner_id=i) for i, agent in enumerate(obj.agents)]
            for_all_players = List(per_player)
            for agent_id, slot in enumerate(for_all_players.slots):
                slot.owner_id = agent_id
            slot = ComponentSlot(self.id, obj, for_all_players)
            setattr(obj, self.private_name, slot)
        else:
            getattr(obj, self.private_name).set(value)
            assert value.slot == getattr(obj, self.private_name)
