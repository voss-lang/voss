# Phase V25: Server-Native Swarm Runtime — Specification

**Created:** 2026-06-17
**Ambiguity score:** 0.125 (gate: ≤ 0.20)
**Requirements:** 11 locked

## Goal

Multi-agent swarms coordinate through the harness FastAPI server + SSE event bus instead of filesystem-as-IPC: a `SwarmStore` is the single server-side source of truth, builder sessions are spawn-gated (no poll/sleep race), per-task file ownership is enforced at `PermissionGate`, and `.voss/swarm/<id>/events/*.jsonl` is an append-only audit/replay mirror only. Supersedes A13's file-bus transport; A13-01 file schema is retained as the audit layer.

## Background

Voss has a harness server (`voss/harness/server/app.py`) that multiplexes many `ServerSession`s in one process, pushes events over SSE (`GET /session/{id}/events`), takes turns via `POST /session/{id}/message`, mediates every file write through `make_toolset` → `PermissionGate.check` (`permissions.py:233`, deny-wins project-policy layer at `:271-290`), recalls semantic memory (`memory_store.py` `MemoryStore.recall`), binds agents to grid panes via `agent_registry.rs` (SQLite), and routes providers/models (`_resolve_provider`, `/models`).

A13 (Agent Swarm Orchestration) already built a swarm — but **filesystem-mediated** (`.voss/swarm/tasks/*.md`, `results/*.md`, `manifest.json`, fs-watch), the same design as the external BridgeSwarm product. A13-01 shipped the file protocol; A13-02..06 (decompose/spawn/result-watch/sidebar/persist) are pending. The file-bus design exists because BridgeSwarm/A13 had no daemon — it needs nudge files, stdin injection, and PATH-injected bash CLIs to wake idle agents. Voss has a daemon, so none of that is necessary. This phase re-bases swarm coordination on server + SSE and demotes the filesystem to audit-only.

No `swarm_store.py`, swarm SSE event types, `/swarm` endpoints, spawn-gating, ownership policy, or memory-scoped recall exist today. This phase creates them.

## Requirements

1. **VSWARM-01 — SwarmStore + event log**: Server-side swarm state with an append-only on-disk mirror.
   - Current: No swarm state in the harness; A13 stored swarm state in `.voss/swarm/manifest.json` written by the Rust client as the runtime source of truth.
   - Target: `voss/harness/swarm_store.py` holds `Swarm{scopeId, goal, roster[Role], tasks[Task]}` in server memory; every mutation appends an immutable event to `.voss/swarm/<id>/events/*.jsonl`; state is rebuildable by replaying the event log.
   - Acceptance: Creating a swarm + 2 tasks then reloading SwarmStore purely from `events/*.jsonl` reconstructs identical state; the JSONL is append-only (no event file is ever rewritten).

2. **VSWARM-02 — Swarm SSE event types**: Swarm coordination flows over the existing SSE bus.
   - Current: SSE bus emits session/turn events only (`EventBusRenderer`); no swarm event types.
   - Target: New event types `swarm.assign`, `swarm.worker_done`, `swarm.gate`, `swarm.needs_operator`, `swarm.complete` published on the existing bus and delivered to subscribed agent sessions.
   - Acceptance: A subscriber to a swarm's event stream receives each of the 5 event types in a scripted run; no `nudges/*.txt` file or stdin injection is used anywhere in the path.

3. **VSWARM-03 — Swarm REST endpoints**: HTTP surface to create and drive a swarm headlessly.
   - Current: No `/swarm` routes exist.
   - Target: `POST /swarm` (create + seed goal), `GET /swarm/{id}` (state), `POST /swarm/{id}/task` (create/update task), `POST /swarm/{id}/message` (inter-agent/operator message), all bearer-authed like existing routes.
   - Acceptance: A swarm can be created, a task added, and a message sent end-to-end via HTTP with a valid token; all four return documented status codes and 401 without a token.

4. **VSWARM-04 — Spawn-gating**: Builders start in a held state and unblock deterministically.
   - Current: A13/BridgeSwarm rely on launch-order timing (coordinator first, builders +2s, poll within 60s) — a race.
   - Target: Builder sessions are created in a `waiting` state and only begin their first turn after the coordinator emits `swarm.assign` for their task. No `sleep`/poll timing dependency.
   - Acceptance: A builder created before its assignment exists runs zero turns until `swarm.assign` arrives, then runs exactly one assigned turn; test passes deterministically with no timing tolerance.

5. **VSWARM-05 — Server-enforced file ownership**: Writes outside a task's owned files are denied at the gate.
   - Current: A13 task files only *instruct* agents ("Do NOT modify files in src/auth/tests/") — advisory, unenforced.
   - Target: A per-session swarm policy injected into `PermissionGate` denies `fs_write`/`fs_edit` to any path outside the active task's `ownedFiles`, via the existing deny-wins project-policy layer; denial emits `swarm.needs_operator`.
   - Acceptance: A builder whose task owns `a.py` is allowed to edit `a.py` and is denied editing `b.py` (gate returns deny, edit does not occur, `swarm.needs_operator` emitted).

6. **VSWARM-06 — Ownership overlap validation**: The store refuses ambiguous file ownership.
   - Current: Nothing prevents two tasks from claiming the same file.
   - Target: `POST /swarm/{id}/task` rejects a task whose `ownedFiles` overlap another active task's `ownedFiles` unless the two are ordered by `dependsOn`.
   - Acceptance: Creating two concurrent tasks both owning `a.py` returns a 4xx with an overlap error; the same two ordered via `dependsOn` succeeds.

7. **VSWARM-07 — Memory-scoped recall injection**: Each agent turn is seeded with task-relevant memory.
   - Current: `MemoryStore.recall` exists and the server already injects code-recall per turn (`_render_code_recall_text`), but not scoped to a swarm task's owned files.
   - Target: Each swarm agent turn auto-injects `MemoryStore.recall(query, scope=task.ownedFiles)`; the scout role is not spawned as a default roster member.
   - Acceptance: A swarm builder turn's assembled prompt contains recall hits filtered to the task's `ownedFiles` scope; default roster for a 2-builder swarm contains no scout agent.

8. **VSWARM-08 — Per-role model routing**: Roles can run on different models.
   - Current: Sessions resolve one model via `_resolve_provider`; no per-role swarm routing.
   - Target: Each `Role` carries a `model`; the coordinator/builder/reviewer sessions resolve their own provider/model through the existing router (e.g. coordinator=Opus, builders=Codex, reviewer=third).
   - Acceptance: A swarm configured with three distinct role models spawns three sessions whose resolved models match the roster spec.

9. **VSWARM-09 — Grid + agent-registry binding**: Swarm agents are bound to panes and discoverable.
   - Current: `agent_registry` tracks per-pane agents (`pane_id`, `session_id`, `cli_binary`, `cwd`, `status`); no swarm linkage.
   - Target: `agent_registry` gains `swarm_id`, `role`, `owned_files` columns; swarm spawn applies a layout preset (`layouts.rs`) and registers each agent session against its pane.
   - Acceptance: After spawning a 2-builder swarm, `agent_registry` rows carry the correct `swarm_id`/`role`/`owned_files`, and the registry can list a swarm's agents by `swarm_id`.

10. **VSWARM-10 — Operator escalation + decision recording**: The human is a first-class participant and gates are recorded.
    - Current: Permission gate already bridges async operator prompts (`POST /session/{id}/permission`); no swarm-level operator role or decision artifact.
    - Target: `@operator` is a roster member; `swarm.needs_operator` surfaces through the existing permission-gate reply path; coordinator/reviewer gate outcomes (approve/reject/conflict) write `.voss/decisions/*.md` with `confidence` + `related_session`.
    - Acceptance: An ownership-denied write raises an operator escalation answerable via the existing permission endpoint; a reviewer reject writes a decision markdown with populated `confidence` and `related_session` frontmatter.

11. **VSWARM-11 — Audit replay**: A completed swarm is reconstructable from disk.
    - Current: No swarm event log; A13's manifest was a mutable snapshot, not a replayable history.
    - Target: `.voss/swarm/<id>/events/*.jsonl` captures the full ordered history (task lifecycle, assigns, worker_done, gates, complete) sufficient to replay the run without the server.
    - Acceptance: After a swarm reaches `swarm.complete`, replaying `events/*.jsonl` yields the full task-state timeline (each task's `open→…→done` transitions in order) with no missing transitions.

## Boundaries

**In scope:**
- `voss/harness/swarm_store.py` — SwarmStore, Task/Role/Swarm models, append-only JSONL event log
- Swarm SSE event types on the existing bus
- `/swarm`, `/swarm/{id}`, `/swarm/{id}/task`, `/swarm/{id}/message` REST endpoints (bearer-authed)
- Spawn-gating (`waiting` → `swarm.assign`)
- PermissionGate per-session ownership policy + SwarmStore overlap validation
- Memory-scoped recall injection per swarm turn; scout folded into chroma
- Per-role model routing through the existing router
- `agent_registry` schema columns (`swarm_id`/`role`/`owned_files`) + thin pane-binding on spawn
- Operator escalation reuse + gate-decision markdown recording
- A 2-builder enforced end-to-end integration test as the acceptance bar
- Retaining A13-01's `.voss/swarm/` file schema as the audit-layer format

**Out of scope:**
- voss-app spawn UI, roster sidebar, launch modal — runtime is verified headlessly; UI binding is V24/voss-app (avoids harness↔Tauri coupling)
- The V24 Swarm Map visualization itself — V25 emits the live plane; V24 renders it
- Coordinator goal→tasks **decomposition logic/quality** — V25 ships task CRUD + transport; the decompose prompt is the coordinator role-prompt, validated separately (keeps requirements falsifiable)
- nudge.txt / stdin-injection wakeups, PATH-injected `bs-*` bash CLIs, per-agent OS process or per-agent `CLAUDE_CONFIG_DIR` — superseded anti-patterns
- Filesystem as runtime transport — audit/replay only
- Changing V3/V5/V7 autonomous-org cage semantics — V25 is human-launched CLI-agent-pane swarm runtime, a distinct surface; convergence is a later decision
- A13-02..06 file-bus plans — superseded, not completed

## Constraints

- **Single-process asyncio**: the harness runs N swarm agents as N interleaving `session.task`s in one shared sidecar. Write collisions are prevented **by construction** (disjoint `ownedFiles` + PermissionGate deny + overlap validation), not by file locks. No new process-per-agent model.
- **Reuse, don't rebuild**: ownership enforcement must use the existing `PermissionGate.check` deny-wins project-policy layer; memory injection must use `MemoryStore.recall`; model routing must use `_resolve_provider` — no parallel mechanisms.
- **Audit log is append-only**: event files are written with create-exclusive semantics; never rewritten in place.
- **Auth parity**: all `/swarm` routes use the same bearer-token middleware as existing routes; unauth'd requests return 401.
- **Depends on V15** live-plane sidecar/SSE for any webview-facing consumption; the runtime itself is verifiable without voss-app.
- Keep `voss do` / `voss chat` / existing session routes working unchanged.

## Acceptance Criteria

- [ ] SwarmStore state reconstructs identically from `.voss/swarm/<id>/events/*.jsonl` alone (event log is append-only)
- [ ] All 5 swarm SSE event types delivered to a subscriber in a scripted run; zero use of nudge files or stdin injection
- [ ] `POST /swarm`, `GET /swarm/{id}`, `POST /swarm/{id}/task`, `POST /swarm/{id}/message` work with a valid token and return 401 without one
- [ ] A builder runs zero turns until its `swarm.assign` arrives, then exactly one — no timing tolerance in the test
- [ ] A builder is allowed to edit its owned file and denied editing a non-owned file (gate deny, no write, `swarm.needs_operator` emitted)
- [ ] Two concurrent tasks owning the same file are rejected (4xx); the same two ordered by `dependsOn` are accepted
- [ ] A swarm builder turn's prompt contains recall hits scoped to its task `ownedFiles`; default 2-builder roster has no scout agent
- [ ] A 3-role swarm spawns sessions whose resolved models match the per-role spec
- [ ] `agent_registry` rows after spawn carry correct `swarm_id`/`role`/`owned_files` and are listable by `swarm_id`
- [ ] An ownership denial is answerable via the existing permission endpoint; a reviewer reject writes a `.voss/decisions/*.md` with `confidence` + `related_session`
- [ ] After `swarm.complete`, replaying `events/*.jsonl` yields each task's full ordered state timeline with no missing transitions
- [ ] **End-to-end bar:** a scripted 2-builder run — coordinator assigns 2 disjoint-file tasks → both builders edit only owned files → a 3rd-file write is denied at the gate → reviewer gates → `swarm.complete` emitted → `events.jsonl` replays the run — passes as one integration test

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Server+SSE runtime, SwarmStore, 11 falsifiable requirements   |
| Boundary Clarity   | 0.92  | 0.70 | ✓      | Surface (runtime+API only), decompose (substrate only), A13 supersede all locked |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Single-process asyncio, by-construction collision avoidance, reuse-not-rebuild |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 2-builder enforced e2e + per-requirement pass/fail checks     |
| **Ambiguity**      | 0.125 | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective | Question summary | Decision locked |
|-------|-------------|------------------|-----------------|
| 0 | Researcher (scout) | What swarm machinery exists today? | A13 = file-mediated swarm twin of BridgeSwarm (A13-01 shipped, 02..06 pending); V3/V5/V7 cage; V24 Swarm Map. V25 supersedes A13 transport. |
| 0 | Failure Analyst (risk) | Is concurrent file-write in one shared sidecar safe? | Resolved: writes funnel through `PermissionGate.check`; ownership = inject deny into existing project-policy layer; collisions prevented by-construction, not by lock |
| 1 | Boundary Keeper | Runtime vs UI surface? | Harness runtime + API only; grid/sidebar binding thin; Swarm Map UI stays V24 |
| 1 | Boundary Keeper | Decompose in scope? | Substrate only — task CRUD + transport; decompose quality is the coordinator role-prompt, validated separately |
| 1 | Failure Analyst | Smallest run that proves it works? | 2-builder enforced run: assign 2 disjoint tasks → owned-only edits → 3rd-file write denied → reviewer gate → complete → events replay |

---

*Phase: V25-server-native-swarm-runtime*
*Spec created: 2026-06-17*
*Next step: /gsd-discuss-phase V25 — implementation decisions (SwarmStore schema, event-log format, role-prompt templates, spawn-gate mechanics)*
