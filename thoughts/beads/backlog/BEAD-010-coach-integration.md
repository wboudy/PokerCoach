---
id: BEAD-010
title: Integrate PokerCoach with solver and test E2E
phase: 1
priority: P1
estimated_effort: L
dependencies: [BEAD-005, BEAD-007, BEAD-008, BEAD-009]
files:
  - src/pokercoach/llm/coach.py
  - src/pokercoach/llm/prompts.py
  - tests/integration/test_coach_e2e.py
---

## Context

This is the capstone bead for Phase 1. Wire everything together:
- LLM (Claude) with poker tools
- Solver bridge for GTO queries
- Conversational interface

## Acceptance Criteria

- [ ] `PokerCoach` class initializes with solver and LLM client
- [ ] `coach.ask(question)` handles natural language poker questions
- [ ] LLM correctly invokes tools when needed
- [ ] System prompt establishes poker coaching persona
- [ ] E2E test: Ask "What should I do with AK on Kh8c3d when villain bets?"
- [ ] Response includes GTO strategy and explanation
- [ ] `pytest tests/integration/test_coach_e2e.py` passes

## Implementation Notes

```python
class PokerCoach:
    def __init__(self, solver: SolverBridge, llm_client: Anthropic):
        self.solver = solver
        self.client = llm_client
        self.tools = [query_gto, explain_line, compare_actions]

    def ask(self, question: str, context: GameState | None = None) -> str:
        """Ask the coach a poker question."""
        messages = [{"role": "user", "content": question}]
        # Tool use loop...
```

System prompt should:
- Establish GTO-based coaching style
- Explain it can query solver for exact numbers
- Be conversational but precise
