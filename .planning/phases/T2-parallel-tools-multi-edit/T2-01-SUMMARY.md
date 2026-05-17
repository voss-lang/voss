---
phase: T2-parallel-tools-multi-edit
plan: 01
type: summary
---

# T2-01 Summary — BatchRecord schema + recorder capture API

## Goal achieved

PAR-06 schema substrate landed: `BatchRecord` dataclass nested under T1's
`IterationRecord` via additive `batches: list[BatchRecord]` field, plus
`RunRecorder.begin_batch` / `end_batch` capture API parallel to T1's
`begin_iteration` / `end_iteration`. Pure data + recorder plumbing — no
agent.py / tools.py / telemetry changes.

## Code locations

| Symbol | File | Line |
|--------|------|------|
| `class BatchRecord` | `voss/harness/session.py` | 76 |
| `IterationRecord.batches: list[BatchRecord]` field | `voss/harness/session.py` | 105 |
| `RunRecorder.begin_batch` | `voss/harness/recorder.py` | 152 |
| `RunRecorder.end_batch` | `voss/harness/recorder.py` | 172 |
| `BatchRecord` import on recorder | `voss/harness/recorder.py` | 17 |

## BatchRecord field set (D-09 locked minimum)

- `batch_index: int`
- `step_indices: list[int] = field(default_factory=list)`
- `parallel_count: int = 0`
- `wall_clock_ms: int = 0`
- `ok_count: int = 0`
- `err_count: int = 0`

No `started_at` / `ended_at`. Planner picked minimal per RESEARCH A1/A2 +
CONTEXT "Claude's Discretion" — single wall-clock time signal avoids
extra serialization surface. Adding timestamps remains additive-safe
should dogfood demand them.

## Additive guarantee

- `IterationRecord.batches` defaults to `[]` via `field(default_factory=list)`.
- Pre-T2 on-disk fixtures (no `"batches"` key in JSON) reconstruct with
  `batches == []` — verified end-to-end via
  `tests/harness/test_session_roundtrip.py::TestPreT2FixtureAdditiveGuarantee::test_pre_t2_session_file_loads_with_empty_batches`.
- `RunRecord` top-level shape unchanged (no new top-level field) —
  preserves `voss resume` round-trip behavior.

## Recorder error paths

| Path | Trigger | Message |
|------|---------|---------|
| `begin_batch` outside iteration | `_iterations` empty | `"begin_batch called outside an iteration scope"` |
| `end_batch` with no iteration | `_iterations` empty | `"end_batch called without a matching begin_batch"` |
| `end_batch` with no batch in current iter | `_iterations[-1].batches` empty | `"end_batch called without a matching begin_batch"` |

`step_indices` is stored as a defensive copy (`list(step_indices)`) —
mutating the caller's input list after `begin_batch` does NOT mutate the
stored `BatchRecord.step_indices`.

## Tests

`tests/harness/test_session_roundtrip.py` (new, 8 tests):

1. `TestBatchRecordSchema::test_defaults_zeroed_with_only_index_required`
2. `TestBatchRecordSchema::test_full_payload_preserves_every_field`
3. `TestIterationRecordAdditive::test_iteration_record_defaults_to_empty_batches`
4. `TestIterationRecordAdditive::test_asdict_serializes_batches_as_list_of_dicts`
5. `TestPreT2FixtureAdditiveGuarantee::test_iteration_dict_without_batches_key_reconstructs_with_empty_list`
6. `TestPreT2FixtureAdditiveGuarantee::test_pre_t2_session_file_loads_with_empty_batches`
7. `TestMultiBatchRoundTrip::test_runrecord_with_two_batches_roundtrips_via_asdict`
8. `TestMultiBatchRoundTrip::test_session_file_preserves_batches_through_save_and_load`

`tests/harness/test_recorder.py` (extended, 9 new tests):

1. `test_begin_batch_appends_and_returns_record`
2. `test_end_batch_patches_trailing_record`
3. `test_begin_end_batch_full_state_after_cycle`
4. `test_multiple_sequential_batches_preserve_monotonic_index`
5. `test_begin_batch_outside_iteration_raises`
6. `test_end_batch_with_no_iteration_raises`
7. `test_end_batch_with_iteration_but_no_batch_raises`
8. `test_step_indices_stored_as_defensive_copy`
9. `test_batches_nest_within_correct_iteration`

## Pytest output

```
$ uv run pytest tests/harness/test_session_roundtrip.py tests/harness/test_recorder.py -v
======================== 22 passed, 1 skipped in 2.34s =========================
```

Regression check against T1 substrate:

```
$ uv run pytest tests/harness/test_session_roundtrip.py \
    tests/harness/test_recorder.py \
    tests/harness/test_session_iterations.py \
    tests/harness/test_recorder_iterations.py -x -q
.....s..................................                                 [100%]
```

Session redaction allowlist + session core:

```
$ uv run pytest tests/harness/test_session.py tests/harness/test_session_redaction.py -x -q
....................                                                     [100%]
```

## Acceptance grep gates (all pass)

```
$ grep -nE "^class BatchRecord" voss/harness/session.py
76:class BatchRecord:

$ grep -n "batches: list\[BatchRecord\]" voss/harness/session.py
105:    batches: list[BatchRecord] = field(default_factory=list)

$ grep -n "def begin_batch\|def end_batch" voss/harness/recorder.py
152:    def begin_batch(
172:    def end_batch(

$ grep -n "BatchRecord(" voss/harness/recorder.py
164:        br = BatchRecord(

$ grep -F 'outside an iteration scope' voss/harness/recorder.py
            raise RuntimeError("begin_batch called outside an iteration scope")

$ grep -F 'without a matching begin_batch' voss/harness/recorder.py
            raise RuntimeError("end_batch called without a matching begin_batch")
```

## Threat model verification

- **T-T2-01-01** (Tampering, save/load roundtrip): mitigated — pre-T2
  fixture test + multi-batch roundtrip test both green.
- **T-T2-01-02** (InfoDisclosure, field set): accepted — 6 fields are
  operational metadata only; no paths, no tool args, no secrets.
- **T-T2-01-03** (DoS, mid-turn RuntimeError): accepted — raises loudly
  on out-of-order invocation; T2-03 scheduler guards with `if recorder
  is not None:` and never calls outside `begin_iteration` scope.

## Wave 1 handoff to T2-03

The partition scheduler (T2-03) can now wire:

```python
br = recorder.begin_batch(batch_index=i, step_indices=indices)
t0 = time.monotonic()
results = await asyncio.gather(*coros, return_exceptions=True)
wall_clock_ms = int((time.monotonic() - t0) * 1000)
ok = sum(1 for r in results if not isinstance(r, Exception))
err = len(results) - ok
recorder.end_batch(wall_clock_ms=wall_clock_ms, ok_count=ok, err_count=err)
```

No further schema or recorder changes required for downstream T2 plans.
