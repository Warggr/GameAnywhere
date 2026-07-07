from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dynamic import ComputedComponentSlot


computed_stack: list[ComputedComponentSlot] = []
