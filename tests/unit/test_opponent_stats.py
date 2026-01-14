"""Tests for opponent statistics."""

import pytest

from pokercoach.opponent.stats import (
    ActionType,
    BetSizingPattern,
    HandAction,
    HandRecord,
    PlayerStats,
    Position,
    PositionalStats,
    StatCounter,
    StatsAccumulator,
    Street,
)
from pokercoach.opponent.profiler import OpponentProfiler, PlayerType


def test_player_stats_model():
    """Test comprehensive PlayerStats model with all required fields."""
    # Test basic stats exist and have correct defaults
    stats = PlayerStats()

    # Core stats (VPIP, PFR, 3bet%, AF, WTSD, W$SD)
    assert stats.vpip == 0.0
    assert stats.pfr == 0.0
    assert stats.three_bet == 0.0
    assert stats.aggression_factor == 0.0
    assert stats.wtsd == 0.0
    assert stats.wsd == 0.0  # Won $ at Showdown

    # Positional stats
    assert stats.positional_stats == {}

    # Create positional stats for BTN
    btn_stats = PositionalStats(
        hands=50,
        vpip=35.0,
        pfr=28.0,
        three_bet=12.0,
        fold_to_3bet=55.0,
        cbet_flop=75.0,
        wtsd=28.0,
    )
    stats.set_positional_stats(Position.BTN, btn_stats)
    assert stats.get_positional_stats(Position.BTN).vpip == 35.0
    assert stats.get_positional_stats(Position.BTN).hands == 50

    # Test that getting non-existent position creates empty stats
    bb_stats = stats.get_positional_stats(Position.BB)
    assert bb_stats.hands == 0
    assert bb_stats.vpip == 0.0

    # Bet sizing patterns
    assert isinstance(stats.bet_sizing, BetSizingPattern)
    stats.bet_sizing.small_bets = 10
    stats.bet_sizing.medium_bets = 20
    stats.bet_sizing.large_bets = 15
    stats.bet_sizing.overbet = 5
    stats.bet_sizing.total_bets = 50
    assert stats.bet_sizing.small_bet_pct == 20.0  # 10/50 * 100
    assert stats.bet_sizing.overbet_pct == 10.0  # 5/50 * 100

    # Test per-hand raw data storage
    hand1 = HandRecord(
        hand_id="hand_001",
        timestamp="2024-01-15T10:30:00Z",
        position=Position.BTN,
        hole_cards="AhKs",
        went_to_showdown=True,
        won_at_showdown=True,
        profit_bb=15.5,
    )

    # Add an action to the hand
    action = HandAction(
        street=Street.FLOP,
        action_type=ActionType.BET,
        amount=10.0,
        pot_size=20.0,
        position=Position.BTN,
    )
    hand1.add_action(action)
    assert len(hand1.actions) == 1
    assert hand1.actions[0].bet_size_pct == 50.0  # 10/20 * 100

    # Add hand to player stats
    stats.add_hand_record(hand1)
    assert len(stats.hand_history) == 1
    assert stats.get_recent_hands(5)[0].hand_id == "hand_001"

    # Test hand history limit
    stats.max_hand_history = 3
    for i in range(5):
        stats.add_hand_record(
            HandRecord(
                hand_id=f"hand_{i:03d}",
                timestamp=f"2024-01-15T10:{i:02d}:00Z",
                position=Position.CO,
            )
        )
    assert len(stats.hand_history) == 3  # Capped at max
    assert stats.hand_history[0].hand_id == "hand_002"  # Oldest kept

    # Test get_hands_at_position
    co_hands = stats.get_hands_at_position(Position.CO)
    assert len(co_hands) == 3

    # Test comprehensive stats initialization
    full_stats = PlayerStats(
        hands_played=500,
        vpip=24.5,
        pfr=18.2,
        three_bet=7.5,
        fold_to_3bet=62.0,
        four_bet=2.1,
        fold_to_4bet=45.0,
        steal_attempt=32.0,
        fold_to_steal=78.0,
        cbet_flop=68.0,
        cbet_turn=55.0,
        cbet_river=48.0,
        fold_to_cbet_flop=42.0,
        fold_to_cbet_turn=38.0,
        fold_to_cbet_river=35.0,
        check_raise_flop=8.5,
        donk_bet=4.2,
        wtsd=26.0,
        wsd=52.0,
        wwsf=45.0,
        aggression_factor=2.8,
        aggression_frequency=42.0,
    )

    # Verify all stats are set correctly
    assert full_stats.hands_played == 500
    assert full_stats.vpip == 24.5
    assert full_stats.pfr == 18.2
    assert full_stats.three_bet == 7.5
    assert full_stats.aggression_factor == 2.8
    assert full_stats.wtsd == 26.0
    assert full_stats.wsd == 52.0
    assert full_stats.confidence == "very_high"
    assert full_stats.is_tag  # TAG profile based on stats


class TestPlayerStats:
    """Tests for PlayerStats class."""

    def test_default_stats(self):
        stats = PlayerStats()
        assert stats.hands_played == 0
        assert stats.vpip == 0.0
        assert stats.confidence == "very_low"

    def test_nit_detection(self):
        stats = PlayerStats(hands_played=100, vpip=12, pfr=10)
        assert stats.is_nit
        assert not stats.is_tag
        assert not stats.is_lag
        assert not stats.is_fish

    def test_tag_detection(self):
        stats = PlayerStats(hands_played=100, vpip=22, pfr=18)
        assert stats.is_tag
        assert not stats.is_nit

    def test_lag_detection(self):
        stats = PlayerStats(hands_played=100, vpip=30, pfr=25)
        assert stats.is_lag
        assert not stats.is_tag

    def test_fish_detection(self):
        stats = PlayerStats(hands_played=100, vpip=40, pfr=8)
        assert stats.is_fish
        assert not stats.is_lag

    def test_confidence_levels(self):
        assert PlayerStats(hands_played=10).confidence == "very_low"
        assert PlayerStats(hands_played=30).confidence == "low"
        assert PlayerStats(hands_played=100).confidence == "medium"
        assert PlayerStats(hands_played=300).confidence == "high"
        assert PlayerStats(hands_played=600).confidence == "very_high"


class TestStatCounter:
    """Tests for StatCounter class."""

    def test_empty_counter(self):
        counter = StatCounter()
        assert counter.percentage == 0.0

    def test_counter_calculation(self):
        counter = StatCounter()
        counter.add_opportunity(True)
        counter.add_opportunity(True)
        counter.add_opportunity(False)
        counter.add_opportunity(False)

        assert counter.opportunities == 4
        assert counter.occurrences == 2
        assert counter.percentage == 50.0


class TestStatsAccumulator:
    """Tests for StatsAccumulator class."""

    def test_accumulator_to_stats(self):
        acc = StatsAccumulator()
        acc.hands = 100

        acc.vpip_counter.opportunities = 100
        acc.vpip_counter.occurrences = 25

        acc.pfr_counter.opportunities = 100
        acc.pfr_counter.occurrences = 20

        stats = acc.to_stats()
        assert stats.hands_played == 100
        assert stats.vpip == 25.0
        assert stats.pfr == 20.0


class TestOpponentProfiler:
    """Tests for OpponentProfiler class."""

    def test_classify_unknown(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(hands_played=10, vpip=25, pfr=15)
        assert profiler.classify_player_type(stats) == PlayerType.UNKNOWN

    def test_classify_nit(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(hands_played=100, vpip=14, pfr=10)
        assert profiler.classify_player_type(stats) == PlayerType.NIT

    def test_classify_rock(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(hands_played=100, vpip=8, pfr=6)
        assert profiler.classify_player_type(stats) == PlayerType.ROCK

    def test_classify_tag(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(hands_played=100, vpip=16, pfr=20)
        assert profiler.classify_player_type(stats) == PlayerType.TAG

    def test_classify_lag(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(hands_played=100, vpip=32, pfr=25)
        assert profiler.classify_player_type(stats) == PlayerType.LAG

    def test_classify_fish(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(hands_played=100, vpip=35, pfr=8)
        assert profiler.classify_player_type(stats) == PlayerType.FISH

    def test_classify_maniac(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(hands_played=100, vpip=45, pfr=30, aggression_factor=4.0)
        assert profiler.classify_player_type(stats) == PlayerType.MANIAC

    def test_identify_exploits(self):
        profiler = OpponentProfiler()

        # Player who folds too much to 3-bet
        stats = PlayerStats(
            hands_played=100,
            vpip=25,
            pfr=18,
            fold_to_3bet=75,
            fold_to_cbet_flop=50,
        )

        exploits = profiler.identify_exploits(stats)
        assert exploits["folds_too_much_to_3bet"] is True
        assert exploits["over_folds_to_cbet"] is False

    def test_build_profile(self):
        profiler = OpponentProfiler()
        stats = PlayerStats(
            hands_played=200,
            vpip=22,
            pfr=18,
            three_bet=8,
            fold_to_3bet=65,
            cbet_flop=70,
            aggression_factor=2.5,
        )

        profile = profiler.build_profile("player123", stats)

        assert profile.player_id == "player123"
        assert profile.player_type == PlayerType.TAG
        assert profile.confidence == "high"  # 200 hands = high confidence
