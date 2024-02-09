import functools

class HtmlElement:
    def __init__(self, tagName, *children, **attrs):
        self.tagName = tagName
        self.children = children
        self.attrs = attrs
    def __str__(self):
        result = f'<{self.tagName}'
        for key, value in self.attrs.items():
            result += f' {key}="{value}"'
        result += '>'
        for child in self.children:
            result += str(child)
        result += f'</{self.tagName}>'
        return result

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
        new_subclass.__init__ = HtmlElementMeta._wrap_init(new_subclass.__init__, tagName=name)
        return new_subclass

class div(metaclass=HtmlElementMeta):
    pass

class style(metaclass=HtmlElementMeta):
    pass
