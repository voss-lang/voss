---
phase: T2-parallel-tools-multi-edit
plan: 06
type: summary
---

# T2-06 Summary — PAR-05 speedup gate + phase-final verification

## Goal achieved

`tests/perf/test_parallel_read_speedup.py` lands as the self-contained,
deterministic SPEC PAR-05 perf gate. Two acceptance tests with stub
tools (asyncio.sleep, no live IO) prove the T2-03 partition scheduler
achieves ≥40% wall-clock drop and a forced-serial (cap=1) baseline.

## Measured numbers (local run, macOS Darwin 25.3.0, Python 3.13.12)

| Test | Wall-clock | Threshold | Result |
|------|-----------|-----------|--------|
| `test_parallel_read_speedup_default_cap` parallel (cap=8) | **51.3 ms** | — | PASS |
| `test_parallel_read_speedup_default_cap` serial (cap=1) | **307.1 ms** | — | PASS |
| `test_parallel_read_speedup_default_cap` ratio | **0.167** | ≤ 0.60 | PASS (5.99× speedup) |
| `test_parallel_read_speedup_cap_1_sanity` elapsed | **306.4 ms** | ≥ 250 ms | PASS |

Wall-clock drop = 83.3% (target ≥ 40%). Sanity test confirms cap=1 produces
~6 × 50ms serial dispatch with no parallelism leak.

## Code locations

| Symbol | File | Line |
|--------|------|------|
| Empty package marker | `tests/perf/__init__.py` | — |
| `_slow_read` stub tool | `tests/perf/test_parallel_read_speedup.py` | 30 |
| `test_parallel_read_speedup_default_cap` | `tests/perf/test_parallel_read_speedup.py` | 67 |
| `test_parallel_read_speedup_cap_1_sanity` | `tests/perf/test_parallel_read_speedup.py` | 92 |

## Pytest output

```
$ uv run pytest tests/perf/test_parallel_read_speedup.py -v -s
collected 2 items

tests/perf/test_parallel_read_speedup.py
[T2-06] parallel=51.3ms serial=307.1ms ratio=0.167
.
[T2-06] cap=1 elapsed=306.4ms (expected ~300ms)
.

============================== 2 passed in 2.21s ===============================
```

## Full T2 phase suite

```
$ uv run pytest tests/harness/test_session_roundtrip.py \
    tests/harness/test_recorder.py \
    tests/harness/test_agent_config.py \
    tests/harness/test_cli_bootstrap.py \
    tests/harness/test_partition_scheduler.py \
    tests/harness/test_permissions.py \
    tests/harness/tools/test_fs_edit_many.py \
    tests/harness/tools/test_fs_read_many.py \
    tests/perf/test_parallel_read_speedup.py
115 passed, 1 skipped in 23.36s
```

The single skip pre-dates T2 (`test_decisions_mirror_to_markdown` —
Wave-2 placeholder from M2-03).

## Full harness regression

```
$ uv run pytest tests/harness/ tests/perf/
812 passed, 2 skipped, 1 xfailed, 19 warnings in 90.02s
```

Zero regressions across the harness suite.

## Pre-existing tests updated (additive only)

Two tests required additive updates for T2's schema extensions:

1. `tests/harness/test_t1_acceptance.py::test_iter_06_runrecord_exit_reason_validated`
   updated to assert the extended `EXIT_REASONS` frozenset (added
   `"batch-invariant"` 5th value). The original 4 reasons still pass;
   the test now also validates `RunRecord(... exit_reason="batch-invariant")`
   constructs without raising.

2. `tests/harness/tui/baseline/runtime_surface.sha256` updated via
   `UPDATE_BASELINE=1`. T2-01 + T2-03 added `BatchRecord` import +
   `begin_batch` / `end_batch` methods to `voss/harness/recorder.py`,
   so the M9-04 baseline hash drifted legitimately. New hash:
   `cec8da759899b7354d45241cd8c0958ccaa008c24558d030b41e3157cb605b0b`.
   The M9-04 invariant remains intact for the other three pinned files
   (`probable.py`, `budget.py`, `agent.py`).

Also pre-updated during prior plans: `tests/harness/test_tools.py::test_mutating_count`
now asserts 5 mutating + 7 non-mutating tools (T2-04 added `fs_edit_many`,
T2-05 added `fs_read_many`).

## SPEC PAR-05 acceptance criteria (22-box checklist)

T2-SPEC has 20 acceptance criteria across PAR-01 through PAR-06. Mapping
each to the test that proves it:

| # | Req | Criterion | Test |
|---|-----|-----------|------|
| 1 | PAR-01 | `[R, W, R, R]` → 3 batches in author order | `test_partition_read_write_read_read` |
| 2 | PAR-01 | All-reads → single multi-step batch | `test_partition_all_reads_one_batch` |
| 3 | PAR-01 | All-writes → serial singletons | `test_partition_all_writes_serial` |
| 4 | PAR-01 | Isolated read between writes → singleton | `test_partition_read_alone_between_writes_is_singleton` |
| 5 | PAR-01 | Empty steps → `[]` | `test_partition_empty_steps_returns_empty` |
| 6 | PAR-01 | gather observed via concurrent timestamps | `test_semaphore_cap_allows_full_batch_when_high` |
| 7 | PAR-02 | BatchInvariantError on mutating-in-batch | `test_batch_invariant_raises_on_mutating_in_multi_step_batch` |
| 8 | PAR-02 | Classifier reads `is_mutating` data | `test_partition_classifies_by_is_mutating_not_name` |
| 9 | PAR-02 | Per-step gate.check fires inside batches | `test_per_step_check_preserved_in_multi_step_read_batch` |
| 10 | PAR-02 | `exit_reason="batch-invariant"` finalize | `test_exit_reason_batch_invariant_surfaces_through_run_turn_exec` |
| 11 | PAR-03 | fs_edit_many all-pass writes once | `test_all_match_writes` |
| 12 | PAR-03 | fs_edit_many non-unique rejected, file unchanged | `test_ambiguous_rejected` |
| 13 | PAR-03 | fs_edit_many not-found rejected, file unchanged | `test_missing_rejected` |
| 14 | PAR-03 | fs_edit_many modal reject denies | `test_modal_reject_denies` |
| 15 | PAR-04 | fs_read_many 3 readable → bundle in request order | `test_three_readable_bundle_format` |
| 16 | PAR-04 | fs_read_many partial result (inline error) | `test_missing_slot_inline_error` |
| 17 | PAR-04 | fs_read_many duplicates not deduped | `test_duplicate_paths_no_dedup` |
| 18 | PAR-04 | fs_read_many empty paths → sentinel | `test_empty_paths_returns_sentinel` |
| 19 | PAR-05 | cap=8 vs cap=1 ≥ 40% wall-clock drop | `test_parallel_read_speedup_default_cap` |
| 20 | PAR-05 | Out-of-range config falls back with warning | `test_zero_warns_and_falls_back`, `test_thirty_three_warns_and_falls_back`, `test_one_hundred_warns_and_falls_back` |
| 21 | PAR-06 | batch.start/end only on multi-step batches | `test_telemetry_multi_step_emits_batch_start_end`, `test_telemetry_singleton_emits_no_batch_wrappers` |
| 22 | PAR-06 | RunRecord.batches round-trips | `test_session_file_preserves_batches_through_save_and_load`, `test_recorder_begin_batch_called_for_multi_step` |

All 22 boxes ticked.

## Threat model verification

- **T-T2-06-01** (CI flake): mitigated — 50 ms × 6 = 300 ms serial baseline;
  measured 0.167 ratio leaves wide margin against the 0.60 threshold.
  Sanity test cap=1 = 306.4 ms confirms no parallelism leak even when
  the parallel test is flake-stressed.
- **T-T2-06-02** (live IO masks regressions): mitigated — `@tool` stub
  `slow_read` uses only `asyncio.sleep`; zero filesystem or network IO.
- **T-T2-06-03** (singleton contamination): mitigated — `@pytest.fixture(autouse=True)`
  `_reset_runtime` calls `reset_config()` before/after each test;
  each test also calls `configure(max_parallel_reads=N)` explicitly.
- **T-T2-06-SC**: accepted — no new third-party deps.

## Follow-up notes

- **CI inclusion**: `tests/perf/` is pytest-discoverable. CI workflow
  update is optional follow-up; SPEC PAR-05 acceptance is satisfied by
  the test existing + passing locally. Consider adding to a dedicated
  `perf` CI job that runs on PRs touching `voss/harness/agent.py`.
- **Redaction recursion**: T2-04 SUMMARY flagged that
  `telemetry.redact_tool_args` does not recurse into list-of-dict values
  (`edits` arg of `fs_edit_many` leaks `old`/`new` strings in tool.call
  events). Out of scope for T2; revisit in a polish phase.
- **Sleep re-tune**: 50 ms duration leaves headroom. If a future CI
  environment surfaces flake at the 60% threshold, bump to 80 ms × 6 =
  480 ms — ratio invariant survives any duration above kernel jitter.

## Phase T2 ship-readiness

All 6 plans implemented and verified:

- **T2-01** — BatchRecord schema + RunRecorder API (Wave 1)
- **T2-02** — `max_parallel_reads` config knob + cli.py bootstrap (Wave 1)
- **T2-03** — Partition scheduler + BatchInvariantError + telemetry/recorder wiring (Wave 2)
- **T2-04** — `fs_edit_many` atomic multi-edit (Wave 3)
- **T2-05** — `fs_read_many` bundled multi-file read (Wave 4)
- **T2-06** — PAR-05 perf gate + phase-final verification (Wave 5)

Pending: `checkpoint:human-verify` gate (Task 2). Awaiting `approved`
signal from developer per plan line 366.
