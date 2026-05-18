---
phase: 05-cli-packaging-linguist
plan: 05-06
subsystem: cli
tags: [cli, packaging, integration, smoke-tests]

requires:
  - phase: 05-cli-packaging-linguist/05-05
    provides: Linguist tooling assets and samples
provides:
  - editable-install/package-data smoke coverage
  - full CLI integration smoke (init, ast, check, compile, run)
  - Phase 5 closure verification

key-files:
  created:
    - tests/cli/test_integration.py
  verified:
    - tests/packaging/test_entrypoint.py

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

completed: 2026-05-18
---

# Phase 05 Plan 06: Packaging + Integration Closure Summary

Phase 5 closed: editable install exposes `voss` console script, package data ships grammar plus init templates, and full CLI smoke covers all five subcommands without leaving repo-local artifacts.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 05-06-0 | PASSED | Confirmed `phase5-cli-contract-ok` marker. |
| 05-06-1 | PASSED | Verified `tests/packaging/test_entrypoint.py` coverage — package-data resource check, parametrized console-script subcommand help, slow venv editable-install verification. |
| 05-06-2 | PASSED | Added `tests/cli/test_integration.py` — init→ast→check smoke, hermetic compile→run, samples ast+check loop, no repo-local cache/generated. |
| 05-06-3 | PASSED | Verified existing CLI surface; no new defects required Phase 5-surface fixes. |
| 05-06-4 | PASSED | Ran full Phase 5 verification commands per `05-VALIDATION.md`. |

## Verification

- `pytest tests/packaging/test_entrypoint.py -q` → 10 passed.
- `pytest tests/cli/test_integration.py -q` → 4 passed.
- `pytest tests/packaging/test_entrypoint.py tests/cli/test_integration.py -q` → 14 passed.
- `pytest tests/cli tests/tooling -q` → 47 passed.
- `pytest tests/parser tests/analyzer tests/codegen tests/cli tests/tooling -q` → 256 passed.
- Isolated venv editable install succeeded: `python3 -m venv --system-site-packages "$tmp/venv" && "$tmp/venv/bin/python" -m pip install -q --no-deps -e . && "$tmp/venv/bin/voss" --help`.
- `phase5-no-repo-local-cache-ok` printed.
- `git diff --check -- tests/packaging/test_entrypoint.py tests/cli/test_integration.py voss/cli.py pyproject.toml` clean.

## Decisions

- Slow venv install test uses `--system-site-packages` plus `pip install --no-deps -e <repo>` to avoid reinstalling heavy runtime dependencies (chromadb, sentence-transformers, pydantic) while still verifying the console-script entry-point shim.
- Console-script subcommand help test prefers `shutil.which("voss")` and falls back to `python3 -m voss.cli` when the binary is not on PATH.
- Integration smoke uses the packaged `voss init` `hello.voss` scaffold as the hermetic compile/run fixture; samples are exercised through ast+check only (no provider runtime).

## Deviations

- `tests/packaging/test_entrypoint.py` already contained the required 05-06 packaging coverage, so this execution verified it rather than changing it.
- The active environment was not mutated with `python3 -m pip install -e .`; an isolated temporary venv performed the editable install smoke instead.

## Self-Check

PASSED. Full Phase 5 validation commands pass; editable install exposes `voss --help`; no repository-local `.voss-cache` artifacts remain after the smoke suite.
