"""Leak detection and pattern analysis."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from pokercoach.analysis.evaluator import DecisionQuality, HandEvaluation
from pokercoach.core.game_state import Position, Street


@dataclass
class LeakPattern:
    """An identified leak pattern."""

    name: str
    description: str
    category: str  # positional, bet_sizing, showdown, etc.
    severity: float  # 0-1, higher is worse
    sample_size: int
    avg_ev_loss: float
    examples: list[str]  # Hand IDs demonstrating the leak


@dataclass
class PositionalStats:
    """Statistics broken down by position."""

    position: Position
    hands_played: int
    ev_loss_per_hand: float
    blunder_rate: float
    accuracy: float


@dataclass
class StreetStats:
    """Statistics broken down by street."""

    street: Street
    decisions_made: int
    ev_loss_per_decision: float
    blunder_rate: float
    accuracy: float


class LeakDetector:
    """Detect patterns of suboptimal play across sessions."""

    # Minimum sample size for confident leak detection
    MIN_SAMPLE_SIZE = 20

    def __init__(self):
        self._hand_evaluations: list[HandEvaluation] = []

    def add_evaluations(self, evaluations: list[HandEvaluation]) -> None:
        """Add evaluated hands for analysis."""
        self._hand_evaluations.extend(evaluations)

    def detect_positional_leaks(self) -> list[LeakPattern]:
        """
        Identify positions where play is suboptimal.

        Returns:
            List of leak patterns by position
        """
        # TODO: Implement positional analysis
        # Group hands by position, calculate stats, identify outliers
        raise NotImplementedError("Positional leak detection not yet implemented")

    def detect_street_leaks(self) -> list[LeakPattern]:
        """
        Identify streets where play is suboptimal.

        Returns:
            List of leak patterns by street
        """
        # TODO: Implement street analysis
        raise NotImplementedError("Street leak detection not yet implemented")

    def detect_bet_sizing_leaks(self) -> list[LeakPattern]:
        """
        Identify bet sizing patterns that deviate from GTO.

        Returns:
            List of bet sizing leak patterns
        """
        # TODO: Implement bet sizing analysis
        raise NotImplementedError("Bet sizing leak detection not yet implemented")

    def detect_all_leaks(self) -> list[LeakPattern]:
        """
        Run all leak detection analyses.

        Returns:
            Combined list of all detected leaks, sorted by severity
        """
        leaks: list[LeakPattern] = []

        try:
            leaks.extend(self.detect_positional_leaks())
        except NotImplementedError:
            pass

        try:
            leaks.extend(self.detect_street_leaks())
        except NotImplementedError:
            pass

        try:
            leaks.extend(self.detect_bet_sizing_leaks())
        except NotImplementedError:
            pass

        # Sort by severity
        leaks.sort(key=lambda l: l.severity, reverse=True)
        return leaks

    def get_top_leaks(self, n: int = 3) -> list[LeakPattern]:
        """
        Get the top N most severe leaks.

        Args:
            n: Number of leaks to return

        Returns:
            List of top leaks
        """
        all_leaks = self.detect_all_leaks()
        return all_leaks[:n]


class TrendAnalyzer:
    """Analyze trends over time."""

    def __init__(self):
        self._sessions: list[dict] = []

    def add_session(
        self,
        session_id: str,
        timestamp: str,
        evaluations: list[HandEvaluation],
    ) -> None:
        """Add a session for trend analysis."""
        self._sessions.append({
            "session_id": session_id,
            "timestamp": timestamp,
            "evaluations": evaluations,
        })

    def calculate_accuracy_trend(self) -> list[tuple[str, float]]:
        """
        Calculate accuracy over time.

        Returns:
            List of (timestamp, accuracy) tuples
        """
        results = []
        for session in self._sessions:
            evals = session["evaluations"]
            if not evals:
                continue

            # Calculate session accuracy
            total_decisions = sum(len(e.action_evaluations) for e in evals)
            if total_decisions == 0:
                continue

            excellent_count = sum(
                sum(1 for a in e.action_evaluations if a.quality == DecisionQuality.EXCELLENT)
                for e in evals
            )

            accuracy = (excellent_count / total_decisions) * 100
            results.append((session["timestamp"], accuracy))

        return results

    def calculate_ev_loss_trend(self) -> list[tuple[str, float]]:
        """
        Calculate EV loss per hand over time.

        Returns:
            List of (timestamp, ev_loss_per_hand) tuples
        """
        results = []
        for session in self._sessions:
            evals = session["evaluations"]
            if not evals:
                continue

            total_ev_loss = sum(e.total_ev_loss for e in evals)
            ev_per_hand = total_ev_loss / len(evals)
            results.append((session["timestamp"], ev_per_hand))

        return results
