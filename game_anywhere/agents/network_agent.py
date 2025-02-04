from game_anywhere.core import Agent
from game_anywhere.components.utils import html
from game_anywhere.core.agent import ChatStream

from .descriptors import AgentDescriptor, Context
from ..network import Server
from ..network.game_room import BaseGameRoom
from ..network.spectator import Session, Spectator
from typing import Any, TypeVar, Callable, Optional
import asyncio

T = TypeVar("T")


class NetworkAgent(Agent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, agent_id: "AgentId", context: Context):
            if "server_room" not in context:
                if Server._instance is None:
                    server = Server(RoomClass=BaseGameRoom)
                    context["server"] = server
                    context["exit_stack"].enter_context(server)
                else:
                    server = context["server"]
                if "game" in context:
                    _room_id, room = server.new_room(
                        BaseGameRoom(game=context["game"], server=server)
                    )
                else:
                    _room_id, room = server.new_room()
                context["server_room"] = room
                # context['exit_stack'].enter_context(room)
            else:
                room = context["server_room"]
            print("Creating session on room")
            session = room.create_session(agent_id)
            return session

        def await_initialization(self, session):
            session.reconnect_sync()
            return NetworkAgent(session)

    def __init__(self, session: Session):
        username = session.room.session_id_to_username[session.id]
        super().__init__(username)
        self.session = session

    # override
    def message(self, message, **kwargs) -> None:
        self.session.send_sync({"type": "message", "text": message, **kwargs})

    # override
    def update(self, diffs: list[Any]):
        def serialize_diff(diff):
            if "new_value" in diff:
                return {
                    "id": diff["id"],
                    "newHTML": str(html(diff["new_value"])),
                }
            elif "append" in diff:
                return {
                    "id": diff["id"],
                    "append": str(html(diff["append"])),
                }
            else:
                raise NotImplementedError("Unrecognized diff type: " + str(diff))

        self.session.send_sync(list(map(serialize_diff, diffs)))

    # override
    def get_2D_choice(self, dimensions):
        return tuple(self.int_choice(min=0, max=dim - 1) for dim in dimensions)

    class InvalidAnswer(Exception):
        def __init__(self, message):
            super().__init__()
            self.message = message

    # override
    def choose_one_component_slot(
        self,
        slots: list["ComponentSlot"],
        indices: Optional[list[T]] = None,
        special_options=[],
    ) -> T:
        if not indices:
            indices = slots
        question = {
            "type": "choice",
            "slots": [slot.get_address() for slot in slots],
            "special_options": special_options,
        }
        ids = {slot.get_address(): index for slot, index in zip(slots, indices)}

        def _validation(answer: str):
            if answer in ids:
                return ids[answer]
            elif answer in special_options:
                return answer
            else:
                raise NetworkAgent.InvalidAnswer("Invalid choice, please try again!")

        return self.question_with_validation(question, _validation)

    # override
    def int_choice(self, min: int | None = 0, max: int | None = None) -> int:
        jsonSchema = {"type": "integer"}
        if min is not None:
            jsonSchema["minimum"] = min
        if max is not None:
            jsonSchema["maximum"] = max

        def _validation(answer: str):
            try:
                assert answer.isdigit()
                integer = int(answer)
                if min is not None:
                    assert integer >= min, f"Please choose a number higher than {min}"
                if max is not None:
                    assert integer <= max, f"Please choose a number higher than {max}"
                return integer
            except (ValueError, AssertionError) as err:
                raise NetworkAgent.InvalidAnswer(repr(err))

        return self.question_with_validation(
            {"type": "choice", "schema": jsonSchema}, _validation
        )

    # override
    def text_choice(self, options: list[str]) -> str:
        jsonSchema = {"type": "string", "enum": options}

        def _validation(answer: str):
            if answer not in options:
                raise NetworkAgent.InvalidAnswer(f"value {answer} not allowed")
            return answer
        return self.question_with_validation(
            {"type": "choice", "schema": jsonSchema}, _validation
        )


    def question_with_validation(
        self, question: Any, validation: Callable[[str], T]
    ) -> T:
        while True:
            print("(network agent) sending question")
            self.session.send_sync(question)
            answer = self.session.get_sync()
            if answer == Session.CLIENT_LOST_TRACK_MESSAGE:
                continue  # goto beginning_of_while_loop # resend question
            try:
                answer = validation(answer)
            except NetworkAgent.InvalidAnswer as err:
                self.session.send_sync({"type": "error", "message": err.message})
                continue  # goto beginning_of_while_loop
            return answer

    def chat_stream(self, event_loop: asyncio.AbstractEventLoop) -> ChatStream:
        return NetworkChatStream(event_loop, self.session)


class NetworkChatStream(ChatStream):
    def __init__(self, loop: asyncio.AbstractEventLoop, spectator: Spectator):
        self.queue = asyncio.Queue()
        self.loop = loop
        self.session = spectator
        self.impl = Spectator.Chat(spectator, on_message=self.on_message)
        self.impl.__enter__()
        self.session.send_sync({"type": "chatcontrol", "set": "on", "message": "Start chatting..."})

    # Called on the network thread
    def on_message(self, message: str) -> bool:
        if message.startswith('/'):
            self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(message[1:]))
            return True
        else:
            return False

    def close(self):
        self.impl.__exit__(None, None, None)
        self.session.send_sync({"type": "chatcontrol", "set": "off"})

    async def __anext__(self) -> str:
        return await self.queue.get()
