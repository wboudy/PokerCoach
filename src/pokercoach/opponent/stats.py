"""HUD-style player statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Position(Enum):
    """Player positions at a poker table."""

    UTG = "utg"
    UTG1 = "utg1"
    UTG2 = "utg2"
    MP = "mp"
    MP1 = "mp1"
    MP2 = "mp2"
    HJ = "hj"  # Hijack
    CO = "co"  # Cutoff
    BTN = "btn"  # Button
    SB = "sb"  # Small blind
    BB = "bb"  # Big blind


class Street(Enum):
    """Betting streets in poker."""

    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(Enum):
    """Types of poker actions."""

    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class BetSizingPattern:
    """Tracks bet sizing patterns for a player."""

    # Bet sizes as percentage of pot (count occurrences in ranges)
    small_bets: int = 0  # < 33% pot
    medium_bets: int = 0  # 33-66% pot
    large_bets: int = 0  # 66-100% pot
    overbet: int = 0  # > 100% pot
    total_bets: int = 0

    # Average bet sizes by street (as % of pot)
    avg_flop_bet_size: float = 0.0
    avg_turn_bet_size: float = 0.0
    avg_river_bet_size: float = 0.0

    # Raise sizes (as multiple of previous bet)
    avg_raise_size: float = 0.0
    min_raise_count: int = 0  # Just min-raises
    standard_raise_count: int = 0  # 2.5-3x
    large_raise_count: int = 0  # > 3x

    @property
    def small_bet_pct(self) -> float:
        """Percentage of bets that are small."""
        return (self.small_bets / self.total_bets * 100) if self.total_bets > 0 else 0.0

    @property
    def overbet_pct(self) -> float:
        """Percentage of bets that are overbets."""
        return (self.overbet / self.total_bets * 100) if self.total_bets > 0 else 0.0


@dataclass
class PositionalStats:
    """Stats for a specific position."""

    hands: int = 0
    vpip: float = 0.0
    pfr: float = 0.0
    three_bet: float = 0.0
    fold_to_3bet: float = 0.0
    cbet_flop: float = 0.0
    wtsd: float = 0.0


@dataclass
class HandAction:
    """A single action taken in a hand."""

    street: Street
    action_type: ActionType
    amount: float = 0.0  # Bet/raise amount
    pot_size: float = 0.0  # Pot size at time of action
    position: Position | None = None

    @property
    def bet_size_pct(self) -> float:
        """Bet size as percentage of pot."""
        if self.pot_size == 0:
            return 0.0
        return (self.amount / self.pot_size) * 100


@dataclass
class HandRecord:
    """Raw data from a single hand for a player."""

    hand_id: str
    timestamp: str  # ISO format
    position: Position
    hole_cards: str | None = None  # e.g., "AhKs" if known
    actions: list[HandAction] = field(default_factory=list)
    went_to_showdown: bool = False
    won_at_showdown: bool = False
    won_without_showdown: bool = False
    profit_bb: float = 0.0  # Profit in big blinds

    def add_action(self, action: HandAction) -> None:
        """Add an action to this hand record."""
        self.actions.append(action)


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

    # Positional stats (keyed by Position enum value)
    positional_stats: dict[str, PositionalStats] = field(default_factory=dict)

    # Bet sizing patterns
    bet_sizing: BetSizingPattern = field(default_factory=BetSizingPattern)

    # Per-hand raw data storage (recent hands, capped for memory)
    hand_history: list[HandRecord] = field(default_factory=list)
    max_hand_history: int = 1000  # Max hands to keep in memory

    def add_hand_record(self, hand: HandRecord) -> None:
        """Add a hand record, maintaining the max history limit."""
        self.hand_history.append(hand)
        if len(self.hand_history) > self.max_hand_history:
            # Remove oldest hands
            self.hand_history = self.hand_history[-self.max_hand_history :]

    def get_positional_stats(self, position: Position) -> PositionalStats:
        """Get stats for a specific position."""
        pos_key = position.value
        if pos_key not in self.positional_stats:
            self.positional_stats[pos_key] = PositionalStats()
        return self.positional_stats[pos_key]

    def set_positional_stats(self, position: Position, stats: PositionalStats) -> None:
        """Set stats for a specific position."""
        self.positional_stats[position.value] = stats

    def get_recent_hands(self, n: int = 10) -> list[HandRecord]:
        """Get the n most recent hands."""
        return self.hand_history[-n:] if self.hand_history else []

    def get_hands_at_position(self, position: Position) -> list[HandRecord]:
        """Get all hands played at a specific position."""
        return [h for h in self.hand_history if h.position == position]

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
    """Calculate player stats from hand histories.

    Processes hands and maintains running aggregates for HUD stats.
    Supports sample size thresholds for stat reliability.
    """

    def __init__(self) -> None:
        self._accumulators: dict[str, StatsAccumulator] = {}

    def get_accumulator(self, player_id: str) -> StatsAccumulator:
        """Get or create accumulator for a player."""
        if player_id not in self._accumulators:
            self._accumulators[player_id] = StatsAccumulator()
        return self._accumulators[player_id]

    def process_hand(self, player_id: str, hand: HandRecord) -> None:
        """
        Process a single hand to update player stats.

        Extracts actions from the hand and updates running aggregates
        for VPIP, PFR, WTSD, WSD, aggression, and other HUD stats.

        Args:
            player_id: Player identifier
            hand: HandRecord with actions to process
        """
        acc = self.get_accumulator(player_id)
        acc.hands += 1

        # Track preflop actions for VPIP/PFR
        has_preflop_action = False
        put_money_preflop = False
        raised_preflop = False
        saw_flop = False
        is_pfr = False  # Was preflop raiser (for cbet tracking)

        for action in hand.actions:
            if action.street == Street.PREFLOP:
                has_preflop_action = True
                if action.action_type in (ActionType.CALL, ActionType.RAISE, ActionType.ALL_IN):
                    put_money_preflop = True
                if action.action_type in (ActionType.RAISE, ActionType.ALL_IN):
                    raised_preflop = True
                    is_pfr = True

                # Track aggression
                if action.action_type == ActionType.CALL:
                    acc.calls += 1
                elif action.action_type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
                    if action.action_type == ActionType.BET:
                        acc.bets += 1
                    else:
                        acc.raises += 1

            elif action.street == Street.FLOP:
                saw_flop = True
                # Track cbet (bet on flop when was preflop raiser)
                if is_pfr and action.action_type == ActionType.BET:
                    acc.cbet_flop_counter.add_opportunity(True)
                elif is_pfr and action.action_type in (ActionType.CHECK, ActionType.FOLD):
                    acc.cbet_flop_counter.add_opportunity(False)

                # Track aggression
                if action.action_type == ActionType.CALL:
                    acc.calls += 1
                elif action.action_type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
                    if action.action_type == ActionType.BET:
                        acc.bets += 1
                    else:
                        acc.raises += 1

            elif action.street in (Street.TURN, Street.RIVER):
                # Track aggression
                if action.action_type == ActionType.CALL:
                    acc.calls += 1
                elif action.action_type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
                    if action.action_type == ActionType.BET:
                        acc.bets += 1
                    else:
                        acc.raises += 1

        # Update VPIP counter (voluntarily put in pot)
        if has_preflop_action:
            acc.vpip_counter.add_opportunity(put_money_preflop)

        # Update PFR counter (preflop raise)
        if has_preflop_action:
            acc.pfr_counter.add_opportunity(raised_preflop)

        # Update WTSD counter (went to showdown given saw flop)
        if saw_flop:
            acc.wtsd_counter.add_opportunity(hand.went_to_showdown)

        # Update WSD counter (won at showdown given went to showdown)
        if hand.went_to_showdown:
            acc.wsd_counter.add_opportunity(hand.won_at_showdown)

    def get_stats(self, player_id: str) -> PlayerStats | None:
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
