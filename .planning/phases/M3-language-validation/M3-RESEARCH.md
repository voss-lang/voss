# Phase M3: Language Validation - Research

**Researched:** 2026-05-11
**Domain:** `.voss` language toolchain validation (parser + analyzer + codegen + runtime + CLI), three canonical AI-workflow samples, hermetic e2e test suite, framing docs.
**Confidence:** HIGH (all claims verified against the codebase at `/Users/benjaminmarks/Projects/Voss/` and cited by file:line)

## Summary

The `.voss` toolchain is **already substantially complete** for M3's surface. Parser (`voss/parser.py:1-799` + `voss/grammar.lark:1-219`) accepts every construct M3 needs — `try/catch` with optional named exception (grammar.lark:133, parser.py:542-557), `use foo::bar` paths (grammar.lark:174-175, parser.py:711-715), `memory.episodic(capacity: 20 turns)` member-typed `let` (grammar.lark:16-22; assistant.voss demonstrates it). The codegen emits working Python for all of them: `try/catch` lowers to `try/except Exception` (codegen.py:1107-1126), `use voss_runtime::tools` lowers to `from voss_runtime import tools` (codegen.py:142-148; test_imports.py:71-90), and `memory.episodic` becomes `EpisodicMemory(capacity=20)` (codegen.py:690-705). The legacy phase-06 test suite (`tests/examples/`) already exists with helpers.py, test_classify_e2e.py, test_support_e2e.py, test_research_e2e.py, test_cli_matrix.py — created May 9, 2026. M3 is overwhelmingly a **wiring + sample-extension + framing** phase, not a compiler-extension phase.

There are exactly **three real implementation gaps** to close before everything Just Works:

1. **D-03 (static-only check) is violated today.** `Analyzer._visit_match_stmt` (analyzer.py:479-501) unconditionally calls `index_builder.build_cases(...)`, which constructs a real `SemanticMatcher` (analyzer.py:181-184) which calls `_encode([...descriptions...])` (semantic.py:43) which calls `_ensure_encoder` (semantic.py:45-50) which loads the HF sentence-transformers model. The `emit_indexes` flag (analyzer.py:435) only gates writing the manifest to disk — it does NOT gate the encoder load. Cold `voss check samples/support.voss` measures **~13s** wall-clock; warm **~8.9s**. After the fix, all three samples check in <1s warm.
2. **D-01 (auto-StubProvider fallback) does not exist.** `voss_runtime.providers.get()` (providers/__init__.py:12-18) returns `LiteLLMProvider` as the default; no current code path inspects credentials before `voss run`. The hook already exists for the harness side: `voss.harness.auth.resolve(preference="auto")` (harness/auth.py:332-375) returns `Resolution(source="none", ...)` when no creds are found, and `harness/cli.py:38-77` already uses it. M3 wires that same resolver into `voss/cli.py:run`, registers `StubProvider` for the resolved-`none` case, emits the stderr banner, and proceeds.
3. **The legacy `tests/examples/` test files currently exercise `tests/parser/examples/*.voss`, not `samples/*.voss`.** CONTEXT D-09/D-10 keep `tests/examples/` as the path but the canonical sources the e2e suite must validate are `samples/classify.voss`, `samples/support.voss`, `samples/research.voss` (so the post-M3 sample extensions are validated). `helpers.copy_example` (tests/examples/helpers.py:23,26-31,34-39) needs a new constant pointing at the repo's `samples/` directory (or an updated `example_source` to look there).

Sample content changes are mechanical: append `memory.episodic` declaration + `.add(...)` + `.last(...)` lines to `samples/support.voss` (already covered by codegen at codegen.py:690-705); wrap `webSearch(...)` in `try { ... } catch { ... }` and prepend `use voss_runtime::tools` to `samples/research.voss`. Raw-python parity files (`examples/raw_python/{support,research}.py`) get matching changes so the e2e parity assertions hold.

**Primary recommendation:** Plan order — (a) Wave 0 fix `voss check` to be static-only (analyzer.py:479-501); (b) wire auto-StubProvider into `voss/cli.py:run`; (c) extend `samples/{support,research}.voss` + their `examples/raw_python/` parity files + sample header comments; (d) re-point `tests/examples/` to `samples/` and slim per D-09 (drop test_helpers.py + test_live_examples.py); (e) add `tests/examples/test_check_speed.py` with hard ≤2s ceiling; (f) parser/analyzer/codegen "coverage" fixtures for `memory.semantic` / `memory.working`; (g) README "What is .voss" section + per-sample header comments + `docs/voss-vs-python.md`.

## Project Constraints (from CLAUDE.md)

There is no `/Users/benjaminmarks/Projects/Voss/CLAUDE.md`. The harness session loaded `~/CLAUDE.md` (user-global) and `~/.claude/CLAUDE.md` (project-namespace under user). Both apply broadly (memory sidecar, graphify skill) but contain **no project-specific Voss directives**. No constraints to copy here.

The `/Users/benjaminmarks/.claude/CLAUDE.md` "behavioral guidelines" (simplicity-first, surgical changes, goal-driven execution) are author-style preferences — the planner should keep tasks minimal and avoid scope creep beyond CONTEXT decisions.

## User Constraints (from CONTEXT.md)

### Locked Decisions

(verbatim from `.planning/phases/M3-language-validation/M3-CONTEXT.md` `<decisions>` block — D-01 through D-15)

**Hermetic run + check speed**
- **D-01:** `voss run` auto-falls back to `StubProvider` when no real provider creds are detected OR `VOSS_HERMETIC=1` is set. Resolution: re-use `voss_runtime` provider config helpers; if `RuntimeConfig.default_model` resolution returns no live credential, register `__stub__` and use it. Zero-config for CI.
- **D-02:** Every stub fallback prints a stderr banner: `voss: no provider creds detected — using __stub__ (deterministic fake responses)`. Banner fires on every invocation (not throttled). Matches M1 D-13 diagnose-don't-fix posture: loud about what's happening, never silent.
- **D-03:** `voss check` is **static-only**. The semantic-matcher / HF encoder load is moved out of any check-time code path. Analyzer continues to validate `match similar(...)` signatures and emit the match manifest. The encoder instantiates lazily only inside generated Python at `voss run` time. This satisfies the roadmap cross-cutting constraint that "`voss check` should be fast enough to run after edits."
- **D-04:** `voss run` success contract for LANG-10 = **exit 0 + non-empty stdout** under `StubProvider`. Minimal CI-assertable contract. Stronger raw-python parity is a separate per-test assertion in the e2e suite (D-12), not the LANG-10 gate.

**Sample coverage (LANG-02..LANG-08)**
- **D-05:** `samples/support.voss` is extended with `memory.episodic` to recall prior tickets — fits the support-agent narrative (recall past customer interactions). LANG-07 (`memory.episodic`) is satisfied through a runnable sample, not a test-only fixture.
- **D-06:** `samples/research.voss` is extended with `try/catch` wrapping `webSearch(...)` (network call is the natural failure point) and a `use voss.tools` import line. LANG-08's `try/catch` and `use` constructs are exercised by a runnable sample. **(Researcher note: the literal "use voss.tools" string in CONTEXT must compile to actual Voss `use` syntax which uses `::` separators — see open question Q-1 below.)**
- **D-07:** `memory.semantic` and `memory.working` (the other two LANG-07 primitives) are covered by **test-only parser/analyzer/codegen fixtures** under `tests/parser/examples/coverage/`, `tests/analyzer/examples/coverage/`, `tests/codegen/snapshots/coverage/` — not surfaced in user-facing samples. Keeps the three canonical samples readable.
- **D-08:** `prompt` and `@tool` (the rest of LANG-08) remain covered by current samples (`prompt SupportAgent { ... }` in support; `tools: [webSearch]` and the implied `@tool` declaration in research). No changes needed for these constructs.

**Test surface**
- **D-09:** M3 builds the **slimmed legacy phase-06 test plan** under `tests/examples/`: `__init__.py`, `helpers.py`, `test_classify_e2e.py`, `test_support_e2e.py`, `test_research_e2e.py`, `test_cli_matrix.py`, `test_check_speed.py`. Drops the legacy `test_helpers.py` meta-suite (testing the helpers themselves is overkill for v0.1). Drops the legacy `--live` optional path (live verification stays manual per M3 scope).
- **D-10:** Test directory is `tests/examples/` — mirrors the `samples/` directory and matches the legacy plan. Not renamed.
- **D-11:** All e2e tests run hermetically: `StubProvider` registered programmatically; fake encoder / fake index used for `support.voss` semantic-routing tests; `VOSS_HERMETIC=1` set in the test environment so the auto-fallback path is exercised end-to-end. No CI-visible HF model downloads.
- **D-12:** `examples/raw_python/{classify,support,research}.py` are **kept as parity oracles**. Each e2e test runs the generated Python AND the raw-Python equivalent under the same `StubProvider` seed; asserts stdout matches. When sample semantics evolve, the raw-Python equivalent must be updated alongside the `.voss` source as part of the same PR.
- **D-13:** `tests/examples/test_check_speed.py` enforces a **hard wall-clock ceiling per sample** for `voss check`. Target: ≤2s per sample on a stock CI worker (tune during execution).

**Framing surface (LANG-01, LANG-05)**
- **D-14:** Two surfaces carry the framing: **README.md** gains a "What is .voss" section positioning `.voss` as the AI-workflow control layer (probable values, confidence gates, context budgets, semantic routing, agents, memory, fallbacks); explicitly states it is **not** a general Python replacement; links to `samples/` and `docs/voss-vs-python.md`. **Sample headers** — each `samples/*.voss` opens with a comment block naming the AI-workflow primitives it demonstrates.
- **D-15:** `docs/voss-vs-python.md` ships as the explicit "shorter, clearer than equivalent Python" deliverable. Each of the three samples is paired with its `examples/raw_python/` equivalent. Includes per-sample LOC counts and a one-paragraph commentary. README links to it.

### Claude's Discretion

(verbatim)

- Exact phrasing of the README "What is .voss" section and per-sample header comments.
- Exact wall-clock ceiling in `test_check_speed.py` (2s is a starting target; tune during execution).
- The mechanism by which auto-StubProvider detection wires in (env-var probe vs. cred-resolver hook in `voss_runtime/providers/`) — pick the smallest diff; mirror M1 D-09's `auth.resolve(preference="auto")` shape if it fits. **(Researcher: recommend `auth.resolve` — see Pattern 1 below.)**
- Fake encoder + fake index implementation for `support.voss` semantic-routing tests — re-use `voss_runtime` test helpers if any exist; otherwise a deterministic hash-bucket encoder is fine. **(Researcher: the existing `tests/examples/helpers.py:SUPPORT_FAKE_INDEX_SITECUSTOMIZE` already exists and works — keep it.)**
- `RuntimeConfig` default for `__stub__` model name and how it interacts with sample-supplied model annotations (if any).
- Whether the stub-fallback banner is suppressed under `VOSS_QUIET=1`.
- Exact shape of `try/catch` syntax in `research.voss` — must match what `voss/parser.py` already accepts. **(Researcher: confirmed, see "Parser surface" §1 below — both `try { } catch { }` and `try { } catch e { }` are accepted today.)**

### Deferred Ideas (OUT OF SCOPE)

(verbatim)

- A 4th canonical sample showcasing memory.* + try/catch + use end-to-end.
- `memory.semantic` and `memory.working` surfaced in runnable samples.
- Live-provider e2e tests in CI (`pytest -m live`).
- `tests/examples/test_helpers.py` meta-tests on the helpers themselves.
- `voss check --speed-budget=Ns` tunable flag.
- `VOSS_QUIET=1` suppressing the stub-fallback banner (discretion, default off).
- `/analyze` or any `.voss`-authored harness skill — M4.
- Embeddings / semantic index beyond M2's flat `repo.idx`.
- Renaming `tests/examples/` to `tests/language/`.
- Retiring `examples/raw_python/`.
- Broader codegen snapshot tests under `tests/codegen/snapshots/` beyond coverage fixtures (D-07).
- `voss init <template>` AI-workflow template scaffolding.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LANG-01 | `.voss` positioned & implemented as AI workflow control language, not general Python replacement | §"State of the Art" framing surface; D-14 README + sample headers; D-15 `docs/voss-vs-python.md`. README.md currently leads with "Phase 1 status: runtime library shipped" — must be replaced. |
| LANG-02 | Parser/analyzer/codegen preserve `probable<T>` + confidence gates | `voss/analyzer.py:_warn_unguarded_probable` already enforces it (M3 needs only a test fixture under `coverage/` plus the existing `classify.voss` sample). |
| LANG-03 | `ctx(budget: N tokens)` preserved | Grammar.lark:128 (`ctx_stmt`), codegen.py implicit/explicit ContextScope wrapping (codegen.py:1128-1144, _emit_implicit_ctx_let:707). Already exercised by all three samples. |
| LANG-04 | `within budget(...) { } fallback { }` preserved | Grammar.lark:129 (`within_stmt`). `samples/research.voss:33-38` already exercises both arms. |
| LANG-05 | `match similar(...)` preserved | Grammar.lark:117 (`similar_pattern`), analyzer.py:479-501 (`_visit_match_stmt`), codegen.py:1011-1051 (`_emit_similar_match`). `samples/support.voss` exercises it; D-03 fix preserves static analysis. |
| LANG-06 | `agent`, `spawn`, `gather` preserved | Grammar.lark:31 (`spawn_expr`), grammar.lark:161-164 (`agent_decl`), runtime `VossAgent` + `gather` exported (voss_runtime/__init__.py:19). `samples/research.voss:2-20` already exercises all three. |
| LANG-07 | `memory.episodic`, `memory.semantic`, `memory.working` preserved | D-05 runnable sample for `episodic` (samples/support.voss); D-07 test-only fixtures for `semantic` + `working`. Codegen at codegen.py:182-186, 690-705. Runtime classes in voss_runtime/memory/{episodic,semantic,working}.py. Pattern reference: `tests/parser/examples/assistant.voss:2-3`. |
| LANG-08 | `@tool`, `prompt`, `try/catch`, `use` preserved | `@tool` decorator (grammar.lark:151-155, current `samples/research.voss:tools: [webSearch]` already implicit) — D-08 says no change. `prompt SupportAgent` already in `samples/support.voss:2-4`. `try/catch` — D-06 adds to research.voss (grammar.lark:133, parser.py:542-557, codegen.py:1107-1126 all support it today). `use` — D-06 adds to research.voss (grammar.lark:174, parser.py:711-715, codegen.py:126-148 all support it; output is `from voss_runtime import tools`). |
| LANG-09 | `voss check` passes on all three samples | Already passes today (all three exit 0 against current parser/analyzer/codegen). M3 must keep this true after sample extensions land; covered by `tests/examples/test_cli_matrix.py` + `test_check_speed.py`. |
| LANG-10 | At least one sample runs end-to-end via `voss run` | D-04 contract: exit 0 + non-empty stdout. D-01/D-02 auto-StubProvider + banner make this CI-assertable. `tests/examples/test_classify_e2e.py:test_classify_voss_run_matches_compile_python` already exercises this for classify; M3 ensures it passes when env has no creds + `VOSS_HERMETIC=1`. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Source parsing (`try/catch`, `use`, `memory.X`) | Compiler (`voss/parser.py` + `voss/grammar.lark`) | — | Already implemented; M3 verifies, does not extend. |
| Static analysis (confidence gates, match manifests, no encoder load) | Compiler (`voss/analyzer.py`) | — | D-03 fix lives here: gate `build_cases(...)` on `emit_indexes`. |
| Python lowering | Compiler (`voss/codegen.py`) | — | Already lowers all M3 constructs; M3 verifies via snapshots. |
| Auto-StubProvider detection + banner | CLI (`voss/cli.py:run`) | Runtime (`voss_runtime/providers`) | Detection logic lives in CLI; registration helper added to runtime. Mirrors M1 D-09 `auth.resolve` shape. |
| Lazy encoder load | Runtime (`voss_runtime/semantic.py`) | — | Already lazy via `from_index()` constructor (semantic.py:79-94); only `__init__` with no `embeddings` arg eager-loads. Codegen path uses `from_index()` so generated `voss run` is already lazy; check-time bypass is the analyzer fix. |
| Memory primitives | Runtime (`voss_runtime/memory/`) | Codegen lowering | Classes exist; codegen maps `memory.episodic` → `EpisodicMemory()`. |
| E2E test orchestration | Test layer (`tests/examples/`) | CLI subprocess | Hermetic stub via `sitecustomize.py` injection (helpers.py:106-118, 201-229) — already implemented. |
| Sample extension content | Source (`samples/*.voss`, `examples/raw_python/*.py`) | — | Mechanical edits, no logic. |
| Framing docs | Source (`README.md`, `docs/voss-vs-python.md`) | — | Pure documentation. |

## Standard Stack

### Core (already in use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `lark` | >=1.1.9 | Parser generator (Earley + dynamic lexer) [VERIFIED: pyproject.toml:11] | Already drives `voss/grammar.lark` + `voss/parser.py`. M3 adds zero parser rules. |
| `click` | >=8.1.0 | CLI [VERIFIED: pyproject.toml:19] | Already wraps `voss check / run / compile`; banner via `click.echo(err=True)` mirrors existing CLI error path (voss/cli.py:42). |
| `pydantic` | >=2.6,<3.0 | Schemas [VERIFIED: pyproject.toml:13] | Used by analyzer / config. Not extended in M3. |
| `pytest` | >=8.0 | Test runner [VERIFIED: pyproject.toml:25] | `pyproject.toml:39-46` already configures `asyncio_mode = "auto"` and `addopts = "-q --strict-markers"`. M3 plays inside this. |
| `pytest-asyncio` | >=0.23 | Async test support [VERIFIED: pyproject.toml:26] | Already used by integration tests (e.g. `tests/integration/test_classify_example.py:33`). |
| `sentence-transformers` | >=2.7.0 | Optional HF encoder [VERIFIED: pyproject.toml:15] | Stays a runtime dep; D-03 moves load out of check time but keeps it available for `voss run`. |
| `litellm` | >=1.50.0 | Provider abstraction [VERIFIED: pyproject.toml:12] | Default provider (`voss_runtime/providers/litellm_provider.py:1`); auto-fallback skips it when no creds. |

### Supporting (already in place; M3 does not add)
| Library | Purpose | When |
|---------|---------|------|
| `httpx` | OAuth token refresh in harness/auth.py:23 | Unchanged in M3 — M3 reuses the existing resolver, doesn't add network calls. |
| `numpy` (transitive via sentence-transformers) | Fake encoder vectors (tests/examples/helpers.py:121-156) | Already used by existing fake-encoder sitecustomize. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `auth.resolve(preference="auto")` for cred detection | Bare `os.environ.get("ANTHROPIC_API_KEY")` env probe | Probe misses OAuth (Keychain / `~/.claude/.credentials.json` / `~/.codex/auth.json`) and would falsely stub-fallback for OAuth-only users. `auth.resolve` already handles all four sources (harness/auth.py:332-375) and returns a single `source == "none"` signal. Strongly recommend the resolver. |
| Hard-code `VOSS_HERMETIC=1` env-var only | env-var OR cred-resolver | Env-var-only forces CI to set the flag; cred-resolver makes it zero-config. CONTEXT D-01 says "OR" — both paths land, and the resolver is the natural primary because the banner message is true under both. |

**Installation:** No new dependencies. Run `pip install -e ".[dev]"` (already in README.md:9-11).

**Version verification (verified 2026-05-11):** `pyproject.toml:10-21` pins floor versions; no upgrades needed for M3.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌──────────────────────────┐
                     │   samples/{name}.voss    │
                     │   examples/raw_python/   │
                     │   {name}.py (parity)     │
                     └────────────┬─────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
       voss check         voss compile          voss run
   (static, fast)       (.py emitted)        (compile + exec)
              │                   │                   │
              ▼                   ▼                   ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐
   │ parse → analyze  │  │ parse → analyze  │  │ same as compile│
   │ (D-03: NO HF     │  │   → generate     │  │   + subprocess │
   │  load; index     │  │   _python        │  │   exec, with   │
   │  builder skipped │  │  → write to      │  │   D-01 stub    │
   │  unless          │  │  .voss-cache/    │  │   fallback +   │
   │  emit_indexes)   │  │  generated/      │  │   D-02 banner  │
   └────────┬─────────┘  └────────┬─────────┘  └───────┬────────┘
            │                     │                    │
            ▼                     ▼                    ▼
      Diagnostics            Generated Python       stdout (must be
                             imports voss_runtime    non-empty for LANG-10)
                                  │
                                  ▼
                           Runtime: ProbableValue,
                           ContextScope, BudgetScope,
                           SemanticMatcher (lazy, via
                           from_index), VossAgent/gather,
                           EpisodicMemory, tool, StubProvider,
                           LiteLLMProvider

   ┌─────────────────── Hermetic test plane ───────────────────┐
   │                                                            │
   │  tests/examples/helpers.py                                 │
   │    - copy_example(tmp_path, "support")                     │
   │    - run_voss(["check", ...], env=hermetic_env)            │
   │    - deterministic_subprocess_env(tmp_path, default_resp)  │
   │      writes sitecustomize.py registering StubProvider,     │
   │      sets PYTHONPATH, sets VOSS_HERMETIC=1                 │
   │    - SUPPORT_FAKE_INDEX_SITECUSTOMIZE patches              │
   │      SemanticMatcher._encode + _ensure_encoder             │
   │  tests/examples/test_{classify,support,research}_e2e.py    │
   │  tests/examples/test_cli_matrix.py                         │
   │  tests/examples/test_check_speed.py (NEW, D-13)            │
   └────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (deltas from current)
```
samples/
├── classify.voss             # add header comment (D-14)
├── support.voss              # add header + memory.episodic (D-05)
└── research.voss             # add header + try/catch + use (D-06)

examples/raw_python/
├── classify.py               # unchanged
├── support.py                # add EpisodicMemory parity to match D-05
└── research.py               # add try/except parity + import to match D-06

voss/
├── analyzer.py               # FIX: gate index_builder.build_cases on emit_indexes (D-03)
├── cli.py                    # ADD: stub-fallback wiring + banner in `run` (D-01, D-02)
└── (no other compiler changes — parser/codegen already support everything)

voss_runtime/
└── providers/__init__.py     # ADD (optional): helper to "auto-select" __stub__ based on auth.resolve

tests/examples/               # PRE-EXISTS; slim per D-09
├── __init__.py               # keep
├── helpers.py                # keep, re-point copy_example to samples/
├── test_classify_e2e.py      # keep, update source to samples/classify.voss
├── test_support_e2e.py       # keep, add memory.episodic assertions
├── test_research_e2e.py      # keep, add try/catch + use assertions
├── test_cli_matrix.py        # keep
├── test_check_speed.py       # NEW (D-13)
├── test_helpers.py           # DELETE (D-09 drops meta-tests)
└── test_live_examples.py     # DELETE (D-09 drops --live)

tests/parser/examples/coverage/         # NEW (D-07)
├── memory_semantic.voss
└── memory_working.voss
tests/analyzer/examples/coverage/       # NEW (D-07) — matches existing pattern
tests/codegen/snapshots/coverage/       # NEW (D-07) — matches existing pattern

docs/
└── voss-vs-python.md         # NEW (D-15)

README.md                     # rewrite intro: "What is .voss" section (D-14)
```

### Pattern 1: Auto-Stub fallback via `auth.resolve`
**What:** In `voss/cli.py:run` (currently at voss/cli.py:170-201), before invoking `subprocess.run([sys.executable, generated])`, detect creds via the existing harness resolver and override the runtime config when no live cred is available.
**When to use:** Every `voss run` invocation. Detection is cheap (env-var + filesystem checks; no network).
**Example:**
```python
# voss/cli.py:run — sketch
# Source: pattern from voss/harness/cli.py:38-77; resolver at voss/harness/auth.py:332-375
import os
from voss.harness import auth as auth_mod

def run(source, cache_dir, project_root, verbose):
    hermetic = os.environ.get("VOSS_HERMETIC") == "1"
    res = auth_mod.resolve(preference="auto")
    if hermetic or res.source == "none":
        click.echo(
            "voss: no provider creds detected — using __stub__ "
            "(deterministic fake responses)",
            err=True,
        )
        # Two-step: configure runtime + ensure subprocess sees it.
        # subprocess inherits env, so we set the env that the generated
        # Python will read at import time:
        env = os.environ.copy()
        env["VOSS_HERMETIC"] = "1"  # generated runtime reads this
        # ...then pass `env=env` to subprocess.run
    else:
        env = None  # inherit unchanged
    # ... existing compile + subprocess.run flow ...
```
Generated runtime side: `voss_runtime._config` (or `voss_runtime.providers.get`) reads `VOSS_HERMETIC=1` on first call and routes `default_model` to `__stub__`. The simplest landing is to add a one-shot check inside `voss_runtime/providers/__init__.py:get()` (line 12-18) that bumps to `__stub__` when the env var is set; this leaves the rest of the codebase untouched.

### Pattern 2: Static-only check (D-03)
**What:** Skip `index_builder.build_cases(...)` (and therefore `SemanticMatcher.__init__`'s eager `_encode` call) when `emit_indexes=False` (analyzer.py:204-211, 435).
**When to use:** Every code path that calls `analyze(..., emit_indexes=False)` — today only `voss/cli.py:check` (cli.py:218-224).
**Example:**
```python
# voss/analyzer.py:_visit_match_stmt (current code at 479-501)
def _visit_match_stmt(self, match: MatchStmt) -> None:
    self._infer_expr(match.scrutinee)
    similar_pairs: list[tuple[str, str]] = []
    for ordinal, case in enumerate(match.cases):
        if isinstance(case.pattern, SimilarPattern):
            label = f"case_{ordinal}"
            similar_pairs.append((case.pattern.text, label))
        for s in case.body:
            self._visit_stmt(s)
    if not similar_pairs:
        return
    # D-03 fix: when indexes will not be emitted, do not encode.
    # Manifest is the only consumer of build_cases output and only emit_indexes
    # writes the manifest (see _emit_program_index call at line 435).
    if not self.emit_indexes:
        self._match_entries.append({
            "match_id": f"match_{match.span.line_start}_{match.span.col_start}",
            "threshold": match.threshold if match.threshold is not None else 0.75,
            "cases": [],   # static-only: no embeddings computed
        })
        return
    # ... existing path (emit_indexes=True) — unchanged
    if self.index_builder is None:
        self.index_builder = SemanticMatcherIndexBuilder()
    built = self.index_builder.build_cases(similar_pairs)
    # ...
```
The "static signature validation" CONTEXT D-03 promises (`analyzer continues to validate match similar(...) signatures`) is the pattern walk + scrutinee inference above — those still run. Only the **embedding computation** is gated.

### Pattern 3: Hermetic e2e via PYTHONPATH-prepended sitecustomize
**What:** Generate a temp `sitecustomize.py` that registers `StubProvider` + (optionally) patches `SemanticMatcher._encode`, then run `voss run` with `PYTHONPATH` prepended.
**When to use:** Every `tests/examples/test_*_e2e.py` and `test_cli_matrix.py` subprocess invocation.
**Example:** Already implemented at `tests/examples/helpers.py:106-118, 121-158, 201-229`. **No changes required for the helper itself.** Only changes: `helpers.example_source` (helpers.py:23, 26-31) and `copy_example` (helpers.py:34-39) need to look at `samples/` not `tests/parser/examples/`.

### Pattern 4: Sample header comment (D-14)
**What:** Each `samples/*.voss` opens with a top-of-file `#` comment block naming the primitives it demonstrates.
**Example:**
```voss
# classify.voss
# Demonstrates: probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.
fn classifyIntent(input: string) -> string {
    let intent: probable<string> = ask("Classify the intent: " + input)
    if intent @ p >= 0.80 {
        return intent.value
    } else {
        return "unknown"
    }
}
let result = classifyIntent("I want to cancel my subscription")
print(result)
```
Comment syntax is `#` (grammar.lark:215, `COMMENT: /\#[^\n]*/`). The existing samples already lead with `# classify.voss` etc., so this is appending a second line per sample.

### Anti-Patterns to Avoid
- **Re-running parser-level golden tests inside `tests/examples/`** — duplicates `tests/parser/test_examples.py`. The e2e suite must test the **runtime/CLI** behavior, not the AST.
- **Embedding model selection inside `voss check`** — `_default_local_model()` (analyzer.py:166-169) imports `DEFAULT_LOCAL_MODEL` from `voss_runtime.semantic`. After D-03, the model name should never be looked up at check time. Verify by importing `voss_runtime.semantic` in a check-only test and asserting the encoder attribute is unset.
- **Hard-coded `__stub__` model name in samples** — CONTEXT D-01 says the auto-fallback decides this at runtime. Samples must not pin a model.
- **Using `cat << 'EOF' > file.voss` in plans** — repo style is text edits via tooling, never heredoc in shell.
- **Adding new optional dependencies for the fake encoder** — `tests/examples/helpers.py:121-158` already builds a working fake using stdlib + numpy (already transitively present). Do not introduce a new package.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detect "should we use stub vs live provider?" | New `_detect_creds()` env-var/file probe | `voss.harness.auth.resolve(preference="auto")` returning `source == "none"` (harness/auth.py:332-375) | Already handles env vars, Anthropic Keychain, `~/.claude/.credentials.json`, `~/.codex/auth.json`. Single source of truth shared with M1. |
| Register a fake provider for tests | Subclass `LiteLLMProvider` | `StubProvider` from `voss_runtime.providers.stub` (registered as `__stub__` at module import: providers/__init__.py:22) | Already deterministic with prompt-fingerprint lookup (stub.py:28-30), `pydantic`-aware `response_format` parsing (stub.py:56-59). Used by every integration test. |
| Patch out sentence-transformers in tests | Mock the import / monkeypatch in each test | `tests/examples/helpers.py:install_support_fake_encoder_in_process` + `SUPPORT_FAKE_INDEX_SITECUSTOMIZE` (helpers.py:121-198) | Drop-in 3-D vector encoder + fake `IndexBuilder` already in tree. |
| Wrap subprocess CLI invocations | `os.system()` or `subprocess.Popen()` directly | `tests/examples/helpers.py:run_voss` (helpers.py:60-69) which routes to `python -m voss.cli` | Captures stdout/stderr/returncode uniformly; already used by all e2e tests. |
| Build a parity oracle for codegen output | Snapshot the generated `.py` | `examples/raw_python/{name}.py` already exists and is a hand-written parity target. Test asserts `voss run` stdout == raw-python stdout under same `StubProvider`. | One artifact, two roles — also doubles as LANG-03 "readable Python" reference per CONTEXT D-12. |
| Re-implement memory primitives in samples | Pure Python class definitions | `voss_runtime.EpisodicMemory` / `SemanticMemory` / `WorkingMemory` (exported voss_runtime/__init__.py:21, 38, 46, 51) | Already public API; codegen at codegen.py:182-186, 690-705 maps `memory.episodic(capacity: 20 turns)` → `EpisodicMemory(capacity=20)`. |
| Build a check-time speed harness | `pytest-benchmark`, statistical sampling | `time.perf_counter()` + a hard `assert elapsed < CEILING` | D-13 says hard ceiling, not p99 / distribution. Simplest pattern that catches regressions. The repo has `.benchmarks/` but no benchmark tests currently in use; mirror legacy `tests/cli/` style. |

**Key insight:** M3 has near-zero novel infrastructure. Every "how should we do X" question already has an answer in the codebase. The planner's job is sequencing + scoping, not designing.

## Runtime State Inventory

> This phase IS a refactor/sample-extension phase. Required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `.voss-cache/{stem}.idx` JSON manifests from prior `voss check` / `voss compile` runs (analyzer.py:679-708). If they were emitted with current eager encoder, they contain real embeddings. After D-03, fresh `voss check` (which uses `emit_indexes=False`) won't touch them. `voss compile` (which uses `emit_indexes=True`) still emits real embeddings. | **None** — existing manifests stay valid because compile path is unchanged. Tests use `tmp_path/.voss-cache/`, never repo-local. |
| Live service config | None — Voss has no external services it registers with. | None. |
| OS-registered state | None — no launchd, no Task Scheduler, no pm2, no systemd. | None. |
| Secrets / env vars | `VOSS_HERMETIC` (new, M3 reads it) — opt-in env var, set in CI test env (D-11). `VOSS_TEST_STUB_RESPONSE` (existing, tests/examples/helpers.py:228) — already used by the sitecustomize injection. `VOSS_NO_KEYCHAIN_WRITE` (existing, harness/auth.py:144) — unchanged. `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — unchanged. | M3 documents `VOSS_HERMETIC=1` in README + the new banner message references it implicitly. No secrets renamed. |
| Build artifacts / installed packages | `voss.egg-info/` is the installed-package metadata (verified by `ls voss.egg-info/` in cwd). The `pyproject.toml:32-33` `[project.scripts] voss = "voss.cli:main"` entry-point is unchanged in M3, so no reinstall required. `tests/examples/__pycache__/` will contain stale bytecode for the deleted `test_helpers.py` / `test_live_examples.py` — pytest handles this fine but a `find tests/examples -name __pycache__ -exec rm -r {} +` is a clean step. | **None blocking.** Optional: clear stale `__pycache__` when deleting `test_helpers.py` + `test_live_examples.py`. |

**Renames / string-replacements in this phase:** None. M3 adds content; it does not rename existing files/modules/symbols.

## Common Pitfalls

### Pitfall 1: "use voss.tools" (CONTEXT D-06 wording) does not parse — must be `use voss_runtime::tools`
**What goes wrong:** Implementer reads CONTEXT D-06 literally and writes `use voss.tools` in `samples/research.voss`. Parser rejects: `use_path` rule (grammar.lark:175) uses `::` separator, not `.`. Period-separated paths are reserved for type expressions (qual_name, grammar.lark:18). Additionally, `voss` is not a runnable Python package (it is the compiler) — at runtime `from voss import tools` would import the compiler. The runtime module is `voss_runtime`.
**Why it happens:** CONTEXT wording is shorthand; the literal token form was not resolved during discuss.
**How to avoid:** Plan task must explicitly write `use voss_runtime::tools` (which compiles to `from voss_runtime import tools` per codegen.py:142-148 + test_imports.py:71-77) OR `use voss_runtime::tools::tool` (which compiles to `from voss_runtime.tools import tool`). Either form parses; pick the one that gives the sample a useful import. **Recommended:** `use voss_runtime::tools::tool` so the sample can later annotate a `@tool fn` block if desired — but for M3, since the existing sample uses `tools: [webSearch]` inside the agent body and references `webSearch` as a bare name, the import is largely cosmetic (CONTEXT D-06 lists it as a LANG-08 surface coverage item, not a behavioral change).
**Warning signs:** `voss check samples/research.voss` exits non-zero with a parser error pointing at `.` after `voss`.

### Pitfall 2: `voss check` still slow after the D-03 fix because the encoder loads at import time somewhere else
**What goes wrong:** `voss/analyzer.py:166-169` (`_default_local_model`) imports `from voss_runtime.semantic import DEFAULT_LOCAL_MODEL`. The import itself is cheap; the eager encoder load is inside `SemanticMatcher.__init__` (semantic.py:43). But: if any other import chain triggers `SemanticMatcher(...)` at module load, the fix is incomplete.
**Why it happens:** Easy to miss the call site at analyzer.py:181-184 (`SemanticMatcherIndexBuilder.build_cases`).
**How to avoid:** After the fix lands, the speed test (`tests/examples/test_check_speed.py`) is the regression gate. Additionally, a sentinel assertion: inside the test, `import voss; from voss_runtime import semantic; assert semantic.SemanticMatcher._encoder is None` after a `voss check` against `samples/support.voss` — proves the encoder never instantiated.
**Warning signs:** Wall-clock for `voss check samples/support.voss` warm > 1.5s after fix.

### Pitfall 3: StubProvider fallback fires under real-cred users running tests locally
**What goes wrong:** Developer has `ANTHROPIC_API_KEY` set in shell. Runs `pytest tests/examples/ -q`. Tests pass but exercised live providers because the sitecustomize set `default_model="__stub__"` only in the child subprocess, not the in-process raw-python parity oracle.
**Why it happens:** The hermetic env injection (helpers.py:201-229) only affects subprocess. In-process tests (test_support_e2e.py:115-152 `_compile_research_in_process` and the raw_python parity oracle imports) run inside the test's own Python interpreter.
**How to avoid:** Already mitigated: `register_stub` context manager (helpers.py:94-103) configures the in-process runtime to `__stub__`. M3 verifies every parity-oracle path uses `register_stub(...)` BEFORE the in-process raw-python call. Lint: `grep -L "register_stub" tests/examples/test_*_e2e.py` should return no matches.
**Warning signs:** Test pass time correlates with network latency; provider error noise in test output when offline.

### Pitfall 4: `tests/examples/copy_example` copies from `tests/parser/examples/` not `samples/`
**What goes wrong:** Test passes on the old `tests/parser/examples/support.voss` (23 LOC, no memory.episodic) while the actual `samples/support.voss` ships the extension. Two divergent canonical sources; the M3 sample extension goes unvalidated by the e2e suite.
**Why it happens:** The existing legacy-phase-06 helpers.py was authored when `samples/` was an empty placeholder per the legacy research doc. Today `samples/` contains the canonical user-facing demos.
**How to avoid:** Plan must include a task to repoint `helpers.py:PARSER_EXAMPLES` (helpers.py:23) to a new `SAMPLES_DIR = REPO_ROOT / "samples"` constant and update `example_source` (helpers.py:26-31) and `copy_example` (helpers.py:34-39) to use it. The parser golden tests at `tests/parser/test_examples.py` remain on `tests/parser/examples/` — they are AST snapshot tests, not behavior tests.
**Warning signs:** `tests/examples/test_support_e2e.py` passes but neither tmp_path/support.voss nor the compiled output contains `memory.episodic`.

### Pitfall 5: Banner duplicated or suppressed by CliRunner
**What goes wrong:** `click.echo(..., err=True)` works at the terminal but Click's `CliRunner` (used by every CLI test) routes stderr separately. The banner shows up in `result.stderr` not `result.output`. Tests that grep `result.output` for the banner will miss it.
**Why it happens:** Click's mix_stderr default behavior; `tests/cli/test_check.py:31` etc. read `result.output`.
**How to avoid:** Assertion in `test_cli_matrix.py` (or a dedicated `test_run_stub_fallback_banner.py`) uses `result.stderr`. Subprocess tests (`run_voss(...)` in helpers.py:60-69) already use `capture_output=True, text=True` and `subprocess.CompletedProcess.stderr` — so they see the banner naturally.
**Warning signs:** Banner never appears in assertion despite tests passing.

### Pitfall 6: `voss check` on support.voss leaves the encoder loaded into Python's import graph
**What goes wrong:** Even with D-03 in place, importing `voss_runtime` (which `voss/analyzer.py` does for `DEFAULT_LOCAL_MODEL`) may pull in `voss_runtime.semantic`. That import itself does NOT load the model (semantic.py:11-14 — `_numpy()` is lazy; `SemanticMatcher.__init__` is the only model-load site, and it's not called). Confirmed by reading semantic.py.
**Why it happens:** False alarm — included so the planner doesn't accidentally over-engineer.
**How to avoid:** None needed. The fix scope is exactly `_visit_match_stmt`.

### Pitfall 7: `examples/raw_python/` parity files drift from sample semantics
**What goes wrong:** D-05 extends `samples/support.voss` with `memory.episodic` but `examples/raw_python/support.py:1-39` is not updated to use `EpisodicMemory`. Per D-12, the e2e parity assertion fails (`generated stdout != raw stdout`).
**Why it happens:** D-12 explicitly calls this out: "When sample semantics evolve, the raw-Python equivalent must be updated alongside the `.voss` source as part of the same PR."
**How to avoid:** Each sample-extension task in the plan MUST bundle the matching `examples/raw_python/*.py` edit in the same task; no separate "update parity later" tasks.
**Warning signs:** `tests/examples/test_support_e2e.py` assertion `generated_value == raw_value` fails after the sample extension lands.

## Code Examples

### Pattern: extend `samples/support.voss` with `memory.episodic` (D-05)
```voss
# samples/support.voss
# Demonstrates: prompt block, match similar (semantic routing),
# ctx(budget: N tokens), memory.episodic.
# Source: PRD §7.2 base + D-05 episodic extension.
prompt SupportAgent {
    "You are a customer support agent for a SaaS product. Be empathetic and clear."
}

let tickets: memory.episodic(capacity: 50 turns)

fn handleMessage(userMessage: string) -> string {
    tickets.add(userMessage, role: "user")
    match userMessage {
        case similar("angry, frustrated, or upset customer") => {
            return escalate(userMessage)
        }
        case similar("refund, money back, cancel subscription") => {
            return refundFlow(userMessage)
        }
        case similar("can't log in, password reset, account locked") => {
            return authSupport(userMessage)
        }
        case _ => {
            ctx(budget: 3000 tokens) {
                include tickets.last(6)
                yield ask(userMessage)
            }
        }
    }
}
```
Codegen lowering (verified by hand against codegen.py:690-705 + EpisodicMemory at voss_runtime/memory/episodic.py:33-37):
```python
# Generated equivalent (approximate; codegen produces async-main wrapper)
from voss_runtime import ContextScope, EpisodicMemory, SemanticMatcher
SUPPORT_AGENT_PROMPT = "You are a customer support agent for a SaaS product..."
tickets = EpisodicMemory(capacity=50)
# ... matcher loaded via SemanticMatcher.from_index(...) at first use ...
async def handleMessage(userMessage: str):
    tickets.add(userMessage, role="user")
    # match dispatched against tickets...
    # case _: under ctx(budget=3000), include tickets.last(6)
```

### Pattern: extend `samples/research.voss` with `try/catch` + `use` (D-06)
```voss
# samples/research.voss
# Demonstrates: agent, spawn, gather, ctx(budget: N tokens),
# within budget(...) fallback, try/catch, use.
use voss_runtime::tools::tool

agent Researcher(topic: string) -> string {
    system: "You are a research analyst. Summarize key findings concisely."
    tools: [webSearch]

    ctx(budget: 2000 tokens) {
        try {
            let results = webSearch(topic, max_results: 5)
            include results
        } catch e {
            include "web search unavailable"
        }
        yield ask("Summarize the key findings on: " + topic)
    }
}

agent Synthesizer(reports: list<string>) -> string {
    system: "You synthesize research into executive summaries."
    ctx(budget: 4000 tokens) {
        include reports
        yield ask("Write a unified executive summary of these research reports.")
    }
}

fn runResearch(company: string) -> string {
    let topics = [
        company + " market position",
        company + " recent news",
        company + " competitors",
        company + " financials"
    ]
    let researchers = topics.map(t => spawn Researcher(t))
    let reports: list<string> = gather(researchers, timeout: 60s)
    within budget(tokens: 5000, latency: 10s) {
        let synth = spawn Synthesizer(reports)
        return gather([synth])[0]
    } fallback {
        return reports.join("\n---\n")
    }
}
print(runResearch("Anthropic"))
```
Validation: parser (grammar.lark:133 + 174-175 + parser.py:542-557, 711-715) accepts it; codegen (codegen.py:1107-1126, 126-148) lowers it; `examples/raw_python/research.py:54-60` already has the matching `try/except BudgetExceededError` parity skeleton — the new `try { webSearch } catch` adds a second `try/except` around the search call.

### Pattern: `tests/examples/test_check_speed.py` (D-13, NEW)
```python
# Source: pattern from tests/cli/test_check.py + time.perf_counter idiom
from __future__ import annotations
import time
from pathlib import Path
import pytest
from tests.examples.helpers import copy_example, run_voss

# Hard wall-clock ceiling (D-13). Start at 2s; tune during execution if needed.
CHECK_CEILING_SECONDS = 2.0

@pytest.mark.parametrize("sample", ["classify", "support", "research"])
def test_check_speed_under_ceiling(tmp_path: Path, sample: str):
    copy_example(tmp_path, sample)
    # Warmup once so first-import overhead doesn't dominate.
    run_voss(["check", f"{sample}.voss"], cwd=tmp_path)
    start = time.perf_counter()
    result = run_voss(["check", f"{sample}.voss"], cwd=tmp_path)
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < CHECK_CEILING_SECONDS, (
        f"voss check {sample}.voss took {elapsed:.2f}s "
        f"(ceiling {CHECK_CEILING_SECONDS}s) — D-03 regression?"
    )

def test_check_does_not_load_hf_encoder(tmp_path: Path):
    """Sentinel: after voss check on support.voss, the encoder must be unloaded.

    Runs in-process (not subprocess) so we can inspect SemanticMatcher state.
    """
    from voss import analyze, parse
    from voss_runtime import semantic as voss_semantic
    src = (Path(__file__).resolve().parents[2] / "samples" / "support.voss").read_text()
    program = parse(src, file="samples/support.voss")
    # emit_indexes=False is the check-time call shape (cli.py:218-224).
    result = analyze(
        program,
        source_path="samples/support.voss",
        emit_indexes=False,
    )
    assert result.ok
    # D-03 invariant: no SemanticMatcher instantiated -> no encoder anywhere.
    # (SemanticMatcher class-level _encoder slot is unset; we test the absence
    # of a sentence_transformers import on demand.)
    import sys
    assert "sentence_transformers" not in sys.modules, (
        "D-03 violated: HF sentence_transformers loaded during voss check"
    )
```

### Pattern: parser/analyzer/codegen coverage fixtures for `memory.semantic` / `memory.working` (D-07)
Mirror `tests/parser/examples/assistant.voss:1-18` pattern:
```voss
# tests/parser/examples/coverage/memory_semantic.voss
let kb: memory.semantic(source: "./knowledge_base/")
fn lookup(q: string) -> list<string> {
    return kb.retrieve(q, top_k: 3)
}
```
```voss
# tests/parser/examples/coverage/memory_working.voss
let scratchpad: memory.working(capacity: 8)
fn note(content: string) {
    scratchpad.add(content)
}
```
Then mirror `tests/parser/test_examples.py:5-24` to parametrize over the coverage dir; mirror `tests/analyzer/test_examples.py` (already in tree per RESEARCH 06-RESEARCH.md:37) for analyzer; codegen snapshot test follows existing `tests/codegen/test_examples.py` shape.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `voss check` eagerly loads HF sentence-transformers | Static-only check; encoder load deferred to `voss run` | M3 (D-03) | Check speed: ~13s cold / ~9s warm → ~1.5s warm. Makes "fast enough to run after edits" (ROADMAP cross-cutting constraint) real. |
| Tests source `.voss` from `tests/parser/examples/` | Tests source from `samples/` (where canonical demos live) | M3 (D-10 + repoint) | Sample extensions get validated by the e2e suite. |
| Legacy phase-06 plan had `--live` opt-in + `test_helpers.py` meta-tests | Hermetic-only; helpers tested implicitly by the e2e suite | M3 (D-09) | Smaller test surface; CI never needs live creds. |
| `voss run` errored when no creds (litellm raised inside generated code) | Auto-falls back to `StubProvider` with banner | M3 (D-01 + D-02) | `voss run samples/X.voss` works zero-config; LANG-10 contract becomes CI-assertable. |
| README leads with "Phase 1 status: runtime library shipped" + Python framing | README leads with "What is .voss" AI-workflow framing | M3 (D-14) | Aligns docs with scope-lock positioning. |
| No side-by-side `.voss` vs raw-Python doc | `docs/voss-vs-python.md` with LOC counts + commentary | M3 (D-15) | Concrete deliverable for ROADMAP success criterion 5. |

**Deprecated / outdated (do not chase):**
- The "Phase 1 status" README banner — replaced by D-14 framing.
- The legacy `06-RESEARCH.md:50-52` "Phase 5 CLI is absent" / "Phase 4 codegen can't emit runnable Python" gaps — closed by current M1 work. `voss/cli.py` exists, codegen emits full Python.
- The legacy `06-01-PLAN.md:97-101` `phase5-cli-contract-ok` marker dependency — irrelevant in the M-prefixed roadmap.
- `tests/integration/test_{classify,support,research}_example.py` (May 7) — pre-M3 integration tests covering raw-Python only. They still pass and are not in scope to remove, but M3's e2e suite supersedes them for the generated-Python path. Keep as raw-Python regression coverage.

## Assumptions Log

> All factual claims about parser/analyzer/codegen/runtime behavior were verified by reading the source at the cited file:line locations. The HF model load timing was verified by running `time python3 -m voss.cli check samples/support.voss` (warm: 8.9s; cold: 13s) on the local machine.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CI runner speed roughly matches local (M2 MacBook). 2s ceiling is realistic after D-03. | D-13 / Pitfall 2 | Test flakes on slow CI; ceiling is tunable per D-13 ("tune during execution if CI worker variance demands a higher number — keep it a real gate either way"). |
| A2 | The `use voss_runtime::tools::tool` form is semantically meaningful and the codegen output (`from voss_runtime.tools import tool`) imports a valid name. | Pitfall 1, Code example for research.voss | Verified: `voss_runtime/tools.py:54-58` exports `tool`. Import statement is real. |
| A3 | Generated Python's `voss run` already exercises the lazy-encoder path (`SemanticMatcher.from_index`) — only `voss check` was eager. | Summary, Pattern 2 | [VERIFIED: codegen.py:1020-1051 `_emit_similar_match`] — codegen emits `SemanticMatcher.from_index(<idx>)` for runtime, which bypasses the eager-encode `__init__`. Confirmed by reading semantic.py:79-94. |

Two of the three remaining "assumed" framing items (A1, A2) were verified during research. A1 is the only true assumption; documented as a tuning knob in D-13.

## Open Questions

1. **Q-1: `use voss_runtime::tools` vs. `use voss_runtime::tools::tool` in `samples/research.voss`?**
   - What we know: Both parse; first compiles to `from voss_runtime import tools` (module import); second compiles to `from voss_runtime.tools import tool` (name import).
   - What's unclear: Which one is more "demonstrative" for LANG-08 coverage? Both exercise the `use` construct.
   - Recommendation: `use voss_runtime::tools::tool` because (a) the generated import is concretely useful — `tool` is a real decorator; (b) it exercises three-segment paths which is the more interesting parser case (codegen.py:142-145 splits on the last segment).

2. **Q-2: Where exactly does `voss_runtime` read `VOSS_HERMETIC=1` to flip the default provider?**
   - What we know: `voss_runtime/providers/__init__.py:12-18` (`get` function) is the dispatch point. Today it reads `get_config().default_model`. The cleanest landing is a small change there: if `os.environ.get("VOSS_HERMETIC") == "1"`, return the `__stub__` provider regardless of `default_model`. Alternative: bump `default_model` to `__stub__` at `voss_runtime/_config.py` import time when the env var is set.
   - What's unclear: Whether configure(default_model="__stub__") inside generated Python (no env-var dance) is preferable. CONTEXT D-01 leaves this to "Claude's Discretion."
   - Recommendation: Smallest-diff path is to add the env-var check inside `providers.get` (one-line conditional). Keep `voss_runtime._config.RuntimeConfig.default_model` untouched so test code that explicitly configures a model still wins.

3. **Q-3: Should the speed test include cold (first-invocation) timing or warm-only?**
   - What we know: Warm classify/research already at ~1.4s; warm support at ~8.9s (D-03 violation). Cold is dominated by import overhead and HF download — unrepresentative of post-D-03 reality.
   - What's unclear: Whether to assert against a single cold run or warm-only.
   - Recommendation: Warm-only with one pre-run warmup invocation in the test (see code example above). Document in test docstring that "cold start" is a separate concern owned by `voss doctor` (M1 D-13 surface, not M3).

4. **Q-4: Should samples include a `model:` annotation on agents, or omit it (letting RuntimeConfig.default_model decide)?**
   - What we know: `agent_decl` grammar (grammar.lark:161-164) supports `model: <expr>`. Current `samples/research.voss:3-19` omits `model:`; current `samples/support.voss:2-4` (prompt, not agent) doesn't apply. Omitting lets the auto-stub fallback work — pinning a model would force CI to pre-register that name.
   - What's unclear: Nothing — recommendation is firm.
   - Recommendation: Do NOT add `model:` annotations to any sample in M3. CONTEXT D-01 zero-config CI behavior requires this.

5. **Q-5: Where does `docs/voss-vs-python.md` live in the link hierarchy?**
   - What we know: `docs/` does not currently exist. README.md has a "Project Docs" section (README.md:60-65) listing `.planning/*` and `PRD.md`.
   - What's unclear: Whether to add a top-level "Compare" link in README or put it under "Project Docs."
   - Recommendation: Inline the link in the new "What is .voss" section (highest-traffic placement) AND keep a reference under "Project Docs." Two links to one doc.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.13.x (`which python3` → `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`); pyproject requires >= 3.11 (pyproject.toml:9) | — |
| pip-installed `voss` (editable) | All | ✓ | `voss.egg-info/` present in cwd | — |
| `lark` | Parser | ✓ | (transitive, pinned >=1.1.9) | — |
| `click` | CLI | ✓ | (transitive, pinned >=8.1.0) | — |
| `pytest` + `pytest-asyncio` | Tests | ✓ | dev extra (pyproject.toml:25-26) | — |
| `sentence-transformers` (HF) | `voss run` of `match similar` samples | ✓ | Loaded during measurement; HF cache present on local. CI does NOT pre-cache. | After D-03, `voss check` never needs it. `voss run` needs it but the e2e suite patches it out via `SUPPORT_FAKE_INDEX_SITECUSTOMIZE` (helpers.py:121-158). Production users with no HF cache hit first-run download. |
| `litellm` | Live provider | ✓ | pinned >=1.50.0 | StubProvider via D-01 |
| `numpy` | Fake encoder vectors | ✓ | Transitive via sentence-transformers | — |
| `git` | none (M3 doesn't shell out to git) | n/a | n/a | n/a |
| `claude` / `codex` OAuth on disk | None — M3 doesn't require live creds | n/a | n/a | StubProvider |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Live-provider runs (out of M3 scope per D-09 dropping `--live`).

## Validation Architecture

> Workflow `nyquist_validation: true` (config.json:19); section required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x (auto mode) [VERIFIED: pyproject.toml:25-26, 39-46] |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]` block at line 39) |
| Quick run command | `pytest tests/examples -q` |
| Per-test run | `pytest tests/examples/test_check_speed.py -q` |
| Full M3 suite | `pytest tests/examples tests/parser tests/analyzer tests/codegen tests/cli -q -m "not live"` |
| Subprocess CLI | `python -m voss.cli {check|compile|run} ...` (helpers.py:60-69) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LANG-01 | `.voss` framing in README + sample headers + docs/voss-vs-python.md | manual / grep | `grep -F "AI workflow control" README.md && test -f docs/voss-vs-python.md` | README.md ✓ (rewrite); docs/voss-vs-python.md ❌ Wave 0 |
| LANG-02 | `probable<T>` + confidence gate preserved | unit | `pytest tests/analyzer/test_examples.py -q` (existing) + `pytest tests/examples/test_classify_e2e.py -q` | Existing ✓ + tests/examples/test_classify_e2e.py ✓ |
| LANG-03 | `ctx(budget:)` preserved | unit / e2e | `pytest tests/codegen/ -q -k ctx` + `pytest tests/examples/ -q` | Existing ✓ |
| LANG-04 | `within budget fallback` preserved | unit / e2e | `pytest tests/codegen/ -q -k within` + `pytest tests/examples/test_research_e2e.py::test_research_timeout_fallback_matches_raw -q` | Existing ✓ |
| LANG-05 | `match similar` preserved (static-only at check) | unit / e2e | `pytest tests/examples/test_support_e2e.py -q` + `pytest tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder -q` | tests/examples/test_support_e2e.py ✓; test_check_speed.py ❌ Wave 0 |
| LANG-06 | `agent`/`spawn`/`gather` preserved | e2e | `pytest tests/examples/test_research_e2e.py -q` | ✓ |
| LANG-07 | `memory.episodic` (runnable) + semantic/working (fixtures) | e2e + fixture | `pytest tests/examples/test_support_e2e.py -q` + `pytest tests/parser/test_examples.py -q -k coverage` + `pytest tests/codegen/ -q -k coverage` | test_support_e2e.py ✓ (update for memory); coverage fixtures ❌ Wave 0 |
| LANG-08 | `@tool`/`prompt`/`try/catch`/`use` preserved | e2e | `pytest tests/examples/test_research_e2e.py -q` (post-D-06 extension) | ✓ (update) |
| LANG-09 | All three samples pass `voss check` | integration | `pytest tests/examples/test_cli_matrix.py -q` (existing) | ✓ |
| LANG-10 | At least one sample runs `voss run` to exit 0 + non-empty stdout | integration | `pytest tests/examples/test_classify_e2e.py::test_classify_voss_run_matches_compile_python -q` | ✓ (already covers contract; CONTEXT D-04 contract = exit 0 + non-empty stdout; existing test asserts both) |
| D-01 banner | Stderr banner on no-cred run | unit | `pytest tests/cli/ -q -k stub_fallback` (NEW) | ❌ Wave 0 |
| D-03 static check | `voss check` does not load HF model | unit + speed | `pytest tests/examples/test_check_speed.py -q` (NEW) | ❌ Wave 0 |
| D-13 speed gate | Per-sample wall-clock ≤ 2s | speed | `pytest tests/examples/test_check_speed.py -q` (NEW) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/examples -q` (~30-60s once D-03 lands; currently dominated by the 13s cold HF load — that's why D-03 is Wave 0).
- **Per wave merge:** `pytest tests/examples tests/parser tests/analyzer tests/codegen tests/cli -q -m "not live"`.
- **Phase gate (`/gsd-verify-work`):** Full suite green + `voss --help` works + `time python3 -m voss.cli check samples/{classify,support,research}.voss` each report <2s.

### Wave 0 Gaps
- [ ] `tests/examples/test_check_speed.py` — D-13 + LANG-05 sentinel for D-03.
- [ ] `tests/cli/test_run_stub_fallback.py` (or extension to existing `test_run.py`) — D-01 + D-02 banner assertion.
- [ ] `tests/parser/examples/coverage/memory_semantic.voss`, `tests/parser/examples/coverage/memory_working.voss` — D-07 fixtures.
- [ ] `tests/analyzer/examples/coverage/` mirror fixtures + parametrized test runner if not auto-discovered.
- [ ] `tests/codegen/snapshots/coverage/` mirror fixtures.
- [ ] `docs/voss-vs-python.md` — D-15 deliverable.
- [ ] **Delete:** `tests/examples/test_helpers.py` + `tests/examples/test_live_examples.py` per D-09.

*(No framework install needed — pytest + pytest-asyncio already pinned in `[project.optional-dependencies].dev` at pyproject.toml:25-26.)*

## Security Domain

> `security_enforcement` is not present in `.planning/config.json`; treating as enabled by default. Note: M3 surface area is **content + read-only check-path optimization + opt-in stub provider**. No new ingress, no new persistence, no new secrets.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (delegated to M1 `harness/auth.py`) | M3 reuses `auth.resolve(preference="auto")` read-only. |
| V3 Session Management | No | M3 doesn't touch sessions. M1/M2 own these. |
| V4 Access Control | Partial | Path-jail invariant: tests must write only under `tmp_path`, not repo root. `tests/examples/helpers.py:72-82` already enforces `assert_no_repo_cache_artifacts()`. |
| V5 Input Validation | Partial | Sample sources are static text; parser already validates. No new user-supplied input surface. |
| V6 Cryptography | No | None used. |
| V14 Configuration | Yes | `VOSS_HERMETIC` env var must not be enabled silently in production. The banner (D-02) is the user-visible signal. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Generated `.py` writes outside `.voss-cache` | Tampering | `codegen._resolve_cache_root` (codegen.py:218-235) refuses non-`.voss-cache` paths — already enforced. |
| `use foo::bar` resolves to a path outside `voss_runtime` and imports arbitrary code | Tampering / RCE | `ImportCollector.add_use` (codegen.py:126-131) writes a literal `from <path> import <name>` line; Python's import machinery handles trust. Samples + tests use only `voss_runtime::*`, so the runtime trust boundary is unchanged. |
| Banner injected via attacker-controlled cred path | Spoofing | Banner text is hard-coded (D-02); no interpolation of user input. |
| `VOSS_HERMETIC=1` accidentally set in production → silent fake responses | Repudiation | D-02 mandates the banner on EVERY invocation. No throttling. Users see the signal. |
| `SUPPORT_FAKE_INDEX_SITECUSTOMIZE` leaks into production Python path | Tampering | Sitecustomize is written only under `tmp_path/_voss_stub/`; PYTHONPATH is constructed per-test (helpers.py:216-227); never persistent. |
| HF model download triggers unexpected network call in CI | Availability | D-03 removes the call from `voss check`. D-11 hermetic tests patch out `SemanticMatcher._encode`. |
| `examples/raw_python/*.py` drift from samples → silently wrong parity assertions | Tampering / integrity | D-12 contract + Pitfall 7 mitigation: same-PR coupling. |

## Sources

### Primary (HIGH confidence — verified by reading source at cited file:line)
- `/Users/benjaminmarks/Projects/Voss/voss/grammar.lark:1-219` — full grammar surface, all M3 constructs confirmed accepted.
- `/Users/benjaminmarks/Projects/Voss/voss/parser.py:1-799` — transformer rules for try_stmt (542-557), use_stmt (711-715), use_path (711-712).
- `/Users/benjaminmarks/Projects/Voss/voss/analyzer.py:1-766` — Analyzer class (197+), `_visit_match_stmt` (479-501, the D-03 fix site), `_emit_program_index` (641-719), `SemanticMatcherIndexBuilder` (172-184), `_default_local_model` (166-169), `emit_indexes` flag (204-211, 435).
- `/Users/benjaminmarks/Projects/Voss/voss/codegen.py:1-1283` — `ImportCollector.add_use` (126-131), `_emit_memory_let` (690-705), `_emit_try` (1107-1126), `_emit_similar_match` (1011-1051), `_resolve_cache_root` (218-235), `_DECL_TYPES` (1153), `ProgramEmitter.emit` (1173-1250).
- `/Users/benjaminmarks/Projects/Voss/voss/cli.py:1-294` — current `check` (204-228, emit_indexes=False already passed), `run` (170-201, the D-01 wire-in site), `_compile_source` (75-118).
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/__init__.py:1-59` — public exports.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/semantic.py:1-94` — `SemanticMatcher.__init__` (24-43), `_ensure_encoder` (45-50), `from_index` (79-94, the bypass path).
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/providers/__init__.py:1-31` — registry, `get()` (12-18), default registrations (22).
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/providers/stub.py:1-74` — StubProvider implementation.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/providers/litellm_provider.py:1-63` — current live default that errors when no creds.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/_config.py:1-37` — RuntimeConfig dataclass.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/memory/episodic.py:1-67` — `EpisodicMemory` API confirmed (add, last, render).
- `/Users/benjaminmarks/Projects/Voss/voss/harness/auth.py:1-376` — `resolve(preference="auto")` (332-375), Resolution dataclass (323-330).
- `/Users/benjaminmarks/Projects/Voss/voss/harness/cli.py:38-77` — `_resolve_auth_or_die` pattern (existing usage of auth.resolve).
- `/Users/benjaminmarks/Projects/Voss/samples/classify.voss:1-13`, `samples/support.voss:1-23`, `samples/research.voss:1-41` — current sample source.
- `/Users/benjaminmarks/Projects/Voss/examples/raw_python/classify.py:1-18`, `support.py:1-39`, `research.py:1-64` — parity oracles.
- `/Users/benjaminmarks/Projects/Voss/tests/examples/helpers.py:1-229` — existing test helpers (re-used).
- `/Users/benjaminmarks/Projects/Voss/tests/examples/test_{classify,support,research}_e2e.py`, `test_cli_matrix.py` — existing test bodies (existed since May 9, slimming required).
- `/Users/benjaminmarks/Projects/Voss/tests/parser/examples/assistant.voss:1-18` — reference for `memory.*` + `use` patterns.
- `/Users/benjaminmarks/Projects/Voss/tests/cli/test_check.py:1-80`, `test_run.py:1-60` — existing CLI test patterns to mirror.
- `/Users/benjaminmarks/Projects/Voss/tests/codegen/test_imports.py:50-105` — `use` codegen behavior verified.
- `/Users/benjaminmarks/Projects/Voss/pyproject.toml:1-53` — deps + test config.
- `/Users/benjaminmarks/Projects/Voss/.planning/REQUIREMENTS.md:54-63` — LANG-01..LANG-10 (canonical).
- `/Users/benjaminmarks/Projects/Voss/.planning/ROADMAP.md:145-179` — M3 phase goal + success criteria.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M3-language-validation/M3-CONTEXT.md:1-191` — full user decisions (D-01..D-15).
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M1-harness-happy-path/M1-CONTEXT.md:1-80` — carry-forward strict-tier + diagnose-don't-fix posture.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M2-project-cognition/M2-CONTEXT.md:1-60` — carry-forward `.voss/` vs `.voss-cache/` separation.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/06-examples-validation/06-RESEARCH.md:1-120` — legacy design lineage.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/06-examples-validation/06-VALIDATION.md:1-73` — legacy validation table M3 slims.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/06-examples-validation/06-01-PLAN.md:1-249` — legacy plan-01 shape (helpers + classify e2e).
- `/Users/benjaminmarks/Projects/Voss/.vscode/voss_v_0_1_scope_lock.md:1-1295` — full v0.1 scope lock (M3 section at 629-655).
- `/Users/benjaminmarks/Projects/Voss/README.md:1-66` — current README, must be rewritten for D-14.

### Measurements
- `time python3 -m voss.cli check samples/support.voss` — cold ~12.97s, warm ~8.87s (measured locally 2026-05-11; dominated by HF model load).
- `time python3 -m voss.cli check samples/classify.voss` — warm ~1.52s.
- `time python3 -m voss.cli check samples/research.voss` — warm ~1.38s.
- `analyze(p, emit_indexes=False, index_builder=FakeBuilder())` — sub-millisecond (verified inline at the end of research).

### Secondary
None (no WebSearch / WebFetch used; everything was in-repo).

### Tertiary
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every recommendation is "use what's already imported"; no new deps.
- Architecture: HIGH — file:line citations for every claim; behavior verified by running the binary and reading the source.
- Pitfalls: HIGH — items 1, 4, 6 are directly observable; items 2, 3, 5, 7 are pattern-match risks from carry-forward decisions in M1/M2.
- Sample-extension feasibility: HIGH — parser/analyzer/codegen all support every construct M3 adds; verified by minimal repro.

**Research date:** 2026-05-11
**Valid until:** 2026-06-11 (compiler stack is stable; only re-validate if `voss/analyzer.py`, `voss/cli.py`, or `voss_runtime/providers/__init__.py` see major refactors).

## RESEARCH COMPLETE
