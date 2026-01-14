---
id: BEAD-004
title: Implement TexasSolver _build_command()
phase: 1
priority: P1
estimated_effort: M
dependencies: [BEAD-001, BEAD-002]
files:
  - src/pokercoach/solver/texas_solver.py
  - tests/unit/test_texas_solver.py
---

## Context

`TexasSolverBridge._build_command()` currently raises `NotImplementedError`. This method must convert a `GameState` into CLI arguments for the TexasSolver binary.

## Acceptance Criteria

- [ ] `_build_command(game_state)` returns valid CLI arg list
- [ ] Handles preflop and postflop states
- [ ] Correctly maps positions to solver format
- [ ] Includes iteration count, accuracy settings
- [ ] Unit tests mock subprocess, verify command format
- [ ] `pytest tests/unit/test_texas_solver.py` passes

## Implementation Notes

TexasSolver CLI format (verify from source):
```bash
./texas_solver \
  --board "Ah Kd 5c" \
  --pot 100 \
  --stack 500 \
  --iterations 1000 \
  --accuracy 0.3 \
  --output json
```

Need to study actual CLI args from:
https://github.com/bupticybee/TexasSolver/blob/main/README.md
