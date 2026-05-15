---
phase: T2-parallel-tools-multi-edit
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/session.py
  - voss/harness/recorder.py
  - tests/harness/test_recorder.py
  - tests/harness/test_session_roundtrip.py
autonomous: true
requirements: [PAR-06]
must_haves:
  truths:
    - "BatchRecord dataclass exists in session.py with batch_index/step_indices/parallel_count/wall_clock_ms/ok_count/err_count fields"
    - "IterationRecord.batches: list[BatchRecord] = field(default_factory=list) added additively to T1's IterationRecord"
    - "RunRecorder.begin_batch(batch_index, step_indices) appends a new BatchRecord onto the current iteration's batches list"
    - "RunRecorder.end_batch(wall_clock_ms, ok_count, err_count) patches the trailing BatchRecord on the current iteration"
    - "begin_batch raises RuntimeError if called outside an iteration scope; end_batch raises RuntimeError if no matching begin_batch"
    - "dataclasses.asdict roundtrip preserves an empty batches list on pre-T2 IterationRecord fixtures (additive guarantee)"
    - "RunRecord serialize -> deserialize roundtrip preserves multi-batch IterationRecord with all BatchRecord field values intact"
  artifacts:
    - path: "voss/harness/session.py"
      provides: "BatchRecord @dataclass + IterationRecord.batches additive field"
      contains: "class BatchRecord"
    - path: "voss/harness/recorder.py"
      provides: "RunRecorder.begin_batch + RunRecorder.end_batch methods"
      contains: "def begin_batch"
    - path: "tests/harness/test_recorder.py"
      provides: "begin_batch/end_batch happy-path + error-path tests"
      contains: "test_begin_batch\\|test_end_batch"
    - path: "tests/harness/test_session_roundtrip.py"
      provides: "Roundtrip test for BatchRecord serialization + pre-T2 fixture additive guarantee"
      contains: "BatchRecord\\|batches"
  key_links:
    - from: "voss/harness/recorder.py:RunRecorder.begin_batch"
      to: "voss/harness/session.py:BatchRecord"
      via: "instantiates BatchRecord and appends to self._iterations[-1].batches"
      pattern: "BatchRecord\\("
    - from: "voss/harness/session.py:IterationRecord.batches"
      to: "voss/harness/session.py:BatchRecord"
      via: "list[BatchRecord] additive field on T1's IterationRecord"
      pattern: "list\\[BatchRecord\\]"
---

<objective>
Land the PAR-06 schema substrate: `BatchRecord` dataclass nested under T1's
`IterationRecord` via a new `batches: list[BatchRecord]` additive field, plus
`RunRecorder.begin_batch`/`end_batch` capture API parallel to T1's
`begin_iteration`/`end_iteration`. This is pure data + recorder plumbing — no
agent.py changes, no tools.py changes, no telemetry.emit changes. T2-03 (the
partition scheduler) calls these methods; this plan provides them.

Purpose: SPEC PAR-06 mandates `IterationRecord.batches` is schema-additive +
M2/T1 compatible. CONTEXT.md D-08 nests `BatchRecord` inside the iteration that
produced it (not at `RunRecord` top level). D-09 locks the minimum field set.
PATTERNS.md confirms the closest analog is T1's `IterationRecord` shape +
T1's `RunRecorder.begin_iteration`/`end_iteration` nesting pattern. This plan
is Wave 1 because it has zero dependency on T2 scheduler work and the scheduler
(T2-03) cannot wire recorder calls until this API exists.

Output: BatchRecord dataclass, IterationRecord.batches additive field,
RunRecorder.begin_batch + end_batch methods, and tests proving (a) happy-path
nest into the current iteration, (b) error paths when called outside an iter
scope, (c) round-trip serialization preserves batches, (d) pre-T2 fixtures
(no batches key on disk) load with empty batches list.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-VALIDATION.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md
@voss/harness/session.py
@voss/harness/recorder.py
</context>

<interfaces>
After T1-01 lands, `voss/harness/session.py` has an `IterationRecord` dataclass
with fields including `tool_results`, `started_at`, `ended_at`, `exit_reason`,
and `RunRecorder._iterations: list[IterationRecord]` is the live capture buffer
(last entry is the "current" iteration).

T1-01's recorder API:
- `RunRecorder.begin_iteration() -> IterationRecord` appends a new entry to
  `self._iterations` and returns it.
- `RunRecorder.end_iteration(plan, tool_results, cost_usd, prompt_tokens,
  completion_tokens, exit_reason)` patches the trailing iteration.

T2 mirrors that nesting pattern one level deeper:
- `RunRecorder.begin_batch(batch_index, step_indices) -> BatchRecord` appends
  a new entry onto `self._iterations[-1].batches` and returns it.
- `RunRecorder.end_batch(wall_clock_ms, ok_count, err_count)` patches the
  trailing batch on the trailing iteration.

BatchRecord field set (per CONTEXT.md D-09 minimum, locked here):
- batch_index: int — monotonic within iteration
- step_indices: list[int] = field(default_factory=list)
- parallel_count: int = 0
- wall_clock_ms: int = 0
- ok_count: int = 0
- err_count: int = 0

NO started_at/ended_at on BatchRecord (CONTEXT.md "Claude's Discretion" flags
this; per RESEARCH.md A1+A2, planner picks minimal — wall_clock_ms is the
single time signal). Avoids extra serialization surface; can add later if
dogfood demands timestamps.

Additive guarantee invariant: pre-T2 `IterationRecord` JSON dicts loaded by
`session.load` must populate `batches=[]` automatically via
`field(default_factory=list)` on the dataclass. This mirrors T1-01's pattern
for the additive `iterations: list[IterationRecord] = field(default_factory=list)`
field on `RunRecord`.

Round-trip mechanism: `session.save()` already uses `dataclasses.asdict` which
recursively serializes nested dataclasses. `session.load()` reconstructs via
`IterationRecord(**iter_dict)` or similar — confirm during read; if it uses a
custom builder, extend to map `batches` list-of-dicts back into `BatchRecord`
instances. The pattern from T1-01 (whatever shape it lands) is the canonical
reference.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: BatchRecord dataclass + IterationRecord.batches additive field</name>
  <files>voss/harness/session.py, tests/harness/test_session_roundtrip.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (PAR-06 + acceptance criterion 18 "RunRecord.batches round-trips")
    - .planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md (D-08, D-09)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (section "voss/harness/session.py — BatchRecord dataclass")
    - voss/harness/session.py (entire file — locate IterationRecord added by T1-01 and the RunRecord dataclass at lines ~70-87, plus the save/load roundtrip path)
    - tests/harness/test_session_roundtrip.py if it exists (T1 CI gate test for pre-T2 fixture parsing); otherwise grep for existing roundtrip tests via `grep -rn "asdict\|from_dict\|session.load" tests/harness/`
  </read_first>
  <behavior>
    - `BatchRecord(batch_index=0)` constructs with default empty step_indices list and zero counts
    - `BatchRecord(batch_index=2, step_indices=[3, 4, 5], parallel_count=3, wall_clock_ms=120, ok_count=3, err_count=0)` constructs with all fields populated
    - `IterationRecord(...)` instances default to `batches=[]` when no batches kwarg passed (additive guarantee)
    - `dataclasses.asdict(iter_record_with_batches)` produces a dict whose `"batches"` key is a list of dicts each containing the 6 BatchRecord fields
    - Round-trip: build a RunRecord containing 1 iteration with 2 BatchRecord entries; call session.save() to a tmp path; call session.load() back; assert `loaded.iterations[0].batches[0].batch_index == 0` and `loaded.iterations[0].batches[1].batch_index == 1` and all field values preserved
    - Pre-T2 fixture: synthesize an IterationRecord JSON dict WITHOUT a "batches" key; load it via the same code path used by session.load; assert `loaded.iterations[0].batches == []` (additive default kicks in)
  </behavior>
  <action>
    Edit `voss/harness/session.py`:

    1. Add `BatchRecord` dataclass JUST ABOVE the T1-introduced
       `IterationRecord` dataclass. Use `@dataclass` (NOT pydantic — match
       T1's `IterationRecord` and the existing `RunRecord` dataclass shape
       per RESEARCH.md A1/A2 + PATTERNS.md "Existing dataclass pattern").

       ```
       @dataclass
       class BatchRecord:
           """One parallel read-batch within an iteration. Singletons emit no BatchRecord (SPEC PAR-06 line 67)."""
           batch_index: int
           step_indices: list[int] = field(default_factory=list)
           parallel_count: int = 0
           wall_clock_ms: int = 0
           ok_count: int = 0
           err_count: int = 0
       ```

       Imports: `field` and `dataclass` are already imported by the existing
       RunRecord dataclass — no new imports.

    2. In `IterationRecord` (the T1-01 dataclass), add a new field at the
       end of the field list:

       ```
       batches: list[BatchRecord] = field(default_factory=list)
       ```

       Place it AFTER all T1-01-introduced fields (preserves their order)
       and BEFORE any closing dataclass body markers. This is a strictly
       additive append.

    3. If `session.load()` or its equivalent uses a custom dict→dataclass
       builder (e.g., `IterationRecord(**iter_dict)` with manual key
       mapping), extend it to map an incoming `"batches"` list-of-dicts
       into `[BatchRecord(**b) for b in iter_dict.get("batches", [])]`.
       If load uses `dacite` or `from_dict`, the additive default handles
       it automatically — confirm by reading the load path.

    Write `tests/harness/test_session_roundtrip.py` (create if missing,
    extend if it exists from T1). Six tests matching the six behavior bullets.

    Use `tmp_path` for the session-file fixture. Use existing helpers from
    `voss/harness/session.py` (e.g. `SessionRecord.save`, `load_session`,
    or whatever T1-01 exposes — discover via `grep -nE "^def |^class " voss/harness/session.py`).

    The "pre-T2 fixture" test should write a JSON dict by hand (using
    `json.dump`) that contains an `IterationRecord`-shaped dict with NO
    "batches" key, then call the load path and assert the resulting
    IterationRecord has `batches == []`. This proves the additive guarantee
    end-to-end on the file format, not just the dataclass default.

    Do NOT touch RunRecord (top-level shape unchanged per D-08). Do NOT
    add timestamps to BatchRecord (locked minimal per CONTEXT.md
    "Claude's Discretion" → minimal pick).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_session_roundtrip.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^class BatchRecord" voss/harness/session.py` returns 1 match
    - source assertion: `grep -n "batches: list\[BatchRecord\]" voss/harness/session.py` returns 1 match
    - source assertion: BatchRecord has all 6 fields — `grep -E "batch_index|step_indices|parallel_count|wall_clock_ms|ok_count|err_count" voss/harness/session.py | grep -v '^#' | wc -l` >= 6
    - additive assertion: pre-T2 fixture (no "batches" key on disk) loads with `batches == []`
    - roundtrip assertion: 2 BatchRecord entries written + loaded preserves all 6 field values on both
    - behavior assertion: all 6 pytest behaviors pass
    - regression assertion: `uv run pytest tests/harness/test_session_roundtrip.py tests/harness/test_recorder.py -x -q` passes (no T1 test breakage)
    - test command: `uv run pytest tests/harness/test_session_roundtrip.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>BatchRecord dataclass lives in session.py with 6 fields; IterationRecord gains a batches: list[BatchRecord] additive field defaulting to []; session.save/load round-trip preserves batches; pre-T2 fixtures load with empty batches.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: RunRecorder.begin_batch + end_batch methods</name>
  <files>voss/harness/recorder.py, tests/harness/test_recorder.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (PAR-06 acceptance criterion "monotonic batch_index across multiple batches")
    - .planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md (D-09 minimum field set)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (section "voss/harness/recorder.py — begin_batch / end_batch")
    - voss/harness/recorder.py (entire file — locate RunRecorder class, begin_iteration/end_iteration methods added by T1-01, and the _iterations attribute)
    - voss/harness/session.py (Task 1 just-written — BatchRecord shape)
    - tests/harness/test_recorder.py (existing test patterns; the begin_iteration/end_iteration tests from T1 are the closest reference)
  </read_first>
  <behavior>
    - begin_batch(batch_index=0, step_indices=[0, 1, 2]) appends a BatchRecord to the current iteration's batches list and returns it
    - The returned BatchRecord has batch_index=0, step_indices=[0, 1, 2], parallel_count=3, and zero-defaulted wall_clock_ms/ok_count/err_count
    - end_batch(wall_clock_ms=125, ok_count=3, err_count=0) patches the trailing BatchRecord on the trailing iteration with those values
    - After begin_batch + end_batch, rec._iterations[-1].batches[-1] reflects the post-end state (all 6 fields populated correctly)
    - Multiple sequential batches within one iteration produce monotonic batch_index values when the caller supplies them (begin_batch is a passive append; the caller decides batch_index)
    - begin_batch called when self._iterations is empty (no begin_iteration prior) raises RuntimeError("begin_batch called outside an iteration scope")
    - end_batch called when self._iterations is empty raises RuntimeError("end_batch called without a matching begin_batch")
    - end_batch called when current iteration's batches is empty (begin_batch never called) raises RuntimeError("end_batch called without a matching begin_batch")
    - The step_indices argument is stored as a copy (not a reference): mutating the input list after begin_batch does NOT mutate the stored BatchRecord.step_indices
  </behavior>
  <action>
    Edit `voss/harness/recorder.py`:

    Add two new methods on `RunRecorder` BELOW the existing T1-01
    `begin_iteration` / `end_iteration` methods:

    ```
    def begin_batch(self, *, batch_index: int, step_indices: list[int]) -> BatchRecord:
        """Append a new BatchRecord to the current iteration's batches list.

        Must be called inside an iteration scope (begin_iteration must have
        been called and end_iteration must NOT have been called for the
        current iter). The caller supplies batch_index; the recorder is a
        passive append site.

        Returns the newly-appended BatchRecord so the caller can hold a
        reference for in-place updates if desired (the normal flow is
        end_batch which patches the trailing entry).
        """
        if not self._iterations:
            raise RuntimeError("begin_batch called outside an iteration scope")
        br = BatchRecord(
            batch_index=batch_index,
            step_indices=list(step_indices),  # defensive copy
            parallel_count=len(step_indices),
        )
        self._iterations[-1].batches.append(br)
        return br

    def end_batch(self, *, wall_clock_ms: int, ok_count: int, err_count: int) -> None:
        """Patch the trailing BatchRecord on the current iteration with totals.

        Wall-clock and ok/err counts are computed by the scheduler after
        asyncio.gather completes. The method is a pure mutation of the
        trailing BatchRecord; it does NOT append a new one.
        """
        if not self._iterations or not self._iterations[-1].batches:
            raise RuntimeError("end_batch called without a matching begin_batch")
        br = self._iterations[-1].batches[-1]
        br.wall_clock_ms = wall_clock_ms
        br.ok_count = ok_count
        br.err_count = err_count
    ```

    Imports: add `from voss.harness.session import BatchRecord` at the top
    of recorder.py if BatchRecord isn't already importable through the
    existing IterationRecord import (check `grep -n "from voss.harness.session import\|from .session import" voss/harness/recorder.py` and extend the same line).

    Write tests in `tests/harness/test_recorder.py` (extend the existing file).
    Nine tests matching the nine behavior bullets. Reuse the
    `tests/harness/test_recorder.py:test_inspect_captures_fs_read`-style
    shape (sync `def test_*` with `RunRecorder.start()` setup).

    Use `pytest.raises(RuntimeError, match="outside an iteration scope")`
    for the begin_batch error path and `pytest.raises(RuntimeError, match="without a matching begin_batch")`
    for both end_batch error paths.

    Do NOT modify begin_iteration / end_iteration. Do NOT change observe.
    The new methods are purely additive.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_recorder.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "def begin_batch\|def end_batch" voss/harness/recorder.py` returns 2 matches
    - source assertion: `grep -n "BatchRecord(" voss/harness/recorder.py` returns >= 1 match (begin_batch instantiation)
    - error-path assertion: `grep -F 'outside an iteration scope' voss/harness/recorder.py` returns 1 match
    - error-path assertion: `grep -F 'without a matching begin_batch' voss/harness/recorder.py` returns 1 match
    - defensive-copy assertion: pytest test confirms mutating input step_indices after begin_batch does not mutate stored BatchRecord
    - behavior assertion: all 9 pytest behaviors pass
    - regression assertion: `uv run pytest tests/harness/test_recorder.py tests/harness/test_session_roundtrip.py -x -q` passes
    - test command: `uv run pytest tests/harness/test_recorder.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>RunRecorder.begin_batch and end_batch methods land on the recorder; happy-path nest + 3 error paths covered; defensive-copy of step_indices verified; no T1 recorder test breakage.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| in-process recorder state → on-disk session JSON | Recorder buffers `_iterations` and writes to `.voss/sessions/<id>.json` via `session.save`; pre-T2 fixtures must load forward-compatibly without losing data |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T2-01-01 | Tampering | session.save/load JSON roundtrip with new BatchRecord field | mitigate | `field(default_factory=list)` ensures pre-T2 fixtures load with empty `batches`; roundtrip pytest covers serialize→deserialize parity for multi-batch IterationRecord |
| T-T2-01-02 | Information Disclosure | BatchRecord field set | accept | All 6 fields are operational metadata (indices, counts, wall-clock); no file paths, no tool args, no secrets — nothing redactable |
| T-T2-01-03 | Denial of Service | recorder error-path raising RuntimeError mid-turn | accept | begin_batch/end_batch RuntimeError on out-of-order invocation surfaces a planner bug loudly (preferable to silent state corruption); the scheduler in T2-03 guards each call with `if recorder is not None:` and never calls outside a `begin_iteration` scope |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_session_roundtrip.py tests/harness/test_recorder.py -x -q` passes
- BatchRecord dataclass at `voss/harness/session.py`; 6 fields exactly per D-09
- IterationRecord gains `batches: list[BatchRecord] = field(default_factory=list)` additive field
- RunRecorder.begin_batch + end_batch methods present; 3 error paths tested
- Pre-T2 fixture (no "batches" key on disk) loads with empty batches list
- Round-trip preserves 2 BatchRecord entries with all field values intact
</verification>

<success_criteria>
- BatchRecord dataclass exists in session.py with the locked 6-field set
- IterationRecord.batches additive field defaults to [] (additive guarantee)
- RunRecorder.begin_batch + end_batch are passive append+patch methods that nest inside the current iteration scope
- All 3 error paths raise RuntimeError with clear messages
- T1 recorder/session tests still pass (no regression)
</success_criteria>

<output>
Create `.planning/phases/T2-parallel-tools-multi-edit/T2-01-SUMMARY.md` when done with: exact line numbers of BatchRecord class + IterationRecord.batches field + begin_batch/end_batch methods; confirmation that pre-T2 fixture loads with empty batches; pytest output showing all 15 tests passing.
</output>
