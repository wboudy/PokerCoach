"""End-to-end solver integration tests.

Tests the full pipeline: GameState -> solver -> Strategy.
Uses mock solver when real binary not available.
"""

from pathlib import Path

import pytest

from pokercoach.core.game_state import (
    ActionType,
    Card,
    GameState,
    Hand,
    Position,
)
from pokercoach.solver.bridge import Solution, SolverBridge, Strategy
from pokercoach.solver.texas_solver import (
    TexasSolverBridge,
    TexasSolverConfig,
)


class MockSolverBridge(SolverBridge):
    """Mock solver for testing without real binary."""

    def __init__(self):
        self._solutions: dict[str, Solution] = {}

    def add_solution(self, key: str, solution: Solution) -> None:
        """Add a mock solution for a cache key."""
        self._solutions[key] = solution

    def solve(
        self,
        game_state: GameState,
        iterations: int = 1000,
        target_exploitability: float = 0.5,
    ) -> Solution:
        """Return mock solution."""
        # Generate a simple mock solution
        strategies = {}
        evs = {}

        # Mock some common hands
        common_hands = [
            ("AsAh", {ActionType.FOLD: 0.0, ActionType.CALL: 0.1, ActionType.RAISE: 0.9}),
            ("KsKh", {ActionType.FOLD: 0.0, ActionType.CALL: 0.2, ActionType.RAISE: 0.8}),
            ("AhKs", {ActionType.FOLD: 0.0, ActionType.CALL: 0.3, ActionType.RAISE: 0.7}),
            ("QsQh", {ActionType.FOLD: 0.05, ActionType.CALL: 0.35, ActionType.RAISE: 0.6}),
            ("JsJh", {ActionType.FOLD: 0.1, ActionType.CALL: 0.4, ActionType.RAISE: 0.5}),
            ("7h2c", {ActionType.FOLD: 0.9, ActionType.CALL: 0.08, ActionType.RAISE: 0.02}),
        ]

        for hand_str, actions in common_hands:
            try:
                hand = Hand.from_string(hand_str)
                strategies[hand_str] = Strategy(hand=hand, actions=actions)
                # Simple EV based on hand strength
                evs[hand_str] = sum(
                    freq * (10 if act == ActionType.RAISE else 3 if act == ActionType.CALL else -2)
                    for act, freq in actions.items()
                )
            except ValueError:
                pass

        return Solution(
            game_state=game_state,
            strategies=strategies,
            ev=evs,
            convergence=0.3,
            iterations=iterations,
        )

    def get_strategy(self, game_state: GameState, hand: Hand) -> Strategy:
        """Get strategy for specific hand."""
        solution = self.solve(game_state)
        strategy = solution.get_strategy(hand)
        if strategy is None:
            # Return default strategy for unknown hands
            return Strategy(
                hand=hand,
                actions={ActionType.FOLD: 0.5, ActionType.CALL: 0.3, ActionType.RAISE: 0.2},
            )
        return strategy

    def get_ev(self, game_state: GameState, hand: Hand, action) -> float:
        """Get EV for action."""
        return 0.0

    def compare_actions(
        self,
        game_state: GameState,
        hand: Hand,
        actions: list,
    ) -> dict:
        """Compare action EVs."""
        return {}


@pytest.fixture
def mock_solver() -> MockSolverBridge:
    """Create mock solver."""
    return MockSolverBridge()


@pytest.fixture
def sample_preflop_state() -> GameState:
    """Create a standard preflop game state."""
    gs = GameState(
        pot=3.0,  # SB + BB
        effective_stack=100.0,
        hero_position=Position.BTN,
    )
    return gs


@pytest.fixture
def sample_flop_state() -> GameState:
    """Create a postflop game state."""
    gs = GameState(
        pot=15.0,
        effective_stack=85.0,
        hero_position=Position.BTN,
    )
    for card_str in ["Qs", "Jh", "2d"]:
        gs.board.add_card(Card.from_string(card_str))
    return gs


class TestE2EPipeline:
    """End-to-end tests for GameState -> solver -> Strategy pipeline."""

    def test_preflop_strategy_retrieval(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test retrieving preflop strategy for a hand."""
        hand = Hand.from_string("AsKs")
        strategy = mock_solver.get_strategy(sample_preflop_state, hand)

        assert isinstance(strategy, Strategy)
        assert strategy.hand == hand
        assert sum(strategy.actions.values()) > 0.99  # Frequencies sum to ~1

    def test_postflop_strategy_retrieval(
        self, mock_solver: MockSolverBridge, sample_flop_state: GameState
    ):
        """Test retrieving postflop strategy."""
        hand = Hand.from_string("AsAh")
        strategy = mock_solver.get_strategy(sample_flop_state, hand)

        assert isinstance(strategy, Strategy)
        assert ActionType.RAISE in strategy.actions or ActionType.BET in strategy.actions

    def test_solution_contains_multiple_hands(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that solution contains strategies for multiple hands."""
        solution = mock_solver.solve(sample_preflop_state)

        assert len(solution.strategies) > 0
        assert "AsAh" in solution.strategies
        assert "KsKh" in solution.strategies

    def test_solution_evs_present(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that solution contains EVs for hands."""
        solution = mock_solver.solve(sample_preflop_state)

        assert len(solution.ev) > 0
        assert solution.ev.get("AsAh", 0) > solution.ev.get("7h2c", 0)

    def test_primary_action_for_strong_hand(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that strong hands have raise as primary action."""
        hand = Hand.from_string("AsAh")
        strategy = mock_solver.get_strategy(sample_preflop_state, hand)

        assert strategy.primary_action == ActionType.RAISE

    def test_primary_action_for_weak_hand(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that weak hands have fold as primary action."""
        hand = Hand.from_string("7h2c")
        strategy = mock_solver.get_strategy(sample_preflop_state, hand)

        assert strategy.primary_action == ActionType.FOLD

    def test_strategy_frequencies_valid(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that strategy frequencies are valid (0-1, sum to 1)."""
        hand = Hand.from_string("AsAh")
        strategy = mock_solver.get_strategy(sample_preflop_state, hand)

        for action, freq in strategy.actions.items():
            assert 0 <= freq <= 1, f"Frequency for {action} out of range: {freq}"

        total = sum(strategy.actions.values())
        assert 0.99 <= total <= 1.01, f"Frequencies don't sum to 1: {total}"

    def test_game_state_preserved_in_solution(
        self, mock_solver: MockSolverBridge, sample_flop_state: GameState
    ):
        """Test that solution preserves original game state."""
        solution = mock_solver.solve(sample_flop_state)

        assert solution.game_state.pot == sample_flop_state.pot
        assert solution.game_state.effective_stack == sample_flop_state.effective_stack
        assert len(solution.game_state.board.cards) == len(sample_flop_state.board.cards)

    def test_convergence_metrics(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that solution contains convergence metrics."""
        solution = mock_solver.solve(sample_preflop_state, iterations=500)

        assert solution.convergence >= 0
        assert solution.iterations > 0


class TestIntegrationWithCoach:
    """Test solver integration with coaching module."""

    def test_solver_used_by_coach_query_gto(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that coach can use solver for GTO queries."""
        from pokercoach.llm.coach import CoachConfig, PokerCoach

        config = CoachConfig()
        coach = PokerCoach(config=config, solver=mock_solver)

        # Test the _query_gto method directly
        result = coach._query_gto(
            hand="AsAh",
            position="BTN",
            pot_size=3.0,
            effective_stack=100.0,
        )

        assert "AsAh" in result
        assert "Raise" in result or "raise" in result.lower()


class TestSolverBridgeInterface:
    """Test that solver bridge interface is properly implemented."""

    def test_mock_solver_implements_interface(self, mock_solver: MockSolverBridge):
        """Test that mock solver implements SolverBridge interface."""
        assert isinstance(mock_solver, SolverBridge)
        assert hasattr(mock_solver, "solve")
        assert hasattr(mock_solver, "get_strategy")
        assert hasattr(mock_solver, "get_ev")
        assert hasattr(mock_solver, "compare_actions")

    def test_solve_returns_solution(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that solve() returns a Solution object."""
        result = mock_solver.solve(sample_preflop_state)
        assert isinstance(result, Solution)

    def test_get_strategy_returns_strategy(
        self, mock_solver: MockSolverBridge, sample_preflop_state: GameState
    ):
        """Test that get_strategy() returns a Strategy object."""
        hand = Hand.from_string("AsAh")
        result = mock_solver.get_strategy(sample_preflop_state, hand)
        assert isinstance(result, Strategy)


class TestRealSolverIntegration:
    """Tests for real solver integration (skipped if binary not available)."""

    @pytest.fixture
    def solver_binary_path(self) -> Path | None:
        """Get real solver binary path if available."""
        # Check common locations
        common_paths = [
            Path.home() / "TexasSolver" / "console_solver",
            Path("/usr/local/bin/texas_solver"),
            Path("/opt/texas_solver/console_solver"),
        ]
        for path in common_paths:
            if path.exists():
                return path
        return None

    @pytest.mark.skipif(
        not any(
            Path(p).exists()
            for p in [
                Path.home() / "TexasSolver" / "console_solver",
                "/usr/local/bin/texas_solver",
            ]
        ),
        reason="Real solver binary not available",
    )
    def test_real_solver_produces_valid_output(self, solver_binary_path: Path):
        """Test with real solver binary if available."""
        if solver_binary_path is None:
            pytest.skip("Solver binary not found")

        config = TexasSolverConfig(
            binary_path=solver_binary_path,
            max_iterations=100,  # Quick solve
            accuracy=1.0,  # Low accuracy for speed
        )
        solver = TexasSolverBridge(config)

        gs = GameState(pot=10.0, effective_stack=100.0)
        for card in ["Qs", "Jh", "2d"]:
            gs.board.add_card(Card.from_string(card))

        solution = solver.solve(gs, iterations=100)

        assert isinstance(solution, Solution)
        assert len(solution.strategies) > 0
