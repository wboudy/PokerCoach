---
id: BEAD-002
title: Acquire/build TexasSolver binary
phase: 1
priority: P0
estimated_effort: M
dependencies: []
files:
  - scripts/build_solver.sh
  - .gitignore
---

## Context

TexasSolver is an open-source C++ poker solver that's 29% faster than PioSolver. We need the compiled binary to run GTO calculations.

Options:
1. Build from source (recommended for customization)
2. Download pre-built release
3. Use Docker container

## Acceptance Criteria

- [ ] TexasSolver binary exists at `bin/texas_solver` or configurable path
- [ ] Binary is executable and responds to `--help`
- [ ] Build script created at `scripts/build_solver.sh`
- [ ] Binary path added to `.gitignore` (don't commit binary)
- [ ] README updated with solver installation instructions

## Implementation Notes

Build from source:
```bash
git clone https://github.com/bupticybee/TexasSolver.git
cd TexasSolver
mkdir build && cd build
cmake ..
make -j$(nproc)
```

Requirements:
- CMake 3.15+
- C++17 compiler (clang/gcc)
- OpenMP (optional, for parallelism)
