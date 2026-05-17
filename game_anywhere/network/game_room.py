from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from itertools import count
from threading import Thread
from typing import TYPE_CHECKING

from aiohttp import http, web

from .room import ServerRoom

if TYPE_CHECKING:
    from typing import Sequence

    from game_anywhere.agents.descriptors import GameDescriptor
    from game_anywhere.core import Game, GameSummary

    from .room import SeatId, Username
    from .server import Server


@dataclass
class GameMetadata:
    game: type["Game"]
    players: dict["SeatId", "Username"]
    started: datetime
    ended: datetime
    summary: "GameSummary | None"


class BaseGameRoom(ServerRoom):
    def __init__(self, game: Game, server: Server, *args, **kwargs):
        super().__init__(server, *args, **kwargs)
        self.game = game

    # override
    @classmethod
    def http_interface(cls, *args, **kwargs):
        router = super().http_interface(*args, **kwargs)
        router.add_routes(
            [
                # see @class Server for an explanation of parameter {roomId}
                web.get(r"/{roomId:\d+}/html", cls.http_get_html_view),
            ]
        )
        return router

    async def http_get_html_view(self, request: web.Request) -> web.Response:
        username = self.get_request_username(request)
        try:
            session_id = request.query["seat"]
        except KeyError as err:
            raise web.HTTPUnauthorized(text="Please provide a seat.") from err
        if session_id == "watch":
            html = self.game.html(viewer_id=None)
        else:
            try:
                session_id = int(session_id)
            except ValueError as err:
                raise web.HTTPBadRequest(text="Session is not an integer") from err
            if session_id not in self.sessions:
                raise web.HTTPUnauthorized(text=f"Session {session_id} not found")

            old_username = self.reserved_sessions.get(session_id, None)
            if old_username is not None and old_username != username:
                raise web.HTTPForbidden(text="Session not owned by authenticated user")
            html = self.game.get_html_for_agent_ref(self.sessions[session_id])
        return web.Response(body=str(html), content_type="text/html")


class Lobby(ServerRoom):
    def __init__(
        self,
        game_type: type[Game],
        expected: Sequence[int] = (),
        game_description: GameDescriptor | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
            greeter_message=lambda: [
                {"op": "replace", "path": "", "value": self._serialized_state()}
            ],
        )
        self.session_ids = count()
        self.game_type = game_type
        self.finalized = False
        self.game_thread = None
        # TODO: at that point we could split it into a Lobby and a GameOwningLobby
        if game_description is not None:
            self.expected = set()
            self.game_promise = game_description.start_initialization(server_room=self)
            # the NetworkAgents should have registered themselves
            assert self.expected == set(expected)
        else:
            self.expected = set(expected)

    # override
    @classmethod
    def http_interface(cls, instance_dispatcher):
        router = super().http_interface(instance_dispatcher)

        @web.middleware
        def close_lobby_once_game_is_started(
            request: web.Request, handler: web.RequestHandler, self: Lobby | None = None
        ):
            if self is not None and self.finalized:
                raise web.HTTPNotFound(
                    text=f"Lobby {request.match_info['room']} is already closed"
                )
            return handler(self=self, request=request)

        router.middlewares.append(close_lobby_once_game_is_started)
        router.add_routes(
            [
                web.get(r"/{roomId:\d+}/", cls.http_list_connected),
                web.get(r"/{roomId:\d+}/enter", cls.http_enter_lobby),
                web.post(r"/{roomId:\d+}/finalize", cls.http_finalize_player_list),
            ]
        )
        return router

    def _serialized_state(self) -> dict:
        return {
            "spectators": len(self.spectators),
            "seats": {
                key: {"username": value.username, "state": value.state.name}
                for key, value in self.sessions.items()
            },
            "num_players": {"const": len(self.expected)},
            "game": self.game_type.__name__,
        }

    async def http_list_connected(self, request: web.Request) -> web.Response:
        return web.json_response(self._serialized_state())

    async def http_enter_lobby(self, request: web.Request):
        new_id = next(self.session_ids)
        return web.Response(
            status=http.HTTPStatus.CREATED, headers={"Location": f"ws/{new_id}"}
        )

    # override
    async def nt_connect_session(self, request: web.Request):
        seat_id = SeatId(request.match_info["seat"])
        if seat_id not in self.sessions:
            session = self.create_session(seat_id=seat_id)
            self.server.loop.create_task(
                self.log_event(
                    {
                        "op": "add",
                        "path": f"/seats/{seat_id}",
                        "value": {"username": None, "state": session.state.name},
                    }
                )
            )
        return await super().nt_connect_session(request)

    async def http_finalize_player_list(self, request: web.Request) -> web.Response:
        assert self.game_promise is not None

        if len(self.sessions) != len(self.expected):
            raise web.HTTPConflict(
                text=f"Wrong number of players: {len(self.sessions)}, {len(self.expected)} expected"
            )

        for i, (session, promise_i) in enumerate(
            zip(self.sessions.values(), self.expected, strict=True)
        ):
            promise = self.game_promise.agent_promises[promise_i]
            _self, _i = promise
            assert _self is self and _i == i
            self.game_promise.agent_promises[promise_i] = session
        assert all(
            [
                descriptor.is_initialized(promise)
                for descriptor, promise in zip(
                    self.game_promise.agent_descriptors,
                    self.game_promise.agent_promises,
                    strict=True,
                )
            ]
        )
        game = self.game_promise.resolve()

        self.game_thread = Thread(target=self.run_game_thread, args=(game,))
        self.game_thread.start()
        self.nt_finalize(game)
        return web.Response(status=http.HTTPStatus.CREATED)

    def nt_finalize(self, game: Game):
        new_room = BaseGameRoom(game, self.server)
        new_room_id, _ = self.server.new_room(new_room)
        self.server.loop.create_task(self.transfer_sessions(new_room))

    async def transfer_sessions(self, other_room: ServerRoom):
        await self.log_event({"op": "finalize", "location": f"/r/{other_room.room_id}"})

        other_room.sessions = self.sessions
        self.sessions = {}
        other_room.reserved_sessions = self.reserved_sessions
        self.reserved_sessions = {}
        for session in other_room.sessions.values():
            session.room = other_room

    def run_game_thread(self, game: Game):
        started = datetime.now()

        summary = game.play_game()

        self.server.loop.call_soon_threadsafe(self.nt_interrupt)

        players = {
            agent_id: agent.name
            for agent_id, agent in zip(game.agent_ids, game.agents, strict=True)
        }
        metadata = GameMetadata(
            game=self.game_type,
            players=players,
            started=started,
            ended=datetime.now(),
            summary=summary,
        )
        self.server.log_game_summary(metadata)
        asyncio.run_coroutine_threadsafe(self.nt_close(), loop=self.server.loop)

    # override
    async def nt_close(self):
        # print("nt_closing GameRoom…")
        # first close the spectators
        await super().nt_close()
        # print("Everything closed, now waiting for the game thread to end…")
        # then wait for the game to end (with no one connected, it can't take long)
        if self.game_thread is not None:
            try:
                self.game_thread.join()
                # print("Game thread ended")
            except Exception:
                print("Game thread ended with an exception")
