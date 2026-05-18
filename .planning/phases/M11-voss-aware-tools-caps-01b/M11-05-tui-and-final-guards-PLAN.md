---
phase: M11-voss-aware-tools-caps-01b
plan: 05
type: execute
wave: 5
depends_on: [M11-02, M11-03, M11-04]
files_modified:
  - voss/harness/tui/widgets/probable_modal.py
  - voss/harness/tui/widgets/budget_trace_modal.py
  - voss/harness/tui/widgets/voss_py_diff_modal.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/renderer.py
  - voss/harness/cli.py
  - tests/harness/tui/test_m11_modals.py
  - tests/harness/test_m11_acceptance.py
autonomous: true
requirements: [VTOOL-01, VTOOL-02, VTOOL-03, VTOOL-04, VTOOL-05]
---

<objective>
Add read-only TUI modal reuse for the three visual M11 surfaces and close the
phase with explicit no-emit acceptance tests. This is not an M9 region
amendment: no new side-panel allocation, no structural TUI grid change.
</objective>

<context>
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-CONTEXT.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-RESEARCH.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-PATTERNS.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-02-probable-budget-surfaces-PLAN.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-03-lint-schema-integration-PLAN.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-04-voss-python-diff-PLAN.md

Read first:
- `voss/harness/tui/widgets/confidence_bar.py`
- `voss/harness/tui/widgets/budget_meter.py`
- `voss/harness/tui/widgets/budget_modal.py`
- `voss/harness/tui/widgets/diff_modal.py`
- `voss/harness/tui/renderer.py`
- `tests/harness/tui/test_budget_modal.py`
- `tests/harness/tui/test_textual_renderer_protocol.py`
</context>

<threat_model>
TUI additions are display-only. They must not add accept/reject/apply actions,
must not alter the M9 region grid, and must not create a second source of
truth for inspector semantics. Plain CLI/slash output remains canonical, with
TUI modals wrapping already-rendered read-only content.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add read-only M11 modal widgets</name>
  <action>
    Add three widgets:

    - `ProbableInspectModal`: renders a title, `ConfidenceBar`, and the
      selected decision sequence text.
    - `BudgetTraceModal`: renders cumulative budget frames with `BudgetMeter`
      rows where a total is known; use text fallback when no total exists.
    - `VossPyDiffModal`: read-only two-pane/stacked source-vs-generated view.

    All three close with Escape. None has accept/reject/apply actions. Export
    them from `voss/harness/tui/widgets/__init__.py`.
  </action>
  <verify>
    <automated>python3 -m py_compile voss/harness/tui/widgets/probable_modal.py voss/harness/tui/widgets/budget_trace_modal.py voss/harness/tui/widgets/voss_py_diff_modal.py</automated>
  </verify>
  <done>Widgets import and do not alter the M9 region grid.</done>
</task>

<task type="auto">
  <name>Task 2: Wire renderer modal hooks without changing non-TUI semantics</name>
  <action>
    In `voss/harness/tui/renderer.py`, add optional methods:

    - `show_probable_inspector(text: str, confidence: float | None = None)`
    - `show_budget_trace(text: str, used: int = 0, total: int = 0)`
    - `show_voss_py_diff(text: str)`

    In `voss/harness/cli.py` slash handlers from M11-02/M11-04, when
    `ctx.renderer` has one of these methods, call it; otherwise keep printing
    to stdout. Do not change the click command output.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_repl_slash.py -k "m11 or btrace or vdiff or probable"</automated>
  </verify>
  <done>TUI can show modals opportunistically; plain CLI/slash output still works.</done>
</task>

<task type="auto">
  <name>Task 3: Add modal and final acceptance tests</name>
  <action>
    Create `tests/harness/tui/test_m11_modals.py`:

    - modal headings render
    - `ProbableInspectModal` includes a confidence value/bar
    - `BudgetTraceModal` includes cumulative tokens
    - `VossPyDiffModal` has no accept/reject/apply footer

    Create `tests/harness/test_m11_acceptance.py`:

    - all M11 tools are read-only
    - `/probable`, `/btrace`, `/vdiff` are registered
    - `/budget` is still registered and still describes USD budget behavior
    - lint schema consumer parses the live skill output
    - protected runtime/recorder files are not modified in git diff
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/tui/test_m11_modals.py tests/harness/test_m11_acceptance.py</automated>
  </verify>
  <done>Phase-level acceptance tests pass.</done>
</task>

<task type="auto">
  <name>Task 4: Run focused phase acceptance</name>
  <action>
    Run the M11 validation command set from `M11-VALIDATION.md`.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_voss_inspect.py tests/harness/test_voss_lint_schema.py tests/harness/test_voss_diff.py tests/harness/test_repl_slash.py tests/harness/test_tools.py tests/harness/tui/test_m11_modals.py tests/harness/test_m11_acceptance.py</automated>
    <automated>python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py</automated>
    <automated>python3 -m voss.cli check voss/harness/agent/</automated>
    <automated>python3 -m voss.cli vdiff voss/harness/agent/planner.voss</automated>
    <automated>git diff --check</automated>
  </verify>
  <done>M11 focused acceptance passes. If the broader suite is run and hits known outside-M11 blockers, document them in the summary without widening scope.</done>
</task>

</tasks>

<verification>
Run the full focused acceptance set from Task 4.
</verification>

<success_criteria>
- M11 visual surfaces have read-only TUI modal support without a region-grid
  amendment.
- CLI/slash/tool surfaces remain the source of behavior.
- The phase has an explicit no-emit guard.
</success_criteria>
