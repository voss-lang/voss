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

## Decisions (all resolved 2026-06-17)
1. **End-state: R3** — all-CLI swarm, V25 as backing spine. ✅
2. **CLI ownership: fs-watch detect + flag/revert**, substrate = **git worktree per
   member** (see resolved section above). ✅
3. **Watch/enforcement plane: the Python `voss serve` server.** ✅ — see resolution below.
4. **GUI swarm-create menu:** new "Swarm" launch surface (A13 D-15) reusing the existing
   agent picker → `POST /swarm` with explicit roster (role → cli-agent → model/args →
   ownedFiles). Build item, no further decision needed.
5. **Frontend convergence:** collapse the two readers onto the V25 `GET /swarm` snapshot,
   extended with the cli/agent axis (which makes it shape-compatible with the existing
   `swarmReconcile.ts` manifest reader). Build item.

### RESOLVED (2026-06-17): execution plane vs enforcement plane
**Two spawn impls, ONE enforcement impl.**
- **Python `voss serve` server = control + enforcement plane.** Owns SwarmStore, coordinator
  decompose, overlap validation, audit, escalation — AND the fs-watch + worktree lifecycle
  + ownership detect/revert. Rationale: enforcement must work **headless** (no Tauri app),
  it belongs next to the overlap validator + audit that back it, and the libs are already
  vendored (`watchdog` + `watchfiles` both present in the venv) so no new dep. The server
  creates each member's worktree and hands the path out to be spawned into.
- **Rust/Tauri = execution plane only.** Owns PTY spawn + grid pane binding +
  `agent_registry`, and reports pane/PTY lifecycle to the server. It already owns PTY
  (`voss_app_core::pty`) and carries **no fs-watch crate** (none in Cargo today) — so
  putting the watcher in Python avoids adding `notify` to Rust.
- **Spawn has two backends, enforcement has one:** GUI mode → Rust spawns the CLI in a pane
  (into the server-provided worktree); headless mode → the server spawns the CLI as a
  subprocess directly (A13's original spawn). Either way the **same server-side watcher**
  enforces ownership, so the guarantee is identical with or without the GUI.

## R3 Concrete Plan (the chosen path)

### What V25 KEEPS (the backing spine)
- **SwarmStore** as server-side source of truth (roster, tasks, lifecycle states).
- **VSWARM-06 overlap validation** — still reject tasks whose `ownedFiles` overlap
  unless `dependsOn`-ordered. More important under R3, since it's the *only* a-priori
  ownership guard.
- **VSWARM-11 events.jsonl** append-only audit/replay.
- **VSWARM-10 operator escalation** — but the *trigger* moves from PermissionGate deny to
  the fs-watch ownership violation (below). Decision markdown recording unchanged.
- **agent_registry** (`cli_binary`, `swarm_id`, `role`, `owned_files`) — now the *primary*
  member record, not a thin binding. This is finally the canonical member shape.

### What V25 DROPS / repurposes (member coordination)
- **VSWARM-04 SSE spawn-gate** → replaced by file-existence gating: a member is spawned
  only when its `tasks/<role>.task.md` exists. Deterministic without asyncio.Event.
- **VSWARM-05 in-process PermissionGate ownership** → impossible for black-box CLIs;
  replaced by fs-watch detect+flag/revert.
- **VSWARM-02 SSE to member sessions** → CLIs don't subscribe; SSE becomes **host→GUI
  only** (drives SwarmMap/cockpit from SwarmStore mutations + fs-watch).
- **VSWARM-07 per-turn recall injection** → can't inject into a CLI's turn; instead bake
  task-scoped recall into `tasks/<role>.task.md` + `shared/context.md` at decompose time.
- **run_turn / per-role ModelProvider** → N/A. `Role.model` becomes a **CLI flag**
  (`claude --model …`, `codex -m …`). The shipped `_effective_model` sentinel fix still
  applies for any native coordinator call, and its model-resolution logic is the template
  for resolving a member's `--model` flag.

### Net-new for R3
1. **`Role` gains the agent axis** — `{name, agent/cli, model, args, owned_files}`.
   `agent` = which CLI (claude|codex|opencode|grok|antigravity|bridgecode|custom command).
   This is the field the runtime never had and the whole bug surfaced.
2. **Coordinator** — server-side single LLM call (A13 D-03): goal → 2–6 tasks with
   `ownedFiles` + per-task agent choice (D-16) → writes task files + seeds SwarmStore.
   Reuse `_effective_model` for the coordinator's own model.
3. **File-bus writer/reader** — host writes `tasks/*.task.md` from SwarmStore; fs-watch on
   `results/*.result.md` for completion (+ PTY-idle fallback, SWM-06); parse frontmatter
   back into SwarmStore → emit SSE to GUI.
4. **Ownership watcher (fs-watch detect + flag/revert)** — see below.
5. **Swarm setup menu** — the missing GUI. A "Swarm" launch surface (A13 D-15) reusing the
   existing agent picker (the wizard screenshots) for per-role CLI choice → `POST /swarm`
   with an explicit roster → coordinator decompose → spawn N CLI panes (apply swarm grid
   preset, SWM-10 / `layouts.rs`).
6. **Frontend convergence** — `swarmReconcile.ts` (A13 manifest, `cli`-based) is now the
   *correct* shape. Extend `GET /swarm` (`swarmClient.ts`) to return the same cli-based
   snapshot from SwarmStore; collapse the two readers onto it.

### Ownership watcher — fs-watch detect + flag/revert (the hard part)
Concurrent CLIs in the same cwd make per-member write **attribution** the core problem.
Recommended substrate: **git worktree per member** — each CLI works in its own checkout.
Then:
- Writes are naturally **attributable** (which worktree changed) and **revertible**
  (`git checkout`/`restore` in that worktree).
- A write touching a path outside the member's `ownedFiles` → emit `swarm.needs_operator`
  (reuse VSWARM-10 escalation) + revert that file in the member's worktree.
- Fan-in becomes a **merge** of member worktrees, where `ownedFiles` disjointness (already
  validated by VSWARM-06) guarantees conflict-free merge.
This turns "flag/revert" from a fragile mtime-diff heuristic into a clean git operation,
and makes overlap validation load-bearing at merge time.

#### RESOLVED (2026-06-17): git worktree per member
Single-cwd + snapshot-diff was rejected — its attribution is heuristic and racy under
concurrent writes (two CLIs writing near-simultaneously is the exact failure mode), and a
heuristic revert can clobber another member's legit concurrent write. R3's entire
ownership guarantee rests on reliable attribution + revert, so the principled substrate
wins. Grounding: `voss/layout.py:derive_layout` already does full git-worktree detection
(`is_worktree`, git-dir vs common-dir), so the toolchain is worktree-aware today.

Mechanics:
- Each member's cwd is its own `git worktree add` checkout. Writes are attributable (which
  worktree changed) and revertible (`git restore` in that worktree).
- Out-of-`ownedFiles` write → `swarm.needs_operator` (reuse VSWARM-10) + revert in that
  worktree.
- **Fan-in = merge of member worktrees.** VSWARM-06 `ownedFiles` disjointness → conflict-
  free merge.
- **File-bus stays in the MAIN checkout's `.voss/swarm/<id>/`** (shared, not per-worktree).
  Members never read `.voss` themselves — the host passes each CLI its task inline (CLI
  positional arg / prompt) and an absolute result-file path. Keeps members hermetic in
  their worktree.
- Open follow-up (build-time, not blocking): shared-artifact strategy for worktrees
  (node_modules / build cache) — symlink shared dirs or accept per-worktree setup cost.

### Honest cost of R3 (acknowledged, decided)
V25-01..06 shipped today; R3 sets aside its SSE spawn-gate + in-process ownership for member
coordination and re-bases on the file-bus those phases were built to replace. The
SwarmStore/overlap/audit/escalation work is reused; the spawn-gate (VSWARM-04) and
PermissionGate ownership (VSWARM-05) implementations are effectively superseded for CLI
members. The 2-builder e2e test (V25-06) will need rewriting against the file-bus path.

## Implementation status (2026-06-17) — R3 server plane shipped

Built and tested (92 swarm tests green; full `tests/harness/server/` green). New code
is additive — the V25 native path is untouched and backward compatible.

**Wave 1 — foundation contract**
- `swarm_store.Role` gains the agent axis: `agent` (default `"voss"`), `command`, `args`
  (alongside existing `model`/`auth_pref`). Default roster stays all-native.
- `SwarmStore.create(roster=...)` persists an explicit roster; replay reconstructs the
  agent axis from the event log.
- `RoleSpec` (route body) mirrors it; `POST /swarm` persists the explicit roster, spawns
  native roles in-process as before, and records CLI roles as `pending` (axis visible
  end-to-end). `GET /swarm` returns the agent axis.
- NEW `voss/harness/swarm_agents.py` — `resolve_agent_argv(role, *, cwd, task_text)` +
  `AGENT_CATALOG` mirroring the app's `modelPrefs.ts` (binary==key, `--model`/`--cwd`/
  trailing task); `is_native`, `known_agents`, `custom` via shlex.

**Wave 2 — leaf modules (new files)**
- `swarm_worktree.py` — git worktree-per-member (create/list/remove/`changed_files`/
  `merge_member`), `WorktreeMergeConflict`.
- `swarm_watch.py` — `detect_violations` (reuses the SAME `build_ownership_policy` +
  fnmatch as the native gate), `revert_paths`, threaded `OwnershipWatcher`.
- `swarm_filebus.py` — A13-format `tasks/*.task.md` + `results/*.result.md` IO
  (frontmatter via vendored pyyaml; emits both `agent:` and `cli:` for frontend compat).
- `swarm_coordinator.py` — `decompose()` (single structured-output provider call →
  disjoint-owned subtasks + per-task agent) + `to_tasks()` (overlap-validated).

**Wave 3 — orchestrator + route**
- `swarm_runtime.py` — injectable `SpawnFn`/`SpawnHandle` (+ `subprocess_spawn` headless
  backend); `run_cli_member` (worktree → task file → spawn → **deterministic post-exit
  ownership reconcile: detect→revert→escalate** → commit-in-scope → merge → read result →
  `mark_done` → teardown) and `run_cli_swarm` (concurrent, native roles skipped,
  `swarm.complete`). Transport-free (emits plain dicts).
- `POST /swarm/{id}/run` — fire-and-forget driver; `_r3_event_adapter` maps the
  orchestrator's dicts → typed `E.Swarm*` SSE events via the existing fan-out.

**Deliberately deferred (not blocking the server plane):**
- GUI swarm-setup menu (decision #4) and frontend reader convergence (decision #5) —
  TS/Tauri work; the live frontend already reads the V25 `GET /swarm` snapshot, which now
  carries the agent axis, so it is forward-compatible.
- Rust/Tauri PTY spawn backend for GUI-mode CLI members (server subprocess backend ships).
- Coordinator auto-decompose on `POST /swarm` (module ready; wiring is a one-liner when
  desired) — today tasks are created via `POST /swarm/{id}/task` then driven by `/run`.
- Rewriting the V25-06 e2e test against the file-bus path (the native e2e still passes).

## Note on the shipped fix
The `Role.model` sentinel fix (`_effective_model` in `server/app.py`) is correct and
needed under **all** options — it makes native members resolve a real model and honor an
explicit one. It does not address the agent axis because `Role` has none yet; that is the
R2 design work above.
