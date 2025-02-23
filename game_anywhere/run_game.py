from game_anywhere.agents import parse_agent_description, agent_types
from game_anywhere.agents.descriptors import Context, GameDescriptor
from .core.game import Game, GameSummary
import argparse


def run_game_from_cmdline(GameType: type[Game], *args, **kwargs) -> GameSummary:
    parser = argparse.ArgumentParser()
    parser.add_argument('agent_types', choices=agent_types.keys(), nargs='+')
    parser.add_argument('--config', '-c', nargs='*')
    cmdline_args = parser.parse_args()

    if cmdline_args.config is None:
        cmdline_args.config = []
    try:
        nb_agents, game_config = GameType.parse_config(cmdline_args.config)
    except Exception as err:
        parser.error(str(err))

    agent_descriptions = [parse_agent_description(arg) for arg in cmdline_args.agent_types]

    return run_game(GameDescriptor(GameType, agent_descriptions, *args, **kwargs, **game_config))


def run_game(descriptor: GameDescriptor):
    game = descriptor.create_game()
    context = Context(game=game)

    agents = descriptor.create_agents(context)

    game.set_agents(agents)

    return game.play_game()
