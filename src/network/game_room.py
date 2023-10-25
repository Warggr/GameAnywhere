from .room import ServerRoom
from ..agents.descriptors import Context
from threading import Thread
from aiohttp import web
from typing import Type
import asyncio

class GameRoom(ServerRoom):
    def __init__(self, game_descriptor : 'GameDescriptor', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.first_step = True
        self.GameClass : Type['Game'] = game_descriptor.GameType
        self.game : 'Game' = None # delayed initialization in game thread
        self.game_thread = Thread(target=self.run_game_thread, args=(game_descriptor,))
        self.game_thread.start()

    def run_game_thread(self, game_descriptor : 'GameDescriptor'):
        print('Starting game thread, waiting for agents…')
        self.game = game_descriptor.create( Context(server_room=self) )
        print('…Agents connected')
        self.game.play_game()
        print('Game ended, interrupting agents')
        self.server.loop.call_soon_threadsafe(self.nt_interrupt)
        print('Game ended, scheduling self.nt_close()')
        asyncio.run_coroutine_threadsafe(self.nt_close(), loop=self.server.loop)

    # override
    async def nt_close(self):
        print('nt_closing GameRoom…')
        # first close the spectators
        await super().nt_close()
        print('Everything closed, now waiting for the game thread to end…')
        # then wait for the game to end (with no one connected, it can't take long)
        self.game_thread.join()
        print('Game thread ended')

    # override
    @classmethod
    def http_interface(cls, *args, **kwargs):
        router = super().http_interface(*args, **kwargs)
        router.add_routes([
            # see @class Server for an explanation of parameter {roomId}
            web.get(r'/{roomId:\d+}/html', cls.http_get_html_view),
        ])
        return router

    async def http_get_html_view(self, request: web.Request) -> web.Response:
        return web.Response(body=self.GameClass.html(), content_type='text/html')
