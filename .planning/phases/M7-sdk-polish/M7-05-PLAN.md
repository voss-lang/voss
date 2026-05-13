---
phase: M7-sdk-polish
plan: 05
type: execute
wave: 5
depends_on:
  - M7-04
files_modified:
  - voss_runtime/providers/__init__.py
  - voss_runtime/__init__.py
  - tests/test_agent.py
  - tests/eval/test_runner_options.py
  - tests/integration/test_classify_example.py
  - tests/integration/test_research_example.py
  - tests/integration/test_support_example.py
  - tests/codegen/test_examples.py
  - tests/examples/helpers.py
  - tests/providers/test_base.py
autonomous: true
requirements:
  - SDK-05
must_haves:
  truths:
    - "`voss_runtime.providers.register(name, provider)` (and the re-exported `voss_runtime.register_provider`) accepts a new `replace: bool = False` keyword-only argument."
    - "Calling `register(name, p)` (or `register_provider`) when `name` is already registered and `replace=False` raises `ValueError` with a message instructing the caller to pass `replace=True` (D-20)."
    - "Calling `register(name, p, replace=True)` overwrites the existing entry silently (preserves today's behavior under explicit opt-in)."
    - "Calling `register(name, p)` where `p` does NOT structurally implement `ModelProvider` raises `TypeError` (D-22 + R-07: Protocol is already `@runtime_checkable`)."
    - "`from voss_runtime import register_provider` succeeds; `register_provider` is the same callable as `voss_runtime.providers.register` (re-export, not a wrapper)."
    - "All 10 in-tree call sites identified in M7-RESEARCH §Q3 have been audited; the 8 test-code sites pass `replace=True` (module-load lines 32/33 stay unchanged because the registry is empty at import time)."
    - "After this plan, `pytest -x` (full suite) is green — no test goes red from the default-flip."
  artifacts:
    - path: "voss_runtime/providers/__init__.py"
      provides: "register gains replace kwarg + isinstance(ModelProvider) validation"
      contains: "replace: bool = False"
    - path: "voss_runtime/__init__.py"
      provides: "register_provider re-export + __all__ extended"
      contains: "register_provider"
    - path: "tests/providers/test_base.py"
      provides: "Coverage for collision raise, replace=True silent overwrite, isinstance validation"
      contains: "test_register_collision"
  key_links:
    - from: "voss_runtime/__init__.py"
      to: "voss_runtime/providers/__init__.py"
      via: "from voss_runtime.providers import register as register_provider"
      pattern: "register_provider"
    - from: "tests/examples/helpers.py register_stub"
      to: "voss_runtime.providers.register"
      via: "replace=True call (single high-leverage audit point per Pattern 10)"
      pattern: "register.*replace=True"
---

<objective>
**ATOMIC WAVE** — Stabilize the provider-registration entry point in one
non-splittable change set:

1. Add `replace: bool = False` keyword-only argument to
   `voss_runtime.providers.register`.
2. Default behavior on collision flips from silent overwrite to loud
   `ValueError` (D-20, M1 D-13 posture).
3. Add `isinstance(provider, ModelProvider)` validation (D-22 + R-07
   — the Protocol is already `@runtime_checkable`).
4. Re-export the function as `voss_runtime.register_provider` (long
   name disambiguates per R-08; bare `register` would shadow the
   submodule symbol).
5. Extend `voss_runtime/__init__.py` `__all__` with `"register_provider"`.
6. Audit and update ALL 10 in-tree call sites identified in M7-RESEARCH
   §Q3 to pass `replace=True` where overwrite is intentional.

Purpose: Embedders currently must reach into the private
`voss_runtime.providers` submodule with no public entry point. Closes
the "Plugin authoring (informal in v0.1)" gap in `docs/sdk.md` line 219.
Closes SDK-05.

**WHY THIS WAVE CANNOT SPLIT:** If the default-flip ships before the
test-site audit, the 8 test-code call sites that re-register `__stub__`
in pytest collide with the module-load registration and the test suite
goes red (Research Risk 3 + R-09). Splitting also breaks the audit
direction — auditing first with `replace=True` against an unchanged
function is harmless but only confirms the function still accepts the
extra kwarg. Combining all changes into one wave keeps CI green at
every commit boundary.

Output:
- `voss_runtime/providers/__init__.py` — `register` signature change +
  validation.
- `voss_runtime/__init__.py` — `register_provider` re-export + `__all__`
  extension.
- 8 test files updated (per audit table below).
- `tests/providers/test_base.py` — new coverage.

This is a promotion + behavior-flip plan. The behavior flip is bounded
to in-tree callers; the audit covers every site that depends on silent
overwrite.
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
@voss_runtime/providers/__init__.py
@voss_runtime/providers/base.py
@voss_runtime/__init__.py
@tests/examples/helpers.py

<interfaces>
Existing `register` at `voss_runtime/providers/__init__.py:10-11` (3
lines — current implementation):
```python
def register(name: str, provider: ModelProvider) -> None:
    _registry[name] = provider
```

Existing `ModelProvider` at `voss_runtime/providers/base.py:22-36`
ALREADY has `@runtime_checkable` (R-07 confirms). `isinstance(obj,
ModelProvider)` is supported today — no Protocol modification needed.

New signature (per D-19, D-20, D-22, R-07, R-08):
```python
def register(
    name: str,
    provider: ModelProvider,
    *,
    replace: bool = False,
) -> None: ...
```

Re-export in `voss_runtime/__init__.py`:
```python
from voss_runtime.providers import register as register_provider
```
Added alphabetically to the existing imports block. Add `"register_provider"`
to `__all__` between `"get_config"` and `"reset_config"` (lowercase tail
of the existing alphabetical sort — `register_provider` < `reset_config`
because `r-e-g` < `r-e-s`).

The 10 in-tree call sites (Pattern 10 / M7-RESEARCH §Q3):

| # | File:line | Current call | Required change |
|---|-----------|--------------|-----------------|
| 1 | `voss_runtime/providers/__init__.py:32` | `register("__default__", LiteLLMProvider())` | **No change** — module-load, registry empty |
| 2 | `voss_runtime/providers/__init__.py:33` | `register("__stub__", StubProvider())` | **No change** — module-load, registry empty (after #1, different key) |
| 3 | `tests/test_agent.py:26` | `register("agent-text-model", provider)` | Add `replace=True` (pytest may reuse same name across tests in same process) |
| 4 | `tests/test_agent.py:85` | `register("agent-structured-model", provider)` | Add `replace=True` |
| 5 | `tests/test_agent.py:99` | `register("agent-failing-model", provider)` | Add `replace=True` |
| 6 | `tests/test_agent.py:118` | `register("agent-tools-model", provider)` | Add `replace=True` |
| 7 | `tests/eval/test_runner_options.py:58` | `register("__eval_task_provider__", task_provider)` | Add `replace=True` |
| 8 | `tests/integration/test_classify_example.py:16` | `voss_runtime.providers.register("__stub__", stub)` | Add `replace=True` |
| 9 | `tests/integration/test_classify_example.py:25` | `voss_runtime.providers.register("__stub__", stub)` | Add `replace=True` |
| 10 | `tests/integration/test_research_example.py:20` | `voss_runtime.providers.register("__stub__", s)` | Add `replace=True` |
| 11 | `tests/integration/test_support_example.py:50` | `voss_runtime.providers.register("__stub__", stub)` | Add `replace=True` |
| 12 | `tests/codegen/test_examples.py:107` | `voss_runtime.providers.register("__stub__", stub)` | Add `replace=True` |
| 13 | `tests/examples/helpers.py:98` | `voss_runtime.providers.register("__stub__", stub)` (inside `register_stub` ctxmgr) | Add `replace=True` — covers most downstream tests transitively (Pattern 10) |
| 14 | `tests/examples/helpers.py:113` | Emitted source string `'voss_runtime.providers.register("__stub__", _stub)\n'` (in `_sitecustomize_source`) | Update the embedded string to `'voss_runtime.providers.register("__stub__", _stub, replace=True)\n'` |

Note: table shows 14 specific lines but rolls up to ~10 logical call
sites (test_agent.py has 4 lines, classify_example.py has 2).

Per R-09, the single highest-leverage audit point is
`tests/examples/helpers.py:98` (`register_stub` ctxmgr) — many tests
use this helper rather than calling `register` directly. If any of the
listed test files DOES use `register_stub` instead of inlining
`register`, that file may not need an additional change. Re-grep at
execution time to confirm:

```bash
grep -rn "voss_runtime\.providers\.register\|from voss_runtime\.providers import register\b" tests/ --include="*.py" | grep -v "register_provider\|register_stub"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Update register signature with replace kwarg + isinstance validation + ModelProvider check + tests</name>
  <files>voss_runtime/providers/__init__.py, tests/providers/test_base.py</files>
  <behavior>
    - `test_register_validates_provider_type`: pass a non-ModelProvider object (e.g. `object()`), assert `TypeError` raised. Assert the error message mentions `ModelProvider` so the caller knows what contract was violated.
    - `test_register_collision_raises_by_default`: `register("test-coll", StubProvider())`; calling `register("test-coll", StubProvider())` a second time raises `ValueError`. The message must contain `"test-coll"` AND `"replace=True"` (D-20 friendly-error contract). Use a fresh name like `"__m7_test_collision__"` so the test doesn't depend on `__stub__` state.
    - `test_register_replace_true_overwrites_silently`: same setup; the second `register("test-coll", new_provider, replace=True)` succeeds without raising. Assert `get("test-coll") is new_provider`.
    - `test_register_replace_true_on_fresh_name_still_works`: `register("brand-new-name", StubProvider(), replace=True)` succeeds even though the name is not yet registered — `replace=True` means "I accept overwrite if it would occur," not "an entry must already exist."
    - `test_register_provider_reexport_is_same_callable`: `from voss_runtime import register_provider; from voss_runtime.providers import register; assert register_provider is register`.
    - `test_module_load_registry_intact`: `from voss_runtime.providers import _registry, get` and assert `"__default__" in _registry and "__stub__" in _registry` (module-load calls succeeded under the new behavior because the registry is empty on the first call and the second call uses a different key).
    - `test_register_keyword_only_replace`: positional-replace fails. `register("name", StubProvider(), True)` raises `TypeError` because `replace` is keyword-only.

    Use a teardown fixture that pops the temporary names from `_registry`
    after each test so collisions don't leak across tests.
  </behavior>
  <action>
    Per D-19, D-20, D-22, R-07, R-08 — modify
    `voss_runtime/providers/__init__.py`:

    1. Update the `register` signature:
       ```python
       def register(
           name: str,
           provider: ModelProvider,
           *,
           replace: bool = False,
       ) -> None:
           """Register a provider. Raises ValueError if name is taken and replace=False.

           Validates that ``provider`` structurally implements
           ``ModelProvider`` via ``isinstance``. Pass ``replace=True`` to
           overwrite an existing entry intentionally.
           """
           if not isinstance(provider, ModelProvider):
               raise TypeError(
                   f"provider for {name!r} must implement ModelProvider Protocol; "
                   f"got {type(provider).__name__}"
               )
           if not replace and name in _registry:
               raise ValueError(
                   f"provider {name!r} is already registered; "
                   f"pass replace=True to overwrite"
               )
           _registry[name] = provider
       ```

    2. **Do not change** the module-load lines 32-33 (`register("__default__", ...)`,
       `register("__stub__", ...)`). They run on an empty registry and
       use distinct keys; both will succeed without `replace=True`
       (Research Q3 confirms).

    3. Add `tests/providers/test_base.py` (new file or extend existing
       if present — check first via `ls tests/providers/`). Provide
       teardown that calls `_registry.pop(name, None)` for any test-
       inserted names. Use `StubProvider` from `voss_runtime.providers`
       as the valid provider in tests.

    Do NOT change `has`, `get`, `_registry`, or the rest of the module.
    Do NOT modify `voss_runtime/providers/base.py` — R-07 confirms
    `@runtime_checkable` is already on `ModelProvider`.
  </action>
  <verify>
    <automated>pytest tests/providers/test_base.py -x -q</automated>
  </verify>
  <done>
    `tests/providers/test_base.py` passes. `register` raises on
    collision when `replace=False`. `register` raises `TypeError` on
    non-Protocol provider. Module-load behavior unchanged. `_registry`
    intact post-import.
  </done>
</task>

<task type="auto">
  <name>Task 2: Re-export register_provider + extend voss_runtime.__all__</name>
  <files>voss_runtime/__init__.py</files>
  <action>
    Per D-19, R-08 — add to the imports block in `voss_runtime/__init__.py`
    (immediately after the existing `from voss_runtime.providers import
    (...)` block, alphabetical position works fine; the existing block
    imports `ModelProvider, ProviderResponse, StubProvider`):

    ```python
    from voss_runtime.providers import register as register_provider
    ```

    Insert `register_provider` between `get_config` and `reset_config`
    in `__all__` (lowercase tail of existing alphabetical sort —
    `r-e-g-i-s` < `r-e-s-e-t`, so `register_provider` slots immediately
    after `get_config`):

    ```python
    __all__: list[str] = [
        ...
        "configure",
        "current_budget",
        "gather",
        "get_config",
        "register_provider",   # M7-05
        "reset_config",
        "run_with_budget",
        "tool",
    ]
    ```

    Do NOT modify the module docstring (Wave 6 / M7-06).

    Note: this task touches `voss_runtime/__init__.py` which is also
    touched by Wave 4 (M7-04). Per R-13, Wave 5 is sequential AFTER
    Wave 4 specifically to avoid this merge conflict. If M7-04 has
    landed first, it should NOT have changed `voss_runtime/__init__.py`
    (its scope is `voss_runtime/_config.py` only — `RuntimeConfig` is
    already exported). Confirm by inspecting `voss_runtime/__init__.py`
    at execution time; if M7-04 modified it unexpectedly, surface that
    as a scope-violation note in this plan's SUMMARY.
  </action>
  <verify>
    <automated>python -c "from voss_runtime import register_provider; from voss_runtime.providers import register; assert register_provider is register, 'not same callable'; print('ok')" | grep -q "^ok$"</automated>
  </verify>
  <done>
    `from voss_runtime import register_provider` succeeds.
    `register_provider is voss_runtime.providers.register` (same
    callable). `"register_provider"` is in `voss_runtime.__all__`. All
    26 prior names in `__all__` still present.
  </done>
</task>

<task type="auto">
  <name>Task 3: Audit + update all in-tree register call sites to pass replace=True</name>
  <files>tests/test_agent.py, tests/eval/test_runner_options.py, tests/integration/test_classify_example.py, tests/integration/test_research_example.py, tests/integration/test_support_example.py, tests/codegen/test_examples.py, tests/examples/helpers.py</files>
  <action>
    Per D-21, R-09, Risk 3 — update each call site listed in the
    `<interfaces>` audit table to pass `replace=True`.

    **Step 1 — Re-grep the live tree to confirm the audit set.** Before
    editing, run:
    ```bash
    grep -rn "voss_runtime\.providers\.register\|from voss_runtime\.providers import register\b" tests/ --include="*.py" | grep -v "register_provider\|register_stub"
    ```
    Confirm the listed 14 lines (across the 7 test files) match. If any
    additional call site has appeared since M7-RESEARCH was written
    (2026-05-13), add it to the audit. If any listed line has moved or
    been removed, adjust accordingly. Record the live audit set in the
    plan SUMMARY at the end.

    **Step 2 — Update each call site:**

    - `tests/test_agent.py` lines 26, 85, 99, 118: change
      `register("agent-text-model", provider)` → `register("agent-text-model", provider, replace=True)`. Same edit for the other 3 lines (different name strings).
    - `tests/eval/test_runner_options.py:58`: change
      `register("__eval_task_provider__", task_provider)` → `register("__eval_task_provider__", task_provider, replace=True)`.
    - `tests/integration/test_classify_example.py:16,25`: change
      `voss_runtime.providers.register("__stub__", stub)` → `voss_runtime.providers.register("__stub__", stub, replace=True)` on both lines.
    - `tests/integration/test_research_example.py:20`: same pattern.
    - `tests/integration/test_support_example.py:50`: same pattern.
    - `tests/codegen/test_examples.py:107`: same pattern.
    - `tests/examples/helpers.py:98` (inside `register_stub` ctxmgr):
      change `voss_runtime.providers.register("__stub__", stub)` → `voss_runtime.providers.register("__stub__", stub, replace=True)`. Per Pattern 10, this single change covers many downstream tests transitively.
    - `tests/examples/helpers.py:113` (inside `_sitecustomize_source`
      string template): update the embedded source string from
      `'voss_runtime.providers.register("__stub__", _stub)\n'`
      to `'voss_runtime.providers.register("__stub__", _stub, replace=True)\n'`.

    **Step 3 — Do NOT touch:**
    - `voss_runtime/providers/__init__.py:32-33` (module-load lines).
    - The `_registry` dict structure.
    - Any non-test code that calls `register` outside the M7 audit (if
      Step 1's grep surfaces such a caller, surface it in SUMMARY but
      do not change it without scoping a follow-up).

    **Step 4 — Run the full test suite as the atomicity gate.** After
    all edits in this wave are applied:
    ```bash
    pytest -x
    ```
    Full suite must pass. If a previously-passing test goes red because
    of an un-audited call site, fix it in this same plan (do not defer
    to a follow-up).

    **Executor note on the verify grep:** the verify command below
    excludes `replace=True` via a Perl-mode whitespace-tolerant regex
    (`replace\s*=\s*True`) to catch alternate spacings (`replace = True`,
    `replace= True`). It does NOT match multi-line call wrappings — if
    any line is flagged that looks like a false positive (e.g. a
    multi-line call where `replace=True` sits on the next line),
    inspect manually before failing the verify gate.
  </action>
  <verify>
    <automated>grep -rn "voss_runtime\.providers\.register\|from voss_runtime\.providers import register\b" tests/ --include="*.py" | grep -v "register_provider\|register_stub" | grep -Pv "replace\s*=\s*True" | grep -v "^[[:space:]]*#"</automated>
    <expected>Empty output (no unaudited call sites remain). If a line surfaces that wraps `replace=True` to the next physical line, inspect manually before treating as a fail.</expected>
  </verify>
  <done>
    Every audited call site passes `replace=True`. `pytest -x` (full
    suite) is green. No remaining unaudited `register(...)` call in
    `tests/` outside of comments and the `register_stub`/`register_provider`
    helpers. `voss_runtime/providers/__init__.py:32-33` unchanged.
  </done>
</task>

</tasks>

<verification>
- `pytest tests/providers/test_base.py -x` passes.
- `pytest -x` (full suite) passes (atomicity gate per R-12 / Risk 3).
- `python -c "import voss_runtime; assert voss_runtime.register_provider is voss_runtime.providers.register; print('ok')"` prints `ok`.
- `python -c "from voss_runtime import RuntimeConfig, StubProvider, register_provider; register_provider('m7-smoke', StubProvider()); from voss_runtime.providers import _registry; assert 'm7-smoke' in _registry; print('ok')"` prints `ok`.
- Manual grep: `grep -rn "voss_runtime\.providers\.register\b" tests/ --include="*.py" | grep -v "register_provider\|register_stub" | grep -Pv "replace\s*=\s*True" | grep -v "^[[:space:]]*#"` returns empty.
- No changes to `voss_runtime/providers/base.py` (regression check: `git diff voss_runtime/providers/base.py` empty).
- No changes to `voss_runtime/providers/__init__.py:32-33` (module-load lines).
- No changes to `tests/packaging/test_public_api.py` in this plan (Wave 6 / M7-06).
- No changes to `docs/sdk.md` in this plan (Wave 6 / M7-06).
</verification>

<success_criteria>
- `register` has a `replace: bool = False` keyword-only argument.
- Default collision behavior raises `ValueError` naming the offending key and pointing at `replace=True`.
- Non-ModelProvider providers raise `TypeError`.
- `register_provider` is exported from `voss_runtime` and is the same callable as `voss_runtime.providers.register`.
- All 10 in-tree call sites of `register` (excluding the 2 module-load lines) pass `replace=True`.
- `pytest -x` (full suite) is green at the end of this wave.
- `voss_runtime.__all__` contains `"register_provider"` and all 26 prior names.
- `_sitecustomize_source` in `tests/examples/helpers.py` emits the updated source string with `replace=True`.
- This wave landed as ONE atomic change set — no intermediate commit that has the default-flip without the audit (per R-09 / Risk 3).
</success_criteria>

<output>
After completion, create `.planning/phases/M7-sdk-polish/M7-05-SUMMARY.md`
documenting:
- The final live audit set (from Step 1's re-grep — may differ from the
  M7-RESEARCH table if new call sites appeared).
- The new `register` signature + error messages.
- Confirmation that `pytest -x` is green.
- Any scope-violation notes if M7-04 unexpectedly touched
  `voss_runtime/__init__.py` or if non-test code outside the audit
  table called `register`.
</output>
