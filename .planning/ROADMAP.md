# Roadmap: Voss

**Created:** 2026-05-07
**Mode:** Horizontal Layers (standard)
**Granularity:** Standard (6 phases)
**Requirements covered:** 36 / 36

## Phase Order

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Runtime Library | Standalone `voss_runtime` package implements all five core constructs and memory primitives, exercised by hand-written Python | RUN-01..11 (11) | 5 |
| 2 | Parser & Grammar | Lark grammar + AST + transformer parses every PRD §7 example into a valid Voss AST | GRAM-01..05 (5) | 4 |
| 3 | Semantic Analysis | Walk AST: type checking, confidence-gate warnings, token-budget warnings, and compile-time embedding index emission to `.voss-cache/` | ANLY-01..03 (3) | 3 |
| 4 | Codegen | AST → readable Python source that imports `voss_runtime` and runs identically to the hand-written Phase 1 equivalents | GEN-01..05 (5) | 3 |
| 5 | CLI, Packaging & Linguist | `voss compile/run/check/init/ast` commands, `pip install`-ready package, `.gitattributes` + Linguist metadata, init scaffold | CLI-01..06, TOOL-01..03 (9) | 4 |
| 6 | Examples Validation | All three PRD §7 example programs compile and run end-to-end through the full pipeline | EX-01..03 (3) | 2 |

---

### Phase 1: Runtime Library
**Goal:** Build `voss_runtime` as a standalone Python package implementing every primitive Voss will codegen against; validate semantics with hand-written Python before any compiler exists.

**Requirements:** RUN-01, RUN-02, RUN-03, RUN-04, RUN-05, RUN-06, RUN-07, RUN-08, RUN-09, RUN-10, RUN-11

**Success Criteria:**
1. `from voss_runtime import ProbableValue, ContextScope, BudgetScope, SemanticMatcher, VossAgent, gather, EpisodicMemory, SemanticMemory, WorkingMemory, tool` works in a clean Python 3.11+ env
2. PRD §7.1, §7.2, §7.3 examples can be hand-written in raw Python using only `voss_runtime` and execute correctly
3. `BudgetScope` interrupts a primary block and routes to fallback when token/latency/cost limits are exceeded
4. Multi-provider model abstraction returns equivalent results from at least two providers (e.g. Anthropic + OpenAI) for the same prompt
5. Full `pytest` suite passes with coverage of every public class

---

### Phase 2: Parser & Grammar
**Goal:** Lark grammar plus AST dataclasses plus transformer accept the full PRD §3 syntax and produce a clean Voss AST for every example.

**Requirements:** GRAM-01, GRAM-02, GRAM-03, GRAM-04, GRAM-05

**Success Criteria:**
1. `grammar.lark` covers `probable<T>`, `ctx`, `within/fallback`, `match similar(...)`, agent definitions, `spawn`, `gather`, memory types, `@tool`, `prompt` inheritance, `try/catch`, `use foo::bar`
2. AST node dataclasses exist for every grammar production
3. Transformer converts Lark trees into Voss AST objects without loss
4. Parser test suite parses all PRD §7 example programs without error

---

### Phase 3: Semantic Analysis
**Goal:** Walk the AST and enforce Voss's type and budget guarantees before codegen runs; emit compile-time embedding indexes.

**Requirements:** ANLY-01, ANLY-02, ANLY-03

**Success Criteria:**
1. Using a `probable<T>` value where `T` is expected without a confidence gate produces a warning with file + line number
2. A `ctx` block whose static token estimate exceeds its declared budget emits a warning at compile time
3. Each `match` block's `similar(...)` cases are embedded once at compile time and stored in `.voss-cache/<program>.idx` for runtime lookup

**Planned:** 2026-05-07 — 5 plans, waves 1-5

**Wave 1:** `03-01` — analyzer diagnostics/result foundation plus a blocking Phase 2 AST/parser contract preflight.

**Wave 2** *(blocked on Wave 1 completion)*: `03-02` — ANLY-01 probable type normalization, scope tracking, and confidence-gate warnings.

**Wave 3** *(blocked on Wave 2 completion)*: `03-03` — ANLY-02 deterministic static token-budget estimation for `ctx` blocks.

**Wave 4** *(blocked on Wave 3 completion)*: `03-04` — ANLY-03 compile-time `similar(...)` index manifest emission with hermetic fake-builder tests and project-local `.voss-cache` path safety.

**Wave 5** *(blocked on Wave 4 completion)*: `03-05` — parser-backed example integration and public analyzer exports.

**Cross-cutting constraints:**
- Phase 3 execution must not proceed until `03-01-0` prints `phase2-contract-ok`.
- Analyzer checks must walk AST dataclasses only; they must not execute user code or call external providers during default tests.
- Default verification must stay hermetic; embeddings are fakeable in tests and token estimation is local/provider-free.

---

### Phase 4: Codegen
**Goal:** Translate the validated AST into readable Python source that imports `voss_runtime` and behaves identically to the hand-written Phase 1 examples.

**Requirements:** GEN-01, GEN-02, GEN-03, GEN-04, GEN-05

**Success Criteria:**
1. Every language construct has a codegen path; generated `.py` files import only `voss_runtime` plus declared user dependencies
2. Generated Python is human-readable (preserved structure, comments where useful, no minification)
3. Voss `try/catch` and `use foo::bar` codegen to correct Python `try/except` and `import` statements; codegen test suite verifies semantic equivalence to Phase 1 hand-written variants

**Planned:** 2026-05-07 — 6 plans, waves 1-6

**Wave 1:** `04-01` — codegen contract gate, public API/result shape, writer, import collector, and initial readability/import tests.

**Wave 2** *(blocked on Wave 1 completion)*: `04-02` — expression, function, basic statement, and async `main` lowering.

**Wave 3** *(blocked on Wave 2 completion)*: `04-03` — runtime primitive lowering for `probable`, `ctx`, `within/fallback`, `try/catch`, and memory declarations.

**Wave 4** *(blocked on Wave 3 completion)*: `04-04` — Phase 3 semantic-index manifest consumption and `use foo::bar` import lowering.

**Wave 5** *(blocked on Wave 4 completion)*: `04-05` — agents, tools, prompts, classes, `spawn`, and `gather` lowering.

**Wave 6** *(blocked on Wave 5 completion)*: `04-06` — PRD example compile/run verification, semantic-equivalence tests, and generated-source snapshots.

**Cross-cutting constraints:**
- Phase 4 execution must not proceed until `04-01-0` prints `phase4-codegen-contract-ok`.
- Codegen must not implement parser/analyzer/runtime substitutes; it consumes Phase 2 ASTs and Phase 3 analyzer/index metadata.
- Default verification must stay hermetic with `StubProvider`, fake manifests, no live providers, no network, and no model downloads.
- Generated Python must avoid compiler imports and include only required stdlib modules, public `voss_runtime` names, Pydantic when needed, and declared `use` dependencies.

---

### Phase 5: CLI, Packaging & Linguist
**Goal:** Ship `voss` as an installable CLI with project scaffolding plus the GitHub/Linguist plumbing so `.voss` files render as code from day one.

**Requirements:** CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, TOOL-01, TOOL-02, TOOL-03

**Success Criteria:**
1. `pip install -e .` (or installable archive) exposes `voss compile|run|check|init|ast` on the path with sensible help text and error messages
2. `voss check` reports unguarded `probable<T>` usage with file paths and line numbers; `voss ast` prints the Voss AST for a `.voss` file
3. `voss init my-project` produces a working scaffold including a `.gitattributes` declaring `*.voss linguist-language=Voss` and `linguist-detectable=true`, plus a hello-world program
4. The Voss repo itself contains a top-level `.gitattributes`, a `samples/` directory of representative programs, and language metadata (extension, color suggestion, parent fallback) sufficient for a future github-linguist/linguist PR

**Planned:** 2026-05-08 — 6 plans, waves 1-6

**Wave 1:** `05-01` — Phase 2/3/4 compiler contract gate, Click command shell, and `[project.scripts]` entrypoint.

**Wave 2** *(blocked on Wave 1 completion)*: `05-02` — read-only `voss ast` and `voss check` commands with diagnostic output and no `.voss-cache` writes.

**Wave 3** *(blocked on Wave 2 completion)*: `05-03` — `voss compile` and subprocess-backed `voss run`.

**Wave 4** *(blocked on Wave 3 completion)*: `05-04` — `voss init` project scaffold, templates, package data, and scaffold `.gitattributes`.

**Wave 5** *(blocked on Wave 4 completion)*: `05-05` — repo-level `.gitattributes`, representative `samples/*.voss`, and draft local Linguist metadata with Python fallback fields.

**Wave 6** *(blocked on Wave 5 completion)*: `05-06` — editable-install smoke, package-data checks, and full hermetic CLI/tooling integration.

**Cross-cutting constraints:**
- Phase 5 execution must not proceed until `05-01-0` prints `phase5-cli-contract-ok`.
- CLI commands must stay thin wrappers over public parser, analyzer, and codegen APIs; no parser/analyzer/codegen/runtime/provider fallbacks belong in the CLI.
- `check` and `ast` must be read-only; `check` uses `emit_indexes=False` and must not write `.voss-cache`.
- `run` must execute generated Python through `subprocess.run([sys.executable, ...])`; no in-process `exec`/`eval` execution.
- Linguist assets must preserve the exact Voss `.gitattributes` declaration while treating Python fallback/highlighting as draft metadata for future upstream registration, not current native GitHub support.

---

### Phase 6: Examples Validation
**Goal:** Prove the full pipeline by compiling and running the three PRD §7 examples end-to-end.

**Requirements:** EX-01, EX-02, EX-03

**Success Criteria:**
1. `voss run classify.voss`, `voss run support.voss`, and `voss run research.voss` each produce expected output against live model providers (or a deterministic stub provider in CI)
2. The same three programs round-trip through `voss compile` then `python3` with identical behavior, and `voss check` passes on each

**Planned:** 2026-05-08 — 4 plans, waves 1-4

**Wave 1:** `06-01` — Phase 1-5 runtime/compiler/CLI contract gate, shared example harness, and EX-01 `classify.voss` end-to-end validation.

**Wave 2** *(blocked on Wave 1 completion)*: `06-02` — EX-02 `support.voss` semantic routing and ctx fallback validation with fake embeddings/indexes.

**Wave 3** *(blocked on Wave 2 completion)*: `06-03` — EX-03 `research.voss` agent spawn/gather and within/fallback validation under deterministic stubs.

**Wave 4** *(blocked on Wave 3 completion)*: `06-04` — full CLI matrix across all three examples, optional live-provider tests, full suite, install smoke, and artifact hygiene.

**Cross-cutting constraints:**
- Phase 6 execution must not proceed until `06-01-0` prints `phase6-examples-contract-ok`.
- Phase 6 validates completed Phase 1-5 outputs; it must not introduce parser/analyzer/codegen/runtime/CLI fallback implementations.
- Default verification must be hermetic with `StubProvider`, fake semantic indexes/embeddings, temp project roots, no live providers, no network, and no model downloads.
- `voss check` must not write `.voss-cache`; `voss compile` and generated files must write only under temp project/output dirs during tests.
- Optional live-provider tests must be marked `live`, skipped without explicit provider configuration, and excluded from default CI.

---

## Coverage

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1 | RUN-01..11 | 11 |
| 2 | GRAM-01..05 | 5 |
| 3 | ANLY-01..03 | 3 |
| 4 | GEN-01..05 | 5 |
| 5 | CLI-01..06, TOOL-01..03 | 9 |
| 6 | EX-01..03 | 3 |
| **Total** | | **36 / 36** |

All v1 requirements mapped. ✓

---

# Milestone v1.1 — Coding Harness

**Added:** 2026-05-09
**Status:** Pending — gated on v1.0 close (Phase 6 in flight)
**Reference:** `.planning/HARNESS-PLAN.md`
**Codename:** none — single `voss` binary; agent verbs added to compiler CLI
**Tracking IDs:** HARN-01..HARN-24

The harness is the compiler's hardest user. The agent loop itself is authored in `.voss` and compiled by the project's own compiler. Every regression in the language shows up first in `voss` (the agent).

## Phase Order — v1.1

| # | Phase | Goal | HARN IDs | Blocking Dependency |
|---|-------|------|----------|---------------------|
| H1 | Skeleton CLI on Raw Runtime | `voss` REPL + `voss do "<task>"` one-shot working against `voss_runtime` directly (Python loop, no `.voss` source yet). TTY renderer, NDJSON mode, permission prompts, in-process episodic memory. | HARN-01..04 | v1.0 Phase 1 ✓ |
| H2 | Sessions, Semantic Memory, REPL Polish | Persistent sessions (`voss resume`/`voss sessions`), repo semantic index (chromadb), slash commands, diff preview + apply flow. | HARN-05..09 | H1 |
| H3 | Loop Port to Voss | Rewrite Python loop → `loop.voss` + `router.voss` + `planner.voss` + `executor.voss` + `reviewer.voss` under `voss/harness/agent/`. CI gate: `voss check voss/harness/agent/`. | HARN-10..13 | H2, v1.0 Phase 4 codegen complete |
| H4 | Voss-Aware Authoring | `voss init` agent-aware templates, inline `voss check` after every `.voss` edit, `ast.search` tool. | HARN-14..17 | H3, v1.0 Phase 5 CLI ✓ |
| H5 | Eval & Telemetry | Five golden tasks run nightly; track success rate, mean cost, mean confidence on success vs. fail; opt-in anonymous telemetry. | HARN-18..21 | H4 |
| H6 | Distribution | `pip install voss` ships compiler + harness in one package; `voss[lite]` extra omits sentence-transformers/chromadb; Homebrew tap; PyInstaller binary; MCP bridge (`voss serve --mcp`). | HARN-22..24 | H5 |

---

### Phase H1: Skeleton CLI on Raw Runtime
**Goal:** Bare `voss` enters interactive agent REPL; `voss do "<task>"` produces a one-shot answer; both run against `voss_runtime` directly with no `.voss` source for the loop.

**Requirements:** HARN-01 (CLI entry + dispatcher), HARN-02 (TTY renderer + status line), HARN-03 (permission gate + sandbox), HARN-04 (NDJSON non-TTY mode)

**Success Criteria:**
1. `voss` (no args) launches REPL with banner; `Ctrl-D` or `/exit` quits cleanly
2. `voss do "<task>"` runs one turn, prints final answer to stdout, exits with status 0
3. Tool calls render as collapsed one-liners with `⏵` glyph; `--verbose` expands them
4. Status line shows model · tokens · cost · ctx %; bell + accent flip at 90% budget
5. `voss do --json` emits one NDJSON event per line (`text`, `tool_call`, `tool_result`, `final`) on a versioned envelope
6. Shell allowlist + cwd jail enforced; allowlisted commands auto-approve in `edit` mode, others prompt

**Cross-cutting constraints:**
- Compiler verbs (`compile`, `run`, `check`, `init`, `ast`) must remain unchanged. Agent verbs are additions, not replacements.
- `voss run <file.voss>` stays compiler. Agent one-shot is `voss do "<task>"`. No collision.
- Provider abstraction reuses `voss_runtime/providers/*`; harness must not introduce a parallel provider stack.

---

### Phase H2: Sessions, Semantic Memory, REPL Polish
**Goal:** Sessions persist across runs; the repo is queryable as a semantic memory; the REPL gains the slash-command surface defined in HARNESS-PLAN §2.4.

**Requirements:** HARN-05 (session save/load), HARN-06 (semantic repo index), HARN-07 (slash commands), HARN-08 (diff preview + apply), HARN-09 (config file at `~/.config/voss/config.toml`)

**Success Criteria:**
1. `/save [name]` writes episodic transcript to `~/.local/state/voss/sessions/<id>.json`; `voss resume <id|name>` rehydrates it
2. `voss sessions` lists saved sessions with `id · started · model · first task line`
3. Semantic index lives at `<cwd>/.voss-cache/repo.idx`; rebuilds on git head change
4. `/diff` previews pending edits in compact unified diff; `/apply` and `/discard` work
5. `/model`, `/budget`, `/mode`, `/cost`, `/why`, `/tools`, `/clear` all work mid-session
6. `voss config` opens config file in `$EDITOR`; project override at `.voss-cache/harness.toml`

**Cross-cutting constraints:**
- Session payloads must not contain provider API keys.
- `.voss-cache/` is gitignored at scaffold time; never check sessions into git.
- Semantic index rebuild must run in a background thread; cold REPL start is not blocked on it.

---

### Phase H3: Loop Port to Voss *(blocked on v1.0 Phase 4 codegen)*
**Goal:** Rewrite the harness's own loop in Voss. The compiler compiles its own harness — strongest possible dogfood loop.

**Requirements:** HARN-10 (`loop.voss` + `router.voss` + `planner.voss` + `executor.voss` + `reviewer.voss`), HARN-11 (`voss check` clean on `voss/harness/agent/`), HARN-12 (CI gate fails the build if compiler regresses on its own harness), HARN-13 (boot path lazily compiles `loop.voss` and caches under `.voss-cache/harness/`)

**Success Criteria:**
1. `voss/harness/agent/*.voss` exists; bare `voss` boots through compiled harness, not Python loop
2. `voss check voss/harness/agent/` produces zero warnings on green CI
3. CI job `harness-self-check` runs on every PR and is required to merge
4. Cached compiled `.py` artifacts under `.voss-cache/harness/` are reused across runs; cache invalidates on `.voss` change

**Cross-cutting constraints:**
- Agent loop must use `ctx`, `BudgetScope`, `gather`, `match similar`, `ProbableValue` — no escape hatches that bypass the language.
- Confidence calibration approach (model self-rating vs ensemble) decided in H1 spike; H3 ratifies the choice in code.

---

### Phase H4: Voss-Aware Authoring
**Goal:** When the user is writing Voss, the harness uses the compiler as a real-time peer — checks every edit, surfaces diagnostics back to the model, scaffolds new projects.

**Requirements:** HARN-14 (`voss init` agent-aware templates: classifier, support bot, research swarm), HARN-15 (post-edit `voss check` loop with diagnostics fed back to the model), HARN-16 (`ast.search` tool backed by tree-sitter Voss grammar), HARN-17 (templates lifted from PRD §7)

**Success Criteria:**
1. `voss init <name>` produces a working `.voss` project with sample agent + tests + `.gitattributes`
2. After every `fs.edit` of a `.voss` file, `voss check` runs automatically; warnings injected into next model turn
3. `ast.search(symbol="X")` returns AST positions across the project; falls back to `voss ast --json` until tree-sitter ships
4. Three templates available at `voss init --template <classifier|support|research>`

**Cross-cutting constraints:**
- Tree-sitter grammar is post-v1 in compiler roadmap. H4 must work without it via `voss ast --json` fallback; tree-sitter upgrade is non-breaking.

---

### Phase H5: Eval & Telemetry
**Goal:** Quantify the harness. Five golden tasks run nightly; track whether reported confidence correlates with success.

**Requirements:** HARN-18 (golden eval suite), HARN-19 (nightly CI run), HARN-20 (cost + confidence tracking per run), HARN-21 (opt-in anonymous telemetry, off by default)

**Success Criteria:**
1. Five golden tasks (per HARNESS-PLAN §9) committed under `voss/harness/tests/golden/`
2. Nightly GitHub Action runs evals against stub providers; pass rate ≥ 80%, mean cost-to-pass logged
3. Correlation between reported confidence and pass/fail tracked per run; trend visible across runs
4. Telemetry is off by default; first-run prompt asks consent; payload never includes user prompts or file contents

**Cross-cutting constraints:**
- No user content (prompts, file paths, source code) leaves the machine without explicit per-event consent.
- Live-provider eval runs are opt-in via `--live`; default eval uses `StubProvider`.

---

### Phase H6: Distribution
**Goal:** `pip install voss` works end-to-end; one binary, two extras, optional MCP bridge for cross-harness interop.

**Requirements:** HARN-22 (`pip install voss` ships compiler + harness; `voss[lite]` extra omits ML deps), HARN-23 (Homebrew tap + PyInstaller single-binary), HARN-24 (`voss serve --mcp` exports `@tool`-decorated Voss functions as MCP server)

**Success Criteria:**
1. `pip install voss` from PyPI exposes both compiler verbs and agent verbs
2. `pip install voss[lite]` works without sentence-transformers/chromadb; semantic memory + `match similar(...)` degrade gracefully
3. `brew install voss/tap/voss` works on macOS arm64
4. `voss serve --mcp` starts an MCP server that other harnesses (Claude Code, Cursor) can attach to and call Voss-defined tools

**Cross-cutting constraints:**
- One binary, no `vh`. CLI dispatcher in `voss.cli:main` routes both worlds.
- Lite install must not import torch, sentence-transformers, chromadb, or transformers at import time. Lazy-load only.

---

## Coverage — v1.1

| Phase | Requirements | Count |
|-------|--------------|-------|
| H1 | HARN-01..04 | 4 |
| H2 | HARN-05..09 | 5 |
| H3 | HARN-10..13 | 4 |
| H4 | HARN-14..17 | 4 |
| H5 | HARN-18..21 | 4 |
| H6 | HARN-22..24 | 3 |
| **Total** | HARN-01..24 | **24** |

All v1.1 harness requirements mapped. Detailed design lives in `.planning/HARNESS-PLAN.md`.

---

# Milestone v1.2 — Rust Harness Shell

**Added:** 2026-05-09
**Status:** Planned — gated on v1.1 H1-H5 close
**Reference:** `.planning/RUST-PORT-PLAN.md`
**Codename:** none — single `voss` binary remains; Rust replaces Python harness shell while compiler stays Python
**Tracking IDs:** RUST-01..RUST-32

The Python harness shell (`voss/harness/`) ports to a Rust binary (`crates/voss-cli/`) for cold-start, distribution, and platform-API quality. The Voss compiler and `voss_runtime` stay Python forever; Rust subprocesses to them via a long-lived JSON-RPC bridge (`voss-bridge` crate ↔ `voss/bridge_server.py`).

## Phase 7 — Rust Harness Shell

**Goal:** Replace the Python harness shell with a Rust binary at parity, ship it as a single static install, and keep the Python compiler reachable through a stable bridge.

**Requirements:** RUST-01..32

**Success Criteria:**

1. `voss --version` returns in ≤50ms cold on macOS arm64.
2. Every Python harness test in `tests/harness/` has a Rust integration equivalent in `crates/voss-cli/tests/` and passes.
3. Parity suite (`tests/parity/`) confirms byte-identical output between Python and Rust binaries for `--help`, `doctor`, `sessions`, and `--json` agent verbs.
4. Live smokes pass against Anthropic OAuth and Codex OAuth subscriptions.
5. `brew install voss/tap/voss` produces a working install where agent verbs work without Python visible to the user; compiler verbs require Python and fail with an actionable error if missing.
6. `pip install voss` continues to work and auto-downloads the matching `voss-cli` binary on first agent verb invocation.
7. `voss/harness/` (Python) deletable without breaking any user-visible feature; kept for one release as a fallback, then removed.

**Plans:** 9 plans, waves R1-R9; full design in `.planning/RUST-PORT-PLAN.md`.

| Wave | Plan | Goal | RUST IDs |
|------|------|------|----------|
| R1 | `07-01` | Cargo workspace, 7 crates scaffolded, `voss-bridge` ↔ `voss.bridge_server` round-trip working for `voss ast`. | RUST-01..04 |
| R2 | `07-02` | `voss-auth` crate: Keychain (security-framework) + file fallback discovery, refresh for both Anthropic + Codex, doctor verb at parity. | RUST-05..08 |
| R3 | `07-03` | `voss-providers`: Anthropic OAuth provider with Claude Code preamble, tool-use translation for response_format, refresh-on-401. Live smoke. | RUST-09..12 |
| R4 | `07-04` | `voss-tools`: 9 tools ported (fs_*, shell_run, git_*, voss_*). Sandbox jail + allowlist mirror Python. | RUST-13..16 |
| R5 | `07-05` | `voss-render` (Tty/Plain/Ndjson) + `permissions` interactive prompt + persisted always-allow. | RUST-17..20 |
| R6 | `07-06` | `voss-cli sessions` / `voss-cli resume` + `/save` slash command; JSON wire-compatible with Python sessions. | RUST-21..23 |
| R7 | `07-07` | `voss-agent::run_turn` parity with Python; chat REPL with line editing + slash commands + status line. | RUST-24..27 |
| R8 | `07-08` | OpenAI OAuth provider with full Codex CLI wire format (depends on `.planning/CODEX-OAUTH-PLAN.md` Phase A fixtures). | RUST-28..30 |
| R9 | `07-09` | Distribution: cargo-dist signed binaries, brew tap, pip dispatcher that auto-downloads + execs the Rust binary. | RUST-31..32 |

**Cross-cutting constraints:**
- The Rust binary never imports or links libpython. Compiler interaction is `std::process::Command` only.
- Voss compiler (`voss/parser.py`, `analyzer.py`, `codegen.py`) and `voss_runtime/*` are read-only across this milestone.
- Schema drift between Rust serde structs and Python pydantic models is a CI failure; snapshot tests enforce equivalence.
- Anthropic / OpenAI request bodies are snapshot-tested per provider; live smokes are opt-in (`--live` / nightly) and never default in CI.
- `voss/harness/` Python tree stays in the repo across this milestone; it is the fallback path that v1.2 keeps green and ships alongside the Rust binary.

## Coverage — v1.2

| Wave | Plan | RUST IDs | Count |
|------|------|----------|-------|
| R1 | 07-01 | RUST-01..04 | 4 |
| R2 | 07-02 | RUST-05..08 | 4 |
| R3 | 07-03 | RUST-09..12 | 4 |
| R4 | 07-04 | RUST-13..16 | 4 |
| R5 | 07-05 | RUST-17..20 | 4 |
| R6 | 07-06 | RUST-21..23 | 3 |
| R7 | 07-07 | RUST-24..27 | 4 |
| R8 | 07-08 | RUST-28..30 | 3 |
| R9 | 07-09 | RUST-31..32 | 2 |
| **Total** | | RUST-01..32 | **32** |

All v1.2 Rust port requirements mapped. Detailed design + dependency picks + risk register live in `.planning/RUST-PORT-PLAN.md`.

---
*Roadmap created: 2026-05-07*
*v1.1 harness milestone added: 2026-05-09*
*v1.2 Rust port milestone added: 2026-05-09*
