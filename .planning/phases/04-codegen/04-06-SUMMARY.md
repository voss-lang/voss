---
phase: 04-codegen
plan: 04-06
subsystem: codegen
tags: [python, codegen, examples, snapshots, hermetic-tests]

requires:
  - phase: 04-codegen/04-05
    provides: agent, tool, prompt, class, spawn, and gather lowering
provides:
  - PRD §7 classify/support/research generated-source execution coverage
  - Generated example snapshot/readability coverage
  - Phase 4 codegen closure verification

key-files:
  created:
    - tests/codegen/helpers.py
    - tests/codegen/test_examples.py
    - tests/codegen/test_snapshots.py
    - tests/codegen/snapshots/classify.py
    - tests/codegen/snapshots/support.py
    - tests/codegen/snapshots/research.py
  modified:
    - voss/codegen.py

requirements-completed:
  - GEN-01
  - GEN-02
  - GEN-03
  - GEN-04
  - GEN-05

completed: 2026-05-08
---

# Phase 04 Plan 06: Example Codegen Closure Summary

Phase 4 now has end-to-end generated-example verification for the three PRD §7 parser fixtures. The generated classify, support, and research modules parse, execute under hermetic stubs/fake semantic data, and are snapshot-tested for readability.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 04-06-1 | PASSED | Added example compile/run tests and test-local helpers for generated-module loading, allowed-import checks, fake analysis, and fake semantic routing. |
| 04-06-2 | PASSED | Added snapshot/readability tests plus classify/support/research snapshots. |
| 04-06-3 | PASSED | Applied codegen-only fixes for Voss `.map(...)`, list `.join(...)`, and indexed awaited `gather(...)` lowering. |

## Commits

| Commit | Description |
|---|---|
| `af82fd7` | Adds example tests/helpers and codegen member-call fixes. |
| `f26eddf` | Fixes runtime-import timing in async example tests. |
| `90d4707` | Adds pre-exec generated-module globals plus snapshot tests and snapshots. |
| pending | Adds this execution summary. |

## Decisions

- Runtime-importing tests were verified with `arch -arm64 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m pytest` because the default launcher uses x86_64 Python against arm64 compiled wheels in this environment.
- Research example tests inject `webSearch` before generated module execution, matching the plan's external-tool boundary without editing raw examples or adding compiler fallbacks.
- Support generated branches use synchronous test shims because the generated source calls external route helpers directly.
- Snapshot compiler-import checks use AST import inspection. The plan's raw substring `assert "from voss" not in text` false-positives on valid `from voss_runtime import ...`, so verification uses the narrower compiler-module check already enforced by `test_snapshots.py`.

## Verification

- `phase4-codegen-contract-ok` preflight passed.
- `arch -arm64 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m pytest tests/codegen -q` -> 49 passed.
- `arch -arm64 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m pytest tests/parser tests/analyzer tests/codegen -q` -> 196 passed.
- Snapshot parse/newline/compiler-import check printed `codegen-snapshots-parse-ok`.
- Repo-local index hygiene check printed `no-repo-local-codegen-indexes`.
- `git diff --check -- voss/codegen.py tests/codegen` passed.

## Deviations

- Plain `pytest tests/codegen/test_examples.py -q` fails in this local environment before collection due the x86_64 Python launcher loading arm64 `pydantic_core`; the same tests pass under the arm64 interpreter used above.
- The literal plan snippet `assert "from voss" not in text` is too broad for the package name `voss_runtime`. The implemented check rejects compiler imports via AST while allowing public runtime imports required by generated Python.

## Self-Check

PASSED. GEN-05 is covered by generated classify/support/research compile-run tests, GEN-01 through GEN-04 remain covered by the full codegen suite, snapshots are parseable/readable, and default verification is hermetic with no repo-local `.voss-cache` indexes.
