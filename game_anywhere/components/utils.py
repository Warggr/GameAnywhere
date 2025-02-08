from typing import Any
from html import escape

"""
Returns an HTML representation of the object.
Semantics are similar to e.g. the str() function, which returns a str representation
"""


def html(obj, *args, **kwargs) -> "Html":
    if obj is None:
        html = ""
    else:
        if hasattr(obj, 'html'):
            html = obj.html(*args, **kwargs)
        else:
            html = escape(str(obj))
    return html


def mask(obj: Any, *_args, **_kwargs) -> "Html":
    """
    Returns a masked HTML representation of the object.
    *args, **kwargs are accepted so the signature is compatible with html().
    """
    try:
        html = obj.HIDDEN_HTML
    except AttributeError:
        html = "Masked " + escape(str(type(obj)))
    return html
