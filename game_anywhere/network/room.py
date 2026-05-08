import asyncio
from itertools import chain
from typing import TYPE_CHECKING, Generic, Iterable, TypeVar

from aiohttp import web

from .async_resource import AsyncResource
from .spectator import Session, Spectator

if TYPE_CHECKING:
    from .server import Server

SeatId = int
Username = str


ServerType = TypeVar("ServerType", bound="Server")


class ServerRoom(AsyncResource, Generic[ServerType]):
    class CouldntConnect(Exception):
        pass

    @staticmethod
    def get_request_username(request: web.Request) -> str | None:
        return request.cookies.get("username", None)

    def __init__(self, server: ServerType, greeter_message="Welcome to the room!"):
        """
        Args:
            greeter_message: The message that will be sent to every new spectator
        """
        self.server = server
        self.greeter_message = greeter_message
        self.spectators: list[Spectator] = []
        self.sessions: dict[SeatId, Session] = {}
        self.reserved_sessions: dict[SeatId, Username] = {}

    def __del__(self):
        # as part of their closing, all sessions should have set themselves to FREE and all spectators should have deleted themselves
        if not hasattr(self, "spectators") and not hasattr(self, "sessions"):
            # Maybe the object is not even initialized yet
            return
        assert len(self.spectators) == 0
        for session in self.sessions.values():
            assert session.state in [
                Spectator.State.INTERRUPTED_BY_SERVER,
                Spectator.State.FREE,
            ]

    @property
    def room_id(self) -> int:
        ((room_id, _this),) = filter(lambda i: i[1] is self, self.server.rooms.items())
        return room_id

    def create_session(self, seat_id: SeatId | None = None) -> Session:
        if seat_id is None:
            seat_id = max(self.sessions.keys(), default=0) + 1
        assert seat_id not in self.sessions
        session = Session(self)
        self.sessions[seat_id] = session
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
            Spectator.State.FREE,
            Spectator.State.INTERRUPTED_BY_SERVER,
        ]
        if type(spectator) is Session:
            pass
        else:
            self.spectators.remove(spectator)
            self.server.log_event(
                {
                    "op": "replace",
                    "key": f"/{self.room_id}/spectators",
                    "value": len(self.spectators),
                }
            )

    def send(self, message: str) -> None:
        for spectator in self.get_spectators_and_sessions():
            spectator.send_sync(message)

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
        self.server.log_event(
            {
                "op": "replace",
                "key": f"/r/{self.room_id}/spectators",
                "value": len(self.spectators),
            }
        )
        return await self.nt_handle_websocket(request, spectator)

    async def nt_connect_session(self, request: web.Request):
        try:
            session_id = SeatId(request.match_info["seat"])
            session = self.sessions[session_id]
        except (KeyError, ValueError) as err:
            raise web.HTTPNotFound(text="No such session expected") from err

        new_name_or_none = self.get_request_username(request)
        match (
            new_name_or_none,
            self.reserved_sessions.get(session_id),
        ):
            case (None, None):
                pass
            case (new_name, None):
                self.reserved_sessions[session_id] = new_name
            case (new_name_or_none, old_name):
                if new_name_or_none != old_name:
                    raise web.HTTPForbidden(text="Session already taken")

        # this is done on the network thread, which is single-threaded.
        # There can be no race condition between reading session.state and claiming the session
        if session.state != Session.State.FREE:
            raise web.HTTPNotFound(text="Session already taken")
        username = request.query.get("username", None) or new_name_or_none
        if username is not None:
            session.username = username
        return await self.nt_handle_websocket(request, session)

    async def nt_handle_websocket(self, request: web.Request, spectator: Spectator):
        ws = web.WebSocketResponse()
        try:
            await spectator.on_connect(request, ws)
            if type(spectator) is not Session:
                await spectator.send(self.greeter_message)
            await spectator.run()
            # the websocket is closed as soon as the method execution finishes, i.e. now
        except asyncio.CancelledError:  # cancelled by server, or the game ended
            pass
        return ws
