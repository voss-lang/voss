---
phase: T1-iteration-loop-streaming-interrupt
plan: 06
status: complete
completed_at: 2026-05-15
commits:
  - 2e35c14 — feat(T1-06): enhance turn task management in TUI (Task 1)
  - 394253a — feat(T1-06): implement cancellable agent turn execution (Task 2)
  - a87c62d — test(T1-06): finalize agent + cli interrupt test coverage
---

# T1-06 Summary — Interrupt wiring

## Files changed

- `voss/harness/tui/app.py` — `VossTUIApp.active_turn_task`, `register_turn_task`, `_clear_turn_task`, filled `action_interrupt`.
- `voss/harness/agent.py` — wrapped `_run_turn_exec` body (lines ~483 → ~872 in pre-T1-06 source) in `try/except asyncio.CancelledError`; handler lives at lines ~874–921 in the rewritten file.
- `voss/harness/cli.py` — added `_run_turn_cancellable(coro, *, renderer)` helper; converted both `asyncio.run(run_turn(...))` call sites (`do_cmd` + `_run_repl`).
- `tests/harness/tui/test_app_interrupt.py` — 7 tests covering register / clear / interrupt / no-op / replace.
- `tests/harness/test_agent_interrupt.py` — 5 tests: cancel-mid-stream, <100ms finalize latency, no task leak, `[interrupted]` renderer marker, between-iter cleanup.
- `tests/harness/test_cli_run_turn_cancellable.py` — 5 tests: happy path, app registration, no-`.app` fallback, `click.Abort` on cancel, `NotImplementedError` add_signal_handler fallback.

## Handler placement in _run_turn_exec

Wrap boundaries in the post-T1-06 file (`grep -n`):

| Line  | Marker                                                                       |
|-------|-------------------------------------------------------------------------------|
| 483   | `rec = RunRecorder.start()`                                                  |
| 484   | `try:` (T1-06 inserted)                                                      |
| 485   | indented `cognition_text = _compose_cognition_prompt(...)`                   |
| ~870  | indented `return TurnResult(...)`                                            |
| 874   | `except asyncio.CancelledError:` — handler entry                             |
| 921   | `raise` — re-raises CancelledError after finalize                            |

The 5-step handler (matches CONTEXT.md "Recorder finalization on cancel"):

1. Close most-recent open iteration with `exit_reason="interrupt"` (synthetic `Plan(rationale="(interrupted)", steps=[], confidence=0.0, final_when_done="")`).
2. Surface `\n[interrupted]\n` via `renderer.stream_delta` + `renderer.finalize_stream(role="system", ...)` wrapped in try/except (renderer may not be mounted in test).
3. Call `rec.finalize(cwd, cost_usd=total_cost_usd, exit_reason="interrupt")`.
4. `telemetry.note_turn(cost_usd=..., outcome="interrupt", iteration_count=..., exit_reason="interrupt", total_tokens=...)`.
5. `raise` (re-raise the CancelledError so the asyncio task ends in cancelled state, no swallow).

### Exit-reason precedence

The `except` runs BEFORE the post-while-loop fallthrough `if exit_reason is None: exit_reason = "max-iter"`. CancelledError raised during the last iter therefore records as `"interrupt"`, NOT `"max-iter"`. The handler bypasses every assignment after the cancel point. Verified by inspection of handler placement (no exit-reason mutation reaches the finalize call other than the literal `"interrupt"`).

## _run_turn_cancellable signature

```python
def _run_turn_cancellable(coro, *, renderer) -> Any:
    """Run an agent-turn coroutine with cancel-on-Ctrl-C semantics."""
```

Behavior:

1. `asyncio.new_event_loop()` + `loop.create_task(coro)`.
2. `app = getattr(renderer, "app", None)`. If `hasattr(app, "register_turn_task")` → `app.register_turn_task(task)`. Only `TextualRenderer` exposes `.app` (see `tui/renderer.py:47`); PlainRenderer / TtyRenderer / JsonRenderer return `None` and skip registration silently.
3. `loop.add_signal_handler(SIGINT, task.cancel)` wrapped in `try/except (NotImplementedError, RuntimeError)` for Windows + non-main-thread fallback.
4. `loop.run_until_complete(task)`.
5. `except asyncio.CancelledError: raise click.Abort()` so CLI exits non-zero on user cancel.
6. `finally:` removes the signal handler (if installed) and closes the loop.

## CLI call sites converted

| Call site            | Pre-T1-06 line | Post-T1-06 line                       |
|----------------------|----------------|----------------------------------------|
| `do_cmd`             | `asyncio.run(run_turn(...))` ~line 998 | `_run_turn_cancellable(run_turn(...), renderer=renderer)` |
| `_run_repl`          | `asyncio.run(run_turn(...))` ~line 1307| `_run_turn_cancellable(run_turn(...), renderer=renderer)` |

`grep -nE "asyncio\.run\(" voss/harness/cli.py | grep run_turn` returns **0 matches**.

## Latency evidence

`test_interrupt_latency_under_100ms` in `test_agent_interrupt.py` measures `time.monotonic()` between `task.cancel()` and `rec.finalize()` invocation via a `RunRecorder.finalize` monkeypatch. Asserts `< 0.1s`. Test passes (typical local run ~5–20ms).

## No task leak

`test_no_task_leak_after_cancel` snapshots `asyncio.all_tasks()` before + after; asserts no new alive tasks remain after the cancel settles. Test passes.

## ContextVar isolation note

`telemetry.note_turn` writes to a task-local `_turn_meta` ContextVar. asyncio tasks capture a copy of the parent context at creation; mutations inside the task don't propagate back. Tests asserting on `note_turn` kwargs use a `monkeypatch.setattr(telemetry, "note_turn", spy)` (also on `agent_mod.telemetry.note_turn` because the module imports the symbol by reference). Documented in this summary so future tests don't trip on the same gotcha.

## Verification

```
uv run pytest tests/harness/                                                     # 694 passed
uv run pytest tests/harness/tui/test_app_interrupt.py \
              tests/harness/test_agent_interrupt.py \
              tests/harness/test_cli_run_turn_cancellable.py                     # 17 passed

grep -n "except asyncio.CancelledError" voss/harness/agent.py                    # 1 match
grep -A3 "def action_interrupt" voss/harness/tui/app.py | grep -F "task.cancel()"# 1 match
grep -c "_run_turn_cancellable" voss/harness/cli.py                              # 3 (def + 2 call sites)
grep -nE "asyncio\.run\(" voss/harness/cli.py | grep run_turn                    # 0 matches
grep -cE 'exit_reason="interrupt"' voss/harness/agent.py                         # 4
```

All four `exit_reason` values (`done`, `max-iter`, `budget`, `interrupt`) now reach their branches via dedicated test fixtures across T1-05 and T1-06.
