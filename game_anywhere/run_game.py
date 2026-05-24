import argparse
import importlib

from game_anywhere.agents.descriptors import GameDescriptor

from .core.game import Game, GameSummary


class _LazyModule:
    def __init__(self, mod_name: str, attr_name: str | None = None):
        self._mod_name = mod_name
        self._attr_name = attr_name
        self._mod = None

    def __getattr__(self, attr: str):
        if self._mod is None:
            self._mod = importlib.import_module(self._mod_name)
            if self._attr_name is not None:
                self._mod = getattr(self._mod, self._attr_name)
        return getattr(self._mod, attr)


def lazy_import(module_name: str, attr_name: str | None = None):
    return _LazyModule(module_name, attr_name)


agent_types = {
    "network": lazy_import("game_anywhere.agents.network_agent", "NetworkAgent"),
    "pipe": lazy_import("game_anywhere.agents.local_agent", "PipeAgent"),
    "human": lazy_import("game_anywhere.agents.local_agent", "HumanAgent"),
}


def run_game_from_cmdline(GameType: type[Game], *args, **kwargs) -> GameSummary:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_types", choices=agent_types.keys(), nargs="+")
    parser.add_argument("--config", "-c", nargs="*")
    cmdline_args = parser.parse_args()

    if cmdline_args.config is None:
        cmdline_args.config = []
    try:
        kwargs = dict(pair.split("=") for pair in cmdline_args.config)
        _, game_config = GameType.parse_config(
            _num_players=len(cmdline_args.agent_types), **kwargs
        )
    except Exception as err:
        parser.error(str(err))

    agent_descriptions = [
        agent_types[arg].Descriptor() for arg in cmdline_args.agent_types
    ]

    descriptor = GameDescriptor(
        GameType, agent_descriptions, *args, **kwargs, **game_config
    )
    promise = descriptor.start_initialization()
    game = promise.resolve()

    return game.play_game()
