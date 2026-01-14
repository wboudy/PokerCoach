# Beads

Atomic work units for Ralph worker execution.

## Structure

```
beads/
├── backlog/       # Ready to execute
├── in-progress/   # Currently being worked on
├── completed/     # Done (archived)
└── blocked/       # Needs resolution
```

## Bead Format

Each bead file: `BEAD-NNN-short-name.md`

```yaml
---
id: BEAD-NNN
title: Short descriptive title
phase: 1
priority: P0/P1/P2
estimated_effort: S/M/L
dependencies: [BEAD-XXX, ...]
files:
  - path/to/file.py
---

## Context
What this bead accomplishes and why.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass

## Implementation Notes
Any specific guidance for implementation.
```

## Workflow

1. Ralph worker claims bead from `backlog/`
2. Moves to `in-progress/`
3. Implements, runs tests
4. Moves to `completed/` on success
5. Moves to `blocked/` if stuck
