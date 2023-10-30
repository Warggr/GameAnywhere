from typing import TypeVar, Generic, Type, Union, List, Tuple, Callable, Iterable
from abc import ABC
from .component import Component

class Board(Component):
    # TODO: a board that's as general as possible
    pass

T = TypeVar('T', bound=Component)

class CheckerBoard(Board, Generic[T]):
    @classmethod
    def specialize(cls, height : int, width : int, CellType : Type[T]) -> Type['CheckerBoard[T]']:
        class _CheckerBoard(CheckerBoard[CellType]):
            def __init__(self, fill: Callable[[], CellType] = CellType):
                self.board = [ [ fill() for i in range(width) ] for j in range(height) ]
        _CheckerBoard.width = width
        _CheckerBoard.height = height
        _CheckerBoard.CellType = CellType
        return _CheckerBoard

    def __getitem__(self, index: Union[int, Tuple[int, int]]) -> Union[T, List[T]]:
        if type(index) == int:
            return self.board[index]
        elif (type(index) == tuple or type(index) == list) and len(index) == 2:
            return self.board[index[0]][index[1]]
        else:
            raise TypeError(f"expected int or (int, int), got {type(index)}")

    def __setitem__(self, index: Tuple[int, int], val : T):
        self.board[index[0]][index[1]] = val

    def all_fields(self) -> Iterable[T]:
        return (self.board[i][j] for j in range(self.width) for i in range(self.height))

    @classmethod
    def get_size(cls) -> int:
        return cls.width * cls.height

    @classmethod
    def get_dimensions(cls) -> Tuple[int, int]:
        return cls.height, cls.width

    def html(self):
        result = ''
        result += f'<div class="checkerboard" style="grid-template-rows: repeat({self.width}, 1fr); grid-template-columns: repeat({self.height}, 1fr)">'
        for field in self.all_fields():
            result += field.html()
        result += '</div>'
        result += '<style>.checkerboard{display:grid;width:100%;height:100%;background-color:red;gap:10px;} .checkerboard div{background-color:white;color:black;border:2px solid;aspect-ratio:1;}</style>'
        return result
