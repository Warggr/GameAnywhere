from typing import TypeVar, Generic, Type, Union, List, Tuple, Callable
from abc import ABC
from .component import Component

class Board(Component):
    # TODO: a board that's as general as possible
    pass

T = TypeVar('T', bound=Component)
CellTypeType = TypeVar('CellType', bound=Component)

class CheckerBoard(Board, Generic[T]):
    @classmethod
    def specialize(cls, height : int, width : int, CellType : CellTypeType) -> Type['CheckerBoard[CellTypeType]']:
        class _CheckerBoard(CheckerBoard[CellTypeType]):
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

    @classmethod
    def get_size(cls) -> int:
        return cls.width * cls.height

    @classmethod
    def get_dimensions(cls) -> Tuple[int, int]:
        return cls.height, cls.width

    @classmethod
    def html(cls):
        result = ''
        result += '<table class="checkerboard"><tbody>'
        for row in range(cls.height):
            result += '<tr>'
            for cell in range(cls.width):
                result += '<td>' + cls.CellType.html() + '</td>'
            result += '</tr>'
        result += '</tbody></table>'
        result += '<style>.checkerboard{border-collapse:collapse;width:100%;height:100%;} .checkerboard td{border:3px;background:white;}</style>'
        return result
