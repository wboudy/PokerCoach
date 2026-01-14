"""Integration tests for vision-based hand capture."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

import numpy as np

from pokercoach.storage.models import HandRecord, SessionRecord, Position, Street


class MockTableState:
    """Mock detected table state."""

    def __init__(
        self,
        hero_cards: tuple[str, str] = ("As", "Ks"),
        board_cards: list[str] | None = None,
        pot: float = 100.0,
        hero_stack: float = 500.0,
        hero_position: str = "BTN",
    ):
        self.hero_cards = hero_cards
        self.board_cards = board_cards or []
        self.pot = pot
        self.hero_stack = hero_stack
        self.hero_position = hero_position


class MockVisionCapture:
    """Mock vision capture that simulates detecting hands."""

    def __init__(self):
        self.callbacks: list = []
        self.current_table_state: MockTableState | None = None

    def register_hand_callback(self, callback):
        """Register callback for new hands."""
        self.callbacks.append(callback)

    def simulate_hand_detected(self, table_state: MockTableState):
        """Simulate detecting a new hand."""
        self.current_table_state = table_state
        for callback in self.callbacks:
            callback(table_state)


def test_hand_auto_save():
    """Test that detected hands are automatically saved to storage.

    This tests the integration between the vision module's hand detection
    and the storage system. When the vision module detects a new hand,
    it should automatically be persisted.
    """
    from pokercoach.vision.capture import HandCaptureHook

    # Track saved hands
    saved_hands: list[HandRecord] = []

    # Mock repository
    class MockHandRepository:
        def save_hand(self, hand: HandRecord) -> HandRecord:
            hand.id = len(saved_hands) + 1
            saved_hands.append(hand)
            return hand

    mock_repo = MockHandRepository()

    # Create the capture hook
    capture_hook = HandCaptureHook(repository=mock_repo)

    # Start a session
    session = capture_hook.start_session(
        session_id="test-session-001",
        site="TestPoker",
        game_type="NLHE",
        stakes="$1/$2",
    )

    # Simulate detecting hands
    hand1_state = MockTableState(
        hero_cards=("As", "Ks"),
        board_cards=["Ah", "7d", "2c"],
        pot=50.0,
        hero_stack=485.0,
        hero_position="BTN",
    )

    hand2_state = MockTableState(
        hero_cards=("Qh", "Jh"),
        board_cards=["Kh", "Th", "3c", "9h"],  # Flush completed on turn
        pot=200.0,
        hero_stack=350.0,
        hero_position="CO",
    )

    # Process the detected hands
    capture_hook.on_hand_detected(hand1_state)
    capture_hook.on_hand_detected(hand2_state)

    # Verify hands were saved
    assert len(saved_hands) == 2

    # Verify first hand
    hand1 = saved_hands[0]
    assert hand1.hero_card1 == "As"
    assert hand1.hero_card2 == "Ks"
    assert hand1.position == Position.BTN
    assert hand1.flop_card1 == "Ah"
    assert hand1.flop_card2 == "7d"
    assert hand1.flop_card3 == "2c"

    # Verify second hand
    hand2 = saved_hands[1]
    assert hand2.hero_card1 == "Qh"
    assert hand2.hero_card2 == "Jh"
    assert hand2.position == Position.CO
    assert hand2.turn_card == "9h"

    # Verify session tracking
    stats = capture_hook.get_session_stats()
    assert stats["hands_captured"] == 2
    assert stats["session_id"] == "test-session-001"


def test_session_start_end():
    """Test session lifecycle management."""
    from pokercoach.vision.capture import HandCaptureHook

    saved_hands = []

    class MockHandRepository:
        def save_hand(self, hand: HandRecord) -> HandRecord:
            saved_hands.append(hand)
            return hand

    capture_hook = HandCaptureHook(repository=MockHandRepository())

    # Start session
    session = capture_hook.start_session(
        session_id="session-002",
        site="TestPoker",
        game_type="NLHE",
        stakes="$0.50/$1",
    )

    assert capture_hook.is_active
    assert capture_hook.current_session_id == "session-002"

    # Capture some hands
    for i in range(3):
        capture_hook.on_hand_detected(MockTableState(
            hero_cards=(f"{i+10}h", "Ac"),
            pot=float(i * 10 + 10),
        ))

    # End session
    summary = capture_hook.end_session()

    assert not capture_hook.is_active
    assert summary["hands_captured"] == 3
    assert summary["session_id"] == "session-002"


def test_running_stats_tracking():
    """Test that running stats are updated as hands are captured."""
    from pokercoach.vision.capture import HandCaptureHook

    class MockHandRepository:
        def save_hand(self, hand: HandRecord) -> HandRecord:
            return hand

    capture_hook = HandCaptureHook(repository=MockHandRepository())
    capture_hook.start_session("stats-session", "TestPoker", "NLHE", "$1/$2")

    # Capture hands with different outcomes
    # Win
    win_state = MockTableState(hero_cards=("As", "Ah"), pot=100.0)
    capture_hook.on_hand_detected(win_state, hero_won=50.0)

    # Loss
    loss_state = MockTableState(hero_cards=("7h", "2d"), pot=80.0)
    capture_hook.on_hand_detected(loss_state, hero_won=-30.0)

    # Check running stats
    stats = capture_hook.get_session_stats()
    assert stats["hands_captured"] == 2
    assert stats["total_profit"] == 20.0  # 50 - 30


def test_no_duplicate_hands():
    """Test that duplicate hands are not saved twice."""
    from pokercoach.vision.capture import HandCaptureHook

    saved_hands = []

    class MockHandRepository:
        def save_hand(self, hand: HandRecord) -> HandRecord:
            # Simulate checking for duplicates
            for existing in saved_hands:
                if existing.hand_id == hand.hand_id:
                    return existing
            saved_hands.append(hand)
            return hand

    capture_hook = HandCaptureHook(repository=MockHandRepository())
    capture_hook.start_session("dedup-session", "TestPoker", "NLHE", "$1/$2")

    # Same hand detected twice (e.g., screen flicker)
    state = MockTableState(hero_cards=("Kh", "Kd"), pot=100.0)
    capture_hook.on_hand_detected(state, hand_id="hand-12345")
    capture_hook.on_hand_detected(state, hand_id="hand-12345")

    # Should only save once
    assert len(saved_hands) == 1
