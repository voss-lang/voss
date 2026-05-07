# Voss

## What This Is

Voss is an AI-native programming language that compiles to Python. It makes the patterns every AI app currently re-implements by hand — confidence checking, token budget management, prompt construction, semantic routing, agent lifecycle — into first-class language constructs. v1 is for the author and early adopters dogfooding it on real AI projects.

## Core Value

A program that takes 300 lines of Python boilerplate around an AI workflow takes ~40 lines of Voss, and the boilerplate semantics (confidence gates, token budgets, fallbacks) are enforced by the compiler — not re-invented per project.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] `.voss` files compile to readable Python that imports `voss_runtime`
- [ ] `probable<T>` type with `@ p >= n` confidence gates and unguarded-use compiler warnings
- [ ] `ctx(budget: N tokens)` blocks with auto-compression and `yield`
- [ ] `within budget(...) { } fallback { }` runtime-monitored execution
- [ ] `match` with `similar("...")` semantic predicates; embedding index built at compile time
- [ ] Agent primitives: `agent` definitions, `spawn`, `gather`, channels
- [ ] Memory primitives: `memory.episodic`, `memory.semantic` (chromadb), `memory.working`
- [ ] `@tool` annotation auto-generates OpenAI/Anthropic tool schema
- [ ] `prompt` classes with inheritance
- [ ] `try/catch` native Voss error handling, codegens to Python `try/except`
- [ ] `use foo::bar` import syntax for multi-file Voss programs
- [ ] Multi-provider model abstraction (Anthropic + OpenAI + Ollama) via unified runtime interface
- [ ] CLI: `voss compile`, `voss run`, `voss check`, `voss init`, `voss ast`
- [ ] Three example programs (PRD §7) compile and run end-to-end

### Out of Scope

- Native compilation (LLVM, Wasm) — Python target is sufficient for v1; AI ecosystem lives in Python
- Targets other than Python (TypeScript, etc.) — same reason
- Standard library beyond AI primitives — use Python interop
- Package manager — use pip
- Debugger / LSP / language server — post-v1
- Multi-process or distributed agents — v1 is asyncio-only
- Fine-tuning / training integrations — v1 is inference-only
- Public PyPI launch / OSS marketing — v1 is for author + early adopters; broader release is post-v1
- Editor support (Tree-sitter, VSCode ext) — Phase 6, post-v1

## Context

- **Author + early adopter audience.** v1 ships to a narrow loop. Feedback comes from dogfooding on real AI workflows, not from external users. This justifies cutting OSS launch polish from v1 scope.
- **Python-as-target is a forcing function for ecosystem leverage.** LangChain, OpenAI/Anthropic SDKs, vector DBs, sentence-transformers — all available immediately. Voss is typed syntax sugar over a powerful runtime library.
- **Runtime-first build order.** Per PRD §13: build `voss_runtime` and exercise it with hand-written Python before writing any compiler. Locks in semantics before syntax.
- **The five constructs are the pitch.** `probable<T>`, `ctx`, `within/fallback`, semantic `match`, agent primitives. If these don't feel right when used, nothing else matters.

## Constraints

- **Tech stack**: Python 3.11+ — `match` statement support required; matches modern AI lib floor
- **Parser**: Lark — pure-Python, fast to prototype, good error messages
- **Embedding model (compile-time)**: sentence-transformers `all-MiniLM-L6-v2` — local, no API key at compile time
- **Vector store (semantic memory)**: ChromaDB local — zero-config, upgradeable
- **Default LLM**: claude-sonnet-4-5 — best capability/cost ratio at PRD time; user-configurable
- **Concurrency**: asyncio only — no multi-process, no distributed agents in v1
- **Codegen target**: readable, debuggable Python (not minified) — debugging Voss = reading the .py output
- **Audience**: author + early adopters — v1 doesn't need PyPI publication, marketing, or polished onboarding

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Compile to Python (not native) | AI ecosystem lives in Python; no new runtime needed | — Pending |
| Lark parser generator | Pure Python, fast prototyping, good error messages | — Pending |
| Multi-provider model abstraction in v1 | Lock-in risk if Anthropic-only; abstraction now is cheap | — Pending |
| Compile-time embedding indexes in `.voss-cache/` | Separate gitignored dir, multiple files OK, easy to nuke | — Pending |
| Native Voss `try/catch` syntax (not Python interop only) | First-class error handling matches the language's "constructs not patterns" philosophy; codegens to Python `try/except` | — Pending |
| `use foo::bar` import keyword (not Python-style `import`) | Distinct Voss syntax signals Voss-aware module resolution; compiles to Python imports under the hood | — Pending |
| Build runtime library before compiler | Locks in runtime semantics before syntax; lets us validate the design with hand-written Python | — Pending |
| Audience = author + early adopters for v1 | Lets v1 ship faster; PyPI/OSS launch deferred post-v1 | — Pending |
| Success metric = three PRD §7 examples run end-to-end | Concrete, testable, covers all five core constructs | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-07 after initialization*
