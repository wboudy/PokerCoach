"""Hand history parsing from various formats."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from pokercoach.core.game_state import (
    Action,
    ActionType,
    Board,
    Card,
    GameState,
    Hand,
    Player,
    Position,
)


@dataclass
class ParsedHand:
    """A fully parsed hand from history."""

    hand_id: str
    timestamp: datetime
    game_state: GameState
    actions_by_street: dict[str, list[Action]]
    showdown_hands: dict[Position, Hand]
    winners: list[Position]
    pot_won: float
    rake: float = 0.0


class HandHistoryParser(ABC):
    """Abstract base class for hand history parsers."""

    @abstractmethod
    def parse_file(self, path: Path) -> Iterator[ParsedHand]:
        """
        Parse a hand history file.

        Args:
            path: Path to hand history file

        Yields:
            ParsedHand objects
        """
        pass

    @abstractmethod
    def parse_text(self, text: str) -> Iterator[ParsedHand]:
        """
        Parse hand history from text.

        Args:
            text: Hand history text

        Yields:
            ParsedHand objects
        """
        pass


class PokerStarsParser(HandHistoryParser):
    """Parser for PokerStars hand history format."""

    def parse_file(self, path: Path) -> Iterator[ParsedHand]:
        """Parse PokerStars hand history file."""
        with open(path, encoding="utf-8") as f:
            text = f.read()
        yield from self.parse_text(text)

    def parse_text(self, text: str) -> Iterator[ParsedHand]:
        """Parse PokerStars hand history text."""
        # Split into individual hands
        hands = text.split("\n\n\n")

        for hand_text in hands:
            if not hand_text.strip():
                continue

            try:
                parsed = self._parse_single_hand(hand_text)
                if parsed:
                    yield parsed
            except Exception as e:
                # Log parsing error but continue
                print(f"Error parsing hand: {e}")
                continue

    def _parse_single_hand(self, text: str) -> Optional[ParsedHand]:
        """Parse a single hand from text."""
        lines = text.strip().split("\n")
        if not lines:
            return None

        # Parse header line
        header = lines[0]
        if "PokerStars" not in header and "Hand #" not in header:
            return None

        # TODO: Implement full PokerStars parsing
        # This is a complex task - the poker-log-parser library
        # should be used for production

        raise NotImplementedError(
            "Full PokerStars parsing not yet implemented. "
            "Consider using poker-log-parser library."
        )


class PHHParser(HandHistoryParser):
    """
    Parser for Poker Hand History (PHH) format.

    PHH is an academic standard format designed for machine parsing.
    See: https://arxiv.org/html/2312.11753v2
    """

    def parse_file(self, path: Path) -> Iterator[ParsedHand]:
        """Parse PHH format file."""
        # TODO: Implement PHH parsing
        raise NotImplementedError("PHH parsing not yet implemented")

    def parse_text(self, text: str) -> Iterator[ParsedHand]:
        """Parse PHH format text."""
        raise NotImplementedError("PHH parsing not yet implemented")


def get_parser(format: str) -> HandHistoryParser:
    """
    Get appropriate parser for format.

    Args:
        format: One of 'pokerstars', 'phh'

    Returns:
        HandHistoryParser instance
    """
    parsers = {
        "pokerstars": PokerStarsParser,
        "phh": PHHParser,
    }

    if format not in parsers:
        raise ValueError(f"Unknown format: {format}. Available: {list(parsers.keys())}")

    return parsers[format]()
