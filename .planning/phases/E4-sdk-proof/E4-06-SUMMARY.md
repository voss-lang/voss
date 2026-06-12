---
phase: E4-sdk-proof
plan: 06
subsystem: testing
tags: [eval, sdk, suite, task-toml, fake-turn, jsonl]

requires:
  - phase: E4-sdk-proof plans 03-05
    provides: "hardened ts/go/rust consumers the schema tests exercise"
  - phase: E4-sdk-proof plan 02
    provides: "sdk:* dispatch + _drive_sdk_client the suite rows flow through"
provides:
  - "voss eval --suite sdk: four scenarios (one per surface) on one shape-agnostic calc.py fixture"
  - "Consumer end-to-end schema/decode proofs vs FAKE_TURN serve (six-key set, typed decode, gate=false)"
  - "Stub-mode JSONL rows for sdk:python + sdk:ts with the exact REQUIRED_FIELDS set (no new keys)"
affects: [E4-sdk-proof plan 07]

tech-stack:
  added: []
  patterns: ["test-local _spawn_fake_serve/_kill_serve helper (not in runner.py); last-JSON-decodable-line parse tolerates build chatter"]

key-files:
  created:
    - tests/eval/sdk/01-python-basic/task.toml
    - tests/eval/sdk/02-ts-permission-allow/task.toml
    - tests/eval/sdk/03-go-permission-allow/task.toml
    - tests/eval/sdk/04-rust-permission-allow/task.toml
    - tests/eval/sdk/01-python-basic/fixture/calc.py (+3 identical copies)
  modified:
    - tests/eval/test_sdk.py

key-decisions:
  - "Deterministic stub check for the permission scenarios = `test -s .voss-eval-final.txt` (runner writes final pre-checks) — consumer plumbing, never the gate"
  - "REQUIRED_FIELDS/_run_eval/_read_rows imported from tests.eval.test_voss_eval_stub (packages have __init__.py) — no helper duplication"

patterns-established: []

requirements-completed: [EVSDK-03, EVSDK-04, EVSDK-05, EVSDK-06]

duration: 15min
completed: 2026-06-12
---

# Phase E4 Plan 06: SDK Suite Wiring Summary

**`voss eval --suite sdk` loads four hybrid-scored scenarios on one calc.py fixture; all three consumers proven end-to-end vs FAKE_TURN (exact six-key schema + session.idle decode + gate=false); stub rows for sdk:python and the full sdk:ts client path carry surface=sdk:* with the unchanged REQUIRED_FIELDS set — tests/eval fully green with zero remaining xfails**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Four scenarios (01-python-basic edit / 02-ts / 03-go / 04-rust permission-allow) at `tests/eval/sdk/<NN>/` — no double-nesting (Pitfall 7), extra=forbid clean, single shared flat calc.py fixture (D-07 shape-agnostic), zero stub-only gate assertions
- Three consumer schema tests: spawn FAKE_TURN serve (test-local helper, kill-in-finally), run each consumer, assert exact six-key set + `surface` + `"echo"` final + `saw_permission_gate is False` + `"session.idle"` in event_types_seen
- `test_sdk_python_stub_row`: in-process sdk:python row through `--suite sdk --stub`; `test_sdk_client_stub_row`: full CLI → `_drive_sdk_client` → ts consumer → E1 gate/judge row. Both `set(row) == REQUIRED_FIELDS` — E4 added no JSONL keys
- `tests/eval` fully green: 121 passed, 2 skipped (EVSDK-07/08 live-only), 0 xfailed — every EVSDK xfail from W0 now flipped

## Task Commits

1. **Task 1: Four sdk task.tomls + fixture** - `0c1bb99` (feat)
2. **Task 2: Consumer schema/decode tests** - `1ac3d1d` (test)
3. **Task 3: Suite-load + stub rows** - `1b466f8` (test)

## Files Created/Modified
- `tests/eval/sdk/0{1,2,3,4}-*/task.toml` + `fixture/calc.py` - the suite scenarios
- `tests/eval/test_sdk.py` - schema tests, suite-load, stub rows

## Decisions Made
- Permission-scenario deterministic check = non-empty `.voss-eval-final.txt` (runner writes final before checks) — proves consumer plumbing without touching the live-only gate.
- Helpers imported from test_voss_eval_stub instead of copied.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. (Note: task_id "02-ts-..." numeric prefix means the E2 toolchain skip-guard (`lang=task_id.split("-")[0]`) never collides with the sdk suite.)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 07 (final): ts Deny variant + permission_choice forwarding + live codex proof run (EVSDK-07/08, operator checkpoint)
- EVSDK-03/04/05/06 fully proven hermetically; live gate exercise is all that remains

---
*Phase: E4-sdk-proof*
*Completed: 2026-06-12*
