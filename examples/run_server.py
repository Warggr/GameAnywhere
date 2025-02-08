import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

import argparse
from game_anywhere.network.http_controlled_server import HttpControlledServer
from game_anywhere.network.router import heartbeat
from aiohttp import web, http
from chess import Chess
from tic_tac_toe import TicTacToe
from poker import Poker
from werewolves import Werewolves
from hanabi import Hanabi

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", default=8080, dest="port", type=int)
args = parser.parse_args()

available_games = {
    "TicTacToe": TicTacToe,
    "Chess": Chess,
    "Poker": Poker,
    "Werewolves": Werewolves,
    "Hanabi": Hanabi,
}

# fmt: off
HttpControlledServer(available_games)\
    .add_client(heartbeat)\
    .add_client(web.static('/web', PROJECT_ROOT / 'client'))\
    .add_client(web.get('/', lambda request: web.Response(status=http.HTTPStatus.PERMANENT_REDIRECT, headers={'Location': '/web/index.html'}))) \
    .nt_start(port=args.port, print=lambda message:print(message.replace("0.0.0.0", "localhost")))
# fmt: on
