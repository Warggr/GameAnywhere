from typing import TYPE_CHECKING

from game_anywhere.components.utils import html

from .component import AbstractComponentSlot
from .tracing import computed_stack

if TYPE_CHECKING:
    from typing import Any, Callable

    from game_anywhere.ui import Html

    from .component import AbstractComposite


class ComputedComponentSlot(AbstractComponentSlot):
    def __init__(
        self,
        method: Callable[[AbstractComposite], Any],
        id_: Any,
        parent: AbstractComposite,
    ):
        super().__init__(id_=id_, parent=parent)
        self.method = method
        self.dependencies: set[AbstractComponentSlot] = set()
        self.value = self._compute()

    def _compute(self):
        computed_stack.append(self)
        result = self.method(self.parent)
        assert computed_stack.pop() is self
        return result

    def get(self):
        return self.value

    def invalidate_cache(self):
        for d in self.dependencies:
            d.dependents.remove(self)
        self.dependencies.clear()
        self.value = self._compute()
        self.get_game().log_component_update(self)

    def html(self, viewer_id=None, *, force_reveal=False) -> Html:
        return html(self.value)


class computed:
    def __init__(self, method: Callable[[AbstractComposite], Any]):
        """
        Can be used as a decorator: @computed def ...
        """
        self.method = method

    def __set_name__(self, owner: type[AbstractComposite], name: str):
        if not hasattr(owner, "_computed_slots"):
            owner._computed_slots = []
        owner._computed_slots.append(name)
        self.name = name

    def __get__(self, obj: AbstractComposite, objtype=None):
        if self.name not in obj.computed_properties:
            slot = ComputedComponentSlot(self.method, id_=self.name, parent=obj)
            obj.computed_properties[self.name] = slot
            obj.get_game().log_added_slot(self.name, slot)
        return obj.computed_properties[self.name].get()
