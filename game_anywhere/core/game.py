from typing import Any, NoReturn, Union
from abc import ABC, abstractmethod

from game_anywhere.components import Component

from .agent import Agent, AgentId
from ..components.component import ComponentOrGame, WeakComponentSlot
from ..components.utils import html
from ..ui import tag


class GameSummary(ABC):
    NO_WINNER = 0

    @abstractmethod
    def get_winner(self) -> AgentId: ...


class SimpleGameSummary(GameSummary):
    def __init__(self, winner: AgentId):
        self.winner = winner

    def get_winner(self):
        return self.winner


"""
Represents a game in progress.
"""


# ComponentOrGame is an ABC, so indirectly Game is also an ABC
class Game(ComponentOrGame):
    """
    Game lifecycle. E.g. assume a game called FooGame.
    - the FooGame class is defined as Python code
    - FooGame.parse_config() is called to parse command-line options, in particular number of agents.
      the type of the agents are often clear from the context - when they are not, i.e. in run_game_from_cmdline,
      there's extra logic to determine them from the command-line arguments
    - FooGame is instantiated: game = FooGame(...)
      from now on the html() method can be called (we know how many agents there are so we can show what an emtpy board looks like)
    - we wait for the agents to connect and then call set_agents - now the game can start
    - play_game is called (typically)
    """

    def __init__(self, agent_descriptions: list["AgentDescriptor"]):
        super().__init__()
        nb_agents = len(agent_descriptions)
        # TODO: maybe a state pattern with AgentDescriptors and Agents, instead of setting them to None at the beginning
        self.agents: list[Agent]|list[None] = [None] * nb_agents

    @classmethod
    def parse_config(cls, config: list[str]|None) -> tuple[int, dict[str, Any]]:
        """ Override this to accept configuration options """
        if len(config) == 0 or config is None:
            return 2, {}
        else:
            raise NotImplementedError(f'{cls.__name__} does not accept configuration options')

    # override
    def get_game(self):
        return self

    # override
    def get_slot_address(self):
        return ""

    # override
    def can_be_seen_by_recursive(self, viewer_id) -> bool:
        """ The Game can be seen by everybody. """
        return True

    def message(self, *args, **kwargs):
        for agent in self.agents:
            agent.message(*args, **kwargs)

    def log_new_slot(self, obj: ComponentOrGame, slot: WeakComponentSlot):
        if self.agents[0] is None:
            return # Return early if the agents are not initialized yet
        for agent_id, agent in enumerate(self.agents):
            if obj.can_be_seen_by_recursive(agent_id):
                update = {"op": "add", "key": slot.get_address(), "value": tag.div(id=slot.get_address())}
                agent.update([update])

    def log_delete_slot(self, obj: ComponentOrGame, slot_relative_address: str):
        if self.agents[0] is None:
            return
        for agent_id, agent in enumerate(self.agents):
            if obj.can_be_seen_by_recursive(agent_id):
                update = {"op": "remove", "key": obj.get_slot_address()}
                agent.update([update])

    def log_component_update(
        self,
        slot: WeakComponentSlot,
        new_value: Component,
        only_update: int|None = None,
        force_reveal = False,
    ):
        address = slot.get_address()

        if only_update is None:
            agents = enumerate(self.agents)
        else:
            agents = [(only_update, self.agents[only_update])]
        if self.agents[0] is None:
            return # Return early if the agents are not initialized yet
        for agent_id, agent in agents:
            if force_reveal or slot.can_be_seen_by_recursive(agent_id):
                agent.update([{"op": "replace", "key": address, "value": html(new_value, viewer_id=agent_id)}])

    def set_agents(self, agents: list[Agent]):
        self.agents = agents

    @abstractmethod
    def play_game(self) -> GameSummary: ...


# TODO: possible improvements:
# Game could detect automatically when Components exist as class properties
# and translate them to ComponentSlotProperties
