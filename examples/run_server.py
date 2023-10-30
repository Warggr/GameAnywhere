import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append( str(PROJECT_ROOT.parent) )

import argparse
from game_anywhere.src.network.http_controlled_server import HttpControlledServer
from game_anywhere.src.network.router import heartbeat
from aiohttp import web, http
from chess import Chess
from tic_tac_toe import TicTacToe

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', default=8080, dest='port', type=int)
args = parser.parse_args()

available_games={ "TicTacToe": TicTacToe, "Chess": Chess }

HttpControlledServer(available_games)\
    .add_client(heartbeat)\
    .add_client(web.static('/web', PROJECT_ROOT / 'client'))\
    .add_client(web.get('/', lambda request: web.Response(status=http.http.HTTPStatus.PERMANENT_REDIRECT, headers={'Location': '/web/index.html'}))) \
    .nt_start(port=args.port)
