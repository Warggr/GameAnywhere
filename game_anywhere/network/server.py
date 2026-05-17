from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from itertools import count
from threading import Semaphore, Thread
from typing import TYPE_CHECKING, Callable, Optional

from aiohttp import web
from aiohttp.web_runner import GracefulExit

from .async_resource import AsyncResource
from .room import ServerRoom

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Mapping

    from .http_controlled_server import ServerEvent


RoomId = int


class Server(AbstractContextManager, AsyncResource):
    """Handles all network connections.

    Can be used in two modes:
    - sync mode: the network thread is just the thread in which the Server has been created
    - async mode: the Server is used as a context manager. It creates its own network thread, and closes it when __exit__ is called.

    Convention:
    all functions that are intended to be called on the network thread start with nt_
        (or with http_ for HTTP request handler)
    """

    def __init__(
        self,
        RoomClasses: Mapping[str, type[ServerRoom]] | None = None,
        assets: dict[str, Path | str] | None = None,
        dynamic_assets: Callable[[str, str], Path] | None = None,
    ):
        """
        Args:
            RoomClasses: room types supported by the server. Defaults to `{"r": ServerRoom}`
        """
        if RoomClasses is None:
            RoomClasses = {"r": ServerRoom}

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.serverThread: Optional[Thread] = None
        self.running = False
        self.rooms: dict[RoomId, ServerRoom] = {}
        self.app = web.Application()
        self.room_ids = count()

        # Ideally we would want one sub-app for each room, but aiohttp doesn't
        # allow adding subapps at runtime. So instead, we create one big
        # sub-app that's not bound to any ServerRoom instance,
        # and use a middleware to bind it to the correct instance at runtime

        @web.middleware
        async def room_dispatcher(request: web.Request, handler: web.RequestHandler):
            if request.match_info.http_exception is not None:
                return await handler(request)
            if "roomId" not in request.match_info:
                raise web.HTTPBadRequest(text="/r/ requires a roomId")
            roomId = RoomId(request.match_info["roomId"])
            if roomId not in self.rooms:
                raise web.HTTPNotFound(text=f"Room {roomId} not found")
            # Using room.<handler_function> instead of the unbound ServerRoom.<handler_function>.
            # by specifying self manually.
            # TODO: only allow this if the handler is linked to the game room type
            return await handler(self=self.rooms[roomId], request=request)

        for prefix, RoomClass in RoomClasses.items():
            subapp = RoomClass.http_interface(instance_dispatcher=room_dispatcher)
            self.app.add_subapp(f"/{prefix}/", subapp)
        if assets is not None:
            assets_app = web.Application()
            assets_app.add_routes(
                [web.static(f"/{key}/", str(path)) for key, path in assets.items()]
            )
            self.app.add_subapp("/assets/", assets_app)
        if dynamic_assets is not None:

            async def _handle_dynamic_asset(request: web.Request) -> web.Response:
                component = request.match_info["component"]
                filename = request.match_info["file"]
                try:
                    file_path = dynamic_assets(component, filename)
                except KeyError as e:
                    raise web.HTTPNotFound(
                        text=f"Component {component} not found"
                    ) from e
                if not file_path.exists():
                    raise web.HTTPNotFound(
                        text=f"Resolved file {filename} not found in filesystem"
                    )
                return web.FileResponse(file_path)

            self.app.add_routes(
                [web.get("/components/{component}/{file}", _handle_dynamic_asset)]
            )

    def __enter__(self):
        event_loop_started = Semaphore(0)
        self.serverThread = Thread(
            target=self.nt_start,
            kwargs={
                "on_start": lambda: event_loop_started.release(),
            },
        )
        self.serverThread.start()
        event_loop_started.acquire()  # block until the event loop has started
        return self

    def __exit__(self, type_, value, traceback):
        self.close()

    def __del__(self):
        assert len(self.rooms) == 0

    def nt_start(self, on_start=None, *args, **kwargs):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # self.loop.add_signal_handler(sig=SIGINT, callback=self.nt_close)
        if on_start is not None:
            on_start()
        self.app.on_shutdown.append(
            self.on_shutdown
        )  # we can't do this after shutdown because the loop will no longer exist
        web.run_app(
            self.app, *args, loop=self.loop, handle_signals=False, **kwargs
        )  # can't handle signals when the server runs in another thread

    async def on_shutdown(self, app):
        await self.interrupt_and_close()

    async def nt_close(self):
        print("Server thread ending, closing rooms…")
        if len(self.rooms) != 0:
            await asyncio.wait(
                [self.loop.create_task(room.nt_close()) for room in self.rooms.values()]
            )
        print("All rooms closed!")
        # closing the web_app
        raise GracefulExit()

    def nt_interrupt(self):
        for room in self.rooms.values():
            room.nt_interrupt()

    def close(self):
        self.loop.call_soon_threadsafe(self.interrupt_and_close())
        self.loop.stop()
        self.serverThread.join()

    def add_client(self, route):
        self.app.add_routes([route])
        return self  # for chaining

    def new_room(self, room: ServerRoom | None = None) -> tuple[RoomId, ServerRoom]:
        if room is None:
            room = ServerRoom(server=self)
        roomId = next(self.room_ids)
        self.rooms[roomId] = room
        # this would be the idiomatic way of doing it, but unfortunately you can't add subapps at runtime
        # self.app.add_subapp('/' + str(roomId), room.http_interface())
        return roomId, room

    def delete_room(self, room: ServerRoom) -> None:
        (room_key,) = [key for (key, value) in self.rooms.items() if value is room]
        del self.rooms[room_key]

    def log_event(self, event: "ServerEvent") -> None:
        """Polymorphic hook for HttpControlledServer, which wants to be notified of events such as agents joining."""
        pass
