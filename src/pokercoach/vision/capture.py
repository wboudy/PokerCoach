"""Screen capture abstraction."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

import numpy as np


@dataclass
class CaptureRegion:
    """A region of the screen to capture."""

    x: int
    y: int
    width: int
    height: int


class HandRepository(Protocol):
    """Protocol for hand storage repository."""

    def save_hand(self, hand: Any) -> Any:
        """Save a hand record."""
        ...


@dataclass
class SessionStats:
    """Running statistics for a capture session."""

    session_id: str
    site: str
    game_type: str
    stakes: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    hands_captured: int = 0
    total_profit: float = 0.0


class HandCaptureHook:
    """Hook into vision pipeline to automatically store detected hands.

    Integrates with the vision detection system to capture and persist
    hands as they are detected during live play.

    Usage:
        capture_hook = HandCaptureHook(repository=hand_repo)
        capture_hook.start_session("session-001", "PokerStars", "NLHE", "$1/$2")

        # Hook is called by vision pipeline when hand is detected
        capture_hook.on_hand_detected(table_state)

        # At end of session
        summary = capture_hook.end_session()
    """

    def __init__(self, repository: HandRepository):
        """Initialize capture hook with storage repository.

        Args:
            repository: Repository for persisting hand records
        """
        self._repository = repository
        self._session: SessionStats | None = None
        self._seen_hands: set[str] = set()

    @property
    def is_active(self) -> bool:
        """Check if a session is currently active."""
        return self._session is not None

    @property
    def current_session_id(self) -> str | None:
        """Get the current session ID if active."""
        return self._session.session_id if self._session else None

    def start_session(
        self,
        session_id: str,
        site: str,
        game_type: str,
        stakes: str,
    ) -> SessionStats:
        """Start a new capture session.

        Args:
            session_id: Unique identifier for this session
            site: Poker site name (e.g., "PokerStars")
            game_type: Game type (e.g., "NLHE", "PLO")
            stakes: Stakes string (e.g., "$1/$2")

        Returns:
            SessionStats object for the new session
        """
        self._session = SessionStats(
            session_id=session_id,
            site=site,
            game_type=game_type,
            stakes=stakes,
        )
        self._seen_hands = set()
        return self._session

    def end_session(self) -> dict[str, Any]:
        """End the current session and return summary.

        Returns:
            Dictionary with session summary statistics
        """
        if not self._session:
            return {"error": "No active session"}

        summary = {
            "session_id": self._session.session_id,
            "site": self._session.site,
            "game_type": self._session.game_type,
            "stakes": self._session.stakes,
            "started_at": self._session.started_at.isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
            "hands_captured": self._session.hands_captured,
            "total_profit": self._session.total_profit,
        }

        self._session = None
        self._seen_hands = set()

        return summary

    def on_hand_detected(
        self,
        table_state: Any,
        hand_id: str | None = None,
        hero_won: float | None = None,
    ) -> None:
        """Callback for when vision module detects a new hand.

        Args:
            table_state: Detected table state from vision module
            hand_id: Optional explicit hand ID (for deduplication)
            hero_won: Optional profit/loss amount for this hand
        """
        if not self._session:
            return

        # Import here to avoid circular dependency
        from pokercoach.storage.models import HandRecord, Position

        # Generate or use provided hand ID
        if hand_id is None:
            hand_id = f"{self._session.session_id}_{uuid4().hex[:8]}"

        # Check for duplicate
        if hand_id in self._seen_hands:
            return
        self._seen_hands.add(hand_id)

        # Extract data from table state
        hero_card1 = table_state.hero_cards[0] if hasattr(table_state, 'hero_cards') else None
        hero_card2 = table_state.hero_cards[1] if hasattr(table_state, 'hero_cards') and len(table_state.hero_cards) > 1 else None

        # Parse position
        import contextlib
        position = None
        if hasattr(table_state, 'hero_position'):
            with contextlib.suppress(ValueError, KeyError):
                position = Position(table_state.hero_position)

        # Extract board cards
        board_cards = getattr(table_state, 'board_cards', []) or []
        flop1 = board_cards[0] if len(board_cards) > 0 else None
        flop2 = board_cards[1] if len(board_cards) > 1 else None
        flop3 = board_cards[2] if len(board_cards) > 2 else None
        turn = board_cards[3] if len(board_cards) > 3 else None
        river = board_cards[4] if len(board_cards) > 4 else None

        # Create hand record
        hand = HandRecord(
            hand_id=hand_id,
            timestamp=datetime.utcnow(),
            hero_card1=hero_card1,
            hero_card2=hero_card2,
            flop_card1=flop1,
            flop_card2=flop2,
            flop_card3=flop3,
            turn_card=turn,
            river_card=river,
            position=position,
            final_pot=getattr(table_state, 'pot', None),
            hero_won=hero_won,
        )

        # Save to repository
        self._repository.save_hand(hand)

        # Update session stats
        self._session.hands_captured += 1
        if hero_won is not None:
            self._session.total_profit += hero_won

    def get_session_stats(self) -> dict[str, Any]:
        """Get current session statistics.

        Returns:
            Dictionary with current session stats
        """
        if not self._session:
            return {"error": "No active session"}

        return {
            "session_id": self._session.session_id,
            "site": self._session.site,
            "game_type": self._session.game_type,
            "stakes": self._session.stakes,
            "started_at": self._session.started_at.isoformat(),
            "hands_captured": self._session.hands_captured,
            "total_profit": self._session.total_profit,
        }


class ScreenCapture:
    """
    Cross-platform screen capture using mss.

    Provides fast screen capture for poker client monitoring.
    """

    def __init__(self):
        self._sct = None

    def _get_sct(self):
        """Lazy initialization of mss."""
        if self._sct is None:
            import mss

            self._sct = mss.mss()
        return self._sct

    def capture_full_screen(self, monitor: int = 1) -> np.ndarray:
        """
        Capture entire screen.

        Args:
            monitor: Monitor index (1-based)

        Returns:
            numpy array of screenshot (BGRA format)
        """
        sct = self._get_sct()
        screenshot = sct.grab(sct.monitors[monitor])
        return np.array(screenshot)

    def capture_region(self, region: CaptureRegion) -> np.ndarray:
        """
        Capture a specific region of the screen.

        Args:
            region: Region to capture

        Returns:
            numpy array of screenshot
        """
        sct = self._get_sct()
        monitor = {
            "left": region.x,
            "top": region.y,
            "width": region.width,
            "height": region.height,
        }
        screenshot = sct.grab(monitor)
        return np.array(screenshot)

    def capture_window(self, window_title: str) -> np.ndarray | None:
        """
        Capture a specific window by title.

        Args:
            window_title: Window title to search for

        Returns:
            numpy array of screenshot or None if window not found
        """
        # TODO: Implement window detection by title
        # Platform-specific: use pywin32 on Windows, Quartz on macOS
        raise NotImplementedError("Window capture not yet implemented")

    def list_windows(self) -> list[str]:
        """List all visible window titles."""
        # TODO: Implement window enumeration
        raise NotImplementedError("Window listing not yet implemented")

    def monitor_changes(
        self,
        region: CaptureRegion,
        callback: Callable[[np.ndarray], None],
        threshold: float = 0.01,
        interval_ms: int = 100,
    ) -> None:
        """
        Monitor a region for changes and call callback when detected.

        Args:
            region: Region to monitor
            callback: Function to call with new screenshot
            threshold: Minimum change ratio to trigger callback
            interval_ms: Polling interval in milliseconds
        """
        import time

        import cv2

        prev_frame = None

        while True:
            frame = self.capture_region(region)

            if prev_frame is not None:
                # Calculate frame difference
                gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGRA2GRAY)
                diff = cv2.absdiff(gray_curr, gray_prev)
                change_ratio = np.count_nonzero(diff > 30) / diff.size

                if change_ratio > threshold:
                    callback(frame)

            prev_frame = frame
            time.sleep(interval_ms / 1000)
