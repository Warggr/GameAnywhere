from typing import TYPE_CHECKING, Generic, Optional, Protocol, TypeVar

from game_anywhere.components.containers import List
from game_anywhere.components.utils import html

from .custom_components import register_component
from .ui import HtmlElement, tag

try:
    from importlib.resources import files
except ImportError:
    from importlib_resource import files

if TYPE_CHECKING:
    from .ui import Html


T = TypeVar("T", contravariant=True)


class DisplayStyle(Protocol, Generic[T]):
    def __call__(self, obj: T, viewer_id=None, visible: bool = True) -> "Html": ...


class Chips:
    def __init__(self, one_chip: "Html"):
        self.one_chip = one_chip

    def __call__(self, obj: int, viewer_id=None, visible: bool = True) -> "Html":
        assert isinstance(obj, int), "only integers can be displayed as chips!"
        if visible:
            return tag.ul(*[tag.li(self.one_chip) for _ in range(obj)])
        else:
            return tag.ul()


class FlippedChips:
    def __init__(
        self, front: "Html", back: "Html", maxi: int, masked: Optional["Html"] = None
    ):
        self.front = front
        self.back = back
        self.maxi = maxi
        self.masked = masked

    def __call__(self, obj: int, viewer_id=None, visible: bool = True) -> "Html":
        assert isinstance(obj, int), "only integers can be displayed as chips!"
        if visible:
            return tag.ul(
                *(
                    [tag.li(self.front) for _ in range(obj)]
                    + [tag.li(self.back) for _ in range(obj, self.maxi)]
                )
            )
        else:
            assert self.masked is not None, (
                "mask flipped chips required but no masked chip display provided!"
            )
            return tag.ul(*[tag.li(self.masked) for _ in range(self.maxi)])


register_component(
    "hand_fan",
    js=files("game_anywhere") / "components" / "assets" / "hand_fan.js",
    css=files("game_anywhere") / "components" / "assets" / "hand_fan.css",
)


def hand_fan(obj: List, viewer_id=None, visible: bool = True) -> "Html":
    assert isinstance(obj, List), "only lists can be displayed in a fan layout!"
    elements = [
        tag.li(html(o, viewer_id=viewer_id, visible=visible))
        for o in obj.get_slots().values()
    ]
    return HtmlElement(
        *elements,
        tag_name="ga-hand-fan",
        css="hand_fan/css",
        js="hand_fan/js",
        **{"class": "ga-list ga-hand-fan"},
    )
