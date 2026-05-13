# Phase M7: SDK Polish - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Source:** Synthesized from ROADMAP.md §"Phase M7: SDK Polish" + REQUIREMENTS.md SDK-01..05 + `docs/sdk.md` + 2026-05-12 SDK contract scout. User declined discuss-phase interactive flow — design surface tight enough that CONTEXT.md captures the locked decisions directly from upstream artifacts.

<domain>
## Phase Boundary

M7 promotes five existing internals to the public surface (`voss.harness.__all__` / `voss_runtime.__all__`) so embedders stop binding to private paths. Pure rename + re-export + docstrings + regression-pin entries in `tests/packaging/test_public_api.py`. No new behavior — every helper added must already exist as private code or be a thin convenience wrapper around existing internals.

**In scope:**
- **SDK-01:** Promote the `Renderer` Protocol (`voss/harness/render.py` line 24) into `voss.harness.__all__`. Add a `NullRenderer` no-op implementation alongside the existing `TtyRenderer` / `PlainRenderer`. Both names added to `__all__`.
- **SDK-02:** Add `tool_entry_from_callable(fn, *, is_mutating, name=None, description=None) -> ToolEntry` factory in `voss/harness/tools.py`. Infers `name` from `fn.__name__` when omitted, `description` from first line of `fn.__doc__` when omitted, parameter schema from `inspect.signature` + type hints. Supports async callables. `is_mutating` is REQUIRED (no default) per M1 D-06 (data not name-pattern).
- **SDK-03:** Add read-only `SessionView` + nested `RunView` types in `voss/harness/session.py` (or new `voss/harness/views.py` — Claude's discretion). Projects `SessionRecord` / `RunRecord` to an embedder-stable surface that excludes sensitive/internal fields (`decisions`, `risks`, `validation`, `failures`, `inspected`, `changed`, `avoided`, `assumptions`, `follow_ups`). Promote `SessionView`, `RunView`, `view_session(SessionRecord) -> SessionView` to `voss.harness.__all__`.
- **SDK-04:** Add `RuntimeConfig.from_toml(path: str | Path) -> RuntimeConfig` and `RuntimeConfig.default() -> RuntimeConfig` in `voss_runtime/_config.py`. `from_toml` reads `[harness]` (or `[runtime]` — Claude's discretion, document the chosen section name) from the file and returns a NEW instance (does NOT mutate global `_config`). `default()` resolves `~/.config/voss/config.toml` if it exists then applies env-var overlay (`VOSS_DEFAULT_MODEL`, `VOSS_MAX_OUTPUT_TOKENS`, `VOSS_TIMEOUT_SECONDS`, `VOSS_MATCH_THRESHOLD`); falls back to dataclass defaults when no file exists.
- **SDK-05:** Document and stabilize `voss_runtime.providers.register(name, provider)`. Re-export as `voss_runtime.register_provider` (or expose the existing `register` directly — Claude's discretion). Default collision policy: silent overwrite (today's behavior) STAYS, but a new `replace: bool = False` kwarg flips to raise-on-duplicate when set to `False` and the name is already registered. Maintains backward compatibility for in-tree callers that rely on overwrite.
- Stability docstrings on `voss/harness/__init__.py` and `voss_runtime/__init__.py` updated to mention each new public name.
- `docs/sdk.md` "Known gaps (closing in M7)" section: each of the five gaps gets its corresponding Quick start / Public surface row updated, gap deleted.
- `tests/packaging/test_public_api.py` — `EXPECTED_HARNESS_PUBLIC_API` and `EXPECTED_RUNTIME_PUBLIC_API` frozensets extended with the new names. Existing 4 tests must continue to pass.
- New end-to-end embedding test (`tests/packaging/test_sdk_embedding.py` or similar): build a tool from a plain Python callable via `tool_entry_from_callable`, drive `run_turn` with `NullRenderer` and `StubProvider`, project the resulting session via `view_session`, configure runtime via `RuntimeConfig.from_toml`, register a custom provider via the promoted entry point — all imports MUST come from `voss.harness.__all__` or `voss_runtime.__all__`.
- M6 wheel-smoke test (`tests/packaging/test_wheel_install.py` if it landed) is unaffected. M7 changes are additive on top.

**Out of scope (deferred to other phases):**
- TS/JS SDK — separate v0.2 candidate; M7 is Python-only.
- HTTP / remote SDK — Voss stays local-first.
- Formal plug-in framework (entry-points, manifest, sandboxed loading) — v0.2+ when external authors arrive.
- Promoting `SessionRecord` / `RunRecord` themselves to `__all__` — the read-only `SessionView` is the M7 contract. The internal schemas stay free to change.
- New behavior in any of the promoted symbols beyond the listed factory inference, env-overlay, and collision-policy additions. M7 is a promotion phase, not a feature phase.
- Renaming existing private modules to underscore-prefixed paths (e.g., `voss.harness.render` → `voss.harness._render`). Stability is enforced by `__all__` + docstring contract per `docs/sdk.md`, not by rename gymnastics.
- Replacing `configure(**kwargs)` with a TOML-only API. `configure(**kwargs)` stays; `from_toml` and `default()` are additive.
- Pydantic-based validation of `RuntimeConfig` fields (e.g., negative timeouts, out-of-range thresholds). Dataclass + simple `__post_init__` checks if desired (Claude's discretion); pydantic migration is out of scope.
- Surfacing `RunRecorder` / cognition / permissions hooks beyond `PermissionGate` (already public per M7 baseline).
- Stable embedding API for the CLI (`voss.cli:main` stays public per existing harness `__all__`).
- A separate `voss.sdk` namespace — `voss.harness` + `voss_runtime` ARE the SDK.

</domain>

<decisions>
## Implementation Decisions

### SDK-01: Renderer Protocol + NullRenderer
- **D-01:** Promote the existing `Renderer` Protocol from `voss/harness/render.py:24` into `voss.harness.__all__` AS-IS. All 9 methods stay (`show_user`, `show_thinking`, `show_plan`, `show_tool_call`, `show_clarify`, `show_final`, `show_cognition`, `show_cognition_overflow`, `show_warning`). No `MinimalRenderer` subset split — embedders that don't care about cognition methods just no-op them in their custom implementation.
- **D-02:** Add `NullRenderer` class in `voss/harness/render.py` (same module as `TtyRenderer` / `PlainRenderer` for locality). All methods are pass-through no-ops. Used by embedders that want zero terminal output and by tests/CI.
- **D-03:** Promote BOTH `Renderer` and `NullRenderer` to `voss.harness.__all__`. Do NOT promote `TtyRenderer` or `PlainRenderer` — those are CLI-internal renderer choices and can change shape. Embedders that want pretty terminal output should compose their own renderer.

### SDK-02: tool_entry_from_callable factory
- **D-04:** Signature: `tool_entry_from_callable(fn: Callable, *, is_mutating: bool, name: str | None = None, description: str | None = None, parameters: dict | None = None) -> ToolEntry`. `is_mutating` is REQUIRED keyword-only argument (M1 D-06 — data not name-pattern). `name` defaults to `fn.__name__`. `description` defaults to the first non-empty line of `fn.__doc__` (or empty string if no docstring). `parameters` defaults to a JSON-schema-shaped dict inferred from `inspect.signature(fn)` + PEP 484 type hints.
- **D-05:** Parameter-schema inference shape: `{"type": "object", "properties": {<param>: {"type": <json_type>, "description": ""}}, "required": [<params_without_defaults>]}` — mirrors what the existing `ToolDescriptor.parameters` field accepts. Python types map: `str` → `"string"`, `int` → `"integer"`, `float` → `"number"`, `bool` → `"boolean"`, `list` / `list[T]` → `"array"`, `dict` → `"object"`. Unannotated params get `{"type": "string"}` as a safe default. `Optional[T]` / `T | None` → schema for `T` with the param removed from `required`. Anything more exotic (Union of non-None, generics with constraints) raises a clear error pointing the caller to pass an explicit `parameters` dict.
- **D-06:** Async support: if `inspect.iscoroutinefunction(fn)` is true, the resulting `ToolEntry.invoke` is awaited inside the existing call path. The factory does NOT need to change `ToolEntry`'s call signature — the existing `descriptor.invoke(**kwargs)` already supports awaitable returns through the executor's `_run_step_loop` (M4). Confirm in research step.
- **D-07:** Live in `voss/harness/tools.py` alongside `ToolEntry` and `make_toolset`. Single module ownership keeps the tool surface coherent.
- **D-08:** No magic. The factory is a clean wrapper around `ToolDescriptor` construction; reading the source is the documentation for what gets inferred. No hidden registration side effects — the returned `ToolEntry` is added to the toolset dict by the caller.

### SDK-03: SessionView + RunView
- **D-09:** New file `voss/harness/views.py` to hold `SessionView` and `RunView` frozen dataclasses. Keeps the projection logic out of `session.py` (which owns the on-disk schema). `voss/harness/__init__.py` re-exports both classes plus `view_session()`.
- **D-10:** `SessionView` fields (frozen dataclass): `id: str`, `name: str`, `cwd: str`, `model: str`, `started_at: str` (ISO), `updated_at: str` (ISO), `total_cost_usd: float`, `runs: tuple[RunView, ...]`. Excluded: `turns` (raw chat blob — too volatile and large for embedder surface).
- **D-11:** `RunView` fields (frozen dataclass): `id: str`, `started_at: str`, `ended_at: str`, `goal: str`, `cost_usd: float`, `confidence: float | None` (extracted from `RunRecord.plan["confidence"]` when present, else None), `diff_summary: str`. Excluded: `inspected`, `changed`, `avoided`, `assumptions`, `decisions`, `risks`, `validation`, `failures`, `follow_ups` — all internal RunRecorder semantics that embedders shouldn't pin against.
- **D-12:** `view_session(record: SessionRecord) -> SessionView` is a pure projection — no I/O, no mutation. Promoted to `voss.harness.__all__`. Embedders that want a `SessionView` from disk read the session JSON via existing private path, hydrate the `SessionRecord`, then call `view_session`. (If that pattern proves clunky in real use, a `load_session(path) -> SessionView` helper is a v0.2 follow-up — not M7.)
- **D-13:** Tuples (not lists) for `SessionView.runs` to keep the view structurally immutable. Frozen dataclass + tuple field is the conventional Python "really read-only" idiom.

### SDK-04: RuntimeConfig.from_toml + default
- **D-14:** Section name in the TOML file: `[runtime]`. Matches the runtime config the file describes; keeps the door open for a future `[harness]` section to hold harness-only config (model preference, etc.) without colliding. `from_toml` reads the `[runtime]` section; missing section = use dataclass defaults for all fields.
- **D-15:** `RuntimeConfig.from_toml(path: str | Path) -> RuntimeConfig` raises `FileNotFoundError` when `path` does not exist (M1 D-13 loud failure). Returns a NEW `RuntimeConfig` instance — does NOT call `configure()` or mutate the module-level `_config` singleton. Embedders that want to install the result globally call `configure(**replace(loaded, **{}).__dict__)` themselves, or just pass the loaded config into their runtime call sites.
- **D-16:** `RuntimeConfig.default() -> RuntimeConfig` resolution order: (a) start from dataclass defaults; (b) overlay `~/.config/voss/config.toml` `[runtime]` section if the file exists (missing file is silent — `default()` must never raise on a fresh machine); (c) overlay env-vars: `VOSS_DEFAULT_MODEL`, `VOSS_DEFAULT_EMBEDDING_MODEL`, `VOSS_LOCAL_EMBEDDING_MODEL`, `VOSS_MAX_RETRIES`, `VOSS_MATCH_THRESHOLD`, `VOSS_CACHE_DIR`, `VOSS_TIMEOUT_SECONDS`, `VOSS_MAX_OUTPUT_TOKENS`. Env-vars win over file. Field naming: `VOSS_<UPPER_SNAKE>` mirrors dataclass field name.
- **D-17:** Env-var coercion: numeric fields cast via `int()` / `float()`; raises a clear error pointing at the offending env-var name if the cast fails. No silent fallback (M1 D-13 posture).
- **D-18:** `from_toml` validates known keys: unknown keys in the `[runtime]` section emit a warning to stderr but don't fail (forward-compat — newer config files on older voss should still load). Strict validation is a future hardening pass.

### SDK-05: Provider register stabilization
- **D-19:** Promote the existing `voss_runtime.providers.register(name, provider)` function to public. Re-exported through `voss_runtime/__init__.py` as `register_provider` (longer name disambiguates from generic `register`). The existing short name `register` in the `voss_runtime.providers` submodule stays available for in-tree callers; new code uses `voss_runtime.register_provider`.
- **D-20:** Add `replace: bool = False` keyword-only argument to BOTH the underlying `voss_runtime.providers.register` AND the re-exported `register_provider`. When `replace=False` and the name is already registered, raise `ValueError(f"provider '{name}' is already registered; pass replace=True to overwrite")`. When `replace=True`, the existing overwrite behavior is preserved. Default is `False` (loud-by-default per M1 D-13).
- **D-21:** Existing in-tree call sites that depend on silent overwrite (e.g., test setup that re-registers `__stub__`) must pass `replace=True` explicitly. M7 includes auditing and updating those call sites in the same wave.
- **D-22:** Validation of the `provider` argument: assert it implements `ModelProvider` via `isinstance` against the `ModelProvider` Protocol when `runtime_checkable` is set on the Protocol; otherwise duck-type (today's behavior). If `ModelProvider` is not currently `runtime_checkable`, M7 adds the decorator — purely additive change to enable validation.

### Tests + docs
- **D-23:** Extend `tests/packaging/test_public_api.py` `EXPECTED_HARNESS_PUBLIC_API` with: `NullRenderer`, `Renderer`, `RunView`, `SessionView`, `tool_entry_from_callable`, `view_session`. Final harness `__all__` size: 8 → 14. Extend `EXPECTED_RUNTIME_PUBLIC_API` with: `register_provider`. Final runtime `__all__` size: 26 → 27.
- **D-24:** New test file `tests/packaging/test_sdk_embedding.py` exercises the full embedding surface end-to-end using ONLY public symbols. Drives `run_turn` with a plain-Python tool wrapped via `tool_entry_from_callable`, `NullRenderer`, `StubProvider`, then projects the session via `view_session`. Asserts: the embedding completes, the session view exposes the expected fields, no `RunRecord` / `SessionRecord` import leaks into the test (gated by an explicit ast-check or a `pytest`-time `from voss.harness import *` smoke).
- **D-25:** `docs/sdk.md` updates: the "Known gaps (closing in M7)" section shrinks to zero items (or is replaced with "All M7 gaps shipped — see § Public surface for current API"); the "Public surface" tables for both `voss_runtime` and `voss.harness` gain rows for each new name; the Quick-start snippets that today reference `voss.harness.render.NullRenderer` (private path) are updated to `from voss.harness import NullRenderer`.
- **D-26:** Stability docstrings on `voss/harness/__init__.py` and `voss_runtime/__init__.py` mention each new public name with a one-line semantic summary. Docstring also reiterates the M7 promotion provenance (so future readers know these names are M7-stabilized rather than legacy).

### Claude's Discretion
- Exact TOML library (stdlib `tomllib` is the natural choice on Python 3.11+; `pyproject.toml` already lists `python_requires>=3.11`).
- Exact `__post_init__` validation set on `RuntimeConfig` if any (e.g., `timeout_seconds > 0`). Lean toward zero validation in M7 — defer to a future hardening pass.
- Exact location of `tool_entry_from_callable` test coverage (`tests/harness/test_tools.py` extension vs new file).
- Whether to make `SessionView` / `RunView` Pydantic models instead of dataclasses for `.model_dump()` ergonomics. Default: dataclasses (matches `SessionRecord` / `RunRecord` shape, no new dep coupling).
- Whether `register_provider` raises `ValueError` or a new `ProviderAlreadyRegisteredError` subclass. ValueError is fine for M7; a typed exception is a v0.2 polish.
- Whether `RuntimeConfig.default()` caches its result (lru_cache vs fresh each call). Default: fresh each call — embedders that want a singleton call `configure(**default().__dict__)` once at startup.
- Whether the `voss-demos/` showcase files (M4 follow-up scaffolding) gain a "via SDK" demo using the new public surface. Out of M7 strict scope; nice-to-have.
- Whether `view_session` accepts a `dict` (raw JSON-loaded session) in addition to a `SessionRecord`. Default: `SessionRecord` only — adding `dict` overload is trivial and a v0.2 polish if asked.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v0.1 scope and product framing
- `.planning/PROJECT.md` — "Harness-led v0.1" framing; `voss_runtime` is the embedding contract.
- `.planning/REQUIREMENTS.md` §"SDK Polish" lines containing SDK-01..05.
- `.planning/ROADMAP.md` §"Phase M7: SDK Polish" — Phase goal, required surface, capabilities, 5 success criteria, cross-cutting constraints (especially the M6/M7 ordering note).
- `docs/sdk.md` — Existing public-API contract + versioning policy + "Known gaps (closing in M7)" list. Must be updated in M7.

### Prior phase decisions (carry forward)
- `.planning/phases/M1-harness-happy-path/M1-CONTEXT.md` — D-05/D-06 (`is_mutating` is data not name-pattern; SDK-02 factory must REQUIRE `is_mutating`), D-13 (diagnose-don't-fix; SDK-04 missing-file raises, SDK-05 collision-default raises).
- `.planning/phases/M2-project-cognition/M2-CONTEXT.md` — D-13/D-14 (`RunRecord` / `SessionRecord` schemas; SDK-03 SessionView projects from these without binding embedders to the on-disk shape).
- `.planning/phases/M3-language-validation/M3-CONTEXT.md` — D-01/D-02 (auto-StubProvider + banner; M7 end-to-end test relies on this for hermetic embedding test).
- `.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md` — `run_turn` signature is the embedding entry point that all 5 promotions plug into; D-09 (Python `agent.py` parity oracle stays — M7 doesn't touch the agent loop).
- `.planning/phases/M6-npm-wrapper/...` — M7 ordering note: M7 ideally lands BEFORE the first `voss==0.1.0` PyPI publish + `voss@0.1.0` npm publish; if M6 ships first, M7 lands as 0.1.1 minor bump per pre-1.0 carve-out (`docs/sdk.md` §Versioning).

### Existing internals to promote (extend, do not rewrite)
- `voss/harness/render.py:24` — `Renderer` Protocol with 9 methods. `TtyRenderer` / `PlainRenderer` are existing implementations (kept private). `NullRenderer` is new but trivially mechanical.
- `voss/harness/tools.py:15` — `ToolEntry` frozen dataclass. `make_toolset(cwd)` builds the harness's default toolset. `tool_entry_from_callable` lives here.
- `voss/harness/session.py:65` — `RunRecord` dataclass (16 fields). `voss/harness/session.py:85` — `SessionRecord` dataclass (10 fields). Both stay private; `SessionView` / `RunView` project from them.
- `voss_runtime/_config.py:7` — `RuntimeConfig` dataclass (8 fields). Existing `configure(**kwargs)`, `get_config()`, `reset_config()` stay. M7 adds `from_toml` + `default`.
- `voss_runtime/providers/__init__.py:10` — Existing `register(name, provider)` function. M7 promotes + adds `replace` kwarg.
- `voss_runtime/providers/base.py` (referenced from `voss/harness/agent.py:24`) — `ModelProvider` Protocol. M7 ensures `@runtime_checkable` if not already.

### Existing public surface (do not regress)
- `voss/harness/__init__.py` — 8 symbols (`Plan`, `PermissionGate`, `RunSemantics`, `ToolCall`, `ToolEntry`, `TurnResult`, `main`, `run_turn`).
- `voss_runtime/__init__.py` — 26 symbols (`__all__` list — see file for canonical order).
- `tests/packaging/test_public_api.py` — Pin sets. 4 tests must continue to pass after M7; sets get extended with the new names.

### Tests + tooling
- `tests/packaging/test_entrypoint.py` — Existing entry-point smoke. M7 must not regress this.
- `tests/harness/test_voss_loop_parity.py` — M4 parity test; consumes `Renderer` and `ToolEntry`. M7 promotion must not change behavior visible to this test.
- `tests/eval/...` — M5 eval suite; consumes `RunRecord.cost_usd` via internal path. M7 leaves this path untouched.
- `pyproject.toml` — Already declares `tomllib`-compatible `python_requires=">=3.11"`. No new deps for M7.

### External libs (already in tree)
- `tomllib` (stdlib, Python 3.11+) — SDK-04 file reader.
- `inspect` (stdlib) — SDK-02 signature introspection.
- `typing.get_type_hints` — SDK-02 type-hint resolution.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`voss/harness/render.py` Renderer Protocol** — 9-method Protocol already defined. No design work for SDK-01; just promote + add NullRenderer no-op class.
- **`voss/harness/tools.py` ToolEntry + ToolDescriptor** — Existing frozen dataclass + descriptor split. SDK-02 factory composes these without changing either type.
- **`voss/harness/session.py` SessionRecord + RunRecord** — Source-of-truth for the on-disk schema. SDK-03 projection consumes these via attribute reads, no schema changes.
- **`voss_runtime/_config.py` RuntimeConfig** — Existing dataclass + `configure(**kwargs)`. SDK-04 adds two classmethods; no field changes.
- **`voss_runtime/providers/__init__.py` register** — Already a function. SDK-05 adds `replace` kwarg + re-export.
- **`tests/packaging/test_public_api.py` EXPECTED_*_PUBLIC_API frozensets** — Existing drift-detection pattern. SDK-23 extends with the 6 new harness names + 1 new runtime name.
- **`voss_runtime.StubProvider` + auto-fallback (M3 D-01)** — SDK end-to-end test uses this for hermetic test.
- **`tomllib` (stdlib)** — SDK-04 reader; no new dep.

### Established Patterns
- **`__all__` as the public-API gate** (SDK contract pass 2026-05-12) — M7 extends both `__all__` lists.
- **Loud failure on missing prerequisites** (M1 D-13, M2 D-07, M3 D-02, M4 D-10, M5 D-10) — SDK-04 `from_toml` raises; SDK-05 collision raises by default.
- **Frozen dataclasses as the read-only idiom** (`ToolEntry` is the precedent) — SDK-03 `SessionView` / `RunView` mirror this.
- **Pure projection / no I/O / no mutation** (M3 D-12 parity oracle posture) — `view_session` is a pure function.
- **Backward-compatible defaults** — `replace: bool = False` for register; `is_mutating` required (no default) for tool factory.
- **Test-public-api regression entries** (2026-05-12 SDK contract pass) — drift detection forces sdk.md updates in same PR.

### Integration Points
- **`voss/harness/__init__.py`** — Extended `__all__` import block. Stability docstring updated.
- **`voss_runtime/__init__.py`** — `register_provider` re-export + extended `__all__`. Stability docstring updated.
- **`voss/harness/render.py`** — New `NullRenderer` class added.
- **`voss/harness/tools.py`** — New `tool_entry_from_callable` factory added.
- **`voss/harness/views.py`** — New module for `SessionView` / `RunView` / `view_session`.
- **`voss_runtime/_config.py`** — `RuntimeConfig.from_toml` + `RuntimeConfig.default` classmethods added.
- **`voss_runtime/providers/__init__.py`** — `register` gains `replace` kwarg; collision raises by default.
- **`voss_runtime/providers/base.py`** — Confirm `ModelProvider` Protocol is `@runtime_checkable`; add decorator if missing.
- **`docs/sdk.md`** — Known-gaps section shrinks to zero; Public-surface tables get new rows; Quick-start snippets updated to import from public paths.
- **`tests/packaging/test_public_api.py`** — `EXPECTED_*_PUBLIC_API` extended; 4 existing tests continue to pass; new test ensures no `_private` symbols leaked into `__all__`.
- **`tests/packaging/test_sdk_embedding.py`** — New end-to-end embedding test using ONLY public symbols.
- **In-tree callers of `voss_runtime.providers.register`** — Audited and updated to pass `replace=True` where overwrite is intentional.

</code_context>

<specifics>
## Specific Ideas

- **M7 is a promotion phase, not a feature phase.** Every new public name maps to a private name that already exists OR is a thin convenience wrapper over existing internals. If a sub-task in planning requires authoring new behavior beyond the 5 promotions, it's scope creep — refile as v0.2.
- **The 5 promotions are independent.** Each can land as its own wave/plan with no cross-promotion dependencies. Wave parallelization is natural: SDK-01 (NullRenderer + Renderer), SDK-02 (tool factory), SDK-03 (SessionView), SDK-04 (TOML config), SDK-05 (register_provider). Final wave: stability docstrings + sdk.md updates + end-to-end embedding test (depends on all 5 landing).
- **Backward compatibility is the M7 gate.** Existing in-tree call sites must keep working. The only intentional break is the `register` collision policy — and that's bounded to in-tree callers, all of which can be updated to `replace=True` in the same wave.
- **The end-to-end embedding test (D-24) is the M7 success contract.** If it passes with ONLY public-symbol imports, M7 has done its job. If a test reviewer can grep for any private path in that file, M7 is incomplete.
- **No new public surface introduced as a side effect.** Each promoted helper either lives in `__all__` or is marked `_private` from day one. The drift test (`test_public_api.py`) is the safety net.
- **Versioning posture.** M7 ships as a minor pre-1.0 bump (0.1.x → 0.2.0) if it lands AFTER first publish, OR rolls into the 0.1.0 publish if it lands before. Either way is acceptable per `docs/sdk.md` §Versioning.

</specifics>

<deferred>
## Deferred Ideas

- **TS/JS SDK** — separate v0.2 candidate; M7 is Python-only.
- **HTTP / remote SDK** — local-first; deferred with TEAM-* / WEB-*.
- **Formal plug-in framework** with entry-points / sandboxing / manifest — v0.2+ when external authors arrive.
- **Promoting `SessionRecord` / `RunRecord` themselves** — schemas stay internal; `SessionView` is the embedder contract.
- **`load_session(path) -> SessionView` helper** — v0.2 if the SessionRecord-hydrate-then-view pattern proves clunky in real use.
- **`view_session` accepting a dict** — v0.2 polish if requested.
- **Pydantic validation of RuntimeConfig fields** — v0.2 hardening pass; M7 keeps dataclass.
- **Typed `ProviderAlreadyRegisteredError`** — v0.2 polish; M7 raises `ValueError`.
- **`unregister` / `list_providers` helpers** — out of M7 strict scope. Embedders that need them can call into the `_registry` dict via the private path until v0.2.
- **A `[harness]` TOML section** (separate from `[runtime]`) — reserved for future M5/M6 follow-up.
- **Renaming private modules to underscore-prefixed paths** — out of scope; `__all__` is sufficient gate.
- **Replacing `configure(**kwargs)` with TOML-only API** — additive only in M7.
- **`MinimalRenderer` subset Protocol** — embedders no-op cognition methods themselves.
- **Caching `RuntimeConfig.default()` result** — fresh per call.
- **`voss-demos/` "via SDK" demo using the new public surface** — nice-to-have; not in M7 strict scope.
- **`docs/release.md` release runbook updates for M7** — bundle with the v0.1.0 release prep, not M7.

</deferred>

<refinements>
## Decisions Refined Post-Research (2026-05-13)

`M7-RESEARCH.md` surfaced 7 corrections to upstream assumptions and 5 open questions. The following decisions REPLACE or AUGMENT the originals listed above. Where a refinement (R-NN) conflicts with the upstream decision (D-NN), the refinement WINS.

### Renderer method count (corrects D-01)
- **R-01:** `Renderer` Protocol has 11 methods, not 9. Existing methods at `voss/harness/render.py:24-44`: `banner`, `show_user`, `show_thinking`, `show_plan`, `show_tool_call`, `show_clarify`, `show_final`, `status`, `show_cognition`, `show_cognition_overflow`, `show_warning`. `NullRenderer` (D-02) must implement all 11 as no-ops. `test_public_api.py` extension list (D-23) is unchanged — symbol count is what's pinned, not method count.

### Tool factory delegation (refines D-04, D-05, replaces D-06)
- **R-02:** `tool_entry_from_callable` DELEGATES to the existing `@tool` decorator in `voss_runtime/tools.py:65-102` rather than re-implementing inference. The factory becomes ~10 LOC: call the existing decorator, wrap returned `ToolDescriptor` in a `ToolEntry(descriptor=..., is_mutating=...)`. Single source of truth for inference; no schema-dialect drift.
- **R-03:** Optional[T] / T | None dialect: match the existing `@tool` decorator's `nullable: True` shape (Research Q1 + Risk 5). Drop the D-05 "remove from required" rule. Whatever the existing decorator emits is what the factory emits — by delegation, this is automatic.
- **R-04:** Sync-callable handling: WRAP. If `inspect.iscoroutinefunction(fn)` is `False`, the factory wraps `fn` in an async shim before constructing the descriptor. The executor at `voss/harness/agent.py:430` always awaits `entry.invoke(...)`, so sync callables passed without the shim crash at runtime. Wrapping is the cheapest fix and preserves the embedder ergonomic ("any callable works").

### SessionView projects from dicts (refines D-11)
- **R-05:** `SessionRecord.runs` is `list[dict]` (raw), not `list[RunRecord]` (per `voss/harness/session.py:94` + `voss/harness/cli.py:830` usage). `view_session` projects each run dict via defensive `.get()` reads with sensible defaults: `id = r.get("id", "")`, `started_at = r.get("started_at", "")`, `ended_at = r.get("ended_at", "")`, `goal = r.get("goal", "")`, `cost_usd = float(r.get("cost_usd", 0.0))`, `diff_summary = r.get("diff_summary", "")`. Confidence extraction stays as documented (`r.get("plan", {}).get("confidence")` → `float | None`).
- **R-06:** `view_session` accepts only `SessionRecord` input in M7 (per D-12). A future `view_session(dict)` overload is v0.2 polish; Research Q3 deferred.

### ModelProvider already runtime_checkable (corrects D-22)
- **R-07:** `ModelProvider` Protocol at `voss_runtime/providers/base.py:22` ALREADY has `@runtime_checkable`. D-22's "add decorator if missing" is a no-op. SDK-05 just adds the `isinstance(provider, ModelProvider)` validation call inside `register` — no Protocol modification needed.

### register_provider naming + audit (refines D-19, D-21)
- **R-08:** Re-export as `register_provider` (not bare `register`) per D-19 — Research Risk 6 confirms bare `register` would shadow the `voss_runtime.providers.register` symbol unhelpfully. Long name disambiguates.
- **R-09:** 10 in-tree call sites of `voss_runtime.providers.register` must pass `replace=True` in the SAME wave as the SDK-05 default-flip (Research Risk 3). Splitting across waves breaks CI on the intermediate commit. The single highest-leverage fix is `tests/examples/helpers.py:98` (the `register_stub` context manager) — covers most downstream tests. Planner: scope SDK-05 as a single atomic wave.

### docs/sdk.md scope (refines D-25)
- **R-10:** `docs/sdk.md` has FOUR items in "Known gaps (closing in M7)", plus SDK-05 referenced in the "Plugin authoring (informal in v0.1)" paragraph at line 224. M7 wave-final task updates BOTH locations: known-gaps section shrinks to zero, plugin-authoring para gets rewritten to point at the new `register_provider` public entry point.

### Version posture (locks Research Q5)
- **R-11:** `pyproject.toml` stays at `0.1.0` during M7 execution. The version bump (to 0.2.0 if M7 ships post-M6, or stays at 0.1.0 if pre-M6) is deferred to the publish wave. M7 PRs do not touch `pyproject.toml [project] version`.

### Wave structure (locks Research §Wave Recommendations)
- **R-12:** Six waves, mostly parallel:
  - **Wave 1 (SDK-01)** — `NullRenderer` + Renderer promotion. Independent. Files: `voss/harness/render.py`, `voss/harness/__init__.py`.
  - **Wave 2 (SDK-02)** — `tool_entry_from_callable` factory delegating to `@tool`. Independent. Files: `voss/harness/tools.py`, `voss/harness/__init__.py`.
  - **Wave 3 (SDK-03)** — `SessionView` / `RunView` / `view_session` in new `voss/harness/views.py`. Independent. Files: `voss/harness/views.py` (new), `voss/harness/__init__.py`.
  - **Wave 4 (SDK-04)** — `RuntimeConfig.from_toml` + `default()`. Independent. Files: `voss_runtime/_config.py`.
  - **Wave 5 (SDK-05) — ATOMIC** — `register` gains `replace=False` kwarg + `isinstance(provider, ModelProvider)` validation + re-export as `register_provider` + audit/update all 10 in-tree call sites + `voss_runtime/__init__.py` `__all__` extension. Must NOT split.
  - **Wave 6 (Integration + tests + docs)** — Depends on waves 1–5. `tests/packaging/test_public_api.py` `EXPECTED_*_PUBLIC_API` extension; new `tests/packaging/test_sdk_embedding.py` end-to-end test (the M7 success contract per D-24); stability docstring updates on both `__init__.py` files; `docs/sdk.md` known-gaps + plugin-authoring rewrite.
- **R-13:** Waves 1–4 parallelize cleanly — disjoint files, no shared symbols. Wave 5 is sequential after wave 4 only to avoid `voss_runtime/__init__.py` merge conflicts with wave 4's `RuntimeConfig.from_toml` import addition (both touch the same file). Wave 6 depends on all prior waves landing.

### Open questions resolved
- Q1 (sync callable): WRAP — see R-04.
- Q2 (Optional dialect): match existing `nullable:True` — see R-03.
- Q3 (view_session dict overload): v0.2 — see R-06.
- Q4 (sdk.md update scope): both locations — see R-10.
- Q5 (version bump): defer to publish wave — see R-11.

</refinements>

---

*Phase: M7-sdk-polish*
*Context gathered: 2026-05-13*
*Refined post-research: 2026-05-13*
