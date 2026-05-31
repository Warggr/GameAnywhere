import functools
from typing import Any, Callable, Iterable


class Html:
    def __init__(
        self, *content, css: str | Iterable[str] = (), js: str | Iterable[str] = ()
    ):
        self.css = set((css,) if isinstance(css, str) else css)
        self.js = set((js,) if isinstance(js, str) else js)
        # Gather resources all at the top and flatten nested HTML
        self.content = []
        for child in content:
            if isinstance(child, Html):
                self.css |= child.css
                child.css.clear()
                self.js |= child.js
                child.js.clear()
            if type(child) is Html:
                self.content += child.content
            else:
                self.content.append(child)

    def __str__(self):
        result = ""
        for child in self.content:
            result += str(child)
        for link in self.css:
            result += f'<link rel="stylesheet" href="/components/{link}"/>'
        for link in self.js:
            result += f'<script src="/components/{link}"></script>'
        return result

    def __add__(self, other):
        if not isinstance(other, Html):
            raise ValueError("HTML: cannot add unrelated type", type(other))
        total_content = []
        for html in (self, other):
            if type(html) is not Html:
                total_content += [html]
            else:  # we can un-nest Html's within Html's
                total_content += html.content
        return Html(*total_content, css=self.css | other.css, js=self.js | other.js)

    def wrap_to_one_element(self) -> "HtmlElement":
        if len(self.content) == 1 and isinstance(self.content[0], HtmlElement):
            child = self.content[0]
            assert not child.css and not child.js
            child.css = self.css
            child.js = self.js
            return child
        return tag.div(*self.content, js=self.js, css=self.css)


HtmlLike = Any


class HtmlElement(Html):
    def __init__(self, *children, tag_name, css=(), js=(), **attrs):
        super().__init__(*children, css=css, js=js)
        self.tag_name = tag_name
        self.attrs = attrs

    def __str__(self):
        result = f"<{self.tag_name}"
        for key, value in self.attrs.items():
            result += f' {key}="{value}"'
        result += ">"
        result += super().__str__()
        result += f"</{self.tag_name}>"
        return result

    def wrap_to_one_element(self):
        return self

    def add_classes(self, *classes: str):
        old_classes = self.attrs.get("class", "").split(" ")
        self.attrs["class"] = " ".join(list(old_classes) + list(classes))


class VoidTag(Html):
    """
    See https://developer.mozilla.org/en-US/docs/Glossary/Void_element.
    These must be handled specially because we must not use a closing </tag>.
    """

    def __init__(self, tag_name, **attrs):
        super().__init__()
        self.tag_name = tag_name
        self.attrs = attrs

    def __str__(self):
        result = f"<{self.tag_name}"
        for key, value in self.attrs.items():
            result += f' {key}="{value}"'
        result += "/>"
        return result


class HtmlElementMeta(type):
    def __getattr__(cls, attrname) -> Callable[..., HtmlElement | VoidTag]:
        if attrname in [
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "link",
            "source",
            "track",
            "wbr",
        ]:
            return functools.partial(VoidTag, tag_name=attrname)
        else:
            return functools.partial(HtmlElement, tag_name=attrname)


class tag(metaclass=HtmlElementMeta):
    """Used as a namespace. Use e.g. tag.div(...), tag.h2(...)"""

    pass
