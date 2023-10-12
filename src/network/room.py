from game_anywhere.include.core.agent import AgentId
from .spectator import Session, Spectator
from itertools import chain
from typing import Iterable, Dict, List, Awaitable
from aiohttp import web
import asyncio
from .async_resource import AsyncResource

SeatId = int

class ServerRoom(AsyncResource):
    class CouldntConnect(Exception):
        pass

    def __init__(self, server : 'Server', greeter_message='Welcome to the room!'):
        self.server = server
        self.greeter_message = greeter_message #The message that will be sent to every new spectator
        self.spectators : List[Spectator] = []
        self.sessions : Dict[SeatId, Session] = {}

    def __del__(self):
        # as part of their closing, all sessions should have set themselves to FREE and all spectators should have deleted themselves
        assert len(self.spectators) == 0
        for session in self.sessions.values():
            assert session.state in [ Spectator.state.INTERRUPTED_BY_SERVER, Spectator.state.FREE ]

    def create_session(self, agent_id: AgentId) -> Session:
        assert agent_id not in self.sessions
        session = Session( agent_id, self )
        self.sessions[agent_id] = session
        return session

    def add_spectator(self, request, session_id : int = 0) -> Spectator:
        if session_id != 0:
            if session_id not in self.sessions:
                raise ServerRoom.CouldntConnect('No such session expected')
            session = self.sessions[session_id]
            # this is done on the network thread, which is single-threaded.
            # There can be no race condition between reading session.state and claiming the session
            if session.state != Session.state.FREE:
                raise ServerRoom.CouldntConnect('Session already taken')
            return session
        else:
            spectator = Spectator(self)
            self.spectators.append(spectator)
            return spectator

    # signals the game that it should end as soon as possible.
    def nt_interrupt(self):
        for spectator in self.get_spectators_and_sessions():
            spectator.interrupt()

    async def nt_close(self) -> None:
        for spectator in self.get_spectators_and_sessions():
            assert spectator.run_handle is not None
        await asyncio.wait([ spectator.run_handle for spectator in self.get_spectators_and_sessions() ])
        self.server.delete_room(self)

    def report_afk(self, spectator: Spectator):
        assert spectator.state in [ Spectator.state.FREE, Spectator.state.INTERRUPTED_BY_SERVER ]
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
        router.add_routes([
            # see @class Server for an explanation of parameter {roomId}
            web.get(r'/{roomId:\d+}/ws/{seat:\d+}', cls.nt_handle_websocket),
        ])
        return router

    async def nt_handle_websocket(self, request : web.Request):
        try:
            seatId = SeatId(request.match_info['seat'])
            spectator = self.add_spectator(request, seatId)
        except ServerRoom.CouldntConnect as err:
            raise web.HTTPNotFound(text=str(err))

        ws = web.WebSocketResponse()
        try:
            await spectator.on_connect(request, ws)
            if(type(spectator) != Session):
                await spectator.send(self.greeter_message)
            await spectator.run()
            # the websocket is closed as soon as the method execution finishes, i.e. now
        except asyncio.CancelledError: # cancelled by server, or the game ended
            pass
        return ws
