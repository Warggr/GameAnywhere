import sys
from pathlib import Path
sys.path.append( str( Path(__file__).parent.parent.parent.parent) )

from game_anywhere.include.core import TurnBasedGame, SimpleGameSummary
from game_anywhere.include.components import Component, CheckerBoard
from enum import Enum, auto
from typing import Optional

class ChessPiece:
    class Type(Enum):
        ROOK = 0
        KNIGHT = 1
        BISHOP = 2
        KING = auto()
        QUEEN = auto()
        PAWN = auto()

    class Color(Enum):
        BLACK = True
        WHITE = False

    def __init__(self, color : 'ChessPiece.Color', type: 'ChessPiece.Type'):
        self.color = color
        self.type = Type

ChessBoard = CheckerBoard.specialize(height=8, width=8, CellType=Optional[ChessPiece])

class Chess(TurnBasedGame):
    SummaryType = SimpleGameSummary

    @staticmethod
    def full_chessboard():
        board = ChessBoard(fill=lambda: None)
        for i, color in enumerate([ 'BLACK', 'WHITE' ]):
            color = ChessPiece.Color[color]
            for j, type in enumerate([ 'ROOK', 'KNIGHT', 'BISHOP', 'QUEEN', 'KING', 'BISHOP', 'KNIGHT', 'ROOK' ]):
                type = ChessPiece.Type[type]
                board[i * 8, j] = ChessPiece(color, type)
            for j in range(8):
                board[ 1 + i*6, j ] = ChessPiece(color, ChessPiece.Type.PAWN)
        return board

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board = Chess.full_chessboard()

    def html(self):
        # TODO add alternate black/white styling
        return self.board.html()

