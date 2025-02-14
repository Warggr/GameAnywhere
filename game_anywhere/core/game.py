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
    def __init__(self, agent_descriptions: Union[list["AgentDescriptor"],"AgentDescriptor"], nb_agents: int|None = None):
        super().__init__()
        if type(agent_descriptions) == list:
            assert nb_agents is None or nb_agents == len(agent_descriptions)
            nb_agents = len(agent_descriptions)
        elif nb_agents is not None:
            pass
        else:
            nb_agents = self.NB_PLAYERS
        self.agents: list[Agent]|list[None] = [None] * nb_agents

    @property
    def NB_PLAYERS(self):
        """ Override this to set the only possible number of players of the game """
        return 2

    @classmethod
    def parse_config(cls, config: list[str]) -> dict[str, Any]|NoReturn:
        """ Override this to accept configuration options """
        if len(config) == 0:
            return {}
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
                update = {"id": obj.get_slot_address(), "append": tag.div(id=slot.get_address())}
                agent.update([update])

    def log_delete_slot(self, obj: ComponentOrGame, slot_relative_address: str):
        if self.agents[0] is None:
            return
        for agent_id, agent in enumerate(self.agents):
            if obj.can_be_seen_by_recursive(agent_id):
                update = {"id": obj.get_slot_address(), "delete": slot_relative_address}
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
                agent.update([{"id": address, "new_value": html(new_value, viewer_id=agent_id)}])

    # Subclasses might override this if they need to be notified once the real agents are available
    # TODO: this is ugly, most overrides do not actually require the agents to be loaded
    def set_agents(self, agents: list[Agent]):
        self.agents = agents

    @abstractmethod
    def play_game(self) -> GameSummary: ...

    def __enter__(self):
        return self

    def __exit__(self, extype, exvalue, traceback):
        pass

# TODO: possible improvements:
# Game could detect automatically when Components exist as class properties
# and translate them to ComponentSlotProperties
