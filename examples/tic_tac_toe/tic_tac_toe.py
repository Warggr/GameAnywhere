import sys
from pathlib import Path
sys.path.append( str( Path(__file__).parent.parent.parent.parent) )

from typing import Tuple, Union

from game_anywhere.include import run_game
from game_anywhere.include.core.game import AgentId
from game_anywhere.include.core import TurnBasedGame, SimpleGameSummary
from game_anywhere.include.components import CheckerBoard

class TicTacToeState:
    class Field:
        def __init__(self):
            self.empty = True
            self.player : AgentId = 0

        def __str__(self):
            return ' ' if self.empty else 'X' if self.player==0 else 'O'

    BOARD_DIMENSION = 3

    def __init__(self):
        self.board = CheckerBoard(self.Field, self.BOARD_DIMENSION, self.BOARD_DIMENSION)


def hasRow(player: AgentId, board: CheckerBoard[TicTacToeState.Field], start: Tuple[int, int], step: Tuple[int, int]):
    for i in range(TicTacToeState.BOARD_DIMENSION):
        if board[start].empty or board[start].player != player:
            return False
        start = [start[i] + step[i] for i in range(2) ]
    return True


class TicTacToe(TurnBasedGame):
    SummaryType = SimpleGameSummary

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = TicTacToeState()

    def turn(self) -> Union[None, SimpleGameSummary]:
        TOTAL_MOVES = self.state.board.get_size()

        if self.get_current_turn() == TOTAL_MOVES:
            return SimpleGameSummary(SimpleGameSummary.NO_WINNER)

        BOARD_DIMENSIONS = self.state.board.get_dimensions()

        field = None
        while True:
            position = self.get_current_agent().get_2D_choice(BOARD_DIMENSIONS);
            field = self.state.board[position]
            if field.empty:
                break

        field.empty = False
        field.player = self.get_current_agent_index()

        message = "-------\n"
        for row in self.state.board.board:
            for cell in row:
                message += '|' + str(cell)
            message += "|\n-------\n"

        for agent in self.agents:
            agent.message(message)

        #check rows
        for row in range(TicTacToeState.BOARD_DIMENSION):
            if hasRow( self.get_current_agent_index(), self.state.board, (row, 0), (0, 1)):
                return SimpleGameSummary(self.get_current_agent_id())

        #check rows
        for col in range(TicTacToeState.BOARD_DIMENSION):
            if hasRow( self.get_current_agent_index(), self.state.board, (0, col), (1, 0)):
                return SimpleGameSummary(self.get_current_agent_id())

        #check diagonals
        if hasRow( self.get_current_agent_index(), self.state.board, (0, 0), (1, 1)):
            return SimpleGameSummary( self.get_current_agent_id() )
        if hasRow( self.get_current_agent_index(), self.state.board, (0, TicTacToeState.BOARD_DIMENSION-1), (1, -1)):
            return SimpleGameSummary( self.get_current_agent_id() )

        return None

if __name__ == "__main__":
    run_game(TicTacToe, sys.argv);
