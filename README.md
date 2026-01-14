# PokerCoach

AI-powered poker coaching system that combines an LLM (Claude) with GTO solver tools for real-time strategy advice and exploitative play recommendations.

## Features

- **GTO Solver Integration**: Query optimal strategy from any position via LLM-accessible tools
- **Pre-computed Caches**: Instant lookups for common preflop/postflop spots
- **Opponent Profiling**: Track HUD stats, classify player types, identify exploits
- **Hand History Import**: Import hands from PokerStars files
- **Vision Module**: Screen capture and game state extraction (for live play)
- **Real-time Coaching**: WebSocket-based live advice during sessions
- **Post-Game Analysis**: Review decisions with solver analysis

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests to verify everything works
uv run pytest

# Start the API server
uv run uvicorn pokercoach.web.app:app --reload

# The API will be available at http://localhost:8000
```

## Usage Examples

### 1. Ask the AI Coach

```python
from pokercoach.llm.coach import PokerCoach, CoachConfig
from pokercoach.solver.texas_solver import TexasSolverBridge, TexasSolverConfig
from pathlib import Path

# Setup solver (requires TexasSolver binary)
solver_config = TexasSolverConfig(binary_path=Path("/path/to/TexasSolver"))
solver = TexasSolverBridge(solver_config)

# Create coach
coach = PokerCoach(CoachConfig(api_key="your-anthropic-key"), solver)

# Ask a question - coach will use solver tools automatically
response = coach.ask("I have AQo in the CO, BTN opened 2.5x. Should I 3bet or call?")
print(response)
```

### 2. Query GTO Strategy Directly

```python
from pokercoach.solver.texas_solver import PrecomputedSolver
from pokercoach.core.game_state import GameState, Hand, Position
from pathlib import Path

# Use precomputed cache with dynamic fallback
solver = PrecomputedSolver(cache_dir=Path("cache/preflop"))

# Build game state
game_state = GameState(pot=7.5, effective_stack=100)
game_state.hero_position = Position.CO

# Get strategy for a hand
hand = Hand.from_string("AhQs")
strategy = solver.get_strategy(game_state, hand)

print(f"Primary action: {strategy.primary_action}")
for action, freq in strategy.actions.items():
    if freq > 0.01:
        print(f"  {action.value}: {freq*100:.1f}%")
```

### 3. Track Opponent Stats

```python
from pokercoach.opponent.stats import StatsCalculator, HandRecord, HandAction, Position, Street, ActionType
from pokercoach.opponent.profiler import OpponentProfiler

# Create calculator and profiler
calculator = StatsCalculator()
profiler = OpponentProfiler()

# Process a hand
hand = HandRecord(
    hand_id="12345",
    timestamp="2024-01-14T10:00:00Z",
    position=Position.BTN,
)
hand.add_action(HandAction(street=Street.PREFLOP, action_type=ActionType.RAISE, amount=2.5))
hand.add_action(HandAction(street=Street.FLOP, action_type=ActionType.BET, amount=5.0, pot_size=7.5))

calculator.process_hand("villain_123", hand)

# Get stats and profile
stats = calculator.get_stats("villain_123")
profile = profiler.build_profile("villain_123", stats)

print(f"Player type: {profile.player_type.name}")
print(f"VPIP: {stats.vpip:.1f}%, PFR: {stats.pfr:.1f}%")
print(f"Exploits: folds_too_much_to_3bet={profile.folds_too_much_to_3bet}")
```

### 4. Import Hand History

```python
from pokercoach.storage.importer import HandHistoryImporter, PokerStarsParser
from pathlib import Path

# Create importer
parser = PokerStarsParser(hero_name="YourScreenName")
importer = HandHistoryImporter(parser=parser, repository=your_repository)

# Import from file
result = importer.import_from_file(Path("hand_history.txt"))
print(f"Imported: {result.hands_imported}, Failed: {result.hands_failed}")

# Or import entire directory
result = importer.import_from_directory(Path("hand_histories/"))
```

### 5. Live Opponent Tracking (Vision Integration)

```python
from pokercoach.vision.tracking import LiveOpponentTracker

tracker = LiveOpponentTracker()
tracker.start_session()

# As hands are played (called by vision module):
tracker.on_hand_start("hand_001", {
    "villain1": {"position": "btn", "stack": 100},
    "villain2": {"position": "sb", "stack": 95},
})

tracker.on_action("villain1", "raise", amount=3.0, pot_size=1.5, street="preflop")
tracker.on_action("villain2", "call", amount=2.5, pot_size=4.5, street="preflop")

tracker.on_hand_complete(winners={"villain1": 10.0})

# Get live stats
stats = tracker.get_player_stats("villain1")
print(f"villain1 VPIP: {stats.vpip:.1f}%")

all_stats = tracker.end_session()
```

### 6. Use the Web API

```bash
# Start server
uv run uvicorn pokercoach.web.app:app --reload

# Health check
curl http://localhost:8000/health

# Ask coach (POST)
curl -X POST http://localhost:8000/api/coach/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Should I 3bet AKo from SB vs BTN open?"}'

# WebSocket for live game state
wscat -c ws://localhost:8000/api/ws/game-state
```

## Project Structure

```
src/pokercoach/
  core/           # Game state models, equity calculations
    game_state.py   # Card, Hand, Board, GameState, Action classes
    equity.py       # Equity calculation utilities

  solver/         # GTO solver integrations
    bridge.py       # SolverBridge protocol, Strategy, Solution
    texas_solver.py # TexasSolverBridge, PrecomputedSolver

  llm/            # LLM coach with tool access
    coach.py        # PokerCoach class with query_gto, compare_actions tools
    prompts.py      # System prompts and templates

  vision/         # Screen capture and detection
    capture.py      # ScreenCapture, HandCaptureHook, SessionStats
    detector.py     # CardDetector (ML-based card recognition)
    tracking.py     # LiveOpponentTracker, VisionIntegrationHook

  opponent/       # Player profiling and exploitation
    stats.py        # PlayerStats, StatsCalculator, StatCounter
    profiler.py     # OpponentProfiler, PlayerType enum

  storage/        # Database and import
    models.py       # SQLAlchemy models (HandRecord, Player, Action)
    database.py     # Database connection and session
    importer.py     # HandHistoryImporter, PokerStarsParser

  web/            # FastAPI backend
    app.py          # Application factory
    routes/
      coach.py      # /api/coach endpoints
      analysis.py   # /api/analysis endpoints
      opponents.py  # /api/opponents endpoints
      game_state.py # WebSocket /ws/game-state

frontend/         # React web interface
  src/components/
    CoachingWindow.tsx   # Main coaching overlay
    RangeGrid.tsx        # Visual range display
    EVChart.tsx          # EV comparison charts
    DecisionTimeline.tsx # Session decision history

cache/            # Pre-computed solver outputs
  preflop/          # RFI ranges, 3bet spots, squeeze spots
  postflop/         # Common flop textures

tests/            # Test suites
  unit/             # Unit tests
  integration/      # Integration tests
```

## Pre-computed Cache Files

The `cache/` directory contains pre-computed GTO solutions for common spots:

### Preflop (`cache/preflop/`)
- `rfi_utg.json` - Raise First In from UTG
- `rfi_hj.json` - Raise First In from HJ
- `rfi_co.json` - Raise First In from CO
- `rfi_btn.json` - Raise First In from BTN
- `rfi_sb.json` - Raise First In from SB
- `3bet_bb_vs_btn.json` - 3bet ranges BB vs BTN open
- `squeeze_bb.json` - Squeeze spots from BB

### Postflop (`cache/postflop/`)
- Common board textures for SRP and 3bet pots
- IP and OOP cbet frequencies

## Requirements

- Python 3.11+
- [TexasSolver](https://github.com/bupticybee/TexasSolver) binary (for live solving)
- Anthropic API key (for AI coach)

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run specific test
uv run pytest tests/unit/test_opponent_stats.py -v

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Configuration

### Solver Configuration

```python
from pokercoach.solver.texas_solver import TexasSolverConfig

config = TexasSolverConfig(
    binary_path=Path("/path/to/TexasSolver"),
    threads=6,                    # CPU threads for solving
    accuracy=0.3,                 # Target exploitability %
    max_iterations=1000,          # Max solver iterations
    use_isomorphism=True,         # Use suit isomorphism
    allin_threshold=0.67,         # Stack/pot ratio for allin
)
```

### Coach Configuration

```python
from pokercoach.llm.coach import CoachConfig

config = CoachConfig(
    model="claude-sonnet-4-20250514",  # Claude model
    api_key="sk-ant-...",              # Anthropic API key
    temperature=0.3,                    # Response temperature
    max_tokens=2048,                    # Max response length
)
```

## Player Type Classifications

The opponent profiler classifies players into these types based on VPIP/PFR/AF stats:

| Type | VPIP | PFR | Description |
|------|------|-----|-------------|
| ROCK | <12% | any | Extremely tight, only plays premiums |
| NIT | <18% | <12% | Very tight, passive |
| TAG | <18% | ≥18% | Tight aggressive (solid) |
| LAG | ≥28% | ≥18% | Loose aggressive |
| FISH | ≥28% | <12% | Loose passive (calling station) |
| MANIAC | >35% | any, AF>3 | Very loose, very aggressive |

## License

MIT
