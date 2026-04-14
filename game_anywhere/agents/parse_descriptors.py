from typing import TYPE_CHECKING, Optional, TypedDict

from .descriptors import AgentDescriptor, GameDescriptor
from .local_agent import HumanAgent, PipeAgent
from .network_agent import NetworkAgent

if TYPE_CHECKING:
    from game_anywhere.core import Game

agent_types = {
    "network": NetworkAgent,
    "human": HumanAgent,
    "pipe": PipeAgent,
}


def parse_agent_description(descr: str) -> AgentDescriptor:
    return agent_types[descr].Descriptor()


class GameDescriptorArgs(TypedDict):
    game: str
    args: Optional[str]
    agents: list[str] | str


def parse_game_descriptor(
    obj: GameDescriptorArgs,
    available_games: dict[str, "Game"],
    defaults: dict | None = None,
) -> GameDescriptor:
    if defaults is None:
        defaults = {}
    obj = dict(
        **obj, **defaults
    )  # TODO: this is intended to be a recursive dictionary merge
    GameType = available_games[obj["game"]]
    if obj["args"]:
        cmdline = obj["args"].split(" ")  # imitating a command line
    else:
        cmdline = []
    nb_players, args = GameType.parse_config(cmdline)

    if type(obj["agents"]) is list:
        agent_descriptions = [parse_agent_description(agent) for agent in obj["agents"]]
    else:
        agent_descriptions = [
            parse_agent_description(obj["agents"]) for _ in range(nb_players)
        ]
    return GameDescriptor(GameType, agent_descriptions, **args)
