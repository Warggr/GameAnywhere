from typing import TypeVar, Generic, Type, Union, List, Tuple, Callable
from .component import Component

class Board(Component):
    # TODO: a board that's as general as possible
    pass

T = TypeVar('T', bound=Component)

class CheckerBoard(Board, Generic[T]):
    def __init__(self, fill: Callable[[], T], width: int, height: int):
        self.board = [ [ fill() for i in range(width) ] for j in range(height) ]

    def __getitem__(self, index: Union[int, Tuple[int, int]]) -> Union[T, List[T]]:
        if type(index) == int:
            return self.board[index]
        elif (type(index) == tuple or type(index) == list) and len(index) == 2:
            return self.board[index[0]][index[1]]
        else:
            raise TypeError(f"expected int or (int, int), got {type(index)}")

    def get_size(self) -> int:
        return len(self.board) * len(self.board[0])

    def get_dimensions(self) -> Tuple[int, int]:
        return len(self.board) , len(self.board[0])

    def html(self):
        result = ''
        result += '<table class="checkerboard"><tbody>'
        for row in self.board:
            result += '<tr>'
            for cell in row:
                result += '<td>' + cell.html() + '</td>'
            result += '</tr>'
        result += '</tbody></table>'
        result += '<style>.checkerboard{border-collapse:collapse;width:100%;height:100%;} .checkerboard td{border:3px;background:white;}</style>'
        return result
