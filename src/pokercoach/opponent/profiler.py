"""Opponent profiling and classification."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from pokercoach.opponent.stats import PlayerStats


class PlayerType(Enum):
    """Classification of player types."""

    NIT = auto()  # Very tight, very passive
    TAG = auto()  # Tight aggressive
    LAG = auto()  # Loose aggressive
    FISH = auto()  # Loose passive (calling station)
    MANIAC = auto()  # Very loose, very aggressive
    ROCK = auto()  # Extremely tight
    UNKNOWN = auto()  # Insufficient data


@dataclass
class PlayerProfile:
    """Complete profile of an opponent."""

    player_id: str
    stats: PlayerStats
    player_type: PlayerType
    confidence: str  # very_low, low, medium, high, very_high

    # Tendencies (0-100, 50 is neutral)
    aggression_tendency: float = 50.0
    bluff_frequency: float = 50.0
    value_betting: float = 50.0
    positional_awareness: float = 50.0

    # Exploitable patterns
    folds_too_much_to_3bet: bool = False
    calls_too_wide_preflop: bool = False
    over_folds_to_cbet: bool = False
    under_bluffs_river: bool = False

    notes: str = ""


class OpponentProfiler:
    """
    Build and maintain opponent profiles.

    Combines statistical analysis with pattern recognition
    to classify opponents and identify exploitable tendencies.
    """

    # Thresholds for player type classification
    VPIP_TIGHT = 18
    VPIP_LOOSE = 28
    PFR_PASSIVE = 12
    PFR_AGGRESSIVE = 18

    def __init__(self):
        self._profiles: dict[str, PlayerProfile] = {}

    def classify_player_type(self, stats: PlayerStats) -> PlayerType:
        """
        Classify player type from statistics.

        Args:
            stats: Player statistics

        Returns:
            PlayerType classification
        """
        if stats.hands_played < 20:
            return PlayerType.UNKNOWN

        vpip = stats.vpip
        pfr = stats.pfr
        af = stats.aggression_factor

        # Rock: Extremely tight
        if vpip < 12:
            return PlayerType.ROCK

        # Nit: Very tight, passive
        if vpip < self.VPIP_TIGHT and pfr < self.PFR_PASSIVE:
            return PlayerType.NIT

        # TAG: Tight, aggressive
        if vpip < self.VPIP_TIGHT and pfr >= self.PFR_AGGRESSIVE:
            return PlayerType.TAG

        # Maniac: Very loose, very aggressive
        if vpip > 35 and af > 3:
            return PlayerType.MANIAC

        # LAG: Loose, aggressive
        if vpip >= self.VPIP_LOOSE and pfr >= self.PFR_AGGRESSIVE:
            return PlayerType.LAG

        # Fish: Loose, passive
        if vpip >= self.VPIP_LOOSE and pfr < self.PFR_PASSIVE:
            return PlayerType.FISH

        # Default to TAG for borderline cases
        return PlayerType.TAG

    def identify_exploits(self, stats: PlayerStats) -> dict[str, bool]:
        """
        Identify exploitable tendencies.

        Args:
            stats: Player statistics

        Returns:
            Dict of exploitable patterns
        """
        exploits = {
            "folds_too_much_to_3bet": stats.fold_to_3bet > 70,
            "calls_too_wide_preflop": stats.vpip - stats.pfr > 15,
            "over_folds_to_cbet": stats.fold_to_cbet_flop > 65,
            "under_bluffs_river": stats.wsd > 55,  # Shows down too often = not bluffing
            "never_folds_to_cbet": stats.fold_to_cbet_flop < 30,
            "steals_too_much": stats.steal_attempt > 40 if stats.steal_attempt else False,
        }
        return exploits

    def build_profile(self, player_id: str, stats: PlayerStats) -> PlayerProfile:
        """
        Build complete player profile.

        Args:
            player_id: Unique player identifier
            stats: Calculated player statistics

        Returns:
            PlayerProfile with classification and exploits
        """
        player_type = self.classify_player_type(stats)
        exploits = self.identify_exploits(stats)

        profile = PlayerProfile(
            player_id=player_id,
            stats=stats,
            player_type=player_type,
            confidence=stats.confidence,
            aggression_tendency=min(100, stats.aggression_factor * 20),
            folds_too_much_to_3bet=exploits.get("folds_too_much_to_3bet", False),
            calls_too_wide_preflop=exploits.get("calls_too_wide_preflop", False),
            over_folds_to_cbet=exploits.get("over_folds_to_cbet", False),
            under_bluffs_river=exploits.get("under_bluffs_river", False),
        )

        self._profiles[player_id] = profile
        return profile

    def get_profile(self, player_id: str) -> Optional[PlayerProfile]:
        """Get stored profile for a player."""
        return self._profiles.get(player_id)

    def update_profile(self, player_id: str, stats: PlayerStats) -> PlayerProfile:
        """Update profile with new statistics."""
        return self.build_profile(player_id, stats)
