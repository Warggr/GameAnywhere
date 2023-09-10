import aiohttp
import asyncio
from aiohttp import web
from enum import Enum, unique
from game_anywhere.include.core.agent import AgentId
from typing import Optional, Any
from threading import Condition, Lock

"""
Represents an active WebSocket connection to the server.

Convention: all methods should be called in the network thread by default,
except those called _sync
"""
class Spectator:
    @unique
    class state(Enum):
        FREE = 0
        CLAIMED = 1
        CONNECTED = 2
        INTERRUPTED_BY_SERVER = 3

    class DisconnectedException(Exception):
        pass

    def __init__(self, room : 'ServerRoom'):
        self.state = Spectator.state.FREE
        self.reading_queue = [] # All messages that haven't been read yet
        self.writing_queue = [] # All messages that haven't been sent yet
        self.protect_reading_queue = Lock()
        self.signal_reading_queue = Condition(self.protect_reading_queue)
        self.listening = False
        self.previously_connected = False
        self.ws : Optional[aiohttp.web.WebSocketResponse] = None
        self.room = room
        self.message_writing_loop = None
        self.run_coro = None

    # this is not guaranteed to be called, unlike a C++ destructor.
    # but it's just an assertion so it's fine
    def __del__(self):
        assert self.state == Spectator.state.FREE or self.state == Spectator.state.INTERRUPTED_BY_SERVER

    # note: in C++, this method is split into two parts, claim() and on_connect()
    # this is not necessary here since we have actual coroutines instead of callbacks
    async def on_connect(self, request):
        assert self.state == Spectator.state.FREE
        self.state = Spectator.state.CLAIMED
        self.ws = web.WebSocketResponse()

        # do the websocket handshake
        await self.ws.prepare(request)
        print("(async spectator) Accept WS handshake")

        with self.protect_reading_queue:
            self.state = Spectator.state.CONNECTED
            self.signal_reading_queue.notify()

        self.run_coro = self.run()

    async def run(self):
        # start the message writing loop, in case there are some messages in the buffer
        if self.message_writing_loop is None:
            self.message_writing_loop = self.send_all_messages()

        await self.read_all_messages()

        if self.message_writing_loop is not None:
            await self.message_writing_loop

        print(self, "received close, ask for disconnect")
        with self.protect_reading_queue:
            self.state = Spectator.state.FREE
            self.signal_reading_queue.notify()

        self.room.report_afk(self)

    async def read_all_messages(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                print(self, "Read message of size", len(msg))

                # Add to queue
                with self.protect_reading_queue:
                    self.reading_queue.append(msg)
                    self.signal_reading_queue.notify()

                if not self.listening:
                    await self.ws.send_str("\"Not listening\"")

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(self, "ws connection closed with exception", self.ws.exception())

    # This is executed on the network thread, so the only possible race condition is with send() or get()
    async def interrupt(self, msg='Server shutdown') -> None:
        print(self, "connection interrupted")
        with self.protect_reading_queue:
            self.state = INTERRUPTED_BY_SERVER
            self.signal_reading_queue.notify() #in case anyone was waiting for it

        if self.ws is not None and not self.ws.closed:
            await self.ws.close()

    async def send_all_messages(self) -> None:
        while len(self.writing_queue) > 0:
            msg = self.writing_queue[0]
            try:
                print('writing', self.writing_queue[0])
                await self.ws.send_json(msg)
                del self.writing_queue[0]
            except ConnectionResetError:
                break
        self.message_writing_loop = None

    async def send(self, msg: Any) -> None:
        print("(main) Sending message")
        queue_empty : bool = len(self.writing_queue) == 0

        # always append to queue, in case the sending fails
        self.writing_queue.append(msg)

        if self.state == Spectator.state.CONNECTED and queue_empty:
            self.message_writing_loop = self.send_all_messages()

    def send_sync(self, msg : str) -> None:
        self.room.server.call_soon_threadsafe( self.send(msg) )

    def get_sync(self) -> str:
        print("(main) Getting string, waiting for mutex...")
        with self.protect_reading_queue:
            self.listening = True
            if len(self.reading_queue) == 0:
                if self.state != Spectator.state.CONNECTED:
                    raise Spectator.DisconnectedException()
                self.signal_reading_queue.wait( # condition for waking up:
                    lambda: len(self.reading_queue)>0
                    or self.state != Spectator.state.CONNECTED
                )
                if self.state != Spectator.state.CONNECTED:
                    raise Spectator.DisconnectedException()

            assert len(self.reading_queue) > 0
            self.listening = False # okay, maybe a semaphore would've been cleaner
            retVal = self.reading_queue[0]
            del self.reading_queue[0]
        return retVal


"""
A Session is like a Spectator, but can reconnect if the connection was lost.
"""
class Session(Spectator):
    TIMEOUT_SECONDS = 3 * 60

    class TimeoutException(Exception):
        pass

    def __init__(self, id: AgentId, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id

    def reconnect_sync(self) -> None:
        with self.protect_reading_queue:
            if self.state == Spectator.state.INTERRUPTED_BY_SERVER:
                raise Spectator.DisconnectedException()
            elif self.state == Spectator.state.CONNECTED:
                return

            # the lock needs to be still locked when we wait for the signal
            print("(sync session) Awaiting reconnect...")
            if not self.signal_reading_queue.wait_for(
                # predicate=lambda:True,
                predicate=lambda: self.state in [Spectator.state.CONNECTED, Spectator.state.INTERRUPTED_BY_SERVER],
                timeout=Session.TIMEOUT_SECONDS
            ):
                raise Session.TimeoutException()

        print("(sync session) ...reconnect signal heard")
        if self.state == Spectator.state.INTERRUPTED_BY_SERVER:
            raise Exception('Interrupted by server')

        assert self.state == Spectator.state.CONNECTED, str(self.state)
        print("(sync session) reconnected!")

    # Override
    def get_sync(self) -> str:
        while True:
            try:
                return super().get_sync()
            except Spectator.DisconnectedException:
                self.reconnect_sync()
