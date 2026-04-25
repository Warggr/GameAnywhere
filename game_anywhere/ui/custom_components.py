from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class CustomComponentStyle:
    js: Path | None = None
    css: Path | None = None


registry: dict[str, CustomComponentStyle] = {}


def register_component(
    name: str,
    *,
    css: Path | None = None,
    js: Path | None = None,
):
    registry[name] = CustomComponentStyle(css=css, js=js)


def get_registered_component(name: str, extension: Literal["css", "js"]) -> Path:
    """
    Raises:
        KeyError if the component was not registered previously.
    """
    registered = registry[name]
    if extension == "css":
        if registered.css is None:
            raise KeyError
        return registered.css
    elif extension == "js":
        if registered.js is None:
            raise KeyError
        return registered.js
    else:
        raise ValueError()
