# Phase M3: Language Validation - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

M3 proves the existing `.voss` toolchain — parser (`voss/parser.py`), analyzer (`voss/analyzer.py`), codegen (`voss/codegen.py`), runtime (`voss_runtime/`) — holds up on the three canonical samples (`samples/classify.voss`, `samples/support.voss`, `samples/research.voss`) across the full LANG-01..10 surface. M3 is **validation and wiring**, not greenfield compiler work: the compiler stack is already ~3.4k LOC and `voss check` passes on all three samples today.

**In scope:**
- Extend `samples/support.voss` with `memory.episodic` to recall prior tickets (covers LANG-07).
- Extend `samples/research.voss` with `try/catch` around `webSearch` and a `use voss.tools` import (covers LANG-08).
- Auto-fallback to `__stub__` provider in `voss run` when no real provider creds are detected (or `VOSS_HERMETIC=1` is set). Required for LANG-10 to run in CI.
- Stderr banner on every stub fallback: `voss: no provider creds detected — using __stub__ (deterministic fake responses)`.
- `voss check` stays static-only: do not instantiate `SemanticMatcher` / load HF embeddings at check time. Analyzer validates `match similar(...)` statically and emits the manifest; the encoder loads only at `voss run`.
- Slimmed legacy-phase-06 test suite under `tests/examples/`:
  - `tests/examples/__init__.py`
  - `tests/examples/helpers.py` — temp-project + Click runner + StubProvider + cache-artifact assertions.
  - `tests/examples/test_classify_e2e.py` — confident + low-confidence paths.
  - `tests/examples/test_support_e2e.py` — semantic route + fallback with fake encoder/index.
  - `tests/examples/test_research_e2e.py` — spawn/gather happy path + within/fallback budget exhaustion.
  - `tests/examples/test_cli_matrix.py` — all three samples through `voss check`, `voss compile` + `python3`, `voss run`.
  - `tests/examples/test_check_speed.py` — hard wall-clock ceiling per sample (~2s; tune during execution).
- Raw-python parity: keep `examples/raw_python/{classify,support,research}.py`; each e2e test asserts generated-Python stdout matches raw-Python stdout under the same `StubProvider`.
- `docs/voss-vs-python.md` — side-by-side `.voss` ↔ raw-python doc with LOC and commentary; linked from README.
- README update: add a "What is .voss" section framing it as AI workflow control (not a Python replacement).
- Sample header comments: each `samples/*.voss` opens with a one-block comment naming the AI-workflow primitives it demonstrates.

**Out of scope (deferred to other phases):**
- Rewriting `/analyze` or any harness skill in `.voss` — that's M4.
- Embeddings / semantic search index beyond M2's flat `repo.idx` manifest — M3 does not depend on it.
- `voss check` exit-code or diagnostic-format overhauls beyond what samples need — already working.
- Codegen changes beyond what extending support/research samples requires — the existing 1283-LOC codegen handles the current sample surface.
- Live-provider tests against real Anthropic/OpenAI — explicitly excluded from CI; live verification stays manual per legacy phase-06 plan.
- `memory.semantic` and `memory.working` surfaced in user-facing samples — covered by parser/analyzer/codegen test fixtures only.
- A 4th canonical sample — the roadmap promises "three meaningful examples"; M3 extends the three, does not add a fourth.
- Distribution / packaging polish (`pip install` smoke beyond `voss --help` working in tests) — M5.

</domain>

<decisions>
## Implementation Decisions

### Hermetic run + check speed
- **D-01:** `voss run` auto-falls back to `StubProvider` when no real provider creds are detected OR `VOSS_HERMETIC=1` is set. Resolution: re-use `voss_runtime` provider config helpers; if `RuntimeConfig.default_model` resolution returns no live credential, register `__stub__` and use it. Zero-config for CI.
- **D-02:** Every stub fallback prints a stderr banner: `voss: no provider creds detected — using __stub__ (deterministic fake responses)`. Banner fires on every invocation (not throttled). Matches M1 D-13 diagnose-don't-fix posture: loud about what's happening, never silent.
- **D-03:** `voss check` is **static-only**. The semantic-matcher / HF encoder load is moved out of any check-time code path. Analyzer continues to validate `match similar(...)` signatures and emit the match manifest. The encoder instantiates lazily only inside generated Python at `voss run` time. This satisfies the roadmap cross-cutting constraint that "`voss check` should be fast enough to run after edits."
- **D-04:** `voss run` success contract for LANG-10 = **exit 0 + non-empty stdout** under `StubProvider`. Minimal CI-assertable contract. Stronger raw-python parity is a separate per-test assertion in the e2e suite (D-12), not the LANG-10 gate.

### Sample coverage (LANG-02..LANG-08)
- **D-05:** `samples/support.voss` is extended with `memory.episodic` to recall prior tickets — fits the support-agent narrative (recall past customer interactions). LANG-07 (`memory.episodic`) is satisfied through a runnable sample, not a test-only fixture.
- **D-06:** `samples/research.voss` is extended with `try/catch` wrapping `webSearch(...)` (network call is the natural failure point) and a `use voss.tools` import line. LANG-08's `try/catch` and `use` constructs are exercised by a runnable sample.
- **D-07:** `memory.semantic` and `memory.working` (the other two LANG-07 primitives) are covered by **test-only parser/analyzer/codegen fixtures** under `tests/parser/examples/coverage/`, `tests/analyzer/examples/coverage/`, `tests/codegen/snapshots/coverage/` — not surfaced in user-facing samples. Keeps the three canonical samples readable.
- **D-08:** `prompt` and `@tool` (the rest of LANG-08) remain covered by current samples (`prompt SupportAgent { ... }` in support; `tools: [webSearch]` and the implied `@tool` declaration in research). No changes needed for these constructs.

### Test surface
- **D-09:** M3 builds the **slimmed legacy phase-06 test plan** under `tests/examples/`:
  - `__init__.py`, `helpers.py`, `test_classify_e2e.py`, `test_support_e2e.py`, `test_research_e2e.py`, `test_cli_matrix.py`, `test_check_speed.py`.
  - Drops the legacy `test_helpers.py` meta-suite (testing the helpers themselves is overkill for v0.1).
  - Drops the legacy `--live` optional path (live verification stays manual per M3 scope).
- **D-10:** Test directory is `tests/examples/` — mirrors the `samples/` directory and matches the legacy plan. Not renamed to `tests/language/` or `tests/m3/`.
- **D-11:** All e2e tests run hermetically: `StubProvider` registered programmatically; fake encoder / fake index used for `support.voss` semantic-routing tests; `VOSS_HERMETIC=1` set in the test environment so the auto-fallback path is exercised end-to-end. No CI-visible HF model downloads.
- **D-12:** `examples/raw_python/{classify,support,research}.py` are **kept as parity oracles**. Each e2e test runs the generated Python AND the raw-Python equivalent under the same `StubProvider` seed; asserts stdout matches. Catches codegen drift. When sample semantics evolve, the raw-Python equivalent must be updated alongside the `.voss` source as part of the same PR.
- **D-13:** `tests/examples/test_check_speed.py` enforces a **hard wall-clock ceiling per sample** for `voss check`. Target: ≤2s per sample on a stock CI worker (tune during execution; if flaky, switch to process time or a higher ceiling, but keep it a real gate, not log-only).

### Framing surface (LANG-01, LANG-05)
- **D-14:** Two surfaces carry the framing:
  - **README.md** — gains a "What is .voss" section. Positions `.voss` as the AI-workflow control layer (probable values, confidence gates, context budgets, semantic routing, agents, memory, fallbacks). Explicitly states it is **not** a general Python replacement. Links to `samples/` and `docs/voss-vs-python.md`.
  - **Sample headers** — each `samples/*.voss` opens with a comment block naming the AI-workflow primitives it demonstrates (e.g., `# classify.voss — probable<T> + confidence gate`).
- **D-15:** `docs/voss-vs-python.md` ships as the explicit "shorter, clearer than equivalent Python" deliverable (roadmap success criterion 5). Each of the three samples is paired with its `examples/raw_python/` equivalent. Includes per-sample LOC counts and a one-paragraph commentary on what `.voss` makes explicit that raw Python leaves implicit. README links to it.

### Claude's Discretion
- Exact phrasing of the README "What is .voss" section and per-sample header comments — pick what reads well; iterate.
- Exact wall-clock ceiling in `test_check_speed.py` (`2s` is a starting target; tune during execution if CI worker variance demands a higher number — keep it a real gate either way).
- The mechanism by which auto-StubProvider detection wires in (env-var probe vs. cred-resolver hook in `voss_runtime/providers/`) — pick the smallest diff; mirror M1 D-09's `auth.resolve(preference="auto")` shape if it fits.
- Fake encoder + fake index implementation for `support.voss` semantic-routing tests — re-use `voss_runtime` test helpers if any exist; otherwise a deterministic hash-bucket encoder is fine.
- `RuntimeConfig` default for `__stub__` model name and how it interacts with sample-supplied model annotations (if any) — straightforward; pick the obvious default.
- Whether the stub-fallback banner is suppressed under `VOSS_QUIET=1` (or any quiet flag) — pick the simplest default; suppression is allowed if the test harness asks for it, but never silent by default.
- Exact shape of `try/catch` syntax in `research.voss` (token name, block shape) — must match what `voss/parser.py` already accepts. If the current parser doesn't yet support `try/catch`, the implementation plan covers parser/analyzer/codegen support before sample extension lands. Researcher: confirm current parser surface for `try`, `catch`, `use`, and `memory.episodic` against `voss/grammar.lark`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v0.1 scope and product framing
- `.vscode/voss_v_0_1_scope_lock.md` §"M3: Language Validation" — Source of truth for what LANG-* requires.
- `.planning/PROJECT.md` — Active requirements, especially the "Core language constructs remain supported" bullet listing `probable<T>`, `ctx`, `within budget/fallback`, `match similar`, `agent`, `spawn`, `gather`, memory primitives, `@tool`, `prompt`, `try/catch`, and `use`.
- `.planning/REQUIREMENTS.md` §lines 54–63 — LANG-01..LANG-10 (the requirement IDs M3 owns).
- `.planning/ROADMAP.md` §"Phase M3: Language Validation" — Phase goal, success criteria, cross-cutting constraints (no Python parity chasing; hermetic default; fast check).

### Prior phase decisions (carry forward)
- `.planning/phases/M1-harness-happy-path/M1-CONTEXT.md` — Specifically D-05 (strict tier mapping), D-13 (doctor diagnose-don't-fix posture mirrors M3's stub-banner stance), D-15 (session storage already lives where it does — M3 doesn't touch session paths).
- `.planning/phases/M2-project-cognition/M2-CONTEXT.md` — Specifically the `.voss/` vs `.voss-cache/` separation (codegen output already writes to `.voss-cache/`, must continue to). M3 does not add new cognition files.

### Legacy planning artifacts (read for design lineage, not as binding contracts)
- `.planning/phases/06-examples-validation/06-RESEARCH.md` — Original research for example validation. Identified the contract gaps and the `StubProvider` strategy that M3 now adopts. The "Contract Gaps" section is largely closed (parser/analyzer/codegen/CLI all exist now).
- `.planning/phases/06-examples-validation/06-VALIDATION.md` — Original test plan with per-task validation map. M3's `tests/examples/` test list (D-09) is a slimmed version of Wave 0 here.
- `.planning/phases/06-examples-validation/06-01-PLAN.md` through `06-04-PLAN.md` — Original plan splits. Reference for what tests/examples files were originally designed to look like.

### Existing compiler stack (parity contract — extend, do not rewrite)
- `voss/parser.py` (799 LOC) — Lark-based parser. Extending samples may require confirming `try/catch`, `use`, and `memory.episodic` constructs already parse; if any don't, the sample-extension plan must precede them with a parser plan (or rule out the construct).
- `voss/grammar.lark` (219 LOC) — Source of grammar truth. Read alongside `parser.py`.
- `voss/analyzer.py` (766 LOC) — Already includes `_warn_unguarded_probable` and `_is_gated` scope tracking for LANG-02. Extending samples may add new analyzer cases; default is no new analyzer code.
- `voss/codegen.py` (1283 LOC) — Lowers AST to Python. Sample extensions exercise existing codegen paths.
- `voss/cli.py` (294 LOC) — Click commands: `voss compile`, `voss run`, `voss check`, `voss init`, `voss ast`. `voss run` is where the auto-StubProvider fallback (D-01) wires in. `voss check` is where the static-only enforcement (D-03) lives.
- `voss_runtime/__init__.py` and submodules — `ProbableValue`, `ContextScope`, `BudgetScope`, `SemanticMatcher`, `VossAgent`, `AgentHandle`, `gather`, memory classes, `tool`, provider config helpers, `StubProvider`. Auto-stub fallback (D-01) is wired here.
- `voss_runtime/providers/litellm_provider.py` — Real-provider path that fails today when no creds. The auto-stub detection lives upstream of this.

### Existing samples and parity targets
- `samples/classify.voss` (13 LOC) — LANG-02 (probable + confidence gate). Unchanged in scope, header comment added.
- `samples/support.voss` (23 LOC) — Will gain `memory.episodic` lines (D-05).
- `samples/research.voss` (41 LOC) — Will gain `try/catch` and `use voss.tools` (D-06).
- `examples/raw_python/classify.py`, `examples/raw_python/support.py`, `examples/raw_python/research.py` — Parity oracles for the e2e suite (D-12). Update alongside any sample change.
- `tests/parser/examples/{classify,support,research,assistant}.voss` — Parser golden fixtures. `assistant.voss` is reference material for `memory.*` and `use` parsing — read before extending samples.
- `tests/parser/test_examples.py` — Parser golden tests pattern. Mirror the structure for new `tests/parser/examples/coverage/` fixtures (D-07).

### External, do not re-derive
- Lark parsing semantics — already in use by `voss/parser.py`.
- pytest + Click `CliRunner` — already in use by `tests/cli/` and `tests/harness/test_cli.py`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`voss_runtime/providers/StubProvider`** — Deterministic fake provider already exists and is registered under `__stub__`. The M3 auto-fallback wires this into `voss run` when no live cred resolves.
- **`voss_runtime` provider config helpers** — Already centralize `RuntimeConfig.default_model` resolution. Auto-stub detection is a small addition to this resolver, not a new code path.
- **`voss/analyzer.py:_warn_unguarded_probable`** — LANG-02 already lands here. Sample extensions do not need new analyzer logic for confidence gates.
- **`voss/analyzer.py` semantic-match manifest emission** — Already emits a per-program manifest for `match similar(...)` consumers. The M3 static-only check (D-03) means this manifest is the only check-time output; encoder instantiation moves to run-time only.
- **`tests/parser/examples/assistant.voss`** — Reference fixture for `memory.*` and `use` syntax. Read before extending support/research samples to confirm current parser surface.
- **`examples/raw_python/*.py`** — Hand-written parity targets already in tree. Used as parity oracles (D-12); no need to author new ones.
- **`tests/parser/test_examples.py`** — Test pattern (parametrized golden fixtures) to mirror for `tests/parser/examples/coverage/`.

### Established Patterns
- **Strict tier / loud failure** (M1 D-05, M2 D-07) — M3 mirrors: stub fallback emits a banner (D-02); malformed sample fails check loudly with a diagnostic.
- **Diagnose-don't-fix** (M1 D-13) — `voss doctor` diagnoses but doesn't act; M3's stub-fallback banner is the same posture for runtime credential gaps.
- **Hermetic-by-default tests** (legacy phase-06 plan; legacy `tests/harness/test_session_redaction.py`) — Use `StubProvider` + fake encoder + temp-cache dirs; never touch real network or HF Hub in CI.
- **Schema-allowlist redaction** (M1 D-16, M2 D-15) — Not directly extended by M3, but: anything M3 writes through `voss_runtime` should respect the same allowlist invariant if it touches `SessionRecord` or `RunRecord` (M3 does not).
- **`.voss-cache/` writes go through `sandbox.py`** (M2 D-06) — Compiler `voss compile`/`voss run` already write generated Python into `.voss-cache/` under the cwd jail. M3 does not touch this.

### Integration Points
- **`voss/cli.py:run` (line ~171)** — Where the auto-StubProvider fallback (D-01) and stderr banner (D-02) wire in. Detection happens before the generated Python is exec'd.
- **`voss/cli.py:check` (line ~205)** — Where the static-only-check guarantee (D-03) is enforced. Any code path that imports / instantiates `SemanticMatcher` at check time must be removed or lazy-wrapped.
- **`voss_runtime/semantic.py` (SemanticMatcher)** — Confirm encoder load is lazy; if today it loads eagerly on import, wrap the HF call in a `__call__`-time lazy property (or a `from_index`-time deferred load).
- **`voss_runtime/providers/litellm_provider.py`** — Upstream cred-resolver decides between live and stub; no changes inside this file.
- **`voss/parser.py` + `voss/grammar.lark`** — Researcher must confirm `try`, `catch`, `use`, and `memory.episodic` already parse. If `try/catch` is absent from the grammar, the implementation plan extends grammar + parser + analyzer + codegen before sample extension lands.
- **`README.md`** (repo root) — Receives the "What is .voss" section (D-14).
- **`docs/voss-vs-python.md`** (new file) — The brevity-demo deliverable (D-15).

</code_context>

<specifics>
## Specific Ideas

- **Three canonical samples remain the LANG-09 surface** — not four. Extensions land in support and research; classify stays minimal. Roadmap success criterion 1 ("Three meaningful `.voss` examples pass `voss check`") is honored verbatim.
- **Auto-stub + banner is the v0.1 transparency signal for runtime credential gaps** — mirrors M2 D-20 (cognition status line). Users see what's loading without `--verbose`. Loud-but-quiet.
- **Static check / lazy encoder is the v0.1 fast-check contract** — splits "is this program well-formed" (cheap) from "can this program actually run" (potentially expensive, deferred to `voss run`).
- **Raw-python parity is the codegen-readability contract for LANG-03** — the `examples/raw_python/` files are simultaneously parity oracles (D-12) and the "readable Python" reference that LANG-03 demands. One artifact, two roles.
- **`docs/voss-vs-python.md` is the success-criterion-5 artifact** — concrete, reviewable, links from README. Not subjective.

</specifics>

<deferred>
## Deferred Ideas

- **A 4th canonical sample showcasing memory.* + try/catch + use end-to-end** — rejected for M3. Roadmap promises three. Coverage handled by extending support/research + test-only fixtures.
- **`memory.semantic` and `memory.working` surfaced in runnable samples** — deferred. Test-fixture-only for M3.
- **Live-provider e2e tests in CI** — deferred. Manual verification only per legacy phase-06 plan. May surface in M5 when distribution / install polish lands.
- **`pytest -m live` marker + opt-in live path** — deferred. The legacy phase-06 plan included this; M3 drops it to keep the test surface lean.
- **`tests/examples/test_helpers.py` meta-tests on the helpers themselves** — rejected for M3 overkill. Trust the helpers; if they break, the e2e tests will surface it.
- **`voss check --speed-budget=Ns` flag for tunable speed gate** — deferred. Hard-coded ceiling in `test_check_speed.py` is enough for v0.1.
- **`VOSS_QUIET=1` suppressing the stub-fallback banner** — discretion. Allowed if needed; never silent by default.
- **`/analyze` or any `.voss`-authored harness skill** — M4.
- **Embeddings / semantic index beyond M2's flat `repo.idx`** — M3+ once language-driven workflows demand it (already deferred in M2).
- **Renaming `tests/examples/` to `tests/language/` or phase-tagged paths** — rejected for M3. Mirrors `samples/` and legacy plan.
- **Retiring `examples/raw_python/` in favor of generated-python snapshots** — rejected. Raw-python files are simultaneously parity oracles and the LANG-03 readability reference.
- **Codegen snapshot tests under `tests/codegen/snapshots/`** — out of scope for M3 beyond what the per-construct coverage fixtures (D-07) need. Broader codegen-snapshot coverage is a separate hardening pass if regressions emerge.
- **`voss init <template>` scaffolds covering AI workflow templates** — out of scope; `voss init` already exists for v0.1 minimal use.

</deferred>

---

*Phase: M3-language-validation*
*Context gathered: 2026-05-11*
