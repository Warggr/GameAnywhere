import asyncio
from asyncio import CancelledError
from game_anywhere.core.agent import Agent, ChatStream
from threading import Thread, Semaphore
from typing import Callable


class Chat:
    def __init__(self, players: list[Agent]):
        self.players = players

    def __enter__(self) -> "Chat":
        semaphore = Semaphore(value=0)
        self.thread = Thread(target=self._messages_thread, kwargs={'on_setup_finished': lambda: semaphore.release()})
        self.thread.start()
        semaphore.acquire() # wait for the thread to be really started
        return self

    async def _broadcast_message_one_player(self, messages: ChatStream, sender: Agent):
        try:
            async for message in messages:
                for player in self.players:
                    if player is not sender:
                        player.message(message, sender=sender.name)
        except CancelledError:
            messages.close()

    async def _broadcast_messages(self, on_setup_finished: Callable[[], None]):
        loops: list[asyncio.Task] = []
        try:
            for player in self.players:
                loop = self._broadcast_message_one_player(player.chat_stream(self.event_loop), player)
                loop = self.event_loop.create_task(loop)
                loops.append(loop)
            on_setup_finished()
            await asyncio.gather(*loops)
        except CancelledError:
            for loop in loops:
                loop.cancel()

    def _messages_thread(self, on_setup_finished: Callable[[], None]):
        self.event_loop = asyncio.new_event_loop()
        self.task = self.event_loop.create_task(self._broadcast_messages(on_setup_finished))
        self.event_loop.run_until_complete(self.task)
        self.event_loop.close()

    def _close(self):
        self.task.cancel()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.event_loop.call_soon_threadsafe(self._close)
        self.thread.join()
