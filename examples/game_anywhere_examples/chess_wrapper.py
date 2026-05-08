from collections import defaultdict
from typing import TYPE_CHECKING, Optional

import chess
from chess import svg

from game_anywhere.components import (
    CheckerBoard,
    Component,
    ComponentSlotProperty,
    List,
)
from game_anywhere.core import TurnBasedGame
from game_anywhere.core.game import GameSummary
from game_anywhere.ui import tag

if TYPE_CHECKING:
    from chess import Move, Square

    from game_anywhere.core import AgentId


class ChessPiece(Component):
    def __init__(self, piece: chess.Piece):
        super().__init__()
        self.impl = piece

    @staticmethod
    def create(*args, **kwargs):
        return ChessPiece(chess.Piece(*args, **kwargs))

    def html(self, viewer_id=None):
        return svg.piece(self.impl)


class ChessBoard(CheckerBoard):
    def __init__(
        self, board: chess.Board, agents_to_colors: dict[AgentId, chess.Color]
    ):
        super().__init__(height=8, width=8)
        self.agents_to_colors = agents_to_colors
        self.impl = board
        # Sync pychess state with Component state
        for sq, piece in self.impl.piece_map().items():
            self[get_coords(sq)] = ChessPiece(piece)

    def html(self, viewer_id=None, *, turn: float | None = None):
        if turn is None:
            if viewer_id in self.agents_to_colors:
                # By default, CheckerBoard shows the low indices (white side) on the top
                turn = {chess.BLACK: 0, chess.WHITE: 180}[
                    self.agents_to_colors[viewer_id]
                ]
            else:
                turn = 90
        html = super().html(viewer_id=viewer_id, turn=turn)
        chess_style = ".checkerboard>div{background-color:white;} "
        # see https://stackoverflow.com/a/69122036
        if turn % 180 == 0:
            black_fields = [f"16n+{2 * i + 1}" for i in range(4)] + [
                f"16n+{2 * i + 10}" for i in range(4)
            ]
        else:
            black_fields = [f"16n+{2 * i + 0}" for i in range(4)] + [
                f"16n+{2 * i + 11}" for i in range(4)
            ]
        black_fields = ", ".join(
            ".checkerboard>div:nth-child(" + idx + ")" for idx in black_fields
        )
        chess_style += black_fields + "{background-color:grey}"
        return html + tag.style(chess_style)


def get_coords(sq: chess.Square) -> tuple[int, int]:
    return chess.square_rank(sq), chess.square_file(sq)


class ChessSummary(GameSummary):
    def __init__(
        self, outcome: chess.Outcome, color_to_agents: dict[chess.Color, AgentId]
    ):
        super().__init__()
        if outcome.winner is None:
            self.winner = self.NO_WINNER
        else:
            self.winner = color_to_agents[outcome.winner]

    def get_winner(self) -> AgentId:
        return self.winner


class Chess(TurnBasedGame):
    SummaryType = ChessSummary

    board = ComponentSlotProperty[ChessBoard]()
    captured = ComponentSlotProperty[List[ChessPiece]]()

    def __init__(self, *args, shuffle_colors: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        colors = [chess.WHITE, chess.BLACK]
        agent_ids = [0, 1]
        if shuffle_colors:
            from random import shuffle

            shuffle(agent_ids)
        self.colors_to_agents = {c: a for c, a in zip(colors, agent_ids, strict=True)}
        self.agents_to_colors = {a: c for c, a in zip(colors, agent_ids, strict=True)}
        self.board = ChessBoard(chess.Board(), self.agents_to_colors)
        self.captured = List[ChessPiece]([])

    CONFIG_SCHEMA = {
        "properties": {
            "_num_players": {"const": 2},
            "shuffle_colors": {
                "type": "boolean",
                "default": True,
                "help": "Randomly choose which player plays white.",
            },
        },
    }

    def apply_move(self, move: Move):
        is_castling = self.board.impl.is_castling(move)
        if is_castling:
            # Manually synch the rooks
            for square in self.board.impl.pieces(chess.ROOK, self.board.impl.turn):
                self.board[get_coords(square)] = None

        self.board.impl.push(move)

        if is_castling:
            for square in self.board.impl.pieces(chess.ROOK, self.board.impl.turn):
                self.board[get_coords(square)] = ChessPiece.create(
                    chess.ROOK, self.board.impl.turn
                )

        starting_coords = get_coords(move.from_square)
        stopping_coords = get_coords(move.to_square)
        piece = self.board[starting_coords]
        self.board[starting_coords] = None

        if self.board[stopping_coords] is not None:
            captured = self.board[stopping_coords]
            self.captured.append(captured)

        if move.promotion is not None:
            self.board[stopping_coords] = ChessPiece.create(move.promotion, piece.color)
        else:
            self.board[stopping_coords] = piece

        assert move.drop is None

    def turn(self) -> Optional[ChessSummary]:
        move_by_starting_position: dict[Square, list[Move]] = defaultdict(list)
        for move in self.board.impl.legal_moves:
            move_by_starting_position[move.from_square].append(move)

        while True:
            starts = list(move_by_starting_position.keys())

            start_field = self.get_current_agent().choose_one_component_slot(
                [self.board.get_slot(get_coords(start)) for start in starts],
                starts,
            )

            moves = move_by_starting_position[start_field]
            chosen_move = self.get_current_agent().choose_one_component_slot(
                [self.board.get_slot(get_coords(move.to_square)) for move in moves],
                moves,
                special_options=["Back"],
            )
            if chosen_move == "Back":
                continue
            else:
                break

        self.apply_move(chosen_move)
        self.message(chosen_move.uci())

        outcome = self.board.impl.outcome()
        if outcome is not None:
            return ChessSummary(outcome, self.colors_to_agents)


if __name__ == "__main__":
    from game_anywhere.run_game import run_game_from_cmdline

    run_game_from_cmdline(Chess)
