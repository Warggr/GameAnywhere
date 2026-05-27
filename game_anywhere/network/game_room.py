from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from threading import Thread
from typing import TYPE_CHECKING, Sequence

from aiohttp import web

from .room import ServerRoom
from .spectator import Spectator

if TYPE_CHECKING:
    from typing import Sequence

    from game_anywhere.agents.descriptors import GameDescriptor
    from game_anywhere.core import Game, GameSummary

    from .room import SeatId, Username
    from .server import Server
    from .spectator import Session


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
            greeter_message=lambda spectator: {
                "type": "room_update",
                "patch": [
                    {
                        "op": "replace",
                        "path": "",
                        "value": self._serialized_state()
                        | {
                            "you": {
                                "spectator_index": self.spectators.index(spectator),
                                "name": self.spectator_names[spectator],
                            }
                        },
                    }
                ],
            },
        )
        self.spectator_names = {}
        self.game_type = game_type
        self.finalized = asyncio.Event()
        self.game_thread = None
        # TODO: at that point we could split it into a Lobby and a GameOwningLobby
        if game_description is not None:
            self.expected = set()
            self.game_promise = game_description.start_initialization(server_room=self)
            # the NetworkAgents should have registered themselves
            assert self.expected == set(expected)
        else:
            self.expected = set(expected)
            self.game_promise = None

    # override
    @classmethod
    def http_interface(cls, instance_dispatcher):
        router = super().http_interface(instance_dispatcher)

        @web.middleware
        async def close_lobby_once_game_is_started(
            request: web.Request, handler: web.RequestHandler, self: Lobby | None = None
        ):
            if request.match_info.http_exception is not None:
                return await handler(request)
            if self is not None and self.finalized.is_set():
                raise web.HTTPNotFound(
                    text=f"Lobby {request.match_info['roomId']} is already closed"
                )
            return await handler(self=self, request=request)

        router.middlewares.append(close_lobby_once_game_is_started)
        router.add_routes(
            [
                web.get(r"/{roomId:\d+}/", cls.http_list_connected),
            ]
        )
        return router

    def _serialized_state(self) -> dict:
        return {
            "spectators": [
                {"name": self.spectator_names[spec]} for spec in self.spectators
            ],
            "num_players": {"const": len(self.expected)},
            "game": self.game_type.__name__,
        }

    async def http_list_connected(self, request: web.Request) -> web.Response:
        return web.json_response(self._serialized_state())

    # override
    async def nt_connect_session(self, request: web.Request):
        raise web.HTTPBadRequest(text="Lobby doesn't take Sessions")

    def login_channel(self, message, spectator):
        if message["op"] == "replace" and message["path"] == "/name":
            new_name = message["value"]
            if not isinstance(new_name, str) or not new_name.strip():
                raise ValueError("Name must be a non-empty string")
            if any(
                new_name == taken_name for taken_name in self.spectator_names.values()
            ):
                raise ValueError("Username already taken")
            new_name = new_name.strip()
            self.spectator_names[spectator] = new_name
            self.log_event_nosync(
                {
                    "op": "replace",
                    "path": f"/spectators/{self.spectators.index(spectator)}/name",
                    "value": new_name,
                }
            )
        elif message["op"] == "finalize":
            self.finalize_player_list()
        else:
            raise ValueError("Unrecognized message")

    async def nt_report_afk(self, spectator: Spectator):
        await super().nt_report_afk(spectator)
        self.spectator_names.pop(spectator, None)

    # override
    async def nt_add_spectator(self, request: web.Request):
        # Logging only to previous agents (the new spectator will receive the full state as a greeter_message)
        username = request.query.get("username", None)
        if username is None:
            username = "guest"
        if any(username == taken_name for taken_name in self.spectator_names.values()):
            original_username = username
            i = 0
            while True:
                i += 1
                username = original_username + str(i)
                if any(
                    username == taken_name
                    for taken_name in self.spectator_names.values()
                ):
                    continue
                else:
                    break

        await self.log_event(
            {
                "op": "add",
                "path": "/spectators/-",
                "value": {"name": username},
            }
        )
        spectator = Spectator(self)
        self.spectators.append(spectator)
        self.spectator_names[spectator] = username
        spectator.add_channel(
            "players", partial(self.login_channel, spectator=spectator)
        )
        return await self.nt_handle_websocket(request, spectator)

    def finalize_player_list(self):
        if len(self.spectators) != len(self.expected):
            raise ValueError(
                f"Wrong number of players: {len(self.sessions)}, {len(self.expected)} expected"
            )

        self.finalized.set()
        assert self.finalized.is_set()
        if self.game_promise is not None:
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

            self.game_thread = Thread(target=self.run_game_thread)
            self.game_thread.start()

    def gt_finalize(self, game: Game):
        self.new_room = BaseGameRoom(game, self.server)
        new_room_id, _ = self.server.new_room(self.new_room)
        self.server.loop.create_task(self.transfer_sessions(self.new_room))

    async def transfer_sessions(self, other_room: ServerRoom):
        assert not other_room.reserved_sessions and not other_room.sessions
        # TODO: if spectator is reserved, reserve it on the other_room
        for seatid, session in self.sessions.items():
            other_room.sessions[seatid] = session
            session.room = other_room

        await asyncio.gather(
            *(
                spectator.send(
                    {"type": "finalize", "location": f"/r/{other_room.room_id}"}
                )
                for spectator in self.get_spectators_and_sessions()
            )
        )
        self.sessions = {}

    def run_game_thread(self):
        game = self.game_promise.resolve()
        self.gt_finalize(game)

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

    def wait_for_session_sync(self, i: int) -> Session:
        from threading import Event

        event = Event()

        async def _nt_wait(callback):
            assert self.finalized.is_set()
            await self.finalized.wait()
            event.set()

        asyncio.run_coroutine_threadsafe(_nt_wait(event), self.server.loop)
        event.wait()
        assert self.finalized.is_set()
        session = self.create_session()
        session.ws = self.spectators[i].ws
        session.send_sync({"type": "finalize", "seat_id": session.seat_id})
        session.username = self.spectator_names[self.spectators[i]]
        return session
