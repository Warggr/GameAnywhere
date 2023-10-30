from typing import List, Any, Dict
from .descriptors import AgentDescriptor, GameDescriptor

from .local_agent import HumanAgent
from .network_agent import NetworkAgent

def parse_agent_descriptions(args: List[str]) -> List[AgentDescriptor]:
    return [ NetworkAgent.Descriptor(), NetworkAgent.Descriptor() ]

def parse_game_descriptor(obj: Any, available_games : Dict[str, 'Game']) -> GameDescriptor:
    GameType = available_games[obj["game"]]
    return GameDescriptor(GameType, parse_agent_descriptions([]))
