---
phase: M9
plan: 04
type: execute
wave: 3
depends_on: [M9-02]
files_modified:
  - voss/harness/tui/widgets/sub_agent_panel.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/renderer.py
  - voss/harness/tui/app.py
  - voss/harness/tui/recorder_bridge.py
  - tests/harness/tui/test_recorder_bridge.py
  - tests/harness/tui/test_live_visualization.py
  - tests/harness/tui/test_no_new_runtime_hooks.py
  - tests/harness/tui/baseline/runtime_surface.sha256
autonomous: true
requirements: [TUI-04]
must_haves:
  truths:
    - "probable<T> values rendered via Renderer.show_clarify / show_plan / show_final produce ConfidenceBars at the locked tiers."
    - "ctx(budget:) drains live in StatusLine BudgetMeter as tokens are reported via Renderer.status."
    - "spawn opens a new SubAgentPanel in the side region; gather collapses panels with a one-line summary in the main pane."
    - "When the recorder lacks an event for a primitive, the TUI silently omits that visualization, does not crash, does not add a new runtime emit point."
    - "No new functions are added to voss/harness/recorder.py or voss_runtime/* in this plan; only consumers in voss/harness/tui/ are added."
  artifacts:
    - path: "voss/harness/tui/widgets/sub_agent_panel.py"
      provides: "SubAgentPanel widget; replaces M9-02 placeholder; header banner + mini status + scrollable body per UI-SPEC"
      exports: ["SubAgentPanel"]
    - path: "voss/harness/tui/recorder_bridge.py"
      provides: "RecorderBridge; consumes the RunRecorder shape (read-only) and translates observations into widget updates"
      exports: ["RecorderBridge"]
    - path: "tests/harness/tui/test_no_new_runtime_hooks.py"
      provides: "Hash-pinned regression test that asserts voss/harness/recorder.py and voss_runtime/{probable,budget,agent}.py are byte-unchanged vs baseline"
  key_links:
    - from: "voss/harness/tui/recorder_bridge.py"
      to: "voss/harness/recorder.py:RunRecorder"
      via: "RecorderBridge wraps a RunRecorder instance and READS its state after each agent step (no new emit point added)"
      pattern: "from voss.harness.recorder import RunRecorder"
    - from: "voss/harness/tui/renderer.py:TextualRenderer"
      to: "voss/harness/tui/widgets/sub_agent_panel.py"
      via: "TextualRenderer.show_subagent_start / show_subagent_end (new PRIVATE methods on TextualRenderer only; NOT added to the Renderer protocol)"
      pattern: "def show_subagent"
---

<objective>
Wire the live workflow visualization that makes the TUI the product face of Voss's language primitives per the unfair-advantage thesis. ConfidenceBars next to probable values, live BudgetMeter in the status line, SubAgentPanels in the side region for spawn/gather. Read-only: no new runtime emit points; if a primitive lacks a recorder event, the visualization degrades.

Purpose: TUI-04. This is the highest-leverage product feature in the phase per CONTEXT specifics ("visible-primitives are the highest-leverage product feature, not a side panel").

Output: SubAgentPanel widget + RecorderBridge consumer + extended TextualRenderer private methods + a regression test that pins the runtime surface so a future PR cannot quietly add a hook.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/notes/voss-agent-unfair-advantage.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@voss/harness/recorder.py
@voss/harness/render.py
@voss_runtime/probable.py
@voss_runtime/budget.py
@voss_runtime/agent.py

<interfaces>
<!-- RunRecorder fields the bridge reads (from voss/harness/recorder.py lines 27-44): -->
RunRecorder.id, .started_at, .inspected: list[str], .changed: list[str],
.validation: list[dict], .failures: list[dict], .cost_usd, .diff_summary,
.goal, .plan, .avoided, .assumptions, .decisions, .risks, .follow_ups

<!-- Renderer.show_* methods already carrying probable/budget signal: -->
- show_plan(plan, *, cost_usd) — plan.confidence: float
- show_clarify(question, confidence: float)
- show_final(text, *, confidence, cost_usd)
- status(*, model, tokens, cost_usd, ctx_pct)
- show_tool_call(name, args, summary, state)

<!-- Subagent indicator: read voss/harness/subagents.py to confirm the tool name string. The executor MUST grep for it rather than assume; if no marker exists, the spawn/gather visualization degrades to "no panel" and a status-line toast only. -->

<!-- This plan adds NO methods to the Renderer Protocol. -->
<!-- TextualRenderer-private methods (NOT in protocol): show_subagent_start, show_subagent_progress, show_subagent_end. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SubAgentPanel widget + RecorderBridge + runtime-surface hash baseline</name>
  <files>voss/harness/tui/widgets/sub_agent_panel.py, voss/harness/tui/widgets/__init__.py, voss/harness/tui/recorder_bridge.py, tests/harness/tui/test_recorder_bridge.py, tests/harness/tui/test_no_new_runtime_hooks.py, tests/harness/tui/baseline/runtime_surface.sha256</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/recorder.py (full file; every public attribute the bridge reads; observe() side effects we read AFTER it runs)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/subagents.py (find the spawn/gather tool name marker; if absent, the bridge degrades gracefully)
    - /Users/benjaminmarks/Projects/Voss/voss_runtime/probable.py, budget.py, agent.py (confirm attrs the bridge reads; baseline hash captures the current bytes)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Component Inventory" SubAgentPanel row; "Region grid" side-panel rules; "Live workflow visualization" table for spawn/gather visual treatment; "Empty side panel" copy = "Side panel hidden entirely (collapsed to 0 cols)")
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md ("Recorder integration mechanics" locks no new emit points)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/budget_meter.py (M9-02; reused inside SubAgentPanel)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02; extend with mount_subagent_panel and friends in Task 2)
  </read_first>
  <behavior>
    - Test (test_no_new_runtime_hooks): the test reads voss/harness/recorder.py, voss_runtime/probable.py, voss_runtime/budget.py, voss_runtime/agent.py and asserts their SHA-256 hashes match `tests/harness/tui/baseline/runtime_surface.sha256`. Captured on first run via env `UPDATE_BASELINE=1`. A failing test message names the changed file and tells the developer to either revert or run with `UPDATE_BASELINE=1` AND document in the M9-04 SUMMARY.
    - Test (test_recorder_bridge): given a RunRecorder, calling `recorder.observe("fs_read", {"path":"x"}, "ok", ok=True)` then `bridge.flush()` calls the app's `update_inspected(["x"])`. Bridge READS state; it does not patch RunRecorder.observe.
    - Test: a second flush with no new observations does NOT re-emit prior entries (idempotent; tracked by `_seen` indexes).
    - Test: when recorder records a validation row with `exit=0`, bridge calls `app.append_tool_line(summary, state="ok")` containing the cmd substring. With `exit != 0` → `state="error"`.
    - Test (SubAgentPanel mount): `SubAgentPanel(name="reviewer", parent_id="abc", budget_used=512, budget_total=2000)` renders header containing `reviewer` styled with class `agent-header` (which the TCSS binds to `$accent`), a BudgetMeter showing `0.5k / 2.0k`, empty body.
    - Test: SubAgentPanel.append_body("checked 3 files") adds one Static line inside the body container.
    - Test: SubAgentPanel.update_budget(1500) refreshes the embedded BudgetMeter to `1.5k / 2.0k` and re-renders.
  </behavior>
  <action>
    Create `voss/harness/tui/widgets/sub_agent_panel.py` with the SubAgentPanel class:
      - Inherits `textual.containers.Vertical`.
      - DEFAULT_CSS sets `border-left: $dim`, `padding: 1 2`, agent-header class colored `$accent` per UI-SPEC accent allow-list item 4.
      - compose() yields: Static(agent_name, classes="agent-header"), BudgetMeter(used, total, classes="mini-status"), Vertical(id=f"body-{parent_id}", classes="agent-body").
      - append_body(line: str) mounts a new Static into the body container.
      - update_budget(used: int) mutates the BudgetMeter and refreshes it.
      - The widget is removeable; on gather, the app calls `panel.remove()` and posts a `✓ gathered · {n} results` line to TurnView per UI-SPEC.

    Replace the M9-02 placeholder export in `voss/harness/tui/widgets/__init__.py` so SubAgentPanel is the real class.

    Create `voss/harness/tui/recorder_bridge.py` with the RecorderBridge class:
      - `__init__(self, recorder: RunRecorder, app)` stores both and initializes `_seen = {"inspected":0,"changed":0,"validation":0,"failures":0}`.
      - `flush(self) -> None` reads delta entries from each list since last flush, calls `app.call_from_thread(app.update_inspected, new_paths)` etc., advances `_seen`.
      - `flush_subagents(self, subagent_state: dict) -> None` (optional path; only called if voss/harness/subagents.py exposes a queryable state — if it does not, this method is a no-op and the executor documents the degradation in the M9-04 SUMMARY).
      - Pure consumer — does not import or modify recorder.py beyond the RunRecorder type.

    Capture the runtime baseline: write `tests/harness/tui/baseline/runtime_surface.sha256` with one `<hash> <relative-path>` line per file. Generated via `UPDATE_BASELINE=1` first run; committed bytes are the gate.

    Tests (5 in test_recorder_bridge.py, 1 in test_no_new_runtime_hooks.py, 3 SubAgentPanel mount tests in test_live_visualization.py per Task 2 — or split those into this task and Task 2 by widget vs renderer; keep widget tests here, renderer tests in Task 2).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; UPDATE_BASELINE=1 pytest tests/harness/tui/test_no_new_runtime_hooks.py -q 2&gt;/dev/null || true ; pytest tests/harness/tui/test_recorder_bridge.py tests/harness/tui/test_no_new_runtime_hooks.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.widgets import SubAgentPanel; from voss.harness.tui.recorder_bridge import RecorderBridge; print('ok')"` exits 0.
    - `wc -l tests/harness/tui/baseline/runtime_surface.sha256` returns >= 4 (one line per runtime file).
    - `grep -c "RunRecorder" voss/harness/tui/recorder_bridge.py` returns >= 1 (typed import).
    - `grep -rn "def observe\\|def absorb\\|def finalize" voss/harness/tui/` returns 0 lines (bridge does not duplicate or wrap the RunRecorder API; pure reader).
    - `git diff --quiet voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py` exits 0 (no runtime files changed in this task).
    - All tests pass; M9-01..03 tests still green.
  </acceptance_criteria>
  <done>SubAgentPanel mounts the locked region treatment. RecorderBridge reads RunRecorder state without mutating it. Runtime surface hash baseline is committed; a future PR that touches the runtime hooks fails the regression test.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: TextualRenderer private subagent methods + app DOM mutators + end-to-end visualization test</name>
  <files>voss/harness/tui/renderer.py, voss/harness/tui/app.py, tests/harness/tui/test_live_visualization.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/renderer.py (M9-02; TextualRenderer existing methods)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02; VossTUIApp; add the mutator methods that recorder_bridge calls into via call_from_thread)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/subagents.py (find the tool name marker for spawn detection inside show_tool_call)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (the Renderer Protocol; confirm we do NOT add subagent methods to it — the existing protocol shape stays as-is so PlainRenderer / JsonRenderer / TtyRenderer remain unchanged)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md ("Live workflow visualization" full table; "Accent reserved for" allow-list — item 4 is the active sub-agent name banner)
  </read_first>
  <behavior>
    - Test: TextualRenderer has private methods `show_subagent_start(name, parent_id, budget_total)`, `show_subagent_progress(parent_id, body_line, used)`, `show_subagent_end(parent_id, n_results)`; none of these names appear on the Renderer protocol in voss/harness/render.py.
    - Test: calling `renderer.show_subagent_start("reviewer", "abc", 2000)` inside `app.run_test()` results in a SubAgentPanel mounted under `#side`; `app.query_one("#side").display` becomes truthy (side region revealed).
    - Test: calling `renderer.show_subagent_end("abc", 3)` removes the panel and adds a `✓ gathered · 3 results` line in TurnView. When the last panel collapses, `#side` returns to hidden display.
    - Test (probable<T> visualization): `renderer.show_clarify("are you sure?", confidence=0.42)` appends a TurnView block whose body contains a ConfidenceBar widget at value=0.42 with the signal-error tier class.
    - Test (budget drain): `renderer.status(model="m", tokens=3000, cost_usd=0.5, ctx_pct=0.75)` updates the StatusLine; the embedded BudgetMeter reflects 75% drained with signal-warn class.
    - Test (graceful degradation): if `voss/harness/subagents.py` does not export the expected spawn marker constant (caught at import time), TextualRenderer.show_tool_call still functions normally; spawn detection silently returns False and no panel mounts. The renderer never raises ImportError up to the agent.
  </behavior>
  <action>
    Extend `voss/harness/tui/renderer.py` (TextualRenderer from M9-02) with three private methods that are NOT part of the Renderer protocol:
      - `show_subagent_start(name, parent_id, budget_total)` constructs a SubAgentPanel and calls `self.app.call_from_thread(self.app.mount_subagent_panel, panel)`.
      - `show_subagent_progress(parent_id, body_line, used)` calls `self.app.call_from_thread(self.app.update_subagent, parent_id, body_line, used)`.
      - `show_subagent_end(parent_id, n_results)` calls `self.app.call_from_thread(self.app.collapse_subagent, parent_id, n_results)`.

    Augment existing `show_tool_call(name, args, summary, state)`: if `name` equals the spawn marker imported from voss/harness/subagents.py (use `try: from voss.harness.subagents import SPAWN_TOOL_NAME except ImportError: SPAWN_TOOL_NAME = None` to satisfy the graceful-degradation behavior test), translate the call into `show_subagent_start` for `state=="pending"` or `show_subagent_end` for `state=="ok"`. Otherwise, fall through to the existing TurnView append.

    Augment existing `show_clarify(question, confidence)` and `show_final(text, *, confidence, cost_usd)`: append a ConfidenceBar widget alongside the body line. For show_final, pass `is_final=True` (UI-SPEC accent allow-list item 6); for show_clarify, pass `is_final=False`.

    Augment existing `status(...)`: pass `tokens` and total (computed from `ctx_pct` if no explicit total exists — assume `total = tokens / ctx_pct if ctx_pct else 1`; this is the only place a derived number is acceptable because the recorder does not emit an explicit budget total) into BudgetMeter.

    Add helper methods to `VossTUIApp`:
      - `mount_subagent_panel(panel: SubAgentPanel)` — `self.query_one("#side").mount(panel)`; toggles `#side.styles.display = "block"`.
      - `update_subagent(parent_id, body_line, used)` — query the matching panel by `parent_id`, call `panel.append_body(body_line)` and `panel.update_budget(used)`.
      - `collapse_subagent(parent_id, n_results)` — remove the matching panel; if `#side` now has zero panels, set `display = "none"`; append `✓ gathered · {n} results` to TurnView.
      - `update_inspected(paths: list[str])`, `append_tool_line(summary, state)` — used by RecorderBridge.

    Create `tests/harness/tui/test_live_visualization.py` with the 6 tests above. The graceful-degradation test uses `monkeypatch.delitem(sys.modules, "voss.harness.subagents", raising=False)` and reimports renderer to confirm no ImportError surfaces.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/tui/test_live_visualization.py tests/harness/tui/test_textual_renderer_protocol.py tests/harness/tui/test_recorder_bridge.py tests/harness/tui/test_no_new_runtime_hooks.py tests/harness/tui/test_plain_parity.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.renderer import TextualRenderer; from voss.harness.render import Renderer; from typing import get_type_hints; import inspect; ms = {n for n,_ in inspect.getmembers(Renderer, predicate=inspect.isfunction)}; assert 'show_subagent_start' not in ms and 'show_subagent_end' not in ms"` exits 0 — confirms protocol shape unchanged.
    - `grep -c "show_subagent" voss/harness/tui/renderer.py` returns >= 3 (three new private methods).
    - `grep -c "show_subagent" voss/harness/render.py` returns 0 (protocol untouched).
    - `git diff --quiet voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py` exits 0 (runtime files still unchanged).
    - All tests in this plan + prior plans pass.
  </acceptance_criteria>
  <done>Spawn/gather render as SubAgentPanels; probable values render as ConfidenceBars in clarify/final; budget drains live in StatusLine. Renderer protocol shape is byte-unchanged. Subagents import is optional — missing module degrades to no-panel without crashing.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| recorder.py → RecorderBridge | bridge reads dataclass state; no untrusted parsing of complex strings. |
| LLM-generated tool result strings → SubAgentPanel.append_body | LLM controls the line; rendered as Text(markup=False). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-04-01 | Tampering | LLM-injected ANSI in subagent body lines | mitigate | append_body wraps the input via `Text(line, markup=False, end="\n")` before mounting; verified by test injecting `\x1b[31mred\x1b[0m` and asserting rendered cell content is the literal escape, not a colored cell. |
| T-M9-04-02 | DoS | Recorder lists grow unbounded across long sessions | mitigate | RecorderBridge tracks `_seen` indexes; only iterates new entries. Memory grows linearly with session length, which is already true for RunRecord itself; no NEW memory pressure introduced. |
| T-M9-04-03 | Confused-deputy | Hash baseline drift | mitigate | test_no_new_runtime_hooks fails loudly with the offending filename; UPDATE_BASELINE env requires intentional opt-in. CI must NOT set UPDATE_BASELINE. |
</threat_model>

<verification>
- 9 tests across 3 files green.
- Hash baseline pins recorder.py + 3 runtime files.
- Renderer protocol shape unchanged (grep confirmed).
</verification>

<success_criteria>
1. SubAgentPanel mounts in the side region with accent-colored header per UI-SPEC.
2. ConfidenceBar appears in clarify/final blocks; tier color follows 0.85/0.50 thresholds.
3. StatusLine BudgetMeter drains live as `status()` is called.
4. test_no_new_runtime_hooks passes; runtime surface is byte-identical to baseline.
5. Renderer protocol in voss/harness/render.py is unchanged from M9-02.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-04-SUMMARY.md`.
</output>
