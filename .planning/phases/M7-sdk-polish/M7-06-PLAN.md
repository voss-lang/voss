---
phase: M7-sdk-polish
plan: 06
type: execute
wave: 6
depends_on:
  - M7-01
  - M7-02
  - M7-03
  - M7-04
  - M7-05
files_modified:
  - tests/packaging/test_public_api.py
  - tests/packaging/test_sdk_embedding.py
  - voss/harness/__init__.py
  - voss_runtime/__init__.py
  - docs/sdk.md
autonomous: true
requirements:
  - SDK-01
  - SDK-02
  - SDK-03
  - SDK-04
  - SDK-05
must_haves:
  truths:
    - "`EXPECTED_HARNESS_PUBLIC_API` in `tests/packaging/test_public_api.py` matches the live `voss.harness.__all__` (final size 14)."
    - "`EXPECTED_RUNTIME_PUBLIC_API` in `tests/packaging/test_public_api.py` matches the live `voss_runtime.__all__` (final size 27)."
    - "`tests/packaging/test_sdk_embedding.py` runs an end-to-end embedding using ONLY symbols from `voss.harness.__all__` and `voss_runtime.__all__` — no `voss.harness.render`, no `voss.harness.tools`, no `voss_runtime.providers.litellm_provider` imports. (One narrow allowed exception: `SessionRecord` from `voss.harness.session` is imported solely to construct projection input until the v0.2 `view_session(dict)` overload ships per R-06.)"
    - "The embedding test passes: builds a tool via `tool_entry_from_callable`, drives `run_turn` with `NullRenderer` + `StubProvider`, projects the resulting session via `view_session`, configures runtime via `RuntimeConfig.from_toml`, registers a provider via `register_provider`."
    - "`docs/sdk.md` 'Known gaps (closing in M7)' section shrinks from 4 items to zero (R-10)."
    - "`docs/sdk.md` 'Plugin authoring (informal in v0.1)' paragraph at line 219+ is rewritten to point at `register_provider` as a stable public entry point (R-10)."
    - "Stability docstrings on `voss/harness/__init__.py` and `voss_runtime/__init__.py` mention each new public name with a one-line semantic summary (D-26)."
    - "`pytest -x` (full suite) is green."
  artifacts:
    - path: "tests/packaging/test_public_api.py"
      provides: "EXPECTED_*_PUBLIC_API frozensets extended with M7 names"
      contains: "tool_entry_from_callable"
    - path: "tests/packaging/test_sdk_embedding.py"
      provides: "End-to-end M7 success contract — embedding via public symbols only"
      contains: "tool_entry_from_callable"
      min_lines: 80
    - path: "voss/harness/__init__.py"
      provides: "Stability docstring updated to describe new public surface"
      contains: "NullRenderer"
    - path: "voss_runtime/__init__.py"
      provides: "Stability docstring updated; register_provider documented"
      contains: "register_provider"
    - path: "docs/sdk.md"
      provides: "Known gaps section shrinks to zero; Plugin authoring para rewritten; Public surface tables extended"
      contains: "register_provider"
  key_links:
    - from: "tests/packaging/test_sdk_embedding.py"
      to: "voss.harness, voss_runtime (top-level only)"
      via: "explicit import block at top of file — no submodule reaches except the documented R-06 SessionRecord caveat"
      pattern: "from voss\\.harness import|from voss_runtime import"
    - from: "tests/packaging/test_public_api.py"
      to: "voss.harness.__all__, voss_runtime.__all__"
      via: "frozenset equality check"
      pattern: "EXPECTED_(HARNESS|RUNTIME)_PUBLIC_API"
    - from: "docs/sdk.md Known gaps section"
      to: "voss.harness.__all__, voss_runtime.__all__"
      via: "Public surface tables now list NullRenderer, Renderer, SessionView, RunView, tool_entry_from_callable, view_session, register_provider"
      pattern: "Public surface"
---

<objective>
Final integration wave for M7. Lands the M7 success contract:

- Drift entries: extend `tests/packaging/test_public_api.py`
  `EXPECTED_HARNESS_PUBLIC_API` and `EXPECTED_RUNTIME_PUBLIC_API`
  frozensets to match the new `__all__` content (Pattern 1 + D-23).
- End-to-end embedding test: new `tests/packaging/test_sdk_embedding.py`
  that exercises every M7 promotion using ONLY public symbols (D-24, the
  M7 success contract).
- Stability docstrings: update `voss/harness/__init__.py` and
  `voss_runtime/__init__.py` to describe the new public surface, with a
  one-line semantic summary per new name (D-26).
- `docs/sdk.md` updates: the "Known gaps (closing in M7)" section
  shrinks from 4 items to zero; the "Plugin authoring (informal in v0.1)"
  paragraph at line 219+ is rewritten to point at `register_provider`;
  the two "Public surface" tables gain rows for each new name; the
  Quick-start snippet at line ~155 (`from voss.harness.render import
  NullRenderer  # private path; example only`) is updated to
  `from voss.harness import NullRenderer` (R-10).

Purpose: This wave is the M7 acceptance proof. If `test_sdk_embedding.py`
passes with ONLY public-symbol imports, M7 has done its job (specifics
of CONTEXT.md / cross-cutting constraint 5).

Output:
- `tests/packaging/test_public_api.py` — frozensets extended.
- `tests/packaging/test_sdk_embedding.py` (new) — end-to-end test.
- `voss/harness/__init__.py` — docstring updated.
- `voss_runtime/__init__.py` — docstring updated.
- `docs/sdk.md` — Known gaps + Plugin authoring + Public surface tables
  + Quick-start snippet updated.

This is an integration plan that depends on every prior wave landing.
No new behavior introduced.
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
@tests/packaging/test_public_api.py
@tests/packaging/test_entrypoint.py
@voss/harness/__init__.py
@voss_runtime/__init__.py
@docs/sdk.md

<interfaces>
**Final public-surface deltas (locked by M7-CONTEXT.md D-23 + R-12):**

`EXPECTED_HARNESS_PUBLIC_API` — current 8 names → target 14 names. Add
the following 6 strings to the frozenset:
- `"NullRenderer"` (Wave 1)
- `"Renderer"` (Wave 1)
- `"RunView"` (Wave 3)
- `"SessionView"` (Wave 3)
- `"tool_entry_from_callable"` (Wave 2)
- `"view_session"` (Wave 3)

`EXPECTED_RUNTIME_PUBLIC_API` — current 26 names → target 27 names. Add:
- `"register_provider"` (Wave 5)

**`docs/sdk.md` known-gaps section (lines 194-215 today):**

Today lists 4 items: Renderer interface, ToolEntry construction helpers,
Session record types, Configuration via TOML. After M7, EACH of these 4
gets removed (the section either becomes empty or is replaced with a
"All M7 gaps shipped — see § Public surface" line).

**`docs/sdk.md` plugin-authoring paragraph (line 219+):**

Today says "implement `voss_runtime.ModelProvider` and register via
`voss_runtime.providers.register(...)` (currently a private call)". After
M7, this should say something like: "implement `voss_runtime.ModelProvider`
and register via `voss_runtime.register_provider(name, provider, *,
replace=False)`. The function raises `ValueError` if `name` is already
registered (loud-by-default); pass `replace=True` to overwrite
explicitly." (R-10)

**`docs/sdk.md` Quick-start snippet (around line 155):**

Today:
```python
from voss.harness.render import NullRenderer  # private path; example only
```
After:
```python
from voss.harness import NullRenderer
```
Also remove the "> Note: `NullRenderer` is a private name today" call-out
block at lines ~159-162 since the note is no longer accurate.

**`docs/sdk.md` Public surface tables:**

Two tables exist today — one for `voss_runtime` (around line 89), one for
`voss.harness` (around line 170). Each must gain a row for every new
public name. New rows (in alphabetical order to match existing style):

`voss.harness` table rows to add:
- `NullRenderer` | Silent no-op renderer; pass to `run_turn` for headless / test embedding.
- `Renderer` | Protocol describing the 11 render hooks `run_turn` invokes.
- `RunView` | Read-only per-turn projection (id, timestamps, goal, cost, confidence, diff_summary). Stable; the on-disk schema is not.
- `SessionView` | Read-only session projection (id, name, cwd, model, timestamps, total cost, runs tuple). Stable; the on-disk schema is not.
- `tool_entry_from_callable` | Factory: wrap a Python callable as a `ToolEntry`. `is_mutating` is required; sync callables are wrapped in an async shim.
- `view_session` | Pure projection from private `SessionRecord` → public `SessionView`.

`voss_runtime` table row to add:
- `register_provider` | Stable entry point for registering a custom `ModelProvider`. Raises on duplicate name unless `replace=True`.

**Stability docstrings (per D-26):**

`voss/harness/__init__.py` docstring currently lists `run_turn, Plan,
ToolCall, TurnResult` only. Extend to describe the 6 new names with
one-line semantic summaries — mirror the table-row text from
`docs/sdk.md`. Add a sentence noting M7 promotion provenance: "Names
added in M7 (Renderer, NullRenderer, tool_entry_from_callable,
SessionView, RunView, view_session) are stable per the SDK contract."

`voss_runtime/__init__.py` docstring currently mentions the embedding
API broadly. Add a one-line mention of `register_provider` and the
"loud collision; opt-in via `replace=True`" semantic. Add a sentence
noting M7 promotion provenance for `register_provider`.

**`tests/packaging/test_sdk_embedding.py` shape (per D-24 + M7-RESEARCH §Q7):**

The new file must:
1. Top-of-file explicit imports — if any symbol is missing from
   `__all__`, the file fails to import (fail-loud per Q7).
2. Use `@pytest.mark.asyncio` for the embedding flow.
3. Build a tool via `tool_entry_from_callable(sync_or_async_fn, is_mutating=False)`.
4. Drive `run_turn` with `NullRenderer()`, `StubProvider`, the built
   tool, and the `tmp_path` fixture for `cwd`.
5. Project a session via `view_session` (the test constructs a
   `SessionRecord` manually since `run_turn` does not persist a session
   on its own — `cli.py` does that). This is the one allowed private-
   path import, documented inline as the R-06 v0.2 caveat.
6. Load a TOML config via `RuntimeConfig.from_toml(tmp_path / "cfg.toml")`.
7. Register a stub provider via `register_provider(unique_name,
   stub)` — and prove registration with a positive `run_turn`
   resolution AND a raise-on-duplicate negative check.

The IMPORT-ONLY gate (no private paths) is implemented via a deterministic
allowlist scan (see Task 2 action), not by comment-walking.

Current StubProvider auto-fallback (M3 D-01) ensures the test does not
hit a real provider even if a system has `VOSS_*` env-vars set.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend EXPECTED_*_PUBLIC_API frozensets to match the live __all__</name>
  <files>tests/packaging/test_public_api.py</files>
  <action>
    Per D-23, Pattern 1. Extend the two frozensets at lines 14-43 and
    46-57.

    `EXPECTED_HARNESS_PUBLIC_API` — add the 6 strings (alphabetical
    order; the existing set is also alphabetical):
    - `"NullRenderer"`
    - `"Renderer"`
    - `"RunView"`
    - `"SessionView"`
    - `"tool_entry_from_callable"`
    - `"view_session"`

    Final 14-name set:
    ```python
    EXPECTED_HARNESS_PUBLIC_API: frozenset[str] = frozenset(
        {
            "NullRenderer",
            "Plan",
            "PermissionGate",
            "Renderer",
            "RunSemantics",
            "RunView",
            "SessionView",
            "ToolCall",
            "ToolEntry",
            "TurnResult",
            "main",
            "run_turn",
            "tool_entry_from_callable",
            "view_session",
        }
    )
    ```

    `EXPECTED_RUNTIME_PUBLIC_API` — add `"register_provider"` in
    alphabetical position. The existing list is alphabetical and
    `register_provider` < `reset_config` (r-e-g vs r-e-s), so it slots
    between `"get_config"` and `"reset_config"` (lowercase tail of the
    existing alphabetical sort). Final 27-name set:

    ```python
    EXPECTED_RUNTIME_PUBLIC_API: frozenset[str] = frozenset(
        {
            "AgentHandle",
            "BudgetExceededError",
            "BudgetScope",
            "ConfidenceTooLowError",
            "ContextScope",
            "EpisodicMemory",
            "ModelProvider",
            "ParseError",
            "ProbableValue",
            "ProviderError",
            "ProviderResponse",
            "RuntimeConfig",
            "SemanticMatcher",
            "SemanticMemory",
            "StubProvider",
            "ToolDescriptor",
            "VossAgent",
            "VossRuntimeError",
            "WorkingMemory",
            "configure",
            "current_budget",
            "gather",
            "get_config",
            "register_provider",
            "reset_config",
            "run_with_budget",
            "tool",
        }
    )
    ```

    Do NOT change the four test functions (lines 60-107). They already
    catch drift in either direction.
  </action>
  <verify>
    <automated>pytest tests/packaging/test_public_api.py -x -q</automated>
  </verify>
  <done>
    All four tests in `tests/packaging/test_public_api.py` pass.
    `EXPECTED_HARNESS_PUBLIC_API` size is 14. `EXPECTED_RUNTIME_PUBLIC_API`
    size is 27. Frozenset contents match live `__all__` exactly.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create tests/packaging/test_sdk_embedding.py — the M7 success contract</name>
  <files>tests/packaging/test_sdk_embedding.py</files>
  <behavior>
    The new file `tests/packaging/test_sdk_embedding.py` MUST contain
    exactly these seven test functions. Each behavior is locked.

    1. `test_public_api_imports_are_live` — pins every public name
       imported at the top of the file by referencing it once (calling
       `.__name__` on classes/functions, `callable()` on callables).
       This test exists specifically to defeat `ruff --fix` /
       `autoflake` stripping unused imports — every imported name is
       referenced live. If `__all__` regresses or a name disappears,
       this test fails BEFORE the static gate runs. Asserts each name
       resolves and is the expected callable/class.

    2. `test_no_private_path_imports_in_this_file` — a static
       allowlist check. Reads this file's own source via
       `Path(__file__).read_text()`. For every string in a
       `FORBIDDEN_PRIVATE_PATHS` module-level constant (defined at top
       of file), asserts the substring does NOT occur in the source.
       The constant is the deterministic gate — no comment-scanning,
       no in-line markers, just a literal substring check. The one
       sanctioned exception (`voss.harness.session.SessionRecord`,
       documented as the R-06 caveat) is NOT in the FORBIDDEN list, so
       the test does not flag it. Asserts the M7 "no private imports"
       gate per CONTEXT.md cross-cutting constraint 5.

    3. `test_runtime_config_from_toml` — write
       `[runtime]\ndefault_model="test-model"\nmax_retries=7\n` to
       `tmp_path/cfg.toml`. Call `cfg = RuntimeConfig.from_toml(...)`.
       Assert `cfg.default_model == "test-model"` and
       `cfg.max_retries == 7`. No teardown needed — `from_toml` does
       not mutate the singleton (per M7-04 D-15).

    4. `test_runtime_config_public_methods_pinned` — explicit
       hasattr/callable check on `RuntimeConfig.from_toml` and
       `RuntimeConfig.default`. These classmethods are reachable
       through the exported `RuntimeConfig` class but are NOT in
       `__all__`. This test pins them so a future refactor that
       silently removes either method breaks a test, not just docs
       (Warning 1 fix).

    5. `test_register_provider_via_public_name` — proves the
       raise-on-duplicate semantic only:
       ```python
       def test_register_provider_via_public_name(unique_provider_name):
           register_provider(unique_provider_name, StubProvider())
           with pytest.raises(ValueError, match="already registered"):
               register_provider(unique_provider_name, StubProvider())
       ```
       The `unique_provider_name` fixture (defined at top of file)
       returns `f"m7-test-{uuid.uuid4().hex[:8]}"` so no two tests
       collide and no teardown is needed. Positive registration proof
       lives in `test_end_to_end_embedding` (Test 7); a comment in
       this test body cross-references it: `# Positive registration
       proof lives in test_end_to_end_embedding (which uses
       register_provider then resolves the name via run_turn).`

    6. `test_view_session_via_public_name` — constructs a minimal
       `SessionRecord` (imported from `voss.harness.session` with an
       inline `# R-06 caveat: SessionRecord input is private until
       v0.2 view_session(dict) overload ships` comment for reader
       guidance — the FORBIDDEN allowlist does NOT include
       `voss.harness.session`). Calls `view = view_session(record)`.
       Asserts `isinstance(view, SessionView)` and that the view's
       public fields (`id`, `name`, `cwd`, etc.) match the constructed
       record. The test docstring states: "Demonstrates `view_session`
       projects a session into the public `SessionView`. The
       `SessionRecord` input type will gain a dict overload in v0.2
       (R-06); until then, this test imports the private type
       directly. This is the sole sanctioned private-path import in
       this file."

    7. `test_end_to_end_embedding` (`@pytest.mark.asyncio`,
       parameter `unique_provider_name`, parameter `tmp_path`,
       parameter `capsys`):
       1. Define `async def echo_tool(msg: str) -> str: return f"echo: {msg}"`.
          Wrap via `entry = tool_entry_from_callable(echo_tool, is_mutating=False)`.
       2. Register a stub:
          `register_provider(unique_provider_name, StubProvider(default_response="m7 says hi"))`.
       3. Configure via `configure(default_model=unique_provider_name)`.
       4. Build tools dict: `tools = {"echo": entry}`.
       5. Call `result = await run_turn(task="say hi", tools=tools,
          cwd=tmp_path, renderer=NullRenderer(),
          permissions=PermissionGate(mode="plan"),
          confidence_threshold=0.6, token_budget=60_000)`.
       6. Assert `isinstance(result, TurnResult)`,
          `result.cost_usd >= 0`, and `capsys.readouterr().out == ""`
          and `capsys.readouterr().err == ""` (NullRenderer emitted
          nothing).
       7. Teardown: `reset_config()` in a `try/finally`.

       Add an explicit cross-reference comment at the registration
       site: `# Registration positive proof: run_turn below resolves
       "{unique_provider_name}" via the registered provider. If
       registration silently no-op'd, run_turn would raise
       provider-not-found.` (Blocker 2 fix.)

    All assertions use only names listed in the two top-of-file
    import blocks plus `pytest`, `pathlib.Path`, `uuid`, and stdlib
    helpers.
  </behavior>
  <action>
    Per D-24, R-10, M7-RESEARCH §Q7, cross-cutting constraint 5.

    Create `tests/packaging/test_sdk_embedding.py` (new file).

    **Top-of-file structure (literal):**

    ```python
    """M7 end-to-end SDK embedding test — the M7 success contract.

    This file imports ONLY from `voss.harness.__all__` and
    `voss_runtime.__all__`, with ONE documented exception:
    `SessionRecord` from `voss.harness.session` is imported in
    `test_view_session_via_public_name` to construct projection input
    until the v0.2 `view_session(dict)` overload ships (R-06).

    No other submodule reaches. The `test_no_private_path_imports_in_this_file`
    test enforces this via a deterministic allowlist scan over this
    file's own source.

    Closes the M7 phase verification per CONTEXT.md D-24 and
    cross-cutting constraint 5.
    """
    from __future__ import annotations

    import uuid
    from pathlib import Path

    import pytest

    from voss.harness import (
        NullRenderer,  # noqa: F401  M7 public-API import gate — do not remove
        PermissionGate,  # noqa: F401  M7 public-API import gate — do not remove
        Plan,  # noqa: F401  M7 public-API import gate — do not remove
        Renderer,  # noqa: F401  M7 public-API import gate — do not remove
        RunSemantics,  # noqa: F401  M7 public-API import gate — do not remove
        RunView,  # noqa: F401  M7 public-API import gate — do not remove
        SessionView,  # noqa: F401  M7 public-API import gate — do not remove
        ToolCall,  # noqa: F401  M7 public-API import gate — do not remove
        ToolEntry,  # noqa: F401  M7 public-API import gate — do not remove
        TurnResult,  # noqa: F401  M7 public-API import gate — do not remove
        main,  # noqa: F401  M7 public-API import gate — do not remove
        run_turn,  # noqa: F401  M7 public-API import gate — do not remove
        tool_entry_from_callable,  # noqa: F401  M7 public-API import gate — do not remove
        view_session,  # noqa: F401  M7 public-API import gate — do not remove
    )
    from voss_runtime import (
        RuntimeConfig,  # noqa: F401  M7 public-API import gate — do not remove
        StubProvider,  # noqa: F401  M7 public-API import gate — do not remove
        configure,  # noqa: F401  M7 public-API import gate — do not remove
        register_provider,  # noqa: F401  M7 public-API import gate — do not remove
        reset_config,  # noqa: F401  M7 public-API import gate — do not remove
    )

    # R-06 caveat: SessionRecord input is private until v0.2 ships
    # the view_session(dict) overload. The one sanctioned private-
    # path import in this file. NOT in FORBIDDEN_PRIVATE_PATHS below.
    from voss.harness.session import SessionRecord  # noqa: F401


    # ------------------------------------------------------------------
    # Static gate — deterministic allowlist of private paths that must
    # NEVER appear in this file's source. The `test_no_private_path_imports_in_this_file`
    # test reads __file__ and asserts each substring is absent.
    #
    # Explicit sanctioned exception (R-06): voss.harness.session.SessionRecord
    # is required to construct projection input until v0.2 ships
    # view_session(dict) overload. NOT included in this FORBIDDEN list.
    # ------------------------------------------------------------------
    FORBIDDEN_PRIVATE_PATHS = [
        "voss.harness.render",
        "voss.harness.tools",
        "voss.harness.agent",
        "voss.harness.cli",
        "voss.harness.permissions",
        "voss_runtime.providers.litellm_provider",
        "voss_runtime.providers.stub",
        "voss_runtime.providers.base",
        "voss_runtime.providers._registry",
        "voss_runtime._config",
    ]


    @pytest.fixture
    def unique_provider_name() -> str:
        """Returns a UUID-suffixed provider name unique per test, so
        register_provider collisions cannot leak across tests in the
        same process. No teardown needed.
        """
        return f"m7-test-{uuid.uuid4().hex[:8]}"
    ```

    Note: `voss_runtime.providers._registry` is included in the FORBIDDEN
    list. No test in this file may reach the private registry directly
    (Blocker 3 closeout — UUID-suffixed names plus the
    raise-on-duplicate semantic mean no teardown needs the registry).

    **Test bodies — implement each per the seven `<behavior>` bullets above.**

    `test_public_api_imports_are_live` reference implementation:
    ```python
    def test_public_api_imports_are_live():
        """Pin every public name imported at top-of-file. If __all__
        regresses or a name disappears, this test fails before the
        static gate even runs. Defeats `ruff --fix` / `autoflake`
        stripping unused imports (Blocker 4)."""
        assert run_turn.__name__ == "run_turn"
        assert Plan.__name__ == "Plan"
        assert PermissionGate.__name__ == "PermissionGate"
        assert NullRenderer.__name__ == "NullRenderer"
        assert Renderer.__name__ == "Renderer"
        assert RunView.__name__ == "RunView"
        assert SessionView.__name__ == "SessionView"
        assert tool_entry_from_callable.__name__ == "tool_entry_from_callable"
        assert view_session.__name__ == "view_session"
        assert ToolCall.__name__ == "ToolCall"
        assert ToolEntry.__name__ == "ToolEntry"
        assert TurnResult.__name__ == "TurnResult"
        assert RunSemantics.__name__ == "RunSemantics"
        assert callable(main)
        # voss_runtime public
        assert RuntimeConfig.__name__ == "RuntimeConfig"
        assert callable(configure)
        assert callable(reset_config)
        assert StubProvider.__name__ == "StubProvider"
        assert callable(register_provider)
    ```

    `test_no_private_path_imports_in_this_file` reference implementation:
    ```python
    def test_no_private_path_imports_in_this_file():
        """Deterministic substring scan over this file's own source.
        No comment-walking; no inline markers. Just an allowlist of
        forbidden submodule paths. The one sanctioned exception
        (voss.harness.session.SessionRecord per R-06) is NOT in
        FORBIDDEN_PRIVATE_PATHS, so this test does not flag it.
        """
        source = Path(__file__).read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_PRIVATE_PATHS:
            assert forbidden not in source, (
                f"Forbidden private path {forbidden!r} found in "
                f"{Path(__file__).name}; M7 public-API gate violation."
            )
    ```

    `test_runtime_config_public_methods_pinned` reference implementation
    (Warning 1 fix — pins SDK-04 classmethods even though they are not
    in `__all__`):
    ```python
    def test_runtime_config_public_methods_pinned():
        """SDK-04 classmethods are not in __all__ (they're on the
        exported class). Pin them here so future removal breaks a
        test, not just docs."""
        assert hasattr(RuntimeConfig, "from_toml")
        assert hasattr(RuntimeConfig, "default")
        assert callable(RuntimeConfig.from_toml)
        assert callable(RuntimeConfig.default)
    ```

    The remaining four tests (`test_runtime_config_from_toml`,
    `test_register_provider_via_public_name`,
    `test_view_session_via_public_name`, `test_end_to_end_embedding`)
    follow the behavior bullets verbatim. Use `@pytest.mark.asyncio`
    on the embedding test. `pytest-asyncio` is configured globally
    via `pyproject.toml [tool.pytest.ini_options]`.

    Reference existing test style in `tests/packaging/test_entrypoint.py`
    (Pattern 7) for layout / fixture usage.

    Total file: ~150-180 LOC including docstrings and fixtures.
  </action>
  <verify>
    <automated>pytest tests/packaging/test_sdk_embedding.py -x -q</automated>
  </verify>
  <done>
    `tests/packaging/test_sdk_embedding.py` passes. All seven tests
    succeed. The end-to-end embedding test produces a `TurnResult`
    from `run_turn` driven via the new public surface. The static
    allowlist gate passes (no forbidden private path in this file's
    source). The R-06 caveat (one `SessionRecord` import) is
    documented inline and explicitly omitted from
    `FORBIDDEN_PRIVATE_PATHS`. Imports are pinned by
    `test_public_api_imports_are_live` so linters cannot strip them.
  </done>
</task>

<task type="auto">
  <name>Task 3: Update stability docstrings on both __init__.py files</name>
  <files>voss/harness/__init__.py, voss_runtime/__init__.py</files>
  <action>
    Per D-26, R-10.

    **`voss/harness/__init__.py`** — extend the module docstring (lines
    1-28 today). Add a "## Public surface" subsection that mirrors the
    `docs/sdk.md` Public surface table, in markdown-list form:

    ```text
    Public surface (M7-stabilized; see ``docs/sdk.md`` for versioning):

    Names below are the only harness symbols covered by the public-API
    stability contract.

    - ``run_turn`` — run one agent turn; returns a ``TurnResult``.
    - ``Plan``, ``ToolCall`` — Pydantic schemas the planner returns.
    - ``TurnResult`` — dataclass returned from ``run_turn``.
    - ``RunSemantics`` — closing-turn semantics from the privileged
      ``record_run`` call.
    - ``PermissionGate`` — tier-mapped gate for tool calls
      (``plan`` / ``edit`` / ``auto``).
    - ``ToolEntry`` — single registry entry pairing a
      ``ToolDescriptor`` with ``is_mutating``.
    - ``tool_entry_from_callable`` — factory: wrap a Python callable
      as a ``ToolEntry`` (M7).
    - ``Renderer`` — Protocol describing the 11 render hooks
      ``run_turn`` invokes (M7).
    - ``NullRenderer`` — silent no-op renderer (M7).
    - ``SessionView``, ``RunView`` — read-only embedder projection
      types (M7).
    - ``view_session`` — pure projection from private
      ``SessionRecord`` → ``SessionView`` (M7).
    - ``main`` — CLI entry point.
    ```

    Append "(M7)" to each name added in this phase to record promotion
    provenance per D-26. Preserve the existing "Embed Voss" usage
    examples — extend them so the snippets use the new public names
    rather than the private path. Specifically: change the existing
    `from voss.harness import run_turn, Plan, ToolCall, TurnResult`
    snippet to also import `NullRenderer` if the embedded example uses
    a renderer.

    **`voss_runtime/__init__.py`** — extend the module docstring. Add
    a one-line mention of `register_provider`:

    ```text
    Plugin authoring:

    - ``register_provider(name, provider, *, replace=False)`` — stable
      entry point for registering a custom ``ModelProvider``. Raises
      ``ValueError`` if ``name`` is already registered unless
      ``replace=True`` (M7).
    ```

    Add a sentence noting "M7 promotion provenance" (D-26) — e.g.
    "``register_provider`` was promoted from the private
    ``voss_runtime.providers.register`` path in M7."

    Do NOT change `__all__` in either file. (M7-01..05 plans already
    handled the `__all__` extensions; this task is docstring-only.)
  </action>
  <verify>
    <automated>python -c "import voss.harness; import voss_runtime; assert 'M7' in (voss.harness.__doc__ or ''), 'harness docstring missing M7 mention'; assert 'register_provider' in (voss_runtime.__doc__ or ''), 'runtime docstring missing register_provider'; print('ok')" | grep -q "^ok$"</automated>
  </verify>
  <done>
    Both module docstrings mention each new public name with a one-line
    summary. M7 promotion provenance noted. Existing usage examples
    updated to use the new public surface. No `__all__` changes in this
    task.
  </done>
</task>

<task type="auto">
  <name>Task 4: Update docs/sdk.md — Known gaps to zero, Plugin authoring rewrite, Public surface tables</name>
  <files>docs/sdk.md</files>
  <action>
    Per D-25, R-10, M7-RESEARCH §Q7 / Risk 7.

    **Edit 1 — `## Known gaps (closing in M7)` section (lines 194-215
    today):** Replace the entire body of this section with a single
    sentence:

    ```markdown
    ## Known gaps

    All M7-tracked public-API gaps shipped in v0.1 / M7. See the
    "Public surface" tables above for the current API. Future v0.2+
    candidates (TS/JS SDK, HTTP / remote SDK, formal plug-in framework)
    are listed in `.planning/ROADMAP.md` §"v0.2 Candidate Phases".
    ```

    The header rename (`Known gaps (closing in M7)` → `Known gaps`)
    keeps the anchor stable for inbound links while signalling the
    section is now informational rather than a TODO list.

    **Edit 2 — `## Plugin authoring (informal in v0.1)` section (line
    219+):** Rewrite the Providers bullet:

    Before:
    > - **Providers** — implement `voss_runtime.ModelProvider` and
    >   register via `voss_runtime.providers.register(...)` (currently
    >   a private call). [...]

    After:
    > - **Providers** — implement `voss_runtime.ModelProvider` and
    >   register via the stable public entry point
    >   `voss_runtime.register_provider(name, provider, *, replace=False)`.
    >   The function raises `ValueError` on duplicate name unless
    >   `replace=True` is passed (loud-by-default). For v0.1, in-tree
    >   providers (`anthropic`, `openai`, `__stub__`, litellm pass-
    >   through) are the supported set.

    Also rename the section header from "Plugin authoring (informal in
    v0.1)" to "Plugin authoring" — the provider entry point is now
    formal; only the rest of the plug-in surface (entry-points,
    manifest, sandboxed loading) remains informal v0.1.

    **Edit 3 — Quick-start snippet (around line 155 — `from
    voss.harness.render import NullRenderer  # private path; example
    only`):**

    Before:
    ```python
    from voss.harness.render import NullRenderer  # private path; example only
    ```
    > Note: `NullRenderer` is a private name today. Promote-to-public
    > is a known follow-up — until then, callers either pass a real
    > `Renderer` or supply a minimal stub. See "Known gaps" below.

    After:
    ```python
    from voss.harness import NullRenderer
    ```
    (Drop the `> Note:` callout entirely.)

    **Edit 4 — Public surface table for `voss_runtime` (around line 89):**

    Add this row (alphabetical position — somewhere between the
    `RuntimeConfig` row and the `ModelProvider` row, or wherever
    alphabetical sort places it):

    ```markdown
    | `register_provider` | Stable entry point for registering a custom `ModelProvider`. Raises on duplicate name unless `replace=True`. |
    ```

    Also update the `RuntimeConfig` row to mention the new classmethods:

    ```markdown
    | `RuntimeConfig`, `configure`, `get_config`, `reset_config` | Runtime configuration. `RuntimeConfig.from_toml(path)` reads `[runtime]` from a TOML file; `RuntimeConfig.default()` resolves dataclass defaults → `~/.config/voss/config.toml` → `VOSS_*` env overlay. |
    ```

    **Edit 5 — Public surface table for `voss.harness` (around line 170):**

    Add 6 rows in alphabetical position:

    ```markdown
    | `NullRenderer` | Silent no-op renderer; pass to `run_turn` for headless / test embedding. |
    | `Renderer` | Protocol describing the 11 render hooks `run_turn` invokes. |
    | `RunView` | Read-only per-turn projection (id, timestamps, goal, cost, confidence, diff_summary). Stable; the on-disk schema is not. |
    | `SessionView` | Read-only session projection (id, name, cwd, model, timestamps, total cost, runs tuple). Stable; the on-disk schema is not. |
    | `tool_entry_from_callable` | Factory: wrap a Python callable as a `ToolEntry`. `is_mutating` is required; sync callables are wrapped in an async shim. |
    | `view_session` | Pure projection from private `SessionRecord` → public `SessionView`. |
    ```

    **Do NOT touch `pyproject.toml [project] version`** (R-11 — version
    bump is deferred to the publish wave).
  </action>
  <verify>
    <automated>grep -c "register_provider" docs/sdk.md && grep -c "NullRenderer\|tool_entry_from_callable\|SessionView" docs/sdk.md && ! grep -q "private path; example only" docs/sdk.md && ! grep -q "currently a private call" docs/sdk.md && echo OK</automated>
    <expected>Shell output ending in `OK` — all four conditions met.</expected>
  </verify>
  <done>
    `docs/sdk.md` "Known gaps" section is reduced to a single
    informational paragraph (no 4-item bullet list). "Plugin authoring"
    section points at `register_provider` as stable. Quick-start
    snippet imports `NullRenderer` from `voss.harness` (no private
    path). Both Public surface tables have rows for every new M7 name.
    `pyproject.toml` unchanged.
  </done>
</task>

<task type="checkpoint:phase-final">
  <name>Task 5: Full-suite acceptance check (M7 phase-final gate)</name>
  <what-built>
    All M7 promotions (Renderer/NullRenderer, tool_entry_from_callable,
    SessionView/RunView/view_session, RuntimeConfig.from_toml/.default,
    register_provider), the extended public-API drift sets, the new
    end-to-end embedding test, the updated stability docstrings, and
    the rewritten `docs/sdk.md` sections.
  </what-built>
  <how-to-verify>
    Run `pytest -x -q --tb=no` against the full suite. All tests must
    pass — this is the M7 acceptance gate.

    If any test fails:
    1. Identify whether the failure is in a M7 plan (M7-01..05) — if
       so, surface back via SUMMARY for the corresponding plan to fix.
    2. Identify whether the failure is a pre-existing flake — if so,
       quarantine and document in SUMMARY.
    3. Identify whether the failure is caused by an unaudited
       `register` call site (Wave 5 audit gap) — if so, update the
       call site here as a corrective measure and document.

    Do NOT skip or `xfail` any test to make this pass.

    Record the test count and pass/fail summary in the plan SUMMARY.

    Acceptance: `pytest -x` (full suite) is green. Test count >= the
    pre-M7 baseline. No tests were skipped or xfail'd to pass.
  </how-to-verify>
  <resume-signal>Type "approved" once the full suite is green.</resume-signal>
</task>

</tasks>

<verification>
- `pytest tests/packaging/test_public_api.py -x` passes.
- `pytest tests/packaging/test_sdk_embedding.py -x` passes.
- `pytest -x` (full suite) passes.
- `python -c "import voss.harness; assert len([n for n in voss.harness.__all__]) == 14; print(sorted(voss.harness.__all__))"` prints all 14 names.
- `python -c "import voss_runtime; assert len([n for n in voss_runtime.__all__]) == 27; print(sorted(voss_runtime.__all__))"` prints all 27 names.
- `grep -c "Known gaps (closing in M7)" docs/sdk.md` returns `0` (section renamed).
- `grep -c "private path; example only" docs/sdk.md` returns `0` (Quick-start snippet updated).
- `grep -c "register_provider" docs/sdk.md` returns at least `2` (table row + plugin-authoring paragraph).
- `pyproject.toml [project] version` is unchanged at `0.1.0` (R-11).
- `voss_runtime/__init__.py:48` still reads `__version__ = "0.1.0"` (R-11).
</verification>

<success_criteria>
**The M7 success contract (CONTEXT.md D-24):**
- `tests/packaging/test_sdk_embedding.py` passes, importing ONLY from `voss.harness.__all__` and `voss_runtime.__all__` (with the one documented R-06 caveat for `SessionRecord` input construction — sanctioned via explicit omission from `FORBIDDEN_PRIVATE_PATHS`).
- An end-to-end embedding flow — tool wrap, `run_turn`, session projection, TOML config, provider registration — succeeds on the new public surface.
- The static allowlist gate (`test_no_private_path_imports_in_this_file`) and the live-imports pin (`test_public_api_imports_are_live`) jointly defeat both linter import-stripping and silent private-path drift.

**ROADMAP M7 success criteria (5/5):**
1. Each new public name appears in the relevant `__all__` AND in `EXPECTED_*_PUBLIC_API` set — verified by `pytest tests/packaging/test_public_api.py`.
2. `docs/sdk.md` "Known gaps" list shrinks to zero — verified by grep. "Plugin authoring" updated.
3. New test file exercises the embedding surface end-to-end — `tests/packaging/test_sdk_embedding.py`.
4. On-disk `SessionRecord` / `RunRecord` schemas remain private — they are not in `voss.harness.__all__`.
5. Stability docstrings updated on both `__init__.py` files.

**Cross-cutting constraints (CONTEXT.md):**
- No new behavior beyond M7 promotions — verified by reviewing every commit in the wave.
- No new private surface introduced as a side effect.
- Backward compatibility maintained for all 8 prior harness symbols + 26 prior runtime symbols.
- `pyproject.toml` version unchanged at `0.1.0`.
- M7 lands as an additive change set — adopters can pin `voss==0.1.0` (or `0.1.x` if M6 ships first) without surprise.
</success_criteria>

<output>
After completion, create `.planning/phases/M7-sdk-polish/M7-06-SUMMARY.md`
documenting:
- Final `EXPECTED_*_PUBLIC_API` set sizes (14 harness, 27 runtime).
- Test count and full-suite pass result.
- `docs/sdk.md` edit summary (sections changed, lines moved).
- Confirmation that `pyproject.toml [project] version` was not touched
  (R-11).
- The single R-06 caveat exception in `test_sdk_embedding.py` (the
  `SessionRecord` construction private-import allowance — sanctioned
  via explicit omission from `FORBIDDEN_PRIVATE_PATHS`).
- Phase-level retrospective: did any prior wave's contract leak
  through? Did any plan need rework after integration?
</output>
