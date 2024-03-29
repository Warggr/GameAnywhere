from typing import TypeVar, Generic, Type, Union, List, Tuple, Callable, Iterable, Optional
from abc import ABC
from .component import Component, ComponentSlot
from game_anywhere.ui import Html, div, style

class Board(Component):
    # TODO: a board that's as general as possible
    pass

T = TypeVar('T', bound=Component)

class CheckerBoard(Board, Generic[T]):
    class Field(ComponentSlot):
        pass

    @classmethod
    def specialize(cls, height : int, width : int, CellType : Type[T]) -> Type['CheckerBoard[T]']:
        class _CheckerBoard(CheckerBoard[CellType]):
            def __init__(self, fill: Callable[[], CellType] = CellType):
                super().__init__()
                self.board = [ [ None for i in range(width) ] for j in range(height) ]
                for i in range(width):
                    for j in range(height):
                        self.board[i][j] = CheckerBoard.Field(
                            id=self.coords_to_field_id((i,j)),
                            parent=self,
                            content=fill()
                        )
        _CheckerBoard.width = width
        _CheckerBoard.height = height
        _CheckerBoard.CellType = CellType
        return _CheckerBoard

    def __getitem__(self, index: Tuple[int, int]) -> 'CheckerBoard.Field':
        try:
            return self.board[index[0]][index[1]]
        except TypeError:
            raise TypeError(f"expected (int, int), got {type(index)}")

    def __setitem__(self, index: Tuple[int, int], val : T):
        self.board[index[0]][index[1]].set(val)

    def all_fields(self) -> Iterable[Tuple[Tuple[int, int], T]]:
        return (((i, j), self.board[i][j]) for j in range(self.width) for i in range(self.height))

    def coords_to_field_id(self, coords : Tuple[int, int]):
        return f"{coords[0]},{coords[1]}"

    @classmethod
    def get_size(cls) -> int:
        return cls.width * cls.height

    @classmethod
    def get_dimensions(cls) -> Tuple[int, int]:
        return cls.height, cls.width

    def html(self) -> Html:
        return Html(
            div(
                *(field.html() for _, field in self.all_fields()),
                **{
                    'class': "checkerboard",
                    'style': f"grid-template-rows: repeat({self.width}, 1fr); grid-template-columns: repeat({self.height}, 1fr)",
                }
            ),
            style('.checkerboard{display:grid;width:100%;height:100%;background-color:red;gap:10px;} .checkerboard div{background-color:white;color:black;border:2px solid;aspect-ratio:1;}'),
        )
