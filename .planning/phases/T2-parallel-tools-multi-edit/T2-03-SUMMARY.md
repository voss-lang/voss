---
phase: T2-parallel-tools-multi-edit
plan: 03
type: summary
---

# T2-03 Summary — Partition scheduler + BatchInvariantError + telemetry/recorder wiring

## Goal achieved

`_run_step_loop` rewritten as a one-pass author-order partition scheduler.
Read-only steps batch under `asyncio.Semaphore(get_config().max_parallel_reads)`
via `asyncio.gather`; mutating + unknown steps flush as singletons.
`BatchInvariantError` enforces partition-time invariant. `batch.start` /
`batch.end` telemetry + `RunRecorder.begin_batch` / `end_batch` wired on
multi-step batches only. `_run_turn_exec` gains `except BatchInvariantError`
handler that finalizes with `exit_reason="batch-invariant"` (5th additive
enum value). Per-step `PermissionGate.check` preserved inside batches.

## Code locations

| Symbol | File | Lines |
|--------|------|-------|
| `class BatchInvariantError` | `voss/harness/agent.py` | 56–68 |
| `except BatchInvariantError` handler in `_run_turn_exec` | `voss/harness/agent.py` | 887–931 |
| `_invoke_step_with_gate` helper | `voss/harness/agent.py` | 988–1082 |
| `_dispatch_singleton` helper | `voss/harness/agent.py` | 1085–1098 |
| `_dispatch_read_batch` helper | `voss/harness/agent.py` | 1101–1186 |
| `_run_step_loop` rewrite (partition scheduler) | `voss/harness/agent.py` | 1189–1250 |
| `EXIT_REASONS` extended with `"batch-invariant"` | `voss/harness/session.py` | 72–76 |

## Architecture

```
_run_step_loop  (one-pass partition walk)
   │
   ├─► consecutive non-mutating steps → _dispatch_read_batch(batch_index=N)
   │      │
   │      ├─ if len(steps) > 1: enforce invariant (raise BatchInvariantError)
   │      ├─ asyncio.Semaphore(cap) per-batch (D-17)
   │      ├─ telemetry.emit("batch.start", ...) + recorder.begin_batch(...)
   │      ├─ asyncio.gather(*_run_one(slot, step), return_exceptions=True)
   │      │      └─ async with sem: results[slot] = await _invoke_step_with_gate(...)
   │      └─ telemetry.emit("batch.end", ...) + recorder.end_batch(...)
   │
   └─► mutating or unknown step → _dispatch_singleton (NO batch wrappers)
          └─ results[i] = await _invoke_step_with_gate(...)
```

Singletons reuse `_dispatch_read_batch(batch_index=None, len=1)` semantics
when invoked through that path, but the production `_run_step_loop` calls
`_dispatch_singleton` for the mutating-or-unknown case. `_dispatch_singleton`
skips invariant checks (single mutating step is allowed). Both paths
converge on `_invoke_step_with_gate` for per-step gate + telemetry +
recorder.observe.

## SPEC acceptance criteria mapping

| Req | Acceptance | Test |
|-----|-----------|------|
| PAR-01 | `[R, W, R, R]` → 3 batches in author order; A < B < (C, D) | `test_partition_read_write_read_read` |
| PAR-01 | All-reads → one parallel batch; peak overlap = N | `test_partition_all_reads_one_batch` |
| PAR-01 | All-writes → serial singletons | `test_partition_all_writes_serial` |
| PAR-01 | Isolated read between writes → singleton (no multi-step) | `test_partition_read_alone_between_writes_is_singleton` |
| PAR-01 | Empty steps → `[]` | `test_partition_empty_steps_returns_empty` |
| PAR-01 | Unknown tool → `<error: unknown tool ...>` slot, peers still run | `test_partition_unknown_tool_slot_is_error_string` |
| PAR-01 | gather + semaphore observed via concurrent timestamps | `test_semaphore_cap_allows_full_batch_when_high`, `test_author_order_preserved_with_variable_latency` |
| PAR-02 | BatchInvariantError on synthetic mutating-in-batch | `test_batch_invariant_raises_on_mutating_in_multi_step_batch` |
| PAR-02 | BatchInvariantError on unknown tool in multi-step batch | `test_batch_invariant_raises_on_unknown_tool_in_multi_step_batch` |
| PAR-02 | Singleton skips invariant check | `test_singleton_skips_invariant_check` |
| PAR-02 | Classification by `is_mutating` data, not name pattern | `test_partition_classifies_by_is_mutating_not_name` |
| PAR-02 | Per-step gate.check fires inside multi-step batch | `test_per_step_check_preserved_in_multi_step_read_batch` |
| PAR-02 | Per-step gate.check fires for write singletons | `test_per_step_check_preserved_for_write_singletons` |
| PAR-02 | Mid-batch denial surfaces in single slot only | `test_per_step_check_denies_one_step_in_batch_others_still_run` |
| PAR-02 | `exit_reason="batch-invariant"` finalize path | `test_exit_reason_batch_invariant_surfaces_through_run_turn_exec` |
| PAR-02 | RunRecord accepts `"batch-invariant"` exit reason | `test_runrecord_accepts_batch_invariant_exit_reason` |
| PAR-05 | Semaphore cap=2 enforces peak in-flight = 2 on 6-read batch | `test_semaphore_cap_enforced_at_2` |
| PAR-06 | `batch.start` / `batch.end` only on multi-step batches | `test_telemetry_multi_step_emits_batch_start_end` |
| PAR-06 | Singletons emit ZERO batch wrappers | `test_telemetry_singleton_emits_no_batch_wrappers` |
| PAR-06 | Per-step `tool.call` / `tool.result` preserved inside batches | `test_telemetry_per_step_events_preserved_inside_batches` |
| PAR-06 | Monotonic `batch_index` across multiple batches | `test_telemetry_monotonic_batch_index_across_iterations` |
| PAR-06 | `ok_count` + `err_count` accuracy | `test_batch_end_ok_err_counts_on_mixed_pass_fail` |
| PAR-06 | `recorder.begin_batch` / `end_batch` wired for multi-step | `test_recorder_begin_batch_called_for_multi_step` |
| PAR-06 | No `begin_batch` for singletons | `test_recorder_no_begin_batch_for_singleton` |
| PAR-06 | Recorder end_batch matches telemetry batch.end exactly | `test_recorder_end_batch_matches_telemetry_data` |
| — | Return contract: len, strings, error slots | `test_return_contract_length_and_strings` |
| D-07 | Outer cancel propagates to in-flight reads | `test_cancellation_propagates_to_in_flight_reads` |

## Pytest output

```
$ uv run pytest tests/harness/test_partition_scheduler.py tests/harness/test_permissions.py -v
collected 28 items

tests/harness/test_partition_scheduler.py .........................      [ 89%]
tests/harness/test_permissions.py ...                                    [100%]

============================== 28 passed in 2.16s ==============================
```

Regression batch (T1 + T2-01 + T2-02 + T2-03 surface):

```
$ uv run pytest tests/harness/ -k "agent or recorder or session or permission or partition or cli or bootstrap" -x -q
........................................................................ [ 27%]
........................................................................ [ 54%]
......s................................................................. [ 81%]
.................................................                        [100%]
```

(265 passed, 1 skipped — single skip pre-dates T2; no T1 regressions.)

## Acceptance grep gates (all pass)

```
$ grep -nE "^class BatchInvariantError" voss/harness/agent.py
56:class BatchInvariantError(Exception):

$ grep -nE "_dispatch_read_batch|_dispatch_singleton|_invoke_step_with_gate" voss/harness/agent.py | wc -l
7  (3 defs + 4 call sites)

$ grep -nE "asyncio\.Semaphore\(.*cap" voss/harness/agent.py
1134:    sem = asyncio.Semaphore(cap)

$ python3 -c "import re; t=open('voss/harness/agent.py').read(); print(len(re.findall(r'asyncio\.gather\(.*return_exceptions=True', t, re.S)))"
1

$ python3 -c "import re; t=open('voss/harness/agent.py').read(); print(len(re.findall(r'telemetry\.emit\(\s*\"batch\.(start|end)\"', t, re.S)))"
2

$ grep -n "recorder\.begin_batch\|recorder\.end_batch" voss/harness/agent.py
1148:            recorder.begin_batch(
1182:            recorder.end_batch(

$ grep -cF 'exit_reason="batch-invariant"' voss/harness/agent.py
3   (open-iter end_iteration + finalize + note_turn)

$ grep -F 'except BatchInvariantError' voss/harness/agent.py
    except BatchInvariantError as e:

$ grep -F "batch-invariant" voss/harness/session.py
# T2-03: extended with "batch-invariant" (PAR-02) — 5th additive value
    {"done", "max-iter", "budget", "interrupt", "batch-invariant"}
```

(grep -E single-line is multi-line for the gather + emit calls; verified via
Python regex with re.S DOTALL flag — patterns satisfied 1× each.)

## Threat model verification

- **T-T2-03-01** (Tampering, silent mutation in batch): mitigated — invariant check at top of `_dispatch_read_batch` raises `BatchInvariantError` before any tool invocation; handler finalizes with `exit_reason="batch-invariant"`.
- **T-T2-03-02** (Tampering, classifier by name): mitigated — partitioner reads `ToolEntry.is_mutating` only; `test_partition_classifies_by_is_mutating_not_name` plants `fs_read_evil` with `is_mutating=True` and confirms singleton flush.
- **T-T2-03-03** (DoS, unbounded concurrency): mitigated — per-batch `asyncio.Semaphore(cap)` with `cap = get_config().max_parallel_reads` (default 8, range 1–32 from T2-02).
- **T-T2-03-04** (DoS, cancel discipline): mitigated — `asyncio.gather` propagates outer cancel automatically; `_invoke_step_with_gate` catches `Exception` not `BaseException` so `CancelledError` flows up; `test_cancellation_propagates_to_in_flight_reads` confirms no leaked tasks.
- **T-T2-03-05** (InfoDisclosure in per-step events): mitigated — `_invoke_step_with_gate` calls `telemetry.redact_tool_args(dict(step.args))` identically to the prior serial path.
- **T-T2-03-06** (Recorder begin/end pairing): mitigated — T2-01 enforces RuntimeError on out-of-order; scheduler always pairs `begin_batch` + `end_batch` for `batch_index is not None`.
- **T-T2-03-SC** (Supply chain): accepted — no new third-party deps; only stdlib `asyncio.Semaphore` + existing `time` / `telemetry` / `recorder`.

## Wave 2 handoff to T2-04 / T2-05

- The scheduler reads `get_config().max_parallel_reads` at run start; T2-04 (`fs_read_many`) and T2-05 (`fs_edit_many`) integrate as new `ToolEntry` registrations. `fs_read_many` registers with `is_mutating=False` (lands inside read batches); `fs_edit_many` registers with `is_mutating=True` (flushes as singleton, preserving M9-05 DiffModal atomicity).
- `BatchRecord` records produced by `recorder.begin_batch` / `end_batch` are visible in `IterationRecord.batches` on disk via T2-01's round-trip path.
- `exit_reason="batch-invariant"` is now in the locked `EXIT_REASONS` set; downstream consumers (`voss show`, telemetry post-processors) auto-accept the 5th value.
