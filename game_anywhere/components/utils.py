"""
Returns an HTML representation of the object.
Semantics are similar to e.g. the str() function, which returns a str representation
"""


def html(obj) -> "Html":
    if obj is None:
        html = ""
    else:
        try:
            html = obj.html()
        except AttributeError:
            html = str(obj)
    return html
