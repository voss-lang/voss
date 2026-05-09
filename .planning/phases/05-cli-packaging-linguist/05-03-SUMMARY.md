---
phase: 05-cli-packaging-linguist
plan: 05-03
subsystem: cli
tags: [cli, compile, run, subprocess, codegen]

requires:
  - phase: 05-cli-packaging-linguist/05-02
    provides: read-only ast/check commands and shared CLI helpers
provides:
  - voss compile parse->analyze->codegen pipeline with atomic write
  - voss run subprocess execution via [sys.executable, generated_path]

key-files:
  created:
    - tests/cli/test_compile.py
    - tests/cli/test_run.py
  modified:
    - voss/cli.py

requirements-completed:
  - CLI-01
  - CLI-02

completed: 2026-05-08
---

# Phase 05 Plan 03: Compile + Run Commands Summary

`voss compile` writes parseable Python after analyzer ok; `voss run` compiles to a temp dir and executes through the current Python interpreter via `subprocess.run`.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 05-03-0 | PASSED | Confirmed `phase5-cli-contract-ok` marker. |
| 05-03-1 | PASSED | `tests/cli/test_compile.py` — 6 tests (default `.py`, --output, warnings still write, errors block, emit_indexes=True, generate_python receives analysis). |
| 05-03-2 | PASSED | `tests/cli/test_run.py` — 4 tests ([sys.executable, path], stdout forward, exit-code propagation, no exec/eval). |
| 05-03-3 | PASSED | Implemented `_compile_source`, `_write_text_atomic`, `compile`, `run` in `voss/cli.py`. |

## Verification

- `pytest tests/cli/test_compile.py tests/cli/test_run.py -q` → 10 passed.
- `cli-run-no-inprocess-exec-ok` printed.
- `no-repo-local-cli-indexes` printed.
- `git diff --check` clean.

## Decisions

- Atomic write via `tempfile.mkstemp` + `os.replace` in same directory.
- `run` compiles into `TemporaryDirectory()` so no artifacts persist; subprocess returncode propagated via `click.exceptions.Exit`.
- `project_root` only forwarded to `generate_python` when explicitly provided.
- No `exec`, `eval`, `runpy`, or in-process generated-code execution.

## Self-Check

PASSED. Pipeline blocks on analyzer errors before write, atomic output beside source by default, subprocess execution forwards stdout/stderr/exit code.
