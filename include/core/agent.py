from typing import Tuple

AgentId = int

class Agent:
    class Surrendered(Exception):
        pass

    def message(self, message: str) -> None:
        raise NotImplementedError()

    def get_2D_choice(self, dimensions: Tuple[int, int]) -> Tuple[int, int]:
        raise NotImplementedError()
