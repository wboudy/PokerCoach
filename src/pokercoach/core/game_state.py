"""Core data models for poker game state."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class Suit(Enum):
    """Card suits."""

    CLUBS = "c"
    DIAMONDS = "d"
    HEARTS = "h"
    SPADES = "s"

    def __str__(self) -> str:
        return self.value


class Rank(Enum):
    """Card ranks."""

    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"

    def __str__(self) -> str:
        return self.value

    @property
    def value_int(self) -> int:
        """Numeric value for comparisons."""
        return list(Rank).index(self) + 2


@dataclass(frozen=True)
class Card:
    """A single playing card."""

    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    @classmethod
    def from_string(cls, s: str) -> "Card":
        """Parse card from string like 'As' or 'Td'."""
        if len(s) != 2:
            raise ValueError(f"Invalid card string: {s}")
        rank = Rank(s[0].upper())
        suit = Suit(s[1].lower())
        return cls(rank=rank, suit=suit)


@dataclass(frozen=True)
class Hand:
    """A player's hole cards."""

    cards: tuple[Card, Card]

    def __str__(self) -> str:
        return f"{self.cards[0]}{self.cards[1]}"

    @classmethod
    def from_string(cls, s: str) -> "Hand":
        """Parse hand from string like 'AsKs' or 'AhKd'."""
        if len(s) != 4:
            raise ValueError(f"Invalid hand string: {s}")
        return cls(
            cards=(
                Card.from_string(s[0:2]),
                Card.from_string(s[2:4]),
            )
        )

    @property
    def is_suited(self) -> bool:
        return self.cards[0].suit == self.cards[1].suit

    @property
    def is_pair(self) -> bool:
        return self.cards[0].rank == self.cards[1].rank


class Street(Enum):
    """Betting streets."""

    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()


@dataclass
class Board:
    """Community cards."""

    cards: list[Card] = field(default_factory=list)

    def __str__(self) -> str:
        return " ".join(str(c) for c in self.cards)

    @property
    def street(self) -> Street:
        """Current street based on board cards."""
        n = len(self.cards)
        if n == 0:
            return Street.PREFLOP
        elif n == 3:
            return Street.FLOP
        elif n == 4:
            return Street.TURN
        elif n == 5:
            return Street.RIVER
        else:
            raise ValueError(f"Invalid board size: {n}")

    def add_card(self, card: Card) -> None:
        """Add a card to the board."""
        if len(self.cards) >= 5:
            raise ValueError("Board already has 5 cards")
        self.cards.append(card)


class Position(Enum):
    """Player positions."""

    BTN = "BTN"  # Button
    SB = "SB"  # Small Blind
    BB = "BB"  # Big Blind
    UTG = "UTG"  # Under the Gun
    UTG1 = "UTG+1"
    UTG2 = "UTG+2"
    MP = "MP"  # Middle Position
    MP1 = "MP+1"
    HJ = "HJ"  # Hijack
    CO = "CO"  # Cutoff


class ActionType(Enum):
    """Types of poker actions."""

    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all-in"


@dataclass
class Action:
    """A poker action taken by a player."""

    type: ActionType
    amount: float = 0.0
    player_position: Optional[Position] = None

    def __str__(self) -> str:
        if self.type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
            return f"{self.type.value} {self.amount}"
        return self.type.value


@dataclass
class Player:
    """A player in the hand."""

    position: Position
    stack: float
    hand: Optional[Hand] = None
    is_hero: bool = False


@dataclass
class GameState:
    """Complete state of a poker hand."""

    # Game configuration
    game_type: str = "NLHE"  # No Limit Hold'em
    stakes: tuple[float, float] = (1.0, 2.0)  # SB/BB

    # Players
    players: list[Player] = field(default_factory=list)
    hero_position: Optional[Position] = None

    # Current state
    board: Board = field(default_factory=Board)
    pot: float = 0.0
    actions: list[Action] = field(default_factory=list)

    # Effective stack for calculations
    effective_stack: float = 100.0  # In BBs

    @property
    def street(self) -> Street:
        """Current street."""
        return self.board.street

    @property
    def hero(self) -> Optional[Player]:
        """Get hero player."""
        for p in self.players:
            if p.is_hero:
                return p
        return None

    def add_action(self, action: Action) -> None:
        """Add an action to the hand history."""
        self.actions.append(action)
        if action.type in (ActionType.BET, ActionType.RAISE, ActionType.CALL, ActionType.ALL_IN):
            self.pot += action.amount

    def to_solver_format(self) -> str:
        """Convert to solver input format."""
        # Implementation depends on solver
        raise NotImplementedError
