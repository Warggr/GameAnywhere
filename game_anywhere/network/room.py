from game_anywhere.core.agent import AgentId
from .spectator import Session, Spectator
from itertools import chain
from typing import Iterable, Awaitable, Optional
from aiohttp import web
import asyncio
from .async_resource import AsyncResource

SeatId = int
Username = str


class ServerRoom(AsyncResource):
    class CouldntConnect(Exception):
        pass

    @staticmethod
    def get_request_username(request: web.Request) -> str:
        try:
            return request.cookies['username']
        except KeyError:
            return request.query['username'] + ' (Guest)'

    def __init__(self, server: "Server", greeter_message="Welcome to the room!"):
        self.server = server
        self.greeter_message = (
            greeter_message  # The message that will be sent to every new spectator
        )
        self.spectators: list[Spectator] = []
        self.sessions: dict[SeatId, Session] = {}
        self.session_id_to_username: dict[SeatId, Username] = {}

    def __del__(self):
        # as part of their closing, all sessions should have set themselves to FREE and all spectators should have deleted themselves
        if not hasattr(self, 'spectators') and not hasattr(self, 'sessions'):
            # Maybe the object is not even initialized yet
            return
        assert len(self.spectators) == 0
        for session in self.sessions.values():
            assert session.state in [
                Spectator.state.INTERRUPTED_BY_SERVER,
                Spectator.state.FREE,
            ]

    def create_session(self, agent_id: AgentId) -> Session:
        assert agent_id not in self.sessions
        session = Session(agent_id, self)
        self.sessions[agent_id] = session
        return session

    # signals the game that it should end as soon as possible.
    def nt_interrupt(self):
        for spectator in self.get_spectators_and_sessions():
            spectator.interrupt()

    async def nt_close(self) -> None:
        # some sessions are probably still waiting for reconnection, let's wait until they all end
        spectators_still_running = [
            spectator.run_handle
            for spectator in self.get_spectators_and_sessions()
            if spectator.run_handle is not None
        ]
        if spectators_still_running:
            await asyncio.wait(spectators_still_running)
        self.server.delete_room(self)

    def report_afk(self, spectator: Spectator):
        assert spectator.state in [
            Spectator.state.FREE,
            Spectator.state.INTERRUPTED_BY_SERVER,
        ]
        if type(spectator) == Session:
            pass
        else:
            self.spectators.remove(spectator)

    def send(self, message: str) -> None:
        for spectator in self.get_spectators_and_sessions():
            spectator.send(message)

    def get_spectators_and_sessions(self) -> Iterable[Spectator]:
        return chain(self.sessions.values(), self.spectators)

    # this is a class method, and the middleware takes care of binding it to
    # the proper instance. See @class Server.
    @classmethod
    def http_interface(cls, instance_dispatcher) -> web.Application:
        router = web.Application(middlewares=[instance_dispatcher])
        router.add_routes(
            [
                # see @class Server for an explanation of parameter {roomId}
                web.get(r"/{roomId:\d+}/ws/{seat:\d+}", cls.nt_connect_session),
                web.get(r"/{roomId:\d+}/ws/watch", cls.nt_add_spectator),
            ]
        )
        return router

    async def nt_add_spectator(self, request: web.Request):
        spectator = Spectator(self)
        self.spectators.append(spectator)
        return await self.nt_handle_websocket(request, spectator)

    async def nt_connect_session(self, request: web.Request):
        try:
            session_id = SeatId(request.match_info["seat"])
            session = self.sessions[session_id]
        except (KeyError, ValueError):
            raise web.HTTPNotFound(text="No such session expected")

        if session_id in self.session_id_to_username:
            if self.get_request_username(request) != self.session_id_to_username[session_id]:
                raise web.HTTPForbidden(text="Session already taken")
        else:
            self.session_id_to_username[session_id] = self.get_request_username(request)

        # this is done on the network thread, which is single-threaded.
        # There can be no race condition between reading session.state and claiming the session
        if session.state != Session.state.FREE:
            raise web.HTTPNotFound(text="Session already taken")
        return await self.nt_handle_websocket(request, session)

    async def nt_handle_websocket(self, request: web.Request, spectator: Spectator):
        ws = web.WebSocketResponse()
        try:
            await spectator.on_connect(request, ws)
            if type(spectator) != Session:
                await spectator.send(self.greeter_message)
            await spectator.run()
            # the websocket is closed as soon as the method execution finishes, i.e. now
        except asyncio.CancelledError:  # cancelled by server, or the game ended
            pass
        return ws
