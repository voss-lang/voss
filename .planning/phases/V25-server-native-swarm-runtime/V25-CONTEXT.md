# Phase V25: Server-Native Swarm Runtime - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Harness server + SSE swarm coordination **runtime** that supersedes A13's filesystem-as-IPC transport. Delivers `swarm_store.py` (server-side source of truth + append-only audit log), swarm SSE event types, `/swarm` REST endpoints, deterministic spawn-gating, PermissionGate-enforced file ownership, memory-scoped recall injection, per-role model routing, and agent-registry binding. Verified **headlessly** (API/CLI/tests). The voss-app spawn UI and the V24 Swarm Map visualization are explicitly NOT in this phase — V25 emits the live plane; V24 renders it.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**11 requirements are locked.** See `V25-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V25-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** `swarm_store.py` (SwarmStore + Task/Role/Swarm models + append-only JSONL event log); swarm SSE event types; `/swarm` REST endpoints (bearer-authed); spawn-gating (`waiting`→`swarm.assign`); PermissionGate per-session ownership policy + overlap validation; memory-scoped recall injection (scout folded into chroma); per-role model routing; `agent_registry` columns (`swarm_id`/`role`/`owned_files`) + thin pane-binding; operator escalation reuse + gate-decision markdown; 2-builder enforced e2e; retaining A13-01's `.voss/swarm/` schema as the audit format.

**Out of scope (from SPEC.md):** voss-app spawn UI / roster sidebar / launch modal (→ V24/voss-app); the V24 Swarm Map visualization itself; coordinator goal→tasks **decomposition quality** (validated separately as the coordinator role-prompt); nudge.txt/stdin-injection, PATH bash CLIs, per-agent OS process; filesystem as runtime transport (audit-only); changing V3/V5/V7 cage semantics; A13-02..06 file-bus plans (superseded, not completed).

</spec_lock>

<decisions>
## Implementation Decisions

### Coordinator shape
- **D-01:** The coordinator is a **full harness `ServerSession`** (its own pane + model), not a one-shot call. It calls `POST /swarm/{id}/task` to seed tasks, emits `swarm.assign`, and can re-plan / gate mid-run as a first-class roster member. **This reverses A13 D-03** (which chose a single one-shot Opus call). Rationale: consistent with the server-native reframe — the coordinator is just another session on the same multiplexed sidecar; enables mid-run re-planning the file-bus design couldn't do.
- **D-02:** Carry forward A13 **D-02 single-coordinator** topology (not peer-to-peer) and **D-12 max-6-concurrent-agents** cap (user-overridable). Coordinator owns all routing; debuggable + auditable.

### V24 Swarm Map feed
- **D-03:** V25 emits the `swarm.*` SSE events as a **first-class dedicated event plane**; V24's `swarmReconcile` (`apps/voss-app/src/org/swarmReconcile.ts`) consumes them directly. NOT bent into existing RunData/board shapes. Rationale: honest-signal by construction (V24 renders only real events) + clean live semantics. **Follow-up flagged:** a small V24 change to teach `swarmReconcile` the swarm event vocabulary — note in V24 backlog, not V25 scope.

### Audit layer / A13-01 reuse
- **D-04:** V25 owns a **new append-only `events/*.jsonl`** under `.voss/swarm/<id>/` as the truth-mirror (satisfies VSWARM-11 replay). A13's `manifest.json` + `tasks/` + `results/` become an **optional derived snapshot view** for back-compat/inspection, rendered FROM the event log — not the source of truth. A13-01's shipped Rust temp-rename writers + `swarmTypes.ts` are **demoted to snapshot rendering**, not deleted. Rationale: A13's manifest is a mutable snapshot (weak replay); event-sourcing needs append-only history.

### Role-prompt templates
- **D-05:** Coordinator/builder/reviewer prompts live as **versioned files in the harness** (e.g. `voss/harness/swarm/prompts/`), git-tracked, generated per-run with task context injected. The **coordinator prompt is seeded from BridgeSwarm's recovered coordinator playbook** (the one role template that was persisted/recovered). Rationale: testable, centrally version-controlled, evolvable; avoids per-project prompt drift.

### Claude's Discretion
- **Ownership policy injection mechanics** (VSWARM-05): build a synthetic per-task `PermissionsConfig` in SwarmStore and attach it to the session's `PermissionGate` via the existing deny-wins `.voss/permissions.yml` project-policy layer (`permissions.py:207,271-290`). SPEC pins "reuse project-policy layer"; the planner/researcher choose the exact construction (synthetic config vs. new gate field). Writes already funnel through `PermissionGate.check` (`permissions.py:233`, called `agent.py:1424`).
- **Event envelope schema** (event id/type/actor/ts/payload shape) — planner's call, constrained by VSWARM-01 (append-only, replayable) and D-03 (must satisfy V24 `swarmReconcile`).
- **Spawn-gate `waiting` mechanics** — new `ServerSession` state vs. lazy session creation on assign — planner's call, constrained by VSWARM-04 (zero turns until assign, deterministic).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements (read first)
- `.planning/phases/V25-server-native-swarm-runtime/V25-SPEC.md` — Locked requirements (VSWARM-01..11), boundaries, acceptance criteria. MUST read before planning.
- `.planning/ROADMAP.md` § "Phase V25: Server-Native Swarm Runtime" — goal, supersede relationship, scope, out-of-scope, concurrency note, suggested waves.

### Superseded transport — design context + shipped artifacts to reuse
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md` — file-bus design decisions D-01..D-22 (D-02/D-12 carried; D-03/D-20 reversed). The transport V25 supersedes.
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-01-SUMMARY.md` — what A13-01 SHIPPED: `apps/voss-app/src/swarm/swarmTypes.ts` (camelCase `swarmId`/`resultFile`), Rust Tauri commands for `.voss/swarm/` writes + polling watcher + temp-rename manifest. These are the writers demoted to snapshot rendering (D-04).
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md` — SWM-01..12; file protocol + directory schema retained as audit format.

### V24 — Swarm Map consumer (V25 emits its plane)
- `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-CONTEXT.md` — Swarm Map data contract, `swarmReconcile` radial model (D-06/07), **honest-signal rule** (render only real events, never fake), identifiers stay `runId`/`RunData`.

### Harness integration points (code)
- `voss/harness/server/app.py` — `ServerSession`, `_run_turn` (turn loop, `make_toolset` + per-session `PermissionGate`), SSE `EventBusRenderer`, session routes; where `/swarm` routes + spawn-gating attach.
- `voss/harness/permissions.py` — `PermissionGate.check` (`:233`), `WRITE={"fs_write","fs_edit"}` (`:54`), deny-wins project-policy layer (`:207`, `:271-290`) — the ownership-enforcement hook.
- `voss/harness/tools.py` — `make_toolset`, `fs_edit`/`fs_write` (`:545,862`) — the write chokepoint.
- `voss/harness/memory_store.py` — `MemoryStore.recall(query, top_k)` — scoped recall injection (VSWARM-07).
- `voss/harness/providers.py` + `_resolve_provider` (app.py:85-112) — per-role model routing (VSWARM-08).
- `crates/voss-app-core/src/agent_registry.rs` — SQLite `agent_sessions`; add `swarm_id`/`role`/`owned_files` columns (VSWARM-09).
- `crates/voss-app-core/src/layouts.rs` — swarm layout preset for pane binding.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PermissionGate` deny-wins project-policy layer** (`permissions.py`): the exact, already-shipped hook for VSWARM-05 ownership enforcement — no new chokepoint needed.
- **Multiplexed `ServerSession` + SSE bus** (`app.py`): N swarm agents = N sessions on one sidecar; coordinator (D-01) is just another session. No per-agent process.
- **`MemoryStore.recall`** (`memory_store.py`): drop-in for scoped recall; server already injects code-recall per turn (`_render_code_recall_text`) — extend with task scope.
- **A13-01 `swarmTypes.ts` + Rust `.voss/swarm/` writers**: reused as the derived-snapshot renderer (D-04), not discarded.
- **`agent_registry` register/sweep/mark-stopped** (`agent_registry.rs`): per-pane lifecycle already tracked; add swarm columns.

### Established Patterns
- **Append-only + temp-rename writes** (A13 manifest pattern, `.voss/` session writes via `fs2` exclusive lock): the JSONL event log (D-04) follows the same create-exclusive discipline.
- **camelCase IPC payloads** (A13-01 `swarmId`/`resultFile`): keep for any Rust↔TS swarm payloads.
- **Bearer-token ASGI middleware** (app.py): `/swarm` routes inherit it (401 without token).

### Integration Points
- `/swarm` routes → `app.py` route table, beside `/session`.
- Spawn-gate → `ServerSession` lifecycle (`waiting` state) in `_run_turn`/session creation.
- Ownership policy → per-task `PermissionsConfig` attached at gate construction in `_run_turn`.
- V24 feed → `swarm.*` events on `EventBusRenderer` bus → `swarmReconcile.ts` (V24 follow-up).

</code_context>

<specifics>
## Specific Ideas

- Coordinator prompt seeded from the **recovered BridgeSwarm coordinator playbook** (the only role template BridgeSwarm persisted to disk) — use as the starting template for `voss/harness/swarm/prompts/coordinator.md`.
- Acceptance anchor is the **2-builder enforced run** (SPEC e2e bar): assign 2 disjoint-file tasks → owned-only edits → 3rd-file write denied at gate → reviewer gate → `swarm.complete` → `events.jsonl` replays. Plan the integration test around this.

</specifics>

<deferred>
## Deferred Ideas

- **V24 `swarmReconcile` swarm-event consumer** — teaching the Swarm Map to read the new `swarm.*` event plane (D-03). Belongs in V24, not V25. Note for V24 backlog.
- **voss-app swarm spawn UI / roster sidebar / launch modal** — A13-05 territory; deferred to V24/voss-app per SPEC boundary.
- **Coordinator decomposition-quality evals** — the LLM prompt that splits a goal into disjoint-file tasks; validate via E-track/eval, separate from V25 substrate.
- **Convergence of V25 CLI-agent swarm with V5/V7 autonomous-org cage** — possible later unification; explicitly not this phase.

</deferred>

---

*Phase: V25-server-native-swarm-runtime*
*Context gathered: 2026-06-17*
