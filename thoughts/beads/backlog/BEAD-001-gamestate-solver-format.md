---
id: BEAD-001
title: Implement GameState.to_solver_format()
phase: 1
priority: P0
estimated_effort: S
dependencies: []
files:
  - src/pokercoach/core/game_state.py
  - tests/unit/test_game_state.py
---

## Context

The `GameState.to_solver_format()` method currently raises `NotImplementedError`. This method is critical for converting our internal game state representation to the format expected by TexasSolver.

TexasSolver expects input in a specific format for:
- Board cards
- Pot size
- Stack depths
- Betting actions

## Acceptance Criteria

- [ ] `to_solver_format()` returns string matching TexasSolver input spec
- [ ] Handles preflop, flop, turn, river states
- [ ] Correctly encodes bet sizes relative to pot/BB
- [ ] Unit tests cover all streets and action types
- [ ] `pytest tests/unit/test_game_state.py` passes

## Implementation Notes

Reference TexasSolver input format:
- https://github.com/bupticybee/TexasSolver#input-format

Example format (approximate):
```
BOARD:Ah Kd 5c
POT:100
STACKS:500 500
ACTIONS:BTN r3x, SB call, BB fold
```
