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
*Roadmap created: 2026-05-07*
