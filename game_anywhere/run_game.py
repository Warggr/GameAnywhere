import argparse

from game_anywhere.agents import agent_types, parse_agent_description
from game_anywhere.agents.descriptors import GameDescriptor

from .core.game import Game, GameSummary


def run_game_from_cmdline(GameType: type[Game], *args, **kwargs) -> GameSummary:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_types", choices=agent_types.keys(), nargs="+")
    parser.add_argument("--config", "-c", nargs="*")
    cmdline_args = parser.parse_args()

    if cmdline_args.config is None:
        cmdline_args.config = []
    try:
        nb_agents, game_config = GameType.parse_config(cmdline_args.config)
    except Exception as err:
        parser.error(str(err))

    agent_descriptions = [
        parse_agent_description(arg) for arg in cmdline_args.agent_types
    ]

    descriptor = GameDescriptor(
        GameType, agent_descriptions, *args, **kwargs, **game_config
    )
    promise = descriptor.start_initialization()
    game = promise.resolve()

    return game.play_game()
