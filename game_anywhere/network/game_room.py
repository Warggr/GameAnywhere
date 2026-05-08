import asyncio
from dataclasses import dataclass
from datetime import datetime
from threading import Thread
from typing import TYPE_CHECKING

from aiohttp import web

from game_anywhere.agents.descriptors import GamePromise

from .room import ServerRoom

if TYPE_CHECKING:
    from game_anywhere.agents.descriptors import GameDescriptor
    from game_anywhere.core import Game, GameSummary

    from .http_controlled_server import HttpControlledServer
    from .room import SeatId, Username


@dataclass
class GameMetadata:
    game: type["Game"]
    players: dict["SeatId", "Username"]
    started: datetime
    ended: datetime
    summary: "GameSummary | None"


class BaseGameRoom(ServerRoom["HttpControlledServer"]):
    def __init__(self, game: "Game", server: "HttpControlledServer", *args, **kwargs):
        super().__init__(server, *args, **kwargs)
        self.game = game
        self.started = datetime.now()

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
        try:
            username = self.get_request_username(request) or request.query["username"]
            session_id = request.query["seat"]
        except KeyError as err:
            raise web.HTTPUnauthorized(
                text=f"Please provide a username and seat (missing: {err})"
            ) from err
        if session_id == "watch":
            html = self.game.html(viewer_id=None)
        else:
            try:
                session_id = int(session_id)
            except ValueError as err:
                raise web.HTTPBadRequest(text="Session is not an integer") from err
            if session_id not in self.sessions:
                raise web.HTTPUnauthorized(text=f"Session {session_id} not found")

            if self.sessions[session_id].username != username:
                raise web.HTTPForbidden(text="Session not owned by authenticated user")
            html = self.game.get_html_for_agent_ref(self.sessions[session_id])
        return web.Response(body=str(html), content_type="text/html")


class GameRoom(BaseGameRoom):
    """Provides its own game, which is launched on another thread from a GameDescriptor"""

    def __init__(self, game_descriptor: "GameDescriptor", *args, **kwargs):
        super().__init__(*args, game=game_descriptor.game, **kwargs)
        promise = game_descriptor.start_initialization(server_room=self)
        self.game_thread = Thread(target=self.run_game_thread, args=(promise,))
        self.game_thread.start()

    def run_game_thread(
        self,
        game_promise: GamePromise,
    ):
        # print("Starting game thread, waiting for agents…")
        self.game = game_promise.resolve()
        # print("…Agents connected")
        summary = self.game.play_game()
        # print("Game ended, interrupting agents")
        self.server.loop.call_soon_threadsafe(self.nt_interrupt)
        # print("Game ended, scheduling self.nt_close()")
        asyncio.run_coroutine_threadsafe(
            self.nt_close(summary=summary), loop=self.server.loop
        )

    # override
    async def nt_close(self, summary: "GameSummary | None" = None):
        # print("nt_closing GameRoom…")
        # first close the spectators
        players = {
            agent_id: agent.name
            for agent_id, agent in zip(
                self.game.agent_ids, self.game.agents, strict=True
            )
        }
        metadata = GameMetadata(
            game=type(self.game),
            players=players,
            started=self.started,
            ended=datetime.now(),
            summary=summary,
        )
        self.server.log_game_summary(metadata)
        await super().nt_close()
        # print("Everything closed, now waiting for the game thread to end…")
        # then wait for the game to end (with no one connected, it can't take long)
        try:
            self.game_thread.join()
            # print("Game thread ended")
        except Exception:
            print("Game thread ended with an exception")
