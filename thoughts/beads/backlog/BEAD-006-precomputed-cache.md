---
id: BEAD-006
title: Implement precomputed solution cache
phase: 1
priority: P2
estimated_effort: M
dependencies: [BEAD-003, BEAD-005]
files:
  - src/pokercoach/solver/texas_solver.py
  - src/pokercoach/solver/cache.py
  - tests/unit/test_solver_cache.py
---

## Context

Solving from scratch takes 5-60 seconds per spot. For common spots (standard open sizes, common board textures), we should cache solutions for instant lookup.

The `PrecomputedSolver` class exists but `_cache_key()` is not implemented.

## Acceptance Criteria

- [ ] `_cache_key(game_state)` generates canonical, collision-free key
- [ ] Cache uses disk storage (JSON files or SQLite)
- [ ] Cache respects position isomorphism (BTN vs CO doesn't matter in HU)
- [ ] Cache respects suit isomorphism (AsKs == AhKh on rainbow board)
- [ ] `save_solution()` and `load_solution()` implemented
- [ ] Cache directory configurable via config
- [ ] `pytest tests/unit/test_solver_cache.py` passes

## Implementation Notes

Cache key should normalize:
1. Effective stacks (100bb, not exact amounts)
2. Pot as % of effective stack
3. Board suits to canonical form
4. Position to relative (IP/OOP)

Example key: `100bb_SRP_IP_Ah8c3d_cbet50`
