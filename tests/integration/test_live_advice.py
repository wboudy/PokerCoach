"""Tests for live advice integration of solver + opponent data."""

import pytest

from pokercoach.core.game_state import (
    ActionType,
    Card,
    GameState,
    Hand,
    Position,
)
from pokercoach.opponent.exploiter import AdjustedStrategy, ExploitationEngine
from pokercoach.opponent.profiler import OpponentProfiler, PlayerProfile, PlayerType
from pokercoach.opponent.stats import PlayerStats
from pokercoach.solver.bridge import Solution, Strategy


class MockSolver:
    """Mock solver for testing."""

    def get_strategy(self, game_state: GameState, hand: Hand) -> Strategy:
        """Return GTO strategy for hand."""
        # Premium hands raise more
        if str(hand) in ["AsAh", "KsKh", "AsKs", "AhKh"]:
            return Strategy(
                hand=hand,
                actions={
                    ActionType.RAISE: 0.9,
                    ActionType.CALL: 0.1,
                    ActionType.FOLD: 0.0,
                },
            )
        # Medium hands mixed
        elif str(hand) in ["QsQh", "JsJh", "AhQh", "AsQs"]:
            return Strategy(
                hand=hand,
                actions={
                    ActionType.RAISE: 0.6,
                    ActionType.CALL: 0.3,
                    ActionType.FOLD: 0.1,
                },
            )
        # Weak hands fold more
        else:
            return Strategy(
                hand=hand,
                actions={
                    ActionType.FOLD: 0.7,
                    ActionType.CALL: 0.2,
                    ActionType.RAISE: 0.1,
                },
            )


class LiveCoachingAdvisor:
    """
    Real-time coaching advisor combining GTO solver + opponent data.

    Produces live recommendations during play by:
    1. Getting GTO strategy from solver
    2. Applying opponent-specific adjustments
    3. Explaining what changes and why
    """

    def __init__(
        self,
        solver,
        profiler: OpponentProfiler,
        engine: ExploitationEngine,
    ):
        self._solver = solver
        self._profiler = profiler
        self._engine = engine

    def get_advice(
        self,
        game_state: GameState,
        hero_hand: Hand,
        opponent_id: str | None = None,
    ) -> dict:
        """
        Get live coaching advice for current decision.

        Args:
            game_state: Current game state
            hero_hand: Hero's hole cards
            opponent_id: Opponent's ID for profiling (if known)

        Returns:
            Dict with GTO strategy, adjustments, and explanation
        """
        # Get base GTO strategy
        gto_strategy = self._solver.get_strategy(game_state, hero_hand)

        result = {
            "gto_strategy": {
                action.value: freq
                for action, freq in gto_strategy.actions.items()
            },
            "primary_action": gto_strategy.primary_action.value,
            "adjustments": [],
            "opponent_info": None,
            "recommendation": gto_strategy.primary_action.value,
            "explanation": "",
        }

        # If we have opponent data, apply adjustments
        if opponent_id:
            profile = self._profiler.get_profile(opponent_id)
            if profile:
                adjusted = self._engine.get_adjustment(
                    game_state, gto_strategy, profile
                )

                result["opponent_info"] = {
                    "player_type": profile.player_type.name,
                    "confidence": profile.confidence,
                    "hands_played": profile.stats.hands_played,
                    "vpip": profile.stats.vpip,
                    "pfr": profile.stats.pfr,
                }

                if adjusted.adjustments:
                    result["adjustments"] = [
                        {
                            "action": adj.action.value,
                            "gto_freq": adj.gto_frequency,
                            "adjusted_freq": adj.adjusted_frequency,
                            "reason": adj.reason,
                            "confidence": adj.confidence,
                        }
                        for adj in adjusted.adjustments
                    ]

                    # Update recommendation based on adjustments
                    final = adjusted.final_strategy
                    if final:
                        best_action = max(final.items(), key=lambda x: x[1])
                        result["recommendation"] = best_action[0].value

                    # Build explanation
                    result["explanation"] = self._build_explanation(
                        gto_strategy, adjusted, profile
                    )
                else:
                    result["explanation"] = (
                        f"Playing GTO vs {profile.player_type.name}. "
                        "No significant exploits identified."
                    )

        return result

    def _build_explanation(
        self,
        gto_strategy: Strategy,
        adjusted: AdjustedStrategy,
        profile: PlayerProfile,
    ) -> str:
        """Build human-readable explanation of adjustments."""
        lines = []

        lines.append(
            f"Opponent is a {profile.player_type.name} "
            f"({profile.stats.hands_played} hands, {profile.confidence} confidence)"
        )

        for adj in adjusted.adjustments:
            delta = adj.adjusted_frequency - adj.gto_frequency
            direction = "more" if delta > 0 else "less"
            lines.append(
                f"  - {adj.action.value.capitalize()} {direction}: {adj.reason}"
            )

        return "\n".join(lines)

    def get_action_comparison(
        self,
        game_state: GameState,
        hero_hand: Hand,
        opponent_id: str | None = None,
    ) -> dict:
        """
        Compare actions with GTO vs exploitative frequencies.

        Returns table of actions showing:
        - GTO frequency
        - Adjusted frequency (if opponent known)
        - Delta
        """
        gto_strategy = self._solver.get_strategy(game_state, hero_hand)

        actions = []
        for action_type in [ActionType.FOLD, ActionType.CALL, ActionType.RAISE]:
            gto_freq = gto_strategy.frequency(action_type)
            adj_freq = gto_freq  # Default to GTO
            delta = 0.0

            if opponent_id:
                profile = self._profiler.get_profile(opponent_id)
                if profile:
                    adjusted = self._engine.get_adjustment(
                        game_state, gto_strategy, profile
                    )
                    final = adjusted.final_strategy
                    adj_freq = final.get(action_type, gto_freq)
                    delta = adj_freq - gto_freq

            actions.append({
                "action": action_type.value,
                "gto_frequency": round(gto_freq * 100, 1),
                "adjusted_frequency": round(adj_freq * 100, 1),
                "delta": round(delta * 100, 1),
            })

        return {"actions": actions}


@pytest.fixture
def solver() -> MockSolver:
    """Create mock solver."""
    return MockSolver()


@pytest.fixture
def profiler() -> OpponentProfiler:
    """Create opponent profiler."""
    return OpponentProfiler()


@pytest.fixture
def engine() -> ExploitationEngine:
    """Create exploitation engine."""
    return ExploitationEngine()


@pytest.fixture
def advisor(solver, profiler, engine) -> LiveCoachingAdvisor:
    """Create live advisor."""
    return LiveCoachingAdvisor(solver, profiler, engine)


@pytest.fixture
def game_state() -> GameState:
    """Create sample game state."""
    return GameState(pot=10.0, effective_stack=100.0, hero_position=Position.BTN)


class TestLiveAdvice:
    """Tests for live coaching advice."""

    def test_get_advice_gto_only(
        self, advisor: LiveCoachingAdvisor, game_state: GameState
    ):
        """Test getting GTO advice without opponent data."""
        hand = Hand.from_string("AsAh")

        advice = advisor.get_advice(game_state, hand)

        assert "gto_strategy" in advice
        assert advice["primary_action"] == "raise"
        assert advice["recommendation"] == "raise"
        assert len(advice["adjustments"]) == 0

    def test_get_advice_with_opponent(
        self,
        advisor: LiveCoachingAdvisor,
        profiler: OpponentProfiler,
        game_state: GameState,
    ):
        """Test getting advice with opponent profile."""
        # Create a fishy opponent
        stats = PlayerStats(
            hands_played=100,
            vpip=45.0,
            pfr=8.0,
            fold_to_cbet_flop=25.0,
        )
        profiler.build_profile("fish_player", stats)

        hand = Hand.from_string("AsAh")
        advice = advisor.get_advice(game_state, hand, opponent_id="fish_player")

        assert advice["opponent_info"] is not None
        assert advice["opponent_info"]["player_type"] == "FISH"

    def test_get_advice_shows_adjustments(
        self,
        advisor: LiveCoachingAdvisor,
        profiler: OpponentProfiler,
        game_state: GameState,
    ):
        """Test that advice shows adjustments when exploits found."""
        # Create a nitty opponent who folds to 3-bets
        stats = PlayerStats(
            hands_played=200,
            vpip=12.0,
            pfr=10.0,
            fold_to_3bet=80.0,
        )
        profiler.build_profile("nit_player", stats)

        hand = Hand.from_string("AsQs")  # Medium strength
        advice = advisor.get_advice(game_state, hand, opponent_id="nit_player")

        # Should have adjustments vs nit
        assert advice["opponent_info"]["player_type"] == "NIT"
        # Explanation should mention the player type
        assert "NIT" in advice["explanation"]


class TestActionComparison:
    """Tests for action comparison table."""

    def test_comparison_without_opponent(
        self, advisor: LiveCoachingAdvisor, game_state: GameState
    ):
        """Test action comparison shows GTO only."""
        hand = Hand.from_string("AsAh")

        comparison = advisor.get_action_comparison(game_state, hand)

        assert "actions" in comparison
        assert len(comparison["actions"]) == 3

        for action in comparison["actions"]:
            assert action["delta"] == 0.0  # No adjustment without opponent

    def test_comparison_with_opponent(
        self,
        advisor: LiveCoachingAdvisor,
        profiler: OpponentProfiler,
        game_state: GameState,
    ):
        """Test action comparison shows adjustments."""
        # Create LAG opponent
        stats = PlayerStats(
            hands_played=200,
            vpip=35.0,
            pfr=25.0,
            aggression_factor=4.0,
        )
        profiler.build_profile("lag_player", stats)

        hand = Hand.from_string("AsAh")
        comparison = advisor.get_action_comparison(
            game_state, hand, opponent_id="lag_player"
        )

        # Check that actions have potential adjustments
        assert "actions" in comparison


class TestIntegrationWithSolver:
    """Integration tests combining solver and opponent data."""

    def test_full_pipeline_preflop_vs_nit(
        self,
        advisor: LiveCoachingAdvisor,
        profiler: OpponentProfiler,
    ):
        """Test full advice pipeline preflop vs nit."""
        # Setup game state
        gs = GameState(
            pot=3.5,  # Raised pot
            effective_stack=97.0,
            hero_position=Position.BB,
        )

        # Create nit profile
        stats = PlayerStats(
            hands_played=150,
            vpip=10.0,
            pfr=8.0,
            fold_to_3bet=75.0,
        )
        profiler.build_profile("nit123", stats)

        # Get advice for AQs (good 3-bet candidate vs nit)
        hand = Hand.from_string("AhQh")
        advice = advisor.get_advice(gs, hand, opponent_id="nit123")

        assert advice["opponent_info"]["player_type"] in ["NIT", "ROCK"]
        assert advice["recommendation"] in ["raise", "call"]

    def test_full_pipeline_postflop_vs_fish(
        self,
        advisor: LiveCoachingAdvisor,
        profiler: OpponentProfiler,
    ):
        """Test full advice pipeline postflop vs fish."""
        # Setup postflop game state
        gs = GameState(
            pot=15.0,
            effective_stack=85.0,
            hero_position=Position.BTN,
        )
        for card in ["Ks", "Td", "4c"]:
            gs.board.add_card(Card.from_string(card))

        # Create fish profile
        stats = PlayerStats(
            hands_played=100,
            vpip=50.0,
            pfr=5.0,
            fold_to_cbet_flop=20.0,
        )
        profiler.build_profile("fish456", stats)

        # Get advice for AK on K-high board
        hand = Hand.from_string("AsKh")
        advice = advisor.get_advice(gs, hand, opponent_id="fish456")

        assert advice["opponent_info"]["player_type"] == "FISH"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_unknown_opponent(
        self, advisor: LiveCoachingAdvisor, game_state: GameState
    ):
        """Test handling of unknown opponent ID."""
        hand = Hand.from_string("AsAh")

        # Pass non-existent opponent
        advice = advisor.get_advice(
            game_state, hand, opponent_id="nonexistent_player"
        )

        # Should fall back to GTO
        assert advice["opponent_info"] is None
        assert len(advice["adjustments"]) == 0

    def test_opponent_low_sample(
        self,
        advisor: LiveCoachingAdvisor,
        profiler: OpponentProfiler,
        game_state: GameState,
    ):
        """Test that low sample opponents get UNKNOWN type."""
        stats = PlayerStats(
            hands_played=5,  # Very low
            vpip=50.0,
            pfr=10.0,
        )
        profiler.build_profile("new_player", stats)

        hand = Hand.from_string("AsAh")
        advice = advisor.get_advice(game_state, hand, opponent_id="new_player")

        # Should classify as UNKNOWN with low sample
        assert advice["opponent_info"]["player_type"] == "UNKNOWN"
