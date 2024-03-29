from game_anywhere.core import Agent
from .descriptors import AgentDescriptor
from typing import Optional, List, TypeVar, Any, Union
from itertools import chain

T = TypeVar('T')

class HumanAgent(Agent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, id : 'AgentId', context):
            pass
        def await_initialization(self, promise) -> 'HumanAgent':
            return HumanAgent()

    def message(self, message):
        print(message)

    @staticmethod
    def get_value(constructor, message = None):
        if message is None:
            message = f"Enter a value of type {constructor}"
        while True:
            raw_result : str = input(message + ":")
            try:
                return constructor(raw_result)
            except ValueError as err:
                print(err)
                print("Please try again.")

    @staticmethod
    def get_integer(min=None, max=None, message=None):
        def _suitable_int(st):
            i = int(st)
            if i < min or max < i:
                raise ValueError(f"{i} is out of bounds: [{min}, {max}] expected")
            return i
        if message is None:
            message=f"Enter a value between {min} and {max}"
        return HumanAgent.get_value(_suitable_int, message)

    # override
    def int_choice(self, min: int|None=0, max: int|None = None) -> int:
        return self.get_integer(min, max)

    # override
    def get_2D_choice(self, dimensions):
        return tuple(
            self.get_integer(min=0, max=dim-1, message=f"[dim {i}/{len(dimensions)}] Enter a value between {0} and {dim-1}")
            for i, dim in enumerate(dimensions)
        )

    def choose_one(self, descriptions : List[Any], indices : List[T]) -> T:
        for i, description in enumerate(descriptions):
            print(f"[{i+1}]", description)
        i = self.int_choice(min=1, max=len(descriptions)) - 1
        return indices[i]

    # override
    def choose_one_component_slot(self, slots : List['ComponentSlot'], indices : Optional[List[T]] = None, special_options=[]):
        for i, option in enumerate(chain(slots, special_options)):
            print(f"[{i+1}]", option)
        i = self.get_integer(min=1, max=len(slots)+len(special_options)) - 1
        if i < len(indices):
            return indices[i]
        else:
            return special_options[i - len(indices)]

    # override
    def text_choice(self, options: List[str]) -> str:
        return self.choose_one(options, options)

    # override
    def update(self, diff : List[Any]):
        print("Some things were updated:")
        for di in diff:
            print(di)
