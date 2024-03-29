from typing import List, Any, Dict
from .descriptors import AgentDescriptor, GameDescriptor

from .local_agent import HumanAgent
from .network_agent import NetworkAgent

json = Any

def parse_agent_descriptions(args: List[str]) -> List[AgentDescriptor]:
    agent_types = {
        'network': NetworkAgent,
        'human': HumanAgent,
    }
    return [ agent_types[arg].Descriptor() for arg in args ]

def parse_game_descriptor(obj: Any, available_games : Dict[str, 'Game'], defaults: Any = {}) -> GameDescriptor:
    obj = dict(**obj, **defaults) # TODO: this is intended to be a recursive dictionary merge
    GameType = available_games[obj["game"]]
    return GameDescriptor(GameType, parse_agent_descriptions(obj["agents"]))
