# Phase M4: Voss-authored Harness Loop - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

M4 dogfoods `.voss` on the harness itself. It rewrites the agent turn loop — currently a single 130-LOC Python function `voss/harness/agent.py:run_turn` — as a five-file `.voss` program under `voss/harness/agent/{loop,router,planner,executor,reviewer}.voss`. Each file owns one stage of the existing pipeline. `voss check voss/harness/agent/` becomes a CI gate (DOG-06). Compiled artifacts cache under `.voss-cache/harness/` (DOG-08). Bare `voss` gains an env-flag opt-in (`VOSS_HARNESS=compiled`) that swaps the Python `run_turn` import for the compiled-from-`.voss` equivalent (DOG-07). Default backend remains Python until v0.1 ships; the compiled path is real but opt-in.

**In scope:**
- Five `.voss` files under `voss/harness/agent/`, expressing a thin control-flow pipeline:
  - `loop.voss` — outer driver: `ctx(budget) { history; route; plan; execute; review }`.
  - `router.voss` — intent classification: `probable<Intent> = classify(task)`; distinguishes slash-command vs natural-language paths.
  - `planner.voss` — the `probable<Plan>` ask; confidence gate; clarify branch when below threshold.
  - `executor.voss` — sequential tool-step dispatch through the existing Python `PermissionGate`.
  - `reviewer.voss` — synthesizes `final_when_done` from tool results; renders to user.
- Thin-`.voss` boundary: `.voss` owns only control flow (`ctx`, `probable<T>`, confidence gates, fallback, `try/catch`). Python keeps everything else — pydantic `Plan`/`ToolCall` models, the `PLAN_SYSTEM` prompt string, the tool registry, `ModelProvider.complete`, the permission gate, sessions, rendering. `.voss` files import Python symbols via `use voss.harness as h`.
- Orchestration direction: **Python imports compiled `.voss` functions.** `voss compile voss/harness/agent/loop.voss` produces `.voss-cache/harness/loop.py` that exports `async def run_turn(task, *, tools, cwd, renderer, ...)`. The harness CLI imports that function when `VOSS_HARNESS=compiled`. `.voss` is implementation; Python is the entry point.
- `voss check` extended to walk directories: when `source.is_dir()`, glob `*.voss` recursively, parse + analyze each, aggregate diagnostics, exit non-zero on any error. Stays static-only (M3 D-03). CI step: `voss check voss/harness/agent/`.
- `voss compile` extended to walk directories: emits one `.py` per source `.voss` under `.voss-cache/harness/`, plus a `_manifest.json` keying source path → source sha + voss version + compiled-at timestamp.
- Loader contract: when `VOSS_HARNESS=compiled`, `voss/harness/cli.py` imports `run_turn` from `.voss-cache/harness/loop.py`. Stale cache (sha mismatch in `_manifest.json`) raises a structured error pointing to `voss compile voss/harness/agent/`. No silent fallback.
- Eager compile hook: install-time (or via `voss doctor --fix` / a new `voss compile voss/harness/agent/` one-liner in docs) runs the directory compile once. JIT compile-on-import is explicitly NOT in scope.
- Parity oracle: `voss/harness/agent.py:run_turn` stays in tree indefinitely as the parity reference (M3 D-12 pattern). A new test `tests/harness/test_voss_loop_parity.py` runs both backends under `StubProvider` on a fixture task and asserts equivalent `TurnResult.final` + same tool-call sequence.
- Success bar for DOG-07: `VOSS_HARNESS=compiled voss do "<fixture task>"` runs end-to-end under `StubProvider` and produces a non-empty `TurnResult` whose `final` and tool-call sequence match the Python path. CI asserts this.
- Cache layout: `.voss-cache/harness/{loop,router,planner,executor,reviewer}.py` + `_manifest.json`. Per-file artifacts. Cache key: source `sha256` + voss version. Writes go through `voss/harness/sandbox.py` (M2 D-06).

**Out of scope (deferred to other phases):**
- Real-provider (Anthropic/OpenAI/etc.) parity under `VOSS_HARNESS=compiled` — `StubProvider` parity is the M4 bar. Live-provider parity defers to M5.
- `voss do` / `voss edit` / `voss chat` full feature parity under compiled path — only `voss do` on a fixture task is asserted in M4. `voss edit` scoped sessions and `voss chat` REPL stay on the Python path until proven.
- `/analyze` (M2 cognition skill) rewritten in `.voss` — that skill is already locked to Python by M2 D-02. M4 does not touch it.
- `voss check --speed-budget` flag, codegen-snapshot diff tests, or any expanded check semantics beyond directory walking — keep the CLI surface minimal.
- JIT compile-on-import (compile lazily on first bare-voss boot) — rejected. Eager `voss compile voss/harness/agent/` is the contract; stale cache is a loud error.
- Bundled single-module cache layout (one `harness.py` exporting `run_turn`) — rejected. Per-file artifacts are the M4 contract for debuggability and per-file regression isolation.
- Auto-detect boot path (use compiled when cache fresh, else fall back silently to Python) — rejected. Env-flag opt-in is the contract; silent backend swaps would mask regressions.
- New `.voss` runtime entry shape where `.voss` is the top-level driver (`voss run loop.voss` with task injected) — rejected. Python-imports-compiled is the orchestration direction.
- Retiring `voss/harness/agent.py` — kept indefinitely as parity oracle.
- Symbolic-only DOG-07 (check passes + import works but no real turn) — rejected. M4 requires a real turn under stub provider.
- Full-parity DOG-07 (compiled path equals Python on every M1 command, live providers) — rejected as M4 overflow.

</domain>

<decisions>
## Implementation Decisions

### File decomposition + Python/.voss seam
- **D-01:** Pipeline split — one stage per file. `loop.voss` (orchestration + ctx budget + history), `router.voss` (`probable<Intent>` classification), `planner.voss` (`probable<Plan>` ask + confidence gate), `executor.voss` (tool-step dispatch), `reviewer.voss` (final synthesis from results). Linear pipeline; `loop.voss` is the only file that calls the others. Each file targets 20–40 LOC of `.voss`.
- **D-02:** Thin `.voss`. The files express ONLY control flow — `ctx(budget: N)`, `probable<T>`, confidence gates (`plan @ p >= threshold`), `try/catch`, `fallback`. Everything else stays Python: the `Plan`/`ToolCall` pydantic models (`voss/harness/agent.py:35–56`), the `PLAN_SYSTEM` prompt text, the tool registry/descriptors, `ModelProvider.complete` calls, the permission gate, `SessionRecord`/`RunRecord`, rendering. `.voss` files import Python symbols via `use voss.harness as h` (or equivalent — researcher must confirm parser surface).
- **D-03:** Orchestration direction — **Python imports compiled `.voss` functions**, not the reverse. `voss compile voss/harness/agent/loop.voss` produces `.voss-cache/harness/loop.py` whose top-level exports include `async def run_turn(task, *, tools, cwd, renderer, confidence_threshold, token_budget, model, provider, history, permissions) -> TurnResult` — the same signature as `voss/harness/agent.py:100`. The harness CLI swaps imports based on `VOSS_HARNESS`. No new runtime entry-point shape.
- **D-04:** Tool exposure to `.voss` — tools are NOT redeclared as `@tool` in the `.voss` files. They remain Python descriptors (`voss/harness/tools.py`); the `.voss` `executor` receives the `tools: dict[str, ToolEntry]` argument and iterates `plan.steps`, calling back into Python `tool.invoke(step)`. Permission gate stays 100% Python (M1 D-05). `.voss` does not gain a privileged tool-call path.

### `voss check <dir>` + CI gate
- **D-05:** Extend `voss check` to walk directories. In `voss/cli.py:check` (line 209), when `source.is_dir()`, glob `source.rglob("*.voss")`, parse + analyze each, aggregate diagnostics across files (preserving per-file line/col), exit non-zero on any error. Single-file behavior unchanged. Same for `voss compile`.
- **D-06:** CI gate is static-only — `voss check voss/harness/agent/` runs in CI. Matches M3 D-03 (static-only check). Compile-and-stub-run regression coverage lives in a separate pytest file (D-13), NOT inside the `voss check` invocation.
- **D-07:** Aggregated diagnostic output format: one `<file>:<line>:<col>: <severity> <message>` line per diagnostic, grouped by file, with a final summary `N errors, M warnings across K files`. Non-zero exit on any error. `--warnings-as-errors` still applies.

### Boot path (DOG-07) + parity oracle
- **D-08:** Env-flag opt-in. `VOSS_HARNESS=compiled` (env var) OR `[harness] backend = "compiled"` in `~/.config/voss/config.toml` flips the import in `voss/harness/cli.py`. Default value: `"python"`. Resolution order: env-var > config.toml > default. CLI flag override `--harness={python,compiled}` is allowed but optional (researcher: decide if needed — `voss do --harness=compiled` is convenient for testing, but env-var covers most cases).
- **D-09:** `voss/harness/agent.py:run_turn` stays in tree indefinitely as the parity oracle. Mirrors M3 D-12 (raw-Python parity oracle). It is not retired by M4 — only by a future phase that proves the compiled path equals it on every supported task class.
- **D-10:** Stale-cache behavior under `VOSS_HARNESS=compiled`: the loader reads `.voss-cache/harness/_manifest.json`, compares each source sha to the live source. On mismatch (or missing manifest), raise a structured `StaleHarnessCacheError` with the message `compiled harness cache stale — run: voss compile voss/harness/agent/`. NO silent fallback to Python. Loud failure is the M4 contract (M1 D-13 diagnose-don't-fix posture).
- **D-11:** Parity contract: `tests/harness/test_voss_loop_parity.py` runs a fixture task through both backends under `StubProvider` (M3 D-01 auto-fallback exercised). Asserts: `python_result.final == voss_result.final` AND tool-call sequence (name + args) is identical. Single fixture task in M4 (`"noop summary of fixture.md"`); broader fixture matrix is deferred.
- **D-12:** M4 success bar (gates merge): (a) `voss check voss/harness/agent/` exits 0; (b) `voss compile voss/harness/agent/` produces all five `.py` files + `_manifest.json`; (c) `VOSS_HARNESS=compiled voss do "<fixture task>"` exits 0 with non-empty `TurnResult.final`; (d) parity test passes. Live-provider compiled parity is NOT a gate.

### Cache layout + invalidation (DOG-08)
- **D-13:** Per-file artifacts. `.voss-cache/harness/{loop,router,planner,executor,reviewer}.py` — one Python file per `.voss` source. `_manifest.json` shape: `{ "version": 1, "voss_version": "<pkg version>", "compiled_at": "<ISO>", "sources": { "loop.voss": {"sha256": "<hex>", "lines": <int>}, ... } }`. Per-file isolation makes regressions traceable; bundled-module layout (D-out-of-scope) rejected.
- **D-14:** Cache key = source `sha256` + `voss_version`. NOT git-head (we want cache reuse across branches when files are unchanged). NOT mtime (unreliable across checkouts). The loader recomputes sha at boot under `VOSS_HARNESS=compiled` and raises on mismatch (D-10).
- **D-15:** Cache writes go through `voss/harness/sandbox.py` (M2 D-06 cross-cutting). The compile command writing to `.voss-cache/harness/` uses the existing sandboxed-write helper; no direct `Path.write_text` from the harness compile path.
- **D-16:** Eager compile only. `voss compile voss/harness/agent/` is the contract. Suggested integration: (a) developer ergonomics — `voss doctor` reports cache freshness and suggests the compile command on drift; (b) install-time — a `pip install -e .` post-install hook or `voss init --compile-harness` flag (researcher: pick lowest-friction). JIT compile-on-import explicitly rejected.

### Claude's Discretion
- Exact syntax of `use voss.harness as h` (or equivalent Python-symbol import in `.voss`) — researcher must confirm `voss/parser.py` + `voss/grammar.lark` accept it; if the construct is absent, a small grammar/codegen extension precedes the `.voss` files (treat as a sub-plan, do not let it expand M4 scope into compiler work).
- Exact `probable<Intent>` type representation in `router.voss` — pick the smallest shape that distinguishes slash-command from natural-language paths; mirror `Plan`'s pydantic-import pattern from D-02.
- The `voss compile <dir>` invocation shape — flag-compatible with single-file `voss compile`; emit per-file diagnostics and a final summary identical in spirit to `voss check`.
- Whether `--harness=python|compiled` CLI flag is added in addition to the env-var (D-08) — convenient for ad-hoc testing; rejecting it forces env-var ceremony. Pick the smallest diff that's testable.
- `StaleHarnessCacheError` exception class location — `voss/harness/diagnostics.py` is the natural home (mirrors M1's diagnose-don't-fix structure).
- Fixture task content for the parity test (D-11) — any deterministic no-op-ish task that `StubProvider` resolves identically under both backends.
- `voss doctor` reporting for harness-cache freshness — extends M2's cognition rows; informational warning only, never blocking.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v0.1 scope and product framing
- `.vscode/voss_v_0_1_scope_lock.md` §"M4: Voss-authored Harness Loop" — Source of truth for DOG-* requirements.
- `.planning/PROJECT.md` — Specifically the "Harness loop can be dogfooded through `voss/harness/agent/loop.voss`, `router.voss`, `planner.voss`, `executor.voss`, `reviewer.voss`" bullet and the "Python harness first, Rust later" principle.
- `.planning/REQUIREMENTS.md` §lines containing DOG-01..DOG-08 — The 8 requirements M4 owns.
- `.planning/ROADMAP.md` §"Phase M4: Voss-authored Harness Loop" — Phase goal, success criteria, cross-cutting constraints ("Python fallback may remain until compiled harness path is proven" — D-08/D-09 lean on this).

### Prior phase decisions (carry forward)
- `.planning/phases/M1-harness-happy-path/M1-CONTEXT.md` — Specifically D-05 (strict tier permission gate; M4 D-04 keeps tools in Python so the gate is not bypassed) and D-13 (diagnose-don't-fix; M4 D-10 loud stale-cache error mirrors this).
- `.planning/phases/M2-project-cognition/M2-CONTEXT.md` — Specifically D-02 (`/analyze` stays Python; M4 dogfoods only the turn loop, not skills) and D-06 (`.voss-cache/` writes through `sandbox.py`; M4 D-15 inherits).
- `.planning/phases/M3-language-validation/M3-CONTEXT.md` — Specifically D-01/D-02 (auto-StubProvider + banner; the M4 parity test relies on this), D-03 (static-only `voss check`; M4 D-06 extends without breaking it), D-12 (raw-Python parity oracle pattern; M4 D-09 applies this to `voss/harness/agent.py`).

### Existing harness stack (extend, do not rewrite)
- `voss/harness/agent.py` (238 LOC) — Source of `run_turn` (line 100), `Plan`/`ToolCall` pydantic models (lines 35–56), `PLAN_SYSTEM` prompt (lines 64–79), `TurnResult` dataclass (line 82). This file stays as the parity oracle (D-09).
- `voss/harness/cli.py` (15.5k bytes) — Where `VOSS_HARNESS` is read and the `run_turn` import is swapped (D-08). The `chat_cmd` and `do_cmd` entry points both route through `run_turn`.
- `voss/harness/tools.py` (7.3k bytes) — `ToolEntry` descriptors and the registry. M4 D-04: `.voss` does NOT redeclare tools; the registry stays here.
- `voss/harness/permissions.py` (5k bytes) — `PermissionGate`. M4 D-04: gate stays 100% Python; `.voss` does not bypass.
- `voss/harness/sandbox.py` (1.4k bytes) — Sandboxed file writes. M4 D-15: `.voss-cache/harness/` writes route through this.
- `voss/harness/session.py`, `voss/harness/render.py`, `voss/harness/providers.py` — Stay Python; the compiled `.voss` path imports `run_turn`'s caller surface, not these.
- `voss/harness/diagnostics.py` — Natural home for `StaleHarnessCacheError` (D-10).

### Compiler stack (extend for directory walking)
- `voss/cli.py:check` (line 204–228) — Extend for directory input (D-05). Add `if source.is_dir(): rglob("*.voss")` branch.
- `voss/cli.py:compile` (line 147–167) — Same extension (D-05).
- `voss/parser.py` (799 LOC) + `voss/grammar.lark` (219 LOC) — Researcher must confirm `use voss.harness as h` (or chosen equivalent), `ctx`, `probable<T>`, `try/catch`, and confidence-gate syntax (`plan @ p >= 0.6`) all parse against the agent-loop file shape. M3 already requires `try/catch` and `use`; if M3 ships first, surface is confirmed.
- `voss/analyzer.py` (766 LOC) — `_warn_unguarded_probable` already handles probable-value gating (M3 prior art). M4 likely needs no new analyzer rules.
- `voss/codegen.py` (1283 LOC) — Lowers AST to Python. M4 needs the codegen to emit a top-level `async def run_turn(...)` with the M1 signature when the `.voss` source declares it. Researcher: confirm current async-function codegen surface.

### Runtime contract
- `voss_runtime/__init__.py` and submodules — `ContextScope`, `ProbableValue`, `StubProvider`. M4's compiled `.voss` files import from here exactly as M3's samples do.
- `voss_runtime/providers/litellm_provider.py` + auto-stub resolver — M4's parity test depends on M3's auto-fallback being live.

### Tests (mirror, extend)
- `tests/harness/test_session_redaction.py` — Pattern for harness-level pytest. M4's `tests/harness/test_voss_loop_parity.py` (D-11) mirrors structure.
- `tests/examples/` (built in M3) — Pattern for stub-provider end-to-end tests. M4's parity test reuses `StubProvider` setup helpers if they exist after M3.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`voss/harness/agent.py:run_turn`** — The function being dogfooded. Its body (lines 100–233) is the algorithm `.voss` files express; its signature (lines 100–112) is the export contract the compiled `loop.py` must match.
- **`voss/harness/agent.py:PLAN_SYSTEM`** — The system prompt the planner uses. Stays Python under thin-`.voss` (D-02); `planner.voss` imports it as a symbol.
- **`voss/harness/agent.py:Plan`, `ToolCall`, `TurnResult`** — Pydantic models / dataclass. Stay Python; `.voss` references them via `probable<h.Plan>` (D-02 strawman syntax).
- **`voss/harness/tools.py:ToolEntry`** — Tool registry shape. M4 D-04 keeps tools as Python descriptors; executor.voss iterates without redeclaring.
- **`voss/harness/permissions.py:PermissionGate`** — Gate stays Python (D-04, M1 D-05).
- **`voss/harness/sandbox.py`** — Sandboxed file-write helper. `voss compile voss/harness/agent/` routes through this for `.voss-cache/harness/` writes (D-15, M2 D-06).
- **`voss_runtime.StubProvider`** + auto-fallback (M3 D-01) — Parity test depends on this. No new test infra.
- **`voss/cli.py:_compile_source` and `_parse_file`** — Already centralize per-file parse/compile. The dir-walking branch (D-05) is a loop around these.

### Established Patterns
- **Strict tier / loud failure** (M1 D-05, M2 D-07, M3 D-02) — M4 mirrors: stale cache raises a structured error (D-10), never silent fallback.
- **Diagnose-don't-fix** (M1 D-13) — `voss doctor` reports cache staleness; user runs `voss compile voss/harness/agent/`; harness does not auto-recompile.
- **Hermetic-by-default tests** (M3 D-11) — Parity test (D-11) uses `StubProvider` + auto-fallback; no real provider calls.
- **Parity oracle** (M3 D-12) — `voss/harness/agent.py` is the M4 parity oracle, exact analogue of `examples/raw_python/*.py` for M3.
- **`.voss-cache/` writes through `sandbox.py`** (M2 D-06) — M4 inherits.
- **Env-flag opt-in defaults to safe** (`VOSS_HERMETIC` in M3) — `VOSS_HARNESS` mirrors: defaults to `python`, opt-in to `compiled`.

### Integration Points
- **`voss/harness/cli.py`** (look for the `chat_cmd` / `do_cmd` definitions and the `run_turn` import sites) — Where the `VOSS_HARNESS` env-flag dispatch lives (D-08). Single import-swap site.
- **`voss/cli.py:check` (line 209) and `voss/cli.py:compile` (line 153)** — Both gain a directory-walking branch (D-05).
- **`voss/harness/diagnostics.py`** — `StaleHarnessCacheError` (D-10).
- **`voss/parser.py` + `voss/grammar.lark`** — Researcher confirms parser surface accepts `use`, `ctx`, `probable<T>`, confidence-gate syntax, `try/catch` against the agent-loop file shape. If gaps exist, plan a small compiler sub-task BEFORE the `.voss` files land.
- **`voss/codegen.py`** — Must emit a top-level `async def run_turn(...)` with the M1 signature when the `.voss` source declares it. Researcher confirms current async codegen surface.
- **`voss-cache/harness/_manifest.json` schema** — New artifact; documented in D-13. Loader reads it on every bare-voss boot under `VOSS_HARNESS=compiled`.
- **CI workflow** — Gains `voss check voss/harness/agent/` step (D-06). Existing `voss check` CI steps for `samples/*.voss` extend to also run dir-mode against the harness dir.

</code_context>

<specifics>
## Specific Ideas

- **The pipeline (D-01) mirrors the existing `run_turn` body comment block in `voss/harness/agent.py:114–125`** — that pseudo-`.voss` block is already the design target. M4 ships it as real `.voss`.
- **`VOSS_HARNESS=compiled` is the v0.1 dogfood toggle.** Mirrors `VOSS_HERMETIC=1` from M3 — env-flag opt-in defaulting to safe, structured failure when prerequisites missing.
- **Parity oracle is the dogfood-honesty contract.** Keeping `voss/harness/agent.py` in tree means any compiled-path regression is one parity-test run away from visible. Retiring agent.py is a future-phase decision, not M4's.
- **Stub-provider real-turn (not symbolic-only) is the dogfood-credibility bar.** A compiled harness that only passes `voss check` doesn't prove the language. A compiled harness that runs a turn under stub provider does.
- **Per-file artifacts (D-13), not bundled** — debuggability over import-time micro-optimization. If `executor.py` regresses, it's traceable to `executor.voss` directly.

</specifics>

<deferred>
## Deferred Ideas

- **Live-provider parity under `VOSS_HARNESS=compiled`** — out of scope. M4 bar is StubProvider parity (D-12). Live-provider compiled parity defers to M5 or a dedicated hardening phase.
- **`voss edit` scoped sessions through the compiled path** — out of scope. `voss edit` keeps Python `run_turn` until proven; M4 only asserts `voss do` on a fixture task.
- **`voss chat` REPL through the compiled path** — same posture as `voss edit`.
- **Rewriting `/analyze` (M2 D-02) in `.voss`** — explicitly deferred by M2. Not M4.
- **Auto-detect boot path (use compiled when cache fresh, else Python)** — rejected. Silent backend swap masks regressions; env-flag is the contract.
- **JIT compile-on-import** — rejected. Eager `voss compile voss/harness/agent/` is the contract.
- **Bundled single-module cache layout (`harness.py` exporting `run_turn`)** — rejected for debuggability.
- **CLI `--harness={python,compiled}` flag** — Claude's discretion; may land if env-var ceremony is too high for ad-hoc testing.
- **Retiring `voss/harness/agent.py`** — not M4. Parity oracle stays indefinitely.
- **Symbolic-only DOG-07 (check + import; no real turn)** — rejected as too weak.
- **Full-parity DOG-07 across `voss do` / `voss edit` / `voss chat` on live + stub providers** — too large for M4.
- **Codegen-snapshot tests on `.voss-cache/harness/*.py`** — would catch silent codegen drift. M3 deferred broader codegen snapshots; M4 inherits the deferral. Parity test (D-11) is the M4 codegen-correctness signal.
- **Compile-and-stub-run inside `voss check`** — D-06 keeps the gate static. The compile-and-run smoke lives in pytest, not in `voss check`.
- **`voss check --speed-budget` flag for tunable speed gate** — deferred (also M3 deferred).
- **Tree-sitter grammar / Linguist upstream PR** — deferred from M0 forward.
- **Rust harness shell** — explicitly post-v0.1.

</deferred>

---

*Phase: M4-voss-authored-harness-loop*
*Context gathered: 2026-05-11*
