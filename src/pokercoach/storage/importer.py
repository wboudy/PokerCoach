"""Hand history import from various poker sites."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pokercoach.storage.models import (
    HandRecord,
    Position,
)


class HandRepository(Protocol):
    """Protocol for hand storage repository."""

    def save_hand(self, hand: HandRecord) -> HandRecord:
        """Save a hand record."""
        ...


@dataclass
class ImportResult:
    """Results from a hand history import operation."""

    hands_imported: int = 0
    hands_failed: int = 0
    errors: list[str] = field(default_factory=list)


class PokerStarsParser:
    """Parser for PokerStars hand history format.

    Parses the standard PokerStars text-based hand history format
    and extracts hand data for storage.
    """

    # Regex patterns for parsing
    HAND_START = re.compile(r"PokerStars Hand #(\d+):")
    STAKES = re.compile(r"\$?([\d.]+)/\$?([\d.]+)")
    TABLE_INFO = re.compile(r"Table '([^']+)' (\d+)-max")
    BUTTON = re.compile(r"Seat #(\d+) is the button")
    SEAT = re.compile(r"Seat (\d+): (\w+) \(\$?([\d.]+)")
    HOLE_CARDS = re.compile(r"Dealt to (\w+) \[([^\]]+)\]")
    # Board patterns - PokerStars format: *** FLOP *** [Ah 7d 2c], *** TURN *** [Ah 7d 2c] [Js]
    BOARD = re.compile(r"\*\*\* (FLOP|TURN|RIVER) \*\*\* (\[[^\]]+\](?:\s*\[[^\]]+\])?)")
    ACTION = re.compile(r"(\w+): (folds|checks|calls|bets|raises)(?: \$?([\d.]+))?")
    COLLECTED = re.compile(r"(\w+) collected \$?([\d.]+)")
    SUMMARY_POT = re.compile(r"Total pot \$?([\d.]+)")

    def __init__(self, hero_name: str = "Hero"):
        """Initialize parser with hero's screen name.

        Args:
            hero_name: The screen name of the hero player
        """
        self.hero_name = hero_name

    def parse(self, content: str) -> list[HandRecord]:
        """Parse hand history content and return list of hand records.

        Args:
            content: Raw hand history text content

        Returns:
            List of parsed HandRecord objects
        """
        hands = []
        hand_texts = self._split_hands(content)

        for hand_text in hand_texts:
            try:
                hand = self._parse_single_hand(hand_text)
                if hand:
                    hands.append(hand)
            except Exception:
                # Log error but continue parsing other hands
                continue

        return hands

    def _split_hands(self, content: str) -> list[str]:
        """Split content into individual hand texts.

        Args:
            content: Full hand history content

        Returns:
            List of individual hand text blocks
        """
        # Split on hand start pattern
        parts = re.split(r"(?=PokerStars Hand #)", content)
        return [p.strip() for p in parts if p.strip() and "PokerStars Hand #" in p]

    def _parse_single_hand(self, text: str) -> HandRecord | None:
        """Parse a single hand from text.

        Args:
            text: Text of a single hand

        Returns:
            HandRecord or None if parsing failed
        """
        lines = text.strip().split("\n")

        # Extract hand ID
        match = self.HAND_START.search(lines[0])
        if not match:
            return None
        hand_id = match.group(1)

        # Extract table info
        table_size = 6  # Default
        button_seat = 1
        for line in lines[:10]:
            if match := self.TABLE_INFO.search(line):
                table_size = int(match.group(2))
            if match := self.BUTTON.search(line):
                button_seat = int(match.group(1))

        # Parse seats and find hero
        seats: dict[int, dict[str, Any]] = {}
        hero_seat = None
        for line in lines:
            if match := self.SEAT.match(line):
                seat_num = int(match.group(1))
                player_name = match.group(2)
                stack = float(match.group(3))
                seats[seat_num] = {"name": player_name, "stack": stack}
                if player_name == self.hero_name:
                    hero_seat = seat_num

        # Calculate hero position from button and seat
        hero_position = None
        if hero_seat and button_seat:
            hero_position = self._calculate_position(
                hero_seat, button_seat, table_size, len(seats)
            )

        # Parse hole cards
        hero_card1 = None
        hero_card2 = None
        for line in lines:
            if (match := self.HOLE_CARDS.search(line)) and match.group(1) == self.hero_name:
                cards = match.group(2).split()
                if len(cards) >= 2:
                    hero_card1 = self._normalize_card(cards[0])
                    hero_card2 = self._normalize_card(cards[1])

        # Require hero cards to be present for a valid hand
        if hero_card1 is None or hero_card2 is None:
            return None

        # Parse board
        flop1 = flop2 = flop3 = turn = river = None
        for line in lines:
            if match := self.BOARD.search(line):
                street = match.group(1)
                # Extract all bracket contents
                board_str = match.group(2)
                # Parse brackets - for TURN/RIVER format: [Ah 7d 2c] [Js]
                brackets = re.findall(r'\[([^\]]+)\]', board_str)

                if street == "FLOP" and brackets:
                    flop_cards = brackets[0].split()
                    if len(flop_cards) >= 3:
                        flop1 = self._normalize_card(flop_cards[0])
                        flop2 = self._normalize_card(flop_cards[1])
                        flop3 = self._normalize_card(flop_cards[2])
                elif street == "TURN" and len(brackets) >= 2:
                    # Turn has flop in first bracket, turn card in second
                    turn_cards = brackets[1].split()
                    if turn_cards:
                        turn = self._normalize_card(turn_cards[0])
                elif street == "RIVER" and len(brackets) >= 2:
                    # River has flop+turn in first bracket, river card in second
                    river_cards = brackets[1].split()
                    if river_cards:
                        river = self._normalize_card(river_cards[0])

        # Parse results
        hero_won = 0.0
        went_to_showdown = 0
        for line in lines:
            if (match := self.COLLECTED.search(line)) and match.group(1) == self.hero_name:
                hero_won = float(match.group(2))
            if "*** SHOW DOWN ***" in line or "shows [" in line.lower():
                went_to_showdown = 1

        # Create hand record
        return HandRecord(
            hand_id=hand_id,
            timestamp=datetime.now(UTC),
            hero_card1=hero_card1,
            hero_card2=hero_card2,
            flop_card1=flop1,
            flop_card2=flop2,
            flop_card3=flop3,
            turn_card=turn,
            river_card=river,
            position=hero_position,
            table_size=table_size,
            button_seat=button_seat,
            hero_seat=hero_seat,
            went_to_showdown=went_to_showdown,
            hero_won=hero_won,
        )

    def _calculate_position(
        self, hero_seat: int, button_seat: int, max_seats: int, active_players: int
    ) -> Position:
        """Calculate hero's position based on seat and button.

        Args:
            hero_seat: Hero's seat number
            button_seat: Button's seat number
            max_seats: Maximum seats at table
            active_players: Number of active players

        Returns:
            Position enum value
        """
        # Calculate seats from button (0 = button)
        if hero_seat == button_seat:
            return Position.BTN

        # Simple position mapping for 6-max
        seats_from_btn = (hero_seat - button_seat) % max_seats

        # Map to positions (6-max typical)
        position_map = {
            0: Position.BTN,
            1: Position.SB,
            2: Position.BB,
            3: Position.UTG,
            4: Position.HJ,
            5: Position.CO,
        }

        return position_map.get(seats_from_btn, Position.MP)

    def _normalize_card(self, card: str) -> str:
        """Normalize card string to standard format (e.g., 'As', 'Kd').

        Args:
            card: Raw card string

        Returns:
            Normalized 2-character card string
        """
        card = card.strip()
        if len(card) < 2:
            return card

        rank = card[0].upper()
        suit = card[1].lower()

        return f"{rank}{suit}"


class HandHistoryImporter:
    """Import hand histories from various poker sites.

    Supports importing from strings, files, and directories.
    Auto-detects poker site format where possible.
    """

    def __init__(self, repository: HandRepository, hero_name: str = "Hero"):
        """Initialize importer with storage repository.

        Args:
            repository: Repository for storing imported hands
            hero_name: Hero's screen name for identifying their cards
        """
        self._repository = repository
        self._parsers = {
            "pokerstars": PokerStarsParser(hero_name=hero_name),
        }

    def import_from_string(
        self, content: str, site: str = "pokerstars"
    ) -> ImportResult:
        """Import hands from a string of hand history text.

        Args:
            content: Hand history text content
            site: Poker site identifier (default: pokerstars)

        Returns:
            ImportResult with statistics
        """
        result = ImportResult()

        parser = self._parsers.get(site.lower())
        if not parser:
            result.errors.append(f"Unknown site: {site}")
            return result

        try:
            hands = parser.parse(content)
            for hand in hands:
                try:
                    self._repository.save_hand(hand)
                    result.hands_imported += 1
                except Exception as e:
                    result.hands_failed += 1
                    result.errors.append(str(e))
        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        return result

    def import_from_file(
        self, path: Path, site: str | None = None
    ) -> ImportResult:
        """Import hands from a file.

        Args:
            path: Path to hand history file
            site: Optional site identifier (auto-detected if not provided)

        Returns:
            ImportResult with statistics
        """
        if not path.exists():
            return ImportResult(errors=[f"File not found: {path}"])

        content = path.read_text(encoding="utf-8", errors="ignore")

        # Auto-detect site if not provided
        if site is None:
            site = self._detect_site(content)

        return self.import_from_string(content, site)

    def import_from_directory(
        self, directory: Path, site: str | None = None
    ) -> ImportResult:
        """Import all hand history files from a directory.

        Args:
            directory: Directory containing hand history files
            site: Optional site identifier

        Returns:
            Combined ImportResult for all files
        """
        result = ImportResult()

        if not directory.is_dir():
            result.errors.append(f"Not a directory: {directory}")
            return result

        # Find all text files
        for file_path in directory.glob("*.txt"):
            file_result = self.import_from_file(file_path, site)
            result.hands_imported += file_result.hands_imported
            result.hands_failed += file_result.hands_failed
            result.errors.extend(file_result.errors)

        return result

    def _detect_site(self, content: str) -> str:
        """Auto-detect poker site from content.

        Args:
            content: Hand history content

        Returns:
            Site identifier string
        """
        if "PokerStars" in content:
            return "pokerstars"
        elif "GGPoker" in content or "GG Network" in content:
            return "ggpoker"
        elif "partypoker" in content.lower():
            return "partypoker"
        else:
            return "pokerstars"  # Default
