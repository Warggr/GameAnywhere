from .room import ServerRoom
from ..agents.descriptors import Context
from threading import Thread
from aiohttp import web
import asyncio


class BaseGameRoom(ServerRoom):
    def __init__(self, game: "Game", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game

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
            username = self.get_request_username(request)
            session_id = request.query['seat']
        except KeyError as err:
            raise web.HTTPUnauthorized(text=f"Please provide a username and seat (missing: {err})")
        if session_id == 'watch':
            viewer_id = None
        else:
            try:
                session_id = int(session_id)
            except ValueError:
                raise web.HTTPBadRequest(text="Session is not an integer")
            if session_id in self.session_id_to_username and self.session_id_to_username[session_id] != username:
                raise web.HTTPForbidden(text="Session not owned by authenticated user")
            viewer_id = session_id
        html = self.game.html(viewer_id=viewer_id)
        return web.Response(body=str(html), content_type="text/html")


class GameRoom(BaseGameRoom):
    """Provides its own game, which is launched on another thread from a GameDescriptor"""

    def __init__(self, game_descriptor: "GameDescriptor", *args, **kwargs):
        self.first_step = True
        self.game = game_descriptor.create_game()
        super().__init__(*args, game=self.game, **kwargs)
        agent_promises: list["AgentPromise"] = game_descriptor.start_initialization(
            Context(server_room=self)
        )
        self.game_thread = Thread(
            target=self.run_game_thread, args=(game_descriptor, agent_promises)
        )
        self.game_thread.start()

    def run_game_thread(
        self, game_descriptor: "GameDescriptor", agent_promises: list["AgentPromise"]
    ):
        # print("Starting game thread, waiting for agents…")
        self.game.set_agents(game_descriptor.await_initialization(agent_promises))
        # print("…Agents connected")
        self.game.play_game()
        # print("Game ended, interrupting agents")
        self.server.loop.call_soon_threadsafe(self.nt_interrupt)
        # print("Game ended, scheduling self.nt_close()")
        asyncio.run_coroutine_threadsafe(self.nt_close(), loop=self.server.loop)

    # override
    async def nt_close(self):
        # print("nt_closing GameRoom…")
        # first close the spectators
        await super().nt_close()
        # print("Everything closed, now waiting for the game thread to end…")
        # then wait for the game to end (with no one connected, it can't take long)
        try:
            self.game_thread.join()
            # print("Game thread ended")
        except Exception:
            print("Game thread ended with an exception")
