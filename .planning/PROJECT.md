# Voss

## What This Is

Voss is an **agent engineering organization layer**: it lets AI coding agents work like a high-performing engineering organization — scoped, budgeted, reviewed, and replayable — rather than a rigid automation pipeline. That layer sits atop two named substrates. The **harness** is the first product surface: the `voss` CLI/TUI that helps developers plan, execute, inspect, and resume AI-assisted code work in real repositories. The **`.voss` language** is the durable, compiler-checkable control layer for workflows that need explicit confidence gates, context budgets, semantic routing, tools, memory, agents, and fallbacks. See [`.planning/docs/ORCHESTRATION_LAYERS.md`](docs/ORCHESTRATION_LAYERS.md) — the canonical PRD — for the full org-layer model.

## Core Value

A developer can give Voss a repo task and get bounded, inspectable, resumable AI coding work, while the most important agent logic is expressible as compiler-checkable `.voss` workflows instead of prompt soup.

## Current Milestone: v0.1 Harness MVP

**Goal:** Ship a tight vertical slice where `voss` can safely plan, execute, inspect, and resume AI-assisted code work in a real repository, with `.voss` preserved as the workflow-control language.

**Target features:**
- M0 Scope Lock: align planning docs around harness-led v0.1 plus language control layer.
- M1 Harness Happy Path: make `voss doctor`, `voss do`, and `voss edit` usable against a real repo.
- M2 Project Cognition: persist project-local memory, plans, decisions, sessions, and validation state.
- M3 Language Validation: prove `.voss` workflows parse, check, compile, and run as the control layer.
- M4 Voss-authored Harness Loop: dogfood the harness loop under `voss/harness/agent/*.voss`.
- M5 Eval and Distribution Prep: measure quality and prepare packaging after Python harness usage is proven.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] `voss` launches an interactive harness REPL and `voss chat` remains an explicit alias.
- [ ] `voss do "<task>"` runs natural-language agent tasks; `voss run <file.voss>` remains reserved for `.voss` programs.
- [ ] `voss edit <path>` starts a scoped edit session with approval before risky changes.
- [ ] `voss doctor`, `voss tools`, `voss config`, `voss sessions`, and `voss resume [id]` support the core harness loop.
- [ ] Project-local durable state lives under `.voss/`; rebuildable machine state lives under `.voss-cache/`.
- [ ] Every agent run records task goal, plan, inspected files, changed files, avoided files, assumptions, decisions, risks, validation, failures, diff summary, and follow-ups.
- [ ] Controlled execution exposes a small safe tool registry: `fs_read`, `fs_glob`, `fs_grep`, `fs_write`, `fs_edit`, `shell_run`, `git_status`, `git_diff`, and `voss_check`.
- [ ] Execution modes `plan`, `edit`, and `auto` enforce cwd path jail, permission prompts, allow/deny/always choices, diff preview, shell allowlist, timeouts, and no secrets in session payloads.
- [ ] `.voss` remains scoped to AI workflow control, not general Python replacement.
- [ ] Core language constructs remain supported: `probable<T>`, confidence gates, `ctx`, `within budget/fallback`, `match similar`, `agent`, `spawn`, `gather`, memory primitives, `@tool`, `prompt`, `try/catch`, and `use`.
- [ ] Canonical repo-centric demo works: `voss doctor`, analyze repo, plan a change, apply approved plan, `voss check .`, and `voss resume`.
- [ ] Language demo works: `voss init support-bot`, `voss check samples/support.voss`, and `voss run samples/support.voss`.
- [ ] Harness loop can be dogfooded through `voss/harness/agent/loop.voss`, `router.voss`, `planner.voss`, `executor.voss`, and `reviewer.voss`.
- [ ] Eval and packaging work tracks golden tasks, cost, success rate, confidence correlation, and install polish.

### Out of Scope

- Full Python language parity — v0.1 is a harness plus AI workflow control language, not a Python replacement.
- Native LLVM/Wasm compilation — Python target is sufficient for the current AI ecosystem.
- TypeScript target — defer until the Python-targeted control layer proves usage.
- Package manager — use Python packaging for now.
- Debugger or full LSP — generated Python and compiler diagnostics are enough for v0.1.
- Distributed or multi-machine agents — local bounded execution first.
- Fine-tuning or training loops — inference and workflow control only.
- Cloud sync, accounts, teams, marketplace, or web UI — not needed for the first repo-centric loop.
- Split-pane TUI — terminal-native CLI is enough.
- Windows support — defer.
- Broad OSS launch campaign — behavior must be proven first.
- Rust harness shell, MCP bridge, tree-sitter grammar, VSCode marketplace release, GitHub Linguist upstream PR, and full telemetry system — strategically relevant but deferred until the Python harness proves real usage.

## Context

- **Scope lock source:** `.vscode/voss_v_0_1_scope_lock.md` is the source of truth for v0.1.
- **Product framing:** Voss should lead with "AI-native coding harness" and "programming language for agent workflows," not "Python fork" or "Python replacement."
- **Primary user:** technically capable builders using AI coding tools who want less babysitting, safer edits, persistent context, and inspectable decisions.
- **Harness-first order:** `voss/harness/` is the near-term product focus because it is the fastest path to a felt product loop.
- **Language role:** `.voss` is still central, but specifically as a compact, inspectable language for AI workflow control.
- **Rust role:** `crates/` is a **frozen spike** — preserved in source control, not on the v0.1 ship path. v0.1 distributes the Python harness via npm (M6, pyright bundled-Python pattern). Resurrect Rust only on a concrete dogfood signal (startup latency or wheel size proves painful in real use). Do not edit `crates/` or invest in keeping it building against current Python; leave it where it is until the trigger arrives.
- **Docs and marketing:** `site/` remains minimal until v0.1 behavior is locked.

## Constraints

- **CLI naming:** `voss run` executes `.voss` programs; `voss do` executes natural-language agent tasks.
- **Project state:** `.voss/` is durable project knowledge; `.voss-cache/` is rebuildable machine state.
- **Security:** controlled execution must enforce cwd path jail, permission prompts, shell allowlist, command timeouts, and no provider API keys in sessions.
- **Runtime:** Python remains the runtime/compiler target because the AI ecosystem is Python-first.
- **Compiler output:** generated Python must stay readable and import `voss_runtime`.
- **Phase naming:** v0.1 roadmap phases use `M` prefixes (`M0` through `M5`) to match the scope-lock document.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| v0.1 is harness-led | The harness is the product surface users feel first | Active |
| `.voss` is the control layer | The language is strongest when it makes AI workflow decisions explicit and checkable | Active |
| Keep compiler and harness verbs separate | Avoids ambiguity and preserves the language as a real layer | Active |
| Python harness first, Rust frozen | v0.1 ships Python via npm (M6 pyright pattern). Rust `crates/` preserved in source control as a frozen spike but explicitly not on the ship path. Resurrect only on real dogfood signal (latency / wheel size). | Active |
| `.voss/` durable, `.voss-cache/` rebuildable | Separates project knowledge from generated indexes/cache | Active |
| M-prefixed phase naming | Mirrors the v0.1 scope-lock milestone structure | Active |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone**:
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-10 after v0.1 scope lock rebaseline*
