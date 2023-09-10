from typing import List, Any
from .descriptors import AgentDescriptor, GameDescriptor

from .local_agent import HumanAgent
from .network_agent import NetworkAgent

from ...examples.tic_tac_toe.tic_tac_toe import TicTacToe

def parse_agent_descriptions(args: List[str]) -> List[AgentDescriptor]:
    return [ HumanAgent.Descriptor(), NetworkAgent.Descriptor() ]

def parse_game_descriptor(obj: Any) -> GameDescriptor:
    return GameDescriptor(TicTacToe, parse_agent_descriptions([]))
