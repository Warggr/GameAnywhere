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

    def wrap_to_one_element(self):
        return div(self)


class HtmlElement(Html):
    def __init__(self, tagName, *children, **attrs):
        super().__init__(*children)
        self.tagName = tagName
        self.attrs = attrs

    def __str__(self):
        result = f"<{self.tagName}"
        for key, value in self.attrs.items():
            result += f' {key}="{value}"'
        result += ">"
        result += super().__str__()
        result += f"</{self.tagName}>"
        return result

    def wrap_to_one_element(self):
        return self


class HtmlElementMeta(type):
    @staticmethod
    def _wrap_init(init, tagName):
        @functools.wraps(init)
        def _new_init(self, *args, **kwargs):
            init(self, tagName, *args, **kwargs)

        return _new_init

    def __new__(cls, name, parents, attrs):
        if HtmlElement not in parents:
            parents = (HtmlElement, *parents)
        new_subclass = type.__new__(cls, name, parents, attrs)
        new_subclass.__init__ = HtmlElementMeta._wrap_init(
            new_subclass.__init__, tagName=name
        )
        return new_subclass


class div(metaclass=HtmlElementMeta):
    pass


class style(metaclass=HtmlElementMeta):
    pass
