from typing import Union

from game_anywhere.core.game import AgentId
from game_anywhere.core import TurnBasedGame, SimpleGameSummary
from game_anywhere.components import Component, CheckerBoard, ComponentSlotProperty


class TicTacToeMark(Component):
    def __init__(self, player: AgentId):
        super().__init__()
        self.player = player

    def html(self, **kwargs):
        return ('<svg width="100%" height="100%" viewBox="0 0 12 12">'
                '<text y="100%" textLength="100%" lengthAdjust="spacingAndGlyphs" style="font-size: 12;">' +
                ("X" if self.player == 0 else "O") + '</text></svg>')


BOARD_SIZE = 3

TicTacToeBoard = CheckerBoard.specialize(
    height=BOARD_SIZE, width=BOARD_SIZE, CellType=TicTacToeMark
)


def hasRow(
    player: AgentId,
    board: TicTacToeBoard,
    start: tuple[int, int],
    step: tuple[int, int],
):
    for i in range(BOARD_SIZE):
        if board[start].empty() or board[start].content.player != player:
            return False
        start = [start[i] + step[i] for i in range(2)]
    return True


class TicTacToe(TurnBasedGame):
    SummaryType = SimpleGameSummary

    board = ComponentSlotProperty()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board = TicTacToeBoard(fill=lambda: None)

    def turn(self) -> Union[None, SimpleGameSummary]:
        TOTAL_MOVES = self.board.get_size()

        if self.get_current_turn() == TOTAL_MOVES:
            return SimpleGameSummary(SimpleGameSummary.NO_WINNER)

        fields = [field for _, field in self.board.all_fields() if field.empty()]
        field = self.get_current_agent().choose_one_component_slot(fields, fields)
        field.content = TicTacToeMark(self.get_current_agent_index())

        # check rows
        for row in range(BOARD_SIZE):
            if hasRow(self.get_current_agent_index(), self.board, (row, 0), (0, 1)):
                return SimpleGameSummary(self.get_current_agent_id())

        # check rows
        for col in range(BOARD_SIZE):
            if hasRow(self.get_current_agent_index(), self.board, (0, col), (1, 0)):
                return SimpleGameSummary(self.get_current_agent_id())

        # check diagonals
        if hasRow(self.get_current_agent_index(), self.board, (0, 0), (1, 1)):
            return SimpleGameSummary(self.get_current_agent_id())
        if hasRow(self.get_current_agent_index(), self.board, (0, BOARD_SIZE - 1), (1, -1)):
            return SimpleGameSummary(self.get_current_agent_id())

        return None


if __name__ == "__main__":
    from game_anywhere.run_game import run_game_from_cmdline

    run_game_from_cmdline(TicTacToe)
