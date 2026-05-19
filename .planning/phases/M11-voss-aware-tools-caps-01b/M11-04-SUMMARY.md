# M11-04 Voss to Python Diff Summary

**Completed:** 2026-05-18T21:35:43Z
**Plan:** `M11-04-voss-python-diff-PLAN.md`
**Wave:** 4

## Outcome

Added the on-demand `.voss` to Python diff viewer:

- Added `voss/harness/voss_diff.py` with `resolve_generated_python()` and `render_voss_py_diff()`.
- Uses cached harness artifacts for dogfood files under `voss/harness/agent/` when `.voss-cache/harness/<stem>.py` exists.
- Falls back to in-memory parse/analyze/codegen for arbitrary `.voss` files without writing durable generated output.
- Added read-only tool `voss_py_diff`.
- Added CLI command `voss vdiff <file.voss> --cwd .`.
- Added slash command `/vdiff <file.voss>`.
- Added focused tests for temp-file rendering, dogfood `planner.voss`, wrong suffix errors, read-only tool classification, slash registration, and avoiding source-map claims.

The rendered view is source-vs-generated only. It does not claim source-map or line-mapped precision.

## Files Changed

- `voss/harness/voss_diff.py`
- `voss/harness/tools.py`
- `voss/harness/cli.py`
- `tests/harness/test_voss_diff.py`
- `tests/harness/test_tools.py`
- `tests/harness/test_repl_slash.py`
- `.planning/phases/M11-voss-aware-tools-caps-01b/M11-04-SUMMARY.md`

## Verification

- `python3 -m pytest -q tests/harness/test_voss_diff.py tests/harness/test_tools.py tests/harness/test_repl_slash.py` passed with 48 tests.
- `python3 -m voss.cli vdiff voss/harness/agent/planner.voss` passed and rendered `Voss source` plus `Generated Python` sections.
- `python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py` passed with 3 tests.
- `python3 -m py_compile voss/harness/voss_diff.py voss/harness/cli.py voss/harness/tools.py` passed.
- `git diff --check` passed.
- `git diff -- voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py` was empty.

## Deviations

- Generic Codex worker subagents were used because local GSD agents are not installed for this repo.
- The main implementation landed in worker commit `5eb3e14`. A follow-up contract fix changed `resolve_generated_python()` to return `(origin_label, python_source)` as the plan specified.

## Self-Check: PASSED
