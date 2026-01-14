---
id: BEAD-007
title: Create LLM query_gto tool
phase: 1
priority: P1
estimated_effort: M
dependencies: [BEAD-003, BEAD-005]
files:
  - src/pokercoach/llm/tools.py
  - src/pokercoach/llm/coach.py
  - tests/unit/test_llm_tools.py
---

## Context

The LLM coach needs a tool to query GTO strategy from the solver. This is the primary interface between the language model and the solver engine.

## Acceptance Criteria

- [ ] `query_gto` tool defined with proper schema (hand, board, pot, stacks, actions)
- [ ] Tool returns strategy frequencies and EVs for given hand
- [ ] Handles natural language input ("I have AK on a K-high board")
- [ ] Integrates with Claude tool_use or function calling
- [ ] Error handling for invalid inputs
- [ ] Unit tests with mocked solver
- [ ] `pytest tests/unit/test_llm_tools.py` passes

## Implementation Notes

Tool schema:
```python
{
    "name": "query_gto",
    "description": "Query optimal GTO strategy for a poker hand",
    "input_schema": {
        "type": "object",
        "properties": {
            "hand": {"type": "string", "description": "Hero's hole cards, e.g. 'AhKs'"},
            "board": {"type": "string", "description": "Community cards, e.g. 'Kd 8c 3h'"},
            "pot": {"type": "number", "description": "Current pot in BB"},
            "effective_stack": {"type": "number", "description": "Effective stack in BB"},
            "position": {"type": "string", "enum": ["IP", "OOP"]},
            "action_history": {"type": "string", "description": "Prior actions"}
        },
        "required": ["hand", "board", "pot", "effective_stack", "position"]
    }
}
```
