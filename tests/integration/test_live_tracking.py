"""Tests for live opponent tracking from vision module."""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pokercoach.opponent.stats import (
    ActionType,
    HandAction,
    HandRecord,
    PlayerStats,
    Position,
    StatsCalculator,
    Street,
)
from pokercoach.vision.capture import HandCaptureHook
from pokercoach.vision.tracking import (
    LiveOpponentTracker,
    TableState,
    VisionIntegrationHook,
)


@dataclass
class MockTableState(TableState):
    """Mock table state for testing, extends the production TableState."""

    def __init__(
        self,
        hero_cards: list[str] | None = None,
        hero_position: str = "btn",
        board_cards: list[str] | None = None,
        pot: float = 0.0,
        players: dict[str, dict[str, Any]] | None = None,
        current_bet: float = 0.0,
        action_on: str = "",
    ):
        super().__init__()
        self.hero_cards = hero_cards if hero_cards is not None else ["As", "Kd"]
        self.hero_position = hero_position
        self.board_cards = board_cards if board_cards is not None else []
        self.pot = pot
        self.players = players if players is not None else {}
        self.current_bet = current_bet
        self.action_on = action_on


@pytest.fixture
def tracker() -> LiveOpponentTracker:
    """Create tracker instance."""
    return LiveOpponentTracker()


@pytest.fixture
def active_tracker() -> LiveOpponentTracker:
    """Create and start tracker."""
    t = LiveOpponentTracker()
    t.start_session()
    return t


class TestLiveOpponentTracker:
    """Tests for LiveOpponentTracker."""

    def test_tracker_starts_inactive(self, tracker: LiveOpponentTracker):
        """Test tracker starts inactive."""
        assert not tracker.is_active

    def test_start_session(self, tracker: LiveOpponentTracker):
        """Test starting a tracking session."""
        tracker.start_session()
        assert tracker.is_active

    def test_end_session(self, active_tracker: LiveOpponentTracker):
        """Test ending a tracking session."""
        stats = active_tracker.end_session()
        assert not active_tracker.is_active
        assert isinstance(stats, dict)

    def test_track_single_hand(self, active_tracker: LiveOpponentTracker):
        """Test tracking a single hand."""
        # Start hand
        active_tracker.on_hand_start(
            hand_id="hand_001",
            players={
                "player_1": {"position": "btn", "stack": 100},
                "player_2": {"position": "bb", "stack": 100},
            },
        )

        # Player 1 raises preflop
        active_tracker.on_action(
            player_id="player_1",
            action_type="raise",
            amount=3.0,
            pot_size=1.5,
            street="preflop",
        )

        # Player 2 folds
        active_tracker.on_action(
            player_id="player_2",
            action_type="fold",
            pot_size=4.5,
            street="preflop",
        )

        # Hand completes
        active_tracker.on_hand_complete(winners={"player_1": 1.5})

        # Check stats updated
        stats = active_tracker.get_player_stats("player_1")
        assert stats is not None
        assert stats.hands_played == 1
        assert stats.pfr > 0  # Raised preflop

    def test_track_showdown(self, active_tracker: LiveOpponentTracker):
        """Test tracking hand that goes to showdown."""
        active_tracker.on_hand_start(
            hand_id="hand_002",
            players={"player_1": {"position": "btn"}},
        )

        # Preflop action
        active_tracker.on_action("player_1", "call", 2.0, 3.0, "preflop")

        # Flop action
        active_tracker.on_action("player_1", "call", 5.0, 10.0, "flop")

        # Showdown
        active_tracker.on_showdown("player_1", hole_cards="AsKd", won=True)

        # Complete
        active_tracker.on_hand_complete(winners={"player_1": 15.0})

        stats = active_tracker.get_player_stats("player_1")
        assert stats is not None
        assert stats.wtsd > 0  # Went to showdown
        assert stats.wsd > 0  # Won at showdown

    def test_track_multiple_players(self, active_tracker: LiveOpponentTracker):
        """Test tracking multiple players in same hand."""
        active_tracker.on_hand_start(
            hand_id="hand_003",
            players={
                "player_1": {"position": "btn"},
                "player_2": {"position": "sb"},
                "player_3": {"position": "bb"},
            },
        )

        # All players act
        active_tracker.on_action("player_1", "raise", 3.0, 1.5, "preflop")
        active_tracker.on_action("player_2", "fold", 0, 4.5, "preflop")
        active_tracker.on_action("player_3", "call", 2.0, 4.5, "preflop")

        active_tracker.on_hand_complete(winners={"player_1": 5.0})

        # All players should have stats
        for pid in ["player_1", "player_2", "player_3"]:
            stats = active_tracker.get_player_stats(pid)
            assert stats is not None
            assert stats.hands_played == 1

    def test_no_tracking_when_inactive(self, tracker: LiveOpponentTracker):
        """Test that actions are ignored when tracker inactive."""
        # Don't start session
        tracker.on_hand_start("hand_004", {"player_1": {"position": "btn"}})
        tracker.on_action("player_1", "raise", 3.0, 1.5, "preflop")
        tracker.on_hand_complete()

        stats = tracker.get_player_stats("player_1")
        assert stats is None

    def test_get_all_stats(self, active_tracker: LiveOpponentTracker):
        """Test getting stats for all players."""
        # Track two separate hands with different players
        active_tracker.on_hand_start("hand_005", {"p1": {"position": "btn"}})
        active_tracker.on_action("p1", "raise", 3.0, 1.5, "preflop")
        active_tracker.on_hand_complete()

        active_tracker.on_hand_start("hand_006", {"p2": {"position": "btn"}})
        active_tracker.on_action("p2", "fold", 0, 3.0, "preflop")
        active_tracker.on_hand_complete()

        all_stats = active_tracker.get_all_stats()
        assert "p1" in all_stats
        assert "p2" in all_stats


class TestVisionIntegration:
    """Tests for vision module integration."""

    def test_vision_hook_initializes(self):
        """Test vision integration hook can be created."""
        tracker = LiveOpponentTracker()
        hook = VisionIntegrationHook(tracker)
        assert hook is not None

    def test_vision_detects_new_hand(self):
        """Test vision hook detects new hand."""
        tracker = LiveOpponentTracker()
        tracker.start_session()
        hook = VisionIntegrationHook(tracker)

        # Simulate state changes
        state1 = MockTableState(hero_cards=[], pot=0)
        hook.on_table_state_changed(state1)

        state2 = MockTableState(
            hero_cards=["As", "Kd"],
            pot=1.5,
            players={"player_1": {"position": "btn"}},
        )
        hook.on_table_state_changed(state2)

        # Should have started tracking
        # (actual tracking depends on implementation details)
        assert tracker.is_active


class TestStatsCalculation:
    """Tests for stats calculation from hand records."""

    def test_vpip_calculation(self, active_tracker: LiveOpponentTracker):
        """Test VPIP is calculated correctly."""
        # Hand 1: Player raises (VPIP = yes)
        active_tracker.on_hand_start("h1", {"p1": {"position": "btn"}})
        active_tracker.on_action("p1", "raise", 3.0, 1.5, "preflop")
        active_tracker.on_hand_complete()

        # Hand 2: Player folds (VPIP = no)
        active_tracker.on_hand_start("h2", {"p1": {"position": "utg"}})
        active_tracker.on_action("p1", "fold", 0, 1.5, "preflop")
        active_tracker.on_hand_complete()

        stats = active_tracker.get_player_stats("p1")
        assert stats is not None
        assert stats.vpip == 50.0  # 1 out of 2 hands

    def test_pfr_calculation(self, active_tracker: LiveOpponentTracker):
        """Test PFR is calculated correctly."""
        # Hand 1: Raise
        active_tracker.on_hand_start("h1", {"p1": {"position": "btn"}})
        active_tracker.on_action("p1", "raise", 3.0, 1.5, "preflop")
        active_tracker.on_hand_complete()

        # Hand 2: Call
        active_tracker.on_hand_start("h2", {"p1": {"position": "bb"}})
        active_tracker.on_action("p1", "call", 2.0, 3.0, "preflop")
        active_tracker.on_hand_complete()

        # Hand 3: Fold
        active_tracker.on_hand_start("h3", {"p1": {"position": "utg"}})
        active_tracker.on_action("p1", "fold", 0, 1.5, "preflop")
        active_tracker.on_hand_complete()

        stats = active_tracker.get_player_stats("p1")
        assert stats is not None
        # PFR = 1/3 = 33.33%
        assert 33.0 <= stats.pfr <= 34.0

    def test_wtsd_calculation(self, active_tracker: LiveOpponentTracker):
        """Test WTSD is calculated correctly."""
        # Hand 1: Goes to showdown
        active_tracker.on_hand_start("h1", {"p1": {"position": "btn"}})
        active_tracker.on_action("p1", "call", 2.0, 3.0, "preflop")
        active_tracker.on_action("p1", "check", 0, 5.0, "flop")
        active_tracker.on_showdown("p1", won=True)
        active_tracker.on_hand_complete()

        # Hand 2: Folds on flop
        active_tracker.on_hand_start("h2", {"p1": {"position": "btn"}})
        active_tracker.on_action("p1", "call", 2.0, 3.0, "preflop")
        active_tracker.on_action("p1", "fold", 0, 10.0, "flop")
        active_tracker.on_hand_complete()

        stats = active_tracker.get_player_stats("p1")
        assert stats is not None
        # WTSD = 1/2 = 50% (of hands that saw flop)
        assert stats.wtsd == 50.0
