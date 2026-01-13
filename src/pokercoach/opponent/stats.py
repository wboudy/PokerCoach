"""HUD-style player statistics."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerStats:
    """
    Standard HUD statistics for a player.

    All percentages are 0-100.
    """

    # Sample size
    hands_played: int = 0

    # Preflop stats
    vpip: float = 0.0  # Voluntarily put in pot %
    pfr: float = 0.0  # Preflop raise %
    three_bet: float = 0.0  # 3-bet %
    fold_to_3bet: float = 0.0  # Fold to 3-bet %
    four_bet: float = 0.0  # 4-bet %
    fold_to_4bet: float = 0.0  # Fold to 4-bet %
    steal_attempt: float = 0.0  # Steal from CO/BTN %
    fold_to_steal: float = 0.0  # Fold blinds to steal %

    # Postflop stats
    cbet_flop: float = 0.0  # C-bet flop %
    cbet_turn: float = 0.0  # C-bet turn %
    cbet_river: float = 0.0  # C-bet river %
    fold_to_cbet_flop: float = 0.0
    fold_to_cbet_turn: float = 0.0
    fold_to_cbet_river: float = 0.0
    check_raise_flop: float = 0.0
    donk_bet: float = 0.0  # Donk bet %

    # Showdown stats
    wtsd: float = 0.0  # Went to showdown %
    wsd: float = 0.0  # Won at showdown %
    wwsf: float = 0.0  # Won when saw flop %

    # Aggression
    aggression_factor: float = 0.0  # (Bet + Raise) / Call
    aggression_frequency: float = 0.0  # (Bet + Raise) / (Bet + Raise + Call + Fold)

    @property
    def is_nit(self) -> bool:
        """Very tight, passive player."""
        return self.vpip < 15 and self.pfr < 12

    @property
    def is_tag(self) -> bool:
        """Tight aggressive player."""
        return 15 <= self.vpip <= 25 and self.pfr >= 15

    @property
    def is_lag(self) -> bool:
        """Loose aggressive player."""
        return self.vpip > 25 and self.pfr >= 20

    @property
    def is_fish(self) -> bool:
        """Loose passive player."""
        return self.vpip > 30 and self.pfr < 15

    @property
    def confidence(self) -> str:
        """Confidence level based on sample size."""
        if self.hands_played < 20:
            return "very_low"
        elif self.hands_played < 50:
            return "low"
        elif self.hands_played < 200:
            return "medium"
        elif self.hands_played < 500:
            return "high"
        else:
            return "very_high"


@dataclass
class StatCounter:
    """Counter for calculating a single statistic."""

    opportunities: int = 0
    occurrences: int = 0

    @property
    def percentage(self) -> float:
        if self.opportunities == 0:
            return 0.0
        return (self.occurrences / self.opportunities) * 100

    def add_opportunity(self, occurred: bool) -> None:
        self.opportunities += 1
        if occurred:
            self.occurrences += 1


@dataclass
class StatsAccumulator:
    """Accumulator for building PlayerStats from hands."""

    hands: int = 0

    # Preflop counters
    vpip_counter: StatCounter = field(default_factory=StatCounter)
    pfr_counter: StatCounter = field(default_factory=StatCounter)
    three_bet_counter: StatCounter = field(default_factory=StatCounter)
    fold_to_3bet_counter: StatCounter = field(default_factory=StatCounter)

    # Postflop counters
    cbet_flop_counter: StatCounter = field(default_factory=StatCounter)
    fold_to_cbet_flop_counter: StatCounter = field(default_factory=StatCounter)

    # Showdown counters
    wtsd_counter: StatCounter = field(default_factory=StatCounter)
    wsd_counter: StatCounter = field(default_factory=StatCounter)

    # Aggression counters
    bets: int = 0
    raises: int = 0
    calls: int = 0

    def to_stats(self) -> PlayerStats:
        """Convert accumulated data to PlayerStats."""
        total_actions = self.bets + self.raises + self.calls
        af = (self.bets + self.raises) / self.calls if self.calls > 0 else 0

        return PlayerStats(
            hands_played=self.hands,
            vpip=self.vpip_counter.percentage,
            pfr=self.pfr_counter.percentage,
            three_bet=self.three_bet_counter.percentage,
            fold_to_3bet=self.fold_to_3bet_counter.percentage,
            cbet_flop=self.cbet_flop_counter.percentage,
            fold_to_cbet_flop=self.fold_to_cbet_flop_counter.percentage,
            wtsd=self.wtsd_counter.percentage,
            wsd=self.wsd_counter.percentage,
            aggression_factor=af,
        )


class StatsCalculator:
    """Calculate player stats from hand histories."""

    def __init__(self):
        self._accumulators: dict[str, StatsAccumulator] = {}

    def get_accumulator(self, player_id: str) -> StatsAccumulator:
        """Get or create accumulator for a player."""
        if player_id not in self._accumulators:
            self._accumulators[player_id] = StatsAccumulator()
        return self._accumulators[player_id]

    def process_hand(self, hand_data: dict) -> None:
        """
        Process a single hand to update player stats.

        Args:
            hand_data: Parsed hand data with player actions
        """
        # TODO: Implement hand processing
        # Extract each player's actions and update their accumulator
        raise NotImplementedError("Hand processing not yet implemented")

    def get_stats(self, player_id: str) -> Optional[PlayerStats]:
        """
        Get calculated stats for a player.

        Args:
            player_id: Player identifier

        Returns:
            PlayerStats or None if no data
        """
        if player_id not in self._accumulators:
            return None
        return self._accumulators[player_id].to_stats()

    def get_all_stats(self) -> dict[str, PlayerStats]:
        """Get stats for all tracked players."""
        return {
            player_id: acc.to_stats()
            for player_id, acc in self._accumulators.items()
        }
