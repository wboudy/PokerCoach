---
id: BEAD-009
title: Create LLM compare_actions tool
phase: 1
priority: P2
estimated_effort: S
dependencies: [BEAD-007]
files:
  - src/pokercoach/llm/tools.py
  - tests/unit/test_llm_tools.py
---

## Context

Users often want to compare two plays: "Should I bet or check here?" This tool shows EV difference between actions.

## Acceptance Criteria

- [ ] `compare_actions` takes hand, board, and list of actions to compare
- [ ] Returns EV for each action and EV difference
- [ ] Highlights which is optimal and by how much
- [ ] Explains when mixing is correct (close EV spots)
- [ ] `pytest tests/unit/test_llm_tools.py` passes

## Implementation Notes

Tool output:
```json
{
  "comparison": [
    {"action": "check", "ev": 12.5, "frequency": 0.3},
    {"action": "bet 33%", "ev": 14.2, "frequency": 0.5},
    {"action": "bet 75%", "ev": 13.8, "frequency": 0.2}
  ],
  "optimal": "bet 33%",
  "ev_loss_from_check": 1.7,
  "is_close": false,
  "recommendation": "Pure bet 33% pot is clearly highest EV here"
}
```
