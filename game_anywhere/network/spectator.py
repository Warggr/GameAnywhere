import aiohttp
import asyncio
from aiohttp import web
from enum import Enum, unique
from game_anywhere.core.agent import AgentId
from typing import Optional, Any, Awaitable, Callable
from threading import Condition, Lock

"""
Represents an active WebSocket connection to the server.

Convention: all methods should be called in the network thread by default,
except those called _sync
"""


class Spectator:
    @unique
    class State(Enum):
        FREE = 0
        CLAIMED = 1
        CONNECTED = 2
        INTERRUPTED_BY_SERVER = 3

    class DisconnectedException(Exception):
        def __init__(self, state=0):
            self.state = state

    def __init__(self, room: "ServerRoom"):
        self.room = room

        self.state = Spectator.State.FREE
        self.listening = False
        self.previously_connected = False

        self.reading_queue: list[str] = []  # All messages that haven't been read yet
        # the reading queue can block the game thread but not the network thread, so we use threading sync primitives
        # (the game thread will wait for messages by locking these primitives)
        self.protect_reading_queue = Lock()
        self.signal_reading_queue = Condition(self.protect_reading_queue)

        self.writing_queue = asyncio.Queue()  # All messages that haven't been sent yet
        # the network thread will wait for the writing queue, so we use asyncio sync primitives
        self.signal_connected = self.loop.create_future()

        self.run_handle: Optional[asyncio.Task] = None
        self.ws: Optional[aiohttp.web.WebSocketResponse] = None

        # Called on each message received. If it returns True, the message is ignored
        # It's an ugly special case to make chatting work.
        self.message_interceptor: Optional[Callable[[str], bool]] = None

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.room.server.loop

    # this is not guaranteed to be called, unlike a C++ destructor.
    # but it's just an assertion so it's fine
    def __del__(self):
        assert (
            self.state == Spectator.State.FREE
            or self.state == Spectator.State.INTERRUPTED_BY_SERVER
        )

    # note: in C++, this method is split into two parts, claim() and on_connect()
    # this is not necessary here since we have actual coroutines instead of callbacks
    async def on_connect(
        self, request: web.Request, websocket: web.WebSocketResponse
    ) -> Awaitable[web.WebSocketResponse]:
        assert self.state == Spectator.State.FREE
        self.state = Spectator.State.CLAIMED
        self.ws = websocket

        # do the websocket handshake
        await self.ws.prepare(request)

        with self.protect_reading_queue:
            self.state = Spectator.State.CONNECTED
            self.signal_reading_queue.notify()
        return self.ws

    async def run(self) -> Awaitable[None]:
        assert self.run_handle is None
        self.run_handle = asyncio.create_task(self._run())
        await self.run_handle
        self.run_handle = None

    async def _run(self):
        message_sending_task = self.loop.create_task(self.send_all_messages())
        try:
            await self.read_all_messages()
            # all messages read, connection closed
            with self.protect_reading_queue:
                self.state = Spectator.State.FREE
        finally:  # catch asyncio.CancelledError
            message_sending_task.cancel()
            await message_sending_task  # in case it had any other exception
            # signal anyone that waits for an incoming message
            with self.protect_reading_queue:
                self.signal_reading_queue.notify()
            self.room.report_afk(self)

    async def read_all_messages(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if self.message_interceptor is not None and self.message_interceptor(msg.data):
                    continue

                # Add to queue
                with self.protect_reading_queue:
                    # CLIENT_LOST_TRACK will be answered by the 'Not listening', no need to propagate it
                    if (
                        not self.listening
                        and msg.data == Session.CLIENT_LOST_TRACK_MESSAGE
                    ):
                        pass
                    else:
                        self.reading_queue.append(msg.data)
                        self.signal_reading_queue.notify()

                if not self.listening:
                    await self.ws.send_json("!Not listening")

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(self, "ws connection closed with exception", self.ws.exception())

    async def send_all_messages(self) -> None:
        try:
            while True:
                msg = await self.writing_queue.get()
                while True:
                    try:
                        await self.ws.send_json(msg)
                        break
                    except ConnectionResetError:
                        await self.signal_connected
                    except Exception as x:
                        print("(net) EXCEPTION when trying to send message:", x)
                        print("(net) discarded message!")
                        break
        except asyncio.CancelledError:
            pass

    # This is executed on the network thread, so the only possible race condition is with send() or get()
    def interrupt(self, msg="Server shutdown") -> None:
        with self.protect_reading_queue:
            self.state = Spectator.State.INTERRUPTED_BY_SERVER
            self.signal_reading_queue.notify()

        if self.run_handle:
            self.run_handle.cancel()

    async def send(self, msg: Any) -> None:
        await self.writing_queue.put(msg)

    def send_sync(self, msg: str) -> None:
        asyncio.run_coroutine_threadsafe(self.send(msg), loop=self.loop)

    def get_sync(self) -> str:
        with self.protect_reading_queue:
            self.listening = True
            if len(self.reading_queue) == 0:
                if self.state != Spectator.State.CONNECTED:
                    raise Spectator.DisconnectedException(self.state)
                self.signal_reading_queue.wait_for(  # condition for waking up:
                    lambda: len(self.reading_queue) > 0
                    or self.state != Spectator.State.CONNECTED
                )
                if self.state != Spectator.State.CONNECTED:
                    raise Spectator.DisconnectedException(self.state)

            assert len(self.reading_queue) > 0
            self.listening = False  # okay, maybe a semaphore would've been cleaner
            retVal = self.reading_queue[0]
            del self.reading_queue[0]
        return retVal

    class Chat:
        def __init__(self, parent: "Spectator", on_message: Callable[[str], bool]):
            self.parent = parent
            self.on_message = on_message
        def __enter__(self):
            assert self.parent.message_interceptor is None
            self.parent.message_interceptor = self.on_message
        def __exit__(self, exc_type, exc_val, exc_tb):
            assert self.parent.message_interceptor is self.on_message
            self.parent.message_interceptor = None

"""
A Session is like a Spectator, but can reconnect if the connection was lost.
"""


class Session(Spectator):
    TIMEOUT_SECONDS = 3 * 60

    CLIENT_LOST_TRACK_MESSAGE = "?"

    class TimeoutException(Exception):
        pass

    def __init__(self, id: AgentId, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id

    def reconnect_sync(self) -> None:
        with self.protect_reading_queue:
            if self.state == Spectator.State.INTERRUPTED_BY_SERVER:
                raise Spectator.DisconnectedException(
                    Spectator.State.INTERRUPTED_BY_SERVER
                )
            elif self.state == Spectator.State.CONNECTED:
                return

            # the lock needs to be still locked when we wait for the signal (wait_for unlocks it)
            if not self.signal_reading_queue.wait_for(
                predicate=lambda: self.state
                in [Spectator.State.CONNECTED, Spectator.State.INTERRUPTED_BY_SERVER],
                timeout=Session.TIMEOUT_SECONDS,
            ):
                raise Session.TimeoutException()

        if self.state == Spectator.State.INTERRUPTED_BY_SERVER:
            raise Exception("Interrupted by server")

        assert self.state == Spectator.State.CONNECTED, str(self.state)

    # Override
    def get_sync(self) -> str:
        while True:
            try:
                return super().get_sync()
            except Spectator.DisconnectedException as err:
                if err.state == Spectator.State.INTERRUPTED_BY_SERVER:
                    raise err
                else:
                    self.reconnect_sync()
