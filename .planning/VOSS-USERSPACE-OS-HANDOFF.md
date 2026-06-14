# Handoff: Voss as Agent Operating System (userspace ABI)

**Created:** 2026-06-14  
**Origin:** Exploratory thread — “What would a Voss-powered operating system written in C look like? Is this worth thinking about?”  
**Status:** Concept / architecture exploration — **not** a committed roadmap phase. No implementation started.  
**Recommended next step:** Draft `VOSS-USERSPACE-ABI.md` (or spike in `.planning/docs/`) defining the userspace “OS layer” Voss should own vs. delegate to the host OS.

---

## Executive summary (for the next model)

**Do not build a C kernel.** Voss’s credible “OS” story is a **userspace agent supervisor** on top of Linux/macOS — not a bootable microkernel.

The product wedge (v0.1+) is an **agent engineering organization layer**: scoped, budgeted, reviewed, replayable AI coding work in real repos. A literal OS diverts from that.

**Do develop** the metaphor into concrete architecture:

| Host OS owns | Voss “OS” owns |
|--------------|----------------|
| PTY, TTY, signals | Cell/agent lifecycle (spawn, wait, kill, tree) |
| Filesystem, network, GPU | Capability-based tool access + permission prompts |
| Process isolation (POSIX) | Token budgets, scope, sandbox policy |
| — | Project cognition (`.voss/`, `.voss-cache/`) |
| — | Audit trail, replay, reviewer gates |

Native code in-repo trends **Rust** (`crates/voss-app-core`, PTY, future IPC) — not C. C only matters for embedded/FFI edge cases.

---

## Three interpretations of “Voss OS” (pick one per doc)

### A. Literal kernel in C — **reject for product**

- Bootable system with syscalls like `agent_spawn()`, `cap_grant()`, `budget_set()`.
- Multi-year effort; fights harness MVP; duplicates containers/seccomp/PTY.
- Only justified if agents run **untrusted native code** needing hardware-enforced isolation — explicit **non-goal** near term.

### B. OS metaphor — **already in the repo**

Voss PRD/recursive architecture already maps org primitives to OS concepts:

| OS | Voss (existing / planned) |
|----|---------------------------|
| Processes | Harness subagents, voss-app “cells” (L2+) |
| Capabilities | `voss/harness/tools.py`, permission gate |
| Memory | `.voss/` cognition, `.voss-cache/` |
| rlimits / cgroups | Token budgets, context windows, scope |
| Audit log | Recorder, session tree (O-track) |
| init / supervisor | EM loop, board gates, reviewers |
| Shell | `voss do`, REPL, PTY panes |

Canonical product identity: `.planning/docs/ORCHESTRATION_LAYERS.md` — “agent engineering organization layer,” six primitives (Capabilities, Principles, Orchestration, Roles, Memory, Verification).

### C. Userspace platform — **the path to develop**

Stack as designed today + forward roadmap:

```
┌─────────────────────────────────────────┐
│  voss-app (Tauri + Solid) — grid UI     │  apps/voss-app/
├─────────────────────────────────────────┤
│  Cell supervisor + event bus (L2, Rust)   │  crates/voss-app-core/ (+ future ipc)
├─────────────────────────────────────────┤
│  Harness — CLI, permissions, sandbox    │  voss/harness/
├─────────────────────────────────────────┤
│  .voss language → Python runtime        │  voss/, voss_runtime/
├─────────────────────────────────────────┤
│  Host OS — Linux / macOS / Windows      │
└─────────────────────────────────────────┘
```

**voss-app build order (locked):** L1 terminal grid (no Voss) → L2 promote pane to cell → L3 `.voss` DSL wiring. See `apps/voss-app/CONCEPT.md`.

---

## What already exists (ground truth for design)

### Product / planning

| Artifact | Role |
|----------|------|
| `.planning/PROJECT.md` | v0.1 harness MVP; `.voss` as control layer |
| `.planning/docs/ORCHESTRATION_LAYERS.md` | Canonical PRD; non-goals; six primitives; L0–L4 recursion |
| `.vscode/voss_v_0_1_scope_lock.md` | “Harness is product surface; language is control plane” |
| `apps/voss-app/CONCEPT.md` | Desktop ADE; cell = subprocess `voss --ipc-mode jsonl`; event bus L2 |

### Harness (Python) — closest to “kernel policy”

| Module | OS analogue |
|--------|-------------|
| `voss/harness/subagents.py` | `SubagentSpec`, `run_subagent` — process-like agents |
| `voss/harness/permissions.py` | Capability gate; modes; prompts |
| `voss/harness/sandbox.py` | Execution boundary |
| `voss/harness/lifecycle.py` | Background jobs, supervisor task, tree-kill, reap |
| `voss/harness/recorder.py` | Audit / replay substrate |
| `voss/harness/team.py` | `.voss team{}` roles |
| `voss/harness/cli.py` | Main CLI surface (~5k lines) |

### Runtime / language

| Module | Role |
|--------|------|
| `voss_runtime/` | Confidence, context, budget, semantic match, memory, agents, tools |
| `voss/` | Parser, analyzer, codegen to Python |
| `PRD.md` | Historical language PRD (superseded for product identity by ORCHESTRATION_LAYERS) |

### Native (Rust)

| Crate | Role |
|-------|------|
| `crates/voss-app-core/` | PTY registry, spawn/write/resize, OSC budget/context telemetry |
| `crates/voss-app-core/src/pty/commands.rs` | `BudgetData`, `ContextData`, `PtyEvent` — already streams “resource telemetry” over IPC |
| `crates/voss-app-ipc/` | **Planned L2, not created yet** per CONCEPT.md |

### OSC telemetry (bridge UI ↔ harness semantics)

Harness can emit budget/context via terminal OSC sequences; Rust side parses into typed structs (`BudgetData`, `ContextData` in `commands.rs`). This is an early “/proc-like” interface for agent resource state.

---

## Explicit non-goals (do not contradict)

From `ORCHESTRATION_LAYERS.md` §3.2:

- Generic chatbot wrapper
- Pure workflow DSL only
- Weak-audit “swarm” demo
- **Replacement for all programming languages**
- Fully autonomous deploy/delete/money without human confirmation
- **Distributed multi-machine agent system in the near term**

Scope lock adds: not “full Python fork,” not general-purpose language replacement.

---

## Open design questions (for next session)

1. **ABI boundary:** What is the stable contract between cell supervisor (Rust) and harness subprocess (Python)? CONCEPT says JSONL over stdio + Unix socket event bus — spec is deferred to L2 design phase.

2. **Capability model:** Should capabilities be strings (`tool:file_write`), paths, or structured scopes? Align with existing `PermissionGate` + `permissions.yml` + cognition schemas.

3. **Process tree vs. session tree:** O-track session tree vs. POSIX process tree — one mapping or two layers?

4. **Identity:** `VOSS_AGENT_ID` (V17 coordination) vs. cell ID vs. subagent handle — unify or namespace?

5. **Kill semantics:** Reuse `lifecycle.py` patterns (`start_new_session`, `killpg`, supervisor watchdog) for cells?

6. **Memory mount points:** What is “mounted” into an agent — files, cognition bundle, principles, team config? Read-only vs. writable?

7. **Verification as syscall:** Should “exit success” require board gate pass, or is that orchestration-layer only?

8. **C vs Rust:** If any native supervisor code ships, default is Rust in `crates/`. Document when C would be considered (embedded, libc-only environments).

---

## Suggested deliverables (pick based on user intent)

### Option 1 — Architecture doc (recommended first)

Create `.planning/docs/VOSS-USERSPACE-ABI.md` covering:

- Glossary: cell, agent, session, capability, budget, mount, gate
- Lifecycle: `spawn`, `attach`, `promote`, `signal`, `wait`, `reap`
- IPC: JSONL message types (align with existing harness server/protocol if any)
- Event bus: cell-to-cell events (`turn_end`, etc. from CONCEPT.md)
- Permission flow: deny-by-default, prompt, audit record
- Mapping table: ABI concept → existing file/function
- Non-goals and host OS delegation

### Option 2 — Spike diagram

Mermaid or ASCII for: user action → voss-app → supervisor → harness subprocess → tools → host OS.

### Option 3 — Kernel thought experiment (research only)

Separate doc `VOSS-KERNEL-THOUGHT-EXPERIMENT.md` — syscall table, microkernel split, **clearly marked not on roadmap**. Keeps creative exploration from polluting product docs.

### Option 4 — Align with voss-app L2

When A11 (v0 terminal) ships, L2 needs cell supervisor + IPC crate. This handoff feeds **A-track successor / L2 spec**, not a new O-track.

---

## Thought-experiment syscall table (research only — not product)

```c
/* NOT a commitment — illustrates what kernel-deep would mean */
pid_t   agent_spawn(const struct agent_spec *);
int     agent_send(pid_t, const void *msg, size_t len);
int     agent_gather(pid_t[], size_t n, struct result *);
int     cap_grant(pid_t, cap_t tool, const struct scope *);
int     budget_set(pid_t, struct token_budget);
int     audit_read(uint64_t from_seq, struct audit_entry *, size_t *);
```

Userspace would still run harness + models. Kernel only pays off for untrusted native agent code or global token scheduling across hardware — both deferred.

---

## Key files to read first

```
.planning/docs/ORCHESTRATION_LAYERS.md   # product truth
.planning/PROJECT.md                      # v0.1 milestone
apps/voss-app/CONCEPT.md                  # L1/L2/L3 layers, cell model
voss/harness/permissions.py
voss/harness/subagents.py
voss/harness/lifecycle.py                 # supervisor / job patterns
voss/harness/sandbox.py
crates/voss-app-core/src/pty/commands.rs  # BudgetData, ContextData, PtyEvent
.planning/TUI-FIXES-HANDOFF.md            # example handoff format in-repo
```

Search hooks: `SubagentSpec`, `PermissionGate`, `run_subagent`, `PtyEvent`, `BudgetUpdate`, `promote to cell`, `jsonl`.

---

## Prior conversation conclusions (do not re-litigate unless user asks)

1. **Worth thinking about** as userspace OS architecture and naming — informs voss-app L2 and harness APIs.
2. **Not worth building** as a C kernel product bet for Voss v0.x–v1.x.
3. **Product promise** is already OS-shaped: “scoped, budgeted, reviewed, replayable” agent work.
4. **Language choice:** Rust for native supervisor; Python harness; `.voss` compiles to Python; C irrelevant unless user explicitly wants embedded research.

---

## User intent (inferred)

Ben wants to **develop the idea further** — likely into a concrete userspace ABI / architecture doc that connects the “Voss OS” metaphor to implementation (voss-app cells, harness lifecycle, permissions, audit) without derailing the harness MVP.

**Ask the user** if unclear:

- Architecture doc only vs. prototype code?
- Tie to voss-app L2 timeline vs. standalone research?
- Audience: internal design vs. public developer docs (`site/docs/`)?

---

## Verification for “done” on architecture pass

- [ ] Every ABI primitive maps to existing code or a named roadmap phase (A/L/O/V/M).
- [ ] Non-goals section matches ORCHESTRATION_LAYERS.md.
- [ ] No implied commitment to C kernel or new language runtime.
- [ ] Cell IPC design compatible with `apps/voss-app/CONCEPT.md` L2 (subprocess-per-cell, JSONL stdio).
- [ ] Permission/budget/replay story consistent with harness + `BudgetData`/`ContextData` telemetry.

---

## Do not redo

- Re-derive “what is Voss” from scratch — use ORCHESTRATION_LAYERS.md.
- Propose replacing Python harness with a C runtime — contradicts compile-to-Python strategy and v0.1 scope.
- Merge this into ROADMAP.md without explicit user approval — this is exploratory until promoted.
