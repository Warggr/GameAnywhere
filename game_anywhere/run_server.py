import argparse
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from aiohttp import http, web

try:
    from importlib.resources import as_file, files
except ImportError:
    from importlib_resource import as_file, files

from game_anywhere.network.http_controlled_server import HttpControlledServer
from game_anywhere.network.router import heartbeat

if TYPE_CHECKING:
    from game_anywhere import Game


def load_games() -> dict[str, "Game"]:
    available_games = {}
    for ep in entry_points(group="game_anywhere.games"):
        try:
            game_class = ep.load()
            available_games[ep.name] = game_class
        except ImportError:
            pass
    return available_games


available_games = load_games()


class ParseGameAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, nargs=2, **kwargs)

    def format_usage(self):
        return f"{self.option_strings} GAME_NAME GAME_ARGS"

    def __call__(self, parser, namespace, values, option_string=None):
        import json

        from game_anywhere.agents.descriptors import GameDescriptor
        from game_anywhere.agents.network_agent import NetworkAgent

        try:
            game_name, game_args = values
            game_args = json.loads(game_args)
            game_type = available_games[game_name]
            num_players, game_kwargs = game_type.parse_config(**game_args)
        except Exception as err:
            raise argparse.ArgumentError(
                message=f"Could not create game:\n{err}", argument=self
            ) from err
        game_description = GameDescriptor(
            game_type,
            [NetworkAgent.Descriptor() for _ in range(num_players)],
            **game_kwargs,
        )
        setattr(namespace, self.dest, game_description)


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", default=8080, dest="port", type=int)
parser.add_argument("-g", "--start-game", action=ParseGameAction)
args = parser.parse_args()


client_root = files("game_anywhere") / "client" / "dist"

with as_file(client_root) as client_dir:
    # fmt: off
    server = HttpControlledServer(available_games)\
        .add_client(heartbeat)\
        .add_client(web.static('/web', str(client_dir)))\
        .add_client(web.get('/', lambda request: web.Response(status=http.HTTPStatus.PERMANENT_REDIRECT, headers={'Location': '/web/index.html'})))
    # fmt: on
    if args.start_game is not None:
        from game_anywhere.network.game_room import Lobby

        room = Lobby.open_game_owning_lobby(
            game_description=args.start_game, server=server
        )
        server.new_room(room)
    server.nt_start(
        port=args.port,
        print=lambda message: print(message.replace("0.0.0.0", "localhost")),
    )
