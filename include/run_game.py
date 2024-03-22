from typing import List
from game_anywhere.src.agents import parse_agent_descriptions
from game_anywhere.src.agents.descriptors import Context
from .core.game import Game, GameSummary
import sys

def run_game(GameType : type[Game]) -> GameSummary:
    agent_descriptions = parse_agent_descriptions(sys.argv[1:])

    game = GameType(agent_descriptions)
    context = Context()

    promises = [ desc.start_initialization(i, context) for i, desc in enumerate(agent_descriptions) ]
    agents = [ desc.await_initialization(promises[i]) for i, desc in enumerate(agent_descriptions) ]

    game.agents = agents

    return game.play_game()
