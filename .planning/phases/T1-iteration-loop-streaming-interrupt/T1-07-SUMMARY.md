---
phase: T1-iteration-loop-streaming-interrupt
plan: 07
status: complete
approved_at: 2026-05-16
completed_at: 2026-05-16
commits:
  - 527f8a0 — ci: add T1 grep gate to prevent re-introduction of _substitute_placeholders
  - c29ca78 — test(T1-07): SPEC acceptance suite + grep gate + golden one-shot
---

# T1-07 Summary — SPEC acceptance suite

## Files added

- `tests/harness/test_t1_acceptance.py` — 18 tests asserting each SPEC acceptance checkbox + the 4 quantitative thresholds + the exit-reason matrix + the per-iter permission-gate invariant.
- `tests/harness/test_substitute_placeholders_gone.py` — standalone grep-gate test (developer-local safety net).
- `tests/eval/test_golden_2_one_shot.py` — M5 rename-symbol scenario runs the actual agent loop with a 4-iter scripted provider; asserts one-shot completion.
- `.github/workflows/ci.yml` — `T1 grep gate` step runs before pytest in CI.
- `pyproject.toml` — registered `t1` + `acceptance` pytest markers (strict-markers mode).

## SPEC checkbox → test function mapping

| # | SPEC criterion                                                          | Test function(s)                                                                                              |
|---|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| 1 | while-loop exits on done / max-iter / budget                            | `test_iter_01_while_loop_exits_on_done` + `_max_iter` + `_budget`                                              |
| 2 | iter N+1 receives prior plan + tool_results                             | `test_iter_02_iter_n_plus_one_receives_prior_results`                                                          |
| 3 | `grep _substitute_placeholders voss/` returns zero                      | `test_iter_02_grep_substitute_placeholders_returns_zero` + `test_substitute_placeholders_fully_removed`        |
| 4 | both providers expose `stream()` + parity                               | `test_iter_03_anthropic_openai_stream_exist` (parity already pinned by T1-03's `test_provider_stream_parity`)  |
| 5 | first TurnView token ≤ 500ms                                            | `test_iter_03_first_token_under_500ms`                                                                         |
| 6 | interrupt cancels + finalize ≤ 100ms + `exit_reason="interrupt"`        | `test_iter_04_interrupt_finalizes_within_100ms`                                                                |
| 7 | confidence gate fires only on terminating iter                          | `test_iter_05_mid_loop_low_confidence_no_clarify` + `_terminating_low_confidence_does_clarify`                 |
| 8 | one `iteration.end` event per iter, monotonic index                     | `test_iter_06_one_iter_end_event_per_iter`                                                                     |
| 9 | `note_turn` + RunRecord carry `iteration_count` + `exit_reason`         | `test_iter_06_note_turn_carries_iteration_count_and_exit_reason` + `_runrecord_exit_reason_validated`          |
| 10 | `agent.max_iterations` defaults to 8                                   | `test_default_max_iterations_is_8`                                                                             |
| 11 | M5 golden #2 (rename-symbol) completes one-shot                        | `tests/eval/test_golden_2_one_shot.py::test_golden_2_rename_completes_in_one_run`                              |
| 12 | exact `"halted: max-iter"` final, no RuntimeError                      | `test_exact_halted_max_iter_string` + `test_no_runtime_error_on_cap`                                           |
| —  | exit-reason matrix (all four reachable)                                | `test_exit_reason_matrix_all_four_reachable`                                                                   |
| —  | per-iter `PermissionGate` fresh-check (CONTEXT.md invariant)           | `test_permission_gate_fresh_per_iteration`                                                                     |

## Measured thresholds (local run, MacBook)

- **First-token latency** (`test_iter_03_first_token_under_500ms`): typical 1–3ms in-process; threshold asserted at ≤ 500ms.
- **Interrupt finalize latency** (`test_iter_04_interrupt_finalizes_within_100ms`): typical 5–20ms via `RunRecorder.finalize` monkeypatch; threshold asserted at ≤ 100ms.

## CI grep gate

Workflow step in `.github/workflows/ci.yml` runs before pytest:

```yaml
- name: T1 grep gate — _substitute_placeholders is deleted (SPEC ITER-02)
  run: |
    if grep -rn --include='*.py' --include='*.voss' \
         "_substitute_placeholders" voss/ ; then
      echo "::error::_substitute_placeholders re-introduced — forbidden by T1 ITER-02"
      exit 1
    fi
```

The pytest-based copy (`test_substitute_placeholders_gone.py`) is the developer-local safety net so the regression fails fast before push.

`--include` flags filter to `.py` + `.voss` source so stale `__pycache__/*.pyc` bytes don't false-positive during local invocations.

## M5 fixture follow-up

CONTEXT.md "M5 fixture compatibility = hard break" — pre-T1 M5 golden fixtures will be re-recorded against the new iteration semantics in a separate M5 follow-up. **TODO captured here** so the follow-up surfaces in M5 planning:

> Re-record `tests/eval/golden/02-*` (and any sibling fixtures pinning pre-T1 single-shot trace) against the T1 iteration loop. T1-05's compiled-backend parity test (`test_python_and_compiled_backends_agree`) is currently xfail-marked for the same reason; that xfail flips back to PASS once the compiled `.voss` harness is rebuilt against the new loop semantics.

## Pre-existing test failures (unrelated to T1-07)

`tests/eval/test_voss_eval_stub.py::test_voss_eval_stub_writes_single_jsonl_row` and `tests/eval/test_runner_options.py::test_judge_exception_is_recorded_as_error` were failing on master before T1-07 landed (`git stash` confirmed same failures pre-merge). Not introduced by this plan; tracked separately.

## Verification

```
uv run pytest tests/harness/test_t1_acceptance.py \
              tests/harness/test_substitute_placeholders_gone.py \
              tests/eval/test_golden_2_one_shot.py -v    # 20 passed

grep -rn --include='*.py' --include='*.voss' \
     "_substitute_placeholders" voss/                    # no output, exit 1
```

## Task 3 (human-verify) — APPROVED 2026-05-16

User approved the phase-final `checkpoint:human-verify` gate. Phase T1 is ship-ready.
