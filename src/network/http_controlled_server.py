from aiohttp import web
from aiohttp import http
from .server import Server
from game_anywhere.src.agents.parse_descriptors import parse_game_descriptor
from .game_room import GameRoom
import json
from typing import Dict

def json_encode_server_room(room : 'ServerRoom'):
    return {
        'spectators': len(room.spectators),
        'seats': { key: str(value.state) for key, value in room.sessions.items() }
    }

class HttpControlledServer(Server):
    def __init__(self, available_games: Dict[str, 'Game']):
        super().__init__(RoomClass=GameRoom)
        self.available_games = available_games
        self.app.add_routes([
            web.post('/room', self.http_create_room),
            web.get('/room/list', self.http_get_rooms),
            web.options('/room', self.http_options_create_room),
        ])

    async def http_create_room(self, request : web.Request) -> web.Response:
        try:
            game_description = parse_game_descriptor(await request.json(), self.available_games)
        except (KeyError, json.JSONDecodeError) as err:
            raise web.HTTPBadRequest(text=repr(err))
        room_id, room = self.new_room(room=GameRoom(game_description, server=self))
        return web.json_response(room_id, status=http.HTTPStatus.CREATED)

    def http_get_rooms(self, request : web.Request) -> web.Response:
        return web.json_response(text=json.dumps(self.rooms, default=json_encode_server_room))

    def http_options_create_room(self, request : web.Request) -> web.Response:
        return web.json_response({
            "enum": list(self.available_games.keys())
        }, headers={'Allow': 'POST'})
