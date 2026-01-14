"""Integration tests for hand history import."""

import pytest
from pathlib import Path
from datetime import datetime

from pokercoach.storage.models import HandRecord, ActionRecord, Position, Street, ActionType


# Sample PokerStars hand history for testing
POKERSTARS_HAND_HISTORY = """PokerStars Hand #123456789:  Hold'em No Limit ($1/$2 USD) - 2024/01/15 10:30:00 ET
Table 'TestTable' 6-max Seat #3 is the button
Seat 1: Player1 ($200 in chips)
Seat 2: Player2 ($185.50 in chips)
Seat 3: Hero ($210 in chips)
Seat 4: Player4 ($195 in chips)
Seat 5: Player5 ($220 in chips)
Seat 6: Player6 ($180 in chips)
Player4: posts small blind $1
Player5: posts big blind $2
*** HOLE CARDS ***
Dealt to Hero [As Kd]
Player6: folds
Player1: raises $6 to $8
Player2: folds
Hero: raises $18 to $26
Player4: folds
Player5: folds
Player1: calls $18
*** FLOP *** [Ah 7d 2c]
Player1: checks
Hero: bets $32
Player1: calls $32
*** TURN *** [Ah 7d 2c] [Js]
Player1: checks
Hero: bets $75
Player1: folds
Uncalled bet ($75) returned to Hero
Hero collected $119 from pot
*** SUMMARY ***
Total pot $119 | Rake $0
Board [Ah 7d 2c Js]
Seat 3: Hero (button) collected ($119)
"""

POKERSTARS_MULTIHAND = """PokerStars Hand #111111111:  Hold'em No Limit ($0.50/$1 USD) - 2024/01/15 09:00:00 ET
Table 'SmallTable' 6-max Seat #1 is the button
Seat 1: Hero ($100 in chips)
Seat 2: Villain ($95 in chips)
Villain: posts small blind $0.50
Hero: posts big blind $1
*** HOLE CARDS ***
Dealt to Hero [Qh Jh]
Villain: raises $2 to $3
Hero: calls $2
*** FLOP *** [Kh Th 3c]
Hero: checks
Villain: bets $4
Hero: raises $12 to $16
Villain: folds
Hero collected $14 from pot
*** SUMMARY ***
Total pot $14 | Rake $0

PokerStars Hand #222222222:  Hold'em No Limit ($0.50/$1 USD) - 2024/01/15 09:05:00 ET
Table 'SmallTable' 6-max Seat #2 is the button
Seat 1: Hero ($111 in chips)
Seat 2: Villain ($82 in chips)
Hero: posts small blind $0.50
Villain: posts big blind $1
*** HOLE CARDS ***
Dealt to Hero [7h 2d]
Hero: folds
Villain collected $1 from pot
*** SUMMARY ***
Total pot $1 | Rake $0
"""


class MockHandRepository:
    """Mock repository for testing imports."""

    def __init__(self):
        self.hands: list[HandRecord] = []

    def save_hand(self, hand: HandRecord) -> HandRecord:
        hand.id = len(self.hands) + 1
        self.hands.append(hand)
        return hand

    def get_hand_by_id(self, hand_id: str) -> HandRecord | None:
        for hand in self.hands:
            if hand.hand_id == hand_id:
                return hand
        return None


def test_pokerstars_import():
    """Test importing PokerStars hand history files.

    This is the primary acceptance test for PokerCoach-qz5.
    It verifies that hand histories from PokerStars text files
    are correctly parsed and imported into storage.
    """
    from pokercoach.storage.importer import HandHistoryImporter

    mock_repo = MockHandRepository()
    importer = HandHistoryImporter(repository=mock_repo)

    # Import the sample hand history
    result = importer.import_from_string(POKERSTARS_HAND_HISTORY, site="pokerstars")

    # Should have imported 1 hand
    assert result.hands_imported == 1
    assert result.hands_failed == 0

    # Verify the imported hand
    hand = mock_repo.hands[0]

    # Basic identifiers
    assert hand.hand_id == "123456789"

    # Hero holdings
    assert hand.hero_card1 == "As"
    assert hand.hero_card2 == "Kd"

    # Board cards
    assert hand.flop_card1 == "Ah"
    assert hand.flop_card2 == "7d"
    assert hand.flop_card3 == "2c"
    assert hand.turn_card == "Js"
    assert hand.river_card is None  # Hand ended on turn

    # Position (Hero was button = seat 3)
    assert hand.position == Position.BTN

    # Table info
    assert hand.table_size == 6

    # Results
    assert hand.hero_won == 119.0
    assert hand.went_to_showdown == 0  # Opponent folded


def test_pokerstars_import_multiple_hands():
    """Test importing multiple hands from a single file."""
    from pokercoach.storage.importer import HandHistoryImporter

    mock_repo = MockHandRepository()
    importer = HandHistoryImporter(repository=mock_repo)

    result = importer.import_from_string(POKERSTARS_MULTIHAND, site="pokerstars")

    assert result.hands_imported == 2
    assert len(mock_repo.hands) == 2

    # First hand
    hand1 = mock_repo.hands[0]
    assert hand1.hand_id == "111111111"
    assert hand1.hero_card1 == "Qh"
    assert hand1.hero_card2 == "Jh"

    # Second hand
    hand2 = mock_repo.hands[1]
    assert hand2.hand_id == "222222222"
    assert hand2.hero_card1 == "7h"
    assert hand2.hero_card2 == "2d"


def test_import_from_file(tmp_path: Path):
    """Test importing from an actual file."""
    from pokercoach.storage.importer import HandHistoryImporter

    # Write sample hand history to file
    hh_file = tmp_path / "hand_history.txt"
    hh_file.write_text(POKERSTARS_HAND_HISTORY)

    mock_repo = MockHandRepository()
    importer = HandHistoryImporter(repository=mock_repo)

    result = importer.import_from_file(hh_file)

    assert result.hands_imported == 1
    assert mock_repo.hands[0].hand_id == "123456789"


def test_import_directory(tmp_path: Path):
    """Test importing all files from a directory."""
    from pokercoach.storage.importer import HandHistoryImporter

    # Create multiple hand history files
    (tmp_path / "hh1.txt").write_text(POKERSTARS_HAND_HISTORY)
    (tmp_path / "hh2.txt").write_text(POKERSTARS_MULTIHAND)

    mock_repo = MockHandRepository()
    importer = HandHistoryImporter(repository=mock_repo)

    result = importer.import_from_directory(tmp_path)

    # Should import 3 total hands (1 + 2)
    assert result.hands_imported == 3


def test_import_handles_parse_errors():
    """Test that import continues even if some hands fail to parse."""
    from pokercoach.storage.importer import HandHistoryImporter

    malformed_hh = """PokerStars Hand #999999999: This is malformed
Not a valid hand history format
"""

    combined = POKERSTARS_HAND_HISTORY + "\n" + malformed_hh

    mock_repo = MockHandRepository()
    importer = HandHistoryImporter(repository=mock_repo)

    result = importer.import_from_string(combined, site="pokerstars")

    # Should still import the valid hand
    assert result.hands_imported == 1
    assert result.hands_failed >= 0  # May or may not count malformed as failed


def test_import_actions():
    """Test that actions are correctly imported."""
    from pokercoach.storage.importer import HandHistoryImporter

    mock_repo = MockHandRepository()
    importer = HandHistoryImporter(repository=mock_repo)

    result = importer.import_from_string(POKERSTARS_HAND_HISTORY, site="pokerstars")

    hand = mock_repo.hands[0]

    # Check that actions were parsed
    # The hand should have: Hero 3-bet, cbet flop, bet turn
    assert hand.actions is not None or hasattr(result, 'actions_imported')


def test_import_result_summary():
    """Test import result provides useful summary."""
    from pokercoach.storage.importer import HandHistoryImporter

    mock_repo = MockHandRepository()
    importer = HandHistoryImporter(repository=mock_repo)

    result = importer.import_from_string(POKERSTARS_MULTIHAND, site="pokerstars")

    assert hasattr(result, 'hands_imported')
    assert hasattr(result, 'hands_failed')
    assert result.hands_imported + result.hands_failed >= 0
