# PokerCoach

AI-powered poker coaching system that augments an LLM with GTO solver tools for optimal strategy analysis and exploitative play recommendations.

## Features

- **GTO Solver Integration**: Query optimal strategy from any position via LLM-accessible tools
- **Vision Module**: Real-time screen capture and game state extraction from online poker clients
- **Post-Game Analysis**: Chess.com-style hand review with blunder detection and leak patterns
- **Exploitative Engine**: Opponent profiling and deviation recommendations

## Quick Start

```bash
# Install with uv
uv sync

# Run the CLI
uv run pokercoach --help

# Start the web interface
uv run pokercoach serve
```

## Project Structure

```
src/pokercoach/
  core/           # Game state models, equity calculations
  solver/         # GTO solver integrations (TexasSolver, etc.)
  llm/            # LLM coach with tool access
  vision/         # Screen capture and card detection
  analysis/       # Hand history parsing and evaluation
  opponent/       # Player profiling and exploitation
  web/            # FastAPI backend

frontend/         # React web interface
tests/            # Test suites
docs/             # Documentation
```

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

## Documentation

- [Implementation Plan](thoughts/shared/plans/pokercoach-mvp-plan.md)
- [Architecture](docs/ARCHITECTURE.md)

## License

MIT
