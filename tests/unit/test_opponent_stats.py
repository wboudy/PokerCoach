"""Tests for opponent statistics."""

import pytest

from pokercoach.opponent.stats import PlayerStats, StatCounter, StatsAccumulator
from pokercoach.opponent.profiler import OpponentProfiler, PlayerType


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
        assert profile.confidence == "medium"
