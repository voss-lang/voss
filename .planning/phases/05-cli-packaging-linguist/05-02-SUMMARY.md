---
phase: 05-cli-packaging-linguist
plan: 05-02
subsystem: cli
tags: [cli, ast, check, diagnostics, read-only]

requires:
  - phase: 05-cli-packaging-linguist/05-01
    provides: Click shell + phase5-cli-contract-ok marker
provides:
  - voss ast read-only AST JSON output
  - voss check analyzer diagnostics with warning/error exit policy

key-files:
  created:
    - tests/cli/test_ast.py
    - tests/cli/test_check.py
  modified:
    - voss/cli.py

requirements-completed:
  - CLI-03
  - CLI-05

completed: 2026-05-08
---

# Phase 05 Plan 02: Read-only Commands Summary

`voss ast` and `voss check` implemented as thin wrappers over public parser/analyzer APIs. Neither writes caches, runs codegen, executes user code, or calls providers.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 05-02-0 | PASSED | Confirmed `phase5-cli-contract-ok` marker. |
| 05-02-1 | PASSED | `tests/cli/test_ast.py` covers normalized JSON, compact mode, read-only. |
| 05-02-2 | PASSED | `tests/cli/test_check.py` covers warning exit 0, --warnings-as-errors nonzero, errors nonzero, no cache writes, emit_indexes=False. |
| 05-02-3 | PASSED | Implemented `ast` and `check` commands plus shared helpers in `voss/cli.py`. |

## Verification

- `pytest tests/cli/test_ast.py tests/cli/test_check.py -q` → 9 passed.
- `read-only-cli-no-exec-ok` printed.
- `no-repo-local-check-indexes` printed.
- `git diff --check` clean.

## Decisions

- Module-level imports of `analyze`/`parse`/`to_dict` for monkeypatch seam.
- Diagnostic display uses `str(diag)`; analyzer-owned format.
- Errors raise `click.exceptions.Exit(code=1)`; warnings exit 0 unless `--warnings-as-errors`.

## Self-Check

PASSED. Read-only commands obey emit_indexes=False, leave no `.voss-cache` artifacts, and use stable diagnostic location format.
