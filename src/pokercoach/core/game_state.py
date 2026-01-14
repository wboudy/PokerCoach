"""Core data models for poker game state."""

from dataclasses import dataclass, field
from enum import Enum, auto


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
    player_position: Position | None = None

    def __str__(self) -> str:
        if self.type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
            return f"{self.type.value} {self.amount}"
        return self.type.value


@dataclass
class Player:
    """A player in the hand."""

    position: Position
    stack: float
    hand: Hand | None = None
    is_hero: bool = False


@dataclass
class GameState:
    """Complete state of a poker hand."""

    # Game configuration
    game_type: str = "NLHE"  # No Limit Hold'em
    stakes: tuple[float, float] = (1.0, 2.0)  # SB/BB

    # Players
    players: list[Player] = field(default_factory=list)
    hero_position: Position | None = None

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
    def hero(self) -> Player | None:
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
        """
        Convert GameState to TexasSolver input format.

        Returns a string containing commands that can be written to a file
        and passed to TexasSolver via the -i flag.

        Format example:
            set_pot 100
            set_effective_stack 500
            set_board Qs,Jh,2h
            set_range_ip AA,KK,QQ,AKs,AKo
            set_range_oop AA,KK,QQ,AKs,AKo
        """
        lines: list[str] = []

        # Set pot size (in chips, typically relative to BB)
        lines.append(f"set_pot {self.pot:.0f}")

        # Set effective stack (in BB)
        lines.append(f"set_effective_stack {self.effective_stack:.0f}")

        # Set board cards (comma-separated, only for postflop)
        if self.board.cards:
            board_str = ",".join(str(card) for card in self.board.cards)
            lines.append(f"set_board {board_str}")

        # Add action history as comment for context
        # TexasSolver needs the current decision point, not full history
        # But we encode the action history for documentation
        if self.actions:
            action_history = self._format_action_history()
            lines.append(f"# Action history: {action_history}")

        return "\n".join(lines)

    def _format_action_history(self) -> str:
        """
        Format action history with bet sizes relative to pot/BB.

        Returns human-readable string like:
            "BTN r3x, SB call, BB fold"
        """
        if not self.actions:
            return ""

        formatted_actions: list[str] = []
        bb = self.stakes[1]  # Big blind amount
        running_pot = self.stakes[0] + self.stakes[1]  # Start with blinds

        for action in self.actions:
            pos_str = ""
            if action.player_position:
                pos_str = f"{action.player_position.value} "

            if action.type == ActionType.FOLD:
                formatted_actions.append(f"{pos_str}fold")
            elif action.type == ActionType.CHECK:
                formatted_actions.append(f"{pos_str}check")
            elif action.type == ActionType.CALL:
                formatted_actions.append(f"{pos_str}call")
                running_pot += action.amount
            elif action.type == ActionType.BET:
                # Format bet as percentage of pot or xBB
                if running_pot > 0:
                    pot_pct = (action.amount / running_pot) * 100
                    formatted_actions.append(f"{pos_str}bet {pot_pct:.0f}%")
                else:
                    bb_mult = action.amount / bb
                    formatted_actions.append(f"{pos_str}bet {bb_mult:.1f}x")
                running_pot += action.amount
            elif action.type == ActionType.RAISE:
                # Format raise as xBB for preflop, pot% for postflop
                if self.street == Street.PREFLOP:
                    bb_mult = action.amount / bb
                    formatted_actions.append(f"{pos_str}raise {bb_mult:.1f}x")
                else:
                    if running_pot > 0:
                        pot_pct = (action.amount / running_pot) * 100
                        formatted_actions.append(f"{pos_str}raise {pot_pct:.0f}%")
                    else:
                        formatted_actions.append(f"{pos_str}raise {action.amount}")
                running_pot += action.amount
            elif action.type == ActionType.ALL_IN:
                bb_mult = action.amount / bb
                formatted_actions.append(f"{pos_str}all-in {bb_mult:.1f}x")
                running_pot += action.amount

        return ", ".join(formatted_actions)

    def to_solver_config(
        self,
        ip_range: str = "",
        oop_range: str = "",
        bet_sizes: dict[str, list[int]] | None = None,
        threads: int = 6,
        accuracy: float = 0.3,
        max_iterations: int = 1000,
    ) -> str:
        """
        Generate complete TexasSolver configuration file content.

        Args:
            ip_range: In-position player range (e.g., "AA,KK,QQ,AKs,AKo")
            oop_range: Out-of-position player range
            bet_sizes: Dict mapping street to list of bet sizes as pot percentages
                       e.g., {"flop": [33, 50, 75], "turn": [50, 75], "river": [50, 100]}
            threads: Number of solver threads
            accuracy: Target exploitability percentage
            max_iterations: Maximum solver iterations

        Returns:
            Complete config file content for TexasSolver
        """
        lines: list[str] = []

        # Basic game state
        lines.append(f"set_pot {self.pot:.0f}")
        lines.append(f"set_effective_stack {self.effective_stack:.0f}")

        # Board (only for postflop)
        if self.board.cards:
            board_str = ",".join(str(card) for card in self.board.cards)
            lines.append(f"set_board {board_str}")

        # Ranges
        if ip_range:
            lines.append(f"set_range_ip {ip_range}")
        if oop_range:
            lines.append(f"set_range_oop {oop_range}")

        # Bet sizes (default to common sizes if not specified)
        if bet_sizes is None:
            bet_sizes = {
                "flop": [33, 50, 75],
                "turn": [50, 75, 100],
                "river": [50, 75, 100],
            }

        # Configure bet sizes for each street and position
        for street_name, sizes in bet_sizes.items():
            for size in sizes:
                lines.append(f"set_bet_sizes oop,{street_name},bet,{size}")
                lines.append(f"set_bet_sizes ip,{street_name},bet,{size}")
                # Also set raise sizes
                lines.append(f"set_bet_sizes oop,{street_name},raise,{size}")
                lines.append(f"set_bet_sizes ip,{street_name},raise,{size}")

        # Solver configuration
        lines.append(f"set_thread_num {threads}")
        lines.append(f"set_accuracy {accuracy}")
        lines.append(f"set_max_iteration {max_iterations}")

        # Build and solve commands
        lines.append("build_tree")
        lines.append("start_solve")

        return "\n".join(lines)
