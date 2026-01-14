"""Integration tests for the LLM poker coach."""

import pytest
from unittest.mock import MagicMock, patch

from pokercoach.core.game_state import (
    ActionType,
    Board,
    Card,
    GameState,
    Hand,
    Player,
    Position,
    Rank,
    Suit,
)
from pokercoach.llm.coach import CoachConfig, PokerCoach
from pokercoach.solver.bridge import Solution, Strategy


class MockSolverBridge:
    """Mock solver for testing."""

    def solve(self, game_state, iterations=1000, target_exploitability=0.5):
        """Return mock solution."""
        return Solution(
            game_state=game_state,
            strategies={
                "AsKs": Strategy(
                    hand=Hand.from_string("AsKs"),
                    actions={
                        ActionType.RAISE: 0.7,
                        ActionType.CALL: 0.2,
                        ActionType.FOLD: 0.1,
                    },
                ),
                "7h2c": Strategy(
                    hand=Hand.from_string("7h2c"),
                    actions={
                        ActionType.FOLD: 0.95,
                        ActionType.CALL: 0.05,
                    },
                ),
            },
            ev={"AsKs": 2.5, "7h2c": -0.8},
            convergence=0.3,
            iterations=500,
        )

    def get_strategy(self, game_state, hand):
        """Return mock strategy for a hand."""
        solution = self.solve(game_state)
        strategy = solution.get_strategy(hand)
        if strategy is None:
            # Return default strategy for unknown hands
            return Strategy(
                hand=hand,
                actions={
                    ActionType.CALL: 0.5,
                    ActionType.FOLD: 0.3,
                    ActionType.RAISE: 0.2,
                },
            )
        return strategy

    def get_ev(self, game_state, hand, action):
        """Return mock EV."""
        return 1.5

    def compare_actions(self, game_state, hand, actions):
        """Return mock action comparison."""
        return {action: 1.0 for action in actions}


def test_query_gto_real():
    """Test that _query_gto returns real solver data, not placeholder."""
    mock_solver = MockSolverBridge()
    config = CoachConfig(api_key="test-key")
    coach = PokerCoach(config=config, solver=mock_solver)

    # Create a game state
    game_state = GameState(
        pot=10.0,
        effective_stack=100.0,
        hero_position=Position.BTN,
    )

    # Query GTO for a premium hand
    result = coach._query_gto(
        hand="AsKs",
        position="BTN",
        board="",
        pot_size=10,
        to_call=2,
        effective_stack=100,
    )

    # Should NOT contain placeholder text
    assert "[Not yet implemented]" not in result
    assert "placeholder" not in result.lower()

    # Should contain actual strategy information
    assert "raise" in result.lower() or "call" in result.lower() or "fold" in result.lower()

    # Should contain frequency information (percentages or decimals)
    import re
    has_frequency = bool(re.search(r'\d+\.?\d*%?', result))
    assert has_frequency, f"Result should contain frequency data: {result}"


def test_query_gto_builds_game_state():
    """Test that _query_gto properly builds GameState from parameters."""
    mock_solver = MockSolverBridge()
    config = CoachConfig(api_key="test-key")
    coach = PokerCoach(config=config, solver=mock_solver)

    # Track if solver was called with correct parameters
    calls = []
    original_get_strategy = mock_solver.get_strategy

    def track_calls(game_state, hand):
        calls.append((game_state, hand))
        return original_get_strategy(game_state, hand)

    mock_solver.get_strategy = track_calls

    # Query with specific parameters
    result = coach._query_gto(
        hand="QhJh",
        position="CO",
        board="Ah Kd 2c",
        pot_size=15,
        to_call=5,
        effective_stack=80,
    )

    # Verify solver was called
    assert len(calls) > 0, "Solver should have been called"

    # Verify game state was constructed correctly
    game_state, hand = calls[0]
    assert hand == Hand.from_string("QhJh")


def test_coach_initialization():
    """Test PokerCoach initializes correctly with solver."""
    mock_solver = MockSolverBridge()
    config = CoachConfig(model="test-model", api_key="test-key")
    coach = PokerCoach(config=config, solver=mock_solver)

    assert coach.config.model == "test-model"
    assert coach.solver == mock_solver


def test_coach_handles_invalid_hand_gracefully():
    """Test that coach handles invalid hands without crashing."""
    mock_solver = MockSolverBridge()
    config = CoachConfig(api_key="test-key")
    coach = PokerCoach(config=config, solver=mock_solver)

    # Should not raise exception for edge cases
    result = coach._query_gto(
        hand="AsKs",
        position="BTN",
        pot_size=0,  # Edge case: empty pot
        to_call=0,
        effective_stack=100,
    )

    assert result is not None
    assert isinstance(result, str)
