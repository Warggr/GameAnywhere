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


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", default=8080, dest="port", type=int)
args = parser.parse_args()

available_games = load_games()

client_root = files("game_anywhere") / "client"

with as_file(client_root) as client_dir:
    # fmt: off
    HttpControlledServer(available_games)\
        .add_client(heartbeat)\
        .add_client(web.static('/web', str(client_dir)))\
        .add_client(web.get('/', lambda request: web.Response(status=http.HTTPStatus.PERMANENT_REDIRECT, headers={'Location': '/web/index.html'}))) \
        .nt_start(port=args.port, print=lambda message: print(message.replace("0.0.0.0", "localhost")))
    # fmt: on
