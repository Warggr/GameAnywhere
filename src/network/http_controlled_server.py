from aiohttp import web
from aiohttp.http import http
from .server import Server
from game_anywhere.src.agents.parse_descriptors import parse_game_descriptor
from .room import ServerRoom, GameRoom
import json

def json_encode_server_room(room : ServerRoom):
    return {
        'spectators': len(room.spectators),
        'seats': { key: str(value.state) for key, value in room.sessions.items() }
    }

class HttpControlledServer(Server):
    def __init__(self):
        super().__init__(RoomClass=GameRoom)
        self.app.add_routes([
            web.post('/room', self.http_create_room),
            web.get('/room/list', self.http_get_rooms),
        ])

    async def http_create_room(self, request : web.Request) -> web.Response:
        game_description = parse_game_descriptor(await request.json())
        game = game_description.create()
        room_id, room = self.new_room(room=GameRoom(game))
        return web.json_response(room_id, status=http.HTTPStatus.CREATED)

    def http_get_rooms(self, request : web.Request) -> web.Response:
        return web.json_response(text=json.dumps(self.rooms, default=json_encode_server_room))
