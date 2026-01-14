# Agent Instructions

PokerCoach is an AI-powered poker coaching system with GTO solver integration. This document provides everything an agent needs to work on this codebase.

## Project Overview

- **Language**: Python 3.11+
- **Package Manager**: uv
- **Architecture**: LLM coach augmented with GTO solver tools
- **Key Modules**: core (game state), solver (TexasSolver), llm (coach), vision (screen capture), analysis (hand history), opponent (profiling)

## Development Commands

```bash
# Setup
uv sync --extra dev          # Install all dependencies

# Quality Gates (run before any commit)
uv run pytest                # Run tests with coverage
uv run ruff check src/       # Lint
uv run ruff format src/      # Format
uv run mypy src/             # Type check

# Run application
uv run pokercoach --help     # CLI
uv run pokercoach serve      # Web server
```

## Quality Gates

**All code changes MUST pass these checks before completion:**

| Check | Command | Must Pass |
|-------|---------|-----------|
| Tests | `uv run pytest` | Yes |
| Lint | `uv run ruff check src/` | Yes |
| Types | `uv run mypy src/` | Yes |
| Format | `uv run ruff format --check src/` | Yes |

Quick validation script:
```bash
uv run pytest && uv run ruff check src/ && uv run mypy src/
```

## Project Structure

```
src/pokercoach/
  core/           # GameState, Card, Hand, Board, Action models
  solver/         # SolverBridge ABC, TexasSolver implementation
  llm/            # PokerCoach class, prompts, tools
  vision/         # ScreenCapture, CardDetector, OCR
  analysis/       # HandHistoryParser, HandEvaluator, LeakDetector
  opponent/       # PlayerStats, OpponentProfiler, ExploitationEngine
  web/            # FastAPI app, routes

tests/
  unit/           # Unit tests (test_game_state.py, test_opponent_stats.py)
  integration/    # Integration tests (test_api.py)

thoughts/beads/   # Markdown-based work tracking (Phase 1 beads)
docs/             # Architecture documentation
```

## Beads System

This project uses two bead tracking systems:

### 1. Markdown Beads (`thoughts/beads/`)

Atomic work units with acceptance criteria. Structure:
```
thoughts/beads/
├── backlog/       # Ready to execute
├── in-progress/   # Currently being worked
├── completed/     # Done
└── blocked/       # Needs resolution
```

**Bead Format** (`BEAD-NNN-short-name.md`):
```yaml
---
id: BEAD-NNN
title: Short title
phase: 1
priority: P0/P1/P2
dependencies: [BEAD-XXX]
files:
  - path/to/file.py
---

## Context
What and why.

## Acceptance Criteria
- [ ] Criterion with testable command
- [ ] `pytest tests/unit/test_foo.py` passes

## Implementation Notes
Guidance for implementation.
```

**Workflow**:
1. Read bead from `backlog/`
2. Move to `in-progress/` (rename file)
3. Implement and run acceptance criteria
4. Move to `completed/` on success
5. Move to `blocked/` if stuck (add blocker note)

### 2. BD CLI (`.beads/`)

Git-backed issue tracking. Commands:
```bash
bd ready                           # Find available work
bd show <id>                       # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>                      # Complete work
bd sync                            # Sync with git
```

## God Ralph Integration

For autonomous execution of beads with validation:

### Prerequisites
1. Beads must be in `bd` database (not just markdown)
2. Each bead needs **executable** acceptance criteria
3. Acceptance criteria should be shell commands that exit 0 on success

### Creating Ralph-Ready Beads

Use `/god-ralph plan` or create manually:
```bash
bd create --title="Implement X" --type=task --priority=2
bd update <id> --acceptance-criteria="uv run pytest tests/unit/test_x.py"
```

### Running God Ralph

```bash
/god-ralph start    # Start orchestrator (runs ready beads in parallel)
/god-ralph status   # Check progress
/god-ralph stop     # Stop gracefully
```

### Validation Flow

God Ralph workers:
1. Claim bead, mark `in_progress`
2. Implement based on context/acceptance criteria
3. Run acceptance criteria commands
4. If pass → `bd close <id>`
5. If fail → iterate or create fix-bead

## Phase 1 Beads (Current Work)

| ID | Title | Priority | Dependencies | Validation |
|----|-------|----------|--------------|------------|
| BEAD-001 | GameState.to_solver_format() | P0 | - | `pytest tests/unit/test_game_state.py` |
| BEAD-002 | Acquire TexasSolver binary | P0 | - | Binary exists at expected path |
| BEAD-003 | Solution/Strategy data types | P0 | - | Type check passes |
| BEAD-004 | TexasSolver _build_command() | P1 | 001, 002 | Unit tests pass |
| BEAD-005 | TexasSolver _parse_output() | P1 | 003, 004 | Unit tests pass |
| BEAD-006 | Precomputed solution cache | P2 | 003, 005 | Cache hit/miss tests |
| BEAD-007 | LLM query_gto tool | P1 | 003, 005 | Integration test |
| BEAD-008 | LLM explain_line tool | P2 | 007 | Integration test |
| BEAD-009 | LLM compare_actions tool | P2 | 007 | Integration test |
| BEAD-010 | Coach integration E2E | P1 | 005, 007-009 | E2E test suite |

**Critical Path**: 001+002+003 (parallel) → 004 → 005 → 007 → 010

## Code Style

- **Formatting**: ruff format (100 char line length)
- **Linting**: ruff with E, F, I, N, W, UP, B, C4, SIM rules
- **Types**: mypy strict mode
- **Tests**: pytest with coverage, asyncio_mode=auto

## Key Patterns

### Solver Bridge (Strategy Pattern)
```python
class SolverBridge(ABC):
    @abstractmethod
    def solve(self, game_state: GameState) -> Solution: ...
```

### Game State Conversion
```python
game_state.to_solver_format()  # Returns solver-compatible string
```

### LLM Tools
Tools defined in `llm/coach.py`: `query_gto`, `compare_actions`, `explain_line`

## Landing the Plane (Session Completion)

**MANDATORY**: Work is NOT complete until `git push` succeeds.

### Checklist

```bash
# 1. Run quality gates
uv run pytest && uv run ruff check src/ && uv run mypy src/

# 2. Stage changes
git status
git add <files>

# 3. Sync beads
bd sync

# 4. Commit
git commit -m "Description of changes

Co-Authored-By: Claude <noreply@anthropic.com>"

# 5. Push
git pull --rebase
git push

# 6. Verify
git status  # Must show "up to date with origin"
```

### Critical Rules

- **NEVER** stop before pushing - work is stranded locally
- **NEVER** say "ready to push when you are" - YOU must push
- **ALWAYS** run quality gates before committing
- **ALWAYS** sync beads before pushing
- If push fails, resolve and retry until success

### Handoff

When ending a session, provide:
1. What was completed
2. What's in progress (with bead IDs)
3. Any blockers discovered
4. Suggested next steps

## Troubleshooting

### Tests Failing
```bash
uv run pytest -v --tb=short  # Verbose with short traceback
uv run pytest tests/unit/test_specific.py::test_name  # Run single test
```

### Type Errors
```bash
uv run mypy src/ --show-error-codes  # Show error codes
```

### Lint Fixes
```bash
uv run ruff check src/ --fix  # Auto-fix what's possible
```

### Dependency Issues
```bash
uv sync --refresh  # Refresh lockfile
```

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready              # Show issues ready to work (no blockers)
bd list --status=open # All open issues
bd show <id>          # Full issue details with dependencies
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes
```

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `bd close <id>`
5. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
bd sync                 # Commit beads changes
git commit -m "..."     # Commit code
bd sync                 # Commit any new beads changes
git push                # Push to remote
```

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->
