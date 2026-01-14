---
id: BEAD-005
title: Implement TexasSolver _parse_output()
phase: 1
priority: P1
estimated_effort: M
dependencies: [BEAD-003, BEAD-004]
files:
  - src/pokercoach/solver/texas_solver.py
  - tests/unit/test_texas_solver.py
  - tests/fixtures/solver_output_sample.json
---

## Context

`TexasSolverBridge._parse_output()` must parse solver JSON output into our `Solution` type. This is the inverse of `_build_command()`.

## Acceptance Criteria

- [ ] Parses JSON output from TexasSolver
- [ ] Creates `Solution` with strategies for all hands in range
- [ ] Extracts exploitability metric
- [ ] Handles edge cases (no solution, timeout)
- [ ] Test fixture with real solver output sample
- [ ] `pytest tests/unit/test_texas_solver.py` passes

## Implementation Notes

Expected output structure (approximate):
```json
{
  "exploitability": 0.25,
  "iterations": 1000,
  "strategies": {
    "AhAs": {"fold": 0.0, "call": 0.3, "raise": 0.7},
    "KhKs": {"fold": 0.0, "call": 0.5, "raise": 0.5},
    ...
  },
  "evs": {
    "AhAs": {"fold": 0, "call": 15.2, "raise": 18.5},
    ...
  }
}
```

Need actual output sample from running solver.
