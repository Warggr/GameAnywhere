import random
from enum import Enum, auto, unique
from typing import Any, Generic, Iterable, TypeVar

from ...ui import Html, tag
from ..component import Component


class PokerCard(Component):
    @unique
    class Color(Enum):
        SPADES = auto()
        HEARTS = auto()
        DIAMONDS = auto()
        CLUBS = auto()

        def __str__(self):
            strs = {
                PokerCard.Color.CLUBS: "♠",
                PokerCard.Color.DIAMONDS: "♦",
                PokerCard.Color.SPADES: "♣",
                PokerCard.Color.HEARTS: "♥",
            }
            return strs[self]  # TODO: this is very non-idiomatic

        def __lt__(self, other):
            if self.__class__ == other.__class__:
                return self.value < other.value
            raise NotImplementedError()

    class Value:
        ACE = 1
        JACK = 11
        QUEEN = 12
        KING = 13

        def __init__(self, value: int):
            assert 1 <= value <= 13
            self.value = value

        def __str__(self):
            special_values = {1: "A", 11: "J", 12: "Q", 13: "K"}
            if self.value in special_values:
                return special_values[self.value]
            else:
                return str(self.value)

        def __int__(self) -> int:
            return self.value

        def __eq__(self, other: Any) -> bool:
            try:
                return int(self) == int(other)
            except ValueError:
                return False

        def __lt__(self, other):
            return int(self) < int(other)

        def __hash__(self):
            return hash(self.value)

        @classmethod
        def all_values(cls) -> Iterable["PokerCard.Value"]:
            return (cls(i + 1) for i in range(13))

    def __init__(self, color: "PokerCard.Color", value: "PokerCard.Value"):
        self.color = color
        self.value = value

    def __str__(self):
        value = (
            self.value.value if self.value.value < 12 else self.value.value + 1
        )  # there's an additional "Knight" in the Unicode sequence
        return chr(
            ord("🂡")
            + (self.color.value - PokerCard.Color.SPADES.value) * 16
            + value
            - 1
        )

    HIDDEN_HTML = "🂠"

    def html(self, viewer_id=None) -> Html:
        return str(self)


T = TypeVar("T")


class Deck(Generic[T], Component):
    def __init__(self, cards: Iterable[T], shuffled=False):
        super().__init__()
        self.cards = list(cards)
        if shuffled:
            self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, n=1) -> T:
        if n == 1:
            return self.cards.pop()
        else:
            cards_drawn = self.cards[-n:]
            self.cards = self.cards[:-n]
            return cards_drawn

    def html(self, viewer_id=None) -> Html:
        return tag.div("Deck with", len(self.cards), "cards")


class DiscardPile(Generic[T], Component):
    def __init__(self):
        super().__init__()
        self.cards: list[T] = []

    def append(self, card: T):
        self.cards.append(card)

    def html(self, viewer_id=None):
        return tag.div("Discard pile with", len(self.cards), "cards")


def fiftytwo_cards() -> Iterable[PokerCard]:
    return (
        PokerCard(color, value)
        for color in PokerCard.Color
        for value in PokerCard.Value.all_values()
    )
