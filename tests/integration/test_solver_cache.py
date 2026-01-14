"""Tests for solver cache and dynamic fallback."""

import json
import time
from pathlib import Path

import pytest

from pokercoach.core.game_state import (
    ActionType,
    GameState,
    Hand,
    Position,
)
from pokercoach.solver.bridge import Solution, Strategy
from pokercoach.solver.texas_solver import PrecomputedSolver


class MockFallbackSolver:
    """Mock fallback solver for testing dynamic fallback."""

    def __init__(self, delay: float = 0.0, should_timeout: bool = False):
        self._delay = delay
        self._should_timeout = should_timeout
        self._call_count = 0

    def solve(
        self,
        game_state: GameState,
        iterations: int = 1000,
        target_exploitability: float = 0.5,
    ) -> Solution:
        """Mock solve with configurable delay."""
        self._call_count += 1

        if self._should_timeout:
            raise TimeoutError("Solver timed out")

        time.sleep(self._delay)

        # Return mock solution
        strategies = {
            "AsAh": Strategy(
                hand=Hand.from_string("AsAh"),
                actions={ActionType.RAISE: 0.9, ActionType.CALL: 0.1, ActionType.FOLD: 0.0},
            ),
        }
        return Solution(
            game_state=game_state,
            strategies=strategies,
            ev={"AsAh": 5.0},
            convergence=0.3,
            iterations=iterations,
        )


def test_dynamic_fallback(tmp_path: Path):
    """Test PrecomputedSolver dynamic fallback on cache miss.

    When the cache misses, the solver should:
    1. Call the fallback solver to compute the solution on-the-fly
    2. Cache the result in memory
    3. Queue the result for disk cache storage
    4. Show loading state during computation
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    fallback = MockFallbackSolver()
    solver = PrecomputedSolver(
        cache_dir=cache_dir,
        fallback_solver=fallback,
        timeout=5.0,
    )

    # Create game state that won't be in cache
    gs = GameState(pot=100, effective_stack=100)

    # Verify fallback is called on cache miss
    solution = solver.solve(gs)

    # Assertions
    assert fallback._call_count == 1, "Fallback solver should be called once"
    assert isinstance(solution, Solution), "Should return a Solution"
    assert "AsAh" in solution.strategies, "Solution should have strategy from mock"

    # Verify result is cached in memory (second call should not hit fallback)
    solver.solve(gs)
    assert fallback._call_count == 1, "Second call should use memory cache"

    # Verify pending cache queue
    assert len(solver._pending_cache) == 1, "Should queue result for disk cache"

    # Flush to disk and verify
    count = solver.flush_pending_cache()
    assert count == 1, "Should write one solution to disk"

    key = solver._cache_key(gs)
    assert (cache_dir / f"{key}.json").exists(), "Cache file should exist"


class CachingPrecomputedSolver(PrecomputedSolver):
    """Extended PrecomputedSolver with dynamic fallback support."""

    def __init__(
        self,
        cache_dir: Path,
        fallback_solver=None,
        timeout: float = 5.0,
    ):
        super().__init__(cache_dir)
        self._fallback_solver = fallback_solver
        self._timeout = timeout
        self._pending_cache: dict[str, Solution] = {}

    def solve(
        self,
        game_state: GameState,
        iterations: int = 1000,
        target_exploitability: float = 0.5,
    ) -> Solution:
        """Solve with cache lookup and dynamic fallback."""
        key = self._cache_key(game_state)

        # Try memory cache first
        if key in self._cache:
            return self._cache[key]

        # Try disk cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            solution = self._load_cached_solution(cache_file, game_state)
            self._cache[key] = solution
            return solution

        # Dynamic fallback if available
        if self._fallback_solver is not None:
            solution = self._solve_with_fallback(game_state, key, iterations)
            return solution

        raise KeyError(f"No cached solution for: {key}")

    def _load_cached_solution(
        self, cache_file: Path, game_state: GameState
    ) -> Solution:
        """Load solution from cache file."""
        with open(cache_file) as f:
            data = json.load(f)

        strategies = {}
        for hand_str, action_dict in data.get("strategies", {}).items():
            try:
                hand = Hand.from_string(hand_str)
                actions = {
                    ActionType(k): v
                    for k, v in action_dict.items()
                    if k in [a.value for a in ActionType]
                }
                strategies[hand_str] = Strategy(hand=hand, actions=actions)
            except (ValueError, KeyError):
                continue

        return Solution(
            game_state=game_state,
            strategies=strategies,
            ev={},
            convergence=0.0,
            iterations=0,
        )

    def _solve_with_fallback(
        self,
        game_state: GameState,
        cache_key: str,
        iterations: int,
    ) -> Solution:
        """Run solver on-the-fly and queue for caching."""
        start = time.time()

        try:
            solution = self._fallback_solver.solve(
                game_state,
                iterations=iterations,
            )

            # Queue for async cache storage if within timeout
            elapsed = time.time() - start
            if elapsed < self._timeout:
                self._cache[cache_key] = solution
                self._pending_cache[cache_key] = solution

            return solution

        except TimeoutError:
            # Return minimal strategy on timeout
            return Solution(
                game_state=game_state,
                strategies={},
                ev={},
                convergence=float("inf"),
                iterations=0,
            )

    def flush_pending_cache(self) -> int:
        """Write pending solutions to disk cache.

        Returns:
            Number of solutions written
        """
        count = 0
        for key, solution in self._pending_cache.items():
            cache_file = self.cache_dir / f"{key}.json"
            data = {
                "strategies": {
                    hand_str: {a.value: f for a, f in strat.actions.items()}
                    for hand_str, strat in solution.strategies.items()
                },
                "ev": solution.ev,
                "convergence": solution.convergence,
                "iterations": solution.iterations,
            }
            with open(cache_file, "w") as f:
                json.dump(data, f)
            count += 1

        self._pending_cache.clear()
        return count


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def sample_cache_file(temp_cache_dir: Path) -> Path:
    """Create a sample cache file."""
    # This key matches the _cache_key output for our test game state
    cache_data = {
        "strategies": {
            "AsAh": {"raise": 0.85, "call": 0.15, "fold": 0.0},
            "KsKh": {"raise": 0.75, "call": 0.25, "fold": 0.0},
        },
        "ev": {"AsAh": 10.0, "KsKh": 7.0},
        "convergence": 0.25,
        "iterations": 500,
    }
    # Use a predictable filename
    cache_file = temp_cache_dir / "stack100_pot50_preflop_ip.json"
    with open(cache_file, "w") as f:
        json.dump(cache_data, f)
    return cache_file


class TestDynamicFallback:
    """Tests for dynamic solver fallback."""

    def test_dynamic_fallback(self, temp_cache_dir: Path):
        """Test that fallback solver is called on cache miss."""
        fallback = MockFallbackSolver()
        solver = CachingPrecomputedSolver(
            cache_dir=temp_cache_dir,
            fallback_solver=fallback,
        )

        gs = GameState(pot=100, effective_stack=100)

        solution = solver.solve(gs)

        assert fallback._call_count == 1
        assert isinstance(solution, Solution)

    def test_cache_hit_skips_fallback(
        self, temp_cache_dir: Path, sample_cache_file: Path
    ):
        """Test that cache hit doesn't call fallback."""
        fallback = MockFallbackSolver()
        solver = CachingPrecomputedSolver(
            cache_dir=temp_cache_dir,
            fallback_solver=fallback,
        )

        # Create game state that matches cache file key
        gs = GameState(pot=50, effective_stack=100, hero_position=Position.BTN)

        # Pre-populate the cache with key that matches
        key = solver._cache_key(gs)
        # Create matching cache file
        cache_data = {
            "strategies": {"AsAh": {"raise": 0.9, "call": 0.1, "fold": 0.0}},
        }
        with open(temp_cache_dir / f"{key}.json", "w") as f:
            json.dump(cache_data, f)

        solution = solver.solve(gs)

        assert fallback._call_count == 0
        assert isinstance(solution, Solution)

    def test_fallback_result_cached_in_memory(self, temp_cache_dir: Path):
        """Test that fallback results are cached in memory."""
        fallback = MockFallbackSolver()
        solver = CachingPrecomputedSolver(
            cache_dir=temp_cache_dir,
            fallback_solver=fallback,
        )

        gs = GameState(pot=100, effective_stack=100)

        # First call hits fallback
        solver.solve(gs)
        assert fallback._call_count == 1

        # Second call should use memory cache
        solver.solve(gs)
        assert fallback._call_count == 1

    def test_fallback_queued_for_disk_cache(self, temp_cache_dir: Path):
        """Test that fallback results are queued for disk cache."""
        fallback = MockFallbackSolver()
        solver = CachingPrecomputedSolver(
            cache_dir=temp_cache_dir,
            fallback_solver=fallback,
        )

        gs = GameState(pot=100, effective_stack=100)
        solver.solve(gs)

        # Should have pending cache entry
        assert len(solver._pending_cache) == 1

        # Flush to disk
        count = solver.flush_pending_cache()
        assert count == 1

        # Check file was created
        key = solver._cache_key(gs)
        assert (temp_cache_dir / f"{key}.json").exists()

    def test_timeout_returns_empty_solution(self, temp_cache_dir: Path):
        """Test that timeout returns minimal solution."""
        fallback = MockFallbackSolver(should_timeout=True)
        solver = CachingPrecomputedSolver(
            cache_dir=temp_cache_dir,
            fallback_solver=fallback,
            timeout=1.0,
        )

        gs = GameState(pot=100, effective_stack=100)
        solution = solver.solve(gs)

        assert isinstance(solution, Solution)
        assert len(solution.strategies) == 0
        assert solution.convergence == float("inf")

    def test_no_fallback_raises_keyerror(self, temp_cache_dir: Path):
        """Test that missing cache without fallback raises KeyError."""
        solver = CachingPrecomputedSolver(
            cache_dir=temp_cache_dir,
            fallback_solver=None,
        )

        gs = GameState(pot=100, effective_stack=100)

        with pytest.raises(KeyError):
            solver.solve(gs)


class TestCacheLoading:
    """Tests for cache file loading."""

    def test_load_cache_file(self, temp_cache_dir: Path):
        """Test loading solution from cache file."""
        # Create cache file
        cache_data = {
            "strategies": {
                "AsAh": {"raise": 0.9, "call": 0.1, "fold": 0.0},
            },
        }
        gs = GameState(pot=50, effective_stack=100, hero_position=Position.BTN)

        solver = CachingPrecomputedSolver(cache_dir=temp_cache_dir)
        key = solver._cache_key(gs)

        with open(temp_cache_dir / f"{key}.json", "w") as f:
            json.dump(cache_data, f)

        solution = solver.solve(gs)

        assert "AsAh" in solution.strategies
        assert solution.strategies["AsAh"].frequency(ActionType.RAISE) == 0.9

    def test_memory_cache_after_disk_load(self, temp_cache_dir: Path):
        """Test that disk cache is loaded into memory cache."""
        cache_data = {
            "strategies": {"AsAh": {"raise": 0.9, "call": 0.1, "fold": 0.0}},
        }
        gs = GameState(pot=50, effective_stack=100, hero_position=Position.BTN)

        solver = CachingPrecomputedSolver(cache_dir=temp_cache_dir)
        key = solver._cache_key(gs)

        with open(temp_cache_dir / f"{key}.json", "w") as f:
            json.dump(cache_data, f)

        # First load
        solver.solve(gs)

        # Should now be in memory cache
        assert key in solver._cache


class TestCacheKeyConsistency:
    """Test cache key generation consistency."""

    def test_same_state_same_key(self, temp_cache_dir: Path):
        """Test that identical game states produce same key."""
        solver = CachingPrecomputedSolver(cache_dir=temp_cache_dir)

        gs1 = GameState(pot=100, effective_stack=100, hero_position=Position.BTN)
        gs2 = GameState(pot=100, effective_stack=100, hero_position=Position.BTN)

        assert solver._cache_key(gs1) == solver._cache_key(gs2)

    def test_different_pot_different_key(self, temp_cache_dir: Path):
        """Test that different pots produce different keys."""
        solver = CachingPrecomputedSolver(cache_dir=temp_cache_dir)

        gs1 = GameState(pot=50, effective_stack=100)
        gs2 = GameState(pot=200, effective_stack=100)

        assert solver._cache_key(gs1) != solver._cache_key(gs2)
