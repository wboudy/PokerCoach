"""TexasSolver integration."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pokercoach.core.game_state import Action, GameState, Hand
from pokercoach.solver.bridge import Solution, SolverBridge, Strategy


@dataclass
class TexasSolverConfig:
    """Configuration for TexasSolver."""

    binary_path: Path
    threads: int = 6
    accuracy: float = 0.3  # Target exploitability %
    max_iterations: int = 1000
    use_isomorphism: bool = True


class TexasSolverBridge(SolverBridge):
    """Bridge to TexasSolver binary."""

    def __init__(self, config: TexasSolverConfig):
        self.config = config
        self._validate_binary()

    def _validate_binary(self) -> None:
        """Ensure solver binary exists and is executable."""
        if not self.config.binary_path.exists():
            raise FileNotFoundError(
                f"TexasSolver binary not found at {self.config.binary_path}. "
                "Please build from source or download from "
                "https://github.com/bupticybee/TexasSolver"
            )

    def _build_command(self, game_state: GameState) -> list[str]:
        """Build command line arguments for solver."""
        # TODO: Implement game state to CLI args conversion
        # This depends on TexasSolver's input format
        raise NotImplementedError("Command building not yet implemented")

    def _parse_output(self, output: str, game_state: GameState) -> Solution:
        """Parse solver JSON output into Solution object."""
        # TODO: Implement output parsing
        raise NotImplementedError("Output parsing not yet implemented")

    def solve(
        self,
        game_state: GameState,
        iterations: int = 1000,
        target_exploitability: float = 0.5,
    ) -> Solution:
        """Run solver and return solution."""
        cmd = self._build_command(game_state)
        cmd.extend(["--iterations", str(iterations)])
        cmd.extend(["--accuracy", str(target_exploitability)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"Solver failed: {result.stderr}")

        return self._parse_output(result.stdout, game_state)

    def get_strategy(self, game_state: GameState, hand: Hand) -> Strategy:
        """Get strategy for specific hand from cached or new solution."""
        solution = self.solve(game_state)
        strategy = solution.get_strategy(hand)
        if strategy is None:
            raise ValueError(f"No strategy found for hand {hand}")
        return strategy

    def get_ev(self, game_state: GameState, hand: Hand, action: Action) -> float:
        """Get EV for specific action."""
        # Would need to solve and extract EV
        raise NotImplementedError

    def compare_actions(
        self,
        game_state: GameState,
        hand: Hand,
        actions: list[Action],
    ) -> dict[Action, float]:
        """Compare EVs of multiple actions."""
        raise NotImplementedError


class PrecomputedSolver(SolverBridge):
    """
    Solver that uses pre-computed solutions.

    Faster for common spots by looking up cached solutions
    instead of running the solver each time.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self._cache: dict[str, Solution] = {}

    def _cache_key(self, game_state: GameState) -> str:
        """Generate cache key from game state."""
        # TODO: Implement canonical game state hashing
        raise NotImplementedError

    def solve(
        self,
        game_state: GameState,
        iterations: int = 1000,
        target_exploitability: float = 0.5,
    ) -> Solution:
        """Look up pre-computed solution."""
        key = self._cache_key(game_state)

        if key in self._cache:
            return self._cache[key]

        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
                # TODO: Deserialize solution
                raise NotImplementedError

        raise KeyError(f"No cached solution for game state: {key}")

    def get_strategy(self, game_state: GameState, hand: Hand) -> Strategy:
        solution = self.solve(game_state)
        strategy = solution.get_strategy(hand)
        if strategy is None:
            raise ValueError(f"No strategy found for hand {hand}")
        return strategy

    def get_ev(self, game_state: GameState, hand: Hand, action: Action) -> float:
        raise NotImplementedError

    def compare_actions(
        self,
        game_state: GameState,
        hand: Hand,
        actions: list[Action],
    ) -> dict[Action, float]:
        raise NotImplementedError
