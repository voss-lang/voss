---
phase: M7-sdk-polish
plan: 02
type: execute
wave: 2
depends_on: []
files_modified:
  - voss/harness/tools.py
  - voss/harness/__init__.py
autonomous: true
requirements:
  - SDK-02
must_haves:
  truths:
    - "Embedders can write `from voss.harness import tool_entry_from_callable` and the import succeeds."
    - "`tool_entry_from_callable(my_async_fn, is_mutating=False)` returns a `ToolEntry` whose descriptor has name/description/parameters inferred identically to the existing `@tool` decorator."
    - "`tool_entry_from_callable(my_sync_fn, is_mutating=False)` returns a `ToolEntry` whose `await entry.invoke(**kwargs)` succeeds (sync callable wrapped in async shim per R-04)."
    - "Calling without `is_mutating=` raises `TypeError` (kwarg is required, no default — M1 D-06)."
    - "Inferred schema for `Optional[T]` parameters matches the existing `@tool` decorator's `nullable: True` dialect (R-03), not D-05's literal-text rule."
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "tool_entry_from_callable factory function delegating to voss_runtime.tool"
      contains: "def tool_entry_from_callable"
    - path: "voss/harness/__init__.py"
      provides: "Re-exports tool_entry_from_callable; __all__ extended"
      contains: "tool_entry_from_callable"
    - path: "tests/harness/test_tool_factory.py"
      provides: "Unit coverage for inference, async shim, required kwarg"
      contains: "test_factory_async_shim"
  key_links:
    - from: "voss/harness/tools.py tool_entry_from_callable"
      to: "voss_runtime.tool"
      via: "_tool_decorator(name=name, description=description)(fn)"
      pattern: "from voss_runtime import .*tool"
    - from: "voss/harness/__init__.py"
      to: "voss/harness/tools.py"
      via: "from .tools import ToolEntry, tool_entry_from_callable"
      pattern: "tool_entry_from_callable"
---

<objective>
Add `tool_entry_from_callable(fn, *, is_mutating, name=None, description=None,
parameters=None) -> ToolEntry` to `voss/harness/tools.py`. The factory
DELEGATES to the existing `@tool` decorator in `voss_runtime/tools.py:65-102`
for name/description/parameter inference (per R-02), and wraps sync
callables in an async shim before constructing the descriptor (per R-04).

Purpose: Embedders currently must author `ToolDescriptor` instances by
hand or use the `@tool` decorator (which doesn't carry `is_mutating`
data). The factory closes the "ToolEntry construction helpers" gap from
`docs/sdk.md` "Known gaps (closing in M7)". Closes SDK-02.

Output:
- `voss/harness/tools.py` — new `tool_entry_from_callable` function (~10
  LOC body) delegating to `voss_runtime.tool` for descriptor inference.
- `voss/harness/__init__.py` — `__all__` gains `tool_entry_from_callable`;
  import line extended.
- `tests/harness/test_tool_factory.py` (new) — unit coverage.

This is a promotion / thin-wrapper plan, not a re-implementation. No new
inference logic; no new schema dialect.
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
@voss/harness/tools.py
@voss/harness/__init__.py
@voss_runtime/tools.py

<interfaces>
Existing `ToolEntry` at `voss/harness/tools.py:14-41` (frozen dataclass,
do NOT modify):
```python
@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool
    # properties: name, description, parameters
    # methods: invoke(**kwargs), invoke_dict(args)
```

Existing `ToolDescriptor` at `voss_runtime/tools.py:41-62` (frozen
dataclass, do NOT modify):
```python
@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Any]
```

Existing `tool` decorator at `voss_runtime/tools.py:65-102` (do NOT
modify): infers name from `f.__name__`, description from first line of
`f.__doc__`, parameter schema via `_type_to_schema` + default-presence
controls `required`. This is what the factory delegates to.

New signature (per D-04 + R-02):
```python
def tool_entry_from_callable(
    fn: Callable[..., Any],
    *,
    is_mutating: bool,
    name: str | None = None,
    description: str | None = None,
    parameters: dict | None = None,
) -> ToolEntry: ...
```

The executor at `voss/harness/agent.py:430` always awaits
`entry.invoke(...)`. Sync callables MUST be wrapped before being passed
into the descriptor (R-04 / Risk 2). Without the shim, sync callables
crash with `TypeError: object str can't be used in 'await' expression`
on first invocation.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement tool_entry_from_callable factory with async shim and parameter override</name>
  <files>voss/harness/tools.py, tests/harness/test_tool_factory.py</files>
  <behavior>
    - `test_factory_infers_from_async_def`: define `async def foo(x: int, y: str = "z") -> str: """First doc line.\n\nMore."""`, call `tool_entry_from_callable(foo, is_mutating=False)`, assert returned `ToolEntry.name == "foo"`, `.description == "First doc line."`, `.parameters["properties"]["x"]["type"] == "integer"`, `.parameters["properties"]["y"]["type"] == "string"`, `.parameters["required"] == ["x"]`, `.is_mutating is False`.
    - `test_factory_async_shim`: define `def sync_fn(msg: str) -> str: return msg.upper()`, call `tool_entry_from_callable(sync_fn, is_mutating=False)`, then `result = await entry.invoke(msg="hi")`, assert `result == "HI"`. This proves the async shim works under the executor's `await entry.invoke(...)` contract.
    - `test_factory_requires_is_mutating`: calling `tool_entry_from_callable(foo)` (no `is_mutating`) raises `TypeError`. Verifies M1 D-06 (data not default).
    - `test_factory_optional_dialect`: define `async def f(x: int | None = None): ...`, assert returned `parameters["properties"]["x"]["nullable"] is True` AND `"x" not in parameters["required"]` (because it has a default — the default-presence rule controls `required`, not the Optional annotation per R-03).
    - `test_factory_name_description_overrides`: pass `name="custom"`, `description="custom desc"` and assert the descriptor reflects both overrides.
    - `test_factory_parameters_override`: pass an explicit `parameters={"type": "object", "properties": {"x": {"type": "string"}}, "required": []}` dict, assert the descriptor's parameters equal exactly that dict (overrides inference).
    - `test_factory_returns_tool_entry_with_is_mutating_true`: assert `tool_entry_from_callable(foo, is_mutating=True).is_mutating is True`.
  </behavior>
  <action>
    Per D-04, D-07, D-08, R-02, R-04 — add at the end of
    `voss/harness/tools.py` (after `_shell_capture`, module-level
    function, not nested):

    Required imports (add to the top-of-file import block, preserving
    existing order):
    - `import dataclasses` (for `dataclasses.replace`)
    - `import inspect` (for `inspect.iscoroutinefunction`)
    - `from typing import Callable` (the file already has `from typing import Any`)
    - `from voss_runtime import tool as _tool_decorator` (add to the existing `from voss_runtime import ToolDescriptor, tool` line — rename inline or add a second import alias)

    Function body (per the R-02 reference implementation in
    M7-RESEARCH.md §Q2, adapted):

    1. If `inspect.iscoroutinefunction(fn)` is `False`, wrap `fn` in an
       async shim: `async def _async_fn(**kwargs): return fn(**kwargs)`.
       Copy `__name__`, `__doc__`, `__annotations__` onto `_async_fn` so
       the `@tool` decorator infers correctly. Reassign `fn = _async_fn`.
    2. Construct descriptor by calling the existing decorator factory:
       `descriptor = _tool_decorator(name=name, description=description)(fn)`.
       This delegates ALL inference (description default, parameters
       schema, name default) to `voss_runtime.tool`.
    3. If `parameters is not None`, override:
       `descriptor = dataclasses.replace(descriptor, parameters=parameters)`.
       (`ToolDescriptor` is frozen, so use `replace`.)
    4. Return `ToolEntry(descriptor=descriptor, is_mutating=is_mutating)`.

    Total body: ~10 LOC excluding docstring. Add a docstring summarising
    the inference rules with a one-line pointer to `voss_runtime/tools.py`
    for the full inference truth (per D-08 "reading the source is the
    documentation"). The docstring's first line MUST be a single
    sentence so the existing `@tool` decorator's `first_line` extraction
    works when the function is itself inspected.

    Do NOT change `_type_to_schema`, `ToolDescriptor`, `ToolEntry`,
    `tool`, or `make_toolset`. Do NOT add a new schema-dialect path. The
    factory is a thin wrapper.

    Create `tests/harness/test_tool_factory.py` (new file) covering
    the seven behavior bullets above. Use `pytest.mark.asyncio` on the
    test that calls `await entry.invoke(...)`. Match the style of
    existing `tests/harness/test_*.py` files.
  </action>
  <verify>
    <automated>pytest tests/harness/test_tool_factory.py -x -q</automated>
  </verify>
  <done>
    `tests/harness/test_tool_factory.py` passes all seven tests.
    `tool_entry_from_callable` exists in `voss/harness/tools.py`.
    `inspect.iscoroutinefunction(tool_entry_from_callable)` is `False`
    (the factory itself is sync). The factory body is ≤ 20 LOC
    (excluding docstring). No new types or dialects introduced.
  </done>
</task>

<task type="auto">
  <name>Task 2: Promote tool_entry_from_callable in voss.harness.__all__</name>
  <files>voss/harness/__init__.py</files>
  <action>
    Extend the import block in `voss/harness/__init__.py`:
    `from .tools import ToolEntry, tool_entry_from_callable` (alphabetical
    within the names imported from `.tools`).

    Add `"tool_entry_from_callable"` to `__all__` in its alphabetical
    position (after `run_turn`, before any later-added names). After
    this plan, `__all__` size is 9 (8 baseline + 1). If M7-01 has
    already merged its `Renderer`/`NullRenderer` adds, the merged
    `__all__` is 11 (8 + 2 + 1). Coordinate alphabetically:

    ```python
    __all__ = [
        "NullRenderer",      # from M7-01 if merged
        "Plan",
        "PermissionGate",
        "Renderer",          # from M7-01 if merged
        "RunSemantics",
        "ToolCall",
        "ToolEntry",
        "TurnResult",
        "main",
        "run_turn",
        "tool_entry_from_callable",  # this plan
    ]
    ```

    Do NOT touch the stability docstring (Wave 6 / M7-06).
  </action>
  <verify>
    <automated>python -c "from voss.harness import tool_entry_from_callable; print('ok')" | grep -q "^ok$"</automated>
  </verify>
  <done>
    `from voss.harness import tool_entry_from_callable` succeeds.
    `"tool_entry_from_callable"` is in `voss.harness.__all__`. All
    existing 8 names still present.
  </done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_tool_factory.py -x` passes (Task 1 behavior).
- `python -c "from voss.harness import tool_entry_from_callable, ToolEntry; e = tool_entry_from_callable(lambda x: x, is_mutating=False, name='id'); print(e.name, e.is_mutating)"` prints `id False`.
- `python -c "from voss.harness import tool_entry_from_callable; tool_entry_from_callable(lambda x: x)"` raises `TypeError` (missing `is_mutating`).
- Manual grep: `grep -c "^def tool_entry_from_callable" voss/harness/tools.py` returns `1`.
- No drift in `voss_runtime/tools.py` (factory delegates, does not modify).
</verification>

<success_criteria>
- `tool_entry_from_callable` exists in `voss/harness/tools.py` and delegates inference to `voss_runtime.tool`.
- Sync callables work under `await entry.invoke(...)` (async shim wraps before descriptor construction).
- `is_mutating` is a required keyword-only argument (no default — M1 D-06).
- Optional[T] inference matches the existing `@tool` dialect (`nullable: True`, default controls `required`).
- `voss.harness.__all__` contains `"tool_entry_from_callable"`.
- No new types introduced; no new private surface introduced as a side effect.
- `tests/harness/test_tool_factory.py` covers inference, async shim, required-kwarg, override paths.
- No changes to `tests/packaging/test_public_api.py` in this plan (Wave 6 / M7-06).
- No changes to `docs/sdk.md` in this plan (Wave 6 / M7-06).
</success_criteria>

<output>
After completion, create `.planning/phases/M7-sdk-polish/M7-02-SUMMARY.md`
documenting the factory signature, delegation strategy (R-02), async
shim handling (R-04), and the seven test cases.
</output>
