# Bead Index

## Phase 1: Foundation & Solver Integration

| ID | Title | Priority | Effort | Dependencies | Status |
|----|-------|----------|--------|--------------|--------|
| BEAD-001 | GameState.to_solver_format() | P0 | S | - | backlog |
| BEAD-002 | Acquire TexasSolver binary | P0 | M | - | backlog |
| BEAD-003 | Solution/Strategy data types | P0 | S | - | backlog |
| BEAD-004 | TexasSolver _build_command() | P1 | M | 001, 002 | backlog |
| BEAD-005 | TexasSolver _parse_output() | P1 | M | 003, 004 | backlog |
| BEAD-006 | Precomputed solution cache | P2 | M | 003, 005 | backlog |
| BEAD-007 | LLM query_gto tool | P1 | M | 003, 005 | backlog |
| BEAD-008 | LLM explain_line tool | P2 | S | 007 | backlog |
| BEAD-009 | LLM compare_actions tool | P2 | S | 007 | backlog |
| BEAD-010 | Coach integration E2E | P1 | L | 005, 007-009 | backlog |

## Dependency Graph

```
BEAD-001 (GameState format) ──┐
                              ├──> BEAD-004 (build_command) ──┐
BEAD-002 (Binary) ────────────┘                               │
                                                              ├──> BEAD-005 (parse_output) ──┐
BEAD-003 (Solution types) ────────────────────────────────────┘                              │
                                                                                             │
                    ┌────────────────────────────────────────────────────────────────────────┘
                    │
                    ├──> BEAD-006 (Cache)
                    │
                    └──> BEAD-007 (query_gto) ──┬──> BEAD-008 (explain_line) ──┐
                                                │                               │
                                                └──> BEAD-009 (compare_actions) ┼──> BEAD-010 (E2E)
```

## Execution Order (Critical Path)

1. **Parallel**: BEAD-001, BEAD-002, BEAD-003 (no deps)
2. **Sequential**: BEAD-004 → BEAD-005
3. **Parallel**: BEAD-006, BEAD-007
4. **Parallel**: BEAD-008, BEAD-009
5. **Final**: BEAD-010

## Estimated Total: ~3 weeks (single developer)
