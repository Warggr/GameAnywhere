from html import escape

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
    return Html(html)


def merge_classes(*class_names: str | None) -> str:
    return " ".join(class_name for class_name in class_names if class_name)
