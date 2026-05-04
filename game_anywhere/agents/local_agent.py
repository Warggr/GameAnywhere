import asyncio
import json
import os
from abc import abstractmethod
from itertools import chain
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Optional, TextIO, TypeVar

from game_anywhere.core import Agent

from ..core.agent import ChatStream
from .descriptors import AgentDescriptor
from .network_agent import AskMultipleTimesMixin

if TYPE_CHECKING:
    from game_anywhere.agents.descriptors import Context
    from game_anywhere.components import ComponentSlot

T = TypeVar("T")


class TextAgent(Agent, AskMultipleTimesMixin):
    """An agent that writes to, and reads from, a text terminal.
    Mostly for debugging purposes.
    """

    @abstractmethod
    def _write(*objects, sep=" ", end="\n"): ...

    @abstractmethod
    def _read(self, message: str | None = None) -> str: ...

    def message(self, message, **kwargs):
        for k, v in kwargs.items():
            if k == "sender":
                message = f"*{v}*: {message}"
            else:
                message = f"[{k}={v}] {message}"
        self._write(message)

    def ask_question(self, question: str) -> Any:
        return self._read(question + ":")

    def criticize_answer(self, error_message: str) -> None:
        self._write(error_message)
        self._write("Please try again.")

    # override
    def query(self, allowedSchema):
        return json.loads(self._read(f"Please answer the query: {allowedSchema}"))

    # override
    def choose_one_component_slot(
        self,
        slots: list["ComponentSlot"],
        indices: Optional[list[T]] = None,
        special_options=(),
        message: str | None = None,
    ):
        if indices is None:
            indices = slots
        for i, (option_addr, option) in enumerate(
            chain(
                map(lambda slot: (slot, slot.get_address()), slots),
                map(lambda s: (s, s), special_options),
            )
        ):
            self._write(f"[{i + 1}]", option_addr, option)
        i = (
            self._get_integer(
                mini=1, maxi=len(slots) + len(special_options), message=message
            )
            - 1
        )
        if i < len(indices):
            return indices[i]
        else:
            return special_options[i - len(indices)]

    # override
    def update(self, diffs: list[Any]):
        self._write("Some things were updated:")
        for di in diffs:
            self._write(di)

    def chat_stream(self, event_loop: asyncio.AbstractEventLoop) -> ChatStream:
        from queue import Queue

        # TODO: Optimization: there might be a way of asynchronously watching multiple files
        class Stream(ChatStream):
            def __init__(self, parent: TextAgent):
                self.parent = parent
                self.original_read = parent._read
                parent._read = self._read

                self.input_queue = Queue()
                self.parent._write(
                    "You have entered a chat room. Lines starting with `/` will be forwarded to the chat."
                )

            def close(self):
                self.parent._read = self.original_read
                self.reading_task.cancel()

            async def __anext__(self) -> str:
                # This spawns a new thread (or whatever the default policy of asyncio for executors is)
                # which waits for original_read
                while True:
                    # TODO: this is often an input() call and can't be interrupted - we have to wait until the user writes something
                    self.reading_task = event_loop.run_in_executor(
                        None, self.original_read
                    )  # Schedule a new read
                    message = await self.reading_task
                    if message.startswith("/"):
                        return message[1:]
                    else:
                        self.input_queue.put(message)

            def _read(self, message: str | None = None) -> str:
                if message is not None:
                    self.parent._write(message)
                return self.input_queue.get()

        return Stream(self)


class HumanAgent(TextAgent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, agent_descriptor_number: int, context):
            self.resolve_name(f"Human agent {agent_descriptor_number}")

        def await_initialization(self, promise) -> "HumanAgent":
            return HumanAgent(self.name)

    def _write(self, *objects, **kwargs):
        print(*objects, **kwargs)

    def _read(self, message: str | None = None) -> str:
        if message is not None:
            return input(message)
        else:
            return input()


class PipeAgent(TextAgent):
    class Disconnected(Exception):
        pass

    class Descriptor(AgentDescriptor):
        def start_initialization(
            self, agent_descriptor_number: int, context
        ) -> tuple[str, str, "Context"]:
            if "tmp_dir" not in context:
                tmpdir = TemporaryDirectory()
                context["tmp_dir"] = tmpdir
                context["exit_stack"].push(tmpdir)
                print("Pipes are in", tmpdir.name)

            def open_pipe(name) -> str:
                tmp_file = os.path.join(context["tmp_dir"].name, name)
                os.mkfifo(tmp_file)
                context["exit_stack"].push(
                    lambda: os.unlink(tmp_file)
                )  # delete file on exit
                return tmp_file

            infile = open_pipe(str(agent_descriptor_number) + ".in")
            outfile = open_pipe(str(agent_descriptor_number) + ".out")
            return infile, outfile, context

        def await_initialization(
            self, promise: tuple[str, str, "Context"]
        ) -> "TextAgent":
            infile, outfile, context = promise
            outfile = open(outfile, "a")
            infile = open(infile, "r")
            # ! The client must first read from the .out pipe and then open the .in pipe for writing!
            context["exit_stack"].push(outfile)  # close file on exit
            context["exit_stack"].push(infile)
            print("Enter your name:", file=outfile, flush=True)
            name = infile.readline().strip()
            self.resolve_name(name)
            return PipeAgent(infile, outfile, name)

    def __init__(self, infile: TextIO, outfile: TextIO, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.infile = infile
        self.outfile = outfile

    def _write(self, *objects, **kwargs):
        print(*objects, **kwargs, file=self.outfile, flush=True)

    def _read(self, message: str | None = None) -> str:
        if message is not None:
            self._write(message)
        read = self.infile.readline().strip()
        if read == "":
            raise self.Disconnected()
        return read
