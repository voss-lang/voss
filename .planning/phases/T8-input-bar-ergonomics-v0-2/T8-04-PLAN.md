---
phase: T8-input-bar-ergonomics-v0-2
plan: 04
type: execute
wave: 2
depends_on: ["T8-02"]
files_modified:
  - voss/harness/tui/app.py
  - voss/harness/cli.py
  - tests/harness/tui/test_full_flow_pilot.py
autonomous: true
requirements: [INPUT-01, INPUT-02, INPUT-03, INPUT-04, INPUT-05]
user_setup: []

must_haves:
  truths:
    - "A4 SCOPE DECISION RECORDED & ACCEPTED: the TUI submit→run_turn wiring is an in-scope T8 ENABLING deliverable (option a). Rationale: make_renderer constructs TextualRenderer(VossTUIApp()) but app.run()/run_async() is NEVER called anywhere in voss/harness/ and _run_repl uses synchronous input('▌ '); without this wiring INPUT-01..05 are structurally unobservable in a real session and the phase goal is unreachable. This is enabling substrate, NOT scope creep."
    - "VossTUIApp has an on_input_bar_submitted handler that dispatches the submitted value to run_turn via the EXISTING register_turn_task / active_turn_task cancellation plumbing (not a new mechanism)"
    - "VossTUIApp stores the live EpisodicMemory (self.history) passed at construction so InputBar (Plan 05 Ctrl-R) can read the per-project corpus via self.app.history"
    - "_run_repl drives the interactive Textual event loop (app.run_async / equivalent) when the renderer is a TextualRenderer; the synchronous input('▌ ') path remains the fallback for Plain/Tty/Json renderers — slash dispatch, clean-exit conventions, and job-reap finally are preserved"
    - "Submitting a task in the TUI causes a turn to render; action_interrupt still cancels the in-flight turn (T1-06 regression intact)"
  artifacts:
    - path: "voss/harness/tui/app.py"
      provides: "on_input_bar_submitted + on_local_event handlers + history wiring"
      contains: "def on_input_bar_submitted"
      min_lines: 240
    - path: "voss/harness/cli.py"
      provides: "_run_repl interactive-app branch for TextualRenderer"
      contains: "run_async"
  key_links:
    - from: "voss/harness/tui/widgets/input_bar.py"
      to: "voss/harness/tui/app.py:on_input_bar_submitted"
      via: "InputBar.Submitted message bubbles to the app handler"
      pattern: "def on_input_bar_submitted"
    - from: "voss/harness/tui/app.py:on_input_bar_submitted"
      to: "voss.harness.agent.run_turn"
      via: "handler schedules run_turn via register_turn_task (existing T1-06 plumbing)"
      pattern: "register_turn_task"
    - from: "voss/harness/cli.py:_run_repl"
      to: "VossTUIApp.run_async"
      via: "TextualRenderer path drives the interactive event loop instead of input()"
      pattern: "isinstance.*TextualRenderer"
---

<objective>
Wire the TUI submit path to `run_turn` and make `_run_repl` drive the interactive Textual event loop when the renderer is a `TextualRenderer` (A4 enabling deliverable, RESEARCH Pitfall 4). Store the live `EpisodicMemory` on `VossTUIApp` so Plan 05's Ctrl-R can read the per-project corpus. Add the `on_local_event` handler that Plan 03's `recorder_bridge.emit` targets.

Purpose: Without this, `make_renderer` builds `TextualRenderer(VossTUIApp())` but `app.run()` is never called and `_run_repl` uses `input("▌ ")` — the TUI is a passive render target and INPUT-01..05 are unobservable. This plan supplies the minimum enabling substrate so the phase goal ("input bar stops being the slowest part of the loop") is reachable. Decision recorded in must_haves.truths and the threat model.
Output: app.py handlers + history field, cli.py interactive branch, pilot regression test for submit→turn + interrupt.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-RESEARCH.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-PATTERNS.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-02-SUMMARY.md

<interfaces>
voss/harness/tui/app.py (VERIFIED — the analog being extended):
- `class VossTUIApp(App)`; `__init__(self, *, session_id="", model="", budget_total=0, slash_registry=None, **kw)` — T8 ADDS `history: EpisodicMemory | None = None` param stored as `self.history`
- `register_turn_task(self, task: asyncio.Task)` — raises on double-register; `task.add_done_callback(self._clear_turn_task)`; `_clear_turn_task` frees `self.active_turn_task`
- `action_interrupt(self)` — cancels `self.active_turn_task` (T1-06; do NOT change)
- existing mutator pattern (lines 187-209): `try: tv = self.query_one("#main", TurnView) except Exception: return` then `tv.append_turn(...)` — `on_local_event` MUST follow this exact guard
- `compose()` yields `InputBar(id="input")`; `on_mount` focuses it

voss/harness/cli.py (VERIFIED):
- `_run_repl(*, cwd, json_mode, mode, history: EpisodicMemory, record, provider, auth_detail="", edit_scope=None, prior_context=None, plain=False, keep_logs=False)` — builds `renderer = make_renderer(...)`, `ReplContext(...)`, then a `while True:` loop using `line = input("▌ ")` (line 1422); slash dispatch at 1440-1453; clean-exit `conventions.run_on_clean_exit` on EOF/KeyboardInterrupt (1423-1434); turn via `_resolve_run_turn(cwd)` + `_run_turn_cancellable(run_turn(line, tools=..., history=ctx.history, ...), renderer=renderer)` (1463-1480); `finally:` reaps jobs + removes `.active-session` (1493-1509)
- `_run_turn_cancellable(coro, *, renderer)` — creates a fresh event loop, `register_turn_task` if `renderer.app` present, SIGINT handler, runs to completion; raises `click.Abort` on cancel
- `from .render import make_renderer`; `make_renderer` returns `TextualRenderer(VossTUIApp())` on the default TUI path (render.py:102/108) — but the app is never run
- detect TextualRenderer via `from .tui.renderer import TextualRenderer; isinstance(renderer, TextualRenderer)` (precedent: cli.py:990-992 `_wire_tui_permissions_if_textual`)

voss/harness/tui/renderer.py: `class TextualRenderer: __init__(self, app: VossTUIApp); self.app = app` — the app instance is `renderer.app`

InputBar.Submitted (Plan 02, M9-locked): `class Submitted(Message): value: str` — bubbles up; Textual routes `InputBar.Submitted` to an `on_input_bar_submitted(self, event)` method on the app.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: VossTUIApp.history + on_input_bar_submitted + on_local_event</name>
  <behavior>
    - VossTUIApp(history=EpisodicMemory()) stores it as self.history; default None preserves existing constructor callers
    - Posting InputBar.Submitted(value) invokes on_input_bar_submitted, which schedules run_turn for `value` exactly once via register_turn_task (raises if a turn is already active — existing contract)
    - on_local_event("shell.local"/"memory.note"/"notice", payload) routes to the #main TurnView (or mounts the Plan-05 notice) using the existing try/except-return guard; never raises if #main is absent
    - action_interrupt during an in-flight submitted turn cancels it (T1-06 regression holds)
  </behavior>
  <read_first>
    - voss/harness/tui/app.py (full file — `__init__`, `register_turn_task`/`_clear_turn_task`, `action_interrupt`, the lines-187-209 mutator guard pattern)
    - T8-RESEARCH.md Pitfall 4 (no on_input_bar_submitted exists; resolution = add handler + worker-thread run_turn + reuse register_turn_task), Pattern 9 (on_local_event is the recorder_bridge.emit target — A3), Open Question 1 (include in scope) / Open Question 3 (store history on app — A6), Anti-Pattern "Reading episodic store from session.py" (use the live in-memory instance)
    - T8-PATTERNS.md §"app.py" (`__init__` adds `history` param; `on_input_bar_submitted`/`on_local_event` follow the `query_one("#main", TurnView)` try/except guard; reuse `register_turn_task` for cancellation)
  </read_first>
  <action>In `app.py`: add `history: EpisodicMemory | None = None` to `VossTUIApp.__init__` keyword params, store `self.history = history` (import `EpisodicMemory` from `voss_runtime`; default None keeps every existing caller — render.py, tests — valid). Add `def on_input_bar_submitted(self, event) -> None`: read `event.value`, schedule the agent turn as an `asyncio.Task` wrapping `run_turn(value, ...)` with the args _run_repl already assembles (tools, cwd, renderer, model, history=self.history, permissions, provider, session_id, cognition, prior_context, voss_md_text) — the concrete arg source is the `ReplContext` the app is given by Task 2; expose a small `self._turn_dispatch` callable set by cli.py so app.py stays import-light and does not duplicate ReplContext assembly. Register the task via the EXISTING `self.register_turn_task(task)` (do NOT invent new cancellation state — T1-06 reuse) so `action_interrupt` keeps working unchanged. Add `def on_local_event(self, event_name: str, payload: dict) -> None` following the verified mutator guard (`try: tv = self.query_one("#main", TurnView) except Exception: return`): for `shell.local`/`memory.note` mount the corresponding Plan-03 LocalBlock into the scroll container; for `notice` mount the Plan-05 `LocalBlockNotice` (tolerate its absence pre-Plan-05 via a guarded import). Keep `from __future__ import annotations` + `# noqa: BLE001` on bare excepts.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_app_shell.py tests/harness/tui/test_app_interrupt.py tests/harness/tui/test_full_flow_pilot.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import inspect; from voss.harness.tui.app import VossTUIApp; s=inspect.signature(VossTUIApp.__init__); assert 'history' in s.parameters; assert hasattr(VossTUIApp,'on_input_bar_submitted') and hasattr(VossTUIApp,'on_local_event')"` exits 0
    - `pytest tests/harness/tui/test_app_interrupt.py -q` exits 0 (T1-06 cancellation regression — action_interrupt still cancels a registered turn task)
    - pilot test in test_full_flow_pilot.py: construct `VossTUIApp(history=seeded_history(...))` with a stub `_turn_dispatch`, post `InputBar.Submitted("hi")`, `await pilot.pause()`, assert `_turn_dispatch` was invoked exactly once with `"hi"` and `register_turn_task` was called — PASS
    - `python -c "from voss.harness.tui.app import VossTUIApp; VossTUIApp()"` exits 0 (default-construction unchanged for existing callers)
    - `git diff voss/harness/tui/app.py` shows `action_interrupt`/`register_turn_task`/`_clear_turn_task` bodies unchanged (no edits to T1-06 plumbing)
  </acceptance_criteria>
  <done>App stores history, routes Submitted→run_turn via existing register_turn_task, has on_local_event for Plan-03 emit; T1-06 interrupt regression intact; existing constructors unbroken.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: _run_repl interactive TextualRenderer branch</name>
  <behavior>
    - When `make_renderer` returns a TextualRenderer, _run_repl drives the interactive Textual event loop (app.run_async / equivalent) with self.history + a turn-dispatch closure bound to the assembled ReplContext, instead of the `input("▌ ")` loop
    - When the renderer is Plain/Tty/Json, the existing `input("▌ ")` loop runs unchanged (slash dispatch, _classify_intent, clean-exit conventions, job-reap finally all preserved)
    - The `finally:` block (lifecycle.reap_jobs + .active-session unlink + keep_logs rmtree) runs on both paths
    - Clean exit from the TUI (quit) still triggers conventions.run_on_clean_exit with ctx.history/record/memory_store
  </behavior>
  <read_first>
    - voss/harness/cli.py lines 1313-1510 (the full `_run_repl` — ReplContext assembly, the input() loop, slash dispatch, clean-exit conventions, the job-reap finally)
    - voss/harness/cli.py lines 255-302 (`_run_turn_cancellable` — the existing fresh-loop + register_turn_task + SIGINT pattern the TUI branch must stay compatible with), lines 984-992 (`_wire_tui_permissions_if_textual` — the `isinstance(renderer, TextualRenderer)` detection precedent)
    - T8-RESEARCH.md Pitfall 4 (resolution: switch _run_repl to app.run_async for TextualRenderer; the agent turn already runs on a worker via TextualRenderer._post call_from_thread), §"Don't Hand-Roll"
    - T8-PATTERNS.md §"app.py" register_turn_task/worker note
  </read_first>
  <action>In `_run_repl`, after `renderer`/`ctx` are assembled, branch on `isinstance(renderer, TextualRenderer)` (import locally from `.tui.renderer`, mirroring `_wire_tui_permissions_if_textual`). TUI branch: set `renderer.app.history = ctx.history`, bind a turn-dispatch closure onto `renderer.app._turn_dispatch` that calls `_resolve_run_turn(cwd)(value, tools=tools, cwd=cwd, renderer=renderer, model=cfg.default_model, history=ctx.history, permissions=gate, provider=provider, session_id=record.id, cognition=bundle, prior_context=ctx.prior_context, voss_md_text=ctx.voss_md_text)` inside the existing cancellable-task discipline (the app's `on_input_bar_submitted` wraps it in a Task + `register_turn_task`; the agent loop already marshals widget calls via `TextualRenderer._post`/`call_from_thread`), then run the app interactively (`await renderer.app.run_async()` driven from this function — wrap so the existing outer `try/finally` still executes the job-reap + `.active-session` cleanup + `conventions.run_on_clean_exit` on app quit). Non-TUI branch: keep the current `while True: input("▌ ")` loop verbatim — do NOT alter slash dispatch, `_classify_intent`, the EOF/KeyboardInterrupt clean-exit, or the `finally`. Surgical change only: the `input()` loop body is preserved for non-TUI; the TUI path is an added branch. Update the existing `test_full_flow_pilot.py` happy-path so it asserts the TextualRenderer branch wires `app.history` and `_turn_dispatch` (drive via the pilot, stub the provider with the Plan-01 `stub_provider` fixture — no live creds).</action>
  <verify>
    <automated>pytest tests/harness/tui/test_full_flow_pilot.py tests/harness/tui/test_cli_integration.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'isinstance' voss/harness/cli.py` increases by exactly the added TextualRenderer check; `grep -n 'run_async' voss/harness/cli.py` shows the call inside `_run_repl`
    - `pytest tests/harness/tui/test_full_flow_pilot.py -q` exits 0 — pilot drives a TUI session: submit a task → stub turn renders; `renderer.app.history is ctx.history`; clean exit triggers `conventions.run_on_clean_exit` (assert via spy)
    - non-TUI regression: `pytest tests/harness/tui/test_cli_integration.py tests/harness/tui/test_plain_parity.py -q` exits 0 (Plain/Tty input() loop + slash dispatch + job-reap finally unchanged)
    - `git diff voss/harness/cli.py` shows the `while True: input("▌ ")` loop body, slash dispatch (1440-1453), clean-exit conventions, and the job-reap `finally` (1493-1509) unmodified — only an added TextualRenderer branch
    - full TUI suite green: `pytest tests/harness/tui/ -q` exits 0
  </acceptance_criteria>
  <done>_run_repl drives the interactive Textual loop for TextualRenderer (history + turn-dispatch wired, job-reap/clean-exit preserved); non-TUI input() path byte-unchanged; pilot proves submit→turn end-to-end.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| InputBar.Submitted → run_turn | submitted task string crosses into the agent loop / model |
| cli.py → interactive event loop | _run_repl now drives app.run_async; job-reap/cleanup must still run |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T8-10 | Denial of service | concurrent turn submission via TUI | mitigate | reuse EXISTING `register_turn_task` which raises on double-register while a turn is active — no new concurrency surface; action_interrupt (T1-06) still cancels |
| T-T8-11 | Tampering | bypassing job-reap / `.active-session` cleanup by changing the loop | mitigate | TUI branch wrapped inside the existing outer `try/finally`; `git diff` gate asserts the `finally` (lifecycle.reap_jobs + active-session unlink + keep_logs rmtree) is unmodified; non-TUI input() loop byte-unchanged |
| T-T8-12 | Spoofing | submitted value reaching run_turn unsanitized | accept | run_turn / permission gate is the established trust boundary for task input (unchanged by T8); InputBar forwards an opaque str exactly as the legacy `input()` loop did — no new trust assumption |
| T-T8-SC | Tampering | npm/pip installs | mitigate | no package installs in this plan (Plan 01 owns dev-dep install) |
</threat_model>

<verification>
- `pytest tests/harness/tui/ -q` exits 0 (full TUI suite — submit→turn, interrupt regression, non-TUI parity)
- `pytest tests/harness/tui/test_app_interrupt.py -q` exits 0 (T1-06 cancellation intact)
- `git diff voss/harness/cli.py` confirms input() loop + slash dispatch + job-reap finally unmodified (additive TUI branch only)
- A4 scope decision recorded in must_haves.truths and threat model (option a, enabling deliverable)
</verification>

<success_criteria>
- A4 decision recorded & accepted: TUI submit→run_turn wiring is an in-scope enabling deliverable
- on_input_bar_submitted dispatches via existing register_turn_task; on_local_event present for Plan-03 emit
- VossTUIApp.history holds the live per-project EpisodicMemory (Plan-05 corpus source)
- _run_repl drives interactive Textual loop for TextualRenderer; non-TUI input() path unchanged; job-reap/clean-exit preserved; T1-06 interrupt regression intact
</success_criteria>

<output>
Create `.planning/phases/T8-input-bar-ergonomics-v0-2/T8-04-SUMMARY.md` when done
</output>
