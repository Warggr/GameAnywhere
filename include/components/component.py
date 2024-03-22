from abc import ABC, abstractmethod
from game_anywhere.include.ui import Html
from itertools import count
from typing import Optional, Dict, Type

ComponentId = str

# TODO find a better name
class ComponentOrGame(ABC):
    """
    We're creating a hierarchy with a Game at the top, which can contain multiple ComponentSlots.
    Each ComponentSlot can contain one Component. Components in turn can have multiple ComponentSlots.
    I.e. each Component has a ComponentSlot as a parent/slot, and each ComponentSlot has a ComponentOrGame as a parent.
    """

    @abstractmethod
    def get_game(self) -> 'Game':
        ...

    @abstractmethod
    def get_slot_address(self) -> str:
        ...

class Component(ABC):
    class NotAttachedToComponentTree(Exception):
        pass

    def __init__(self):
        self.slot : Optional['ComponentSlot'] = None

    def get_game(self):
        if self.slot is None:
            raise Component.NotAttachedToComponentTree()
        return self.slot.parent.get_game()

    def get_slot_address(self):
        return self.slot.get_address()

    @abstractmethod
    def html(self) -> Html:
        ...

class ComponentSlot:
    def __init__(self, id, parent : ComponentOrGame, content : Optional[Component] = None):
        self.id = id
        self.parent = parent
        self._content = content
        if content is not None:
            content.slot = self

    def get_address(self):
        return self.parent.get_slot_address() + '/' + self.id

    def get_game(self) -> 'Game':
        return self.parent.get_game()

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content : Component):
        # assert isinstance(content, Component), type(content).__mro__
        self._content = content
        if content is not None:
            content.slot = self
        try:
            game = self.get_game()
            game.log_component_update(self.get_address(), content)
        except Component.NotAttachedToComponentTree:
            # No need to update the clients then
            pass

    def empty(self) -> bool:
        return self._content is None

    def html(self) -> Html:
        if self._content is None:
            html = ''
        else:
            html = self._content.html()
        html = Html(html)
        if not isinstance(html, Html):
            html = Html(html)
        html = html.wrap_to_one_element()
        html.attrs['id'] = self.get_address()
        return html

class ComponentSlotProperty:
    _next_id = count()
    components : Dict[ComponentId, 'Component'] = {}

    def __init__(self, id : Optional[ComponentId] = None):
        if id is None:
            while (id := hex(next(ComponentSlotProperty._next_id))[2:]) in ComponentSlotProperty.components:
                pass
        else:
            assert id not in ComponentSlotProperty.components
        self.id = id
        ComponentSlotProperty.components[id] = self

    def __set_name__(self, owner : Type[ComponentOrGame], name):
        self.private_name = '_' + name

    def __get__(self, obj : ComponentOrGame, objtype=None):
        return getattr(obj, self.private_name).content

    def __set__(self, obj : ComponentOrGame, value : Component):
        if not hasattr(obj, self.private_name):
            setattr(obj, self.private_name, ComponentSlot(self.id, obj, value))
            assert value.slot == getattr(obj, self.private_name)
        else:
            getattr(obj, self.private_name).content = value
            assert value.slot == getattr(obj, self.private_name)
