from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_anywhere.ui import Html


def html(obj, *args, visible: bool = True, **kwargs) -> "Html":
    """
    Returns an HTML representation of the object.
    Semantics are similar to e.g. the str() function, which returns a str representation.
    """
    if obj is None:
        html = ""
    else:
        if visible:
            if hasattr(obj, "html"):
                html = obj.html(*args, **kwargs)
            else:
                html = escape(str(obj))
        else:
            try:
                html = obj.HIDDEN_HTML
            except AttributeError:
                html = "Masked " + escape(str(type(obj)))
    return html
