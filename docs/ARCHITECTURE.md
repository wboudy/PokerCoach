# PokerCoach Architecture

This document describes the architecture of PokerCoach, an AI-powered poker coaching system.

## Overview

PokerCoach augments a large language model (LLM) with poker-specific tools to provide GTO (Game Theory Optimal) strategy analysis and exploitative play recommendations.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           PokerCoach                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────────────┐  │
│  │    Vision     │   │  LLM Coach    │   │      Web UI           │  │
│  │    Module     │   │  + Solver     │   │   (React/FastAPI)     │  │
│  └───────┬───────┘   └───────┬───────┘   └───────────┬───────────┘  │
│          │                   │                       │               │
│          ▼                   ▼                       ▼               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      Core Domain Layer                         │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │  │
│  │  │GameState│  │ Solver  │  │Analysis │  │    Opponent     │   │  │
│  │  │ Models  │  │ Bridge  │  │ Engine  │  │    Profiler     │   │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      Storage Layer                             │  │
│  │            SQLite/PostgreSQL + File Cache                      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Architecture

### Core Domain (`pokercoach/core/`)

The foundation layer containing poker-specific data models.

```
core/
├── game_state.py    # Card, Hand, Board, Action, GameState
└── equity.py        # Hand equity calculations
```

**Key Classes:**
- `Card`, `Hand`, `Board` - Card representations
- `Action`, `ActionType` - Poker actions
- `GameState` - Complete hand state
- `Position` - Player positions (BTN, CO, etc.)

### Solver Integration (`pokercoach/solver/`)

Abstract interface to GTO solvers with concrete implementations.

```
solver/
├── bridge.py        # SolverBridge ABC, Strategy, Solution
└── texas_solver.py  # TexasSolver implementation
```

**Design Pattern:** Strategy pattern for solver swapping.

```python
class SolverBridge(ABC):
    @abstractmethod
    def solve(self, game_state: GameState) -> Solution: ...

    @abstractmethod
    def get_strategy(self, state: GameState, hand: Hand) -> Strategy: ...
```

### LLM Coach (`pokercoach/llm/`)

Tool-augmented LLM for natural language coaching.

```
llm/
├── coach.py         # PokerCoach class
└── prompts.py       # System prompts
```

**Tool Integration:**
- `query_gto` - Query solver for optimal strategy
- `compare_actions` - Compare EVs of different actions
- `explain_line` - Strategic explanation

### Vision Module (`pokercoach/vision/`)

Computer vision for screen capture and game state extraction.

```
vision/
├── capture.py       # ScreenCapture (mss-based)
├── detector.py      # CardDetector, OCRExtractor
└── calibration.py   # Site-specific calibration
```

**Pipeline:**
```
Screenshot → Region Extraction → Card Detection/OCR → GameState
```

### Analysis Engine (`pokercoach/analysis/`)

Hand history parsing and GTO comparison.

```
analysis/
├── parser.py        # HandHistoryParser implementations
├── evaluator.py     # HandEvaluator, DecisionQuality
└── patterns.py      # LeakDetector, TrendAnalyzer
```

**Decision Quality Scale:**
| Rating | EV Loss (BB) |
|--------|--------------|
| Blunder | > 1.0 |
| Mistake | 0.5 - 1.0 |
| Inaccuracy | 0.1 - 0.5 |
| Good | < 0.1 |
| Excellent | ~0 |

### Opponent Profiling (`pokercoach/opponent/`)

Player statistics and exploitation engine.

```
opponent/
├── stats.py         # PlayerStats, StatsCalculator
├── profiler.py      # OpponentProfiler, PlayerType
└── exploiter.py     # ExploitationEngine
```

**Player Types:**
- NIT - Very tight, passive (VPIP < 15, PFR < 12)
- TAG - Tight aggressive (VPIP 15-25, PFR > 15)
- LAG - Loose aggressive (VPIP > 25, PFR > 20)
- FISH - Loose passive (VPIP > 30, PFR < 15)
- MANIAC - Very loose, very aggressive

### Site Adapters (`pokercoach/sites/`)

Site-specific configurations and detection.

```
sites/
├── base.py          # SiteAdapter ABC
└── pokerstars.py    # PokerStarsAdapter
```

### Web API (`pokercoach/web/`)

FastAPI backend with REST and WebSocket support.

```
web/
├── app.py           # FastAPI application
└── routes/
    ├── coach.py     # /api/coach/* endpoints
    ├── analysis.py  # /api/analysis/* endpoints
    └── opponents.py # /api/opponents/* endpoints
```

## Data Flow

### Live Coaching Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Screen  │───▶│  Vision  │───▶│  Coach   │───▶│    UI    │
│ Capture  │    │  Module  │    │   LLM    │    │ Display  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │               │
                     ▼               ▼
               ┌──────────┐    ┌──────────┐
               │   Site   │    │  Solver  │
               │ Adapter  │    │  Bridge  │
               └──────────┘    └──────────┘
```

### Post-Game Analysis Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│   Hand   │───▶│  Parser  │───▶│Evaluator │───▶│ Report   │
│ History  │    │          │    │          │    │Generator │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
               ┌──────────┐                   ┌──────────┐
               │  Solver  │                   │   Leak   │
               │  Bridge  │                   │ Detector │
               └──────────┘                   └──────────┘
```

### Exploitation Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Player  │───▶│  Stats   │───▶│ Profiler │───▶│Exploiter │
│  Hands   │    │Calculator│    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                                                      ▼
                                               ┌──────────┐
                                               │ Adjusted │
                                               │ Strategy │
                                               └──────────┘
```

## Storage Architecture

### Database Schema

```
┌─────────────────┐     ┌─────────────────┐
│    sessions     │     │    players      │
├─────────────────┤     ├─────────────────┤
│ id              │     │ id              │
│ session_id      │     │ player_id       │
│ timestamp       │     │ site            │
│ accuracy_score  │     │ vpip, pfr, ...  │
│ total_ev_loss   │     │ player_type     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │    ┌─────────────────┐│
         └───▶│     hands       │◀┘
              ├─────────────────┤
              │ id              │
              │ hand_id         │
              │ session_id (FK) │
              │ player_id (FK)  │
              │ hero_hand       │
              │ analysis_data   │
              └─────────────────┘
```

### File Storage

```
~/.pokercoach/
├── config.json           # User configuration
├── calibrations/         # Site calibration files
│   └── pokerstars.json
├── cache/
│   └── solutions/        # Cached solver solutions
└── database.db           # SQLite database
```

## Security Considerations

1. **No Automation** - System is for analysis only, no automated play
2. **Local Processing** - Vision runs locally, no screenshots sent externally
3. **User Acknowledgment** - Users must acknowledge site TOS implications
4. **API Key Management** - LLM API keys stored securely in config

## Performance Targets

| Component | Target | Notes |
|-----------|--------|-------|
| Vision Pipeline | < 500ms | End-to-end detection |
| Solver Query (cached) | < 100ms | Pre-computed solutions |
| Solver Query (new) | < 5s | Simple spots |
| Hand Analysis | < 1s/hand | Batch processing |
| API Response | < 100ms | P95 latency |

## Extension Points

### Adding a New Solver

1. Implement `SolverBridge` interface
2. Add configuration for solver binary/API
3. Register in solver factory

### Adding a New Poker Site

1. Create site adapter extending `SiteAdapter`
2. Define calibration regions
3. Add card templates if using template matching
4. Register in site factory

### Adding New Analysis Types

1. Extend `HandEvaluator` with new metrics
2. Add new `LeakPattern` types
3. Create API endpoints in `routes/analysis.py`

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Language | Python 3.11+ | ML ecosystem, rapid development |
| LLM | Claude/GPT-4 | Tool use, reasoning capability |
| Solver | TexasSolver | Open-source, performant |
| Vision | OpenCV + mss | Proven, cross-platform |
| OCR | EasyOCR | Better accuracy than Tesseract |
| Database | SQLite | Simple, portable |
| API | FastAPI | Async, OpenAPI docs |
| Frontend | React + TypeScript | Modern, type-safe |
