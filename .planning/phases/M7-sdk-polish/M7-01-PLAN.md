---
phase: M7-sdk-polish
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/render.py
  - voss/harness/__init__.py
autonomous: true
requirements:
  - SDK-01
must_haves:
  truths:
    - "Embedders can write `from voss.harness import Renderer, NullRenderer` and the import succeeds."
    - "`NullRenderer()` satisfies `isinstance(obj, Renderer)` (Protocol is `@runtime_checkable`-compatible via structural conformance)."
    - "Driving `run_turn` with `NullRenderer()` produces zero stdout/stderr output from the renderer."
    - "Existing 8-symbol harness public surface still imports without regression."
  artifacts:
    - path: "voss/harness/render.py"
      provides: "Renderer Protocol (existing line 24) + new NullRenderer class with 11 no-op methods"
      contains: "class NullRenderer"
    - path: "voss/harness/__init__.py"
      provides: "Re-exports Renderer and NullRenderer; __all__ extended"
      contains: "NullRenderer"
  key_links:
    - from: "voss/harness/__init__.py"
      to: "voss/harness/render.py"
      via: "from .render import Renderer, NullRenderer"
      pattern: "from .render import"
    - from: "tests/harness/test_renderers.py (new)"
      to: "voss.harness.NullRenderer / voss.harness.Renderer"
      via: "structural conformance assertion"
      pattern: "isinstance.*Renderer"
---

<objective>
Promote the existing `Renderer` Protocol (`voss/harness/render.py:24`) into
`voss.harness.__all__` AS-IS, and add a new `NullRenderer` class in the
same module whose 11 methods are pass-through no-ops. Both names become
part of the harness public surface.

Purpose: Embedders that want silent runs or custom rendering currently
import from the private `voss.harness.render` module (see existing example
in `docs/sdk.md` Quick start, which today reads `from voss.harness.render
import NullRenderer  # private path; example only`). This plan removes
that private-path workaround. Closes SDK-01.

Output:
- `voss/harness/render.py` — new `NullRenderer` class (11 no-op methods).
- `voss/harness/__init__.py` — `__all__` gains `Renderer` and `NullRenderer`;
  import line extended.

This is a promotion plan, not a feature plan. No new behavior beyond the
no-op class.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/M7-sdk-polish/M7-CONTEXT.md
@.planning/phases/M7-sdk-polish/M7-RESEARCH.md
@.planning/phases/M7-sdk-polish/M7-PATTERNS.md
@voss/harness/render.py
@voss/harness/__init__.py

<interfaces>
The `Renderer` Protocol already exists at `voss/harness/render.py:24-44`.
It has **11 methods** (R-01 corrects D-01's "9 methods" claim). All 11
must be implemented as no-ops by `NullRenderer`. Existing signatures
(copy these literally — keyword arguments and `Any` types preserved):

```python
class Renderer(Protocol):
    def banner(self, *, model: str, cwd: Path, git_status: str) -> None: ...
    def show_user(self, task: str) -> None: ...
    def show_thinking(self, label: str) -> None: ...
    def show_plan(self, plan: Any, *, cost_usd: float) -> None: ...
    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None: ...
    def show_clarify(self, question: str, confidence: float) -> None: ...
    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None: ...
    def status(self, *, model: str, tokens: int, cost_usd: float, ctx_pct: float) -> None: ...
    def show_cognition(self, *, architecture_tokens: int, constraints_count: int,
                       plans_loaded: int = 0, decisions_loaded: int = 0) -> None: ...
    def show_cognition_overflow(self, *, architecture_tokens: int, budget: int = 6000) -> None: ...
    def show_warning(self, msg: str) -> None: ...
```

The existing `PlainRenderer` at `voss/harness/render.py:175-224` is the
nearest precedent — `NullRenderer` mirrors its method list but every
method body is `pass` (no stderr writes, no stdout writes).

Current `voss/harness/__init__.py` `__all__` (8 names — do not regress):
`["Plan", "PermissionGate", "RunSemantics", "ToolCall", "ToolEntry",
"TurnResult", "main", "run_turn"]`. Target size after this plan: 10
(adds `Renderer`, `NullRenderer`). The remaining 4 names (`RunView`,
`SessionView`, `tool_entry_from_callable`, `view_session`) come in later
M7 plans.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add NullRenderer class + structural conformance test</name>
  <files>voss/harness/render.py, tests/harness/test_renderers.py</files>
  <behavior>
    - `NullRenderer()` constructs with no arguments.
    - Every one of the 11 Renderer Protocol methods returns `None` without raising.
    - Calling every method captures zero output on stdout AND zero output on stderr (assert via `capsys`).
    - `isinstance(NullRenderer(), Renderer)` returns `True` (Protocol structural check).
    - `PlainRenderer` and `TtyRenderer` are unchanged (regression: assert both still construct).
  </behavior>
  <action>
    Per D-02 + R-01: Add `class NullRenderer:` to `voss/harness/render.py`
    immediately after `JsonRenderer` (end of file is fine; module is
    flat). Body: 11 methods matching the `Renderer` Protocol signatures
    listed in the `<interfaces>` block. Every method body is a single
    `pass` statement. Method order should mirror the Protocol declaration
    order (`banner`, `show_user`, `show_thinking`, `show_plan`,
    `show_tool_call`, `show_clarify`, `show_final`, `status`,
    `show_cognition`, `show_cognition_overflow`, `show_warning`). No
    `__init__` needed — the class has no state.

    Decorate `Renderer` with `@runtime_checkable` (not currently
    decorated — `voss/harness/render.py:24` declares
    `class Renderer(Protocol):` with no decorator). This is required
    for `isinstance(NullRenderer(), Renderer)` assertions in the test.
    Note: R-07 confirms `ModelProvider` already has the decorator;
    `Renderer` is a separate Protocol that needs it added. Import path:
    `from typing import Protocol, runtime_checkable` (the file already
    imports `Protocol` at line 12 — extend the existing typing import).

    Create `tests/harness/test_renderers.py` (new file) covering the
    five behavior bullets above. Use `capsys` fixture for the
    stdout/stderr assertion. Use the unit-test style of the existing
    `tests/harness/*` directory (plain `def test_*`, no asyncio).
  </action>
  <verify>
    <automated>pytest tests/harness/test_renderers.py -x -q</automated>
  </verify>
  <done>
    `tests/harness/test_renderers.py` passes. `NullRenderer` has 11
    no-op methods. `isinstance(NullRenderer(), Renderer)` is `True`.
    Existing `voss/harness/render.py` tests (if any) still pass.
    Nothing else changed in `voss/harness/render.py`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Promote Renderer + NullRenderer in voss.harness.__all__</name>
  <files>voss/harness/__init__.py</files>
  <action>
    Per D-03: Add `from .render import NullRenderer, Renderer` to the
    import block in `voss/harness/__init__.py` (alphabetically before
    `from .tools import ToolEntry` is fine — match the existing block's
    grouping). Extend `__all__` from the current 8 names to 10 names by
    adding `"NullRenderer"` and `"Renderer"` in their alphabetical
    positions:

    ```python
    __all__ = [
        "NullRenderer",
        "Plan",
        "PermissionGate",
        "Renderer",
        "RunSemantics",
        "ToolCall",
        "ToolEntry",
        "TurnResult",
        "main",
        "run_turn",
    ]
    ```

    Do NOT promote `TtyRenderer` or `PlainRenderer` per D-03 — they
    stay private (CLI-internal renderer choices). Do NOT touch the
    module docstring in this task; the stability-docstring update is
    a Wave 6 (M7-06) task per R-12.

    Note: this task touches `voss/harness/__init__.py` which is also
    touched by waves 2/3 (M7-02/M7-03). Since waves 1-3 are parallel
    per R-13 and each only adds a single import + 2 `__all__` entries,
    coordinate by adding the names alphabetically — merge conflicts on
    `__init__.py` are mechanical and resolvable.
  </action>
  <verify>
    <automated>python -c "from voss.harness import Renderer, NullRenderer; r = NullRenderer(); print('ok' if isinstance(r, Renderer) else 'fail')" | grep -q "^ok$"</automated>
  </verify>
  <done>
    `from voss.harness import Renderer, NullRenderer` succeeds.
    `voss.harness.__all__` contains both names. The existing 8 names
    remain in `__all__`. `python -c "import voss.harness"` does not
    raise.
  </done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_renderers.py -x` passes (Task 1 behavior).
- `python -c "from voss.harness import Renderer, NullRenderer"` exits 0.
- `python -c "from voss.harness import Plan, PermissionGate, RunSemantics, ToolCall, ToolEntry, TurnResult, main, run_turn"` exits 0 (existing 8-symbol regression check).
- Manual grep: `grep -c "^class NullRenderer" voss/harness/render.py` returns `1`.
- Manual grep: `grep -E '"(Null)?Renderer"' voss/harness/__init__.py | wc -l` returns `2` or more (counts the entries in `__all__`).
</verification>

<success_criteria>
- `NullRenderer` exists in `voss/harness/render.py` with 11 no-op methods covering every method of the `Renderer` Protocol.
- `voss.harness.__all__` includes `"Renderer"` and `"NullRenderer"` and still includes all 8 prior names.
- `NullRenderer()` produces zero output on stdout and stderr when every method is invoked.
- `isinstance(NullRenderer(), Renderer)` is `True`.
- No changes to `TtyRenderer`, `PlainRenderer`, `JsonRenderer`, or `make_renderer`.
- No changes to `tests/packaging/test_public_api.py` in this plan (that's Wave 6 / M7-06).
- No changes to `docs/sdk.md` in this plan (that's Wave 6 / M7-06).
</success_criteria>

<output>
After completion, create `.planning/phases/M7-sdk-polish/M7-01-SUMMARY.md`
documenting the new `NullRenderer` class, the `__all__` extension, and any
notes about the structural conformance test (e.g., the addition of
`@runtime_checkable` to `Renderer`, which was absent in pre-M7 code).
</output>
