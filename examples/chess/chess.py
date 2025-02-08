import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from game_anywhere.core import TurnBasedGame, SimpleGameSummary
from game_anywhere.components import (
    Component,
    CheckerBoard,
    ComponentSlot,
    ComponentSlotProperty,
)
from enum import Enum, auto
from typing import Optional, Any


class ChessPiece(Component):
    class Type(Enum):
        ROOK = 0  # Rook, Knight, and Bishop have to be in that order
        KNIGHT = 1
        BISHOP = 2
        # Here we use `auto()` to indicate that we don't care about their specific values.
        KING = auto()
        QUEEN = auto()
        PAWN = auto()

    class Color(Enum):
        BLACK = True
        WHITE = False

    def __init__(self, color: "ChessPiece.Color", type: "ChessPiece.Type"):
        super().__init__()
        self.color = color
        self.type = type

    def html(self):
        UNICODE_ICONS = {
            "KING": "♔",
            "QUEEN": "♕",
            "ROOK": "♖",
            "KNIGHT": "♘",
            "BISHOP": "♗",
            "PAWN": "♙",
        }
        BLACK_OFFSET = ord("♚") - ord("♔")

        code = ord(UNICODE_ICONS[self.type.name])
        if self.color == ChessPiece.Color.BLACK:
            code += BLACK_OFFSET
        return chr(code)


ChessBoard = CheckerBoard.specialize(height=8, width=8, CellType=ChessPiece)


def full_chessboard() -> ChessBoard:
    board = ChessBoard(fill=lambda: None)
    for i, color in enumerate(["WHITE", "BLACK"]):
        color = ChessPiece.Color[color]
        for j, type in enumerate(
            ["ROOK", "KNIGHT", "BISHOP", "QUEEN", "KING", "BISHOP", "KNIGHT", "ROOK"]
        ):
            type = ChessPiece.Type[type]
            board[j, i * 7].content = ChessPiece(color, type)
        for j in range(8):
            board[j, 1 + i * 5].content = ChessPiece(color, ChessPiece.Type.PAWN)
    return board


class ChessCoordinates(tuple[int, int]):
    """
    Just a tuple of int with a few useful methods for chess coordinates
    """

    class OutOfBounds(Exception):
        pass

    # tuples are immutable so initialization must happen in __new__ - see https://stackoverflow.com/a/1565448
    def __new__(cls, *args):
        if len(args) == 1:
            tup = tuple(*args)
        elif len(args) == 2:
            tup = (args[0], args[1])
        else:
            raise TypeError("Expected iterable or (int, int), got", args)
        obj: tuple[int, int] = super(cls, ChessCoordinates).__new__(
            cls, tup
        )  # using super().__new__ to create a ChessCoordinates object
        for i in range(2):
            if not (0 <= obj[i] and obj[i] < 8):
                raise ChessCoordinates.OutOfBounds()
        return obj

    def algebraic_notation(self) -> str:
        return chr(self[0] + ord("a")) + chr(self[1] + ord("1"))

    def __add__(self, other: tuple[int, int]) -> "ChessCoordinates":
        """
        override the + operator to get neighbours of field easily.
        Throws a ChessCoordinates.OutOfBounds error when the field is outside the chessboard
        """
        return ChessCoordinates(self[0] + other[0], self[1] + other[1])

    def try_add(self, other: tuple[int, int]) -> Optional["ChessCoordinates"]:
        try:
            return self + other
        except ChessCoordinates.OutOfBounds:
            return None


class ChessMove:
    def __init__(
        self,
        start_coords: ChessCoordinates,
        stop_coords: ChessCoordinates,
        piece_captured: Optional[ChessPiece] = None,
    ):
        self.start_coords = start_coords
        self.stop_coords = stop_coords
        self.piece_captured = piece_captured


CARDINAL_DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
DIAGONAL_DIRECTIONS = [(i, j) for i in (-1, 1) for j in (-1, 1)]


class Chess(TurnBasedGame):
    SummaryType = SimpleGameSummary

    board = ComponentSlotProperty()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board = full_chessboard()
        self.last_field_moved_through_for_en_passant = None
        self.captured: list[ChessPiece] = []

    def color_of(self, agent_id: "AgentId"):
        """
        currently a static method, but in the future, colors might not be tied to agent ID
        (e.g. color could be decided randomly at the beginning of the game).
        In that case, it would become a regular method again
        """
        return ChessPiece.Color.WHITE if agent_id == 1 else ChessPiece.Color.BLACK

    def current_color(self):
        return self.color_of(self.get_current_agent_id())

    def go_straight(
        self,
        position: ChessCoordinates,
        direction: tuple[int, int],
        color: ChessPiece.Color,
    ) -> list[ChessCoordinates]:
        assert (
            self.board[position].content and self.board[position].content.color == color
        )
        possibilities = []
        while True:
            position = position.try_add(direction)
            if position and (
                self.board[position].empty()
                or self.board[position].content.color != color
            ):
                possibilities.append(position)
            if not position or self.board[position].content:
                break
        return possibilities

    def possible_movements(
        self, piece: ChessPiece, position: ChessCoordinates
    ) -> list[ChessCoordinates]:
        assert self.board[position].content == piece
        possibilities = []
        if piece.type == ChessPiece.Type.PAWN:
            forward = 1 if piece.color == ChessPiece.Color.WHITE else -1
            field_in_front = position.try_add((0, forward))
            if field_in_front and self.board[field_in_front].empty():
                possibilities.append(field_in_front)
                if (piece.color == ChessPiece.Color.WHITE and position[1] == 1) or (
                    piece.color == ChessPiece.Color.BLACK and position[1] == 6
                ):
                    field_2_in_front = field_in_front.try_add((0, forward))
                    if field_2_in_front and self.board[field_2_in_front].empty():
                        possibilities.append(field_2_in_front)
            for side in (-1, 1):
                field_at_diag = position.try_add((side, forward))
                if field_at_diag:
                    if (
                        (
                            self.board[field_at_diag].content
                            and self.board[field_at_diag].content.color != piece.color
                        )
                        or self.last_field_moved_through_for_en_passant == field_at_diag
                    ):
                        possibilities.append(field_at_diag)
        elif piece.type == ChessPiece.Type.BISHOP:
            for direction in DIAGONAL_DIRECTIONS:
                possibilities += self.go_straight(position, direction, piece.color)
        elif piece.type == ChessPiece.Type.ROOK:
            for direction in CARDINAL_DIRECTIONS:
                possibilities += self.go_straight(position, direction, piece.color)
        elif piece.type == ChessPiece.Type.QUEEN:
            for direction in CARDINAL_DIRECTIONS + DIAGONAL_DIRECTIONS:
                possibilities += self.go_straight(position, direction, piece.color)
        elif piece.type == ChessPiece.Type.KING:
            for direction in CARDINAL_DIRECTIONS + DIAGONAL_DIRECTIONS:
                next_position = position.try_add(direction)
                if next_position and (
                    self.board[next_position].empty()
                    or self.board[next_position].content.color != piece.color
                ):
                    possibilities.append(next_position)
            # TODO castling
        elif piece.type == ChessPiece.Type.KNIGHT:
            for long in [-2, 2]:
                for short in [-1, 1]:
                    for direction in [(long, short), (short, long)]:
                        next_position = position.try_add(direction)
                        if next_position and (
                            self.board[next_position].empty()
                            or self.board[next_position].content.color != piece.color
                        ):
                            possibilities.append(next_position)
        # TODO do not allow the king to be in check
        return possibilities

    def all_options(
        self, previous_choices: list[ChessCoordinates] = []
    ) -> list[ChessCoordinates] | None:
        if len(previous_choices) == 0:
            return [
                ChessCoordinates(coords)
                for coords, field in self.board.all_fields()
                if field.content is not None
                and field.content.color == self.current_color()
            ]

        field_chosen: tuple[int, int] = previous_choices[0]
        piece_chosen = self.board[field_chosen].content
        assert piece_chosen.color == self.current_color()

        if len(previous_choices) == 1:
            return self.possible_movements(piece_chosen, field_chosen)

        assert len(previous_choices) == 2
        return None

    def apply_move(self, choices: list[ChessCoordinates]) -> ChessMove:
        # TODO: it would be more convenient if this worked on a copy of self
        starting_coords: ChessCoordinates = choices[0]
        stopping_coords: ChessCoordinates = choices[1]
        # TODO: assert that the move is valid
        starting_field = self.board[starting_coords]
        piece = starting_field.content
        starting_field.content = None
        assert piece.color == self.current_color()

        captured = None
        if self.board[stopping_coords].content:
            captured = self.board[stopping_coords].content
            assert captured.color != self.current_color()
            self.captured.append(captured)

        self.board[stopping_coords].content = piece

        if (
            piece.type == ChessPiece.Type.PAWN
            and abs(stopping_coords[1] - starting_coords[1]) == 2
        ):
            self.last_field_moved_through_for_en_passant = starting_coords + (
                0,
                (stopping_coords[1] - starting_coords[1]) / 2,
            )
        else:
            self.last_field_moved_through_for_en_passant = (
                None  # en passant expires after one move
            )

        # TODO: pawn promotion

        return ChessMove(starting_coords, stopping_coords, captured)

    def turn(self) -> Optional[SimpleGameSummary]:
        partial_choices: list[PartialChoice] = []
        while True:
            options = self.all_options(partial_choices)
            if options is None:
                break
            special_options = []
            if len(partial_choices) != 0:
                special_options = ["Back"]
            chosen_option = self.get_current_agent().choose_one_component_slot(
                [self.board[coords] for coords in options], options, special_options
            )
            if chosen_option == "Back":
                partial_choices.pop()
            else:
                partial_choices.append(chosen_option)

        move = self.apply_move(partial_choices)

        if any([piece.type == ChessPiece.Type.KING for piece in self.captured]):
            return SimpleGameSummary(winner=self.get_current_agent_id())

    def html(self):
        # TODO add alternate black/white styling
        return super().html()


if __name__ == "__main__":
    from game_anywhere.run_game import run_game_from_cmdline

    run_game_from_cmdline(Chess)
