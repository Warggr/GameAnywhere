import functools


class Html:
    def __init__(self, *content):
        self.content = content

    def __str__(self):
        result = ""
        for child in self.content:
            result += str(child)
        return result

    def __add__(self, other):
        if not isinstance(other, Html):
            raise ValueError("HTML: cannot add unrelated type", type(other))
        total_content = []
        for html in (self, other):
            if type(html) != Html:
                total_content += [html]
            else:  # we can un-nest Html's within Html's
                total_content += html.content
        return Html(*total_content)

    def wrap_to_one_element(self) -> 'HtmlElement':
        return tag.div(self)


class HtmlElement(Html):
    def __init__(self, tag_name, *children, **attrs):
        super().__init__(*children)
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


class HtmlElementMeta(type):
    _tags: dict[str, type["HtmlElement"]] = {}

    @staticmethod
    def _wrap_init(init, tag_name):
        @functools.wraps(init)
        def _new_init(self, *args, **kwargs):
            init(self, tag_name, *args, **kwargs)

        return _new_init

    def __getattr__(cls, attrname) -> type[HtmlElement]:
        try:
            return HtmlElementMeta._tags[attrname]
        except KeyError:
            tag_class = type.__new__(type, attrname, (HtmlElement,), {})
            tag_class.__init__ = HtmlElementMeta._wrap_init(
                tag_class.__init__, tag_name=attrname
            )
            return tag_class


class tag(metaclass=HtmlElementMeta):
    """ Used as a namespace. Use e.g. tag.div(...), tag.h2(...) """
    pass
