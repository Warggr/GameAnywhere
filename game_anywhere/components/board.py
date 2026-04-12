from typing import (
    Callable,
    Generic,
    Iterable,
    Iterator,
    Optional,
    TypeVar,
)

from game_anywhere.ui import Html, tag

from .component import Component, ComponentSlot


class Board(Component):
    # TODO: a board that's as general as possible
    pass


T = TypeVar("T", bound=Component)


class CheckerBoard(Board, Generic[T]):
    class Field(ComponentSlot):
        pass

    def __init__(
        self, height: int, width: int, fill: Callable[[], Optional[T]] | None = None
    ):
        super().__init__()
        self.width = width
        self.height = height
        self.board: list[list[Optional[T]]] = [
            [None for i in range(width)] for j in range(height)
        ]
        if fill is None:
            fill = lambda: None  # noqa: E731
        for i in range(width):
            for j in range(height):
                self.board[i][j] = CheckerBoard.Field(
                    id_=self._coords_to_field_id((i, j)),
                    parent=self,
                    content=fill(),
                )

    def __getitem__(self, index: tuple[int, int]) -> Optional[T]:
        try:
            return self.board[index[0]][index[1]].get()
        except TypeError as err:
            raise TypeError(f"expected (int, int), got {type(index)}") from err

    def __setitem__(self, index: tuple[int, int], val: Optional[T]):
        self.board[index[0]][index[1]].set(val)

    def all_fields(self) -> Iterable[tuple[tuple[int, int], Optional[T]]]:
        return (
            ((i, j), self.board[i][j])
            for j in range(self.width)
            for i in range(self.height)
        )

    def get_slot(self, index: tuple[int, int]) -> "CheckerBoard.Field":
        i, j = index
        return self.board[i][j]

    @staticmethod
    def _coords_to_field_id(coords: tuple[int, int]):
        return f"{coords[0]},{coords[1]}"

    def get_size(self) -> int:
        return self.width * self.height

    def get_dimensions(self) -> tuple[int, int]:
        return self.height, self.width

    # Component interface methods

    def get_slots(self) -> Iterator[tuple[str, "CheckerBoard.Field"]]:
        for i in range(self.height):
            for j in range(self.width):
                yield self._coords_to_field_id((i, j)), self.board[i][j]

    def _iter_fields(
        self, trans_height: int, trans_width: int, turn: float = 0
    ) -> Iterable["CheckerBoard.Field"]:
        reverse_transforms = {
            0: lambda i, j: (i, j),
            90: lambda i, j: (j, self.height - i - 1),
            180: lambda i, j: (self.height - i - 1, self.width - j - 1),
            270: lambda i, j: (self.width - j - 1, i),
        }
        rev_transform = reverse_transforms[int(turn % 360)]
        for it in range(trans_height):
            for jt in range(trans_width):
                i, j = rev_transform(it, jt)
                yield self.board[i][j]

    def html(self, viewer_id=None, *, turn: float = 0) -> Html:
        if turn % 180 == 0:
            width, height = self.width, self.height
        elif turn % 180 == 90:
            width, height = self.height, self.width
        else:
            raise NotImplementedError(
                "CheckerBoard must be rotated by 90° or a multiple!"
            )
        return Html(
            tag.div(
                *(field.html() for field in self._iter_fields(height, width, turn)),
                **{
                    "class": "checkerboard",
                    "style": f"grid-template-rows: repeat({width}, 1fr); grid-template-columns: repeat({height}, 1fr)",
                },
            ),
            tag.style(
                ".checkerboard{display:grid;width:100%;height:100%;gap:10px;}"
                + " .checkerboard div{background-color:white;color:black;border:2px solid;aspect-ratio:1;}"
            ),
        )
