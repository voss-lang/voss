---
phase: E2-golden-tasks-repo-matrix
plan: 08
subsystem: testing
tags: [eval, runner, cli, summary, jinja, toolchain, skip]

# Dependency graph
requires:
  - phase: E2-golden-tasks-repo-matrix (plan 01)
    provides: "strict-xfail runner scaffold tests + RED summary tests this plan turns green"
  - phase: E1-eval-runner
    provides: "run_suite/_run_suite_async/_append_row/write_summary the extensions bolt onto"
provides:
  - "run_suite toolchain preflight: {py: python3, rust: cargo, ts: node} shutil.which map echoed as OK/MISSING before any model call"
  - "Skip-row guard: absent-toolchain task records skipped=True/skip_reason=toolchain-absent/gate_pass=None (never False) and continues without fixture or model call"
  - "run_suite(require_all_toolchains=True) raises click.UsageError naming missing binaries pre-provider; voss eval --require-all-toolchains threads it"
  - "summary.md skipped-rate header line + per-task skipped column, conditional on rows carrying the skipped field (legacy byte-identical)"
affects: [E-track proof runs, eval matrix runner, eval summary consumers]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Toolchain skip = lang prefix (task_id.split('-')[0]) → which-map lookup; skip rows carry full row schema incl. input_tokens/surface; summary renders skip info only when the field exists (show_skipped)"]

key-files:
  created: []
  modified:
    - voss/eval/runner.py
    - voss/harness/cli.py
    - voss/eval/summary.py
    - voss/templates/eval/summary.md.jinja
    - tests/eval/test_matrix_runner.py

key-decisions:
  - "Conditional skip rendering instead of the plan's unconditional column insert: test_summary_md.py pins the legacy table header AND exact output bytes for golden rows; show_skipped=any('skipped' in row) satisfies both the matrix tests and the byte-exact legacy gate"
  - "Skip row extended beyond the plan schema with input_tokens=0 + surface=spec.surface so toolchain-absent rows still satisfy test_matrix_stub's REQUIRED_FIELDS superset check"
  - "Summary header line is '- skipped rate: N% (n/total toolchain-absent)' — the RED test asserts the literal '- skipped rate:' prefix, not the plan's '- skipped (toolchain-absent):' wording; tests win"

patterns-established:
  - "Missing toolchain reads as SKIPPED — never green, never gate FAIL (gate_pass=None)"

requirements-completed: [EVGLD-05, EVGLD-06]

# Metrics
duration: 25min
completed: 2026-06-11
---

# Phase E2 Plan 08: Toolchain Awareness Summary

**Runner preflight prints py/rust/ts OK/MISSING pre-model; absent-toolchain cells record gate_pass=None skip rows and continue; --require-all-toolchains fails fast naming missing binaries; summary.md gains conditional skipped header + column — full eval suite green (108 passed)**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-06-11
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Toolchain preflight (D-03): `{"py": which("python3"), "rust": which("cargo"), "ts": which("node")}` built in run_suite, echoed as `toolchains: py=OK rust=MISSING ts=OK` in the header line, before `_provider_for_eval`
- Skip guard in `_run_suite_async`: lang from `task_id.split("-")[0]`; absent toolchain → full skip row via `_append_row` (skipped=True, skip_reason="toolchain-absent", gate_pass=None, success=None, judge_verdict="skipped", provider/model/judge_model="n/a", duration_s=0.0, input_tokens=0, surface) then `continue` — no fixture copy, no model call (T-E2-19)
- `require_all_toolchains=True` raises `click.UsageError("missing toolchains: cargo ...")` pre-provider (T-E2-20); `voss eval --require-all-toolchains` wired (option + signature + call)
- summary.py: skipped aggregation via `.get("skipped")` (back-compat), per-task skipped count, `show_skipped` presence flag; jinja renders `- skipped rate:` line + skipped column between gate pass and pass rate only when rows carry the field
- Plan-01 xfail markers removed from the 3 runner tests; eval suite 108 passed / 3 xfailed — zero RED left in E2

## Task Commits

1. **Task 1: runner preflight + skip rows + require-all (runner.py, cli.py)** - absorbed into `b2915d6` + `85787ef` by the concurrent auto-committer (bundled with unrelated Claude-SDK work; my diffs verified intact in both)
2. **Task 2: summary skipped count + column (summary.py, jinja)** - `06a84f5` (feat)

## Files Created/Modified
- `voss/eval/runner.py` - run_suite signature + preflight/enforcement + _run_suite_async skip guard
- `voss/harness/cli.py` - --require-all-toolchains option, signature, run_suite threading
- `voss/eval/summary.py` - skipped aggregation + per-task count + context fields
- `voss/templates/eval/summary.md.jinja` - conditional skipped header line + table column (inline expressions, no block-tag newline churn)
- `tests/eval/test_matrix_runner.py` - xfail markers removed; _which helper fixed

## Decisions Made
- **Conditional rendering over unconditional column:** plan claimed the new column was additive, but `test_summary_md.py` pins the OLD table header as a substring and the full legacy output as exact bytes. `show_skipped = any("skipped" in row)` renders the new line/column only for runs that produced skip-aware rows — both test files pass.
- **Header wording from the test, not the plan:** RED test asserts `- skipped rate:`; plan suggested `- skipped (toolchain-absent):`. Implemented `- skipped rate: {rate} ({n}/{total} toolchain-absent)` satisfying both required substrings.
- **Skip row superset:** added `input_tokens=0` and `surface` to the plan's skip-row schema so `test_matrix_stub.REQUIRED_FIELDS ⊇` holds on toolchain-absent machines.

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed plan-01 scaffold test helper**
- **Found during:** Task 1 GREEN
- **Issue:** `_which(cmd, path)` helper called `real_which(cmd, path)` positionally — second positional is shutil.which's `mode`, so any non-stubbed binary raised TypeError. Scaffold never executed under strict xfail (known fictional-scaffold pattern).
- **Fix:** `real_which(cmd, path=path)` in all three tests.
- **Files modified:** tests/eval/test_matrix_runner.py
- **Verification:** all 3 tests pass
- **Committed in:** 85787ef (auto-committer absorbed)

---

**Total deviations:** 1 auto-fixed (test scaffold bug) + 2 documented test-driven adjustments to plan wording/schema (no scope creep; all plan acceptance criteria met).

## Issues Encountered
- Concurrent auto-committer absorbed Task 1 into its own commits (`b2915d6` bundled with Claude-SDK provider work, `85787ef` with stream-parity tests) mid-`git commit` — staged files vanished into those commits; diffs verified intact afterward. Task 2 committed normally (`06a84f5`). Working tree also carries unrelated in-flight SDK edits (auth.py, providers.py, server/app.py) — not mine, left alone.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- E2 phase complete: 12-cell matrix + toolchain awareness + summary surfacing; zero RED in tests/eval (108 passed, 3 xfailed)
- Live proof runs can use `--require-all-toolchains` to guarantee full-matrix coverage, or rely on skip rows reading as skipped (never green) on partial machines

---
*Phase: E2-golden-tasks-repo-matrix*
*Completed: 2026-06-11*
