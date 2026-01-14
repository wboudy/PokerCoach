---
id: BEAD-008
title: Create LLM explain_line tool
phase: 1
priority: P2
estimated_effort: S
dependencies: [BEAD-007]
files:
  - src/pokercoach/llm/tools.py
  - tests/unit/test_llm_tools.py
---

## Context

After getting GTO strategy, users need explanations of *why* certain plays are optimal. This tool provides reasoning about poker lines.

## Acceptance Criteria

- [ ] `explain_line` tool takes a hand, board, and action sequence
- [ ] Returns structured explanation with:
  - Range analysis (what hands take this line)
  - Board texture assessment
  - Equity vs opponent range
  - Why this action is +EV
- [ ] Works with partial information (no solver needed for explanation)
- [ ] `pytest tests/unit/test_llm_tools.py` passes

## Implementation Notes

This tool is more heuristic than `query_gto`. It can use:
1. Solver output for concrete numbers
2. LLM reasoning for qualitative explanation
3. Pre-written explanations for common spots

Output format:
```json
{
  "board_texture": "Dry K-high rainbow, favors preflop raiser",
  "hand_strength": "Top pair top kicker, ahead of villain's continuing range",
  "action_reasoning": "Betting for value against Kx, QQ-TT, and draws",
  "key_considerations": ["Board pairs on turn hurt us", "Can value 3 streets"]
}
```
