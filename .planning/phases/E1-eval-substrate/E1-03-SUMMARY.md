---
phase: E1-eval-substrate
plan: 03
subsystem: testing
tags: [eval, hybrid-gate, max-turns, judge-model, jsonl, summary]

requires:
  - phase: E1-eval-substrate (plan 01)
    provides: _run_checks executor + TaskSpec.checks schema
  - phase: E1-eval-substrate (plan 02)
    provides: get_eval_max_turns, get_eval_judge_model, VOSS_DEV gate, --max-turns CLI option
provides:
  - Hybrid gate/judge plumbing in run_suite (gate_pass decides success; judge scores quality)
  - Turn cap via configure(max_iterations=max_turns) with capped row + judge skip
  - Judge-model default split (get_eval_judge_model) + same-model stderr warning
  - summary.md gate-pass rate and judge rate as separate columns
affects: [E1-04]

tech-stack:
  added: []
  patterns:
    - "gate_pass conjunction forces success=False regardless of judge verdict"
    - "capped tasks skip judge (not capped guard) and record capped:true"
    - "max_turns forwarded CLI → run_suite → configure(max_iterations=...)"

key-files:
  created:
    - tests/eval/test_hybrid_gate.py
  modified:
    - voss/eval/runner.py
    - voss/harness/cli.py
    - voss/eval/summary.py
    - voss/templates/eval/summary.md.jinja
    - tests/eval/test_summary_md.py
    - tests/eval/test_voss_eval_stub.py
    - tests/eval/test_runner_options.py

key-decisions:
  - "Turn cap hooks via configure(max_iterations=max_turns) around run_turn — least invasive to harness"
  - "capped detected from RunRecord exit_reason == max-iter"
  - "Stub runs keep prior judge_model resolution; live runs default judge to get_eval_judge_model()"

patterns-established:
  - "JSONL row additive fields: gate_pass, capped, checks"
  - "success = False on crash, capped, or gate failure; else judge verdict or None"

requirements-completed: [EVSUB-02, EVSUB-04, EVSUB-06]

duration: ~20min
completed: 2026-06-10
---

# E1 Plan 03: Hybrid Gate + Turn Cap + Judge Split Summary

**Eval runner wires checks into JSONL rows (gate decides pass/fail), enforces per-task turn caps with upfront run header, splits judge model defaults, and extends summary.md with gate-pass vs judge-rate columns**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Integrated `_run_checks` into `run_suite` after `_drive_task`; `gate_pass` forces `success=False` when checks fail
- Added `max_turns` resolution (CLI flag > config > default 15), run header print, and cap via `configure(max_iterations=...)`
- Capped tasks record `capped: true`, `success: false`, `judge_verdict: "skipped"` — no hang
- Judge model defaults to `get_eval_judge_model()` for live runs; same-model collision warns on stderr
- Extended `summary.py` + jinja template with gate-pass and judge-pass rates (5-column per-task table)
- Added `test_hybrid_gate.py` (5 tests); updated `REQUIRED_FIELDS` sentinel and summary exact-bytes pin

## Files Created/Modified

- `voss/eval/runner.py` — full hybrid integration
- `voss/harness/cli.py` — `max_turns=max_turns` forwarded to `run_suite`
- `voss/eval/summary.py` + `voss/templates/eval/summary.md.jinja` — gate/judge rate columns
- `tests/eval/test_hybrid_gate.py` — gate override, no-checks fallback, capped path, header, judge default
- `tests/eval/test_summary_md.py` — updated section + exact-bytes assertions
- `tests/eval/test_voss_eval_stub.py` — `REQUIRED_FIELDS` extended to 19 fields

## Decisions Made

- Turn cap implemented by temporarily setting `configure(max_iterations=max_turns)` around `run_turn` rather than modifying harness iteration API
- `_drive_resume` also threads max_turns and reports capped from `exit_reason`

## Deviations from Plan

Task 3 (`REQUIRED_FIELDS` update) was completed alongside Task 1 when the subagent updated stub tests to match the new row schema. `test_runner_options.py` judge-model assertion also updated for the new default resolution.

## Issues Encountered

- Never-finishing stub plans must use `name` (not `tool`) on Plan steps for StubProvider validation — otherwise the provider falls back to a completing plan and capped stays false

## Verification

```
.venv/bin/python -m pytest tests/eval/ -q  → 66 passed
grep gate_rate / judge_rate in summary.py  → 2 each
grep "not capped" runner.py                → 1
max_turns=max_turns in cli.py              → present
REQUIRED_FIELDS                            → 19 fields
```

## User Setup Required

None.

## Next Phase Readiness

- Golden task.toml files can be retrofitted with `[[checks]]` entries (likely E1-04+)
- Live full-suite proof run on codex auth remains for a later plan

---
*Phase: E1-eval-substrate*
*Completed: 2026-06-10*
