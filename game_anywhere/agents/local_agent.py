from game_anywhere.core import Agent
from .descriptors import AgentDescriptor
from typing import Optional, TypeVar, Any, TextIO
from itertools import chain
import json
from tempfile import TemporaryDirectory
import os
from abc import abstractmethod
import asyncio
from ..core.agent import ChatStream

T = TypeVar("T")


class TextAgent(Agent):
    """
    An agent that writes to, and reads from, a text terminal.
    Mostly for debugging purposes.
    """

    @abstractmethod
    def _write(*objects, sep=' ', end='\n'): ...

    @abstractmethod
    def _read(self, message: str | None = None) -> str: ...

    def message(self, message, **kwargs):
        for k, v in kwargs.items():
            if k == 'sender':
                message = f'*{v}*: {message}'
            else:
                message = f'[{k}={v}] {message}'
        self._write(message)

    def _get_value(self, constructor, message=None):
        if message is None:
            message = f"Enter a value of type {constructor}"
        while True:
            raw_result: str = self._read(message + ":")
            try:
                return constructor(raw_result)
            except ValueError as err:
                self._write(err)
                self._write("Please try again.")

    def _get_integer(self, min=None, max=None, message=None):
        def _suitable_int(st):
            i = int(st)
            if i < min or max < i:
                raise ValueError(f"{i} is out of bounds: [{min}, {max}] expected")
            return i

        if message is None:
            message = f"Enter a value between {min} and {max}"
        return self._get_value(_suitable_int, message)

    # override
    def int_choice(self, min: Optional[int] = 0, max: Optional[int] = None) -> int:
        return self._get_integer(min, max)

    # override
    def query(self, query):
        return json.loads(self._read(f"Please answer the query: {query}"))

    # override
    def get_2D_choice(self, dimensions):
        return tuple(
            self._get_integer(
                min=0,
                max=dim - 1,
                message=f"[dim {i}/{len(dimensions)}] Enter a value between {0} and {dim-1}",
            )
            for i, dim in enumerate(dimensions)
        )

    def choose_one(self, descriptions: list[Any], indices: list[T]) -> T:
        for i, description in enumerate(descriptions):
            self._write(f"[{i+1}]", description)
        i = self.int_choice(min=1, max=len(descriptions)) - 1
        return indices[i]

    # override
    def choose_one_component_slot(
        self,
        slots: list["ComponentSlot"],
        indices: Optional[list[T]] = None,
        special_options=[],
    ):
        if indices is None:
            indices = slots
        for i, option in enumerate(chain(slots, special_options)):
            self._write(f"[{i+1}]", option)
        i = self._get_integer(min=1, max=len(slots) + len(special_options)) - 1
        if i < len(indices):
            return indices[i]
        else:
            return special_options[i - len(indices)]

    # override
    def text_choice(self, options: list[str]) -> str:
        return self.choose_one(options, options)

    # override
    def update(self, diff: list[Any]):
        self._write("Some things were updated:")
        for di in diff:
            self._write(di)

    def chat_stream(self, loop: asyncio.AbstractEventLoop) -> ChatStream:
        from queue import Queue

        # TODO: Optimization: there might be a way of asynchronously watching multiple files
        class Stream(ChatStream):
            def __init__(self, parent: TextAgent):
                self.parent = parent
                self.original_read = parent._read
                parent._read = self._read

                self.input_queue = Queue()
                self.parent._write('You have entered a chat room. Lines starting with `/` will be forwarded to the chat.')
            def close(self):
                self.parent._read = self.original_read
                self.reading_task.cancel()
            async def __anext__(self) -> str:
                # This spawns a new thread (or whatever the default policy of asyncio for executors is)
                # which waits for original_read
                while True:
                    # TODO: this is often an input() call and can't be interrupted - we have to wait until the user writes something
                    self.reading_task = loop.run_in_executor(None, self.original_read) # Schedule a new read
                    message = await self.reading_task
                    if message.startswith('/'):
                        return message[1:]
                    else:
                        self.input_queue.put(message)
            def _read(self, message: str|None = None) -> str:
                if message is not None:
                    self.parent._write(message)
                return self.input_queue.get()

        return Stream(self)

class HumanAgent(TextAgent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, id: "AgentId", context):
            pass

        def await_initialization(self, promise) -> "HumanAgent":
            return HumanAgent('Bob')

    def _write(*objects, **kwargs):
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
            self, id: "AgentId", context
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

            infile = open_pipe(str(id) + ".in")
            outfile = open_pipe(str(id) + ".out")
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
            print('Enter your name:', file=outfile, flush=True)
            name = infile.readline().strip()
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
