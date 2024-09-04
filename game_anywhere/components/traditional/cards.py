from enum import Enum, unique, auto
from typing import Iterable, TypeVar, Generic, Any
import random
from ..component import Component
from ...ui import Html, div


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
                Poker.SPADES: "♣",
                PokerCard.Color.HEARTS: "♥",
            }
            return strs[self]  # TODO: this is very non-idiomatic

        def __lt__(self, other):
            if self.__class__ == other.__class__:
                return self.value < other.value
            raise NotImplemented()

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
        def all_values(Value) -> Iterable["Value"]:
            return (Value(i + 1) for i in range(13))

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

    def html(self) -> Html:
        return str(self)


T = TypeVar("T")


class Deck(Generic[T], Component):
    def __init__(self, cards: Iterable[T], shuffled=False):
        self.cards = list(cards)
        if shuffled:
            self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self) -> T:
        return self.cards.pop()

    def html(self) -> Html:
        return div("Deck with", len(self.cards), "cards")


def fiftytwo_cards() -> Iterable[PokerCard]:
    return (
        PokerCard(color, value)
        for color in PokerCard.Color
        for value in PokerCard.Value.all_values()
    )
