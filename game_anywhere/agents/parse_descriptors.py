from typing import Any
from .descriptors import AgentDescriptor, GameDescriptor

from .local_agent import HumanAgent, PipeAgent
from .network_agent import NetworkAgent

agent_types = {
    "network": NetworkAgent,
    "human": HumanAgent,
    "pipe": PipeAgent,
}

def parse_agent_description(descr: str) -> AgentDescriptor:
    return agent_types[descr].Descriptor()


def parse_game_descriptor(
    obj: Any, available_games: dict[str, "Game"], defaults: Any = {}
) -> GameDescriptor:
    obj = dict(
        **obj, **defaults
    )  # TODO: this is intended to be a recursive dictionary merge
    GameType = available_games[obj["game"]]
    args = {}
    if obj["args"]:
        print(obj["args"].split(' '))
        args = GameType.parse_config(obj["args"].split(' ')) # imitating a command line
    if type(obj["agents"]) == list:
        agent_descriptions = [parse_agent_description(agent) for agent in obj["agents"]]
    else:
        agent_descriptions = parse_agent_description(obj["agents"])
    return GameDescriptor(GameType, agent_descriptions, **args)
