import asyncio
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

from game_anywhere.core import Agent
from game_anywhere.core.agent import ChatStream
from game_anywhere.ui.custom_components import get_registered_component

from ..network import Server
from ..network.game_room import BaseGameRoom
from ..network.spectator import Session, Spectator
from .descriptors import AgentDescriptor

if TYPE_CHECKING:
    from game_anywhere.components import ComponentSlot

    from .descriptors import Context

T = TypeVar("T")
Json = Any


class AskMultipleTimesMixin(ABC):
    class InvalidAnswer(Exception):
        def __init__(self, message):
            super().__init__()
            self.message = message

    def question_with_validation(self, question: Any, validation: Callable[[Any], T]):
        while True:
            answer = self.ask_question(question)
            try:
                answer = validation(answer)
            except self.InvalidAnswer:
                continue  # goto beginning_of_while_loop
            return answer

    @abstractmethod
    def ask_question(self, question: Any) -> Any: ...

    @abstractmethod
    def criticize_answer(self, error_message) -> None: ...


def int_validation(
    mini: int | None = 0, maxi: int | None = None
) -> Callable[[str], int]:
    def _validation(answer: str):
        try:
            assert answer.isdigit()
            integer = int(answer)
            if mini is not None:
                assert integer >= mini, f"Please choose a number higher than {mini}"
            if maxi is not None:
                assert integer <= maxi, f"Please choose a number higher than {maxi}"
            return integer
        except (ValueError, AssertionError) as err:
            raise AskMultipleTimesMixin.InvalidAnswer(repr(err)) from err

    return _validation


class JsonSchemaAgentMixin(AskMultipleTimesMixin):
    # override
    def int_choice(self, mini: int | None = 0, maxi: int | None = None) -> int:
        jsonSchema = {"type": "integer"}
        if mini is not None:
            jsonSchema["minimum"] = mini
        if maxi is not None:
            jsonSchema["maximum"] = maxi

        return self.question_with_validation(
            {"type": "choice", "schema": jsonSchema}, int_validation(mini, maxi)
        )

    # override
    def text_choice(self, options: list[str]) -> str:
        jsonSchema = {"type": "string", "enum": options}

        def _validation(answer: str):
            assert answer.startswith('"') and answer.endswith(
                '"'
            )  # answer should be JSON text
            answer = answer[1:-1]

            if answer not in options:
                raise NetworkAgent.InvalidAnswer(f"value {answer} not allowed")
            return answer

        return self.question_with_validation(
            {"type": "choice", "schema": jsonSchema}, _validation
        )

    # override
    def choose_one_component_slot(
        self,
        slots: list["ComponentSlot"],
        indices: Optional[list[T]] = None,
        special_options=(),
        message: Optional[str] = None,
    ) -> T:
        if not indices:
            indices = slots
        question = {
            "type": "choice",
            "slots": [slot.get_address() for slot in slots],
            "special_options": special_options,
        }
        if message is not None:
            question["message"] = message
        ids = {
            slot.get_address(): index
            for slot, index in zip(slots, indices, strict=True)
        }

        def _validation(answer: str) -> str:
            if answer in ids:
                return ids[answer]
            elif answer in special_options:
                return answer
            else:
                raise NetworkAgent.InvalidAnswer("Invalid choice, please try again!")

        return self.question_with_validation(question, _validation)

    # override
    def query(self, allowedSchema):
        def _validation(answer: str):
            try:
                return json.loads(answer)
            except json.decoder.JSONDecodeError as err:
                raise self.InvalidAnswer(str(err)) from err

        return self.question_with_validation(
            {"type": "choice", "schema": allowedSchema}, _validation
        )


class NetworkAgent(JsonSchemaAgentMixin, Agent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, agent_descriptor_number: int, context: Context):
            if "server_room" not in context:
                if "server" not in context:
                    asset_dirs = {}
                    asset_dir = context["game"].get_asset_dir()
                    if asset_dir is not None:
                        asset_dirs[context["game"].__name__] = asset_dir
                    server = Server(
                        RoomClass=BaseGameRoom,
                        assets=asset_dirs,
                        dynamic_assets=get_registered_component,
                    )
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
            session = room.create_session(agent_descriptor_number)
            return session

        def await_initialization(self, session):
            session.reconnect_sync()
            self.resolve_name(session.username)
            return NetworkAgent(session)

    def __init__(self, session: Session):
        username = session.username
        super().__init__(username)
        self.session = session

    # override
    def message(self, message, **kwargs) -> None:
        self.session.send_sync({"type": "message", "text": message, **kwargs})

    # override
    def update(self, diffs: list[Any]):
        def serialize_diff(diff: dict):
            if diff["op"] in ["add", "update", "replace"]:
                diff = diff.copy()
                diff["value"] = str(diff["value"])
            return diff

        self.session.send_sync(list(map(serialize_diff, diffs)))

    # override
    def ask_question(self, question: Json) -> str:
        while True:
            self.session.send_sync(question)
            answer = self.session.get_sync()
            if answer == Session.CLIENT_LOST_TRACK_MESSAGE:
                continue  # resend question
            return answer

    # override
    def criticize_answer(self, error_message) -> None:
        self.session.send_sync({"type": "error", "message": error_message})

    def chat_stream(self, event_loop: asyncio.AbstractEventLoop) -> ChatStream:
        return NetworkChatStream(event_loop, self.session)

    def __eq__(self, o):
        """
        Used for Game.get_html_for_agent_ref.
        """
        if isinstance(o, Session) and o is self.session:
            return True
        return False


class NetworkChatStream(ChatStream):
    CHAT_CHARACTER = "<"

    def __init__(self, loop: asyncio.AbstractEventLoop, spectator: Spectator):
        self.queue = asyncio.Queue()
        self.loop = loop
        self.session = spectator
        self.impl = Spectator.Chat(spectator, on_message=self.on_message)
        self.impl.__enter__()
        self.session.send_sync(
            {"type": "chatcontrol", "set": "on", "message": "Start chatting..."}
        )

    # Called on the network thread
    def on_message(self, message: str) -> bool:
        if message.startswith(self.CHAT_CHARACTER):
            self.loop.call_soon_threadsafe(lambda: self.queue.put_nowait(message[1:]))
            return True
        else:
            return False

    def close(self):
        self.impl.__exit__(None, None, None)
        self.session.send_sync({"type": "chatcontrol", "set": "off"})

    async def __anext__(self) -> str:
        return await self.queue.get()
