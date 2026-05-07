# Requirements: Voss

**Defined:** 2026-05-07
**Core Value:** A program that takes 300 lines of Python boilerplate around an AI workflow takes ~40 lines of Voss, and the boilerplate semantics (confidence gates, token budgets, fallbacks) are enforced by the compiler — not re-invented per project.

## v1 Requirements

### Runtime

- [ ] **RUN-01**: `ProbableValue[T]` class with `value`, `confidence`, `gate(threshold)`, and `__matmul__` overload for `value @ 0.85` syntax
- [ ] **RUN-02**: `ContextScope` context manager with token budget tracking, `add(content, compression)` and `ask(prompt, return_type)` methods
- [ ] **RUN-03**: `BudgetScope` context manager enforcing token + latency + cost limits; raises `BudgetExceededError`
- [ ] **RUN-04**: `SemanticMatcher` with sentence-transformers backend, configurable threshold, returns label of first case above threshold
- [ ] **RUN-05**: `VossAgent` abstract base class + `AgentHandle` + async `gather(handles, timeout)` for concurrent agent execution
- [ ] **RUN-06**: `EpisodicMemory` with capacity, `add(message, role)`, `last(n)`, auto-summarize when full
- [ ] **RUN-07**: `SemanticMemory` backed by ChromaDB local, with `add(text, metadata)` and `retrieve(query, top_k)`
- [ ] **RUN-08**: `WorkingMemory` scratchpad with `set/get/clear`, cleared after each ctx block
- [ ] **RUN-09**: `@tool` decorator auto-generates JSON schema compatible with OpenAI and Anthropic tool-calling APIs
- [ ] **RUN-10**: Multi-provider model abstraction supporting Anthropic, OpenAI, and Ollama via unified runtime interface
- [ ] **RUN-11**: Runtime test suite covers all classes; PRD §7 examples can run as hand-written Python using runtime directly

### Grammar

- [ ] **GRAM-01**: Lark grammar (`grammar.lark`) covers full syntax from PRD §3 (probable, ctx, within/fallback, match similar, agent, spawn/gather, memory types, @tool, prompt, try/catch, use)
- [ ] **GRAM-02**: AST node dataclasses for every language construct
- [ ] **GRAM-03**: Lark tree → Voss AST transformer
- [ ] **GRAM-04**: Parser produces valid AST for all PRD §7 example programs without error
- [ ] **GRAM-05**: Parser test suite (round-trip every example program)

### Analysis

- [ ] **ANLY-01**: Type checker emits warning when `probable<T>` is used in a context expecting `T` without an explicit confidence gate, with line numbers
- [ ] **ANLY-02**: Token budget estimator statically warns when a `ctx` block code path likely exceeds declared budget
- [ ] **ANLY-03**: Compile-time embedding index generator pre-computes embeddings for all `similar()` cases and stores indexes in `.voss-cache/`

### Codegen

- [ ] **GEN-01**: Codegen emits Python for every language construct (probable, ctx, within/fallback, match similar, agent, spawn/gather, memory types, @tool, prompt, try/catch, use)
- [ ] **GEN-02**: Generated Python is readable and debuggable (not minified)
- [ ] **GEN-03**: Voss `try/catch` codegens to Python `try/except`
- [ ] **GEN-04**: Voss `use foo::bar` codegens to Python `import` statements with correct module resolution
- [ ] **GEN-05**: Codegen test suite (compile → run → verify output for all example programs)

### CLI

- [ ] **CLI-01**: `voss compile myprogram.voss` produces a runnable `myprogram.py`
- [ ] **CLI-02**: `voss run myprogram.voss` compiles and executes in one step
- [ ] **CLI-03**: `voss check myprogram.voss` lints without compiling and reports unguarded `probable<T>` usage with line numbers
- [ ] **CLI-04**: `voss init my-project` scaffolds a new Voss project
- [ ] **CLI-05**: `voss ast myprogram.voss` prints the AST for debugging
- [ ] **CLI-06**: `pyproject.toml` with correct dependencies; package installable via `pip install` (locally or from GitHub)

### Examples

- [ ] **EX-01**: `classify.voss` (PRD §7.1) compiles and runs end-to-end (probabilistic classification with confidence gate)
- [ ] **EX-02**: `support.voss` (PRD §7.2) compiles and runs end-to-end (semantic routing + ctx blocks + prompt classes)
- [ ] **EX-03**: `research.voss` (PRD §7.3) compiles and runs end-to-end (agent spawn/gather + within/fallback)

## v2 Requirements

### Editor

- **EDIT-01**: Tree-sitter grammar for syntax highlighting
- **EDIT-02**: VSCode extension (highlighting + snippets)
- **EDIT-03**: LSP server for inline type errors

### Distribution

- **DIST-01**: Public PyPI release with marketing/onboarding polish
- **DIST-02**: Public README with quickstart targeting external users

### Memory-augmented Examples

- **EX2-01**: `assistant.voss` (PRD §7.4) memory-augmented assistant compiles and runs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Native compilation (LLVM, Wasm) | Python target sufficient for v1; AI ecosystem lives in Python |
| Targets other than Python (TypeScript, etc.) | Same as above |
| Standard library beyond AI primitives | Use Python interop |
| Package manager | Use pip |
| Debugger | Generated Python is readable; debug via standard Python tools |
| Multi-process / distributed agents | v1 is asyncio only |
| Fine-tuning / training integrations | v1 is inference only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RUN-01 | Phase 1 | Pending |
| RUN-02 | Phase 1 | Pending |
| RUN-03 | Phase 1 | Pending |
| RUN-04 | Phase 1 | Pending |
| RUN-05 | Phase 1 | Pending |
| RUN-06 | Phase 1 | Pending |
| RUN-07 | Phase 1 | Pending |
| RUN-08 | Phase 1 | Pending |
| RUN-09 | Phase 1 | Pending |
| RUN-10 | Phase 1 | Pending |
| RUN-11 | Phase 1 | Pending |
| GRAM-01 | Phase 2 | Pending |
| GRAM-02 | Phase 2 | Pending |
| GRAM-03 | Phase 2 | Pending |
| GRAM-04 | Phase 2 | Pending |
| GRAM-05 | Phase 2 | Pending |
| ANLY-01 | Phase 3 | Pending |
| ANLY-02 | Phase 3 | Pending |
| ANLY-03 | Phase 3 | Pending |
| GEN-01 | Phase 4 | Pending |
| GEN-02 | Phase 4 | Pending |
| GEN-03 | Phase 4 | Pending |
| GEN-04 | Phase 4 | Pending |
| GEN-05 | Phase 4 | Pending |
| CLI-01 | Phase 5 | Pending |
| CLI-02 | Phase 5 | Pending |
| CLI-03 | Phase 5 | Pending |
| CLI-04 | Phase 5 | Pending |
| CLI-05 | Phase 5 | Pending |
| CLI-06 | Phase 5 | Pending |
| EX-01 | Phase 6 | Pending |
| EX-02 | Phase 6 | Pending |
| EX-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 after initial definition*
