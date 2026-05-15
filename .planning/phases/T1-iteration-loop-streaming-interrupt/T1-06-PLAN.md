---
phase: T1-iteration-loop-streaming-interrupt
plan: 06
type: execute
wave: 4
depends_on: [T1-05]
files_modified:
  - voss/harness/agent.py
  - voss/harness/tui/app.py
autonomous: true
requirements: [ITER-04, ITER-06]
must_haves:
  truths:
    - "VossTUIApp.active_turn_task: Optional[asyncio.Task] is set when a turn starts and cleared (or left as a completed task) when the turn ends"
    - "VossTUIApp.action_interrupt calls active_turn_task.cancel() iff the task exists and is not done"
    - "_run_turn_exec wraps its loop body in try/except asyncio.CancelledError that sets exit_reason='interrupt', finalizes the recorder with that reason, surfaces 'interrupted' in the TurnView, and re-raises CancelledError"
    - "Exit reason precedence: if cancel arrives during a stream that is already past max-iter or budget exhaustion semantically, exit_reason is 'interrupt', not 'max-iter' or 'budget'"
    - "Interrupt-to-recorder-finalize latency is < 100ms in a measured test"
    - "telemetry.note_turn carries exit_reason='interrupt' on cancel paths"
  artifacts:
    - path: "voss/harness/tui/app.py"
      provides: "VossTUIApp.active_turn_task attribute + filled action_interrupt body"
      contains: "active_turn_task"
    - path: "voss/harness/agent.py"
      provides: "try/except asyncio.CancelledError wrapping _run_turn_exec's loop body"
      contains: "asyncio.CancelledError"
  key_links:
    - from: "voss/harness/tui/app.py:VossTUIApp.action_interrupt"
      to: "voss/harness/agent.py:_run_turn_exec"
      via: "task.cancel() propagates CancelledError into the active stream() / iteration body"
      pattern: "active_turn_task\\.cancel\\(\\)"
    - from: "voss/harness/agent.py:_run_turn_exec"
      to: "voss/harness/recorder.py:RunRecorder.finalize"
      via: "called from inside the CancelledError handler with exit_reason='interrupt'"
      pattern: "rec\\.finalize\\(.*exit_reason=\"interrupt\""
---

<objective>
Wire interrupt cancellation: TUI tracks the active turn's asyncio.Task,
action_interrupt cancels it, _run_turn_exec catches CancelledError and
finalizes the recorder cleanly with exit_reason="interrupt", with
documented precedence over max-iter and budget.

Purpose: SPEC ITER-04 acceptance says "Test triggers action_interrupt
mid-stream; RunRecord.exit_reason == 'interrupt' and recorder is
finalized within 100ms of the interrupt call; no asyncio task leak after
the cancel." CONTEXT.md "Recorder finalization on cancel" locks the
four-step handler: set iter exit_reason, finalize, surface text, re-raise.
"Exit reason precedence" in CONTEXT.md "Specifics" requires interrupt
to win over max-iter in the rare race.

Output: VossTUIApp gains active_turn_task tracking + a working
action_interrupt; _run_turn_exec gains the CancelledError handler;
TextualRenderer (or the cli.py boot) registers the task on the app when
a turn starts.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md
@voss/harness/agent.py
@voss/harness/tui/app.py
@voss/harness/recorder.py
@voss/harness/session.py
</context>

<interfaces>
After T1-05, _run_turn_exec is a while-loop that:
- starts: rec = RunRecorder.start()
- enters: async with ContextScope(...) as ctx:
- loops: while iteration_index < max_iterations:
- ends: rec.finalize(cwd, cost_usd=total_cost_usd, exit_reason=exit_reason)

The cancel-points (locked in CONTEXT.md):
A. `async for event in provider.stream(...)` — natural CancelledError
   propagation; provider's `async with httpx.stream(...)` closes the
   connection cleanly
B. `await entry.invoke(**step.args)` inside _run_step_loop — natural
   CancelledError propagation
The handler placement: a single `try/except asyncio.CancelledError`
wrapping the entire `async with ContextScope(...): while ...` block,
INSIDE the function body, BEFORE the post-loop record_run / finalize
calls.

VossTUIApp current state:
- voss/harness/tui/app.py line 79: action_interrupt is `pass`
- No `active_turn_task` attribute today

Where the turn task is created: in cli.py the chat / do flow eventually
schedules `run_turn(...)` as an awaitable. The TUI mode runs it through
TextualRenderer; the headless mode just awaits directly. For TUI-mode
cancel to work, the App must hold a reference to the live Task. Pattern:
- Add `self.active_turn_task: Optional[asyncio.Task] = None` in __init__
- Expose `def register_turn_task(self, task: asyncio.Task) -> None:` that
  sets the attribute AND attaches a done_callback that clears it (cleared
  meaning set back to None) when the task finishes
- The caller (TextualRenderer wrapper or cli.py TUI launcher) wraps the
  `run_turn(...)` coroutine via `task = asyncio.create_task(run_turn
  (...)); app.register_turn_task(task)` before awaiting it
- Locate the call site: `grep -rn "run_turn\|create_task" voss/harness/
  | grep -i tui` — likely in cli.py around the TUI launch path or in
  textual_renderer.py

action_interrupt body (CONTEXT.md locked):
```python
def action_interrupt(self) -> None:
    task = self.active_turn_task
    if task is not None and not task.done():
        task.cancel()
```

_run_turn_exec CancelledError handler (CONTEXT.md Recorder finalization
on cancel locked):
1. Set the current open iteration's exit_reason = "interrupt"
2. Call rec.finalize(cwd, cost_usd=total_cost_usd, exit_reason=
   "interrupt") — this returns a RunRecord with exit_reason="interrupt"
3. Surface "interrupted" in the TurnView (renderer.show_interrupted()
   or renderer.finalize_stream(role="system", ...) with an interrupted
   message — pick the existing surface; if none exists, add a
   show_interrupted shim that defaults to a stream_delta("\n[interrupted]\n")
   + finalize_stream call)
4. Call telemetry.note_turn(cost_usd=total_cost_usd, outcome="interrupt",
   iteration_count=len(all_iter_records), exit_reason="interrupt")
5. Re-raise CancelledError so the task ends in cancelled state (asyncio
   convention: NEVER swallow CancelledError)

The "current open iteration" is the most recent record in rec._iterations
that has empty ended_at. If begin_iteration was called but end_iteration
was not (cancel happened mid-stream or mid-tool-dispatch), close it via
end_iteration with placeholder values: cost_usd=accumulated_so_far,
prompt_tokens=0, completion_tokens=0, tool_results=[any results so far],
exit_reason="interrupt". If begin_iteration was never called (cancel
arrived between iters), the iter list is empty and we just finalize the
record with exit_reason="interrupt".

Exit-reason precedence: per CONTEXT.md "Specifics" — interrupt wins over
max-iter. Implementation: the except CancelledError block runs BEFORE
the line that maps `if exit_reason is None: exit_reason = "max-iter"` in
T1-05's post-loop code, so when cancel fires the except block sets
exit_reason="interrupt" and returns/re-raises, never reaching the
fallthrough max-iter assignment. Document this in T1-06-SUMMARY.md.

Headless (non-TUI) cancel: cli.py `voss do` path doesn't have a TUI;
Ctrl-C delivers KeyboardInterrupt which asyncio translates to
CancelledError on the active task. The handler works the same way —
no separate path needed. Document this so the test plan covers both.
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: VossTUIApp.active_turn_task + action_interrupt body + register_turn_task helper</name>
  <files>voss/harness/tui/app.py, tests/harness/tui/test_app_interrupt.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-04 acceptance)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Interrupt + mid-iter cleanup section)
    - voss/harness/tui/app.py (entire file — find __init__, action_interrupt line 79)
    - tests/harness/tui/ (look for existing app tests — `ls tests/harness/tui/test_app*`)
  </read_first>
  <behavior>
    - VossTUIApp() instance has `active_turn_task` attribute defaulting to None
    - app.register_turn_task(task) sets self.active_turn_task = task and attaches a done_callback
    - When the registered task completes (naturally or via cancel), the done_callback runs and sets self.active_turn_task = None
    - app.action_interrupt() with active_turn_task = None is a no-op (does not raise)
    - app.action_interrupt() with a running (not-done) task calls task.cancel() and the task ends in a cancelled state
    - app.action_interrupt() with an already-done task is a no-op (does not call cancel())
    - Calling register_turn_task twice (without the first finishing) raises RuntimeError("active turn task already registered") OR overwrites with a warning — pick "raises RuntimeError" for safety; test asserts the raise
  </behavior>
  <action>
    Edit `voss/harness/tui/app.py`:

    1. In __init__, after `self.focused_turn_index: int | None = None`,
       add: `self.active_turn_task: Optional[asyncio.Task] = None`. Add
       `import asyncio` and `from typing import Optional` at the top if
       not already imported (asyncio likely not imported today — check
       `grep -n "^import asyncio\|^from typing" voss/harness/tui/app.py`).

    2. Add a method `register_turn_task(self, task: asyncio.Task) -> None:`:
       - If `self.active_turn_task is not None and not self.active_turn_task.done()`: raise RuntimeError("active turn task already registered")
       - Otherwise set self.active_turn_task = task and call
         `task.add_done_callback(self._clear_turn_task)`

    3. Add a method `_clear_turn_task(self, task: asyncio.Task) -> None:`
       that sets `self.active_turn_task = None` (the callback receives
       the task ref but we just blank the attribute).

    4. Replace `action_interrupt` body (line 79):
       ```
       task = self.active_turn_task
       if task is not None and not task.done():
           task.cancel()
       ```
       Remove the stale `# M9-04 wires interrupt to the running turn; M9-03 stub is a no-op.` comment and replace with a brief note pointing to T1.

    Write `tests/harness/tui/test_app_interrupt.py` with seven tests
    matching the seven behavior bullets. Use a real asyncio event loop
    (pytest-asyncio is presumably already a dep — `grep -n
    "pytest-asyncio" pyproject.toml`). Use asyncio.sleep-based fake
    tasks. Do not mount the full Textual App if it complicates fixtures;
    you can instantiate VossTUIApp() and test the methods directly
    without mounting (the methods don't depend on widget query).

    Do NOT modify any other action_* method. Do NOT modify __init__
    fields above the new active_turn_task line.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/tui/test_app_interrupt.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "active_turn_task\|register_turn_task\|_clear_turn_task" voss/harness/tui/app.py` returns >= 4 matches
    - source assertion: `grep -A3 "def action_interrupt" voss/harness/tui/app.py | grep -F "task.cancel()"` returns 1 match
    - source assertion: `grep -A3 "def action_interrupt" voss/harness/tui/app.py | grep -F "pass"` returns 0 matches (stub gone)
    - behavior assertion: all seven pytest behaviors pass
    - regression assertion: `uv run pytest tests/harness/tui/ -x -q` passes (no other action_* method broken)
    - test command: `uv run pytest tests/harness/tui/test_app_interrupt.py tests/harness/tui/ -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>VossTUIApp tracks the active turn's asyncio.Task; action_interrupt cancels it cleanly; register_turn_task / _clear_turn_task manage the lifecycle and prevent double-registration; tests cover all four state combinations (None, running, already-done, double-register).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: _run_turn_exec CancelledError handler + register from TUI launcher</name>
  <files>voss/harness/agent.py, voss/harness/cli.py, tests/harness/test_agent_interrupt.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-04 — 100ms latency criterion + "no asyncio task leak after the cancel" + Specifics "Exit reason precedence")
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Interrupt + mid-iter cleanup section + Recorder finalization on cancel — exact 5-step handler)
    - voss/harness/agent.py (after T1-05 — the new while-loop body and the line where exit_reason maps to final string)
    - voss/harness/recorder.py (after T1-01 — begin_iteration / end_iteration semantics for "close the most recent open iter")
    - voss/harness/cli.py — locate where run_turn is invoked from the TUI launch path. `grep -rn "run_turn\|asyncio.run\|create_task" voss/harness/cli.py` to find the TUI hook point.
    - voss/harness/tui/app.py (after Task 1 — register_turn_task signature)
  </read_first>
  <behavior>
    - Given a FakeStreamingProvider that emits TextDelta then awaits an
      asyncio.Event-controlled hang, calling task.cancel() on the
      _run_turn_exec task results in: (a) task ends in cancelled state,
      (b) provider.stream() exits via its async-context exit, (c) the
      recorder is finalized with exit_reason="interrupt" — testable via
      a side-effect hook on RunRecorder.finalize
    - Latency from task.cancel() to recorder.finalize() invocation is
      <= 100ms (measure with time.monotonic; allow generous slack for
      CI noise but assert <0.1s)
    - The finalized RunRecord has exit_reason == "interrupt"
    - asyncio.all_tasks() after the cancelled task settles does NOT
      include any leaked tasks attributable to the turn (assert by
      tracking task count delta)
    - telemetry.note_turn was called with kwargs including
      exit_reason="interrupt" and outcome="interrupt"
    - Precedence test: cancel arrives on iteration max_iterations
      (last possible iter). The handler runs first and sets exit_reason
      ="interrupt", NOT "max-iter". The finalized RunRecord has
      exit_reason == "interrupt".
    - Mid-iter cleanup: cancel arrives AFTER begin_iteration but BEFORE
      end_iteration. The handler invokes end_iteration on the most-recent
      open iter with exit_reason="interrupt" (so IterationRecord
      .ended_at is non-empty and IterationRecord.exit_reason ==
      "interrupt"). Verifiable via run.iterations[-1].
    - Between-iter cleanup: cancel arrives between iterations (after
      end_iteration but before the next begin_iteration). The handler
      finds no open iter and finalizes the RunRecord directly with
      exit_reason="interrupt". run.iterations is the closed list of
      completed iters.
    - CLI TUI launch path (voss/harness/cli.py) wraps the run_turn call
      in `asyncio.create_task` and calls `app.register_turn_task(task)`
      when the app is the active TUI surface. (Headless `voss do` path
      stays as a plain `await run_turn(...)` — Ctrl-C delivers
      KeyboardInterrupt which asyncio cancels naturally.)
  </behavior>
  <action>
    In `voss/harness/agent.py`:

    Add `import asyncio` at the top if not already imported (check via
    `grep -n "^import asyncio" voss/harness/agent.py`).

    Wrap the while-loop block introduced in T1-05 (the
    `async with ContextScope(...): while iteration_index < max_iterations: ...`
    section) in `try: ... except asyncio.CancelledError: ...`.

    Handler body — exact sequence per CONTEXT.md:

    ```
    except asyncio.CancelledError:
        # Step 1: close most recent open iter, if any, with interrupt reason
        open_iter = next(
            (ir for ir in reversed(rec._iterations) if not ir.ended_at),
            None,
        )
        if open_iter is not None:
            rec.end_iteration(
                plan=Plan(rationale="(interrupted)", steps=[], confidence=0.0, final_when_done=""),
                tool_results=[],
                cost_usd=0.0,
                prompt_tokens=0,
                completion_tokens=0,
                exit_reason="interrupt",
            )
        # Step 2: surface in the TurnView via renderer
        try:
            renderer.stream_delta("\n[interrupted]\n")
            renderer.finalize_stream(role="system", confidence=None, cost_usd=None, timestamp=None)
        except Exception:  # noqa: BLE001 — renderer may not be mounted in test
            pass
        # Step 3: finalize the record. exit_reason precedence: interrupt wins.
        run = rec.finalize(cwd, cost_usd=total_cost_usd, exit_reason="interrupt")
        # Step 4: telemetry
        telemetry.note_turn(
            cost_usd=total_cost_usd,
            outcome="interrupt",
            iteration_count=len(all_iter_records),
            exit_reason="interrupt",
            total_tokens=total_prompt_tokens + total_completion_tokens,
        )
        # Step 5: re-raise so task state is cancelled, not absorbed
        raise
    ```

    Place the `try:` immediately before `async with ContextScope(...)`
    and the `except asyncio.CancelledError:` immediately after the
    matching `# End ContextScope async-with` comment from T1-05 — i.e.,
    the post-loop final-string-build / record_run / finalize block STAYS
    OUTSIDE the try/except. Rationale: cancel during record_run (which
    is another provider call) should also trigger the handler; place
    record_run INSIDE the try block too.

    Reconsider placement: PUT the try at the same level as the existing
    rec = RunRecorder.start() — i.e., wrap from "rec = RunRecorder.start()"
    down through "return TurnResult(...)" in the try. The except handler
    closes the iter, finalizes, emits telemetry, and re-raises. This way
    cancel during ANY phase (stream, _run_step_loop, _record_run_call,
    finalize) is caught and produces a clean recorder entry.

    Locate the post-handler precedence assertion: the line
    `if exit_reason is None: exit_reason = "max-iter"` lives inside the
    try block, so cancel that arrives at iteration_index ==
    max_iterations - 1 right after the stream completes still goes
    through the except handler (which overwrites exit_reason to
    "interrupt"). DOCUMENT in the SUMMARY: "interrupt > max-iter
    precedence is enforced by source-order: the except clause is
    structurally below the cap-fallthrough but runtime-precedes via
    Python exception propagation."

    In `voss/harness/cli.py`:

    Locate the TUI launch path (search for `VossTUIApp(` and the call
    to `app.run_async()` or equivalent). The chat/turn loop inside the
    TUI eventually awaits run_turn. Wrap that await in:
    ```
    task = asyncio.create_task(run_turn(...args...))
    app.register_turn_task(task)
    try:
        result = await task
    finally:
        # done_callback on the app clears active_turn_task; no manual cleanup
        pass
    ```
    Confirm the exact placement by reading the file: there may be a
    helper like `_run_turn_in_tui` already; if so, wrap there. If the
    flow is deeply nested in a worker thread (Textual workers can run
    coroutines in a separate event loop via app.run_worker(...) — see
    `grep -n "run_worker\|call_from_thread" voss/harness/`), adapt the
    pattern: workers expose a handle that supports cancel(); wire the
    app.action_interrupt to call that handle's cancel.

    Write `tests/harness/test_agent_interrupt.py` covering the eight
    behavior bullets. Use a FakeStreamingProvider with an explicit
    asyncio.Event "release" gate the test can hold open then cancel
    around. Use asyncio.create_task + task.cancel(); await the task
    inside `with pytest.raises(asyncio.CancelledError):`.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_interrupt.py -x -q 2>&amp;1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "except asyncio.CancelledError" voss/harness/agent.py` returns >= 1 match in _run_turn_exec
    - source assertion: `grep -n "exit_reason=\"interrupt\"" voss/harness/agent.py` returns >= 2 matches (end_iteration + finalize + note_turn)
    - source assertion: `grep -n "register_turn_task" voss/harness/cli.py` returns >= 1 match (TUI launch wires the task)
    - latency assertion: pytest test_interrupt_finalize_latency completes asserting time.monotonic() delta < 0.1s
    - precedence assertion: pytest test_interrupt_precedence_over_max_iter asserts run.exit_reason == "interrupt" when cancel arrives at the cap iteration
    - leak assertion: pytest test_no_task_leak asserts asyncio.all_tasks() delta is 0 after cancel settles
    - behavior assertion: all eight pytest behaviors pass
    - regression assertion: `uv run pytest tests/harness/ -k "agent or recorder or session or tui" -x -q` passes (no break in T1-01/05 tests)
    - test command: `uv run pytest tests/harness/test_agent_interrupt.py tests/harness/ -k "agent or recorder or session or tui" -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>_run_turn_exec catches CancelledError, closes any open iter with exit_reason="interrupt", finalizes the record with exit_reason="interrupt", emits note_turn(outcome="interrupt", exit_reason="interrupt"), and re-raises; cli.py TUI launch registers the task on the app; interrupt precedence over max-iter is enforced by exception flow; latency <100ms in measured test.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/test_app_interrupt.py tests/harness/test_agent_interrupt.py -x -q` passes
- `grep -n "except asyncio.CancelledError" voss/harness/agent.py` >= 1 match
- `grep -A3 "def action_interrupt" voss/harness/tui/app.py | grep -F "task.cancel()"` 1 match
- All four exit_reasons (done, max-iter, budget, interrupt) reachable via dedicated test fixtures across T1-05 + T1-06 tests
- `uv run pytest tests/harness/ -k "agent or recorder or session or tui or provider_stream" -x -q` passes
</verification>

<success_criteria>
- action_interrupt cancels the active turn's asyncio.Task; the task ends in cancelled state
- _run_turn_exec's CancelledError handler closes the open iter, finalizes the recorder with exit_reason="interrupt", emits telemetry, and re-raises
- Latency from task.cancel() to recorder.finalize() < 100ms (measured)
- No asyncio task leak after cancel settles
- Exit reason precedence: interrupt > max-iter > budget > done (handler-precedes-fallthrough invariant)
- cli.py TUI launch path registers the task on the app so action_interrupt has something to cancel
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-06-SUMMARY.md` when done with: exact handler placement (line range in _run_turn_exec), TUI launch wiring point (cli.py function name), evidence of <100ms latency from the test run output, and any deviation from the 5-step handler spec.
</output>
