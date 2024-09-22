from game_anywhere.agents import parse_agent_description, agent_types
from game_anywhere.agents.descriptors import Context
from .core.game import Game, GameSummary
import argparse


def run_game(GameType: type[Game], *args, **kwargs) -> GameSummary:
    parser = argparse.ArgumentParser()
    parser.add_argument('agent_types', choices=agent_types.keys(), nargs='+')
    parser.add_argument('--config', '-c', nargs='*')
    cmdline_args = parser.parse_args()

    if cmdline_args.config is not None:
        try:
            game_config = GameType.parse_config(cmdline_args.config)
        except Exception as err:
            parser.error(str(err))
    else:
        game_config = {}

    agent_descriptions = [parse_agent_description(arg) for arg in cmdline_args.agent_types]

    with GameType(agent_descriptions, *args, **game_config, **kwargs) as game:
        context = Context(game=game)

        promises = [
            desc.start_initialization(i, context)
            for i, desc in enumerate(agent_descriptions)
        ]
        agents = [
            desc.await_initialization(promises[i])
            for i, desc in enumerate(agent_descriptions)
        ]

        game.set_agents(agents)

        return game.play_game()
