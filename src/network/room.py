from game_anywhere.include.core.agent import AgentId
from .spectator import Session, Spectator
from itertools import chain
from typing import Iterable, Dict, List
from threading import Thread
from aiohttp import web

SeatId = int

class ServerRoom:
    class CouldntConnect(Exception):
        pass

    def __init__(self, greeter_message='Welcome to the room!'):
        self.greeter_message = greeter_message #The message that will be sent to every new spectator
        self.spectators : List[Spectator] = []
        self.sessions : Dict[SeatId, Session] = {}

    def create_session(self, agent_id: AgentId) -> Session:
        assert agent_id not in self.sessions
        session = Session( self, agent_id )
        self.sessions[agent_id] = session
        return session

    async def add_spectator(self, request, session_id : int = 0):
        if session_id != 0:
            if session_id not in self.sessions:
                raise ServerRoom.CouldntConnect('No such session expected')
            session = self.sessions[session_id]
            # this is done on the network thread, which is single-threaded.
            # There can be no race condition between reading session.state and claiming the session
            if session.state != Session.state.FREE:
                raise ServerRoom.CouldntConnect('Session already taken')
            await session.on_connect(request)
            return session
        else:
            spectator = Spectator(self)
            await spectator.on_connect(request)
            self.spectators.append(spectator)
            await spectator.send(self.greeter_message)
            return spectator

    # signals the game that it should end as soon as possible.
    def interrupt(self):
        for spectator in self.get_spectators_and_sessions():
            spectator.interrupt()

    def report_afk(self, spectator: Spectator):
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
            # all routes need to have a parameter {roomId}
            web.get(r'/{roomId:\d+}/ws/{seat:\d+}', cls.nt_handle_websocket),
        ])
        return router

    async def nt_handle_websocket(self, request : web.Request):
        print('nt_handle_websocket called')
        try:
            seatId = SeatId(request.match_info['seat'])
            spectator = await self.add_spectator(request, seatId)
            await spectator.run_coro
            # the websocket is closed as soon as the method execution finishes, i.e. now
        except ServerRoom.CouldntConnect as err:
            raise web.HTTPNotFound(text=str(err))

class GameRoom(ServerRoom):
    def __init__(self, game : 'Game'):
        super().__init__()
        self.first_step = True
        self.game = game
        self.game_thread = Thread(target=self.game.play_game)

    # override
    @classmethod
    def http_interface(cls, *args, **kwargs):
        router = super().http_interface(*args, **kwargs)
        router.add_routes([
            # all routes need to have a parameter {roomId}
            web.get(r'/{roomId:\d+}/html', cls.http_get_html_view),
        ])
        print('Creating GameRoom http interface')
        return router

    async def http_get_html_view(self, request: web.Request) -> web.Response:
        return web.Response(body=self.game.html())
