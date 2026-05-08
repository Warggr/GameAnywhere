from dataclasses import dataclass
from enum import Enum, auto, unique
from importlib.resources import files
from typing import TYPE_CHECKING, Union

from game_anywhere.components import (
    ComponentSlot,
    ComponentSlotProperty,
    Dict,
    List,
    PerPlayer,
)
from game_anywhere.components.component import Component, PerPlayerComponent
from game_anywhere.components.traditional.cards import Deck, DiscardPile
from game_anywhere.core import AgentId, GameSummary, TurnBasedGame
from game_anywhere.ui import Html, tag
from game_anywhere.ui.display_styles import FlippedChips, hand_fan

if TYPE_CHECKING:
    from pathlib import Path


@unique
class Color(Enum):
    WHITE = auto()
    YELLOW = auto()
    RED = auto()
    BLUE = auto()
    GREEN = auto()


@dataclass
class HanabiCard(Component):
    color: Color
    value: int

    HIDDEN_HTML = "??"

    def html(self, viewer_id=None) -> Html:  # override
        return tag.div(
            str(self.value),
            style="color: "
            + self.color.name.lower()
            + f"; background-image: url(/assets/Hanabi/cards/{self.color.name.lower()}_{self.value}.png); height: 3em; width: 2em;",
        )


def default_hanabi_deck() -> list[HanabiCard]:
    deck = []
    for color in Color:
        for value in (1, 2, 3, 4, 5):
            if value == 1:
                deck += [HanabiCard(color, value)] * 3
            elif value == 5:
                deck.append(HanabiCard(color, value))
            else:
                deck += [HanabiCard(color, value)] * 2
    return deck


class EveryoneCanSeeItExceptMyself(ComponentSlot):
    # override
    def can_be_seen_by(self, viewer_id=None):
        return viewer_id is not None and viewer_id != self.owner_id


class HanabiPerPlayerComponent(PerPlayerComponent):
    cards = ComponentSlotProperty[List[HanabiCard]](display_as=hand_fan)


class Hanabi(TurnBasedGame):
    @dataclass
    class Summary(GameSummary):
        cards_played: int

        def get_winner(self) -> AgentId:
            return GameSummary.NO_WINNER

    nb_lives = ComponentSlotProperty[int]()
    nb_hints = ComponentSlotProperty[int](
        display_as=FlippedChips(
            front=tag.img(src="/assets/Hanabi/hint_active.png", style="width: 1em;"),
            back=tag.img(src="/assets/Hanabi/hint_inactive.png", style="width: 1em;"),
            maxi=8,
        )
    )
    deck = ComponentSlotProperty[Deck[HanabiCard]]()
    players = PerPlayer(HanabiPerPlayerComponent)
    stacks = ComponentSlotProperty[Dict[Color, List[HanabiCard]]]()
    discard_pile = ComponentSlotProperty[DiscardPile[HanabiCard]]()
    MAX_HINTS = 8

    CONFIG_SCHEMA = {
        "properties": {"_num_players": {"type": "integer", "minimum": 3, "maximum": 6}}
    }

    @classmethod
    def get_asset_dir(cls) -> Path:
        return files("game_anywhere_examples.hanabi") / "assets"

    def __init__(self, agent_descriptions, *args, **kwargs):
        super().__init__(*args, agent_descriptions=agent_descriptions, **kwargs)
        self.deck = Deck(default_hanabi_deck(), shuffled=True)
        self.nb_hints = self.MAX_HINTS
        self.nb_lives = 3
        self.stacks = Dict[Color, List]()
        self.discard_pile = DiscardPile()

        nb_players = len(agent_descriptions)
        assert 2 <= nb_players <= 5, "Hanabi can be played only between 2 and 5 players"
        CARDS_PER_PLAYER = 5 if nb_players <= 3 else 4
        for i, player in enumerate(self.players):
            player.cards = List(
                self.deck.draw(CARDS_PER_PLAYER),
                slotClass=EveryoneCanSeeItExceptMyself,
                owner_id=i,
            )

    def turn(self) -> Union["Hanabi.Summary", None]:
        options = ["Place card", "Cycle card"]
        if self.nb_hints > 0:
            options.append("Give hint")
        choice = self.get_current_agent().text_choice(options)
        if choice == "Place card":
            card = (
                self.get_current_agent()
                .choose_one_component_slot(
                    [
                        slot
                        for slot in self.players[self.get_current_agent_index()]
                        .cards.get_slots()
                        .values()
                    ]
                )
                .content
            )
            self.players[self.get_current_agent_index()].cards.remove(card)
            if card.color not in self.stacks and card.value == 1:
                self.stacks[card.color] = List([card])
            elif (
                card.color in self.stacks
                and self.stacks[card.color][-1].value == card.value - 1
            ):
                self.stacks[card.color].append(card)
            else:
                self.discard_pile.append(card)
                self.nb_lives -= 1
                if self.nb_lives == 0:
                    return self.Summary(
                        sum(len(stack) for stack in self.stacks.values())
                    )
            self.players[self.get_current_agent_index()].cards.extend(self.deck.draw())
        elif choice == "Cycle card":
            card_slot = self.get_current_agent().choose_one_component_slot(
                list(
                    self.players[self.get_current_agent_index()]
                    .cards.get_slots()
                    .values()
                )
            )
            card = card_slot.take()
            self.discard_pile.append(card)
            self.players[self.get_current_agent_index()].cards.extend(self.deck.draw())
            if self.nb_hints < self.MAX_HINTS:
                self.nb_hints += 1
        elif choice == "Give hint":
            player_hinted = (
                self.get_current_agent()
                .choose_one_component_slot(
                    [
                        slot
                        for i, slot in enumerate(self.players.get_slots().values())
                        if i != self.get_current_agent_index()
                    ]
                )
                .content
            )
            options = {}
            for color in Color:
                options[str(color)] = color
            for i in (1, 2, 3, 4, 5):
                options[str(i)] = i
            hint_key = self.get_current_agent().text_choice(list(options.keys()))
            hint_key = options[hint_key]
            hint_value = []
            for slot in player_hinted.cards.get_slots().values():
                if (
                    type(hint_key) is int
                    and slot.content.value == hint_key
                    or type(hint_key) is Color
                    and slot.content.color == hint_key
                ):
                    hint_value.append(
                        {
                            "op": "add",
                            "key": slot.get_address() + "/hint",
                            "value": f"is {hint_key}",
                        }
                    )
                else:
                    hint_value.append(
                        {
                            "op": "add",
                            "key": slot.get_address() + "/hint",
                            "value": f"is not {hint_key}",
                        }
                    )
            self.agents[player_hinted.owner_id].update(hint_value)

            self.nb_hints -= 1
        else:
            raise AssertionError(f"Unrecognized choice: {choice}")
