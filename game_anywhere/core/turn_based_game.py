from abc import abstractmethod
from typing import TYPE_CHECKING, Union

from .game import AgentId, Game, GameSummary

if TYPE_CHECKING:
    from .agent import Agent


class TurnBasedGame(Game):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.totalTurn = 0

    def play_game(self) -> GameSummary:
        while True:
            winner = self.turn()
            if winner is not None:
                return winner
            self.totalTurn += 1

    @abstractmethod
    def turn(self) -> Union[None, GameSummary]: ...

    def get_current_agent_index(self) -> int:
        return self.totalTurn % len(self.agents)

    def get_current_agent_id(self) -> AgentId:
        return self.get_current_agent_index() + 1

    def get_current_agent(self) -> "Agent":
        return self.agents[self.get_current_agent_index()]

    def get_current_turn(self) -> int:
        return self.totalTurn
