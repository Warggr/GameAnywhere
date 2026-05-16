from __future__ import annotations

import json
from asyncio.queues import Queue
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from aiohttp import http, web
from aiohttp_sse import sse_response

from game_anywhere.agents.descriptors import GameDescriptor
from game_anywhere.agents.network_agent import NetworkAgent
from game_anywhere.ui.custom_components import get_registered_component

from .game_room import GameRoom
from .server import Server

if TYPE_CHECKING:
    from game_anywhere.core import Game, GameSummary

    from .game_room import GameMetadata
    from .room import ServerRoom


def json_encode_server_room(room: "ServerRoom") -> dict:
    return {
        "spectators": len(room.spectators),
        "seats": {
            key: {"username": value.username, "state": value.state.name}
            for key, value in room.sessions.items()
        },
    }


class JsonPatch(TypedDict):
    op: Literal["add", "replace", "remove"]
    key: str
    value: Any


ServerEvent = JsonPatch


def json_encode_game_summary(summary: "GameSummary") -> dict:
    return {
        "winner": summary.get_winner(),
    }


def json_encode_game_metadata(metadata: "GameMetadata") -> dict:
    result = asdict(metadata)
    result["game"] = result["game"].__name__
    result["started"] = metadata.started.timestamp()
    result["ended"] = metadata.ended.timestamp()
    if result["summary"] is not None:
        result["summary"] = json_encode_game_summary(result["summary"])
    else:
        result["summary"] = None
    return result


class HttpControlledServer(Server):
    SERVER_CLOSED_DUMMY_MSG = None

    def __init__(self, available_games: dict[str, "Game"]):
        asset_dirs = {}
        for g in available_games.values():
            asset_dir = g.get_asset_dir()
            if asset_dir is not None:
                asset_dirs[g.__name__] = asset_dir
        super().__init__(
            RoomClass=GameRoom,
            assets=asset_dirs,
            dynamic_assets=get_registered_component,
        )
        self.available_games = available_games
        # Warning: The server routes are /room, the GameRoom routes are /r.
        # (even though POST /room, GET /room/list, GET /room/1 would be more idiomatic)
        # This allows the router to differentiate them.
        self.app.add_routes(
            [
                web.post("/room", self.http_create_room),
                web.get("/room/list", self.http_get_rooms),
                web.get("/watch", self.http_watch_server),
                web.options("/room", self.http_options_create_room),
                web.get("/logs/list", self.http_list_games),
                web.get(r"/logs/{gameId:\d+}", self.http_get_game),
                web.post("/login", self.http_login),
            ]
        )
        self.event_queues: list[Queue] = []
        self.games: list["GameMetadata"] = []

    async def http_create_room(self, request: web.Request) -> web.Response:
        body = await request.json()
        try:
            game_type = self.available_games[body.pop("_id")]
            num_players, game_kwargs = game_type.parse_config(**body)
            game_description = GameDescriptor(
                game_type,
                [NetworkAgent.Descriptor() for _ in range(num_players)],
                **game_kwargs,
            )
            room_id, room = self.new_room(room=GameRoom(game_description, server=self))
        except Exception as ex:
            raise web.HTTPBadRequest(text=str(ex)) from ex
        self.log_event(
            {
                "op": "add",
                "key": f"/r/{room_id}",
                "value": json_encode_server_room(room),
            },
        )
        return web.json_response(room_id, status=http.HTTPStatus.CREATED)

    def http_get_rooms(self, request: web.Request) -> web.Response:
        return web.json_response(
            text=json.dumps(self.rooms, default=json_encode_server_room)
        )

    async def http_watch_server(self, request: web.Request) -> web.StreamResponse:
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
        defs = {}
        for game_name, game in self.available_games.items():
            schema = game.CONFIG_SCHEMA.copy()
            schema["type"] = "object"
            schema["properties"] = schema["properties"].copy()
            schema["properties"]["_id"] = {"const": game_name}
            schema["required"] = schema.get("required", ["_num_players"])
            schema["required"].append("_id")
            defs[game_name] = schema
        schema = {
            "$id": "/schema",
            "oneOf": [{"$ref": "#/$defs/" + val} for val in defs],
            "$defs": defs,
        }
        return web.json_response(schema, headers={"Allow": "POST"})

    async def http_login(self, request: web.Request) -> web.Response:
        login_data = await request.json()
        username = login_data["username"]
        return web.Response(
            status=http.HTTPStatus.NO_CONTENT,
            headers={"Set-Cookie": f"username={username}"},
        )

    def http_list_games(self, request: web.Request) -> web.Response:
        return web.json_response(
            text=json.dumps([json_encode_game_metadata(game) for game in self.games])
        )

    def http_get_game(self, request: web.Request) -> web.Response:
        try:
            idx = int(request.match_info["gameId"])
        except ValueError as err:
            raise web.HTTPBadRequest(text="gameId is not an int") from err
        return web.json_response(
            text=json.dumps(self.games[idx], default=json_encode_game_metadata)
        )

    def log_game_summary(self, metadata: "GameMetadata"):
        # This is called on the network thread.
        self.games.append(metadata)
        self.log_event(
            {
                "op": "add",
                "key": f"/s/{len(self.games)}",
                "value": json_encode_game_metadata(metadata),
            }
        )

    def log_event(self, event: ServerEvent):
        event_str = json.dumps([event])  # JSON patch has to be a list of patches
        for queue in self.event_queues:
            queue.put_nowait(event_str)

    # override
    def nt_interrupt(self):
        super().nt_interrupt()
        for queue in self.event_queues:
            queue.put_nowait(HttpControlledServer.SERVER_CLOSED_DUMMY_MSG)
