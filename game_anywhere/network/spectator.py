from __future__ import annotations

import asyncio
import json
from enum import Enum, unique
from threading import Condition, Lock
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import aiohttp
from aiohttp import web

if TYPE_CHECKING:
    from typing import Callable, Optional

    from .room import ServerRoom


T = TypeVar("T", bound="Spectator")


class SyncChannel(Generic[T]):
    def __init__(self, spectator: T):
        self.reading_queue: list[str] = []  # All messages that haven't been read yet
        self.spectator = spectator
        self.listening = False

    def __call__(self, message: Any):
        if not self.listening:
            raise RuntimeError("Not listening")

        # Add to queue
        with self.spectator.protect_reading_queue:
            self.reading_queue.append(message)
            self.spectator.signal_reading_queue.notify()

    def get_sync(self) -> str:
        with self.spectator.protect_reading_queue:
            self.listening = True
            if len(self.reading_queue) == 0:
                if self.spectator.state != Spectator.State.CONNECTED:
                    raise Spectator.DisconnectedException(self.spectator.state)
                self.spectator.signal_reading_queue.wait_for(  # condition for waking up:
                    lambda: (
                        len(self.reading_queue) > 0
                        or self.spectator.state != Spectator.State.CONNECTED
                    )
                )
                if self.spectator.state != Spectator.State.CONNECTED:
                    raise Spectator.DisconnectedException(self.spectator.state)

            assert len(self.reading_queue) > 0
            self.listening = False
            retVal = self.reading_queue.pop(0)
        return retVal


class Spectator:
    """
    Represents an active WebSocket connection to the server.

    Convention: all methods should be called in the network thread by default,
    except those called _sync
    """

    SyncChannel = SyncChannel

    @unique
    class State(Enum):
        FREE = 0
        CLAIMED = 1
        CONNECTED = 2
        INTERRUPTED_BY_SERVER = 3

    class DisconnectedException(Exception):
        def __init__(self, state: "Spectator.State | int" = 0):
            self.state = Spectator.State(state)

    def __init__(self, room: "ServerRoom"):
        self.room = room

        self._state = Spectator.State.FREE
        self.previously_connected = False

        # the reading queue can block the game thread but not the network thread, so we use threading sync primitives
        # (the game thread will wait for messages by locking these primitives)
        self.protect_reading_queue = Lock()  # protects self.state
        self.signal_reading_queue = Condition(self.protect_reading_queue)

        self.run_handle: Optional[asyncio.Task] = None
        self.ws: Optional[aiohttp.web.WebSocketResponse] = None

        self.sync_channel = SyncChannel(self)
        self.channels: dict[str, Callable[[dict], None]] = {}

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.room.server.loop

    @property
    def state(self) -> "Spectator.State":
        return self._state

    @state.setter
    def state(self, value: "Spectator.State"):
        self._state = value
        # The logging is done in @class Room

    # this is not guaranteed to be called, unlike a C++ destructor.
    # but it's just an assertion so it's fine
    def __del__(self):
        assert (
            self.state == Spectator.State.FREE
            or self.state == Spectator.State.INTERRUPTED_BY_SERVER
        )

    def add_channel(self, name, channel: Callable[[Any], None]):
        """
        Thread-safe.
        """
        if channel in self.channels:
            raise ValueError()
        self.channels[name] = channel

    async def on_connect(
        self, request: web.Request, websocket: web.WebSocketResponse
    ) -> web.WebSocketResponse:
        assert self.state == Spectator.State.FREE
        self.state = Spectator.State.CLAIMED
        self.ws = websocket

        # do the websocket handshake
        await self.ws.prepare(request)

        with self.protect_reading_queue:
            self.state = Spectator.State.CONNECTED
        return self.ws

    async def run(self) -> None:
        assert self.run_handle is None
        self.run_handle = asyncio.create_task(self._run())
        await self.run_handle
        self.run_handle = None

    async def _run(self):
        try:
            await self.read_all_messages()
            # all messages read, connection closed
            with self.protect_reading_queue:
                self.state = Spectator.State.FREE
        finally:  # catch asyncio.CancelledError
            # signal anyone that waits for an incoming message
            with self.protect_reading_queue:
                self.signal_reading_queue.notify()
            await self.room.nt_report_afk(self)

    async def read_all_messages(self):
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    channel = self.channels[data["channel"]]
                    channel(data)
                except Exception as e:
                    self.loop.create_task(
                        self.ws.send_json({"channel": "error", "msg": str(e)})
                    )

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(self, "ws connection closed with exception", self.ws.exception())

    # This is executed on the network thread, so the only possible race condition is with send() or get()
    def interrupt(self, msg="Server shutdown") -> None:
        with self.protect_reading_queue:
            self.state = Spectator.State.INTERRUPTED_BY_SERVER
            self.signal_reading_queue.notify()

        if self.run_handle:
            self.run_handle.cancel()

    async def send(self, msg: Any) -> None:
        await self.ws.send_json(msg)

    def send_sync(self, msg: Any) -> None:
        asyncio.run_coroutine_threadsafe(self.send(msg), loop=self.loop)

    class Chat:
        def __init__(self, parent: "Spectator", on_message: Callable[[str], None]):
            self.parent = parent
            self.on_message = on_message

        def __enter__(self):
            assert "chat" not in self.parent.channels
            self.parent.channels["chat"] = self.on_message

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.parent.channels.pop("chat")


class Session(Spectator):
    """A Session is like a Spectator, but can reconnect if the connection was lost."""

    TIMEOUT_SECONDS = 3 * 60

    class TimeoutException(Exception):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: str | None = None  # set by the server when someone connects

    @property
    def seat_id(self) -> int:
        ((seat_id, _this),) = filter(lambda i: i[1] is self, self.room.sessions.items())
        return seat_id

    @Spectator.state.setter
    def state(self, value: "Spectator.State"):
        self._state = value
        self.room.log_event_nosync(
            {
                "op": "replace",
                "path": f"/seats/{self.seat_id}/state",
                "value": value.name,
            }
        )

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
                predicate=lambda: (
                    self.state
                    in [
                        Spectator.State.CONNECTED,
                        Spectator.State.INTERRUPTED_BY_SERVER,
                    ]
                ),
                timeout=Session.TIMEOUT_SECONDS,
            ):
                raise Session.TimeoutException()

        if self.state == Spectator.State.INTERRUPTED_BY_SERVER:
            raise Exception("Interrupted by server")

        assert self.state == Spectator.State.CONNECTED, str(self.state)

    class SyncChannel(SyncChannel["Session"]):
        # Override
        def get_sync(self) -> str:
            while True:
                try:
                    return super().get_sync()
                except Spectator.DisconnectedException as err:
                    if err.state == Spectator.State.INTERRUPTED_BY_SERVER:
                        raise err
                    else:
                        self.spectator.reconnect_sync()
