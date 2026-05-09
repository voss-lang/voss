---
phase: 05-cli-packaging-linguist
plan: 05-01
subsystem: cli
tags: [cli, packaging, click, contract-gate]

requires:
  - phase: 04-codegen/04-06
    provides: full parser/analyzer/codegen public API and PRD example coverage
provides:
  - Phase 5 contract gate (`phase5-cli-contract-ok`)
  - voss/cli.py Click root group + compile/run/check/init/ast subcommand shells
  - pyproject.toml [project.scripts] voss = "voss.cli:main"

key-files:
  created:
    - voss/cli.py
    - tests/cli/__init__.py
    - tests/cli/test_help.py
    - tests/packaging/__init__.py
    - tests/packaging/test_entrypoint.py
  modified:
    - pyproject.toml

requirements-completed:
  - CLI-01
  - CLI-02
  - CLI-03
  - CLI-04
  - CLI-05
  - CLI-06
  - TOOL-01
  - TOOL-02
  - TOOL-03

completed: 2026-05-08
---

# Phase 05 Plan 01: CLI Shell + Packaging Entrypoint Summary

Phase 5 foundation: contract gate marker, Click command shell, and console-script entrypoint.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 05-01-0 | PASSED | Read-only contract gate printed `phase5-cli-contract-ok`. |
| 05-01-1 | PASSED | Added `tests/cli/test_help.py` and `tests/packaging/test_entrypoint.py`. |
| 05-01-2 | PASSED | Created `voss/cli.py` with Click root group + `compile`, `run`, `check`, `init`, `ast` shells. |
| 05-01-3 | PASSED | Added `[project.scripts] voss = "voss.cli:main"` to `pyproject.toml`. |

## Marker

`phase5-cli-contract-ok` — recorded for downstream Phase 5 plans (05-02..06) and Phase 6 gate.

## Verification

- `phase5-cli-contract-ok` printed by preflight gate.
- `pytest tests/cli/test_help.py tests/packaging/test_entrypoint.py -q` → 11 passed.
- `python3 -m voss.cli --help` exits 0.
- `voss-entrypoint-metadata-ok` printed.
- `git diff --check -- voss/cli.py pyproject.toml tests/cli tests/packaging` clean.

## Decisions

- Subcommand bodies raise `click.ClickException("not implemented yet")` until later plans replace them; help rendering does not execute bodies.
- No parser/analyzer/codegen imports at module load; deferred to command callbacks.

## Self-Check

PASSED. Click shell discovers all five Phase 5 subcommands, console script metadata is declared, help/entrypoint tests are hermetic.
