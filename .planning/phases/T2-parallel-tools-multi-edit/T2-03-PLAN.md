---
phase: T2-parallel-tools-multi-edit
plan: 03
type: execute
wave: 2
depends_on: [T2-01, T2-02]
files_modified:
  - voss/harness/agent.py
  - tests/harness/test_partition_scheduler.py
  - tests/harness/test_permissions.py
autonomous: true
requirements: [PAR-01, PAR-02, PAR-06]
must_haves:
  truths:
    - "_run_step_loop is rewritten as a one-pass partition scheduler that walks plan.steps left-to-right, grouping consecutive is_mutating=False steps into a batch, flushing on every mutating step as a singleton"
    - "Read batches dispatch via asyncio.gather(*coros, return_exceptions=True) bounded by asyncio.Semaphore(get_config().max_parallel_reads)"
    - "Author order is preserved: a read step never executes before a write authored earlier in plan.steps; reads after a write run in the NEXT batch, never hoisted"
    - "Partition-time invariant: every step in a multi-step batch has ToolEntry.is_mutating == False; violation raises BatchInvariantError"
    - "BatchInvariantError class is defined in voss/harness/agent.py as a standalone Exception subclass (D-18; not a domain hierarchy per RESEARCH.md A1)"
    - "Per-step PermissionGate.check still fires for EVERY step including those inside multi-step batches (preserves M1 D-06 / SPEC Constraint 7)"
    - "Multi-step batches emit one telemetry.emit('batch.start', ...) before dispatch and one telemetry.emit('batch.end', ...) after gather completion, with monotonic batch_index"
    - "Singletons (whether read or write) emit NO batch.start / batch.end events (Pattern 8 / SPEC PAR-06 line 67)"
    - "Multi-step batches invoke recorder.begin_batch + recorder.end_batch when recorder is not None; singletons do NOT invoke either"
    - "Per-step tool.call and tool.result events are PRESERVED unchanged inside batches (M2 schema invariant)"
    - "Return contract preserved: _run_step_loop returns list[str] of length len(plan.steps) in author order; failed slots contain '<error: ...>' strings (never None)"
    - "Outer CancelledError propagation cancels in-flight sibling read coros via asyncio.gather cancel-propagation (no manual task.cancel plumbing)"
    - "Semaphore is per-batch (created at batch entry, GC'd after gather returns); not process-wide and not module-global per D-17"
    - "_run_turn_exec gains an except BatchInvariantError handler that finalizes the recorder with exit_reason='batch-invariant' (additive 5th value joining T1's done|max-iter|budget|interrupt)"
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "_run_step_loop rewrite + _dispatch_read_batch + _dispatch_singleton + _invoke_step_with_gate helpers + BatchInvariantError class"
      contains: "class BatchInvariantError\\|_dispatch_read_batch\\|_dispatch_singleton"
    - path: "voss/harness/agent.py"
      provides: "_run_turn_exec except BatchInvariantError handler with exit_reason='batch-invariant' finalize"
      contains: "except BatchInvariantError\\|exit_reason=\"batch-invariant\""
    - path: "tests/harness/test_partition_scheduler.py"
      provides: "Partition fixture tests (read/write/read/read), gather concurrency observation, BatchInvariantError synthetic, semaphore cap enforcement, telemetry+recorder wiring"
      contains: "test_partition_read_write_read_read\\|test_batch_invariant\\|test_semaphore_cap"
    - path: "tests/harness/test_permissions.py"
      provides: "Per-step PermissionGate.check still fires once-per-step inside multi-step batches"
      contains: "test_per_step_check_preserved"
  key_links:
    - from: "voss/harness/agent.py:_run_step_loop"
      to: "voss_runtime.get_config().max_parallel_reads"
      via: "cap value read at run start; passed into asyncio.Semaphore"
      pattern: "get_config\\(\\)\\.max_parallel_reads"
    - from: "voss/harness/agent.py:_run_step_loop"
      to: "voss/harness/recorder.py:RunRecorder.begin_batch"
      via: "called from _dispatch_read_batch when batch_index is not None and recorder is not None"
      pattern: "recorder\\.begin_batch"
    - from: "voss/harness/agent.py:_run_step_loop"
      to: "voss/harness/telemetry.py:emit"
      via: "telemetry.emit('batch.start', ...) / ('batch.end', ...) on multi-step batches only"
      pattern: "batch\\.(start|end)"
    - from: "voss/harness/agent.py:_run_turn_exec"
      to: "voss/harness/recorder.py:RunRecorder.finalize"
      via: "except BatchInvariantError finalizes with exit_reason='batch-invariant'"
      pattern: "exit_reason=\"batch-invariant\""
---

<objective>
Rewrite `_run_step_loop` (`voss/harness/agent.py:507`) as a one-pass author-
order partition scheduler that runs read-only step batches in parallel
(bounded by `asyncio.Semaphore(max_parallel_reads)`) and keeps mutating
singletons strictly serial. Land `BatchInvariantError` at the partition-time
invariant boundary. Wire `batch.start` / `batch.end` telemetry events and
`RunRecorder.begin_batch` / `end_batch` calls for multi-step batches only.
Add `_run_turn_exec` exception handler that surfaces `BatchInvariantError`
as `exit_reason="batch-invariant"` (5th additive enum value).

Purpose: SPEC PAR-01 (partition scheduler), PAR-02 (BatchInvariantError +
preserved per-step gate), and PAR-06 (telemetry+recorder wiring) all
converge on the scheduler rewrite. This plan covers all three because the
scheduler is the single emission site for batch.start/end events and
recorder.begin_batch/end_batch calls; splitting them would require
re-touching agent.py.

This plan depends on T2-01 (BatchRecord schema + RunRecorder API) and T2-02
(get_config().max_parallel_reads). Both Wave 1 plans must complete before
this Wave 2 plan executes.

Output: agent.py rewrite with partition scheduler + BatchInvariantError +
batch telemetry/recorder wiring + exit_reason handler; partition tests
(ordering, gather concurrency, semaphore cap, invariant error); permissions
regression test confirming per-step gate fires inside batches.
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
@.planning/phases/T2-parallel-tools-multi-edit/T2-01-PLAN.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-02-PLAN.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-05-PLAN.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-06-PLAN.md
@voss/harness/agent.py
@voss/harness/tools.py
@voss/harness/permissions.py
@voss/harness/telemetry.py
@voss/harness/recorder.py
@voss/harness/session.py
</context>

<interfaces>
Inputs from T2-01 (Wave 1):
- `voss.harness.session.BatchRecord` dataclass (6 fields)
- `voss.harness.session.IterationRecord.batches: list[BatchRecord]` field
- `voss.harness.recorder.RunRecorder.begin_batch(batch_index, step_indices)`
- `voss.harness.recorder.RunRecorder.end_batch(wall_clock_ms, ok_count, err_count)`

Inputs from T2-02 (Wave 1):
- `voss_runtime.RuntimeConfig.max_parallel_reads: int` (default 8, range 1-32)
- `voss_runtime.get_config().max_parallel_reads` accessor

Inputs from T1-05/T1-06 (must have shipped before T2 executes):
- `_run_turn_exec` is a while-loop body wrapped in `try: ... except asyncio.CancelledError: ...`
- `RunRecord.exit_reason` accepts the enum values {"done", "max-iter", "budget", "interrupt"} as EXIT_REASONS frozenset
- T2 ADDS "batch-invariant" as the 5th value

Existing serial body at `voss/harness/agent.py:507-598` is the line-for-line
source for the refactored `_invoke_step_with_gate` helper. T2-PATTERNS.md
section "voss/harness/agent.py — rewrite _run_step_loop" contains the exact
code shape to lift; the planner translation is verbatim with two surgical
changes:
1. Drop the outer `for step in plan_steps:` and replace with the partition
   scheduler while-loop
2. Each helper returns `text: str` (or writes into `results[slot]`) instead
   of mutating a shared `results` list inside the for-body

Cancel discipline (D-06 / D-07):
- Outer CancelledError (from T1-06's `_run_turn_exec` task.cancel()) propagates
  into asyncio.gather automatically; in-flight read coros are cancelled
- DO NOT use `return_exceptions=True` for the gather inside the SCHEDULER
  in a way that swallows CancelledError. The pattern is: `_invoke_step_with_gate`
  catches `Exception` (NOT `BaseException`) so CancelledError still propagates,
  and the outer gather propagates CancelledError to siblings. PATTERNS.md
  has the exact body.
- `gather(*coros, return_exceptions=True)` is correct here because the
  swallowed-exception strings happen INSIDE _invoke_step_with_gate's
  `except Exception`; CancelledError is BaseException and skips that handler

Telemetry shape (PAR-06):
- batch.start data: {batch_index: int, step_indices: list[int], parallel_count: int}
- batch.end data: {batch_index: int, wall_clock_ms: int, ok_count: int, err_count: int}
- Per-step tool.call / tool.result events INSIDE batches UNCHANGED — same
  schema, same redaction, fire from _invoke_step_with_gate

EXIT_REASONS frozenset (T1-01 establishes):
- T2 extends to include "batch-invariant" (5th value) — extend the frozenset
  in session.py (where T1-01 defined it) OR validate locally in this plan's
  finalize call. PATTERNS.md notes the additive enum extension. Read session.py
  to locate the frozenset and add "batch-invariant" to its body.

NullRenderer for tests:
- Tests need a Renderer stub with show_tool_call() as a no-op. Use the existing
  pattern from T1 tests (likely `tests/harness/conftest.py:NullRenderer` after
  T1-05 lifted it). If not present, create a minimal class in this plan's
  test file with show_tool_call(*a, **kw): pass.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Partition scheduler + BatchInvariantError + _invoke_step_with_gate refactor</name>
  <files>voss/harness/agent.py, tests/harness/test_partition_scheduler.py, tests/harness/test_permissions.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (PAR-01 + PAR-02 acceptance criteria, Constraints 1, 7, 8)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md (D-04, D-06, D-07, D-17, D-18)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (sections: "rewrite _run_step_loop", "BatchInvariantError", Pattern 1, Pattern 2, Pattern 3)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md (Patterns 1-3, Code Examples 1-2, Pitfalls 1-4 + 9)
    - voss/harness/agent.py (lines 1-50 for imports; 507-598 for current _run_step_loop body; T1-05-rewritten _run_turn_exec body — locate via `grep -n "_run_turn_exec\|_run_step_loop\|except asyncio.CancelledError" voss/harness/agent.py`)
    - voss/harness/tools.py (ToolEntry dataclass at line 14, is_mutating field)
    - voss/harness/permissions.py (lines 145-185: PermissionGate dataclass + check method)
    - voss/harness/session.py (EXIT_REASONS frozenset added by T1-01; locate via `grep -n "EXIT_REASONS\|exit_reason" voss/harness/session.py`)
    - voss/harness/telemetry.py (emit signature at lines 150-183; redact_tool_args at 87-112)
    - tests/harness/conftest.py if exists (NullRenderer + FakeStreamingProvider after T1)
  </read_first>
  <behavior>
    PARTITION CORRECTNESS:
    - Plan steps `[read_A, write_B, read_C, read_D]` produce execution order: A finishes before B starts; B finishes before C and D start; C and D may interleave (parallel)
    - Plan steps `[read_A, read_B, read_C]` (all reads) produce a single 3-step batch; all three may interleave
    - Plan steps `[write_A, write_B, write_C]` (all writes) produce 3 singleton dispatches in author order; A finishes before B, B before C
    - Plan steps `[read_A, write_B, read_C]` (read alone between writes) produces 3 separate batches: [A] (singleton), [B] (singleton), [C] (singleton) — NO multi-step batches
    - Plan steps `[]` (empty) returns `[]` immediately
    - Plan steps with an unregistered tool name → that slot's result is "<error: unknown tool 'X'>"; surrounding reads in same partition still execute

    SEMAPHORE / CONCURRENCY:
    - With max_parallel_reads=2 and a 6-read batch where each tool awaits asyncio.sleep(0.05), peak in-flight count never exceeds 2 (measured via a counter inside the stub tool that increments on enter, decrements on exit)
    - With max_parallel_reads=8 and a 6-read batch, peak in-flight is 6 (all start ~simultaneously)
    - Author order in results array: result[i] corresponds to plan_steps[i], regardless of interleaving

    PERMISSION GATE PRESERVATION:
    - For plan steps `[read_A, read_B, read_C]`, PermissionGate.check is invoked exactly 3 times (once per step) even though the 3 reads run inside one parallel batch (test_permissions.py:test_per_step_check_preserved)
    - For plan steps `[write_A, write_B]`, PermissionGate.check is invoked exactly 2 times
    - The gate's prompt_fn (when injected for tests) sees each step's args (no caching, no skipping)

    BATCH INVARIANT:
    - _dispatch_read_batch invoked with a multi-step batch containing a mutating step (planted synthetically by bypassing the partitioner) raises BatchInvariantError("step 'X' in multi-step batch is mutating or unregistered")
    - _dispatch_read_batch with single-step batch (len=1) does NOT check the invariant (singletons are exempt — read or write both allowed)
    - The normal partition path never produces a multi-step batch with a mutating step (the inner-while-loop break excludes mutating tools)

    RETURN CONTRACT:
    - _run_step_loop returns list[str] of length len(plan.steps)
    - Slot i corresponds to plan.steps[i] (author order)
    - Tool exception → slot contains "<error: {exc}>" (per existing convention)
    - Permission denial → slot contains "<denied: {why}>"
    - Successful tool → slot contains str(tool_result)
    - No slot is None

    TELEMETRY EVENTS (PAR-06):
    - Multi-step read batch [A, B, C, D] emits exactly ONE batch.start with parallel_count=4 and batch_index=0; exactly ONE batch.end with batch_index=0
    - Singleton (write or single read) emits ZERO batch.start / batch.end events
    - Per-step tool.call events still fire for every step inside batches (4 tool.call events for a 4-read batch)
    - Multiple multi-step batches in one iteration: batch_index is monotonic (0, 1, 2)
    - batch.end data includes wall_clock_ms (int > 0 for any sleeping coros), ok_count (=N on all-pass), err_count (=0 on all-pass)
    - Mixed pass/fail batch: ok_count + err_count == len(steps); err_count counts slots whose result string starts with "<error:" or "<denied:"

    RECORDER WIRING:
    - For multi-step batches with recorder is not None, recorder.begin_batch is called once before dispatch and recorder.end_batch once after gather; the IterationRecord.batches list grows by 1
    - For singletons OR when recorder is None, neither begin_batch nor end_batch is called
    - begin_batch's step_indices argument equals the positional indices of the batch's steps in plan.steps (e.g., [2, 3] for steps starting at index 2)
    - end_batch's wall_clock_ms, ok_count, err_count match the telemetry batch.end data values exactly (one source of truth)

    CANCELLATION DISCIPLINE:
    - Outer asyncio.Task wrapping _run_step_loop, cancelled mid-batch via task.cancel(), propagates CancelledError; in-flight read coros also receive cancellation (asyncio.gather propagates cancel to children); the partial results list contains "<error: ...>" or pre-set strings for completed slots; the calling _run_turn_exec catches CancelledError per T1-06

    EXIT REASON HANDLER:
    - _run_turn_exec gains an `except BatchInvariantError as e:` clause (sibling to T1-06's except CancelledError) that:
      a. Surfaces the error message via renderer (best-effort try/except)
      b. Calls rec.finalize(cwd, cost_usd=..., exit_reason="batch-invariant")
      c. Calls telemetry.note_turn(..., outcome="batch-invariant", exit_reason="batch-invariant")
      d. Re-raises or returns a TurnResult with the failure surfaced (planner matches T1-06's pattern; if T1-06 re-raises CancelledError, this handler re-raises BatchInvariantError; if T1-06 returns a TurnResult, mirror)
    - session.py EXIT_REASONS frozenset includes "batch-invariant" (additive 5th value)
  </behavior>
  <action>
    Edit `voss/harness/session.py`:

    Locate the EXIT_REASONS frozenset (added by T1-01). Add "batch-invariant"
    as the 5th value:
    ```
    EXIT_REASONS = frozenset({"done", "max-iter", "budget", "interrupt", "batch-invariant"})
    ```

    Edit `voss/harness/agent.py`:

    1. Imports (top of file):
       - `asyncio` is already imported (line ~10)
       - `time` already imported (line ~11)
       - `get_config` already imported via voss_runtime (line ~18-23)
       - Add `from voss.harness.session import BatchRecord` if not already
         imported through IterationRecord's import chain (check via grep)

    2. Add `BatchInvariantError` class near the top of the file, after the
       imports block and before the existing classes/functions:
       ```
       class BatchInvariantError(Exception):
           """Raised when a multi-step batch contains a mutating step.

           Indicates a planner bug or partitioner regression. Surfaces in
           RunRecord.exit_reason = 'batch-invariant' (additive enum value
           joining T1's done|max-iter|budget|interrupt).
           """
       ```
       Standalone Exception subclass per D-18 + RESEARCH.md A1 (NOT a domain
       hierarchy; mirrors `voss/harness/sandbox.py:25` SandboxError shape).

    3. Refactor the body of the current `_run_step_loop` (lines ~507-598)
       into three helpers + a new scheduler body. Lift the per-step
       dispatch into `_invoke_step_with_gate(step, tools, gate, renderer,
       recorder) -> str` (PATTERNS.md has the verbatim body). The function
       returns the result string; raises only on BaseException (e.g.
       CancelledError); swallows regular Exception into "<error: {exc}>"
       strings (existing M1 behavior preserved).

       Add `_dispatch_singleton(*, step, step_index, tools, gate, renderer,
       recorder, results) -> None` that calls _invoke_step_with_gate and
       writes the result into results[step_index]. NO batch.start /
       batch.end emission. NO recorder.begin_batch / end_batch call.

       Add `_dispatch_read_batch(*, steps, step_indices, tools, gate,
       renderer, recorder, results, cap, batch_index) -> None`:
       - If len(steps) > 1 AND batch_index is not None: enforce the
         partition invariant (raise BatchInvariantError if any step is
         mutating or unregistered)
       - Create asyncio.Semaphore(cap) at batch entry (per-batch scope; D-17)
       - Record t0 = time.perf_counter()
       - If batch_index is not None: emit batch.start telemetry +
         recorder.begin_batch (when recorder is not None)
       - Build N coroutines each wrapped in `async with sem:` and
         _invoke_step_with_gate; results[slot] = await ...
       - await asyncio.gather(*coros, return_exceptions=True)
       - Compute ok_count by counting slots NOT starting with "<error:" or "<denied:"; err_count = len - ok_count
       - If batch_index is not None: emit batch.end telemetry +
         recorder.end_batch (when recorder is not None)

       Rewrite `_run_step_loop` body (replacing the existing for-loop):
       ```
       async def _run_step_loop(plan_steps, tools, permissions, renderer,
                                 *, recorder=None) -> list[str]:
           gate = permissions or PermissionGate(auto_yes=True)
           results: list[str | None] = [None] * len(plan_steps)
           cap = get_config().max_parallel_reads
           batch_index = 0
           i = 0
           while i < len(plan_steps):
               j = i
               while j < len(plan_steps):
                   entry = tools.get(plan_steps[j].name)
                   if entry is None or entry.is_mutating:
                       break
                   j += 1
               if j > i:
                   multi_step = (j - i) > 1
                   await _dispatch_read_batch(
                       steps=plan_steps[i:j],
                       step_indices=list(range(i, j)),
                       tools=tools, gate=gate, renderer=renderer,
                       recorder=recorder, results=results, cap=cap,
                       batch_index=batch_index if multi_step else None,
                   )
                   if multi_step:
                       batch_index += 1
                   i = j
               else:
                   await _dispatch_singleton(
                       step=plan_steps[i], step_index=i,
                       tools=tools, gate=gate, renderer=renderer,
                       recorder=recorder, results=results,
                   )
                   i += 1
           return [r if r is not None else "<error: missing result>" for r in results]
       ```

    4. In `_run_turn_exec`, add `except BatchInvariantError as e:` AS A
       SIBLING to T1-06's `except asyncio.CancelledError:` (NOT nested,
       NOT inside the cancel handler). Handler body, modeled on T1-06's
       cancel handler shape:
       ```
       except BatchInvariantError as e:
           # Surface to renderer best-effort
           try:
               renderer.stream_delta(f"\n[error: batch-invariant: {e}]\n")
               renderer.finalize_stream(role="system", confidence=None,
                                          cost_usd=None, timestamp=None)
           except Exception:  # noqa: BLE001
               pass
           run = rec.finalize(cwd, cost_usd=total_cost_usd,
                                exit_reason="batch-invariant")
           telemetry.note_turn(cost_usd=total_cost_usd,
                                outcome="batch-invariant",
                                iteration_count=len(all_iter_records),
                                exit_reason="batch-invariant",
                                total_tokens=total_prompt_tokens + total_completion_tokens)
           raise
       ```
       If T1-06's CancelledError handler RETURNS a TurnResult instead of
       re-raising, mirror that pattern (read T1-06-SUMMARY.md if it exists
       to confirm the post-handler return shape). The exit_reason wiring
       is the load-bearing part; the surface mechanism follows T1-06.

    Write `tests/harness/test_partition_scheduler.py`. PATTERNS.md
    has the test pattern in section "tests/harness/test_step_loop_partition.py
    (NEW)". Use the autouse fixture `_config` that resets and configures
    RuntimeConfig per test.

    Required tests (at minimum, one per behavior section above):
    - test_partition_read_write_read_read (ordering; A < B < C, A < B < D)
    - test_partition_all_reads_one_batch (3 reads, one batch, interleave allowed)
    - test_partition_all_writes_serial (3 writes, serial)
    - test_partition_read_alone_between_writes (3 singletons, no multi-step)
    - test_partition_empty_steps (returns [])
    - test_partition_unknown_tool (slot contains "<error: unknown tool ...>")
    - test_semaphore_cap_enforced (peak in-flight <= cap; instrument via a counter on the stub tool)
    - test_author_order_preserved_in_results (parallel execution but results in author order)
    - test_batch_invariant_raises (synthetic mutating-in-batch via direct _dispatch_read_batch call)
    - test_singleton_skips_invariant_check (single mutating step does NOT raise)
    - test_telemetry_multi_step_emits_batch_start_end (spy on telemetry.emit; assert 1 batch.start + 1 batch.end with monotonic indices)
    - test_telemetry_singleton_emits_no_batch_wrappers
    - test_telemetry_per_step_events_preserved_inside_batches (tool.call + tool.result still fire per step)
    - test_recorder_begin_batch_called_for_multi_step (capture begin_batch/end_batch calls via a recorder spy)
    - test_recorder_no_begin_batch_for_singleton
    - test_exit_reason_batch_invariant_finalizes_recorder (full _run_turn_exec path; cancel injected via a stub provider+plan; assert run.exit_reason == "batch-invariant")
    - test_return_contract_length_and_strings (every slot is a str, never None; failed slots start with "<error:" or "<denied:")
    - test_cancellation_propagates_to_in_flight_reads (outer task.cancel() while a 4-read batch is mid-flight; asyncio.gather propagates cancel; in-flight coros end in cancelled state)

    Use FakeStreamingProvider from T1's conftest (lifted in T1-07) for the
    full _run_turn_exec test. Use plain @tool decorators with asyncio.sleep
    stubs for the partition unit tests.

    Edit `tests/harness/test_permissions.py` (extend the existing file):
    Add `test_per_step_check_preserved`. Inject a Recording prompt_fn into
    PermissionGate(auto_yes=False, mode="edit") that appends to a list each
    call. Run _run_step_loop with `[read_A, read_B, read_C]` (all
    is_mutating=False with mode="edit" gate). Assert exactly 3 invocations.
    Also run with `[write_A, write_B]` (is_mutating=True) and assert 2
    invocations. The point: parallel dispatch does NOT cache or skip
    gate.check.

    Use careful imports: BatchInvariantError must be importable from
    voss.harness.agent. EXIT_REASONS extension is tested by attempting
    RunRecord(..., exit_reason="batch-invariant") and asserting it does
    NOT raise.

    Do NOT modify PermissionGate. Do NOT modify telemetry.emit. Do NOT
    change ToolEntry. Do NOT modify renderer or recorder beyond what
    T2-01 already shipped.

    Implementation note on cancellation semantics in tests
    (per RESEARCH.md Pitfall 3): when a stub tool itself raises
    CancelledError mid-batch, the gather with return_exceptions=True
    captures it as a result. The slot's result string should be
    "<error: CancelledError>" or similar (this is the "inner cancel"
    case). The "outer cancel" case (task wrapping _run_turn_exec is
    cancelled) propagates through gather to all in-flight coros.
    Distinguish these two paths in the tests.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_partition_scheduler.py tests/harness/test_permissions.py::test_per_step_check_preserved -x -q 2>&amp;1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^class BatchInvariantError" voss/harness/agent.py` returns 1 match
    - source assertion: `grep -n "_dispatch_read_batch\|_dispatch_singleton\|_invoke_step_with_gate" voss/harness/agent.py` returns >= 6 matches (3 defs + >= 3 call sites)
    - source assertion: `grep -nE "asyncio\.Semaphore\(.*cap" voss/harness/agent.py` returns >= 1 match (per-batch scope)
    - source assertion: `grep -nE "asyncio\.gather\(.*return_exceptions=True" voss/harness/agent.py` returns >= 1 match
    - source assertion: `grep -nE 'telemetry\.emit\("batch\.(start|end)"' voss/harness/agent.py` returns >= 2 matches
    - source assertion: `grep -n "recorder\.begin_batch\|recorder\.end_batch" voss/harness/agent.py` returns >= 2 matches
    - source assertion: `grep -F 'exit_reason="batch-invariant"' voss/harness/agent.py` returns >= 2 matches (finalize + note_turn)
    - source assertion: `grep -F 'except BatchInvariantError' voss/harness/agent.py` returns 1 match (sibling to T1-06's except CancelledError)
    - source assertion: `grep -F "batch-invariant" voss/harness/session.py` returns >= 1 match (EXIT_REASONS frozenset extension)
    - partition assertion: pytest test_partition_read_write_read_read PASSES with the ordering invariant A < B < C and A < B < D
    - semaphore assertion: pytest test_semaphore_cap_enforced PASSES with peak in-flight <= cap on a 6-read batch with cap=2
    - invariant assertion: pytest test_batch_invariant_raises PASSES with BatchInvariantError raised on synthetic mutating-in-batch
    - telemetry assertion: pytest test_telemetry_multi_step_emits_batch_start_end PASSES with monotonic batch_index
    - singleton assertion: pytest test_telemetry_singleton_emits_no_batch_wrappers PASSES with zero batch.* events for singletons
    - permission assertion: pytest test_per_step_check_preserved PASSES (3 reads → 3 gate invocations; 2 writes → 2 invocations)
    - cancellation assertion: pytest test_cancellation_propagates_to_in_flight_reads PASSES with no leaked tasks
    - regression assertion: `uv run pytest tests/harness/test_recorder.py tests/harness/test_session_roundtrip.py tests/harness/test_permissions.py -x -q` passes (no T2-01 or M1 regression)
    - regression assertion: `uv run pytest tests/harness/ -k "agent or recorder or session or permissions or partition" -x -q` passes
    - test command: `uv run pytest tests/harness/test_partition_scheduler.py tests/harness/test_permissions.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>_run_step_loop rewritten as one-pass partition scheduler; BatchInvariantError defined; _dispatch_read_batch + _dispatch_singleton + _invoke_step_with_gate helpers extracted; batch.start/end telemetry + recorder.begin_batch/end_batch wired for multi-step batches only; per-step gate fires inside batches; _run_turn_exec except BatchInvariantError handler with exit_reason="batch-invariant" finalize; EXIT_REASONS extended; ~18 partition tests + 1 permissions regression test pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| plan.steps (LLM-author input) → scheduler dispatch | Partitioner classifies by `ToolEntry.is_mutating` data field, not by tool-name pattern (M1 D-06 invariant); a misclassified tool slipping into a multi-step batch must be a hard error, not a silent degrade |
| outer asyncio.Task → gather → in-flight read coros | CancelledError propagation must reach in-flight siblings within T1's 100ms finalize budget |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T2-03-01 | Tampering | partition scheduler dispatching a mutating tool inside a parallel batch (silent mutation race) | mitigate | Partition-time invariant in `_dispatch_read_batch` raises `BatchInvariantError` when len(steps) > 1 AND any step has is_mutating=True or is unregistered; `_run_turn_exec` finalizes with exit_reason="batch-invariant" (visible failure, not silent degradation per Pitfall 4) |
| T-T2-03-02 | Tampering | tool name pattern matching used for classification | mitigate | Partitioner reads `ToolEntry.is_mutating` ONLY (M1 D-06 invariant; SPEC Constraint 8); the test `test_partition_classifies_by_is_mutating_not_name` plants a tool named "fs_read_evil" with is_mutating=True and confirms it's treated as mutating |
| T-T2-03-03 | Denial of Service | unbounded concurrent reads exhaust file handles / network connections | mitigate | `asyncio.Semaphore(get_config().max_parallel_reads)` caps in-flight at 8 by default; config knob enforces range 1-32 (T2-02 PAR-05) |
| T-T2-03-04 | Denial of Service | cancellation doesn't reach in-flight read coros within budget | mitigate | `asyncio.gather` propagates outer Cancel to all in-flight tasks automatically (Python stdlib semantics; CITED in RESEARCH.md "Don't Hand-Roll" table); T1's <100ms finalize budget honored via the same propagation chain |
| T-T2-03-05 | Information Disclosure | per-step tool.call / tool.result events inside parallel batches leak unredacted args | mitigate | _invoke_step_with_gate calls `telemetry.redact_tool_args(dict(step.args))` identically to the existing serial path (PATTERNS.md verbatim); no new redaction surface needed |
| T-T2-03-06 | Repudiation | recorder.begin_batch/end_batch called out of order leaves orphan BatchRecord with zero counts | mitigate | T2-01 enforces begin_batch raises RuntimeError outside iteration scope and end_batch raises if no matching begin_batch; scheduler always pairs them; tests confirm |
| T-T2-03-SC | Tampering | npm/pip/cargo installs | accept | No new third-party packages introduced in this plan (RESEARCH.md "Package Legitimacy Audit" — none; all primitives are stdlib or already-pinned dev deps) |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_partition_scheduler.py tests/harness/test_permissions.py -x -q` passes
- `grep -nE "^class BatchInvariantError" voss/harness/agent.py` returns 1 match
- `grep -nE 'telemetry\.emit\("batch\.(start|end)"' voss/harness/agent.py` returns >= 2 matches
- `grep -F 'except BatchInvariantError' voss/harness/agent.py` returns 1 match
- `grep -F "batch-invariant" voss/harness/session.py` returns >= 1 match
- Partition `[read_A, write_B, read_C, read_D]` → 3 batches in order: singleton [A], singleton [B], multi-step [C, D]
- Semaphore caps peak in-flight at the configured value
- BatchInvariantError raised on synthetic mutating-in-batch
- Per-step PermissionGate.check fires once per step inside batches
- Telemetry emits batch.start/end ONLY for multi-step batches
- Recorder begin_batch/end_batch wired only when batch_index is not None AND recorder is not None
- _run_turn_exec finalizes with exit_reason="batch-invariant" on BatchInvariantError
- No T1 regression in agent/recorder/session/permissions test suite
</verification>

<success_criteria>
- _run_step_loop is an order-preserving partition scheduler (PAR-01 acceptance: [A, B, C, D] → [A], [B], [C, D])
- asyncio.gather + Semaphore(cap) bounds parallel dispatch (PAR-01 acceptance: gather observed via concurrent timestamps; PAR-05 acceptance: cap=2 enforces peak in-flight = 2)
- BatchInvariantError raised on mutating-in-batch (PAR-02 acceptance: synthetic test passes)
- Per-step PermissionGate.check still fires for every step (PAR-02 acceptance: 3 reads → 3 invocations)
- batch.start / batch.end telemetry emitted ONLY for multi-step batches (PAR-06 acceptance)
- IterationRecord.batches populated via recorder API (PAR-06 acceptance: RunRecord.batches round-trips)
- exit_reason="batch-invariant" is the 5th additive enum value; _run_turn_exec finalizes correctly
- No T1 regression (recorder, session, permissions tests still green)
</success_criteria>

<output>
Create `.planning/phases/T2-parallel-tools-multi-edit/T2-03-SUMMARY.md` when done with: line ranges of BatchInvariantError, _run_step_loop rewrite, _dispatch_read_batch, _dispatch_singleton, _invoke_step_with_gate, and the new except BatchInvariantError handler; spec acceptance criteria mapping (PAR-01 × 4, PAR-02 × 2, PAR-06 × 4) → test function names; concrete pytest output showing all partition + permissions tests passing.
</output>
