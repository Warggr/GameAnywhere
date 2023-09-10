import asyncio
from aiohttp import web
from aiohttp.web_runner import GracefulExit
import time
from threading import Thread, Semaphore, Lock
from websockets.server import serve, WebSocketServerProtocol
from contextlib import AbstractContextManager
from abc import ABCMeta
from .room import ServerRoom, SeatId
from typing import Dict, Callable

class Singleton(ABCMeta):
    def get_instance(cls, *args, **kwargs):
        """ warning: no guarantee that the returned instance will actually have been created with the given args"""
        if cls._instance is None:
            cls._instance = cls(*args, **kwargs)
        return cls._instance

    def create_instance(cls, *args, **kwargs):
        assert cls._instance is None
        cls._instance = cls(*args, **kwargs)
        return cls._instance

    def __init__(cls, name, superclasses, attributes):
        super().__init__(name, superclasses, attributes)

        cls._instance = None

        def wrap_new(__new):
            def _wrapper(cls, *args, **kwargs):
                assert cls._instance == None, "An instance already exists. Please use get_instance"
                return __new(cls, *args, **kwargs)
            return _wrapper
        cls.__new__ = wrap_new(cls.__new__)

RoomId = int

"""
Convention:
all functions that are intended to be called on the network thread start with nt_
    (or with http_ for HTTP request handler)
"""
class Server(AbstractContextManager, metaclass=Singleton):
    def __init__(self, RoomClass = ServerRoom):
        self.loop = None
        self.serverThread = None
        self.running = False
        self.rooms : Dict[RoomId, ServerRoom] = {}
        self.app = web.Application()

        # Ideally we would want one sub-app for each room, but aiohttp doesn't
        # allow adding subapps at runtime. So instead, we create one big
        # sub-app that's not bound to any ServerRoom instance,
        # and use a middleware to bind it to the correct instance at runtime

        @web.middleware
        async def room_dispatcher(request: web.Request, handler: web.RequestHandler):
            print(f'{request.path=}, {handler=}')
            if request.match_info.http_exception is not None:
                return await handler(request)
            if 'roomId' not in request.match_info:
                raise web.HTTPBadRequest(text='/r/ requires a roomId')
            roomId = RoomId(request.match_info['roomId'])
            if roomId not in self.rooms:
                raise web.HTTPNotFound(text=f'Room {roomId} not found')
            # Using room.<handler_function> instead of the unbound ServerRoom.<handler_function>.
            # TODO: this is very non-idiomatic and bad
            return await handler(self.rooms[roomId], request)

        subapp = RoomClass.http_interface(instance_dispatcher=room_dispatcher)
        self.app.add_subapp('/r/', subapp)

    def __enter__(self):
        event_loop_started = Semaphore(0)
        self.serverThread = Thread(
            target=self.nt_start,
            kwargs={'on_start': lambda: event_loop_started.release(),}
        )
        self.serverThread.start()
        event_loop_started.acquire() # block until the event loop has started
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def nt_start(self, on_start=None, *args, **kwargs):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        if on_start is not None:
            on_start()
        # we'll handle SIGINT in our code, no need for aiohttp to handle them
        web.run_app(self.app, handle_signals=False, loop=self.loop, *args, **kwargs)
        print('Server thread ending')

    def nt_close(self):
        raise GracefulExit

    def close(self):
        self.loop.call_soon_threadsafe( self.nt_close )
        self.loop.stop()
        self.serverThread.join()

    def add_client(self, route):
        self.app.add_routes([ route ])
        return self #for chaining

    def new_room(self, room : ServerRoom = None) -> (RoomId, ServerRoom):
        if room is None:
            room = ServerRoom()
        roomId = len(self.rooms)
        self.rooms[roomId] = room
        # this would be the idiomatic way of doing it, but unfortunately you can't add subapps at runtime
        # self.app.add_subapp('/' + str(roomId), room.http_interface())
        return roomId, room
