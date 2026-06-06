from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto, unique
from importlib.resources import files
from typing import TYPE_CHECKING, Union

from game_anywhere.components import (
    AbstractComposite,
    Component,
    ComponentSlot,
    ComponentSlotProperty,
    Composite,
    Dict,
    List,
    PerPlayer,
)
from game_anywhere.components.component import PerPlayerComponent
from game_anywhere.components.traditional.cards import Deck, DiscardPile
from game_anywhere.core import AgentId, GameSummary, TurnBasedGame
from game_anywhere.ui import Html, tag
from game_anywhere.ui.display_styles import FlippedChips, hand_fan

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


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
            + f"; background-image: url(/assets/Hanabi/cards/{self.color.name.lower()}_{self.value}.png); height: 9em; width: 6em; background-size: cover;",
        )


class EveryoneCanSeeItExceptMyself(ComponentSlot):
    # override
    def can_be_seen_by(self, viewer_id=None):
        return viewer_id is not None and viewer_id != self.owner_id


class HanabiHandCard(Composite):
    card = ComponentSlotProperty[HanabiCard](EveryoneCanSeeItExceptMyself)
    hints = ComponentSlotProperty[list[str]]()

    def __init__(self, card: HanabiCard):
        super().__init__()
        self.card = card
        self.hints = List()

    def wrap_slot_html(self, *args, **kwargs):
        # Do not use the Composite slot HTML with a label
        return AbstractComposite.wrap_slot_html(self, *args, **kwargs)

    def merge_slot_html(self, items: list[Any]) -> Any:
        card_html, hints_html = items
        card_html.attrs["style"] = (
            card_html.attrs.get("style", "") + "position: absolute; top: 0;"
        )
        hints_html.attrs["style"] = (
            hints_html.attrs.get("style", "") + "color: lightgray;"
        )
        return tag.div(
            card_html,
            hints_html,
            style="position: relative;",
            **{"class": "hanabi-card"},
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


class HanabiPerPlayerComponent(PerPlayerComponent):
    cards = ComponentSlotProperty[List[HanabiHandCard]](display_as=hand_fan)


class Hanabi(TurnBasedGame):
    @dataclass
    class Summary(GameSummary):
        cards_played: int

        def get_winner(self) -> AgentId:
            return GameSummary.NO_WINNER

    nb_lives = ComponentSlotProperty[int]()
    nb_hints = ComponentSlotProperty[int](
        display_as=FlippedChips(
            front=tag.img(
                src="/assets/Hanabi/hint_active.png",
                style="max-width: 5vh; max-height: 5vh",
            ),
            back=tag.img(
                src="/assets/Hanabi/hint_inactive.png",
                style="max-width: 5vh; max-height: 5vh",
            ),
            maxi=8,
        )
    )
    deck = ComponentSlotProperty[Deck[HanabiCard]]()
    players = PerPlayer(HanabiPerPlayerComponent)
    stacks = ComponentSlotProperty[Dict[Color, List[HanabiCard]]]()
    discard_pile = ComponentSlotProperty[DiscardPile[HanabiCard]]()
    MAX_HINTS = 8

    CONFIG_SCHEMA = {
        "properties": {"_num_players": {"type": "integer", "minimum": 3, "maximum": 5}}
    }

    @classmethod
    def get_asset_dir(cls) -> Path:
        return files("game_anywhere_examples.hanabi") / "assets"

    def __init__(self, agents, *args, **kwargs):
        super().__init__(agents, *args, **kwargs)
        self.deck = Deck(default_hanabi_deck(), shuffled=True)
        self.nb_hints = self.MAX_HINTS
        self.nb_lives = 3
        self.stacks = Dict[Color, List]()
        self.discard_pile = DiscardPile()

        nb_players = len(agents)
        assert 2 <= nb_players <= 5, "Hanabi can be played only between 2 and 5 players"
        CARDS_PER_PLAYER = 5 if nb_players <= 3 else 4
        for player, agent_id in zip(self.players, self.agent_ids, strict=True):
            player.cards = List(
                map(HanabiHandCard, self.deck.draw(CARDS_PER_PLAYER)),
                owner_id=agent_id,
            )

    def turn(self) -> Union["Hanabi.Summary", None]:
        options = ["Place card", "Cycle card"]
        if self.nb_hints > 0:
            options.append("Give hint")
        choice = self.get_current_agent().text_choice(options)
        if choice == "Place card":
            card = (
                self.get_current_agent()
                .choose_one(
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
            card = card.card
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
            (drawn_card,) = self.deck.draw()
            self.players[self.get_current_agent_index()].cards.append(
                HanabiHandCard(drawn_card)
            )
        elif choice == "Cycle card":
            card_slot = self.get_current_agent().choose_one(
                list(
                    self.players[self.get_current_agent_index()]
                    .cards.get_slots()
                    .values()
                )
            )
            card = card_slot.take().card
            self.discard_pile.append(card)
            self.players[self.get_current_agent_index()].cards.extend(self.deck.draw())
            if self.nb_hints < self.MAX_HINTS:
                self.nb_hints += 1
        elif choice == "Give hint":
            player_hinted = (
                self.get_current_agent()
                .choose_one(
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
            for slot in player_hinted.cards.get_slots().values():
                if (
                    type(hint_key) is int
                    and slot.content.card.value == hint_key
                    or type(hint_key) is Color
                    and slot.content.card.color == hint_key
                ):
                    slot.content.hints.append(f"is {hint_key}")
                else:
                    slot.content.hints.append(f"is not {hint_key}")

            self.nb_hints -= 1
        else:
            raise AssertionError(f"Unrecognized choice: {choice}")
