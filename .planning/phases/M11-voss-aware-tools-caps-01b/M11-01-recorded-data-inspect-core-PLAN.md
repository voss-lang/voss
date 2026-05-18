---
phase: M11-voss-aware-tools-caps-01b
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/voss_inspect.py
  - tests/harness/test_voss_inspect.py
autonomous: true
requirements: [VTOOL-02, VTOOL-03, VTOOL-05]
---

<objective>
Create the pure recorded-data inspection core for M11. This plan adds no CLI,
slash, tool, or TUI surface. It only normalizes existing session/run records
and renders two read-only views:

- probable inspector data from `RunRecord.decisions[]`
- budget trace data from `RunRecord.iterations[]`

It must preserve the M11 D-01 downgrade verbatim: probable output is a
confidence-annotated decision sequence, not a propagation DAG; budget output is
an agent-iteration timeline, not per-`ctx(budget:)` frames.
</objective>

<context>
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-CONTEXT.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-RESEARCH.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-PATTERNS.md

Read first:
- `voss/harness/session.py` (`RunRecord`, `IterationRecord`, `SessionRecord`,
  `load`)
- `voss/harness/recorder.py` (`write_decisions_md`, `RunRecorder.end_iteration`)
- `tests/harness/test_session_iterations.py`
- `tests/harness/tui/test_no_new_runtime_hooks.py`
</context>

<threat_model>
Primary risk is accidental instrumentation creep. This plan must not edit
`voss/harness/recorder.py`, `voss_runtime/probable.py`,
`voss_runtime/budget.py`, or `voss_runtime/agent.py`; it reads persisted
session fields only. Output may contain user-authored decision bodies, but it
is printed/read-only and adds no new persistence path.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add `voss/harness/voss_inspect.py` pure data helpers</name>
  <action>
    Create `voss/harness/voss_inspect.py` with small dataclasses and pure
    functions:

    - `DecisionView(index, title, body, confidence, previous_index, next_index)`
    - `BudgetFrame(index, prompt_tokens, completion_tokens,
      cache_creation_input_tokens, cache_read_input_tokens, total_tokens,
      cumulative_tokens, cost_usd, exit_reason)`
    - `decision_sequence(run) -> list[DecisionView]`
    - `budget_timeline(run) -> list[BudgetFrame]`
    - `render_decision_sequence(run, decision_index=None) -> str`
    - `render_budget_timeline(run) -> str`
    - `load_run(cwd: Path, session_id_or_name: str, run_index: int = -1)`

    Implement a tiny `_get(obj, key, default=None)` normalizer so the helpers
    accept both dataclass instances and JSON-hydrated dictionaries. Do not
    import or edit `recorder.py`. Do not import `voss_runtime.probable` or
    `voss_runtime.budget`.
  </action>
  <verify>
    <automated>python3 -m py_compile voss/harness/voss_inspect.py</automated>
  </verify>
  <done>Module exists, imports cleanly, and contains no new persistence or emit path.</done>
</task>

<task type="auto">
  <name>Task 2: Add core inspector tests with synthetic records</name>
  <action>
    Create `tests/harness/test_voss_inspect.py`.

    Cover:
    - two decisions render in order with confidence values
    - selecting `decision_index=1` renders only that decision plus previous/next
      context labels
    - no decisions returns a clear no-data message
    - two iteration records produce correct per-frame and cumulative token
      totals, including cache token fields
    - `exit_reason="budget"` is visibly marked on the budget frame
    - JSON-dict shaped runs and dataclass-shaped runs both work
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_voss_inspect.py</automated>
  </verify>
  <done>Focused tests pass and prove the downgraded sequence/timeline semantics.</done>
</task>

<task type="auto">
  <name>Task 3: Verify no runtime/recorder emit points changed</name>
  <action>
    Run the existing runtime-surface guard and inspect git diff for the
    protected files.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py</automated>
    <automated>git diff -- voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py</automated>
  </verify>
  <done>The hash guard passes and protected-file diff is empty.</done>
</task>

</tasks>

<verification>
Run:

```bash
python3 -m pytest -q tests/harness/test_voss_inspect.py
python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py
python3 -m py_compile voss/harness/voss_inspect.py
git diff --check
```
</verification>

<success_criteria>
- VTOOL-02/03 have a shared core data model.
- Tests encode the no-DAG/no-scope-frame boundary.
- No changes to recorder or runtime primitive files.
</success_criteria>
