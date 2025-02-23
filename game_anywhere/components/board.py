from typing import (
    TypeVar,
    Generic,
    Type,
    Callable,
    Iterable,
    Optional, Iterator,
)

from .component import Component, ComponentSlot
from game_anywhere.ui import Html, tag


class Board(Component):
    # TODO: a board that's as general as possible
    pass


T = TypeVar("T", bound=Component)


class CheckerBoard(Board, Generic[T]):
    class Field(ComponentSlot):
        pass

    def __init__(self, height: int, width: int, fill: Callable[[], Optional[T]] | None = None):
        super().__init__()
        self.width = width
        self.height = height
        self.board: list[list[Optional[T]]] = [[None for i in range(width)] for j in range(height)]
        if fill is None:
            fill = lambda: None
        for i in range(width):
            for j in range(height):
                self.board[i][j] = CheckerBoard.Field(
                    id=self._coords_to_field_id((i, j)),
                    parent=self,
                    content=fill(),
                )

    def __getitem__(self, index: tuple[int, int]) -> Optional[T]:
        try:
            return self.board[index[0]][index[1]].get()
        except TypeError:
            raise TypeError(f"expected (int, int), got {type(index)}")

    def __setitem__(self, index: tuple[int, int], val: Optional[T]):
        self.board[index[0]][index[1]].set(val)

    def all_fields(self) -> Iterable[tuple[tuple[int, int], Optional[T]]]:
        return (
            ((i, j), self.board[i][j])
            for j in range(self.width)
            for i in range(self.height)
        )

    def get_slot(self, index: tuple[int, int]) -> "Checkerboard.Field":
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
                yield self._coords_to_field_id((i,j)), self.board[i][j]

    def html(self, viewer_id=None) -> Html:
        return Html(
            tag.div(
                *(field.html() for _, field in self.all_fields()),
                **{
                    "class": "checkerboard",
                    "style": f"grid-template-rows: repeat({self.width}, 1fr); grid-template-columns: repeat({self.height}, 1fr)",
                },
            ),
            tag.style(
                ".checkerboard{display:grid;width:100%;height:100%;gap:10px;}" +
                " .checkerboard div{background-color:white;color:black;border:2px solid;aspect-ratio:1;}"
            ),
        )
