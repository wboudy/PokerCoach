"""TexasSolver integration."""

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from pokercoach.core.game_state import Action, ActionType, Card, GameState, Hand, Position, Suit
from pokercoach.solver.bridge import Solution, SolverBridge, Strategy

# Default ranges for common spots
DEFAULT_IP_RANGE = (
    "AA,KK,QQ,JJ,TT,99:0.75,88:0.75,77:0.5,66:0.25,55:0.25,"
    "AK,AQs,AQo:0.75,AJs,AJo:0.5,ATs:0.75,A6s:0.25,A5s:0.75,A4s:0.75,A3s:0.5,A2s:0.5,"
    "KQs,KQo:0.5,KJs,KTs:0.75,K5s:0.25,K4s:0.25,"
    "QJs:0.75,QTs:0.75,Q9s:0.5,JTs:0.75,J9s:0.75,J8s:0.75,"
    "T9s:0.75,T8s:0.75,T7s:0.75,98s:0.75,97s:0.75,96s:0.5,"
    "87s:0.75,86s:0.5,85s:0.5,76s:0.75,75s:0.5,65s:0.75,64s:0.5,54s:0.75,53s:0.5,43s:0.5"
)

DEFAULT_OOP_RANGE = (
    "QQ:0.5,JJ:0.75,TT,99,88,77,66,55,44,33,22,"
    "AKo:0.25,AQs,AQo:0.75,AJs,AJo:0.75,ATs,ATo:0.75,A9s,A8s,A7s,A6s,A5s,A4s,A3s,A2s,"
    "KQ,KJ,KTs,KTo:0.5,K9s,K8s,K7s,K6s,K5s,K4s:0.5,K3s:0.5,K2s:0.5,"
    "QJ,QTs,Q9s,Q8s,Q7s,JTs,JTo:0.5,J9s,J8s,T9s,T8s,T7s,"
    "98s,97s,96s,87s,86s,76s,75s,65s,64s,54s,53s,43s"
)


@dataclass
class TexasSolverConfig:
    """Configuration for TexasSolver."""

    binary_path: Path
    threads: int = 6
    accuracy: float = 0.3  # Target exploitability %
    max_iterations: int = 1000
    use_isomorphism: bool = True
    resource_dir: Path | None = None
    ip_range: str = DEFAULT_IP_RANGE
    oop_range: str = DEFAULT_OOP_RANGE
    bet_sizes: dict[str, list[int]] = field(
        default_factory=lambda: {
            "flop": [50],
            "turn": [50],
            "river": [50],
        }
    )
    allin_threshold: float = 0.67
    dump_rounds: int = 2


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
        """
        Build command line arguments for solver.

        Creates a temporary input file with the solver configuration
        and returns the command to invoke the solver.

        Args:
            game_state: Current game state to solve

        Returns:
            List of command line arguments starting with binary path
        """
        # Generate solver input file content
        input_content = self._generate_input_file(game_state)

        # Write to temporary file (the file is kept until explicitly deleted
        # or process ends - we use delete=False so the solver can read it)
        # Using NamedTemporaryFile without context manager is intentional here
        # because the file must persist after this method returns for the solver to read
        self._input_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
            mode="w",
            suffix=".txt",
            prefix="solver_input_",
            delete=False,
        )
        self._input_file.write(input_content)
        self._input_file.close()

        # Build command
        cmd = [str(self.config.binary_path)]
        cmd.extend(["--input_file", self._input_file.name])

        # Add resource directory if configured
        if self.config.resource_dir:
            cmd.extend(["--resource_dir", str(self.config.resource_dir)])
        else:
            # Default to resources directory next to binary
            default_resource_dir = self.config.binary_path.parent / "resources"
            if default_resource_dir.exists():
                cmd.extend(["--resource_dir", str(default_resource_dir)])

        return cmd

    def _generate_input_file(self, game_state: GameState) -> str:
        """
        Generate the content of the solver input file.

        Args:
            game_state: Current game state

        Returns:
            String content for the solver input file
        """
        lines: list[str] = []

        # Basic game state
        lines.append(f"set_pot {game_state.pot:.0f}")
        lines.append(f"set_effective_stack {game_state.effective_stack:.0f}")

        # Board cards (only for postflop)
        if game_state.board.cards:
            board_str = ",".join(str(card) for card in game_state.board.cards)
            lines.append(f"set_board {board_str}")

        # Ranges
        lines.append(f"set_range_ip {self.config.ip_range}")
        lines.append(f"set_range_oop {self.config.oop_range}")

        # Bet sizes for each street and position
        for street_name, sizes in self.config.bet_sizes.items():
            for size in sizes:
                lines.append(f"set_bet_sizes oop,{street_name},bet,{size}")
                lines.append(f"set_bet_sizes oop,{street_name},raise,{size}")
                lines.append(f"set_bet_sizes ip,{street_name},bet,{size}")
                lines.append(f"set_bet_sizes ip,{street_name},raise,{size}")
            # Add allin option for each street
            lines.append(f"set_bet_sizes oop,{street_name},allin")
            lines.append(f"set_bet_sizes ip,{street_name},allin")

        # Allin threshold
        lines.append(f"set_allin_threshold {self.config.allin_threshold}")

        # Build the game tree
        lines.append("build_tree")

        # Solver configuration
        lines.append(f"set_thread_num {self.config.threads}")
        lines.append(f"set_accuracy {self.config.accuracy}")
        lines.append(f"set_max_iteration {self.config.max_iterations}")
        lines.append(f"set_use_isomorphism {1 if self.config.use_isomorphism else 0}")

        # Start solving
        lines.append("start_solve")

        # Output configuration
        lines.append(f"set_dump_rounds {self.config.dump_rounds}")
        lines.append("dump_result output_result.json")

        return "\n".join(lines)

    def _parse_output(self, output: str, game_state: GameState) -> Solution:
        """
        Parse solver JSON output into Solution object.

        Args:
            output: JSON string from solver output
            game_state: Original game state that was solved

        Returns:
            Solution object with strategies, EVs, and convergence metrics

        Raises:
            ValueError: If output is empty or invalid JSON
        """
        if not output or not output.strip():
            raise ValueError("Empty solver output")

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in solver output: {e}") from e

        # Extract top-level metrics
        exploitability = data.get("exploitability", 0.0)
        iterations = data.get("iterations", 0)

        # Extract strategies and EVs from root node
        root = data.get("root", {})
        raw_strategies = root.get("strategy", {})
        raw_evs = root.get("ev", {})

        # Build Strategy objects for each hand
        strategies: dict[str, Strategy] = {}
        for hand_str, action_freqs in raw_strategies.items():
            # Convert action names to ActionType enum
            actions: dict[ActionType, float] = {}
            for action_name, freq in action_freqs.items():
                try:
                    action_type = ActionType(action_name.lower())
                    actions[action_type] = freq
                except ValueError:
                    # Skip unknown action types
                    continue

            # Create Hand object for the strategy
            try:
                hand = Hand.from_string(hand_str)
                strategies[hand_str] = Strategy(hand=hand, actions=actions)
            except ValueError:
                # Skip hands that can't be parsed
                continue

        # Extract EVs
        evs: dict[str, float] = {}
        for hand_str, ev_value in raw_evs.items():
            evs[hand_str] = float(ev_value)

        return Solution(
            game_state=game_state,
            strategies=strategies,
            ev=evs,
            convergence=exploitability,
            iterations=iterations,
        )

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
    Solver that uses pre-computed solutions with dynamic fallback.

    Faster for common spots by looking up cached solutions
    instead of running the solver each time. When cache misses,
    can optionally run solver on-the-fly with timeout and queue
    the result for cache storage.
    """

    def __init__(
        self,
        cache_dir: Path,
        fallback_solver: SolverBridge | None = None,
        timeout: float = 30.0,
    ):
        self.cache_dir = cache_dir
        self._cache: dict[str, Solution] = {}
        self._fallback_solver = fallback_solver
        self._timeout = timeout
        self._pending_cache: dict[str, Solution] = {}
        self._loading = False  # Indicates if dynamic solving is in progress

    def _cache_key(self, game_state: GameState) -> str:
        """Generate cache key from game state.

        Normalizes the game state for cache lookup using:
        - Stack bucketing (100bb buckets)
        - Pot as percentage of stack
        - Suit isomorphism (canonicalize board texture)
        - Relative position (IP/OOP)

        Args:
            game_state: Current game state to generate key for

        Returns:
            Canonical string key for cache lookup
        """
        parts: list[str] = []

        # 1. Stack bucketing - round to nearest 100bb bucket
        stack_bucket = int(game_state.effective_stack // 100) * 100
        if stack_bucket == 0:
            stack_bucket = 100  # Minimum bucket
        parts.append(f"stack{stack_bucket}")

        # 2. Pot as percentage of stack (rounded to nearest 10%)
        if game_state.effective_stack > 0:
            pot_pct = int(round(game_state.pot / game_state.effective_stack * 10)) * 10
        else:
            pot_pct = 0
        parts.append(f"pot{pot_pct}")

        # 3. Board texture with suit isomorphism
        if game_state.board.cards:
            canonical_board = self._canonicalize_board(game_state.board.cards)
            parts.append(f"board_{canonical_board}")
        else:
            parts.append("preflop")

        # 4. Position normalization (simplified to IP/OOP concept)
        if game_state.hero_position:
            # BTN, CO, HJ are typically IP positions
            ip_positions = {Position.BTN, Position.CO, Position.HJ}
            if game_state.hero_position in ip_positions:
                parts.append("ip")
            else:
                parts.append("oop")
        else:
            parts.append("unk")

        return "_".join(parts)

    def _canonicalize_board(self, cards: list[Card]) -> str:
        """Canonicalize board cards with suit isomorphism.

        Transforms suits to a canonical form where:
        - First suit seen becomes 'a'
        - Second unique suit becomes 'b'
        - And so on...

        This ensures Ah Kd 2c produces the same key as As Kh 2d.

        However, we preserve flush draw information by tracking
        how many cards share each suit.

        Args:
            cards: List of Card objects

        Returns:
            Canonical board string
        """
        if not cards:
            return "empty"

        # Map original suits to canonical suits
        suit_map: dict[Suit, str] = {}
        canonical_suits = ['a', 'b', 'c', 'd']
        next_canonical = 0

        # Count suits for flush texture
        suit_counts: dict[Suit, int] = {}
        for card in cards:
            suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1

        # Sort cards by rank (descending) for consistent ordering
        sorted_cards = sorted(cards, key=lambda c: -c.rank.value_int)

        canonical_parts = []
        for card in sorted_cards:
            # Get or assign canonical suit
            if card.suit not in suit_map:
                suit_map[card.suit] = canonical_suits[next_canonical]
                next_canonical = min(next_canonical + 1, 3)

            canonical_parts.append(f"{card.rank.value}{suit_map[card.suit]}")

        # Add texture indicator based on suit distribution
        texture = self._get_board_texture(suit_counts)

        return f"{'-'.join(canonical_parts)}_{texture}"

    def _get_board_texture(self, suit_counts: dict[Suit, int]) -> str:
        """Determine board texture from suit counts.

        Args:
            suit_counts: Dict mapping suits to count of cards

        Returns:
            Texture string: 'mono' (3 suited), 'fd' (2 suited), 'rainbow'
        """
        max_suited = max(suit_counts.values()) if suit_counts else 0

        if max_suited >= 3:
            return "mono"  # Monotone (flush possible)
        elif max_suited == 2:
            return "fd"  # Flush draw
        else:
            return "rainbow"  # No flush draw

    @property
    def is_loading(self) -> bool:
        """Check if dynamic solving is currently in progress."""
        return self._loading

    def solve(
        self,
        game_state: GameState,
        iterations: int = 1000,
        target_exploitability: float = 0.5,
    ) -> Solution:
        """Look up pre-computed solution with dynamic fallback.

        First checks memory cache, then disk cache. If both miss
        and a fallback solver is configured, runs solver on-the-fly
        with timeout and queues the result for cache storage.

        Args:
            game_state: Current game state to solve
            iterations: Max iterations for convergence (for fallback)
            target_exploitability: Target exploitability (for fallback)

        Returns:
            Solution with strategies and EVs

        Raises:
            KeyError: If no cached solution and no fallback solver configured
        """
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

        raise KeyError(f"No cached solution for game state: {key}")

    def _load_cached_solution(
        self, cache_file: Path, game_state: GameState
    ) -> Solution:
        """Load solution from cache file.

        Args:
            cache_file: Path to the cache file
            game_state: Game state for the solution

        Returns:
            Deserialized Solution object
        """
        with open(cache_file) as f:
            data = json.load(f)

        strategies: dict[str, Strategy] = {}
        for hand_str, action_dict in data.get("strategies", {}).items():
            try:
                hand = Hand.from_string(hand_str)
                actions: dict[ActionType, float] = {}
                for k, v in action_dict.items():
                    try:
                        actions[ActionType(k)] = v
                    except ValueError:
                        continue
                strategies[hand_str] = Strategy(hand=hand, actions=actions)
            except (ValueError, KeyError):
                continue

        return Solution(
            game_state=game_state,
            strategies=strategies,
            ev=data.get("ev", {}),
            convergence=data.get("convergence", 0.0),
            iterations=data.get("iterations", 0),
        )

    def _solve_with_fallback(
        self,
        game_state: GameState,
        cache_key: str,
        iterations: int,
    ) -> Solution:
        """Run solver on-the-fly and queue result for caching.

        Args:
            game_state: Current game state to solve
            cache_key: Key for caching the result
            iterations: Max iterations for solver

        Returns:
            Solution from fallback solver, or minimal solution on timeout
        """
        import time

        self._loading = True
        start = time.time()

        try:
            solution = self._fallback_solver.solve(
                game_state,
                iterations=iterations,
            )

            # Queue for cache storage if completed within timeout
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
        finally:
            self._loading = False

    def flush_pending_cache(self) -> int:
        """Write pending solutions to disk cache.

        Should be called periodically to persist dynamically
        computed solutions.

        Returns:
            Number of solutions written to disk
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
