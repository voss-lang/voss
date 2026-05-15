---
phase: T1-iteration-loop-streaming-interrupt
plan: 06
type: execute
wave: 4
depends_on: [T1-05]
files_modified:
  - voss/harness/agent.py
  - voss/harness/tui/app.py
  - voss/harness/cli.py
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
    - "cli.py exposes a single helper `_run_turn_cancellable(coro, *, renderer)` that creates the asyncio.Task, registers it with the active TUI app (if any) via the renderer.app attribute, runs the loop until done, and propagates CancelledError. Both `do_cmd` (cli.py line 998) and `_run_repl` (cli.py line 1307) replace their `asyncio.run(run_turn(...))` calls with this helper."
  artifacts:
    - path: "voss/harness/tui/app.py"
      provides: "VossTUIApp.active_turn_task attribute + filled action_interrupt body + register_turn_task/_clear_turn_task helpers"
      contains: "active_turn_task"
    - path: "voss/harness/agent.py"
      provides: "try/except asyncio.CancelledError wrapping _run_turn_exec's loop body"
      contains: "asyncio.CancelledError"
    - path: "voss/harness/cli.py"
      provides: "_run_turn_cancellable(coro, *, renderer) helper + do_cmd/_run_repl call-site replacements"
      contains: "_run_turn_cancellable"
  key_links:
    - from: "voss/harness/tui/app.py:VossTUIApp.action_interrupt"
      to: "voss/harness/agent.py:_run_turn_exec"
      via: "task.cancel() propagates CancelledError into the active stream() / iteration body"
      pattern: "active_turn_task\\.cancel\\(\\)"
    - from: "voss/harness/agent.py:_run_turn_exec"
      to: "voss/harness/recorder.py:RunRecorder.finalize"
      via: "called from inside the CancelledError handler with exit_reason='interrupt'"
      pattern: "rec\\.finalize\\(.*exit_reason=\"interrupt\""
    - from: "voss/harness/cli.py:_run_turn_cancellable"
      to: "voss/harness/tui/app.py:VossTUIApp.register_turn_task"
      via: "extracts app from renderer.app (TextualRenderer attribute, see tui/renderer.py line 46-47) and registers the task"
      pattern: "register_turn_task"
---

<objective>
Wire interrupt cancellation: TUI tracks the active turn's asyncio.Task,
action_interrupt cancels it, _run_turn_exec catches CancelledError and
finalizes the recorder cleanly with exit_reason="interrupt", with
documented precedence over max-iter and budget. cli.py replaces both
of its `asyncio.run(run_turn(...))` call sites with a single new
helper `_run_turn_cancellable` that wires the task to the app via
the TextualRenderer.app attribute (set at construction time in
render.py line 93 / line 99) so action_interrupt can find it.

Purpose: SPEC ITER-04 acceptance says "Test triggers action_interrupt
mid-stream; RunRecord.exit_reason == 'interrupt' and recorder is
finalized within 100ms of the interrupt call; no asyncio task leak
after the cancel." CONTEXT.md "Recorder finalization on cancel" locks
the four-step handler: set iter exit_reason, finalize, surface text,
re-raise. "Exit reason precedence" in CONTEXT.md "Specifics" requires
interrupt to win over max-iter in the rare race.

Output: VossTUIApp gains active_turn_task tracking + a working
action_interrupt; _run_turn_exec gains the CancelledError handler;
cli.py gains `_run_turn_cancellable` helper and replaces 2 call sites.
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
@voss/harness/tui/renderer.py
@voss/harness/render.py
@voss/harness/cli.py
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
   connection cleanly (verified in T1-03)
B. `await entry.invoke(**step.args)` inside _run_step_loop — natural
   CancelledError propagation (existing behavior)
The handler placement: a single `try/except asyncio.CancelledError`
wrapping the entire `rec = RunRecorder.start()` through the
post-ContextScope finalize + return block. This catches cancel during
ANY phase (stream, _run_step_loop, _record_run_call, finalize).

VossTUIApp current state (read from voss/harness/tui/app.py):
- voss/harness/tui/app.py line 79: action_interrupt is `pass`
- No `active_turn_task` attribute today
- __init__ at line 39 takes session_id/model/budget_total/slash_registry

cli.py call sites for `asyncio.run(run_turn(...))` (CONFIRMED via reads):
- `do_cmd` at voss/harness/cli.py line 998-1011: `result = asyncio.run(
   run_turn(text, tools=tools, cwd=cwd, renderer=renderer, model=do_model,
   provider=do_provider, permissions=gate, history=do_history,
   session_id=do_record.id, voss_md_text=voss_md_text))`
- `_run_repl` at voss/harness/cli.py line 1307-1322: `result = asyncio.run(
   run_turn(line, tools=tools, cwd=cwd, renderer=renderer, model=...,
   history=ctx.history, permissions=gate, provider=provider,
   session_id=record.id, cognition=bundle, prior_context=ctx.prior_context,
   voss_md_text=ctx.voss_md_text))`

Both call sites use the synchronous `asyncio.run(coro)` API which does
not expose the underlying Task. The single committed approach: replace
both call sites with a new helper `_run_turn_cancellable(coro, *,
renderer) -> TurnResult` that:

1. Creates a new event loop via asyncio.new_event_loop() and sets it
   current via asyncio.set_event_loop(loop).
2. Calls `task = loop.create_task(coro)`.
3. Looks up the TUI app via `app = getattr(renderer, "app", None)`
   (TextualRenderer has `self.app = app` at tui/renderer.py line 47;
   non-Textual renderers do not have that attribute -> getattr returns
   None). If `app is not None and hasattr(app, "register_turn_task")`,
   call `app.register_turn_task(task)`.
4. Installs a SIGINT handler on the loop via
   `loop.add_signal_handler(signal.SIGINT, task.cancel)` for the
   headless / non-TUI path. (On Windows, add_signal_handler raises
   NotImplementedError — wrap in try/except and fall back to the
   default KeyboardInterrupt behavior, which still cancels the task
   via the natural CancelledError propagation when KeyboardInterrupt
   reaches the loop.)
5. Runs `result = loop.run_until_complete(task)` and returns result.
   On CancelledError, the handler in _run_turn_exec catches the cancel
   and re-raises; the outer run_until_complete also receives
   CancelledError. Catch CancelledError at this outer level and return
   the partial TurnResult by reading the recorder's final state via a
   side channel — actually NO: simpler, the caller wants the
   TurnResult or a CancelledError-shaped exception. Re-raise
   CancelledError as a `click.Abort` (idiomatic click cancel) for the
   user-facing CLI exit code. Document this in the helper's docstring.
6. In a `finally:` block, remove the signal handler if installed and
   close the loop via loop.close().

VossTUIApp.register_turn_task contract (Task 1 of this plan):
- `def register_turn_task(self, task: asyncio.Task) -> None`
- If self.active_turn_task is not None AND not self.active_turn_task.done():
    raise RuntimeError("active turn task already registered")
- Otherwise: self.active_turn_task = task and
  task.add_done_callback(self._clear_turn_task) where _clear_turn_task
  sets self.active_turn_task = None.

action_interrupt body (locked):
  task = self.active_turn_task
  if task is not None and not task.done():
      task.cancel()

_run_turn_exec CancelledError handler (locked, 5 steps):
1. Close the most recent open iteration with exit_reason="interrupt"
   via rec.end_iteration(plan=&lt;synthetic interrupted Plan&gt;,
   tool_results=[], cost_usd=0.0, prompt_tokens=0, completion_tokens=0,
   exit_reason="interrupt").
2. Surface "[interrupted]" via renderer.stream_delta + finalize_stream
   wrapped in try/except (renderer may not be mounted in test).
3. Call rec.finalize(cwd, cost_usd=total_cost_usd, exit_reason="interrupt")
   -> RunRecord with exit_reason="interrupt".
4. telemetry.note_turn(cost_usd=total_cost_usd, outcome="interrupt",
   iteration_count=len(all_iter_records), exit_reason="interrupt",
   total_tokens=total_prompt_tokens + total_completion_tokens).
5. Re-raise CancelledError.

Exit-reason precedence: the except clause runs FIRST (catches the
CancelledError before the fallthrough `if exit_reason is None:
exit_reason = "max-iter"` line in T1-05's post-loop code). Document this
in the SUMMARY.

Headless (non-TUI) cancel: cli.py `voss do` path runs through
_run_turn_cancellable too. KeyboardInterrupt -> SIGINT -> signal handler
calls task.cancel(). The same handler runs. No separate path needed.
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
    - Calling register_turn_task twice (without the first finishing) raises RuntimeError("active turn task already registered")
  </behavior>
  <action>
    Edit `voss/harness/tui/app.py`:

    1. In __init__, after `self.focused_turn_index: int | None = None`,
       add: `self.active_turn_task: Optional[asyncio.Task] = None`. Add
       `import asyncio` and `from typing import Optional` at the top if
       not already imported (check `grep -n "^import asyncio\|^from typing" voss/harness/tui/app.py`).

    2. Add a method `register_turn_task(self, task: asyncio.Task) -> None:`:
       - If `self.active_turn_task is not None and not self.active_turn_task.done()`: raise RuntimeError("active turn task already registered")
       - Otherwise set self.active_turn_task = task and call
         `task.add_done_callback(self._clear_turn_task)`

    3. Add a method `_clear_turn_task(self, task: asyncio.Task) -> None:`
       that sets `self.active_turn_task = None` (the callback receives
       the task ref but we just blank the attribute).

    4. Replace `action_interrupt` body (line 79). New body:
       task = self.active_turn_task
       if task is not None and not task.done():
           task.cancel()
       Remove the stale `# M9-04 wires interrupt to the running turn;
       M9-03 stub is a no-op.` comment and replace with a brief note
       pointing to T1.

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
  <name>Task 2: _run_turn_exec CancelledError handler + cli.py _run_turn_cancellable helper</name>
  <files>voss/harness/agent.py, voss/harness/cli.py, tests/harness/test_agent_interrupt.py, tests/harness/test_cli_run_turn_cancellable.py</files>
  <read_first>
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-SPEC.md (ITER-04 — 100ms latency criterion + "no asyncio task leak after the cancel" + Specifics "Exit reason precedence")
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md (Interrupt + mid-iter cleanup section + Recorder finalization on cancel — exact 5-step handler)
    - voss/harness/agent.py (after T1-05 — the new while-loop body and the line where exit_reason maps to final string)
    - voss/harness/recorder.py (after T1-01 — begin_iteration / end_iteration semantics)
    - voss/harness/cli.py lines 985-1015 (do_cmd's asyncio.run call site) and lines 1295-1335 (_run_repl's asyncio.run call site)
    - voss/harness/tui/renderer.py line 46-47 (TextualRenderer.__init__ sets self.app = app — the lookup point for register_turn_task)
    - voss/harness/render.py (PlainRenderer, TtyRenderer, JsonRenderer have no .app attribute — getattr(renderer, "app", None) returns None for those)
    - voss/harness/tui/app.py (after Task 1 — register_turn_task signature)
  </read_first>
  <behavior>
    Agent-side handler behaviors (test_agent_interrupt.py):
    - Given a FakeStreamingProvider that emits TextDelta then awaits
      an asyncio.Event-controlled hang, calling task.cancel() on the
      _run_turn_exec task results in: (a) task ends in cancelled
      state, (b) provider.stream() exits via its async-context exit,
      (c) the recorder is finalized with exit_reason="interrupt"
    - Latency from task.cancel() to recorder.finalize() invocation is
      <= 100ms (measure with time.monotonic; assert <0.1s)
    - The finalized RunRecord has exit_reason == "interrupt"
    - asyncio.all_tasks() after the cancelled task settles does NOT
      include any leaked tasks attributable to the turn
    - telemetry.note_turn was called with kwargs including
      exit_reason="interrupt" and outcome="interrupt"
    - Precedence test: cancel arrives on iteration max_iterations
      (last possible iter). The handler runs first and sets
      exit_reason="interrupt", NOT "max-iter". The finalized RunRecord
      has exit_reason == "interrupt".
    - Mid-iter cleanup: cancel arrives AFTER begin_iteration but
      BEFORE end_iteration. The handler invokes end_iteration on the
      most-recent open iter with exit_reason="interrupt".
    - Between-iter cleanup: cancel arrives between iterations. The
      handler finds no open iter and finalizes the RunRecord directly
      with exit_reason="interrupt".

    CLI helper behaviors (test_cli_run_turn_cancellable.py):
    - `_run_turn_cancellable(coro, *, renderer=PlainRenderer())` runs
      the coroutine to completion and returns its result (happy path,
      no cancel).
    - When renderer is a TextualRenderer (or a stub with an `.app`
      attribute exposing `register_turn_task`), the helper calls
      `renderer.app.register_turn_task(task)` exactly once before
      run_until_complete.
    - When renderer has no `.app` attribute (PlainRenderer / TtyRenderer
      / JsonRenderer), the helper does NOT raise — getattr returns None
      and the registration step is skipped.
    - When the running coroutine raises CancelledError (e.g. via
      app.action_interrupt -> task.cancel from a side thread), the
      helper catches the CancelledError and re-raises as click.Abort
      (or returns the partial result; pick click.Abort for idiomatic
      CLI exit-code semantics). Test asserts pytest.raises(click.Abort).
    - On platforms where loop.add_signal_handler raises
      NotImplementedError (Windows), the helper falls back gracefully
      without raising. Test monkeypatches add_signal_handler to raise
      NotImplementedError and asserts the helper still runs to
      completion on a non-cancelled coroutine.
  </behavior>
  <action>
    In `voss/harness/agent.py`:

    Add `import asyncio` at the top if not already imported (check via
    `grep -n "^import asyncio" voss/harness/agent.py`).

    Wrap the relevant section of _run_turn_exec (the
    `rec = RunRecorder.start()` line through the final `return
    TurnResult(...)` at the end of the function body — both the
    ContextScope async-with block AND the post-loop record_run +
    finalize + return-construction logic) in
    `try: ... except asyncio.CancelledError: ...`.

    Handler body — exact 5-step sequence per CONTEXT.md "Recorder
    finalization on cancel":

    Step 1: locate the most recent open iter via
      `open_iter = next((ir for ir in reversed(rec._iterations) if
      not ir.ended_at), None)`. If open_iter is not None, call
      `rec.end_iteration(plan=Plan(rationale="(interrupted)", steps=[],
      confidence=0.0, final_when_done=""), tool_results=[], cost_usd=0.0,
      prompt_tokens=0, completion_tokens=0, exit_reason="interrupt")`.

    Step 2: surface in the TurnView via renderer wrapped in
      try/except (renderer may not be mounted in test):
      try:
          renderer.stream_delta("\n[interrupted]\n")
          renderer.finalize_stream(role="system", confidence=None,
                                    cost_usd=None, timestamp=None)
      except Exception:  # noqa: BLE001
          pass

    Step 3: finalize the record:
      run = rec.finalize(cwd, cost_usd=total_cost_usd,
                          exit_reason="interrupt")

    Step 4: telemetry:
      telemetry.note_turn(cost_usd=total_cost_usd, outcome="interrupt",
                           iteration_count=len(all_iter_records),
                           exit_reason="interrupt",
                           total_tokens=total_prompt_tokens + total_completion_tokens)

    Step 5: re-raise:
      raise

    Source-order invariant: the except clause is structurally below
    the `if exit_reason is None: exit_reason = "max-iter"` line from
    T1-05, but Python exception propagation runs the except BEFORE
    the fallthrough — so cancel at iteration_index == max_iterations
    - 1 produces exit_reason="interrupt" without ever executing the
    max-iter assignment.

    In `voss/harness/cli.py`:

    Add a new top-level helper near the existing
    `_resolve_run_turn` function (line 174):

      def _run_turn_cancellable(coro, *, renderer) -> Any:
          """Run an agent-turn coroutine with cancel-on-Ctrl-C semantics.

          Replaces `asyncio.run(coro)` everywhere. The helper:
            1. Creates a new event loop and a Task wrapping the coro.
            2. If `renderer` exposes an `.app` attribute (TextualRenderer
               only — see voss/harness/tui/renderer.py:47), registers the
               Task on that app so VossTUIApp.action_interrupt can find
               it.
            3. Installs a SIGINT handler on the loop so Ctrl-C in the
               headless path also cancels the Task. On platforms where
               add_signal_handler raises NotImplementedError (Windows),
               falls back to the default KeyboardInterrupt path.
            4. Runs the loop until the Task completes.
            5. Returns the result. Re-raises CancelledError as click.Abort
               so the CLI exits with a non-zero status on user-initiated
               cancel.
          """
          import signal as _signal
          loop = asyncio.new_event_loop()
          asyncio.set_event_loop(loop)
          task = loop.create_task(coro)

          app = getattr(renderer, "app", None)
          if app is not None and hasattr(app, "register_turn_task"):
              app.register_turn_task(task)

          handler_installed = False
          try:
              try:
                  loop.add_signal_handler(_signal.SIGINT, task.cancel)
                  handler_installed = True
              except (NotImplementedError, RuntimeError):
                  # Windows / non-main-thread fallback
                  pass
              try:
                  return loop.run_until_complete(task)
              except asyncio.CancelledError:
                  raise click.Abort()
          finally:
              if handler_installed:
                  try:
                      loop.remove_signal_handler(_signal.SIGINT)
                  except Exception:  # noqa: BLE001
                      pass
              loop.close()
              asyncio.set_event_loop(None)

    Replace the `do_cmd` call site at lines 998-1011. Original:
      result = asyncio.run(
          run_turn(text, tools=tools, ...kwargs...)
      )
    Replace with:
      result = _run_turn_cancellable(
          run_turn(text, tools=tools, ...kwargs...),
          renderer=renderer,
      )

    Replace the `_run_repl` call site at lines 1307-1322 the same way:
      result = _run_turn_cancellable(
          run_turn(line, tools=tools, ...kwargs...),
          renderer=renderer,
      )

    Use the existing `click` import (cli.py imports click at the top).
    If `import asyncio` is not already present in cli.py, add it.

    Write `tests/harness/test_agent_interrupt.py` covering the eight
    agent-side behaviors. Use a FakeStreamingProvider with an
    asyncio.Event "release" gate the test holds open then cancels
    around. Use asyncio.create_task + task.cancel(); await the task
    inside `with pytest.raises(asyncio.CancelledError):`. Spy on
    rec.finalize via a side-effect hook to assert exit_reason="interrupt"
    AND measure latency from cancel() to finalize() invocation.

    Write `tests/harness/test_cli_run_turn_cancellable.py` covering
    the five CLI-helper behaviors. Use a happy-path coroutine that
    returns a sentinel; an always-pending coroutine cancelled mid-run;
    a stub renderer with a `.app` attribute exposing a Recording
    register_turn_task; a renderer with no `.app` attribute; and a
    monkeypatch on asyncio.AbstractEventLoop.add_signal_handler to
    raise NotImplementedError once.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_interrupt.py tests/harness/test_cli_run_turn_cancellable.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "except asyncio.CancelledError" voss/harness/agent.py` returns >= 1 match in _run_turn_exec
    - source assertion: `grep -nE 'exit_reason="interrupt"' voss/harness/agent.py` returns >= 2 matches (end_iteration + finalize + note_turn)
    - source assertion: `grep -n "_run_turn_cancellable" voss/harness/cli.py` returns >= 3 matches (one def + two call sites)
    - source assertion: `grep -nE "asyncio\.run\(" voss/harness/cli.py | grep run_turn` returns 0 matches (both call sites converted)
    - source assertion: `grep -n "register_turn_task" voss/harness/cli.py` returns >= 1 match (the helper wires the task on the TUI app)
    - latency assertion: pytest test_interrupt_finalize_latency completes with time.monotonic() delta < 0.1s
    - precedence assertion: pytest test_interrupt_precedence_over_max_iter asserts run.exit_reason == "interrupt" when cancel arrives at the cap iteration
    - leak assertion: pytest test_no_task_leak asserts asyncio.all_tasks() delta is 0 after cancel settles
    - behavior assertion: all 8 agent-side tests + all 5 cli-helper tests pass
    - regression assertion: `uv run pytest tests/harness/ -k "agent or recorder or session or tui or cli" -x -q` passes (no break in T1-01/05 tests)
    - test command: `uv run pytest tests/harness/test_agent_interrupt.py tests/harness/test_cli_run_turn_cancellable.py tests/harness/ -k "agent or recorder or session or tui or cli" -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>_run_turn_exec catches CancelledError, closes any open iter with exit_reason="interrupt", finalizes the record, emits note_turn, and re-raises; cli.py exposes a single _run_turn_cancellable helper and both asyncio.run(run_turn(...)) call sites are converted; interrupt precedence over max-iter enforced via exception flow; latency <100ms in measured test.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/harness/test_app_interrupt.py tests/harness/test_agent_interrupt.py tests/harness/test_cli_run_turn_cancellable.py -x -q` passes
- `grep -n "except asyncio.CancelledError" voss/harness/agent.py` >= 1 match
- `grep -A3 "def action_interrupt" voss/harness/tui/app.py | grep -F "task.cancel()"` 1 match
- `grep -n "_run_turn_cancellable" voss/harness/cli.py` >= 3 matches (def + 2 call sites)
- `grep -nE "asyncio\.run\(" voss/harness/cli.py | grep run_turn` returns 0 matches
- All four exit_reasons (done, max-iter, budget, interrupt) reachable via dedicated test fixtures across T1-05 + T1-06 tests
- `uv run pytest tests/harness/ -k "agent or recorder or session or tui or provider_stream or cli" -x -q` passes
</verification>

<success_criteria>
- action_interrupt cancels the active turn's asyncio.Task; the task ends in cancelled state
- _run_turn_exec's CancelledError handler closes the open iter, finalizes the recorder with exit_reason="interrupt", emits telemetry, and re-raises
- Latency from task.cancel() to recorder.finalize() < 100ms (measured)
- No asyncio task leak after cancel settles
- Exit reason precedence: interrupt > max-iter > budget > done (handler-precedes-fallthrough invariant)
- cli.py exposes a single _run_turn_cancellable helper; both asyncio.run(run_turn(...)) call sites converted; TUI mode registers the task via renderer.app, headless mode catches SIGINT
</success_criteria>

<output>
Create `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-06-SUMMARY.md` when done with: exact handler placement (line range in _run_turn_exec), _run_turn_cancellable signature, evidence of <100ms latency from the test run output, and confirmation that both cli.py call sites (do_cmd line 998-1011 and _run_repl line 1307-1322) were converted.
</output>
