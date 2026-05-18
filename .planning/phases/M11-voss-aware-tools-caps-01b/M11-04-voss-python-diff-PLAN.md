---
phase: M11-voss-aware-tools-caps-01b
plan: 04
type: execute
wave: 4
depends_on: [M11-01, M11-02]
files_modified:
  - voss/harness/voss_diff.py
  - voss/harness/tools.py
  - voss/harness/cli.py
  - tests/harness/test_voss_diff.py
  - tests/harness/test_tools.py
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [VTOOL-04, VTOOL-05]
---

<objective>
Add the on-demand `.voss` to Python diff viewer. It must work on the harness's
own dogfood `.voss` files and arbitrary `.voss` files. It is read-only,
two-pane/source-vs-generated, and does not claim source-map precision.
</objective>

<context>
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-CONTEXT.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-RESEARCH.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-PATTERNS.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-02-probable-budget-surfaces-PLAN.md

Read first:
- `voss/cli.py` compile command and `_compile_source()`
- `voss/codegen.py` `generate_python()`
- `voss/harness/cache.py`
- `voss/harness/agent/planner.voss`
- `tests/codegen/test_examples.py`
</context>

<threat_model>
The diff viewer reads source and generated Python only. It must not write
generated artifacts durably, apply edits, or imply line-level source-map
precision. Path handling must stay cwd-jail aware through existing helpers or
explicit resolution checks, and `voss run` remains reserved for compiler
execution.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add `voss/harness/voss_diff.py` core</name>
  <action>
    Create helpers:

    - `resolve_generated_python(source: Path, *, cwd: Path) -> tuple[str, str]`
      returning `(origin_label, python_source)`.
    - `render_voss_py_diff(source: Path, *, cwd: Path, width: int = 120) -> str`.

    Behavior:
    - Require `.voss` suffix.
    - If `source` is under `voss/harness/agent/` and
      `.voss-cache/harness/<stem>.py` exists, read that cached artifact.
    - Otherwise parse/analyze/codegen in memory via public parser/analyzer/codegen
      APIs.
    - Render source and generated Python as bounded side-by-side or stacked
      sections. Include labels `Voss source` and `Generated Python`.
    - Do not write generated output to a durable path.
  </action>
  <verify>
    <automated>python3 -m py_compile voss/harness/voss_diff.py</automated>
  </verify>
  <done>Core can produce a read-only source-vs-generated view.</done>
</task>

<task type="auto">
  <name>Task 2: Add CLI, slash, and tool surface</name>
  <action>
    Add:

    - Click command `voss vdiff <file.voss> --cwd .`
    - Slash `/vdiff <file.voss>`
    - Tool `voss_py_diff(path: str) -> str`, `is_mutating=False`

    Reuse `render_voss_py_diff()`. Return/print concise errors for missing
    files, wrong suffix, parse/analyze failures, or missing source.
  </action>
  <verify>
    <automated>python3 -m voss.harness vdiff --help</automated>
  </verify>
  <done>Diff viewer is available through CLI, slash, and read-only tool.</done>
</task>

<task type="auto">
  <name>Task 3: Add diff tests, including dogfood file</name>
  <action>
    Create `tests/harness/test_voss_diff.py`.

    Cover:
    - a temporary simple `.voss` file renders generated Python without writing
      durable output
    - `voss/harness/agent/planner.voss` renders a view when cached artifact is
      present or falls back to in-memory generation cleanly
    - wrong suffix errors cleanly
    - output does not mention "source map" or "line mapped"

    Extend:
    - `tests/harness/test_tools.py`: add `voss_py_diff` read-only and update
      non-mutating count by +1 relative to M11-02.
    - `tests/harness/test_repl_slash.py`: assert `/vdiff` registration.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_voss_diff.py tests/harness/test_tools.py tests/harness/test_repl_slash.py</automated>
  </verify>
  <done>Focused tests pass, including dogfood diff acceptance.</done>
</task>

</tasks>

<verification>
Run:

```bash
python3 -m pytest -q tests/harness/test_voss_diff.py tests/harness/test_tools.py tests/harness/test_repl_slash.py
python3 -m voss.cli vdiff voss/harness/agent/planner.voss
python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py
git diff --check
```
</verification>

<success_criteria>
- VTOOL-04 is available on demand and works for dogfood `.voss`.
- No source map is claimed or generated.
- `voss_py_diff` is read-only and no new emit point is added.
</success_criteria>
