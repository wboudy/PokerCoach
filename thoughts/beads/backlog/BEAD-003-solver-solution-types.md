---
id: BEAD-003
title: Define Solution and Strategy data types
phase: 1
priority: P0
estimated_effort: S
dependencies: []
files:
  - src/pokercoach/solver/bridge.py
  - tests/unit/test_solver_types.py
---

## Context

The solver bridge needs proper data types for representing solver output:
- `Solution`: Complete solution for a game tree node
- `Strategy`: Action frequencies for a specific hand
- `ActionEV`: Expected value for each action

Currently `bridge.py` has placeholder imports but no concrete implementations.

## Acceptance Criteria

- [ ] `Solution` dataclass with strategies per hand, metadata
- [ ] `Strategy` dataclass with action frequencies (fold%, check%, bet sizes)
- [ ] `ActionEV` dataclass with EV per action
- [ ] Methods: `Solution.get_strategy(hand)`, `Strategy.optimal_action()`
- [ ] Unit tests for data type construction and methods
- [ ] `pytest tests/unit/test_solver_types.py` passes

## Implementation Notes

```python
@dataclass
class Strategy:
    hand: Hand
    action_frequencies: dict[ActionType, float]  # sum to 1.0
    action_evs: dict[ActionType, float]  # in BB

    def optimal_action(self) -> ActionType:
        """Return highest EV action."""

@dataclass
class Solution:
    game_state: GameState
    strategies: dict[str, Strategy]  # hand_str -> Strategy
    exploitability: float  # Nash distance
    iterations: int

    def get_strategy(self, hand: Hand) -> Strategy | None:
        ...
```
