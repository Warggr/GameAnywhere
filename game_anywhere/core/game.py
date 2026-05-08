from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Iterable

from ..components.component import ComponentOrGame, PropertySlotMixin, WeakComponentSlot
from .agent import Agent

if TYPE_CHECKING:
    from pathlib import Path

    from game_anywhere.ui import Html

    from ..agents.descriptors import AgentDescriptor


"""
An AgentId identifies one of the players.
It is 1-based (so that 0 can be "invalid value"), but this is an implementation detail.
To translate between AgentIds and indices, use `enumerate(self.agent_ids)`.

AgentId's are tied to the order of players.
Agent 1 typically is the starting player; if you want to randomize the order, pass the agent_descriptors in a random order.
"""

AgentId = int


class GameSummary(ABC):
    NO_WINNER = 0

    @abstractmethod
    def get_winner(self) -> AgentId: ...


class SimpleGameSummary(GameSummary):
    def __init__(self, winner: AgentId):
        self.winner = winner

    def get_winner(self):
        return self.winner


# ComponentOrGame is an ABC, so indirectly Game is also an ABC
class Game(PropertySlotMixin):
    """
    Represents a game in progress.
    """

    """Game lifecycle. E.g. assume a game called FooGame.
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
        self.agents: list[Agent] | list[None] = [None] * nb_agents
        self.agent_descriptions = agent_descriptions

    CONFIG_SCHEMA = {
        "properties": {
            "_num_players": {"const": 2},
        },
    }

    @classmethod
    def parse_config(cls, **kwargs) -> tuple[int, dict[str, Any]]:
        """Override this for advanced configuration option management.
        Args:
            **kwargs: an object conforming to cls.CONFIG_SCHEMA.
        Returns:
            num_agents: the number of agents.
        Raises:
            jsonschema.ValidationError: if the object does not conform.
            ValueError: if the object conforms, but is semantically invalid.
        """
        from jsonschema import validate

        full_schema = cls.CONFIG_SCHEMA.copy()
        full_schema["type"] = "object"
        full_schema["properties"] = full_schema["properties"].copy()
        validate(kwargs, schema=full_schema)
        return kwargs.pop("_num_players"), kwargs

    @property
    def agent_ids(self) -> Iterable[AgentId]:
        return range(1, len(self.agents) + 1)

    @classmethod
    def get_asset_dir(cls) -> Path | None:
        """Override this to get the Path loaded as static assets by the server."""
        return None

    # override
    def get_game(self):
        return self

    # override
    def get_slot_address(self):
        return ""

    def lookup_slot_address(self, address: str) -> "WeakComponentSlot":
        assert address.startswith("/")
        address = address.removeprefix("/")
        return super().lookup_slot_address(address)

    # override
    def can_be_seen_by_recursive(self, viewer_id) -> bool:
        """The Game can be seen by everybody."""
        return True

    def message(self, *args, **kwargs):
        for agent in self.agents:
            agent.message(*args, **kwargs)

    def log_new_slot(self, obj: ComponentOrGame, slot: WeakComponentSlot):
        """
        Args:
            obj: The object which has a new slot.
            slot_relative_address: The new slot's key.
            slot: The new slot's value.
        """
        if self.agents[0] is None:
            return  # Return early if the agents are not initialized yet
        for agent_id, agent in zip(self.agent_ids, self.agents, strict=True):
            if obj.can_be_seen_by_recursive(agent_id):
                update = {
                    "op": "add",
                    "key": slot.get_address(),
                    "value": slot.html(viewer_id=agent_id),
                }
                agent.update([update])

    def log_delete_slot(self, obj: ComponentOrGame, slot_relative_address: str):
        """
        Args:
            obj: The object which has one fewer slot.
            slot_relative_address: The key of the slot that's deleted.
        """
        if self.agents[0] is None:
            return
        for agent_id, agent in zip(self.agent_ids, self.agents, strict=True):
            if obj.can_be_seen_by_recursive(agent_id):
                update = {
                    "op": "remove",
                    "key": obj.get_slot_address() + "/" + slot_relative_address,
                }
                agent.update([update])

    def log_component_update(
        self,
        slot: WeakComponentSlot,
        only_update: AgentId | None = None,
        *,
        force_reveal=False,
    ):
        address = slot.get_address()

        if only_update is None:
            agents = zip(self.agent_ids, self.agents, strict=True)
        else:
            agents = [(only_update, self.agents[only_update])]
        if self.agents[0] is None:
            return  # Return early if the agents are not initialized yet
        for agent_id, agent in agents:
            agent.update(
                [
                    {
                        "op": "replace",
                        "key": address,
                        "value": slot.html(
                            viewer_id=agent_id, force_reveal=force_reveal
                        ),
                    }
                ]
            )

    def set_agents(self, agents: list[Agent]):
        self.agents = agents

    def get_html_for_agent_ref(self, agent_ref: Any) -> "Html":
        """
        Args:
            agent_ref: something tied to an agent that the agent can recognize.
                       For example, a Session for a NetworkAgent.
        """
        # I chose not to have agent_ref be the agent itself because lower-level
        # components like the server are not aware of the agent type.
        for agent_id, agent in zip(self.agent_ids, self.agents, strict=True):
            if agent == agent_ref:
                return self.html(viewer_id=agent_id)
        raise ValueError("agent_ref was not recognized by any agent!")

    @abstractmethod
    def play_game(self) -> GameSummary: ...


# TODO: possible improvements:
# Game could detect automatically when Components exist as class properties
# and translate them to ComponentSlotProperties
