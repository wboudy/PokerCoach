# Implementation Plan: PokerCoach MVP

**Generated:** 2026-01-13
**Version:** 1.0

---

## Goal

Build an AI-powered poker coaching system that augments an LLM with solver tools to provide:
1. Real-time GTO strategy analysis from any position
2. Automated game state recognition via computer vision
3. Post-game hand analysis with Chess.com-style review
4. Exploitative play recommendations based on opponent profiling

---

## Research Summary

### GTO Solver Options

| Solver | Type | Performance | Integration |
|--------|------|-------------|-------------|
| [TexasSolver](https://github.com/bupticybee/TexasSolver) | Open-source C++ | 29% faster than PioSolver | CLI/API, AGPL license |
| [sol5000/gto](https://github.com/sol5000/gto) | Python/Streamlit | Monte Carlo equity | Native Python, JSON output |
| [PioSOLVER](https://piosolver.com/) | Commercial | Industry standard | Command-line API |
| [GTO Wizard API](https://gtowizard.com/) | Commercial SaaS | Pre-computed solutions | REST API (if available) |

**Recommendation:** Start with TexasSolver for open-source flexibility, with abstraction layer to support commercial solvers later.

### Computer Vision Stack

| Component | Library | Purpose |
|-----------|---------|---------|
| Screen Capture | mss | Fast cross-platform capture (~320ms) |
| Card Recognition | OpenCV + Moondream-2B | Template matching + VLM fallback |
| OCR | Tesseract / EasyOCR | Pot/stack size extraction |
| UI Detection | OpenCV contours | Button/action detection |

**Reference Projects:**
- [ace-autopilot-poker-ai](https://github.com/newMeta98/ace-autopilot-poker-ai) - Full vision pipeline
- [poker-vision](https://github.com/MemDbg/poker-vision) - OpenCV card detection
- [PyPokerBot](https://github.com/gbencke/PyPokerBot) - OpenCV + Tesseract integration

### Hand History Parsing

| Library | Language | Sites Supported |
|---------|----------|-----------------|
| [poker](https://pypi.org/project/poker/) | Python | PokerStars, FTP, PKR |
| [poker-log-parser](https://pypi.org/project/poker-log-parser/) | Rust/Python | PokerStars, Pluribus |
| [PHH Format](https://arxiv.org/html/2312.11753v2) | Standard | Universal (academic) |

**Recommendation:** Use `poker-log-parser` for speed, with PHH as internal format.

### Opponent Modeling

| Approach | Complexity | Effectiveness |
|----------|------------|---------------|
| Statistical HUD (VPIP/PFR/etc) | Low | Good baseline |
| [PokerRL](https://github.com/EricSteinberger/PokerRL) framework | High | Deep CFR + NFSP |
| Style embeddings + RL | Medium | [AMP3 approach](https://link.springer.com/article/10.1007/s00521-025-11262-x) |
| LLM-guided adaptation | Medium | [Stanford research](https://cs224r.stanford.edu/projects/pdfs/cs224rFinalProject.pdf) shows 5% improvement |

**Recommendation:** Start with statistical profiling, add RL-based exploitation in Phase 4.

---

## Architecture Overview

```
+------------------------------------------------------------------+
|                         PokerCoach                                |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+    +------------------+    +---------------+ |
|  |   Vision Module  |    |   LLM + Solver   |    |  Analysis UI  | |
|  |  (Screen Reader) |    |   (Coach Core)   |    |   (Web App)   | |
|  +--------+---------+    +--------+---------+    +-------+-------+ |
|           |                       |                      |         |
|           v                       v                      v         |
|  +------------------+    +------------------+    +---------------+ |
|  |  Game State      |    |   Solver Bridge  |    |  Hand Review  | |
|  |  Extractor       |    |   (GTO Engine)   |    |   Engine      | |
|  +--------+---------+    +--------+---------+    +-------+-------+ |
|           |                       |                      |         |
|           +----------+------------+----------------------+         |
|                      |                                             |
|                      v                                             |
|           +---------------------+                                  |
|           |   Data Layer        |                                  |
|           | - Hand History DB   |                                  |
|           | - Player Profiles   |                                  |
|           | - Session Memory    |                                  |
|           +---------------------+                                  |
|                                                                    |
+------------------------------------------------------------------+
```

---

## Implementation Phases

### Phase 1: Foundation & Solver Integration (Weeks 1-3)

**Goal:** LLM that can query GTO solver and explain strategy

#### Files to Create

```
src/
  pokercoach/
    __init__.py
    core/
      __init__.py
      game_state.py      # Hand/Board/Action data models
      solver_bridge.py   # Abstract solver interface
      equity.py          # Hand equity calculations
    solver/
      __init__.py
      texas_solver.py    # TexasSolver wrapper
      precomputed.py     # Cached solution lookup
    llm/
      __init__.py
      coach.py           # Main LLM coach interface
      prompts.py         # System prompts for poker coaching
      tools.py           # Tool definitions for solver access
```

#### Implementation Steps

1. **Define core data models** (`game_state.py`)
   - `Card`, `Hand`, `Board` classes
   - `Action` enum (fold, check, call, bet, raise, all-in)
   - `GameState` with positions, stacks, pot, board, actions
   - `Range` class for hand range representation

2. **Create solver abstraction** (`solver_bridge.py`)
   ```python
   class SolverBridge(ABC):
       @abstractmethod
       def solve(self, game_state: GameState, iterations: int) -> Solution: ...

       @abstractmethod
       def get_strategy(self, game_state: GameState, hand: Hand) -> Strategy: ...

       @abstractmethod
       def get_ev(self, game_state: GameState, hand: Hand, action: Action) -> float: ...
   ```

3. **Implement TexasSolver wrapper** (`texas_solver.py`)
   - Build TexasSolver from source or use pre-built binary
   - Parse CLI output into structured data
   - Cache solutions for common spots

4. **Create LLM coach** (`coach.py`)
   - Tool-augmented LLM (Claude/GPT-4)
   - Tools: `query_gto`, `explain_line`, `compare_actions`
   - Conversational interface for strategy discussion

#### Acceptance Criteria
- [ ] Can query optimal strategy for any NLHE spot
- [ ] LLM explains GTO rationale in natural language
- [ ] Sub-5 second response for cached solutions
- [ ] Handles preflop and postflop queries

---

### Phase 2: Vision Module (Weeks 4-6)

**Goal:** Real-time screen capture and game state extraction

#### Files to Create

```
src/
  pokercoach/
    vision/
      __init__.py
      capture.py         # Screen capture abstraction
      detector.py        # Card/chip/button detection
      ocr.py             # Text extraction (pot, stacks)
      templates/         # Card template images
        cards/
        chips/
      calibration.py     # Site-specific calibration
    sites/
      __init__.py
      base.py            # Base site adapter
      pokerstars.py      # PokerStars-specific detection
      ggpoker.py         # GGPoker-specific detection
```

#### Implementation Steps

1. **Screen capture system** (`capture.py`)
   ```python
   class ScreenCapture:
       def capture_window(self, window_title: str) -> np.ndarray: ...
       def capture_region(self, bbox: Tuple[int,int,int,int]) -> np.ndarray: ...
       def monitor_changes(self, callback: Callable) -> None: ...
   ```

2. **Card detection pipeline** (`detector.py`)
   - Template matching for card recognition
   - Contour detection for card boundaries
   - VLM fallback (Moondream-2B) for ambiguous cases
   - Support for different card designs per site

3. **OCR for numeric values** (`ocr.py`)
   - Pot size extraction
   - Stack size extraction
   - Bet sizing detection
   - Preprocessing: grayscale, threshold, denoise

4. **Site-specific adapters** (`sites/`)
   - Define regions of interest per site
   - Handle different UI layouts
   - Calibration tool for new sites

#### Acceptance Criteria
- [ ] Detects hole cards with >99% accuracy
- [ ] Extracts pot/stack sizes within 5% error
- [ ] Recognizes community cards on flop/turn/river
- [ ] Works with PokerStars and one other major site
- [ ] <500ms end-to-end latency

---

### Phase 3: Post-Game Analysis (Weeks 7-9)

**Goal:** Chess.com-style hand review with blunder detection

#### Files to Create

```
src/
  pokercoach/
    analysis/
      __init__.py
      parser.py          # Hand history parsing
      evaluator.py       # GTO comparison engine
      metrics.py         # EV loss, accuracy metrics
      patterns.py        # Leak detection
      reporter.py        # Generate analysis reports
    storage/
      __init__.py
      database.py        # Hand history database
      models.py          # SQLAlchemy/Pydantic models
```

#### Implementation Steps

1. **Hand history parsing** (`parser.py`)
   - Support PokerStars HH format
   - Support Poker Hand History (PHH) format
   - Convert to internal `GameState` representation
   - Batch import capability

2. **GTO evaluation engine** (`evaluator.py`)
   ```python
   class HandEvaluator:
       def evaluate_action(self, state: GameState, action: Action) -> Evaluation:
           """Returns EV comparison vs GTO"""

       def classify_decision(self, ev_loss: float) -> DecisionQuality:
           """Blunder / Mistake / Inaccuracy / Good / Excellent"""

       def find_optimal_action(self, state: GameState) -> Action: ...
   ```

3. **Leak pattern detection** (`patterns.py`)
   - Aggregate stats across sessions
   - Identify systematic deviations
   - Categories: positional leaks, bet sizing leaks, showdown leaks
   - Trend analysis over time

4. **Report generation** (`reporter.py`)
   - Per-hand breakdown with annotations
   - Session summary statistics
   - Visual EV graph (like chess accuracy chart)
   - Exportable HTML/PDF reports

#### Acceptance Criteria
- [ ] Parses standard PokerStars hand histories
- [ ] Classifies each decision on 5-point scale
- [ ] Identifies top 3 leaks per session
- [ ] Generates visual accuracy chart
- [ ] Handles 1000+ hands per session

---

### Phase 4: Exploitative Play Engine (Weeks 10-14)

**Goal:** Opponent profiling and deviation recommendations

#### Files to Create

```
src/
  pokercoach/
    opponent/
      __init__.py
      stats.py           # HUD-style statistics
      profiler.py        # Opponent modeling
      exploiter.py       # Exploitation engine
      memory.py          # Player history storage
    exploit/
      __init__.py
      adjustments.py     # GTO deviation logic
      rl_engine.py       # Optional: RL-based exploitation
```

#### Implementation Steps

1. **Statistical profiling** (`stats.py`)
   ```python
   @dataclass
   class PlayerStats:
       hands_played: int
       vpip: float           # Voluntarily put in pot %
       pfr: float            # Preflop raise %
       three_bet: float      # 3-bet %
       fold_to_3bet: float
       cbet_flop: float      # C-bet frequency
       fold_to_cbet: float
       wtsd: float           # Went to showdown %
       wsd: float            # Won at showdown %
       aggression_factor: float
   ```

2. **Opponent profiler** (`profiler.py`)
   - Calculate stats from hand history
   - Classify player type (TAG, LAG, Nit, Fish, etc.)
   - Confidence intervals based on sample size
   - Live update during session

3. **Exploitation engine** (`exploiter.py`)
   ```python
   class ExploitationEngine:
       def get_adjustment(self,
                          gto_strategy: Strategy,
                          opponent_profile: PlayerProfile) -> AdjustedStrategy:
           """Return modified strategy based on opponent tendencies"""

       def should_deviate(self,
                          gto_ev: float,
                          exploit_ev: float,
                          sample_size: int) -> bool:
           """Determine if exploitation is profitable given uncertainty"""
   ```

4. **Adjustment recommendations** (`adjustments.py`)
   - vs Nit: Steal more, fold to raises
   - vs Fish: Value bet thinner, bluff less
   - vs LAG: Trap more, 4-bet light
   - Dynamic adjustment based on tendencies

#### Advanced (Optional): RL Engine (`rl_engine.py`)
   - Train exploitation policy using PokerRL framework
   - Style embeddings from opponent history
   - Actor-Critic for adaptive play

#### Acceptance Criteria
- [ ] Calculates standard HUD stats accurately
- [ ] Classifies opponents into player types
- [ ] Provides specific exploitation recommendations
- [ ] Tracks opponent history across sessions
- [ ] Shows confidence level for recommendations

---

### Phase 5: User Interface (Weeks 15-18)

**Goal:** Web-based dashboard for all features

#### Files to Create

```
src/
  pokercoach/
    web/
      __init__.py
      app.py             # FastAPI application
      routes/
        coach.py         # Live coaching endpoints
        analysis.py      # Hand review endpoints
        opponents.py     # Player database endpoints
      websocket.py       # Real-time updates
frontend/
  src/
    components/
      HandReplayer.tsx   # Interactive hand replay
      RangeChart.tsx     # Range visualization
      EVGraph.tsx        # EV over time chart
      HUD.tsx            # Live stats overlay
    pages/
      Coach.tsx          # Live coaching view
      Analysis.tsx       # Post-game review
      Opponents.tsx      # Player database
```

#### Implementation Steps

1. **Backend API** (`app.py`, `routes/`)
   - FastAPI with WebSocket support
   - REST endpoints for analysis
   - WebSocket for live coaching updates

2. **Frontend components**
   - Hand replayer with action annotations
   - Interactive range charts
   - EV/accuracy graphs
   - Responsive design for desktop/tablet

3. **Live overlay option**
   - Electron wrapper for desktop
   - Transparent overlay capability
   - Hotkey activation

#### Acceptance Criteria
- [ ] Web dashboard with all core features
- [ ] Real-time updates via WebSocket
- [ ] Interactive hand replay
- [ ] Works on desktop and tablet
- [ ] <100ms UI response time

---

## Testing Strategy

### Unit Tests
- Game state model validation
- Solver output parsing
- Hand history parsing accuracy
- Equity calculations vs known values

### Integration Tests
- Solver bridge end-to-end
- Vision pipeline with sample screenshots
- Full hand analysis workflow

### Performance Tests
- Solver query latency benchmarks
- Vision module frame rate
- Batch analysis throughput

### Accuracy Tests
- Card recognition on diverse samples
- OCR accuracy across stake levels
- GTO comparison vs PioSolver reference

---

## Tech Stack Summary

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.11+ | Ecosystem, ML libraries |
| LLM | Claude 3.5/GPT-4 | Tool use, reasoning |
| Solver | TexasSolver | Open-source, fast |
| Vision | OpenCV + mss | Proven, cross-platform |
| OCR | EasyOCR | Better than Tesseract for screens |
| VLM (fallback) | Moondream-2B | Fast, local inference |
| Database | SQLite/PostgreSQL | Hand history storage |
| Backend | FastAPI | Async, WebSocket support |
| Frontend | React + TypeScript | Modern, type-safe |
| Desktop | Electron | Overlay capability |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Solver performance on complex spots | High latency | Pre-compute common spots, progressive solving |
| Site TOS violations | Legal/account risk | User acknowledgment, no automation |
| Vision accuracy across sites | Unusable feature | Calibration system, user corrections |
| Opponent sample size | Unreliable exploits | Confidence intervals, GTO fallback |
| TexasSolver licensing | Commercial limitation | Abstract solver interface, support alternatives |

---

## Estimated Complexity

| Phase | Complexity | Person-Weeks |
|-------|------------|--------------|
| Phase 1: Solver Integration | Medium | 3 |
| Phase 2: Vision Module | High | 4 |
| Phase 3: Post-Game Analysis | Medium | 3 |
| Phase 4: Exploitative Engine | High | 4 |
| Phase 5: User Interface | Medium | 4 |
| **Total** | | **18 weeks** |

---

## MVP Definition

For a functional MVP, prioritize:

1. **Must Have (Phase 1 + 3)**
   - LLM coach with solver access
   - Hand history import and analysis
   - Basic blunder detection

2. **Should Have (Phase 2)**
   - Screen capture for one poker site
   - Live game state extraction

3. **Nice to Have (Phase 4 + 5)**
   - Opponent profiling
   - Web dashboard
   - Real-time overlay

---

## Next Steps

1. Initialize repository with project structure
2. Set up development environment (uv, pre-commit)
3. Build TexasSolver from source
4. Implement core data models
5. Create first LLM tool: `query_gto`

---

## References

### GTO Solvers
- [TexasSolver](https://github.com/bupticybee/TexasSolver)
- [sol5000/gto](https://github.com/sol5000/gto)
- [PioSOLVER](https://piosolver.com/)
- [GTO Wizard](https://gtowizard.com/)

### Vision & OCR
- [ace-autopilot-poker-ai](https://github.com/newMeta98/ace-autopilot-poker-ai)
- [poker-vision](https://github.com/MemDbg/poker-vision)
- [PyPokerBot](https://github.com/gbencke/PyPokerBot)
- [OpenCV-Playing-Card-Detector](https://github.com/EdjeElectronics/OpenCV-Playing-Card-Detector)

### Hand History Parsing
- [poker-log-parser](https://pypi.org/project/poker-log-parser/)
- [poker (Python)](https://poker.readthedocs.io/)
- [PHH Format Specification](https://arxiv.org/html/2312.11753v2)

### Opponent Modeling
- [PokerRL Framework](https://github.com/EricSteinberger/PokerRL)
- [AMP3: Adaptive Poker Policy](https://link.springer.com/article/10.1007/s00521-025-11262-x)
- [LLM-Guided Strategy](https://cs224r.stanford.edu/projects/pdfs/cs224rFinalProject.pdf)
- [GTO Wizard Player Profiles](https://blog.gtowizard.com/profiles_explained_modeling_exploitable_opponents/)
