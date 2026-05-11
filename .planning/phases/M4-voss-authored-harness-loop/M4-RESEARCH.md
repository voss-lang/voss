# Phase M4: Voss-authored Harness Loop - Research

**Researched:** 2026-05-11
**Domain:** Dogfood `.voss` on the harness turn loop. Five-file pipeline under `voss/harness/agent/{loop,router,planner,executor,reviewer}.voss`. `voss check <dir>` + `voss compile <dir>` directory walking. `VOSS_HARNESS=compiled` env-flag boot path with per-file `.voss-cache/harness/*.py` + `_manifest.json` (sha256+voss_version key, loud stale-cache error).
**Confidence:** HIGH on every file:line citation against the live repo at `/Users/benjaminmarks/Projects/Voss/` (commit `99d292e` per gitStatus). MEDIUM on two compiler-surface gaps (`use ... as alias` + `await imported_fn(...)`) — the gaps are confirmed; the smallest-diff resolution is a recommendation, not a verified patch.

## Summary

M4 is a **dogfood-and-wiring** phase whose hardest research question is "where does the .voss surface stop and where do we need compiler work?" The answer, after reading the parser/grammar/codegen at every relevant file:line, is that **two locked CONTEXT decisions cannot be implemented against the current compiler** and need narrow grammar+codegen extensions, both fitting in <100 LOC of compiler diff:

1. **`use voss.harness as h` does not parse and never has.** Grammar (`voss/grammar.lark:174-175`) is `use_path: IDENT ("::" IDENT)*` — no `.` separator and **no `as <alias>` clause**. Parser (`voss/parser.py:711-715`) always sets `alias=None`. The AST (`UseStmt.alias: str | None`) and codegen (`voss/codegen.py:126-148`) already support aliases — only the grammar+parser are missing it. **Smallest fix:** add `("as" IDENT)?` to the `use_stmt` rule and pass the alias through the transformer. Replace the CONTEXT D-02 strawman `use voss.harness as h` with `use voss::harness::run_turn` / `use voss::harness::tools::ToolEntry` for symbols (compiles to `from voss.harness import run_turn`) — the `voss` package IS importable (the compiler itself lives there, and `voss.harness` is a real sub-package per `voss/harness/__init__.py:1-8`). Aliasing is needed only if .voss imports a top-level module (e.g. `use voss::harness as h` so `.voss` can write `h.something`); see the call-site issue in (2).

2. **There is no way to `await` an imported Python coroutine from `.voss`.** Codegen (`voss/codegen.py:438-447`) emits `await` **only** when the callee is a bare `Identifier` whose name appears in `self.generated_fns` (i.e. a `fn` declared in the same file). Member-style calls (`h.run_turn(...)`) and identifier calls against `use`-imported names are not auto-awaited. The .voss grammar (`voss/grammar.lark`) has **no `await` token**. Therefore the M4 D-04 executor pattern *"voss executor receives `tools: dict[str, ToolEntry]` and iterates plan.steps calling Python `tool.invoke`"* is unimplementable as written — `ToolEntry.invoke(...)` returns the result of `descriptor.invoke(**kwargs)` which calls `func(**kwargs)`, and harness tools (`voss/harness/tools.py:48-58` `fs_read`, etc.) are `async def`, so the result is a coroutine that must be awaited. The same applies to `provider.complete(...)` in planner.voss. **Smallest fix:** extend the existing `generated_fns` await-trigger in `codegen.py:441-446` to also auto-await calls against names imported by `use` (track `use_imports: frozenset[str]` on the emitter the way `generated_fns` is tracked; populate it from `ProgramEmitter.emit` at `codegen.py:1175-1176`). Alternative escape-hatch: introduce a sync wrapper `ToolEntry.invoke_sync` (Python-side `asyncio.get_event_loop().run_until_complete(...)`) but that re-enters the loop and is fragile. The codegen extension is cleaner and ~20 LOC.

Aside from those two compiler gaps, every other M4 building block already exists at full strength:

- **`async def` codegen for fns** — `voss/codegen.py:798-801` emits `async def {name}(...)` for every `FnDecl`. The compiled `loop.py` will export `async def run_turn(...)` naturally provided `loop.voss` declares `fn run_turn(...) -> TurnResult { ... }` matching the existing signature at `voss/harness/agent.py:100-112`.
- **`ctx(budget: N tokens) { ... }`** — `voss/grammar.lark:128`, `voss/codegen.py:935-957` emit `async with ContextScope(token_budget=N) as ctx:`. Already used by all three samples.
- **`probable<T>` + `if x @ p >= 0.80`** — `voss/grammar.lark:73-74` confidence_gate, `voss/analyzer.py:_warn_unguarded_probable` (M3-RESEARCH cites :479-501 and the gate logic). Lowering is implicit via `ProbableValue` wrapping. Used by `samples/classify.voss:5`.
- **`try { } catch [name] { }`** — `voss/grammar.lark:133`, `voss/parser.py:542-557`, `voss/codegen.py:1107-1126`. Lowers to `try: ... except Exception [as name]:`.
- **`within budget(...) { } fallback { }`** — `voss/grammar.lark:129`, `voss/codegen.py:_emit_within:959+`. Already used by `samples/research.voss:33-38`.
- **Programs with NO top-level executable code** (only `fn`/`agent`/`use` decls) generate no `async def main():` wrapper — verified at `voss/codegen.py:1192-1231` (`requires_async_main = bool(execs)` where `execs` is the non-decl, non-`UseStmt` top-level statements). So `loop.voss` containing only `use ...` + `fn run_turn(...)` compiles to a clean module that exports `run_turn`, importable by `voss/harness/cli.py`.
- **`StubProvider` parity test infrastructure** — `tests/harness/test_agent_integration.py:21-50` already has a `FakeProvider` returning canned `Plan` objects + tests against `run_turn`. M4's `tests/harness/test_voss_loop_parity.py` mirrors this exactly with a single `Plan` fixture and runs it through both backends.

The "wiring" parts (`voss check <dir>`, `voss compile <dir>`, `VOSS_HARNESS=compiled` import swap, manifest writer, `StaleHarnessCacheError`) are all sub-100-LOC additions with clean analog sites in tree.

**Primary recommendation:** Plan order — (a) **Wave 0 compiler gap** sub-plan: extend grammar+parser+codegen with `use ... as alias` (grammar `("as" IDENT)?`, parser transformer pass-through, ~30 LOC) AND auto-await for `use`-imported callees (codegen track `use_imports` frozenset and extend the await condition at codegen.py:441-446, ~20 LOC). One plan, ~50 LOC compiler diff + 4-6 unit tests. (b) **Wave 1 dir-walking** `voss check <dir>` + `voss compile <dir>` in `voss/cli.py:204-228` and `voss/cli.py:147-167`, plus `voss/harness/sandbox.py` gets a `write_cache(cache_root, relpath, text)` helper. (c) **Wave 1 cache + manifest** writer module (`voss/harness/cache.py` new file, ~60 LOC) + `StaleHarnessCacheError` in `voss/harness/diagnostics.py`. (d) **Wave 2 .voss files** — author the five `voss/harness/agent/*.voss` files using the seam decided in Wave 0. (e) **Wave 2 boot dispatch** in `voss/harness/cli.py` — single `_resolve_run_turn(env)` helper that returns either the Python `run_turn` or the compiled-cache `run_turn`. (f) **Wave 3 parity test** + CI gate + doctor row. Gaps (1) and (2) are scoped sub-plans, NOT blockers: they have known fixes and bounded surface.

## Project Constraints (from CLAUDE.md)

There is no `/Users/benjaminmarks/Projects/Voss/CLAUDE.md`. The session-injected `~/CLAUDE.md` is QuadFlow project-manager guidance (irrelevant to compiler work; the agent should NOT create QuadFlow ideas/issues for M4 plans). The user-global guidelines at `~/.claude/CLAUDE.md` ("simplicity first / surgical changes / goal-driven execution") apply as stylistic preference — keep tasks minimal, no scope creep into broader compiler refactors.

## User Constraints (from CONTEXT.md)

### Locked Decisions

(verbatim from `.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md` `<decisions>` block — D-01 through D-16)

**File decomposition + Python/.voss seam**
- **D-01:** Pipeline split — one stage per file. `loop.voss` (orchestration + ctx budget + history), `router.voss` (`probable<Intent>` classification), `planner.voss` (`probable<Plan>` ask + confidence gate), `executor.voss` (tool-step dispatch), `reviewer.voss` (final synthesis from results). Linear pipeline; `loop.voss` is the only file that calls the others. Each file targets 20–40 LOC of `.voss`.
- **D-02:** Thin `.voss`. The files express ONLY control flow — `ctx(budget: N)`, `probable<T>`, confidence gates (`plan @ p >= threshold`), `try/catch`, `fallback`. Everything else stays Python: the `Plan`/`ToolCall` pydantic models (`voss/harness/agent.py:35-56`), the `PLAN_SYSTEM` prompt text, the tool registry/descriptors, `ModelProvider.complete` calls, the permission gate, `SessionRecord`/`RunRecord`, rendering. `.voss` files import Python symbols via `use voss.harness as h` (or equivalent — researcher must confirm parser surface). **(Researcher: the literal token form is broken — see Pitfall 1 below. Use `use voss::harness::run_turn` and `use voss::harness::tools::ToolEntry` for name imports; `use voss::harness as h` requires a small grammar extension for the `as` clause.)**
- **D-03:** Orchestration direction — Python imports compiled `.voss` functions. `voss compile voss/harness/agent/loop.voss` produces `.voss-cache/harness/loop.py` whose top-level exports include `async def run_turn(task, *, tools, cwd, renderer, confidence_threshold, token_budget, model, provider, history, permissions) -> TurnResult` — the same signature as `voss/harness/agent.py:100-112`. The harness CLI swaps imports based on `VOSS_HARNESS`. No new runtime entry-point shape.
- **D-04:** Tool exposure to `.voss` — tools are NOT redeclared as `@tool` in the `.voss` files. They remain Python descriptors (`voss/harness/tools.py`); the `.voss` `executor` receives the `tools: dict[str, ToolEntry]` argument and iterates `plan.steps`, calling back into Python `tool.invoke(step)`. Permission gate stays 100% Python (M1 D-05). `.voss` does not gain a privileged tool-call path. **(Researcher: requires compiler extension — see Pitfall 2 / Open Question Q-2. `ToolEntry.invoke` returns a coroutine because `func` is `async def`; current codegen does not emit `await` for member calls or imported-name calls.)**

**`voss check <dir>` + CI gate**
- **D-05:** Extend `voss check` to walk directories. In `voss/cli.py:check` (line 204), when `source.is_dir()`, glob `source.rglob("*.voss")`, parse + analyze each, aggregate diagnostics across files (preserving per-file line/col), exit non-zero on any error. Single-file behavior unchanged. Same for `voss compile`.
- **D-06:** CI gate is static-only — `voss check voss/harness/agent/` runs in CI. Matches M3 D-03 (static-only check). Compile-and-stub-run regression coverage lives in a separate pytest file (D-13), NOT inside the `voss check` invocation.
- **D-07:** Aggregated diagnostic output format: one `<file>:<line>:<col>: <severity> <message>` line per diagnostic, grouped by file, with a final summary `N errors, M warnings across K files`. Non-zero exit on any error. `--warnings-as-errors` still applies.

**Boot path (DOG-07) + parity oracle**
- **D-08:** Env-flag opt-in. `VOSS_HARNESS=compiled` OR `[harness] backend = "compiled"` in `~/.config/voss/config.toml` flips the import in `voss/harness/cli.py`. Default: `"python"`. Resolution order: env-var > config.toml > default. CLI flag override `--harness={python,compiled}` is allowed but optional.
- **D-09:** `voss/harness/agent.py:run_turn` stays in tree indefinitely as the parity oracle. Mirrors M3 D-12 (raw-Python parity oracle). It is not retired by M4.
- **D-10:** Stale-cache behavior under `VOSS_HARNESS=compiled`: the loader reads `.voss-cache/harness/_manifest.json`, compares each source sha to the live source. On mismatch (or missing manifest), raise a structured `StaleHarnessCacheError` with the message `compiled harness cache stale — run: voss compile voss/harness/agent/`. NO silent fallback to Python.
- **D-11:** Parity contract: `tests/harness/test_voss_loop_parity.py` runs a fixture task through both backends under `StubProvider` (M3 D-01 auto-fallback exercised). Asserts: `python_result.final == voss_result.final` AND tool-call sequence (name + args) is identical. Single fixture task in M4 (`"noop summary of fixture.md"`); broader fixture matrix deferred.
- **D-12:** M4 success bar: (a) `voss check voss/harness/agent/` exits 0; (b) `voss compile voss/harness/agent/` produces all five `.py` files + `_manifest.json`; (c) `VOSS_HARNESS=compiled voss do "<fixture task>"` exits 0 with non-empty `TurnResult.final`; (d) parity test passes.

**Cache layout + invalidation (DOG-08)**
- **D-13:** Per-file artifacts. `.voss-cache/harness/{loop,router,planner,executor,reviewer}.py` — one Python file per `.voss` source. `_manifest.json` shape: `{ "version": 1, "voss_version": "<pkg version>", "compiled_at": "<ISO>", "sources": { "loop.voss": {"sha256": "<hex>", "lines": <int>}, ... } }`. Per-file isolation makes regressions traceable.
- **D-14:** Cache key = source `sha256` + `voss_version`. NOT git-head. NOT mtime. The loader recomputes sha at boot under `VOSS_HARNESS=compiled` and raises on mismatch.
- **D-15:** Cache writes go through `voss/harness/sandbox.py` (M2 D-06 cross-cutting). **(Researcher: `sandbox.py` today (49 LOC, `jail_path` + `shell_allowed` only) has NO write helper. M4 must add one — `write_cache(project_root, relpath, text)` — that jails then writes atomically. Pattern: extend M2's existing approach where `tools.py:91-93` calls `jail_path` then `p.write_text(content)`. See Pattern 4 below.)**
- **D-16:** Eager compile only. `voss compile voss/harness/agent/` is the contract. Integration: (a) `voss doctor` reports cache freshness (informational row, never blocking); (b) install-time one-liner in `README.md` (`voss compile voss/harness/agent/` after `pip install -e .`). JIT compile-on-import rejected.

### Claude's Discretion

(verbatim)

- Exact syntax of `use voss.harness as h` — researcher must confirm `voss/parser.py` + `voss/grammar.lark` accept it; if absent, small grammar/codegen extension precedes the `.voss` files. **(Researcher: ABSENT today. See Pitfall 1 + Q-1. Recommendation: a Wave 0 sub-plan adds `("as" IDENT)?` to `use_stmt` AND auto-await for `use`-imported callees in codegen. Two small fixes; one plan. Use `use voss::harness::run_turn` / `use voss::harness::tools::ToolEntry` for name imports — those work today.)**
- Exact `probable<Intent>` representation in `router.voss` — pick the smallest shape; mirror `Plan`'s pydantic import pattern from D-02. **(Researcher: `probable<string>` distinguishing `"slash"` vs `"natural"` is enough; see Pattern 2 below. A new pydantic class is not required because `probable<string>` already lowers correctly per M3-RESEARCH §LANG-02.)**
- The `voss compile <dir>` invocation shape — flag-compatible with single-file `voss compile`; emit per-file diagnostics and final summary identical in spirit to `voss check`. **(Researcher: yes — share the dir-walking helper between `check` and `compile`. See Pattern 3.)**
- Whether `--harness=python|compiled` CLI flag is added in addition to env-var (D-08) — convenient for testing; rejecting it forces env-var ceremony. **(Researcher: recommend skip for M4. The env-var is already trivial (`VOSS_HARNESS=compiled voss do ...`). Adding a CLI flag means plumbing it through every command shape — `do`, `chat`, `edit`, `resume` — and the M4 success bar (D-12 (c)) is just `voss do`. Add the flag only if a real user-pain emerges.)**
- `StaleHarnessCacheError` exception class location — `voss/harness/diagnostics.py` is the natural home. **(Researcher: agree. `voss/harness/diagnostics.py` is 198 LOC of doctor `Check` infrastructure; adding a new `StaleHarnessCacheError(VossError)` class at the top of the module mirrors `voss/exceptions.py:VossError` cleanly. Alternative `voss/harness/cache.py` (new file) is acceptable if cache code grows; for M4 surface size, diagnostics.py is fine.)**
- Fixture task content for the parity test (D-11) — any deterministic no-op-ish task that `StubProvider` resolves identically under both backends. **(Researcher: see Pattern 6 below. The fixture is the Plan dict the StubProvider's response map returns, not the task text. Task text `"summarize README"` + one `fs_read` step + final `"README begins with: {{step_0}}"` is the smallest deterministic shape.)**
- `voss doctor` reporting for harness-cache freshness — extends M2's cognition rows; informational warning only, never blocking. **(Researcher: add `check_harness_cache_fresh(cwd)` to `voss/harness/diagnostics.py:run_all_checks` returning `Check(name="harness cache", result=WARN if stale else OK, fix="voss compile voss/harness/agent/")`. Mirrors `check_project_dirs` at diagnostics.py:158-178.)**

### Deferred Ideas (OUT OF SCOPE)

(verbatim)

- Live-provider parity under `VOSS_HARNESS=compiled` — M5 or hardening phase.
- `voss edit` scoped sessions through compiled path — deferred.
- `voss chat` REPL through compiled path — deferred.
- `/analyze` rewritten in `.voss` — M2 D-02 deferred this.
- Auto-detect boot path / silent fallback — rejected.
- JIT compile-on-import — rejected.
- Bundled single-module cache layout (`harness.py` exporting `run_turn`) — rejected.
- Retiring `voss/harness/agent.py` — not M4. Parity oracle stays indefinitely.
- Symbolic-only DOG-07 (check + import; no real turn) — rejected as too weak.
- Full-parity DOG-07 across all M1 commands on live + stub — too large.
- Codegen-snapshot tests on `.voss-cache/harness/*.py` — M3 deferral inherited.
- Compile-and-stub-run inside `voss check` — gate stays static; pytest covers compile+run.
- `voss check --speed-budget` flag — M3 deferral inherited.
- Tree-sitter / Linguist upstream PR — post-v0.1.
- Rust harness shell — explicitly post-v0.1.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOG-01 | `voss/harness/agent/loop.voss` exists | New file, ~30 LOC. Calls into router/planner/executor/reviewer with `ctx(budget: N tokens)` wrapping the pipeline. Pattern 2 below. |
| DOG-02 | `voss/harness/agent/router.voss` exists | New file, ~20 LOC. `probable<string>` for `"slash"` vs `"natural"` route classification. Pattern 2. |
| DOG-03 | `voss/harness/agent/planner.voss` exists | New file, ~30 LOC. `probable<h.Plan>` ask + confidence gate + clarify branch. Pattern 2. |
| DOG-04 | `voss/harness/agent/executor.voss` exists | New file, ~30 LOC. Tool-step dispatch loop, calling Python `tool.invoke(step)` via `use voss::harness::tools::ToolEntry`. **REQUIRES auto-await sub-plan (Pitfall 2).** Pattern 2. |
| DOG-05 | `voss/harness/agent/reviewer.voss` exists | New file, ~20 LOC. Substitutes `{{step_N}}` placeholders in `plan.final_when_done` against results; returns final. Pattern 2. |
| DOG-06 | `voss check voss/harness/agent/` is a CI gate | Extend `voss/cli.py:check` for dir input (D-05). Add CI step to `.github/workflows/ci.yml:14-26` job `stub`. Pattern 3. |
| DOG-07 | Bare `voss` boots through compiled harness logic when env-flag set | Add `_resolve_run_turn(env, config)` to `voss/harness/cli.py` swapping the `run_turn` import. Mirror the existing `_resolve_auth_or_die` pattern at cli.py:108-147. Pattern 5. |
| DOG-08 | Compiled harness artifacts cache under `.voss-cache/harness/` | New `voss/harness/cache.py` (writer + loader + manifest) OR extend `voss/harness/sandbox.py` with a `write_cache(...)` helper. `_manifest.json` schema per D-13. Pattern 4. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Authoring control flow in `.voss` (ctx, probable, gates, try/catch) | Source (`voss/harness/agent/*.voss`) | — | This is the dogfood. 5 files, 20-40 LOC each. |
| Hosting Python types/models/prompts | Source (`voss/harness/agent.py` parity oracle + `tools.py` + `permissions.py` + `providers.py`) | — | D-02 thin .voss: pydantic models, prompts, provider client, permission gate stay Python. |
| Source parsing (`use ... as alias`) | Compiler (`voss/grammar.lark` + `voss/parser.py`) | — | Wave 0 sub-plan — `("as" IDENT)?` extension. ~10 LOC grammar+parser. |
| Auto-await for `use`-imported callees | Compiler (`voss/codegen.py`) | — | Wave 0 sub-plan — extend `generated_fns` await-trigger at codegen.py:441-446. ~20 LOC. |
| Directory-mode parsing + analysis aggregation | Compiler CLI (`voss/cli.py:check` + `voss/cli.py:compile`) | — | D-05. Single `_walk_voss_sources(path)` helper used by both. ~40 LOC. |
| Cache write + manifest | Harness (`voss/harness/cache.py` new OR `voss/harness/sandbox.py` extended) | — | D-13/D-14/D-15. Per-file `.py` + `_manifest.json` writer; sha256+voss_version key. ~60 LOC. |
| Cache freshness check + loud failure | Harness (`voss/harness/diagnostics.py` extended) | Harness CLI (`voss/harness/cli.py` import-swap site) | D-10. `StaleHarnessCacheError` (subclass of `voss.exceptions.VossError`) raised at import time. |
| Boot-path import swap | Harness (`voss/harness/cli.py` `_resolve_run_turn(env, config)`) | — | D-08. Single seam. `voss do` / `voss chat` / `voss edit` / `voss resume` all call `_resolve_run_turn()` then `asyncio.run(run_turn(...))`. |
| Parity oracle test | Test (`tests/harness/test_voss_loop_parity.py` new) | — | D-11. Mirrors `tests/harness/test_agent_integration.py:21-50` `FakeProvider` pattern. |
| CI gate | CI workflow (`.github/workflows/ci.yml:14-26`) | — | D-06. One new step `run: python -m voss.cli check voss/harness/agent/` before pytest. |
| Doctor freshness row | Harness diagnostics (`voss/harness/diagnostics.py:run_all_checks`) | Harness CLI render | D-16. Informational only — never blocks. |

## Standard Stack

### Core (already in tree; nothing new for M4)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `lark` | >=1.1.9 [VERIFIED via M3-RESEARCH; pyproject.toml:11] | Parser generator | Grammar extension for `use ... as` lands here. |
| `click` | >=8.1.0 [VERIFIED via M3-RESEARCH] | CLI | `voss check`/`voss compile` dir-walk + harness commands. |
| `pydantic` | >=2.6,<3.0 [VERIFIED via M3-RESEARCH] | Schemas | `Plan`/`ToolCall` already pydantic v2 (`voss/harness/agent.py:35-56`). |
| `pytest` | >=8.0 [VERIFIED via M3-RESEARCH] | Test runner | Parity test framework. |
| `pytest-asyncio` | >=0.23 [VERIFIED via M3-RESEARCH] | Async test support | `run_turn` is async; parity test asserts via `asyncio.run`. |
| `tomli` / `tomllib` | stdlib in 3.11+ | `[harness] backend` parsing | Used by `voss/harness/config.py` today (verified by `voss/harness/cli.py:42-56` `_resolve_default_model` calling `harness_config.load_harness_config`). |

### Supporting (used unchanged)
| Library | Purpose | When |
|---------|---------|------|
| `hashlib` | sha256 cache key | `_manifest.json` writer. Already used at `voss/harness/cognition.py:298` for repo.idx sha1. Use sha256 per D-14. |
| `json` | manifest read/write | Same pattern as `voss/harness/cognition.py:80-94` `_load_json` + `:84` `json.loads(path.read_text())`. |
| `voss_runtime` | `StubProvider`, `ContextScope`, `EpisodicMemory`, `ProbableValue`, `ModelProvider` | Already imported by `voss/harness/agent.py:17-24`; compiled `.voss` imports same names. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `voss/harness/cache.py` module for write/load/manifest | Extend `voss/harness/sandbox.py` | Sandbox.py today is 49 LOC of path-jail + shell-allowlist (the M2 "cache writes go through sandbox" decision IS conceptual — there's no write helper). Either is fine. CONTEXT D-15 picks sandbox; mirror by ADDING `write_cache(project_root, relpath, text) -> Path` to sandbox.py (~15 LOC) and a separate `voss/harness/cache.py` with `load_manifest`, `compute_sources_sha`, `assert_fresh` (~50 LOC). Both files modified, narrow surfaces. |
| Subclass-`asyncio.run` wrapper for sync tool invoke | Codegen extension for auto-await on use-imports | Sync wrapper re-enters the event loop and breaks the outer `asyncio.run` at `voss/harness/cli.py:235`. Codegen extension is ~20 LOC and stays inside the compiler. Recommended. |
| Hand-write `.voss-cache/harness/*.py` to bypass codegen gaps | Fix codegen properly | Hand-writing defeats the dogfood. The compiler gaps are real; fix them. |
| Per-CLI-flag `--harness=python|compiled` | Env-var + config.toml only | Env-var is enough for M4 success bar (D-12). Skip flag. |

**Installation:** No new dependencies. Existing `pip install -e ".[dev]"` covers everything.

**Version verification:** Stack already verified in M3-RESEARCH (pyproject.toml:10-21 floors). M4 adds zero deps.

## Architecture Patterns

### System Architecture Diagram

```
                          ┌──────────────────────────────────┐
                          │ voss/harness/agent/{loop,router, │
                          │ planner,executor,reviewer}.voss  │
                          │       (sources, ~150 LOC)        │
                          └──────────────┬───────────────────┘
                                         │
              ┌──────────────────────────┼─────────────────────────┐
              │                          │                         │
              ▼                          ▼                         ▼
     voss check <dir>          voss compile <dir>           voss do "<task>"
   (D-05 / D-06 / D-07)     (eager compile, D-16)      (D-07 boot-path swap)
              │                          │                         │
              ▼                          ▼                         ▼
   ┌────────────────────┐   ┌────────────────────────┐  ┌────────────────────────┐
   │ rglob *.voss → for │   │ rglob *.voss → for     │  │ env=VOSS_HARNESS       │
   │ each: parse+analyze│   │ each: _compile_source  │  │   ?: read env > config │
   │ aggregate diagnostc│   │ → write via sandbox    │  │   > default("python")  │
   │ + summary line     │   │ → write _manifest.json │  │ if compiled:           │
   │ exit 0/1           │   │ (sha256+voss_version)  │  │   load manifest,       │
   └─────────┬──────────┘   └───────────┬────────────┘  │   verify shas,         │
             │                          │               │   import run_turn      │
             ▼                          ▼               │   from .voss-cache/    │
      diagnostics             .voss-cache/harness/      │     harness/loop.py    │
      (CI gate D-06)            {loop,router,           │ else:                  │
                                 planner,executor,      │   from voss.harness.   │
                                 reviewer}.py +         │     agent import       │
                                 _manifest.json         │     run_turn (oracle)  │
                                                        └────────────┬───────────┘
                                                                     │
                                                                     ▼
                                                          asyncio.run(run_turn(
                                                            task, tools=...,
                                                            cwd=..., renderer=...,
                                                            provider=...))
                                                                     │
                                                                     ▼
                                                            TurnResult.final
                                                            (parity test asserts
                                                             python == compiled
                                                             under StubProvider)

Python parity oracle (D-09, never retired):
  voss/harness/agent.py:run_turn  ←  the algorithm; line 100-231
  voss/harness/agent.py:Plan,ToolCall,TurnResult,PLAN_SYSTEM
  voss/harness/tools.py:ToolEntry  ←  imported by both backends via `use`
  voss/harness/permissions.py:PermissionGate
```

### Recommended Project Structure (deltas only)

```
voss/
├── grammar.lark              # MODIFY: add ("as" IDENT)? to use_stmt
├── parser.py                 # MODIFY: pass alias through use_stmt transformer
├── codegen.py                # MODIFY: track use_imports; auto-await imported callees
├── cli.py                    # MODIFY: dir-walk in check (line 204) + compile (line 147)
└── harness/
    ├── agent.py              # UNCHANGED — parity oracle (D-09)
    ├── cli.py                # MODIFY: _resolve_run_turn(env, config) seam (D-08)
    ├── sandbox.py            # MODIFY: add write_cache(project_root, relpath, text)
    ├── diagnostics.py        # MODIFY: add StaleHarnessCacheError + check_harness_cache_fresh
    ├── cache.py              # NEW: load_manifest, compute_sha, assert_fresh, write_manifest (~80 LOC)
    └── agent/                # NEW directory — the dogfood
        ├── loop.voss         # NEW (~30 LOC) — orchestration + ctx budget
        ├── router.voss       # NEW (~20 LOC) — probable<string> route
        ├── planner.voss      # NEW (~30 LOC) — probable<Plan> + gate
        ├── executor.voss     # NEW (~30 LOC) — sequential tool dispatch
        └── reviewer.voss     # NEW (~20 LOC) — final synthesis

tests/harness/
├── test_voss_loop_parity.py  # NEW (D-11) — single-fixture parity assertion
├── test_voss_check_dir.py    # NEW (D-05/D-07) — directory walk + diagnostic format
├── test_voss_compile_dir.py  # NEW — manifest + per-file artifacts
└── test_cache_freshness.py   # NEW (D-10) — StaleHarnessCacheError surface

tests/codegen/
├── test_use_alias.py         # NEW (Wave 0 sub-plan) — grammar/parser/codegen for use..as
└── test_await_use_import.py  # NEW (Wave 0 sub-plan) — auto-await on use-imported callee

.github/workflows/ci.yml      # MODIFY: add `python -m voss.cli check voss/harness/agent/` step

.voss-cache/harness/          # NEW (runtime artifact; gitignored)
├── loop.py
├── router.py
├── planner.py
├── executor.py
├── reviewer.py
└── _manifest.json
```

### Pattern 1: Compiler-gap sub-plan (Wave 0)

**What:** Two narrow extensions that MUST land before any `.voss` file authoring task.

**1a — grammar: `use ... as alias`**

Source: `voss/grammar.lark:174-175`:
```lark
use_stmt: "use" use_path
use_path: IDENT ("::" IDENT)*
```
Replace with:
```lark
use_stmt: "use" use_path ("as" IDENT)?
use_path: IDENT ("::" IDENT)*
```
Parser side: `voss/parser.py:714-715` currently:
```python
def use_stmt(self, meta, children):
    return UseStmt(span=_span(meta, self.file), path=children[0], alias=None)
```
Replace `alias=None` with logic to pick up the second child when present:
```python
def use_stmt(self, meta, children):
    path = children[0]
    alias = None
    if len(children) > 1 and children[1] is not None:
        alias = str(children[1])
    return UseStmt(span=_span(meta, self.file), path=path, alias=alias)
```
AST already supports `UseStmt.alias`. Codegen already supports it at `voss/codegen.py:142-148`. Tests at `tests/codegen/test_imports.py:56-60` already verify `test_use_stmt_alias_is_preserved_when_ast_provides_alias` — only the parser→AST link is broken. Add `tests/parser/test_use_alias.py` with a small case.

**1b — codegen: auto-await for `use`-imported callees**

Source: `voss/codegen.py:441-446` (await is emitted only for `generated_fns`):
```python
text = f"{callee_text}({', '.join(arg_texts)})"
if (
    await_context
    and isinstance(call.callee, Identifier)
    and call.callee.name in self.generated_fns
):
    text = f"await {text}"
```
The harness symbols imported via `use voss::harness::run_turn` and `use voss::harness::tools::ToolEntry` are async (run_turn is `async def`; `ToolEntry.invoke` returns a coroutine because `func` is async). The cleanest extension is to track imported names on the `ExpressionEmitter` (where `generated_fns` already lives at codegen.py:349), populate it from `ProgramEmitter.emit` at codegen.py:1175-1176 (`if isinstance(stmt, UseStmt): self.imports.add_use(stmt.path, alias=stmt.alias)` — there's a natural place to ALSO collect a name set), and extend the await condition to:
```python
if (
    await_context
    and isinstance(call.callee, Identifier)
    and (call.callee.name in self.generated_fns
         or call.callee.name in self.use_imported_names)
):
    text = f"await {text}"
```
Aliased imports (`use ... as h`) need a slightly different shape — `h.something(...)` is a `Member` callee, not `Identifier`. **For M4, recommend skipping aliased member-call auto-await and using NAME imports only:** `use voss::harness::run_turn` (so `.voss` writes `run_turn(...)` not `h.run_turn(...)`). Then the auto-await fires on bare-identifier calls just like generated fns. This restricts the M4 surface to a single ~5-line codegen change and lets the `as` clause (1a) be a smaller, narrower add for cosmetic aliasing.

**When to use:** This sub-plan MUST land before any `.voss` file ships. Without 1b, executor.voss cannot call `tool.invoke(...)`; without 1a, the `use voss.harness as h` strawman in CONTEXT D-02 cannot compile (but the `use voss::harness::name` form CAN with only 1b).

**Source citations for the grammar extension:** `voss/grammar.lark:174-175`, `voss/parser.py:711-715`, `voss/codegen.py:126-148`, `tests/codegen/test_imports.py:56-60`.

---

### Pattern 2: The `.voss` file shapes (DOG-01..DOG-05)

**Source:** Pseudo-`.voss` block already living in `voss/harness/agent.py:114-125` is the design target:
```python
"""
ctx(budget: token_budget) {
    let plan: probable<Plan> = ask(...)
    if plan @ p >= threshold {
        for step in plan.steps: tool.invoke(step)
        yield review(results)
    } else {
        yield clarify(plan.open_question)
    }
}
"""
```

**`voss/harness/agent/loop.voss`** (~30 LOC, target shape — illustrative; exact tokens must match grammar):
```voss
# loop.voss
# Demonstrates: ctx(budget: N tokens), control flow, try/catch, fallback.
# Calls into router/planner/executor/reviewer for one agent turn.
use voss::harness::agent::TurnResult
use voss::harness::tools::ToolEntry
use voss::harness::permissions::PermissionGate

fn run_turn(
    task: string,
    tools: dict<string, ToolEntry>,
    cwd: string,
    renderer: any,
    confidence_threshold: float = 0.60,
    token_budget: int = 60000,
    model: string = null,
    provider: any = null,
    history: any = null,
    permissions: PermissionGate = null,
) -> TurnResult {
    ctx(budget: 60000 tokens) {
        let route = route_intent(task)
        let plan_result = plan_task(task, tools, route, provider, model)
        if plan_result @ p >= confidence_threshold {
            let results = execute_steps(plan_result.value, tools, permissions, renderer)
            return review(plan_result.value, results, history, task)
        } else {
            return clarify(plan_result.value, renderer)
        }
    }
}
```

**`voss/harness/agent/router.voss`** (~20 LOC):
```voss
# router.voss
# Demonstrates: probable<string> for intent classification.
fn route_intent(task: string) -> string {
    let intent: probable<string> = ask("Is this a slash command or natural-language task? " + task)
    if intent @ p >= 0.80 {
        return intent.value
    } else {
        return "natural"
    }
}
```

**`voss/harness/agent/planner.voss`** (~30 LOC):
```voss
# planner.voss
# Demonstrates: probable<Plan>, confidence gate, ask-with-schema.
use voss::harness::agent::Plan
fn plan_task(task: string, tools: any, route: string, provider: any, model: string) -> probable<Plan> {
    let plan: probable<Plan> = ask("Task: " + task)
    return plan
}
```

**`voss/harness/agent/executor.voss`** (~30 LOC):
```voss
# executor.voss
# Demonstrates: sequential tool dispatch via Python ToolEntry.invoke (auto-await).
fn execute_steps(plan: any, tools: any, permissions: any, renderer: any) -> list<string> {
    # Tool iteration — calls into Python tool.invoke, which requires
    # the Wave 0 auto-await codegen extension (Pattern 1b).
    # ... (loop over plan.steps; call tools[step.name].invoke(**step.args))
}
```

**`voss/harness/agent/reviewer.voss`** (~20 LOC):
```voss
# reviewer.voss
# Demonstrates: try/catch and final synthesis from results.
fn review(plan: any, results: list<string>, history: any, task: string) -> any {
    try {
        # substitute {{step_N}} placeholders, append history, return TurnResult
    } catch e {
        # surface failure gracefully
    }
}
```

**Important caveats** the planner MUST resolve at plan time, by reading the codegen behavior:
- `dict<string, ToolEntry>` parses fine (`voss/grammar.lark:17-22` `type_expr` with generics). `list<string>` is the existing pattern from `samples/research.voss:31`.
- **`.voss` does not have a `for` loop today.** Grammar `stmt` (grammar.lark:88-98) covers `let / if / match / ctx / within / try / return / yield / include / match_threshold / expr_stmt` — no `for`. The executor loop must be written as `.map(...)` or as recursive calls, OR the `for` construct is itself a sub-plan (NOT recommended for M4 — see Open Question Q-3). Recommendation: use the `.map(lambda)` lowering (codegen.py:463-472 already supports `member.map(lambda)` → list comprehension) and have executor.voss return `plan.steps.map(s => tools[s.name].invoke(**s.args))`. This is awkward (`.map` lowers to a synchronous list comp; coroutines would be created but not awaited inside the comp) — see Open Question Q-3 for the cleanest resolution.
- **There is no `**kwargs` spread in `.voss`.** Tool args are `dict[str, Any]`; calling Python `tool.invoke(**step.args)` is not a syntax `.voss` supports. The cleanest workaround: have the Python `ToolEntry` expose an `invoke_dict(args: dict)` method on the Python side, and `.voss` calls it as `tool.invoke_dict(step.args)`. This is a one-line addition to `voss/harness/tools.py:ToolEntry`. Recommend.

### Pattern 3: `voss check <dir>` + `voss compile <dir>` (D-05/D-07)

**Analog:** Existing `_compile_source` (voss/cli.py:75-118) and `check` (voss/cli.py:209-228) are per-file. The dir-walking branch wraps them.

**Helper to add** (`voss/cli.py`, top of file or in a small helper):
```python
def _walk_voss_sources(source: Path) -> list[Path]:
    """Return [source] if file, else sorted([p for p in source.rglob('*.voss')])."""
    if source.is_file():
        return [source]
    if source.is_dir():
        return sorted(source.rglob("*.voss"))
    raise click.ClickException(f"not a file or directory: {source}")
```

**`check` extension** (replace the single-file body at voss/cli.py:209-228):
```python
def check(source, warnings_as_errors, cache_dir, project_root):
    files = _walk_voss_sources(source)
    error_count = 0
    warning_count = 0
    for f in files:
        program = _parse_file(f)
        try:
            result = analyze(program, source_path=str(f), project_root=project_root,
                             cache_dir=cache_dir, emit_indexes=False)
        except VossError as exc:
            raise click.ClickException(str(exc))
        _print_diagnostics(result.diagnostics)  # already file:line:col format per voss/diagnostics.py
        error_count += len(result.errors)
        warning_count += len(result.warnings)
    if len(files) > 1:
        click.echo(f"{error_count} errors, {warning_count} warnings across {len(files)} files")
    if error_count > 0:
        raise click.exceptions.Exit(code=1)
    if warnings_as_errors and warning_count > 0:
        raise click.exceptions.Exit(code=1)
```

**Diagnostic format (D-07):** Each `Diagnostic` already renders as `<file>:<line>:<col>: <severity> <message>` per the existing `_print_diagnostics(result.diagnostics)` path (voss/cli.py:40-42 + `str(diag)`). Per-file grouping is implicit because we iterate files. Summary line appended only when N > 1.

**`compile` extension** (voss/cli.py:147-167): identical wrapper around `_compile_source`. Output paths must be inside `.voss-cache/harness/` (per D-13) — `_compile_source`'s `output_path` arg supports this; the wrapper computes `output_path = cache_root / "harness" / f.with_suffix('.py').name` for each file. Also pass through the manifest writer (Pattern 4) after the loop.

**Single-file behavior:** unchanged — when `source.is_file()`, the loop runs once and the summary line is suppressed.

### Pattern 4: Cache writer + manifest (DOG-08, D-13/D-14/D-15)

**`voss/harness/sandbox.py` extension** (~15 LOC):
```python
def write_cache(project_root: Path, relpath: str | os.PathLike, text: str) -> Path:
    """Write text to project_root/.voss-cache/<relpath> atomically; jail enforced.

    relpath must be relative; jail_path() prevents escape from .voss-cache.
    """
    cache_root = jail_path(project_root, ".voss-cache")  # ensures .voss-cache inside project_root
    target = jail_path(cache_root, relpath)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write — mirror voss/cli.py:56-72 _write_text_atomic pattern.
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(target)
    return target
```
Calls into `jail_path` which already exists at `voss/harness/sandbox.py:20-31`.

**`voss/harness/cache.py` (NEW, ~80 LOC):**
```python
"""Compiled-harness cache helpers.

D-13: per-file artifacts under .voss-cache/harness/{name}.py + _manifest.json.
D-14: cache key = source sha256 + voss_version.
D-15: writes route through voss.harness.sandbox.write_cache (jailed atomic write).
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from voss import __version__ as VOSS_VERSION
from .sandbox import write_cache

HARNESS_AGENT_DIR = "voss/harness/agent"  # relative to project_root
CACHE_HARNESS_DIR = ".voss-cache/harness"
MANIFEST_NAME = "_manifest.json"
MANIFEST_VERSION = 1


@dataclass(frozen=True)
class ManifestEntry:
    sha256: str
    lines: int


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_source_shas(project_root: Path) -> dict[str, ManifestEntry]:
    src_dir = project_root / HARNESS_AGENT_DIR
    out: dict[str, ManifestEntry] = {}
    for p in sorted(src_dir.glob("*.voss")):
        text = p.read_text()
        out[p.name] = ManifestEntry(sha256=sha256_text(text), lines=text.count("\n") + 1)
    return out


def write_manifest(project_root: Path, entries: dict[str, ManifestEntry]) -> Path:
    payload = {
        "version": MANIFEST_VERSION,
        "voss_version": VOSS_VERSION,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "sources": {name: {"sha256": e.sha256, "lines": e.lines} for name, e in entries.items()},
    }
    return write_cache(project_root, f"{CACHE_HARNESS_DIR}/{MANIFEST_NAME}",
                       json.dumps(payload, indent=2) + "\n")


def load_manifest(project_root: Path) -> dict | None:
    path = project_root / CACHE_HARNESS_DIR / MANIFEST_NAME
    if not path.exists():
        return None
    return json.loads(path.read_text())


def assert_fresh(project_root: Path) -> None:
    """Raise StaleHarnessCacheError if cache is missing or any source sha mismatches."""
    from .diagnostics import StaleHarnessCacheError
    manifest = load_manifest(project_root)
    if manifest is None:
        raise StaleHarnessCacheError(
            "compiled harness cache missing — run: voss compile voss/harness/agent/"
        )
    if manifest.get("voss_version") != VOSS_VERSION:
        raise StaleHarnessCacheError(
            f"compiled harness cache stale (voss version mismatch: "
            f"manifest={manifest.get('voss_version')}, runtime={VOSS_VERSION}) — "
            "run: voss compile voss/harness/agent/"
        )
    current = compute_source_shas(project_root)
    for name, entry in current.items():
        record = manifest.get("sources", {}).get(name, {})
        if record.get("sha256") != entry.sha256:
            raise StaleHarnessCacheError(
                f"compiled harness cache stale ({name} sha mismatch) — "
                "run: voss compile voss/harness/agent/"
            )
```

**Cite-pattern:** sha computation mirrors `voss/harness/cognition.py:298` (sha1 for repo.idx). We bump to sha256 per D-14. JSON shape mirrors `voss/harness/cognition.py:repo.idx` (cognition.py:310 returns `{"version": 1, "git_head": ..., "files": [...]}`). Atomic write mirrors `voss/cli.py:56-72`.

### Pattern 5: Boot-path dispatch (DOG-07, D-08)

**Analog:** Existing `_resolve_auth_or_die(preference)` (voss/harness/cli.py:108-147) is the canonical "resolve before run" pattern.

**New helper** in `voss/harness/cli.py` (place near `_resolve_auth_or_die`):
```python
def _resolve_run_turn():
    """Pick the run_turn callable based on VOSS_HARNESS env > config.toml > default.

    Returns the callable; raises StaleHarnessCacheError if compiled is requested
    but cache is stale (D-10). No silent fallback.
    """
    from . import config as harness_config
    backend = (
        os.environ.get("VOSS_HARNESS")
        or harness_config.load_harness_config().get("backend")
        or "python"
    )
    if backend not in ("python", "compiled"):
        raise click.ClickException(
            f"invalid VOSS_HARNESS={backend!r}: expected 'python' or 'compiled'"
        )
    if backend == "python":
        from .agent import run_turn  # parity oracle (D-09)
        return run_turn

    # backend == "compiled" (D-07)
    from . import cache as harness_cache
    cwd = Path.cwd()  # NOTE: must match the project_root used at compile time.
    harness_cache.assert_fresh(cwd)
    # Dynamic import from .voss-cache/harness/loop.py.
    import importlib.util
    loop_py = cwd / harness_cache.CACHE_HARNESS_DIR / "loop.py"
    spec = importlib.util.spec_from_file_location(
        "voss_compiled_harness_loop", loop_py
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_turn
```

**Call site:** `do_cmd` at voss/harness/cli.py:196-246, `chat_cmd` at :271-292 — currently `from .agent import run_turn` at module top (voss/harness/cli.py:23). Replace with a call inside each command:
```python
run_turn = _resolve_run_turn()
result = asyncio.run(run_turn(text, tools=tools, cwd=cwd, renderer=renderer, ...))
```
Plus drop the module-top `from .agent import run_turn` to avoid eager Python-backend wiring (or keep it as a fallback alias for in-process callers like `_run_repl`).

**`config.toml` shape:** Already used by `voss/harness/config.py:load_harness_config` (cli.py:42-56). Add a `backend` key under `[harness]`:
```toml
[harness]
preferred_model = "claude-opus"   # existing
backend = "compiled"              # NEW (D-08)
```
`voss/harness/config.py:56` already writes via `p.write_text(new_text)`. No new file or schema work.

### Pattern 6: Parity test fixture (D-11)

**Analog:** `tests/harness/test_agent_integration.py:21-50` (`FakeProvider` + canned `Plan`).

```python
# tests/harness/test_voss_loop_parity.py
"""M4 D-11: same fixture, two backends, identical TurnResult.final + tool sequence."""
from __future__ import annotations
import asyncio
import os
from pathlib import Path
import pytest

from voss.harness.agent import Plan, ToolCall, TurnResult
from voss.harness.permissions import PermissionGate
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "fixture.md").write_text("noop fixture body\n")
    return tmp_path


# Reuse FakeProvider from test_agent_integration.py (or copy the class inline
# for isolation — the M3 hermetic stub policy says no live providers in CI).
class FakeProvider:
    def __init__(self, plan: Plan): self.plan = plan; self.calls = []
    async def complete(self, *, messages, model, response_format=None, **_):
        from voss_runtime.providers.base import ProviderResponse
        self.calls.append({"model": model, "messages": messages})
        return ProviderResponse(
            text=self.plan.model_dump_json(),
            model=model, prompt_tokens=10, completion_tokens=10,
            cost_usd=0.0, raw={"fake": True},
            parsed=self.plan if response_format is Plan else None,
        )
    def count_tokens(self, *, text, model): return 1


def _fixture_plan() -> Plan:
    return Plan(
        rationale="read the noop fixture",
        steps=[ToolCall(name="fs_read", args={"path": "fixture.md"})],
        confidence=0.95,
        final_when_done="contents: {{step_0}}",
    )


def _run(project: Path, run_turn):
    return asyncio.run(run_turn(
        "noop summary of fixture.md",
        tools=make_toolset(project),
        cwd=project,
        renderer=PlainRenderer(),
        provider=FakeProvider(_fixture_plan()),
        permissions=PermissionGate(auto_yes=True),
    ))


def test_python_and_compiled_backends_agree(project: Path):
    """D-11: same task, same Plan, same tool sequence, same final."""
    from voss.harness.agent import run_turn as python_run_turn

    # Compiled backend: must have been compiled by Wave 1 plan.
    # If .voss-cache/harness/loop.py is missing, assert_fresh raises
    # StaleHarnessCacheError — test should pre-compile in a fixture.
    from voss.harness import cache as harness_cache
    harness_cache.assert_fresh(project)  # asserts cache is fresh OR raises
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "voss_compiled_harness_loop_test",
        project / harness_cache.CACHE_HARNESS_DIR / "loop.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    compiled_run_turn = mod.run_turn

    py_result = _run(project, python_run_turn)
    voss_result = _run(project, compiled_run_turn)

    assert py_result.final == voss_result.final
    assert [s.name for s in py_result.plan.steps] == [s.name for s in voss_result.plan.steps]
    assert [s.args for s in py_result.plan.steps] == [s.args for s in voss_result.plan.steps]
```

The fixture pre-compile step happens in a session-scoped fixture that runs `voss compile voss/harness/agent/ --project-root=<tmp_path>` once before the parity test. Mirror `tests/examples/helpers.py:run_voss(...)` (per M3-RESEARCH).

### Anti-Patterns to Avoid

- **Inlining the compiler gap fix into a `.voss` file plan.** The grammar/codegen extension is a Wave 0 sub-plan. Mixing compiler work into the same plan that authors `loop.voss` makes the diff unreviewable and couples failure modes. Keep them separate.
- **Silent fallback to Python when cache is stale.** D-10 mandates loud failure. Implementing "if stale, just use the parity oracle" would mask exactly the regressions M4 exists to expose. Mirror M1 D-13 diagnose-don't-fix.
- **Authoring `.voss` files BEFORE the compiler sub-plan lands.** If executor.voss exists and the compiler can't generate `await tool.invoke(...)`, `voss compile voss/harness/agent/` succeeds but the generated Python deadlocks at first tool call (or returns a coroutine instead of a string). The Wave 0 sub-plan MUST land first.
- **Hand-rolling a `for` loop construct in `.voss` for executor.voss.** No `for` exists today; adding one is a real grammar/codegen expansion (loop body scope, break/continue, iteration protocol). The recommended workaround is `.map(lambda)` or recursion. See Open Question Q-3.
- **Using `**kwargs` spread in `.voss`.** Doesn't exist. Use a `ToolEntry.invoke_dict(args_dict)` Python-side helper instead.
- **Compiling into a hand-chosen directory other than `.voss-cache/harness/`.** Codegen's `_resolve_cache_root` at codegen.py:218-235 requires the cache root be named `.voss-cache` and live inside project_root. Anything else raises `CodegenError` — by design.
- **Reading `voss_runtime` from `.voss-cache/harness/*.py` differently than the parity oracle.** Both compiled and Python paths must end up using the same `voss_runtime.ContextScope`, same `voss_runtime.EpisodicMemory`, same `voss_runtime.StubProvider` — otherwise parity is meaningless. The generated files already import from `voss_runtime`; the parity oracle does too. No new runtime contract.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tool descriptor in `.voss` | Re-declare `@tool fn fs_read(...)` blocks in `.voss` | `use voss::harness::tools::ToolEntry`; executor.voss receives `tools` arg | D-04 explicit. Tool registry stays Python; `.voss` does not bypass permission gate. |
| Permission tier check | Inline `if mode == "plan" and is_mutating: ...` in executor.voss | `PermissionGate.check(name, args, is_mutating)` from `voss/harness/permissions.py:check` | M1 D-05 strict tier mapping. M4 D-04 keeps the gate 100% Python. |
| Plan/ToolCall schema | Define class Plan in `.voss` | `use voss::harness::agent::Plan` (after grammar extension OR use `from voss.harness.agent import Plan` in generated Python directly via use-stmt) | D-02 thin .voss. The pydantic v2 model at agent.py:35-56 already handles JSON-from-LLM correctly. |
| Episodic memory | Re-implement turn buffer in executor.voss | `EpisodicMemory` from `voss_runtime/memory/episodic.py` | Already public API; runtime contract is shared with samples. |
| Stub provider for parity test | Subclass `LiteLLMProvider` | `StubProvider` (already at `voss_runtime/providers/stub.py:8-74`) OR the in-file `FakeProvider` pattern at `tests/harness/test_agent_integration.py:21-50` | Existing tests use both shapes; pick whichever is shorter. Recommend the in-file `FakeProvider` for the parity test because it's already canned with a `Plan` object — exactly the M4 fixture shape. |
| Manifest writer | New `json.dump(..., open(...))` in a loop | The `compute_source_shas + write_manifest` helpers in `voss/harness/cache.py` (new module per Pattern 4) | Centralizes the sha256 + voss_version + ISO timestamp shape. Reusable for `voss doctor` cache-freshness check. |
| Sandboxed cache write | `Path.write_text(...)` from cli.py directly | `voss/harness/sandbox.write_cache(project_root, relpath, text)` | D-15 + M2 D-06. Cwd jail invariant must hold; `jail_path` already does the work. |
| `StaleHarnessCacheError` shape | Custom exception with custom message format | Subclass of `voss.exceptions.VossError` with a fixed message ending in `run: voss compile voss/harness/agent/` | D-10 mandates the exact suggestion text. Matches `voss/exceptions.py:VossError` pattern (1 line: `class StaleHarnessCacheError(VossError): pass`). |
| Directory walking | `glob.glob("**/*.voss", recursive=True)` | `Path.rglob("*.voss")` | Already used throughout (e.g., `voss/harness/cognition.py:289` walks `cwd.rglob("*")`). |
| Per-file diagnostic aggregation | New diagnostic-collector class | Per-file `_print_diagnostics(result.diagnostics)` calls + summary line | `Diagnostic.__str__` at voss/diagnostics.py already renders `<file>:<line>:<col>: <severity> <message>`; aggregation is just iteration + counting. |
| Auto-fallback `StubProvider` detection at compile time | Re-implement in M4 | Already shipped by M3 D-01 in `voss_runtime/providers/__init__.py:get()`; the parity test sets `VOSS_HERMETIC=1` to force it | Don't duplicate M3 wiring. The compiled `loop.py` reads from the same `voss_runtime.providers.get()` registry. |
| Configuration of `[harness] backend` | Custom config file | `voss/harness/config.py` already loads `[harness]` section (cli.py:42-56) | Add `backend` key alongside existing `preferred_model`. Same `load_harness_config()`. |

**Key insight:** Every M4 problem has an in-tree analog. The compiler-gap sub-plan (Pattern 1) is the ONLY new design surface. Everything else is mechanical extension.

## Runtime State Inventory

> M4 introduces compiled artifacts under `.voss-cache/harness/` — strict cache-write/read flow. Required to inventory.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `.voss-cache/harness/{loop,router,planner,executor,reviewer}.py` + `_manifest.json` are NEW artifacts written eagerly by `voss compile voss/harness/agent/`. The directory does not exist before M4 lands. **No legacy artifacts** from M1/M2/M3 conflict — M3 uses `.voss-cache/{stem}.idx` (analyzer manifest); M2 uses `.voss-cache/repo.idx`; both are flat-files, different names. | None blocking. `.gitignore` already includes `.voss-cache/` from M2 D-09 (see Pitfall 6 below — verify presence). |
| Live service config | None — Voss has no external services that register the compiled harness. The compiled `loop.py` is consumed in-process via `importlib.util.spec_from_file_location`. | None. |
| OS-registered state | None — no launchd, no Task Scheduler, no pm2, no systemd. | None. |
| Secrets / env vars | `VOSS_HARNESS` (NEW, M4 reads it). `VOSS_HERMETIC` (existing, M3 D-01) — parity test uses this to force StubProvider. `~/.config/voss/config.toml` `[harness] backend` (NEW, M4 reads it). No new secrets. | M4 must NOT log `VOSS_HARNESS` value into session JSON (M1 D-16 schema-allowlist redaction already prevents this since `SessionRecord` fields are fixed; env vars are not in the schema). |
| Build artifacts / installed packages | `voss.egg-info/` is unchanged. `pip install -e .` does not need re-running. **Stale Python `__pycache__`** under `voss/harness/agent/__pycache__/` could exist if a previous tree had Python files there; the M4 directory is `.voss` files only, but be aware. | Optional: `find voss/harness/agent -name __pycache__ -exec rm -rf {} +` in clean step. |

**Renames / string-replacements in this phase:** None. M4 adds content (5 .voss files, 1 new cache module, 1 new test file, ~50 LOC compiler diff). It does not rename existing symbols or move files.

**The canonical question:** *After the .voss files land and `voss compile voss/harness/agent/` runs, what runtime systems still have the old (Python-only) behavior cached?* — Answer: **The Python path itself, on purpose (D-09 parity oracle).** Anything else would be a regression. Old `__pycache__` directories may exist but auto-update because `*.py` mtimes change with edits. CI starts clean each run.

## Common Pitfalls

### Pitfall 1: `use voss.harness as h` (CONTEXT D-02 strawman) does not parse

**What goes wrong:** Implementer reads CONTEXT D-02 literally and writes `use voss.harness as h` at the top of `loop.voss`. Parser rejects: `use_path` rule (`voss/grammar.lark:175`) uses `::` separator (matches Rust/C++-style paths, not Python `.` paths). Additionally `voss/parser.py:711-715` `use_stmt` does NOT process an `as <alias>` clause — the grammar `use_stmt: "use" use_path` has no slot for it.

**Why it happens:** CONTEXT D-02 wording is shorthand; the actual token form was not resolved during the discuss phase. The same trap appeared in M3 (M3-RESEARCH §Pitfall 1) where `use voss.tools` was the strawman — M3 resolved by switching to `use voss_runtime::tools::tool`.

**How to avoid:** Two paths, ordered by minimum scope:

1. **NAME imports (preferred, no grammar work):** Use `use voss::harness::run_turn`, `use voss::harness::tools::ToolEntry`, etc. The compiler emits `from voss.harness import run_turn` and `from voss.harness.tools import ToolEntry` per `voss/codegen.py:142-148`. `.voss` references these as bare identifiers. **This works today, BUT requires the Wave 0 codegen auto-await sub-plan (Pattern 1b) because `run_turn` and `ToolEntry.invoke` are async and current codegen does not auto-await imported names.**

2. **ALIASED module imports (cosmetic, needs grammar extension):** `use voss::harness as h` + call sites `h.run_turn(...)`. Requires Pattern 1a grammar+parser fix AND a different codegen extension to auto-await Member calls where `obj` is an aliased import — significantly more compiler surface than (1). Don't recommend for M4.

**Warning signs:** `voss check voss/harness/agent/loop.voss` exits non-zero with parse error pointing at the `.` after `voss` or at the `as` token.

### Pitfall 2: Compiled executor.voss returns a coroutine instead of running tools

**What goes wrong:** Without the Wave 0 codegen auto-await sub-plan (Pattern 1b), executor.voss compiles cleanly, `voss check` passes, `voss compile` writes the files, BUT at runtime `tool.invoke(...)` returns a coroutine object that is never awaited. Tool results are `<coroutine object fs_read at 0x...>`. Final answer placeholder substitution `{{step_0}}` shows the coroutine repr.

**Why it happens:** `voss/codegen.py:441-446` auto-await condition fires only for `Identifier` callees in `generated_fns`. `use`-imported callees and member-calls don't qualify.

**How to avoid:** The Wave 0 sub-plan MUST land before `.voss` file authoring plans. Sentinel test in `tests/codegen/test_await_use_import.py`:
```python
def test_use_imported_async_fn_is_awaited():
    """voss_runtime: a use-imported name is awaited when called inside async context."""
    # ... build AST with UseStmt(path=("foo","bar")) + FnDecl that calls bar()
    # ... assert "await bar()" in generated source
```
Plus a runtime regression: `tests/harness/test_voss_loop_parity.py` (Pattern 6) fails loudly if executor returns coroutine objects rather than result strings.

**Warning signs:** Parity test fails with `assert "coroutine object" not in voss_result.final`; tool_results list contains coroutine repr; pytest emits `RuntimeWarning: coroutine 'fs_read' was never awaited`.

### Pitfall 3: `voss compile voss/harness/agent/` writes outside `.voss-cache`

**What goes wrong:** Implementer extends `_compile_source` for dir-mode but forgets to thread `output_path = cache_root / "harness" / f.with_suffix('.py').name` through the loop. Default behavior at `voss/cli.py:52-53` (`_default_output_path`) is `input_path.with_suffix(".py")` — i.e. `voss/harness/agent/loop.py` would be written **next to** the source, which (a) leaks generated Python into the source tree, (b) fights the codegen jail at `voss/codegen.py:218-235` (cache must be named `.voss-cache`).

**Why it happens:** `_compile_source` is per-file; the dir-walking wrapper must explicitly compute the cache path.

**How to avoid:** The dir-walk wrapper in `voss/cli.py:compile` MUST set `output_path=cache_dir / "harness" / source_file.name.replace(".voss", ".py")` for each file. Mirror the codegen `_resolve_cache_root` invariant: output paths must end up inside `.voss-cache`. Test: `tests/harness/test_voss_compile_dir.py` asserts (a) no `.py` files appear inside `voss/harness/agent/`; (b) all five `.py` files appear inside `.voss-cache/harness/`.

**Warning signs:** `git status` shows untracked `voss/harness/agent/loop.py` after `voss compile`. CI fails because the source tree has unexpected `.py` files next to `.voss`.

### Pitfall 4: Stale cache silently used because `assert_fresh` is called too late

**What goes wrong:** `_resolve_run_turn()` (Pattern 5) imports the cached `loop.py` first and only checks `assert_fresh()` afterward. If the cached `loop.py` has stale `from voss.harness import X` lines but the live `voss/harness/agent.py:Plan` schema changed since the last compile, the import succeeds (Python's import doesn't reject schema-incompatible callers) but `run_turn` later fails with a confusing `ValidationError`.

**Why it happens:** Easy to put `importlib.util.spec_from_file_location(...)` before `assert_fresh(cwd)` because importing feels like a prerequisite for "checking".

**How to avoid:** Pattern 5 already orders correctly — `harness_cache.assert_fresh(cwd)` is called BEFORE the dynamic import. Add a sentinel test: `tests/harness/test_cache_freshness.py::test_stale_cache_raises_before_import` patches one source file's content (`(project/"voss/harness/agent/loop.voss").write_text("...changed...")`) and asserts that `_resolve_run_turn()` raises `StaleHarnessCacheError` without ever importing the stale `loop.py`.

**Warning signs:** Mysterious pydantic ValidationErrors mid-turn; mismatched function signatures; debug logs show `loop.py` imported even when stale.

### Pitfall 5: `.voss-cache/` not in `.gitignore` — generated files committed

**What goes wrong:** Developer runs `voss compile voss/harness/agent/`, commits `.voss-cache/harness/*.py`, and now the repo has both source-of-truth `.voss` and stale generated Python. CI starts using committed files instead of fresh ones.

**Why it happens:** M2 D-09 specifies `.gitignore` adds `.voss-cache/` — but verify it's present. The repo root `.gitignore` IS the place; per M2-CONTEXT this was a hand-write or `cognition.append_gitignore_line_idempotent` call.

**How to avoid:** Pre-flight check in the M4 plan: read `.gitignore` and confirm `.voss-cache/` is present. If absent, add it as part of the cache-writer task. Sentinel test: `tests/harness/test_voss_compile_dir.py::test_voss_cache_ignored` runs `git check-ignore .voss-cache/harness/loop.py` and asserts exit 0.

**Warning signs:** `git status` shows `.voss-cache/harness/loop.py` as untracked. CI uses old artifacts because they were committed at some point.

### Pitfall 6: Parity test passes locally because dev has Anthropic key, fails CI because StubProvider used

**What goes wrong:** Developer runs the parity test locally; it passes because both backends use the live provider and return identical answers. CI runs the same test with no keys, both backends fall back to `StubProvider`, but the `Plan` shape returned by `StubProvider` differs between paths because the compiled side has different prompt structure.

**Why it happens:** The compiled `loop.py` may construct the user prompt slightly differently than the Python `run_turn` (different whitespace, different field ordering in tools list). `StubProvider.fingerprint(messages)` (stub.py:30) is a `sha256` of the messages — divergent prompts → divergent fingerprints → divergent responses.

**How to avoid:** Parity test MUST register an explicit `FakeProvider` returning a fixed `Plan` (not rely on `StubProvider` fingerprint lookup). Pattern 6 above uses `FakeProvider(_fixture_plan())` exactly to avoid this trap — the same Plan is forced into both backends regardless of prompt-fingerprint differences. M3 D-12 raw-Python parity used the same pattern.

**Warning signs:** Parity test passes locally, fails CI. Test asserts on `tool_results` equality but the underlying issue is `plan.steps` differ.

### Pitfall 7: `voss/cli.py:check` `emit_indexes=False` is shared but the dir-walk overrides it

**What goes wrong:** When the new dir-walk in `voss/cli.py:check` iterates files, an implementer might paste the body from `_compile_source` (which uses `emit_indexes=True`) instead of `check`'s own (which uses `emit_indexes=False`). This re-introduces the M3 D-03 violation: each `voss check voss/harness/agent/*.voss` triggers a HF encoder load (~13s per file × 5 files = ~65s CI wall-clock).

**Why it happens:** Copy-paste error. The two CLI commands look similar but `check` has the static-only invariant (M3 D-03).

**How to avoid:** The new `check` dir-walk (Pattern 3) MUST keep `emit_indexes=False` in the analyze call. Add a regression test `tests/harness/test_voss_check_dir.py::test_check_dir_does_not_load_hf_encoder` mirroring M3's `tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder`:
```python
def test_check_dir_does_not_load_hf_encoder():
    # Run voss check voss/harness/agent/ in-process or subprocess
    # Then assert "sentence_transformers" not in sys.modules
```
Plus a speed gate: `voss check voss/harness/agent/` total wall-clock < 5s on a stock worker.

**Warning signs:** CI step `voss check voss/harness/agent/` runs >10s. Total CI time bumps by ~minute. `sys.modules` after the check call contains `sentence_transformers`.

### Pitfall 8: Compiled `loop.py` uses a different `EpisodicMemory` than Python `run_turn`

**What goes wrong:** Compiled `loop.py` does `from voss_runtime import EpisodicMemory` (codegen.py:152-154 auto-adds runtime imports). The Python `run_turn` at `voss/harness/agent.py:19` also does `from voss_runtime import EpisodicMemory`. **Both backends use the same class.** OK — but if a future M5 change moves `EpisodicMemory` to `voss/harness/memory.py`, compiled vs Python paths could diverge.

**Why it happens:** Implicit shared runtime is fine today; the trap is future-proofing.

**How to avoid:** Document in `voss/harness/agent/loop.voss` header (or in `M4-PATTERNS.md` analog) that `EpisodicMemory`/`ContextScope`/`PermissionGate` are imported from the SAME sources as the parity oracle. Add an assertion in the parity test: `assert py_result.history.__class__ is voss_result.history.__class__`.

**Warning signs:** Future tests fail with `<class 'voss_runtime.memory.EpisodicMemory'> != <class 'voss.harness.memory.EpisodicMemory'>`.

## Code Examples

### Pattern: Grammar extension for `use ... as alias` (Wave 0 sub-plan, Pattern 1a)

```lark
# voss/grammar.lark — line 174-175 before:
use_stmt: "use" use_path
use_path: IDENT ("::" IDENT)*

# After (D-02 strawman support):
use_stmt: "use" use_path ("as" IDENT)?
use_path: IDENT ("::" IDENT)*
```

```python
# voss/parser.py — replace lines 714-715 use_stmt method:
def use_stmt(self, meta, children):
    path = children[0]
    alias = None
    if len(children) > 1 and children[1] is not None:
        alias = str(children[1])
    return UseStmt(span=_span(meta, self.file), path=path, alias=alias)
```

```python
# tests/parser/test_use_alias.py (NEW)
def test_use_with_alias_parses():
    program = parse("use foo::bar as baz\n", file="<test>")
    use = program.body[0]
    assert isinstance(use, UseStmt)
    assert use.path == ("foo", "bar")
    assert use.alias == "baz"


def test_use_without_alias_still_works():
    program = parse("use foo::bar\n", file="<test>")
    use = program.body[0]
    assert use.alias is None
```
Codegen test exists already at `tests/codegen/test_imports.py:56-60`.

### Pattern: Codegen auto-await for `use`-imported callees (Wave 0 sub-plan, Pattern 1b)

```python
# voss/codegen.py — ExpressionEmitter, after generated_fns field at line 349:
@dataclass
class ExpressionEmitter:
    ...
    generated_fns: frozenset[str] = field(default_factory=frozenset)
    use_imported_names: frozenset[str] = field(default_factory=frozenset)  # NEW
    ...
```

```python
# voss/codegen.py — replace lines 441-446 in _emit_call:
if (
    await_context
    and isinstance(call.callee, Identifier)
    and (
        call.callee.name in self.generated_fns
        or call.callee.name in self.use_imported_names  # NEW
    )
):
    text = f"await {text}"
```

```python
# voss/codegen.py — in ProgramEmitter.emit (around line 1196-1197):
expr_emitter = ExpressionEmitter(
    self.imports,
    generated_fns=fn_names,
    use_imported_names=frozenset(
        stmt.alias or stmt.path[-1]  # imported as last segment OR alias
        for stmt in self.program.body
        if isinstance(stmt, UseStmt)
    ),
)
```

```python
# tests/codegen/test_await_use_import.py (NEW)
def test_use_imported_name_is_awaited_in_async_context():
    # Build AST: use foo::bar; fn caller() { bar() }
    use = UseStmt(span=span(), path=("foo", "bar"))
    body_call = ExprStmt(span=span(), expr=Call(callee=Identifier(span=span(), name="bar"), args=()))
    fn = FnDecl(span=span(), name="caller", params=(), return_type=None,
                body=(body_call,), decorators=())
    program = Program(span=span(), body=(use, fn))
    result = generate_python(program, analysis=_ok_analysis())
    assert "await bar()" in result.source
```

### Pattern: Manifest writer + assert_fresh (Pattern 4 invocation)

```python
# voss/cli.py — extend compile() with dir-mode tail:
from voss.harness import cache as harness_cache

def compile(source, output, cache_dir, project_root, verbose):
    files = _walk_voss_sources(source)
    for f in files:
        target = (Path(cache_dir) / "harness" / f.with_suffix(".py").name) if source.is_dir() else output
        _compile_source(f, output_path=target, project_root=project_root,
                        cache_dir=cache_dir, verbose=verbose)
    if source.is_dir() and source.name == "agent":  # harness dir mode
        proj = Path(project_root or Path.cwd())
        entries = harness_cache.compute_source_shas(proj)
        harness_cache.write_manifest(proj, entries)
        if verbose:
            click.echo(f"wrote manifest with {len(entries)} sources")
```

### Pattern: CI gate insertion

```yaml
# .github/workflows/ci.yml — insert AFTER `pip install -e ".[dev]"` (line 25):
      - name: voss check harness sources (M4 DOG-06)
        run: python -m voss.cli check voss/harness/agent/
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `run_turn` is Python-only at `voss/harness/agent.py` | `run_turn` is implemented in `voss/harness/agent/loop.voss` (compiled), with the Python file kept as parity oracle | M4 (DOG-01..05) | Dogfood: the harness's hottest loop is the first real `.voss` program. Regressions become language regressions. |
| `voss check <file>` only | `voss check <file_or_dir>` recursive | M4 D-05 | CI gate `voss check voss/harness/agent/` becomes possible (DOG-06). Single-file behavior unchanged. |
| Eager Python imports of `run_turn` in `voss/harness/cli.py:23` | Dispatched via `_resolve_run_turn(env, config)` | M4 D-08 | Single seam swaps backend by env-var / config. No silent fallback. |
| No language-level harness cache | `.voss-cache/harness/{name}.py + _manifest.json` per-file | M4 DOG-08 | Per-file regression isolation; sha256+voss_version key makes cross-branch reuse safe. |
| No `as` aliasing in `use` statements | `use voss::harness as h` parses (Wave 0 sub-plan) | M4 Pattern 1a | Cosmetic naming control for imports; non-blocking (NAME imports work without it). |
| Codegen auto-awaits only `generated_fns` callees | Codegen also auto-awaits `use`-imported callees | M4 Pattern 1b | **Required** for executor.voss to call back into Python tools. ~5-line condition extension. |

**Deprecated / outdated (do not chase):**
- The "Phase H3 ports it to .voss" comment at `voss/harness/agent.py:1-7` — H3 was the legacy phase number; M4 is the current owner.
- The pseudo-`.voss` block at `voss/harness/agent.py:114-125` — that comment WAS the design target; M4 ships it as real `.voss`. The Python file body is now the parity oracle, but the block-comment can be deleted/updated to point at the new `.voss` files.
- `voss/harness/sandbox.py`'s 49-LOC scope — M4 extends it minimally with `write_cache(...)`. M2-CONTEXT D-06 anticipated this; it just wasn't implemented in M2.
- The legacy "Harness can remain Python-authored in M1" framing (M1-CONTEXT) — M4 retires it for `run_turn` only; the rest stays Python per D-02.

## Assumptions Log

> All factual claims about parser/grammar/codegen/runtime behavior were verified by reading source at the cited file:line locations. Compiler-gap claims (Pitfall 1, Pitfall 2) verified by reading the relevant rules in grammar.lark and the _emit_call logic in codegen.py. No claims are based on training-data knowledge of `.voss` (which would be unreliable — `.voss` is a project-internal language).

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The codegen auto-await extension (Pattern 1b) is ~20 LOC and stays inside the compiler. | Summary, Pattern 1 | If the codegen change ripples into `ExpressionEmitter`'s broader caller surface (e.g., type-system implications), the sub-plan grows. The extension is isolated to one condition expansion + one constructor parameter — risk is small but real. [ASSUMED] — verified by reading codegen.py:349, 441-446, 1196-1197 but not by writing the patch. |
| A2 | `.voss` has no `for` loop and no `**kwargs` spread; executor.voss must use `.map(lambda)` or recursion + a `ToolEntry.invoke_dict(args_dict)` Python-side helper. | Pattern 2, Open Question Q-3 | If `.voss` users find `.map(...)` awkward and lobby for a `for` construct, M4 could overflow. The recommendation is to stay within current grammar; the `for` loop is a future-phase decision. [VERIFIED: grammar.lark:88-98 stmt rules, codegen.py:463-472 map handling]. |
| A3 | Subprocess inheritance of `VOSS_HARNESS` / `VOSS_HERMETIC` works transparently because Python's `subprocess.run` inherits parent env by default at `voss/cli.py:192-196`. | Section "VOSS_HARNESS subprocess inheritance" | Only relevant for `voss run` (which subprocs the generated Python); the harness `voss do` and the parity test run in-process. So this is a non-issue for M4 specifically. [VERIFIED: voss/cli.py:192-196 — `subprocess.run` with no `env=` arg inherits.] |
| A4 | The Python harness `_run_repl` at `voss/harness/cli.py:360-489` does not need DOG-07 wiring — only `do_cmd` is in scope per CONTEXT (live-provider parity + chat/edit through compiled path is M5). | Pattern 5 | If user wants `voss chat` to also flip to compiled, M5 inherits. M4 success bar (D-12 (c)) is only `voss do`. [VERIFIED: CONTEXT M4 deferred ideas list.] |
| A5 | `StaleHarnessCacheError` should subclass `voss.exceptions.VossError` (the existing compiler-error base). | Pattern 4 | Alternative would be a new exception hierarchy under harness. `VossError` is reasonable — it's the existing single-base umbrella per `voss/exceptions.py:4`. [VERIFIED: voss/exceptions.py:1-22.] |
| A6 | The parity test fixture (Pattern 6) is best authored with an in-file `FakeProvider`, not `StubProvider`, because the parity contract is on Plan + tool sequence, not on prompt-fingerprint reproducibility. | Pattern 6, Pitfall 6 | If a test reviewer prefers `StubProvider`, it can be used by pre-registering the fingerprint for the exact compiled-side prompt — fragile. FakeProvider is the cleaner pattern; `tests/harness/test_agent_integration.py:21-50` is the in-repo precedent. [VERIFIED.] |

**Summary:** 6 entries. A1 is the only real assumption (the codegen patch sizes); all others are verified or are non-issues marked for documentation.

## Open Questions

1. **Q-1: Should the `use ... as` grammar extension land in M4 or be deferred?**
   - What we know: NAME imports (`use voss::harness::run_turn`) work today + Pattern 1b auto-await. ALIAS-style (`use voss::harness as h`) is a cosmetic nicety.
   - What's unclear: Whether dropping the alias clause makes `.voss` files less readable enough to justify the grammar work.
   - Recommendation: **Land the alias clause in Wave 0 anyway.** It's ~30 LOC of grammar+parser+1 test, and CONTEXT D-02 + Claude's Discretion section both anticipate it. Skipping leaves a known footgun for any future `.voss` that wants to import a module rather than names.

2. **Q-2: How does `executor.voss` iterate `plan.steps` without a `for` construct?**
   - What we know: `.voss` has `.map(lambda)` (codegen.py:463-472 lowers to list comp) and `match`/`case`. No `for`.
   - What's unclear: A list comprehension of `tools[s.name].invoke(**s.args)` would create coroutines without awaiting them (list comps don't auto-await elements). Pattern 1b extension would help only if the callee is a bare `Identifier`, which a list-comp inner expression isn't typically.
   - Recommendation: Add a Python-side helper `async def run_steps(plan_steps: list, tools: dict, permissions: ...) -> list[str]` to `voss/harness/agent.py` (next to the existing `run_turn`); executor.voss imports and calls it as `let results = run_steps(plan.steps, tools, permissions, renderer)`. **This is the smallest unblock**: the Python helper does the awaiting loop (existing logic at agent.py:184-207 lifted into a helper); `.voss` provides only the control-flow shell. Alternative: introduce a `for` construct (compiler work — out of scope for M4).

3. **Q-3: Where exactly does the env-var vs config.toml resolution live?**
   - What we know: `voss/harness/config.py:load_harness_config()` already reads `[harness]` section (cli.py:42-56 calls it for `preferred_model`).
   - What's unclear: Should `_resolve_run_turn` (Pattern 5) read env-var directly, or should `load_harness_config` itself return a merged dict?
   - Recommendation: Direct env-var read in `_resolve_run_turn` (mirrors `os.environ.get("VOSS_HERMETIC")` pattern). Config.toml read via existing `load_harness_config`. Two-step resolution is clearest at the call site.

4. **Q-4: Where does `voss compile voss/harness/agent/` get the project_root from when invoked from CI?**
   - What we know: `voss compile` has `--project-root` flag (voss/cli.py:151). Default is `None`, which `_resolve_cache_root` (codegen.py:218-235) treats as `Path.cwd()`.
   - What's unclear: For the CI gate `voss check voss/harness/agent/`, project_root is implicitly cwd of the GH Actions runner. For `voss compile`, manifest writer needs project_root explicitly to know where `.voss-cache/harness/` goes.
   - Recommendation: Default to `Path.cwd()` (matches existing behavior). Document in install one-liner `cd <project> && voss compile voss/harness/agent/`. No new flag.

5. **Q-5: Should the parity test pre-compile in a session fixture, or rely on a separate `pytest --voss-compile-harness` step before running?**
   - What we know: pytest fixtures can run subprocess steps in `conftest.py`. Pre-compiling once per test session is standard.
   - What's unclear: Whether to make compilation a tested artifact (run via a pytest fixture so it's exercised in CI) or a separate Makefile/CI step.
   - Recommendation: Session-scoped pytest fixture in `tests/harness/conftest.py` that runs `python -m voss.cli compile voss/harness/agent/ --project-root=<tmp_path>` once. This dual-purpose-tests the compile path too. CI calls `pytest` only; no separate compile step needed.

6. **Q-6: Should `voss/harness/agent.py` get a `run_turn_async_helpers` extraction so executor.voss can reuse the existing tool-loop logic?**
   - What we know: agent.py:184-207 is the tool-execution loop with permission gate + result aggregation + summarize. ~25 LOC, async.
   - What's unclear: Whether the planner authors executor.voss to re-express this in `.voss` (dogfood-maximalist) or to import it from Python (dogfood-pragmatist).
   - Recommendation: Per Q-2, lift the loop into a Python helper `_run_step_loop(plan_steps, tools, permissions, renderer) -> list[str]` and have executor.voss call it. This is exactly what D-04 anticipates ("`.voss` does not gain a privileged tool-call path"). Pure-`.voss` re-expression of the loop is a future hardening pass.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.13 (cwd venv) / 3.11+3.12 (CI matrix) | — |
| `lark` | Grammar extension (Pattern 1a) | ✓ | pinned >=1.1.9 (M3-RESEARCH cited) | — |
| `click` | CLI dir-walk + harness cmds | ✓ | pinned >=8.1.0 | — |
| `pydantic` | Plan/ToolCall/TurnResult shared between backends | ✓ | pinned >=2.6,<3.0 | — |
| `pytest` + `pytest-asyncio` | Parity test | ✓ | dev extras | — |
| `voss_runtime` (editable install) | Both backends consume it | ✓ | `voss.egg-info/` present | — |
| `voss compile voss/harness/agent/` artifact (`.voss-cache/harness/`) | Compiled-backend boot path | ✗ (until M4 runs) | n/a | `VOSS_HARNESS=python` (default) — Python parity oracle always works. |
| `git` | sha256 is on text, not git-head (D-14) — git not required for cache | n/a | n/a | n/a |
| Network | Parity test uses StubProvider / FakeProvider hermetically (M3 D-01) | n/a | n/a | StubProvider auto-fallback (M3 D-01). |
| HF `sentence-transformers` | None — `voss check voss/harness/agent/` is static-only (M3 D-03); harness samples have NO `match similar(...)` constructs | n/a | n/a | n/a |

**Missing dependencies with no fallback:** None blocking M4 itself. The compiled cache is the deliverable, not a prereq.

**Missing dependencies with fallback:** The compiled cache (auto-fallback to Python via D-08 default).

## Validation Architecture

> Workflow `nyquist_validation: true` (`.planning/config.json:19`); section required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x (auto mode) [VERIFIED via M3-RESEARCH; pyproject.toml:25-26, 39-46] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (M3-RESEARCH §Validation Architecture) |
| Quick run command | `pytest tests/harness/test_voss_loop_parity.py tests/harness/test_voss_check_dir.py tests/harness/test_voss_compile_dir.py tests/harness/test_cache_freshness.py -q` |
| Per-test run | `pytest tests/harness/test_voss_loop_parity.py -q` |
| Full M4 suite | `pytest tests/harness/ tests/codegen/test_use_alias.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q -m "not live"` |
| Subprocess CLI | `python -m voss.cli {check,compile,do} ...` |
| Compiler sub-plan check | `pytest tests/codegen/test_imports.py tests/codegen/test_use_alias.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOG-01 | `voss/harness/agent/loop.voss` exists | file existence + parse | `test -f voss/harness/agent/loop.voss && python -m voss.cli check voss/harness/agent/loop.voss` | ❌ Wave 2 |
| DOG-02 | `voss/harness/agent/router.voss` exists | file existence + parse | `python -m voss.cli check voss/harness/agent/router.voss` | ❌ Wave 2 |
| DOG-03 | `voss/harness/agent/planner.voss` exists | file existence + parse | `python -m voss.cli check voss/harness/agent/planner.voss` | ❌ Wave 2 |
| DOG-04 | `voss/harness/agent/executor.voss` exists | file existence + parse + auto-await codegen | `python -m voss.cli compile voss/harness/agent/executor.voss && grep -q "await " .voss-cache/harness/executor.py` | ❌ Wave 2 |
| DOG-05 | `voss/harness/agent/reviewer.voss` exists | file existence + parse | `python -m voss.cli check voss/harness/agent/reviewer.voss` | ❌ Wave 2 |
| DOG-06 | `voss check voss/harness/agent/` is CI gate | integration | `python -m voss.cli check voss/harness/agent/` (exit 0); CI step `.github/workflows/ci.yml` invokes this | ❌ Wave 1 (dir-walk) + Wave 4 (CI yaml) |
| DOG-07 | Bare `voss` boots through compiled harness | integration | `VOSS_HARNESS=compiled python -m voss.cli do "noop summary of fixture.md"` (exit 0, non-empty stdout) | ❌ Wave 2 (boot dispatch) |
| DOG-08 | Compiled harness artifacts cache under `.voss-cache/harness/` | integration | `python -m voss.cli compile voss/harness/agent/ && test -f .voss-cache/harness/loop.py && test -f .voss-cache/harness/_manifest.json` | ❌ Wave 1 (cache + manifest) |
| D-05 / D-07 dir walk | `voss check <dir>` aggregates per-file diagnostics + summary | unit | `pytest tests/harness/test_voss_check_dir.py -q` | ❌ Wave 1 |
| D-10 stale cache | `StaleHarnessCacheError` on sha mismatch + missing manifest | unit | `pytest tests/harness/test_cache_freshness.py -q` | ❌ Wave 1 |
| D-11 parity | Same fixture, both backends, identical final + tool sequence | integration | `pytest tests/harness/test_voss_loop_parity.py -q` | ❌ Wave 3 |
| Pattern 1a (grammar) | `use ... as alias` parses + roundtrips | unit | `pytest tests/parser/test_use_alias.py tests/codegen/test_imports.py::test_use_stmt_alias_is_preserved_when_ast_provides_alias -q` | parser test ❌ Wave 0; codegen test ✓ existing |
| Pattern 1b (codegen) | `use`-imported callee auto-awaited | unit | `pytest tests/codegen/test_await_use_import.py -q` | ❌ Wave 0 |
| Pitfall 7 (static check) | `voss check voss/harness/agent/` does not load HF encoder | unit | `pytest tests/harness/test_voss_check_dir.py::test_check_dir_does_not_load_hf_encoder -q` | ❌ Wave 1 |

### Sampling Rate
- **Per task commit:** `pytest tests/harness/ tests/codegen/test_use_alias.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q -m "not live"` (~30s).
- **Per wave merge:** Full quick run plus `python -m voss.cli check voss/harness/agent/` + `python -m voss.cli compile voss/harness/agent/` + `VOSS_HARNESS=compiled python -m voss.cli do "noop summary of fixture.md"` smoke (~60s).
- **Phase gate (`/gsd-verify-work`):** All four D-12 success criteria green: `voss check` exit 0 + `voss compile` produces 5 .py + manifest + `VOSS_HARNESS=compiled voss do "<fixture>"` exit 0 with non-empty `TurnResult.final` + parity test green. Full pytest suite passes (`pytest -q -m "not live"`).

### Wave 0 Gaps
- [ ] **Wave 0 (compiler sub-plan):**
  - [ ] `tests/parser/test_use_alias.py` — Pattern 1a parser-level fixture.
  - [ ] `tests/codegen/test_await_use_import.py` — Pattern 1b await emission.
  - [ ] grammar + parser + codegen patches per Pattern 1.
- [ ] **Wave 1 (CLI dir walk + cache infra):**
  - [ ] `voss/harness/cache.py` (NEW, ~80 LOC) — manifest helpers.
  - [ ] `voss/harness/sandbox.py` (MODIFY, +15 LOC) — `write_cache(...)`.
  - [ ] `voss/harness/diagnostics.py` (MODIFY) — `StaleHarnessCacheError` class + `check_harness_cache_fresh(cwd)` row.
  - [ ] `voss/cli.py` (MODIFY) — `_walk_voss_sources` + dir-mode in `check` (line 204) and `compile` (line 147).
  - [ ] `tests/harness/test_voss_check_dir.py` (NEW).
  - [ ] `tests/harness/test_voss_compile_dir.py` (NEW).
  - [ ] `tests/harness/test_cache_freshness.py` (NEW).
- [ ] **Wave 2 (.voss authoring + boot dispatch):**
  - [ ] 5 × `voss/harness/agent/*.voss` files.
  - [ ] Python helper `_run_step_loop(plan_steps, tools, permissions, renderer)` in `voss/harness/agent.py` (per Open Question Q-2) so executor.voss can call it.
  - [ ] `ToolEntry.invoke_dict(args: dict)` helper in `voss/harness/tools.py` (per Pattern 2 spread-workaround).
  - [ ] `voss/harness/cli.py` MODIFY: `_resolve_run_turn()` + replace module-top `from .agent import run_turn` with per-command call sites.
  - [ ] `voss/harness/config.py` extension: read `backend` key from `[harness]`.
- [ ] **Wave 3 (parity test + DOG-07 success):**
  - [ ] `tests/harness/test_voss_loop_parity.py` (NEW) per Pattern 6.
  - [ ] Smoke test: `VOSS_HARNESS=compiled voss do "<fixture>"` end-to-end.
- [ ] **Wave 4 (CI gate + docs):**
  - [ ] `.github/workflows/ci.yml` (MODIFY) — add `python -m voss.cli check voss/harness/agent/` step.
  - [ ] `README.md` (MODIFY) — add eager-compile one-liner under install instructions: `voss compile voss/harness/agent/` (D-16 install-time integration).
  - [ ] `voss/harness/diagnostics.py` — add cache-freshness row to `run_all_checks` (D-16 doctor integration).
- [ ] **Framework install:** Not needed — pytest + pytest-asyncio already pinned in `[project.optional-dependencies].dev`.

## Security Domain

> `security_enforcement` not present in `.planning/config.json`; treating as enabled. M4 surface area is **new compiled artifacts + new env-var + new boot-path dispatch + grammar extension**. No new ingress, no new external surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (M1 owns; M4 reuses `auth.resolve` unchanged) | M4 doesn't touch auth surface. |
| V3 Session Management | No (M1+M2 own; M4 doesn't touch SessionRecord) | M1 D-16 schema-allowlist redaction unchanged. |
| V4 Access Control | Yes (cache write jail) | `sandbox.write_cache()` (Pattern 4) routes through existing `jail_path` to prevent writes outside `.voss-cache/`. |
| V5 Input Validation | Partial | `.voss` sources are static text from the repo; parser validates. Manifest JSON is internal artifact, parsed with strict shape check (`MANIFEST_VERSION`, `voss_version` string compare). No user-supplied input enters the boot path beyond `VOSS_HARNESS` (a closed enum {"python","compiled"}). |
| V6 Cryptography | No (sha256 used for integrity, not auth) | hashlib.sha256 standard library. No key material. |
| V14 Configuration | Yes | `VOSS_HARNESS=compiled` must not be enabled silently in production — but unlike M3's `VOSS_HERMETIC`, there's no fake-response risk; the worst case is `StaleHarnessCacheError` at startup. Loud failure is fine. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Compiled `loop.py` writes outside `.voss-cache/harness/` | Tampering | `_resolve_cache_root` (codegen.py:218-235) refuses non-`.voss-cache` paths; `sandbox.write_cache` (new) double-checks via `jail_path`. |
| Attacker substitutes `.voss-cache/harness/loop.py` between compile and boot | Tampering / RCE | sha256 check in `assert_fresh` validates each source against the manifest. If `loop.py` was hand-edited without re-running `voss compile`, the next boot raises `StaleHarnessCacheError`. (Note: sha is on the SOURCE `.voss` files, not on the compiled `.py`. So a hand-edit of `loop.py` is NOT detected by sha alone — see Open Question / Pitfall: this is by design per D-14, but a future hardening pass could add a sha of the .py artifact too.) |
| `VOSS_HARNESS=compiled` in an environment where cache is missing | Repudiation / Availability | D-10 loud `StaleHarnessCacheError` with explicit `run: voss compile voss/harness/agent/` fix suggestion. No silent fallback to Python (D-10 explicit). |
| Imported Python module via `use voss::harness::X` resolves to attacker-controlled package | Tampering / RCE | Python import machinery handles trust. `voss.harness` is the repo's own package — installed via `pip install -e .`; no path-injection risk. Generated `from voss.harness import X` lines are literal text written by codegen (codegen.py:142-148) — no template injection. |
| `_manifest.json` parsed with arbitrary JSON | Tampering | Manifest version mismatch raises `StaleHarnessCacheError`. No `eval` / no `pickle` — only `json.loads`. |
| Source `.voss` file in `voss/harness/agent/` contains shell-injection style content | Tampering | `.voss` is parsed by lark, not executed by shell. Codegen emits Python text written via `write_cache` (atomic, jailed). |
| Parity test asserts equality on attacker-controllable values | Spoofing | Parity test uses `FakeProvider` with a hard-coded Plan fixture; no external input. |

## Sources

### Primary (HIGH confidence — verified by reading source at cited file:line)

- `/Users/benjaminmarks/Projects/Voss/voss/harness/agent.py:1-238` — `run_turn` (100-231), `Plan`/`ToolCall`/`TurnResult` (35-89), `PLAN_SYSTEM` (64-79), `_format_tools` (91-97), `_summarize` (234-238).
- `/Users/benjaminmarks/Projects/Voss/voss/harness/cli.py:1-737` — `do_cmd` (177-246), `chat_cmd` (271-292), `edit_cmd` (319-357), `_run_repl` (360-489), `_resolve_auth_or_die` (108-147), `_resolve_default_model` (38-56), `AGENT_COMMANDS` (689-704), module-top `from .agent import run_turn` (23).
- `/Users/benjaminmarks/Projects/Voss/voss/cli.py:1-294` — `_compile_source` (75-118), `compile` (147-167), `run` (170-201), `check` (204-228), `_walk_voss_sources` (does not yet exist — Pattern 3 adds it), `_parse_file` (32-37), `_write_text_atomic` (56-72).
- `/Users/benjaminmarks/Projects/Voss/voss/grammar.lark:1-219` — `use_stmt` + `use_path` (174-175), `try_stmt` (133), `ctx_stmt` (128), `within_stmt` (129), `fn_decl` (156), `agent_decl` (161-164), `confidence_gate` (73-74), no `await` keyword anywhere (verified), no `for` loop (verified).
- `/Users/benjaminmarks/Projects/Voss/voss/parser.py:1-799` — `try_stmt` (542-557), `use_path` (711-712), `use_stmt` (714-715 — always `alias=None`), `fn_decl` (589-609), `agent_decl` (634-655), `decorated_decl` (730-735).
- `/Users/benjaminmarks/Projects/Voss/voss/codegen.py:1-1283` — `ImportCollector.add_use` (126-131), `render` (133-163), `_emit_fn` (798-811, emits `async def`), `_emit_agent` (830-871, emits `class X(VossAgent): async def run`), `_emit_try` (1107-1126), `_emit_ctx` (935-957), `_emit_within` (959+), `_emit_call` (417-447, the await-trigger condition at 441-446), `_emit_member_call` (457-481, only special-cases `.map` and `.join`), `_resolve_cache_root` (218-235, jail), `ProgramEmitter.emit` (1173-1250, `requires_async_main` gated on non-decl execs at 1192).
- `/Users/benjaminmarks/Projects/Voss/voss/harness/sandbox.py:1-50` — `jail_path` (20-31), `shell_allowed` (34-49), `SandboxError` (16-17). **No file-write helper today.**
- `/Users/benjaminmarks/Projects/Voss/voss/harness/diagnostics.py:1-198` — `Check` dataclass (27-32), `CheckResult` enum (21-25), `run_all_checks` (181-191), `aggregate_exit_code` (194-198), individual checks (35-178).
- `/Users/benjaminmarks/Projects/Voss/voss/harness/tools.py:1-199` — `ToolEntry` dataclass (14-38), `invoke` proxies to `descriptor.invoke(**kwargs)` (37-38), `make_toolset` (41+).
- `/Users/benjaminmarks/Projects/Voss/voss/harness/permissions.py:1-50` — `PermissionGate` (referenced; mode/tier check). `Mode` literal (28). `mode_allows` (35-50).
- `/Users/benjaminmarks/Projects/Voss/voss/harness/cognition.py:1-361` — `voss_dir` / `cache_dir` (67-72), `_load_json` (80-94), `build_repo_idx` (254-310, sha1 + JSON manifest pattern to mirror), `append_gitignore_line_idempotent` (329-344).
- `/Users/benjaminmarks/Projects/Voss/voss/exceptions.py:1-22` — `VossError` base (4-5), `VossParseError` (7-22).
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/__init__.py:1-59` — public re-exports including `ContextScope`, `EpisodicMemory`, `ModelProvider`, `Plan`-relevant names, `StubProvider`, `tool`.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/agent.py:1-110` — `VossAgent` (17-76), `AgentHandle` (79-92), `gather` (95-110).
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/providers/stub.py:1-74` — `StubProvider.complete` (32-70), `fingerprint` (29-30).
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/tools.py:1-103` — `ToolDescriptor` (41-62, `invoke` at 58-59).
- `/Users/benjaminmarks/Projects/Voss/tests/harness/test_agent_integration.py:1-180` — `FakeProvider` (21-50), parity test pattern (project fixture, `_run` helper, plan-driven assertions).
- `/Users/benjaminmarks/Projects/Voss/tests/codegen/test_imports.py:1-105` — `use` codegen tests including alias preservation (56-60).
- `/Users/benjaminmarks/Projects/Voss/.github/workflows/ci.yml:1-48` — stub job (14-26) where M4 D-06 CI step inserts.
- `/Users/benjaminmarks/Projects/Voss/samples/research.voss:1-41` — current `agent` + `ctx` + `within/fallback` reference.
- `/Users/benjaminmarks/Projects/Voss/samples/classify.voss:1-13` — current `probable<T>` + confidence gate reference.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md:1-192` — full user decisions (D-01..D-16).
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M4-voss-authored-harness-loop/M4-DISCUSSION-LOG.md:1-130` — discuss alternatives audit trail (all options aligned with CONTEXT decisions).
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M1-harness-happy-path/M1-CONTEXT.md:1-184` — carry-forward D-05 strict-tier + D-13 diagnose-don't-fix.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M2-project-cognition/M2-CONTEXT.md:1-211` — carry-forward D-02 `/analyze` stays Python + D-06 `.voss-cache/` writes through sandbox.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M3-language-validation/M3-CONTEXT.md:1-191` — carry-forward D-01/D-02 auto-StubProvider + D-03 static-only check + D-12 raw-Python parity oracle.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M3-language-validation/M3-RESEARCH.md` (lines 1-784) — verified parser surface for `try/catch`, `use::path`, `memory.X`. M3-RESEARCH §Pitfall 1 documents the `use foo.bar` parser rejection that mirrors M4 Pitfall 1.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M3-language-validation/M3-PATTERNS.md:1-200` — analog patterns (sample header convention, raw-Python parity oracle).
- `/Users/benjaminmarks/Projects/Voss/.planning/REQUIREMENTS.md:67-74` — DOG-01..DOG-08 (M4 owned).
- `/Users/benjaminmarks/Projects/Voss/.planning/ROADMAP.md:191-225` — M4 phase goal + 4 success criteria + cross-cutting constraints.
- `/Users/benjaminmarks/Projects/Voss/.planning/STATE.md:1-60` — current position confirmation.
- `/Users/benjaminmarks/Projects/Voss/.planning/config.json:1-40` — `nyquist_validation: true`, `security_enforcement` absent (treat as enabled).
- `/Users/benjaminmarks/Projects/Voss/.vscode/voss_v_0_1_scope_lock.md` (M4 §) — scope lock source of truth (read via M4-CONTEXT canonical refs, not re-fetched).

### Secondary
None used — all verification is in-repo.

### Tertiary
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every recommendation uses an in-tree library or pattern; no new deps.
- Architecture: HIGH — file:line citations for every claim; behavior verified by reading source.
- Pitfalls: HIGH — Pitfalls 1, 2, 3, 7 are directly verifiable in current code; Pitfalls 4, 5, 6, 8 are pattern-match risks with verified mitigations.
- Compiler sub-plan feasibility: HIGH on what needs to change (grammar.lark:174-175 line edit, parser.py:714-715 4-line patch, codegen.py:441-446 condition extension); MEDIUM on whether the sub-plan stays under 100 LOC of diff — could grow if test fixtures fan out. Recommend the planner budget the sub-plan as 1 plan with 3-5 sub-tasks, monitor scope.
- Parity test reliability: HIGH — `FakeProvider` pattern is in tree and proven (`tests/harness/test_agent_integration.py`).

**Research date:** 2026-05-11
**Valid until:** 2026-06-11 (compiler stack is stable; re-validate only if `voss/grammar.lark`, `voss/parser.py`, `voss/codegen.py`, or `voss/harness/cli.py` see major refactors).

## RESEARCH COMPLETE
