from asyncio.queues import Queue
from aiohttp import web
from aiohttp import http
from aiohttp_sse import sse_response, EventSourceResponse
from .server import Server
from game_anywhere.agents.parse_descriptors import parse_game_descriptor
from .game_room import GameRoom
import json
import traceback
import sys


def json_encode_server_room(room: "ServerRoom"):
    return {
        "spectators": len(room.spectators),
        "seats": {key: str(value.state) for key, value in room.sessions.items()},
    }


class HttpControlledServer(Server):
    SERVER_CLOSED_DUMMY_MSG = None

    def __init__(self, available_games: dict[str, "Game"]):
        super().__init__(RoomClass=GameRoom)
        self.available_games = available_games
        self.app.add_routes(
            [
                web.post("/room", self.http_create_room),
                web.get("/room/list", self.http_get_rooms),
                web.get("/room/list/watch", self.http_watch_rooms),
                web.options("/room", self.http_options_create_room),
                web.post("/login", self.http_login),
            ]
        )
        self.event_queues: list[Queue] = []

    async def http_create_room(self, request: web.Request) -> web.Response:
        default_description = {"agents": "network"}
        try:
            game_description = parse_game_descriptor(
                await request.json(), self.available_games, default_description
            )
        except (KeyError, json.JSONDecodeError) as err:
            raise web.HTTPBadRequest(text=repr(err))
        try:
            room_id, room = self.new_room(room=GameRoom(game_description, server=self))
        except Exception as ex:
            traceback.print_exception(ex, file=sys.stderr)
            raise web.HTTPBadRequest(text=str(ex))
        self.log_event(
            json.dumps(
                {"add": {"key": room_id, "value": room}},
                default=json_encode_server_room,
            )
        )
        return web.json_response(room_id, status=http.HTTPStatus.CREATED)

    def http_get_rooms(self, request: web.Request) -> web.Response:
        return web.json_response(
            text=json.dumps(self.rooms, default=json_encode_server_room)
        )

    async def http_watch_rooms(self, request: web.Request) -> web.StreamResponse:
        queue = Queue()
        self.event_queues.append(queue)
        try:
            async with sse_response(request) as channel:
                while True:
                    data = await queue.get()
                    if data == HttpControlledServer.SERVER_CLOSED_DUMMY_MSG:
                        break
                    await channel.send(data)
        except ConnectionResetError:
            pass
        self.event_queues.remove(queue)
        return channel

    def http_options_create_room(self, request: web.Request) -> web.Response:
        return web.json_response(
            {"enum": list(self.available_games.keys())}, headers={"Allow": "POST"}
        )

    async def http_login(self, request: web.Request) -> web.Response:
        login_data = await request.json()
        username = login_data['username']
        return web.Response(status=http.HTTPStatus.NO_CONTENT, headers={'Set-Cookie': f'username={username}'})

    def log_event(self, data):
        for queue in self.event_queues:
            queue.put_nowait(data)

    # override
    def nt_interrupt(self):
        super().nt_interrupt()
        self.log_event(HttpControlledServer.SERVER_CLOSED_DUMMY_MSG)
