"""Live opponent tracking from vision module.

This module integrates the vision pipeline with opponent statistics tracking,
updating player stats in real-time as hands are detected during live play.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

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


@dataclass
class TableState:
    """Detected table state from vision module."""

    hero_cards: list[str] = field(default_factory=list)
    hero_position: str = "btn"
    board_cards: list[str] = field(default_factory=list)
    pot: float = 0.0
    players: dict[str, dict[str, Any]] = field(default_factory=dict)
    current_bet: float = 0.0
    action_on: str = ""


class LiveOpponentTracker:
    """
    Real-time opponent stats tracker integrated with vision module.

    Hooks into the vision pipeline to update opponent statistics
    as hands are detected during live play.

    Usage:
        tracker = LiveOpponentTracker()
        tracker.start_session()

        # Vision module calls these as actions happen:
        tracker.on_hand_start("hand_001", {"player1": {"position": "btn"}})
        tracker.on_action("player1", "raise", amount=3.0, pot_size=1.5)
        tracker.on_hand_complete(winners={"player1": 5.0})

        stats = tracker.get_player_stats("player1")
        all_stats = tracker.end_session()
    """

    def __init__(self, stats_calculator: StatsCalculator | None = None):
        """Initialize tracker.

        Args:
            stats_calculator: Optional StatsCalculator instance for tracking.
                            If not provided, a new one will be created.
        """
        self._stats_calculator = stats_calculator or StatsCalculator()
        self._current_hand: dict[str, HandRecord] = {}  # player_id -> current hand
        self._session_active = False

    @property
    def is_active(self) -> bool:
        """Check if tracking is active."""
        return self._session_active

    def start_session(self) -> None:
        """Start a new tracking session."""
        self._session_active = True
        self._current_hand = {}

    def end_session(self) -> dict[str, PlayerStats]:
        """End session and return all player stats."""
        self._session_active = False
        return self._stats_calculator.get_all_stats()

    def on_hand_start(
        self,
        hand_id: str,
        players: dict[str, dict[str, Any]],
    ) -> None:
        """Called when a new hand starts.

        Args:
            hand_id: Unique hand identifier
            players: Dict of player_id -> {position, stack, ...}
        """
        if not self._session_active:
            return

        timestamp = datetime.now(UTC).isoformat()

        for player_id, player_info in players.items():
            position_str = player_info.get("position", "btn").lower()
            try:
                position = Position(position_str)
            except ValueError:
                position = Position.BTN

            self._current_hand[player_id] = HandRecord(
                hand_id=hand_id,
                timestamp=timestamp,
                position=position,
            )

    def on_action(
        self,
        player_id: str,
        action_type: str,
        amount: float = 0.0,
        pot_size: float = 0.0,
        street: str = "preflop",
    ) -> None:
        """Called when a player takes an action.

        Args:
            player_id: Player identifier
            action_type: Type of action (fold, check, call, bet, raise, all_in)
            amount: Bet/raise amount
            pot_size: Current pot size
            street: Current street
        """
        if not self._session_active:
            return

        if player_id not in self._current_hand:
            return

        # Parse action type
        try:
            action = ActionType(action_type.lower())
        except ValueError:
            return

        # Parse street
        try:
            street_enum = Street(street.lower())
        except ValueError:
            street_enum = Street.PREFLOP

        hand_action = HandAction(
            street=street_enum,
            action_type=action,
            amount=amount,
            pot_size=pot_size,
        )

        self._current_hand[player_id].add_action(hand_action)

    def on_showdown(
        self,
        player_id: str,
        hole_cards: str | None = None,
        won: bool = False,
    ) -> None:
        """Called when player goes to showdown.

        Args:
            player_id: Player identifier
            hole_cards: Player's hole cards if shown
            won: Whether player won at showdown
        """
        if not self._session_active:
            return

        if player_id not in self._current_hand:
            return

        hand = self._current_hand[player_id]
        hand.went_to_showdown = True
        hand.won_at_showdown = won
        if hole_cards:
            hand.hole_cards = hole_cards

    def on_hand_complete(
        self,
        winners: dict[str, float] | None = None,
    ) -> None:
        """Called when hand completes.

        Args:
            winners: Dict of player_id -> amount won
        """
        if not self._session_active:
            return

        winners = winners or {}

        # Process all player hands
        for player_id, hand in self._current_hand.items():
            # Mark wins without showdown
            if player_id in winners and not hand.went_to_showdown:
                hand.won_without_showdown = True

            if player_id in winners:
                hand.profit_bb = winners[player_id]

            # Update stats
            self._stats_calculator.process_hand(player_id, hand)

        # Clear current hand tracking
        self._current_hand = {}

    def get_player_stats(self, player_id: str) -> PlayerStats | None:
        """Get current stats for a player."""
        return self._stats_calculator.get_stats(player_id)

    def get_all_stats(self) -> dict[str, PlayerStats]:
        """Get stats for all tracked players."""
        return self._stats_calculator.get_all_stats()


class VisionIntegrationHook:
    """Hook to integrate vision capture with live tracking.

    Processes table state changes from the vision module and translates
    them into tracking events for the LiveOpponentTracker.
    """

    def __init__(
        self,
        tracker: LiveOpponentTracker,
        capture_hook: HandCaptureHook | None = None,
    ):
        """Initialize the vision integration hook.

        Args:
            tracker: LiveOpponentTracker instance
            capture_hook: Optional HandCaptureHook for storage integration
        """
        self._tracker = tracker
        self._capture_hook = capture_hook
        self._last_table_state: TableState | None = None
        self._current_hand_id: str | None = None

    def on_table_state_changed(self, table_state: TableState) -> None:
        """Called when vision detects table state change.

        Processes the state change and updates tracking accordingly.
        """
        if self._last_table_state is None:
            self._last_table_state = table_state
            return

        # Detect new hand
        if self._is_new_hand(table_state):
            self._handle_new_hand(table_state)

        # Detect actions
        self._detect_actions(table_state)

        # Detect showdown
        if self._is_showdown(table_state):
            self._handle_showdown(table_state)

        # Detect hand complete
        if self._is_hand_complete(table_state):
            self._handle_hand_complete(table_state)

        self._last_table_state = table_state

    def _is_new_hand(self, state: TableState) -> bool:
        """Detect if a new hand has started."""
        # New hand if hero cards changed
        if self._last_table_state is None:
            return True
        return state.hero_cards != self._last_table_state.hero_cards and len(state.hero_cards) == 2

    def _handle_new_hand(self, state: TableState) -> None:
        """Process new hand start."""
        self._current_hand_id = f"hand_{uuid4().hex[:8]}"
        self._tracker.on_hand_start(
            hand_id=self._current_hand_id,
            players=state.players,
        )

    def _detect_actions(self, state: TableState) -> None:
        """Detect and process player actions."""
        # Simplified: compare pot sizes to detect actions
        pass

    def _is_showdown(self, state: TableState) -> bool:
        """Detect showdown state."""
        return len(state.board_cards) == 5 and state.current_bet == 0

    def _handle_showdown(self, state: TableState) -> None:
        """Process showdown."""
        pass

    def _is_hand_complete(self, state: TableState) -> bool:
        """Detect hand completion."""
        # Simplified: pot cleared indicates hand complete
        if self._last_table_state is None:
            return False
        return self._last_table_state.pot > 0 and state.pot == 0

    def _handle_hand_complete(self, state: TableState) -> None:
        """Process hand completion."""
        self._tracker.on_hand_complete()
