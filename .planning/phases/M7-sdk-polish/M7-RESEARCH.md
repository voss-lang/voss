# Phase M7: SDK Polish - Research

**Researched:** 2026-05-13
**Domain:** Public-API promotion across `voss.harness` and `voss_runtime`
**Confidence:** HIGH (all findings verified against in-tree source)

## Summary

M7 promotes five existing internals to the public surface. The research confirms every promotion is mechanically simple, but exposes three surprises the planner must address before drafting plans:

1. **The Renderer Protocol has 11 methods, not 9** as CONTEXT.md D-01 claims. `NullRenderer` must implement `banner` and `status` in addition to the 9 listed.
2. **`tool_entry_from_callable` cannot be a pure delegate to `voss_runtime.tool`** because the executor calls `await entry.invoke(...)` (`voss/harness/agent.py:430`), and the existing `tool` decorator preserves the original function's awaitability. The factory MUST either reject sync callables OR wrap them in an async shim. CONTEXT.md D-06 hand-waves this — research confirms the executor will break on a sync callable.
3. **A `[harness]` TOML section already exists** at `voss/harness/config.py` with its own parser (regex-based, NOT tomllib). D-14's choice of `[runtime]` for SDK-04 is the right call — it sidesteps collision — but the planner must ensure the new `tomllib`-based reader does not interfere with the existing `[harness]` regex writer's preservation logic.

**Primary recommendation:** Plan SDK-01..05 as five independent waves with a final "integration + tests + docs" wave (Wave 6). Audit-and-update of `register(__stub__, ...)` callers MUST land in the same wave as SDK-05's collision-default flip, or all stub-using tests break in CI.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Renderer Protocol + NullRenderer | `voss.harness` | — | Rendering is a harness concern; runtime does not import rendering |
| `tool_entry_from_callable` factory | `voss.harness.tools` | `voss_runtime.tools` (delegates inference) | Wraps the runtime's `@tool` decorator + adds harness's `is_mutating` data |
| SessionView / RunView projection | `voss.harness.views` (new) | `voss.harness.session` (source schema) | Pure projection; reads SessionRecord, writes nothing |
| `RuntimeConfig.from_toml` / `default` | `voss_runtime._config` | stdlib `tomllib` | Config lives in runtime; harness re-uses via `get_config()` |
| `register_provider` re-export | `voss_runtime` `__init__` | `voss_runtime.providers` | Promotion only; underlying function stays in `providers/__init__.py` |

## Findings per Research Question

### Q1 — inspect.signature + type-hint inference (SDK-02)

**Finding:** `voss_runtime/tools.py` ALREADY implements full type-hint inference in the `@tool` decorator at lines 65–102. The factory should delegate to this code, not reimplement it.

Existing inference behavior (`voss_runtime/tools.py:19-38` `_type_to_schema`):
- `str`/`int`/`float`/`bool` → primitive JSON types [VERIFIED: read source]
- `list[T]` → `{"type": "array", "items": ...}` (recursive)
- `dict` → `{"type": "object"}` (no value-type)
- `BaseModel` subclasses → `model_json_schema()`
- `Optional[T]` / `T | None` → schema for T with `nullable: True` added
- Falls back to `{"type": "string"}` for anything exotic (does NOT raise as D-05 prescribes)

**Drift vs CONTEXT.md D-05:**
- D-05 says `Optional[T]` should map to "schema for T with the param removed from `required`." Existing code keeps it in `required` and adds `nullable: True`. **The factory should match existing behavior** to keep schemas consistent with `make_toolset`'s 10 tools. Diverging will produce two schema dialects in the same runtime.
- D-05 says exotic types should raise. Existing code returns `{"type": "string"}` silently. The planner should pick one — recommend matching existing behavior (silent string fallback) since the existing 10 tools depend on it.

**Async support:** `voss/harness/agent.py:430` does `res = await entry.invoke(**step.args)`. `entry.invoke` → `descriptor.invoke` → `self.func(**kwargs)`. For an **async** function this returns a coroutine that `await` resolves. For a **sync** function this returns a plain value and `await <plain>` raises `TypeError: object str can't be used in 'await' expression`.

Conclusion: the executor does NOT transparently handle sync callables. CONTEXT.md D-06's "the existing call path already supports awaitable returns" is partially right (it supports awaitables) but does NOT support sync callables. Three options for the factory:
- **(a)** Require `inspect.iscoroutinefunction(fn)` and raise otherwise — narrowest contract, matches existing tool shape.
- **(b)** Wrap sync `fn` in an `async def shim(**kw): return fn(**kw)` — most embedder-friendly, ~3 lines.
- **(c)** Change the executor to `if inspect.iscoroutine(res): res = await res` — wider blast radius; touches Wave 6 territory.

Recommend (b): the factory wraps sync callables transparently. M7 stays "promotion only" while making the public API actually usable from plain Python.

**Hand-written parameter-schema examples in `make_toolset` (`voss/harness/tools.py:51-186`):** every existing tool uses the `@tool` decorator and lets `voss_runtime/tools.py` infer the schema. There are NO hand-written parameter dicts in `make_toolset`. The factory's inferred output will be identical-shaped to existing tools — by construction, since both go through `_type_to_schema`. [VERIFIED: grep]

### Q2 — ToolDescriptor location and shape

**Finding:** `ToolDescriptor` is defined in `voss_runtime/tools.py:41-62` as a frozen dataclass with fields `name: str`, `description: str`, `parameters: dict[str, Any]`, `func: Callable`. It has `schema()` and `invoke()` methods. [VERIFIED: read source]

The `parameters` field accepts an OpenAI-tool-format dict: `{"type": "object", "properties": {...}, "required": [...]}` — exactly what D-05 prescribes (modulo the Optional handling above).

Constructor signature: `ToolDescriptor(name=..., description=..., parameters=..., func=...)` — all four keyword-args required.

The simplest factory body (after async-wrap decision) is:

```python
from voss_runtime import tool as _tool_decorator
from voss_runtime import ToolDescriptor

def tool_entry_from_callable(
    fn, *, is_mutating: bool, name=None, description=None, parameters=None
) -> ToolEntry:
    if not inspect.iscoroutinefunction(fn):
        async def _async_fn(**kwargs):
            return fn(**kwargs)
        _async_fn.__name__ = fn.__name__
        _async_fn.__doc__ = fn.__doc__
        _async_fn.__annotations__ = getattr(fn, "__annotations__", {})
        fn = _async_fn
    descriptor = _tool_decorator(name=name, description=description)(fn)
    if parameters is not None:
        descriptor = dataclasses.replace(descriptor, parameters=parameters)
    return ToolEntry(descriptor=descriptor, is_mutating=is_mutating)
```

Note: `ToolDescriptor` is frozen — so `replace` is required to override `parameters`. Alternatively, build the descriptor by hand.

### Q3 — In-tree callers of `voss_runtime.providers.register` (SDK-05 audit)

**All call sites that must be audited (with file:line):**

| # | File:line | Caller intent | Action for M7 |
|---|-----------|--------------|---------------|
| 1 | `voss_runtime/providers/__init__.py:32` | Module-load `register("__default__", LiteLLMProvider())` | No change — registry empty on first call |
| 2 | `voss_runtime/providers/__init__.py:33` | Module-load `register("__stub__", StubProvider())` | No change — registry empty on first call |
| 3 | `tests/test_agent.py:26,85,99,118` | `register("agent-text-model", ...)` etc. (4 distinct fresh names) | Pass `replace=True` — pytest may re-import in same process |
| 4 | `tests/eval/test_runner_options.py:11` | Imports `register` for re-registering | Audit usage; pass `replace=True` |
| 5 | `tests/integration/test_classify_example.py:16,25` | `voss_runtime.providers.register("__stub__", stub)` × 2 | Pass `replace=True` — overwrites module-load stub |
| 6 | `tests/integration/test_research_example.py:20` | Same pattern | Pass `replace=True` |
| 7 | `tests/integration/test_support_example.py:50` | Same pattern | Pass `replace=True` |
| 8 | `tests/codegen/test_examples.py:107` | Same pattern | Pass `replace=True` |
| 9 | `tests/examples/helpers.py:98` | `register_stub` ctxmgr (used by many tests) | Pass `replace=True` — single point of fix that covers downstream |
| 10 | `tests/examples/helpers.py:113` | Emits sitecustomize source string `voss_runtime.providers.register("__stub__", _stub)` | Update generated source to pass `replace=True` |

**Why module-load lines 32/33 are safe:** They run exactly once during import, when the `_registry` dict is empty. The first `register("__default__", ...)` sees an empty dict → no collision. The second `register("__stub__", ...)` sees one entry under a different name → no collision. Both will succeed under the new raise-by-default behavior.

**Test re-run risk:** Within a single pytest process, after `__stub__` has been registered once by module-load, any test that calls `register("__stub__", ...)` (entries 5–9) will hit a collision. ALL of these need updating in the SAME wave as SDK-05's behavior change, or the test suite is red. This is the "audit and update in the same wave" requirement from CONTEXT.md D-21 — confirmed concrete and necessary.

**`register_stub` ctxmgr** in `tests/examples/helpers.py:95` is the canonical single fix-point: many integration tests use it. Updating that one helper to pass `replace=True` covers most of the downstream test cases. Files 5/6/7/8 may use it directly OR may inline the call — must check each.

### Q4 — ModelProvider Protocol runtime_checkable status

**Finding:** `voss_runtime/providers/base.py:22` already decorates `ModelProvider` with `@runtime_checkable`. [VERIFIED: read source]

`isinstance(some_obj, ModelProvider)` will work today. SDK-05 D-22's "add decorator if missing" is a no-op — confirm in implementation plan and skip the change. The Protocol's `count_tokens` method has no `*` keyword-only marker (line 36); both methods are checked structurally.

### Q5 — Existing tomllib / config.toml integration (SDK-04)

**Finding:** Two existing TOML readers in tree:

1. **`voss/harness/config.py`** — reads/writes `~/.config/voss/config.toml` `[harness]` section. Uses REGEX (`_HARNESS_BLOCK`, `_KV` at lines 18-19), NOT `tomllib`. Today's only key is `preferred_model`. `set_preferred_model` preserves other sections via regex sub (line 50).
2. **`voss/harness/plugins.py:4,47,95`** — reads plugin manifests via `tomllib`.

**Naming collision risk:**
- CONTEXT.md D-14 picks `[runtime]` for the new section. ✓ Avoids collision with `[harness]`.
- The same file (`~/.config/voss/config.toml`) will now have BOTH sections. The regex-based `set_preferred_model` writer at `voss/harness/config.py:50` uses a regex that captures one section (`re.compile(r"^\[harness\][^\[]*", re.MULTILINE)`) — it preserves everything outside the `[harness]` block. Safe with `[runtime]` siblings.
- The new `RuntimeConfig.from_toml` will use `tomllib.loads(path.read_text())` and `data.get("runtime", {})`. Reading the existing `[harness]` section is a no-op for runtime config. Safe.

**Integration risk:** if a future writer ever writes the `[runtime]` section via similar regex preservation, it must not eat the `[harness]` block. Recommend: M7 reads `[runtime]` but does NOT write it. `RuntimeConfig.from_toml` is read-only; `configure(**kwargs)` continues to be the in-process mutation API. CONTEXT.md D-15 already specifies this — confirmed correct.

**Env-var coercion** (D-16, D-17): `tomllib` returns native Python types (numbers as int/float). Env-vars are always strings. `int(os.environ["VOSS_MAX_RETRIES"])` is the standard coercion; D-17's "raises clear error" is implicit in `int()`/`float()`'s ValueError. Recommend the implementation wrap the cast with a friendlier message: `raise ValueError(f"VOSS_MAX_RETRIES={raw!r} is not a valid int")`.

### Q6 — Session JSON shape on disk vs SessionRecord (SDK-03)

**Finding:** `SessionRecord.runs` is typed as `list[dict]`, NOT `list[RunRecord]`. [VERIFIED: `voss/harness/session.py:94`]

Confirmed by `voss/harness/cli.py:830`:
```python
record.runs.append(asdict(result.run))
```

RunRecord is `asdict`'d into the runs list at save time. On load, `_hydrate` (`session.py:119`) does NOT rehydrate runs back into RunRecord objects — they stay as dicts.

**Consequence for `view_session`:**
- Cannot do `for r in record.runs: RunView(id=r.id, ...)` — `r` is a dict.
- Must do `for r in record.runs: RunView(id=r.get("id", ""), started_at=r.get("started_at", ""), ...)`.
- Defensive `.get()` reads are REQUIRED, not optional, because legacy sessions on disk may pre-date some RunRecord fields. The existing `_hydrate` already handles this for SessionRecord top-level fields; the projection must do the same for run dicts.

**Field mapping for `RunView` projection from a run dict:**

| RunView field | Source dict key | Default |
|---------------|-----------------|---------|
| `id` | `"id"` | `""` |
| `started_at` | `"started_at"` | `""` |
| `ended_at` | `"ended_at"` | `""` |
| `goal` | `"goal"` | `""` |
| `cost_usd` | `"cost_usd"` | `0.0` |
| `confidence` | `plan.confidence` (nested) | `None` |
| `diff_summary` | `"diff_summary"` | `""` |

`confidence` is nested: `run_dict.get("plan", {}).get("confidence")`. If `plan` is None or absent, `confidence` is None — matches D-11's `float | None` type.

### Q7 — Existing test patterns for new test_sdk_embedding.py

**Finding:** `tests/packaging/test_entrypoint.py` (`tests/packaging/test_entrypoint.py:1-106`) is the closest existing pattern. It uses:
- Plain `def` test functions (no `pytest-asyncio` decorator on packaging tests — but pytest-asyncio is available via `pyproject.toml`)
- `subprocess.run([sys.executable, "-m", "voss.cli", ...])` for CLI surface tests
- `tomllib.loads(Path("pyproject.toml").read_text())` for static checks
- `@pytest.mark.slow` decorator for the editable-install test

For SDK embedding (`test_sdk_embedding.py`), the simpler pattern is:
- `@pytest.mark.asyncio` (pytest-asyncio configured in pyproject) wrapping an `async def test_*` that calls `await run_turn(...)` directly
- Use `StubProvider(default_response=...)` from `voss_runtime` for hermetic provider
- Use `NullRenderer()` (the new SDK-01 symbol) for silent rendering
- Use `tool_entry_from_callable` (the new SDK-02 symbol) to build a tool from a plain `async def` (or sync, if the factory wraps)
- Use a `tmp_path` fixture for cwd and pass `tmp_path` to `run_turn(cwd=...)`
- After the turn, manually hydrate a `SessionRecord` (or call `view_session` on a constructed record) — since `run_turn` does NOT auto-persist sessions (that's done by `cli.py`)
- For RuntimeConfig.from_toml: write a temp `[runtime]` TOML file under `tmp_path`, pass its path to `RuntimeConfig.from_toml(p)`, assert returned values
- For register_provider: register a fresh-named stub, call `from voss_runtime.providers import get`, assert resolution

**Conftest:** `tests/conftest.py` likely exists. The new file does NOT need a dedicated conftest; existing pytest-asyncio config in pyproject.toml is sufficient.

**The "ast-check or import-* smoke" gate from D-24:** simplest implementation is a unit assertion at top of test file:

```python
from voss.harness import (
    NullRenderer, Renderer, RunView, SessionView, ToolEntry,
    TurnResult, tool_entry_from_callable, view_session,
    Plan, PermissionGate, ToolCall, RunSemantics, main, run_turn,
)
from voss_runtime import (
    RuntimeConfig, StubProvider, register_provider,
)
# If any of these import lines fail, the test file fails to import → fail-loud.
```

The drift is caught by import failure, no AST parsing needed.

### Q8 — Cross-package import shape

**Finding:** No circular imports detected. [VERIFIED: `grep "^from voss\b\|^import voss\b" voss_runtime/`]

`voss_runtime` is independent. `voss_runtime/__init__.py:40` imports from `voss_runtime.providers`, which imports from `voss_runtime.providers.base`. Clean.

Adding `register_provider` to `voss_runtime/__init__.py` is a single-line addition:

```python
from voss_runtime.providers import register as register_provider
```

Placed alphabetically in the existing imports block. No risk.

### Q9 — Existing parameter-schema patterns in make_toolset

**Finding:** All 10 tools in `voss/harness/tools.py:51-186` use the `@tool` decorator from `voss_runtime`. Examples:

- `fs_read(path: str)` → `{"properties": {"path": {"type": "string"}}, "required": ["path"]}`
- `fs_edit(path: str, old: str, new: str)` → all three required, all strings
- `git_diff(staged: bool = False, path: str = "")` → both optional (have defaults), staged is bool, path is str
- `record_run(goal: str = "", avoided: list | None = None, ...)` → `avoided` is `Optional[list]` → currently inferred as `{"type": "array", "items": {"type": "string"}, "nullable": True}` with `"default": None`

The factory's inferred output for `record_run` would match exactly, since it delegates to the same `@tool` decorator path.

**Mismatch from D-05:** D-05 says `Optional[T]` removes from `required`. Existing code keeps it in `required` (because the param has a default → already not in `required` via the `param.default is inspect._empty` check at `voss_runtime/tools.py:84`). Default-presence is what controls `required`, not Optional-ness. The "Optional → not required" rule of D-05 is incidentally correct in practice for all existing tools (every Optional has a default), but the planner should write the rule as "params with defaults are not required" to match the implementation.

### Q10 — Pre-1.0 versioning carve-out

**Finding:** `pyproject.toml:6` declares `version = "0.1.0"`. `voss_runtime/__init__.py:48` declares `__version__ = "0.1.0"`. [VERIFIED: read source]

`docs/sdk.md:39-50` documents the carve-out: pre-1.0 minor bumps may break `__all__`. M7 is allowed to land as either a 0.1.x patch (since it's strictly additive — none of the 5 promotions remove names) or a 0.2.0 minor (since the rule allows breakage either way, additive bumps are conventionally minor pre-1.0). No published-version pin in tests or CI blocks a pre-publish modification — the only version check is in `tests/packaging/test_entrypoint.py:22-24` which checks `[project.scripts]` entry, not the version string.

**Recommendation:** M7 ships as 0.1.0 (pre first publish, as CONTEXT.md cross-cutting constraint allows) OR 0.2.0 (if M6 ships first per ROADMAP M7 ordering note). Plan against both — the version bump is a single-line change in `pyproject.toml` + `voss_runtime/__init__.py`, deferrable to the release wave.

## Integration Risks the Planner Must Address

### Risk 1: Renderer method count mismatch
CONTEXT.md D-01 claims 9 methods; actual count is 11 (adds `banner` and `status`). `NullRenderer` must implement all 11 as pass-through no-ops. The packaging test's "all `__all__` symbols importable" check won't catch a missing Protocol method since `Renderer` is structural. The end-to-end test in D-24 will catch it if it exercises `banner`/`status` — but `run_turn` itself does NOT call either (those are CLI-only). Recommend: explicit unit test that asserts `isinstance(NullRenderer(), Renderer)` to lock structural conformance at test time, since `@runtime_checkable` Protocols support isinstance.

### Risk 2: Sync-callable async-shim decision (SDK-02)
The executor at `voss/harness/agent.py:430` does `await entry.invoke(...)`. A sync callable wrapped by the factory without an async shim WILL crash on first invocation. Plan must make the async-wrap decision explicit. Recommend option (b): factory wraps sync `fn` in an `async def` shim.

### Risk 3: register collision audit must land in the SAME wave as the behavior flip
10 call sites identified across 6 test files plus `tests/examples/helpers.py:98,113`. Order matters: if SDK-05's `replace: bool = False` default ships before the audit, every `__stub__` re-registration in pytest goes red. Plan must combine these into one atomic wave (or land the audit first and the default flip second — but combining is cleaner).

### Risk 4: SessionRecord.runs is list[dict], not list[RunRecord]
D-12 says `view_session(record: SessionRecord) -> SessionView`. The projection cannot use attribute access on run entries. Plan must specify defensive `.get()` reads OR rehydrate each dict to a typed run inside the projection. Recommend `.get()` reads — simpler, no schema coupling.

### Risk 5: Optional[T] schema dialect — existing vs D-05
Existing `_type_to_schema` (`voss_runtime/tools.py:32-37`) adds `nullable: True` and keeps the param in `required` unless it has a default. D-05 says "remove from required." Recommend the factory match existing behavior (defaults control `required`, Optional adds `nullable: True`), not D-05's literal text. Otherwise two dialects coexist in the same runtime, which the end-to-end test may not catch but a provider that strict-validates schemas will.

### Risk 6: `register_provider` shadows `register` in voss_runtime namespace?
No shadowing. `voss_runtime/__init__.py` does not currently export `register` (only the providers submodule does). Adding `register_provider` is the only public name in `voss_runtime` for this function. The original `voss_runtime.providers.register` stays available — embedders using the long name go through `__all__`, in-tree code keeps the short name.

### Risk 7: docs/sdk.md "Known gaps" has FOUR items, not five
`docs/sdk.md:194-215` lists exactly 4 known gaps (Renderer, ToolEntry helpers, Session record types, TOML config). SDK-05 (provider register stabilization) is NOT in the "Known gaps closing in M7" section — it's mentioned in "Plugin authoring (informal in v0.1)" at line 224 instead. CONTEXT.md and ROADMAP frame M7 as closing "four known holes + SDK-05." Plan's docs/sdk.md update must update BOTH the known-gaps section AND the plugin-authoring section, not just one. SUCCESS-2 criterion ("Known gaps list shrinks by exactly the five items") is mis-stated against the actual document — the gaps section closes 4 items, plus the plugin-authoring para gets a "register_provider is stable" insertion.

## Reusable Patterns from Existing Code

### Pattern 1: Test-public-api drift entries
`tests/packaging/test_public_api.py:14-43` — extend `EXPECTED_RUNTIME_PUBLIC_API` and `EXPECTED_HARNESS_PUBLIC_API` frozensets. The test failure message itself instructs the human to update sdk.md. Use this for SDK-23. Final harness `__all__` size after M7 should be **14** (8 + Renderer, NullRenderer, tool_entry_from_callable, SessionView, RunView, view_session). Runtime `__all__` size: **27** (26 + register_provider). [matches CONTEXT.md D-23]

### Pattern 2: tool_decorator delegation
`voss_runtime/tools.py:65-102` is a fully-realized type-hint-to-JSON-schema function. The new factory uses it via `voss_runtime.tool(fn)` and captures the returned `ToolDescriptor`. ~10 lines of factory code, not 80.

### Pattern 3: Frozen dataclass projection
`voss/harness/tools.py:14-41` (`ToolEntry`) is the precedent. `SessionView` and `RunView` mirror this: `@dataclass(frozen=True)`, no methods (or one classmethod `from_record(...)` if helpful).

### Pattern 4: dataclasses.replace for fluent config
`voss_runtime/_config.py:29` uses `replace(_config, **kwargs)` — the same idiom can implement `RuntimeConfig.from_toml`: start from `cls()` defaults, `replace(defaults, **toml_data)`, `replace(intermediate, **env_overrides)`. Three-line implementation.

### Pattern 5: load_harness_config → load_runtime_config
`voss/harness/config.py:30-39` is a working template for `RuntimeConfig.from_toml`. The new method goes on the dataclass (classmethod), uses `tomllib.loads` instead of regex, and reads the `[runtime]` section. Different section, different parser, same overall pattern.

### Pattern 6: StubProvider hermetic test driver
`tests/integration/test_classify_example.py:8-25` shows the canonical hermetic test pattern: `StubProvider(default_response="...")`, `register("__stub__", stub)`, `configure(default_model="__stub__")`. The new `test_sdk_embedding.py` mirrors this but with `register_provider("test-provider", stub, replace=True)` to exercise the new public name AND the new `replace` kwarg.

## Wave / Parallelization Recommendations

The 5 promotions are **structurally independent**. No SDK-N depends on SDK-M code-wise. Plan as 6 waves:

| Wave | Scope | Files touched | Blocking? |
|------|-------|---------------|-----------|
| 1 (SDK-01) | NullRenderer class + `__all__` add | `voss/harness/render.py`, `voss/harness/__init__.py` | No — pure addition |
| 2 (SDK-02) | `tool_entry_from_callable` + `__all__` add | `voss/harness/tools.py`, `voss/harness/__init__.py` | No — pure addition |
| 3 (SDK-03) | `voss/harness/views.py` new + `__all__` add | `voss/harness/views.py`, `voss/harness/__init__.py` | No — pure addition |
| 4 (SDK-04) | `RuntimeConfig.from_toml` + `.default()` + tests | `voss_runtime/_config.py` | No — additive classmethods |
| 5 (SDK-05) | `replace` kwarg + audit ALL 10 callers + re-export | `voss_runtime/providers/__init__.py`, `voss_runtime/__init__.py`, **all test files in Q3 table** | **YES — must be atomic to keep CI green** |
| 6 (integration) | docs/sdk.md, test_public_api drift entries, test_sdk_embedding.py end-to-end, stability docstrings | `docs/sdk.md`, `tests/packaging/test_public_api.py`, `tests/packaging/test_sdk_embedding.py`, `voss/harness/__init__.py`, `voss_runtime/__init__.py` | YES — depends on waves 1–5 |

**Parallelization within waves 1–4:** safe to run in parallel since they touch disjoint files (`render.py`, `tools.py`, `views.py`, `_config.py`). Each only edits its own module plus the package `__init__.py`. The `__init__.py` edits are tiny (one import + one `__all__` entry each) — easy to coordinate.

**Wave 5 must NOT parallelize with the test changes:** the audit (10 files) and the default flip (1 file) must land as one commit or the test suite breaks. Treat as one task even though it touches many files.

**Wave 6 must run last** — it depends on every name from waves 1–5 existing in `__all__`.

## Open Questions

1. **Sync vs async-only callables in SDK-02.** The factory either rejects sync callables or wraps them. Recommend wrapping (option b) — `is_mutating` already required, `name`/`description`/`parameters` already inferred-or-passed; rejecting sync just for shape-purity makes the factory less useful. Confirm with planner before locking.

2. **Optional[T] schema dialect.** D-05 prescribes "removed from required"; existing tool decorator adds `nullable: True` and uses default-presence as the `required` gate. Recommend matching existing behavior. Confirm with planner.

3. **D-12 input type for `view_session`.** D-12 takes `SessionRecord`. Should it also accept a dict (raw JSON-loaded session) for embedders that read the file themselves? CONTEXT.md Claude's Discretion item allows this; recommend dict overload is a v0.2 follow-up unless trivial. The projection itself already does `.get()` reads on inner run dicts, so accepting an outer dict is one extra `isinstance` check.

4. **Number of "Known gaps" closed in docs/sdk.md.** Document lists 4, ROADMAP success criterion 2 says "shrinks by exactly the five items shipped." Recommend the plan-checker treat this as: shrinks `known gaps` section from 4→0 AND updates the `Plugin authoring` paragraph to mark `register_provider` as stable. Both edits in the same PR. Surface this to discuss if interpretation matters.

5. **Stability docstring text.** D-26 says docstrings on `__init__.py` files mention each new public name with a one-line summary. The existing harness docstring (`voss/harness/__init__.py:1-28`) currently lists `run_turn, Plan, ToolCall, TurnResult` only. Recommend a "## Public surface" subsection that mirrors `docs/sdk.md`'s Public surface table format — keeps the two in sync.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.11+ (pyproject requires-python) | — |
| `tomllib` | SDK-04 | ✓ | stdlib (3.11+) | — |
| `inspect`, `typing.get_type_hints` | SDK-02 | ✓ | stdlib | — |
| `pytest`, `pytest-asyncio` | All tests | ✓ | pytest>=8.0, pytest-asyncio>=0.23 (pyproject) | — |
| `pydantic` | Existing tools.py | ✓ | already in deps | — |

No missing dependencies. No new deps added by M7.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.23+ |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/packaging/ -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SDK-01 | `Renderer` / `NullRenderer` in `__all__` | unit | `pytest tests/packaging/test_public_api.py -x` | ✅ extend |
| SDK-01 | `NullRenderer` satisfies Renderer Protocol | unit | `pytest tests/harness/test_renderers.py -x` | ❌ Wave 6 (new) |
| SDK-02 | `tool_entry_from_callable` infers schema | unit | `pytest tests/harness/test_tools.py::test_tool_entry_from_callable -x` | ❌ Wave 2 (extend or new) |
| SDK-02 | Factory wraps sync callables to be awaitable | unit | `pytest tests/harness/test_tools.py::test_factory_async_shim -x` | ❌ Wave 2 |
| SDK-03 | `view_session` excludes sensitive fields | unit | `pytest tests/harness/test_views.py -x` | ❌ Wave 3 (new) |
| SDK-04 | `from_toml` loads `[runtime]` section | unit | `pytest tests/test_config.py::test_from_toml -x` | ✅ extend |
| SDK-04 | `default()` applies env overlay | unit | `pytest tests/test_config.py::test_default_env_overlay -x` | ✅ extend |
| SDK-04 | `from_toml` raises on missing file | unit | `pytest tests/test_config.py::test_from_toml_missing -x` | ✅ extend |
| SDK-05 | `register_provider` raises on duplicate by default | unit | `pytest tests/providers/test_base.py::test_register_collision -x` | ✅ extend |
| SDK-05 | `replace=True` overwrites silently | unit | `pytest tests/providers/test_base.py::test_register_replace -x` | ✅ extend |
| All | Drift entries in `EXPECTED_*_PUBLIC_API` | unit | `pytest tests/packaging/test_public_api.py -x` | ✅ extend |
| All | End-to-end embedding via public symbols only | integration | `pytest tests/packaging/test_sdk_embedding.py -x` | ❌ Wave 6 (new) |

### Sampling Rate
- **Per task commit:** `pytest tests/packaging/ tests/harness/ tests/providers/ -x` (~ targeted layers)
- **Per wave merge:** `pytest -x` (full)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/harness/test_renderers.py` — covers SDK-01 Protocol conformance + NullRenderer no-op assertions
- [ ] `tests/harness/test_tools.py` extension OR new `tests/harness/test_tool_factory.py` — covers SDK-02 inference + async shim
- [ ] `tests/harness/test_views.py` — covers SDK-03 projection (fields included/excluded, defensive .get reads)
- [ ] `tests/packaging/test_sdk_embedding.py` — Wave 6 integration test

No new framework install needed.

## Sources

### Primary (HIGH confidence)
- `voss/harness/render.py` lines 12, 24-44 (Renderer Protocol — 11 methods confirmed)
- `voss/harness/tools.py` lines 14-41 (ToolEntry), 51-186 (make_toolset's 10 tools)
- `voss/harness/session.py` lines 65-94 (RunRecord + SessionRecord shapes), line 119 (_hydrate)
- `voss/harness/cli.py` line 830 (`record.runs.append(asdict(result.run))` — confirms run dict shape)
- `voss/harness/agent.py` lines 236-265 (run_turn signature), line 430 (await entry.invoke pattern)
- `voss/harness/__init__.py` lines 30-44 (current 8-symbol public surface)
- `voss/harness/config.py` lines 13-58 (existing [harness] TOML reader, regex-based)
- `voss_runtime/__init__.py` lines 18-77 (current 26-symbol public surface)
- `voss_runtime/_config.py` lines 6-37 (RuntimeConfig dataclass + configure)
- `voss_runtime/tools.py` lines 11-102 (existing _type_to_schema + @tool decorator inference)
- `voss_runtime/providers/__init__.py` lines 1-43 (register function, module-load calls)
- `voss_runtime/providers/base.py` line 22 (ModelProvider Protocol already @runtime_checkable)
- `tests/packaging/test_public_api.py` lines 14-108 (drift-detection pattern)
- `tests/packaging/test_entrypoint.py` lines 1-106 (closest existing pattern for new test file)
- `tests/examples/helpers.py` lines 95-120 (register_stub ctxmgr — key audit target)
- `pyproject.toml` (version 0.1.0, requires-python >=3.11)

### Secondary (MEDIUM confidence)
- `docs/sdk.md` (Known gaps section lists 4 items, not 5 — see Risk 7)

### Tertiary (LOW confidence)
None — all findings verified against source.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommend factory wraps sync callables (not rejects) | Q1 / Risk 2 | If planner rejects sync, factory contract narrows; embedder docs must say "async only" — minor docs delta |
| A2 | Recommend matching existing Optional[T] dialect (nullable:True, default controls required) | Q1 / Q9 / Risk 5 | If planner picks D-05 literal text, two dialects coexist; strict-schema providers may reject |
| A3 | docs/sdk.md "Known gaps" interpretation: shrinks from 4→0 plus plugin-authoring update | Q7 / Risk 7 | If success criterion is literal "5 items", plan-checker must verify a 5-item shrink — but only 4 items exist in that list today |
| A4 | Wave 5 register audit + behavior flip MUST be atomic | Q3 / Risk 3 | If split, test suite goes red on the intermediate commit |
| A5 | Version stays 0.1.0 in M7; release wave bumps if needed | Q10 | If planner wants 0.2.0 bump now, single-line change |

## Project Constraints (from CLAUDE.md)

No project-specific `./CLAUDE.md` constraints affect M7. The repo-root CLAUDE.md is a QuadFlow scaffold not relevant to this phase's Python promotion work.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries (stdlib `tomllib`, `inspect`, pydantic, pytest) already in tree
- Architecture: HIGH — exact file:line citations for every claim; no inference from training data
- Pitfalls: HIGH — async-shim, register audit, runs-as-dicts, Optional dialect all surfaced from reading source

**Research date:** 2026-05-13
**Valid until:** 2026-06-12 (30 days — stable codebase, low churn risk)
