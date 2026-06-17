# Swarm Reconciliation Spike — A13 vs V25 (and the frontend)

**Created:** 2026-06-17 · **Status:** design spike, no code · **Trigger:** swarm `Role.model` sentinel bug surfaced that a swarm member has no "which agent" axis.

## DECISION (2026-06-17)

**Chosen end-state: R3 — all-CLI swarm, V25 as backing services.**
**CLI ownership: fs-watch detect + flag/revert.**

Every swarm member is a real pane CLI (claude/codex/opencode/…). Coordination is the
A13 **file-bus, kept live**. V25 is demoted from "the runtime" to "the server spine":
SwarmStore (state), overlap validation, events.jsonl audit, operator escalation.
This **inverts the V25 SPEC's "supersedes A13's file-bus" claim** — under R3 the file-bus
is the live transport and V25's SSE/spawn-gate/in-process-ownership machinery is set
aside for member coordination (SSE is repurposed host→GUI only). See "R3 Concrete Plan"
at the bottom for what is kept, dropped, and net-new.

## TL;DR

V25's SPEC already declared "**Supersedes A13's file-bus transport**." That decision is
only *half* valid. V25 silently swapped the definition of a swarm **member** — from
A13's *external CLI* (claude/codex/opencode) to a *voss-native ServerSession keyed by
model* — and in doing so **dropped the heterogeneous-agent axis that was A13's entire
reason to exist and is the product's core UX** (the wizard "Add AI coding agents", the
`agent_registry.cli_binary` column, A13 D-16 "coordinator picks the CLI per subtask").

A third-party `codex` CLI in a terminal pane **cannot subscribe to voss's SSE bus**. It
only speaks files + stdin. So V25's server+SSE coordination reaches **only native
members**. The moment a real Codex/Claude-Code CLI is a swarm member, V25's transport
does not reach it. "Supersedes A13" is true for native members and **false for CLI
members** — for which the file-bus is still the only channel.

## Current state: THREE member models, none agree

| Layer | "Member" shape | Which-agent axis? | Create path? |
|-------|----------------|-------------------|--------------|
| **Frontend** `org/swarmReconcile.ts` (V14-07) | A13 manifest `{cli, paneId, task, status}` | **yes — `cli`** | reads `.voss/swarm/manifest.json` it does not produce |
| **Frontend** `org/live/swarmClient.ts` | V25 server snapshot | n/a | **GET /swarm/{id} only — no POST** |
| **Runtime** `voss/harness/swarm_store.py` (V25) | `Role{name, model, auth_pref}` → ServerSession + `run_turn` | **no — model only** | `POST /swarm` (API only, no GUI) |
| **Rust** `crates/voss-app-core/src/agent_registry.rs` | row `{cli_binary, pane_id, session_id, swarm_id, role, owned_files}` | **yes — `cli_binary`** | `register_agent` on pane launch |

The which-agent axis exists in the **frontend reconciler** and the **Rust registry** —
the two layers built around the terminal-pane agent picker — and is **absent in the one
layer that actually runs the swarm** (V25 runtime). VSWARM-08 even says "builders=Codex"
but implements it as a *model id* through litellm/codex-oauth, not as "spawn the Codex
CLI." VSWARM-09 binds a *ServerSession* to a pane whose registry column is `cli_binary`
(built for external CLIs). Both are seams where model-thinking and agent-thinking meet
and don't fit.

## Why A13's file-bus existed (and why "demote to audit-only" is wrong for CLI members)

A13 D-01: *file-mediated communication "works with any CLI agent without modification."*
The file-bus is not an accident of "no daemon" — it is the **only IPC a black-box
third-party CLI offers**. V25's framing ("Voss has a daemon, so none of that is
necessary") holds **only if the member is voss's own loop**, which can subscribe to SSE
and be spawn-gated in-process. It does not hold for `claude`/`codex`/`opencode`
binaries.

## Answer to "is there a swarm setup menu to invoke the proper agent?"

- **Pick a CLI agent per terminal pane** (the screenshots / A12 wizard): yes — feeds the
  pane-launch + `agent_registry`, **not a swarm**.
- **Set up a coordinated swarm with role → agent**: **no.** A13 designed it (modal Swarm
  tab D-15, coordinator-picks-agent D-16) — unbuilt. V25 shipped a swarm but it is
  API-only, `default_roster`, **model-only, no agent axis, no create-from-GUI** (frontend
  can only `GET`).

## Three coherent end-states

### R1 — Native-only swarm (drop heterogeneous CLIs as members)
Swarm members are always voss-native ServerSessions; they differ only by model + auth.
The wizard's claude/codex CLIs stay **standalone panes, never swarm members**.
- **Pro:** ~90% built; V25 stands as-is; one transport (SSE); spawn-gate + ownership clean.
- **Con:** Contradicts the product framing ("launch a coordinated team of agents —
  Claude, Codex, OpenCode") and A13 D-16. You can never coordinate a *real* Codex CLI —
  only voss's loop pointed at a Codex model. Frontend reconciler (A13 manifest/`cli`) and
  registry `cli_binary` become dead/secondary for swarms.

### R2 — Two member *kinds* under one V25 runtime  ★ recommended
V25 stays the single source of truth (SwarmStore, ownership, audit, operator escalation).
`Role`/`Task` gain a **member-kind axis**:
- `kind = native` → ServerSession + `run_turn` + SSE (today's path; `model`+`auth_pref`).
- `kind = cli`    → spawn an external CLI in a pane (`agent_registry.cli_binary` + args),
  coordinate via the **A13 file-bus kept LIVE for these members** (task file in →
  fs-watch → result file out), because files are the only channel the CLI has.

One store, one ownership model, one audit log; **transport per member kind** — SSE where
possible (native), files where required (CLI). A13's file protocol is *not* demoted to
audit-only; it is the live transport **for CLI members specifically**. Coordinator (D-16)
can assign the right kind per subtask.
- **Pro:** Honest reconciliation; keeps both strengths; matches product UX + registry +
  frontend reconciler; the file-bus survives exactly where it's still needed.
- **Con:** Most design surface — two spawn paths, two completion-detection paths
  (SSE `worker_done` vs result-file watch), ownership enforced two ways (PermissionGate
  for native, advisory-or-wrapper for CLI since a black-box CLI can't be gated in-process).

### R3 — All-CLI / pane-native (A13 wins, V25 is backing services)
Every member is a pane CLI; V25 SwarmStore/ownership/audit back it; coordination is
file-bus always.
- **Pro:** One member model; maximal CLI heterogeneity.
- **Con:** Throws away V25's spawn-gate + SSE + in-process ownership for native members;
  re-introduces the fs-watch/nudge races V25 was built to kill.

## Recommendation

**R2.** It is the only end-state where "a coordinated team of Claude + Codex + OpenCode"
(the stated product) and "server-native, race-free, gate-enforced" (V25's wins) are both
true. R1 is the cheap path if we consciously decide swarms are voss-native-only and the
wizard agents stay solo panes — a legitimate but narrower product.

### The hard sub-problem R2 must answer
**Ownership enforcement for CLI members.** V25's killer feature (VSWARM-05: deny writes
outside `ownedFiles` at `PermissionGate`) works because native members route every write
through voss's toolset. A black-box `codex` CLI writes to disk directly — voss cannot gate
it in-process. Options: (a) advisory only (A13's original "Do NOT modify…" instruction —
unenforced), (b) post-hoc detection via fs-watch + revert/flag on out-of-scope writes,
(c) run CLI members in a sandbox/overlay that intercepts writes. This choice gates whether
R2's ownership guarantee is real or advisory for CLI members.

## Decision needed before any code
1. R1, R2, or R3?
2. If R2: ownership enforcement for CLI members — advisory / fs-watch-detect / sandbox?
3. Who creates the swarm from the GUI (the missing menu)? New "Swarm" launch surface that
   `POST /swarm` with an explicit roster (role → kind → agent/model/auth or command).
4. Frontend: collapse the two swarm readers (A13-manifest reconciler vs V25 `GET /swarm`)
   onto one shape — almost certainly the V25 server snapshot, extended with the member
   kind/agent axis.

## Note on the shipped fix
The `Role.model` sentinel fix (`_effective_model` in `server/app.py`) is correct and
needed under **all** options — it makes native members resolve a real model and honor an
explicit one. It does not address the agent axis because `Role` has none yet; that is the
R2 design work above.
