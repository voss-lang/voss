# Phase V15: Live Plane Integration (sidecar handshake + structured pane rendering) — Specification

**Created:** 2026-06-09
**Ambiguity score:** 0.123 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

The cockpit runs against a real `voss serve`: a Tauri-managed per-workspace sidecar hands the `{v,port,token}` handshake to the webview, the V13.1 TS client fills V14's three injectable sockets (RunCommandBar native `createSession`, drawer `followUpClient`, SSE → AttentionQueue/overlay), and Voss-native panes render the PROTOCOL §6 event union as structured DOM with an inline permission gate — `liveLabel` flips to `live` for real.

## Background

- **Sidecar keystone de-risked** (`crates/voss-app-core/src/sidecar.rs`, commit `de93b4d`): spawn `python -m voss.cli serve --port 0`, parse the one-line `{"v":1,"port":…,"token":…}` handshake (log lines don't false-parse), Bearer-authed request → 200 / missing header → 401, reap with no orphan. ~1.5s warm boot; 60s cold-start budget + `LITELLM_LOCAL_MODEL_COST_MAP=true` + `PYDANTIC_DISABLE_PLUGINS=1` already encoded. NOT yet exposed as a Tauri command; no managed state; zero frontend wiring.
- **V13.1 SDK ready, Node-launcher-blocked in webview** (V14 Pitfall 4): `sdk/typescript` exports `subscribeToEvents` (sse.ts — sets the `Authorization: Bearer` header raw EventSource cannot), `rest.ts` (createSession/postMessage), `permission.ts` (`replyPermission`, choices `a|A|d|y|n`). The webview can only *consume*; spawn must come from Tauri.
- **V14 sockets waiting, all gated**: `RunCommandBar.client?` (native path disabled-with-reason when undefined), `feedbackWritePath.FollowUpClient` (drawer follow-up), `org/live/sseClient.ts` (consumes `subscribeToEvents` verbatim → `ingestEvent` + live overlay + `liveLabel` 'live'|'snapshot' signal).
- **Panes are PTY-only**: `PaneComponent.tsx` is xterm; no structured mode exists. The approved Live Work mockup (`.planning/sketches/V14-livework-mockup.html`) shows the pane *body* V14 never built: EM task header, structured tool lines, plan prose, stream deltas, inline permission gate, reviewer lines.
- **Protocol surface**: §6 event union has 21 members (authoritative: `contracts/events.schema.json`); §7 permission loop is `permission.updated` → `POST /session/:id/permission {choice}`; §10 sessions persist to `<cwd>/.voss/sessions/<id>.json` and `GET /session` lists them (attach is server-supported).

## Requirements

1. **VLIVE-01 — Sidecar Tauri command + managed lifecycle**: The app spawns/reuses one `voss serve` per workspace cwd and hands the handshake to the webview.
   - Current: `spawn_voss_serve` proven in `voss-app-core` but unreachable from the app — no Tauri command, no managed state, no frontend caller.
   - Target: a Tauri command (e.g. `start_voss_serve(cwd)`) spawns lazily on first native-run intent, holds `VossServe` in managed state keyed by workspace cwd, reuses-if-alive, returns the serializable handshake. Sidecars stay alive across workspace switches (no cap); all reaped on app exit.
   - Acceptance: invoking the command twice for the same cwd yields one server process (same port/pid); two different cwds yield two processes; after app exit `kill -0 <pid>` fails for all spawned servers.

2. **VLIVE-02 — V13.1 client fills the V14 sockets**: The webview constructs the TS client from the handshake and plugs all three injectable seams.
   - Current: `RunCommandBar.client`, drawer `followUpClient`, and the sseClient stream source are undefined/mock — native paths render disabled-with-reason.
   - Target: with a live handshake, RunCommandBar's native path calls real `createSession` (base URL `http://127.0.0.1:<port>`, Bearer token), the drawer follow-up calls real `postMessage`, and sseClient subscribes via the SDK. With no sidecar available, every affordance degrades to the existing disabled-with-reason state unchanged.
   - Acceptance: with sidecar up, a RunCommandBar native run returns a real server session id and the drawer follow-up on that session returns 202; with sidecar absent, the V14 disabled-with-reason strings render exactly as today (existing tests stay green).

3. **VLIVE-03 — Live SSE drives queue, overlay, and label**: Per-session `subscribeToEvents` streams route into both sinks and flip the label.
   - Current: `sseClient.ts` exists but nothing real feeds it; `liveLabel` is permanently 'snapshot'.
   - Target: each native session subscribes on start; events flow to `ingestEvent` (AttentionQueue) and the live overlay (budget/status/confidence/gate); `liveLabel` = 'live' while a stream is connected for the selected run, reset on end/abort/error.
   - Acceptance: a stub-provider run emitting `permission.updated` produces an AttentionQueue row; `budget.updated` visibly changes the overlay; the titlebar label reads 'live' during the stream and returns to 'snapshot' after `final`/`session.idle`/stream death.

4. **VLIVE-04 — Structured pane mode for native runs**: Sessions started via the RunCommandBar native path render protocol events as DOM instead of xterm output.
   - Current: every pane body is xterm/PTY; Voss-native runs would render raw bytes.
   - Target: a protocol-backed pane view renders the mockup-visible set with dedicated DOM — EM task header, tool lines (name + args summary + result line), plan prose, `stream.delta`/`stream.finalize` text, `final` — and renders every other §6 union member as a generic one-line row (event type + summary); nothing is silently dropped. External CLI, adopted, and `voss chat` PTY panes are untouched. Visual contract: the pane content of `.planning/sketches/V14-livework-mockup.html`, distilled to a UI-SPEC before planning.
   - Acceptance: a stub run renders header/tool/plan/delta/final DOM nodes matching the UI-SPEC; an injected union member outside the dedicated set (e.g. `cognition_loaded`) renders as a generic row; the full existing pane/PTY test suite passes unmodified.

5. **VLIVE-05 — Inline permission gate sharing the queue's reply loop**: `permission.updated` renders an in-pane gate AND a queue row; one reply clears both.
   - Current: queue ingest exists (mock-fed); no inline gate; no reply wiring anywhere.
   - Target: the in-pane gate offers Deny / Allow once / Allow for scope (mapped to §7 choices `d`/`a`/`A`); replying from either the pane gate or the AttentionQueue issues one `POST /session/:id/permission` via the SDK's `replyPermission` and clears the pending state in both surfaces.
   - Acceptance: a stub-provider permission event renders the inline gate and the queue row simultaneously; Allow-once from the pane returns 200, the turn proceeds, and both surfaces clear; Deny from the queue likewise clears the pane gate and the turn records the denial.

6. **VLIVE-06 — Attach structured pane to an existing session**: A user can open a structured pane onto a listed server session, including after app restart.
   - Current: no attach path; a relaunch strands `.voss/sessions` records with no way to act on them from the app.
   - Target: from the cockpit, attach a structured pane to any session returned by `GET /session` (respawned sidecar post-restart included): subscribe to its event stream and enable the follow-up write path. Pane auto-restore stays out (A6); transcript backfill is NOT promised — PROTOCOL v1 has no message-history endpoint and contracts are frozen, so attach renders new events forward plus whatever `SessionInfo` carries.
   - Acceptance: create a session, quit the app, relaunch, trigger sidecar respawn — the session appears in the list, attach succeeds, a follow-up message returns 202, and its resulting events render in the attached pane.

7. **VLIVE-07 — Lifecycle honesty (cold start, spawn failure, server death)**: Every degraded state is visible and truthful; nothing fakes liveness.
   - Current: no frontend lifecycle surface exists at all.
   - Target: handshake-pending shows a "starting Voss…" affordance (60s budget); spawn failure surfaces an honest error including the stderr tail (already captured by `sidecar.rs`); server death mid-session flips `liveLabel` to 'snapshot', shows the structured pane's ended state, and flips write affordances to disabled-with-reason; the next native-run intent respawns fresh. No auto-restart watchdog.
   - Acceptance: SIGKILL the server mid-run → label flips to 'snapshot', the pane shows an ended state, follow-up renders disabled-with-reason; the next RunCommandBar native run spawns a new server (different pid) and succeeds.

8. **VLIVE-08 — Hermetic verification + human real-run checkpoint**: Automated acceptance runs against a real spawned `voss serve` with a stub/fake provider; one human checkpoint walks the full spine on a real provider.
   - Current: no E2E test exercises spawn→handshake→client→SSE from the app side (the spike's gated cargo test covers the crate only).
   - Target: the automated AC suite spawns real `voss serve` (stub provider, no API key, no network) and drives the spine; the phase's human-verify checkpoint performs one real-provider run confirming live label, structured rendering, and the permission loop end-to-end.
   - Acceptance: AC suite passes on a machine with no provider credentials; human checkpoint sign-off recorded covering the full spine (RunCommandBar → sidecar spawn → structured stream → inline permission → final → drawer follow-up → overlay update).

## Boundaries

**In scope:**
- Tauri command + managed per-workspace sidecar state in `apps/voss-app/src-tauri` over `crates/voss-app-core::sidecar` (lazy spawn, reuse-if-alive, keep-alive across workspace switch, reap on exit)
- Frontend client construction from the handshake; plumbing into RunCommandBar `client`, drawer `followUpClient`, and `sseClient`
- Live SSE consumption → AttentionQueue + live overlay + `liveLabel`
- Structured protocol pane mode for RunCommandBar-native sessions (mockup set + generic fallback row)
- Inline permission gate sharing one reply loop with the AttentionQueue
- Attach-a-new-structured-pane to existing server sessions (incl. post-restart)
- Cold-start affordance, spawn-failure error surface, honest server-death degrade
- Hermetic stub-provider AC suite + one human real-provider checkpoint
- UI-SPEC distillation of the mockup's pane content before plan-phase

**Out of scope:**
- VCKP-13b permission proxy for external CLIs — roadmap-excluded; tier-A enforcement is its own phase
- Rollback / re-run of runs — roadmap-excluded
- Embedded browser — roadmap-excluded
- Pane auto-restore after restart — A6 Session Persist territory; V15 ships attach-to-existing only
- Structured view for external CLI / adopted / `voss chat` PTY panes — no protocol stream exists for them (physics, not preference); revisit post-VCKP-13b
- Structured transcript in Run Review replay — replay keeps reading snapshots
- Interpreter-resolution UX for non-dev installs — spike chain (`VOSS_PYTHON` > repo `.venv/bin/python` > `python3`) ships as-is; picker UI lands with A11
- Transcript backfill on attach — no message-history endpoint in PROTOCOL v1 and contracts are frozen
- Multi-server LRU caps / auto-restart watchdog — premature complexity; honest degrade instead
- Any Python server, PROTOCOL.md, `contracts/*.json`, or `sdk/typescript` schema change — app-side-only phase

## Constraints

- **App-side only**: `voss/` Python server, `.planning/PROTOCOL.md`, `contracts/*.json`, and `sdk/typescript` are consumed as-is (frozen). Server/protocol gaps discovered mid-phase become deferred notes, never patches.
- **Frozen crates rule**: `crates/` v0.1-ship members stay untouched; `crates/voss-app-core` and `apps/voss-app/src-tauri` are the live members (sidecar.rs is the production home).
- **Spawn environment is load-bearing**: `LITELLM_LOCAL_MODEL_COST_MAP=true` (case-sensitive; `"1"` does not work), `PYDANTIC_DISABLE_PLUGINS=1`, 60s handshake timeout, continuous stderr drain, stdin-pipe heartbeat, `kill_on_drop` — all already in `sidecar.rs`; must survive the Tauri integration.
- **SSE via the SDK verbatim**: never raw `EventSource` (cannot set the Bearer header — `sse.ts:20`).
- **Solid render-layer discipline**: module-level signals + immutable spreads; no `produce`/`structuredClone` in tree utils called from the render layer.
- **No new npm/cargo dependencies expected**; any addition requires explicit justification in the plan.
- **UI-SPEC before planning** (V14 lesson — don't build from prose): distill `.planning/sketches/V14-livework-mockup.html` pane content via /gsd-ui-phase before plan-phase.

## Acceptance Criteria

- [ ] Same-cwd double invoke of the sidecar command reuses one server; different cwds run two; app exit leaves zero orphan processes (`kill -0` fails)
- [ ] With sidecar up: RunCommandBar native run returns a real server session id; drawer follow-up returns 202
- [ ] With sidecar absent: all V14 disabled-with-reason states render unchanged (existing suite green)
- [ ] Stub-provider run: `permission.updated` → AttentionQueue row; `budget.updated` → overlay change; `liveLabel` = 'live' during stream, 'snapshot' after `final`/`session.idle`/stream death
- [ ] Structured pane renders EM header, tool lines, plan prose, stream deltas, and final per the UI-SPEC; an out-of-set union member renders as a generic row (nothing dropped)
- [ ] External CLI / adopted / `voss chat` panes still render via PTY; full existing pane test suite passes unmodified
- [ ] Permission event renders inline gate + queue row; one reply (`d`/`a`/`A` → `POST /session/:id/permission`) clears both surfaces; turn proceeds or records denial accordingly
- [ ] Post-restart: respawned sidecar lists the prior session; attach renders forward events; follow-up returns 202
- [ ] SIGKILL mid-run: label → 'snapshot', pane shows ended state, write affordances disabled-with-reason; next native run spawns a fresh server and succeeds
- [ ] Automated AC suite passes with no provider credentials and no network (real `voss serve`, stub provider)
- [ ] Human checkpoint: one real-provider run walks the full spine (intake → spawn → structured stream → inline permission → final → follow-up → overlay) and is signed off
- [ ] PROTOCOL.md, `contracts/*.json`, `sdk/typescript`, and `voss/` Python are byte-unchanged at phase close

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                            |
|--------------------|-------|------|--------|--------------------------------------------------|
| Goal Clarity       | 0.92  | 0.75 | ✓      | Spine + truth bar locked                         |
| Boundary Clarity   | 0.90  | 0.70 | ✓      | Every contested boundary individually decided    |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Frozen surfaces + spawn env + SDK-verbatim rule  |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 12 pass/fail criteria                            |
| **Ambiguity**      | 0.123 | ≤0.20| ✓      |                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective              | Question summary                                   | Decision locked                                                                 |
|-------|--------------------------|----------------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher               | Sidecar instance scoping + spawn timing            | Per-workspace, lazy on first native intent; reuse-if-alive; cold-start affordance |
| 1     | Researcher               | What creates a structured pane?                    | RunCommandBar native path only; PTY panes untouched                             |
| 1     | Researcher               | E2E truth bar                                      | Stub-provider hermetic ACs + one human real-provider checkpoint                 |
| 2     | Simplifier               | Renderer coverage over 21-member union             | Mockup set dedicated + generic fallback row; nothing silently dropped           |
| 2     | Researcher               | May V15 touch server/contracts?                    | App-side only; PROTOCOL/contracts/SDK/Python frozen; gaps → deferred notes      |
| 2     | Failure Analyst (early)  | Server death mid-session                           | Honest degrade, no auto-restart; respawn on next intent                         |
| 3     | Boundary Keeper          | Done demo                                          | Full spine incl. overlay assertion                                              |
| 3     | Boundary Keeper          | Workspace-switch multi-server policy               | Keep alive, no cap; reap all on exit                                            |
| 4     | Boundary Keeper (reshow) | Reattach after restart (exclusions Q was skipped)  | Attach-to-existing IN; pane auto-restore OUT (A6); no transcript backfill       |
| 4     | Boundary Keeper (reshow) | Structured view for external/adopted/chat panes    | OUT — physics: no protocol stream exists without VCKP-13b                       |
| 4     | Boundary Keeper (reshow) | Interpreter-resolution UX                          | OUT — spike chain as-is; picker UI lands with A11                               |
| 5     | Gate                     | Ambiguity 0.123, write?                            | Yes — write SPEC.md                                                             |

Note: round-3 exclusions multi-select came back unanswered; round 4 re-asked each item individually — user pulled attach-to-existing IN (originally proposed as excluded) and confirmed the rest OUT.

---

*Phase: V15-live-plane-integration*
*Spec created: 2026-06-09*
*Next step: /gsd-discuss-phase V15 — implementation decisions (how to build what's specified above)*
