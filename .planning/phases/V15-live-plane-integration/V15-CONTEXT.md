# Phase V15: Live Plane Integration (sidecar handshake + structured pane rendering) - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Plug the V14 cockpit into a real `voss serve`: Tauri-managed per-workspace sidecar hands the `{v,port,token}` handshake to the webview; the V13.1 TS client fills V14's three injectable sockets (RunCommandBar native `createSession`, drawer `followUpClient`, SSE → AttentionQueue/overlay/`liveLabel`); Voss-native panes graduate from raw PTY to structured PROTOCOL §6 event rendering with an inline permission gate. App-side only — server, protocol, contracts, and SDK are frozen.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked.** See `V15-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V15-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Tauri command + managed per-workspace sidecar state in `apps/voss-app/src-tauri` over `crates/voss-app-core::sidecar` (lazy spawn, reuse-if-alive, keep-alive across workspace switch, reap on exit)
- Frontend client construction from the handshake; plumbing into RunCommandBar `client`, drawer `followUpClient`, and `sseClient`
- Live SSE consumption → AttentionQueue + live overlay + `liveLabel`
- Structured protocol pane mode for RunCommandBar-native sessions (mockup set + generic fallback row)
- Inline permission gate sharing one reply loop with the AttentionQueue
- Attach-a-new-structured-pane to existing server sessions (incl. post-restart)
- Cold-start affordance, spawn-failure error surface, honest server-death degrade
- Hermetic stub-provider AC suite + one human real-provider checkpoint
- UI-SPEC distillation of the mockup's pane content before plan-phase

**Out of scope (from SPEC.md):**
- VCKP-13b permission proxy for external CLIs — roadmap-excluded
- Rollback / re-run of runs — roadmap-excluded
- Embedded browser — roadmap-excluded
- Pane auto-restore after restart — A6 territory; attach-to-existing only
- Structured view for external CLI / adopted / `voss chat` PTY panes — no protocol stream exists (physics)
- Structured transcript in Run Review replay — replay keeps reading snapshots
- Interpreter-resolution UX for non-dev installs — spike chain ships as-is
- Transcript backfill on attach — no message-history endpoint; contracts frozen
- Multi-server LRU caps / auto-restart watchdog — honest degrade instead
- Any Python server, PROTOCOL.md, `contracts/*.json`, or `sdk/typescript` schema change

</spec_lock>

<decisions>
## Implementation Decisions

### Run-start pane behavior
- **D-01:** Native run submit (RunCommandBar, either mode) auto-opens a structured pane in the Live Work grid immediately; if the app is in Run Review, it flips to Live Work focused on the new pane. Instant feedback that the run is real — "grid is for steering agents."
- **D-02:** New structured panes land via the same grid-insertion path as the sidebar quick-launch agent spawn (new cell + `balanceRatios` equalize). One insertion behavior everywhere; zero new layout logic.
- **D-03:** One pane per native run, no cap. Honest 1:1 run↔pane mapping; grid proven at 9 panes (A3 perf bar).

### Attach surface
- **D-04:** Attach-to-existing lives in a cockpit sidebar "Server sessions" section: `GET /session` list (id/title/age, recent-first) with an Attach action. Attached panes land via the D-02 grid path.
- **D-05:** Session list shows everything `GET /session` returns (including CLI-created `voss chat` sessions — same store), newest first. No source filtering; honest mirror.
- **D-06:** Attaching registers the session as a native cockpit card via the existing native-card bridge — attached ≡ started; board/drawer see one consistent model.

### Transcript density + retention
- **D-07:** Tool lines render as collapsed one-liners by default; click expands full args/result/excerpt. **This overrides the mockup's inline fs_edit excerpts** — the UI-SPEC must encode collapsed-by-default as a deliberate deviation from `.planning/sketches/V14-livework-mockup.html`.
- **D-08:** Transcript DOM is capped, trim-oldest (Claude picks N, order of a few hundred events). The EM task header and any pending permission rows are pinned — never trimmed.
- **D-09:** `stream.delta` appends to a growing live block with the existing V14 honest streaming pulse; `stream.finalize` settles it into plain prose. Sticky-bottom auto-scroll unless the user scrolled up.

### Lifecycle affordance placement
- **D-10:** Cold start renders an in-pane boot placeholder ("starting Voss…" + elapsed) until the handshake lands, then the transcript begins. Statusbar dot is secondary. (Warm ~1.5s; cold up to 60s.)
- **D-11:** Server death mid-run: transcript appends an ended banner row, pane chrome dims, statusbar flips to snapshot, follow-up goes disabled-with-reason. Reuse the ExitBanner visual language from PTY panes — consistent death across pane types.
- **D-12:** Sidecar spawn failure: the boot placeholder becomes an in-pane error state — message + stderr tail (already captured by `sidecar.rs`) + a Retry button that re-invokes spawn.

### Claude's Discretion
- Exact transcript cap value (D-08) — a few hundred events, planner picks.
- Internal architecture of the structured pane component (new component vs PaneComponent mode branch), event→DOM renderer structure, EM-header data sourcing from the event stream, stub-provider test mechanics — planner/researcher territory within SPEC constraints.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements + findings
- `.planning/phases/V15-live-plane-integration/V15-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/phases/V15-live-plane-integration/V15-SPIKE-sidecar.md` — Proven sidecar keystone: spawn env, handshake parse, timings, ported supervisor knowledge
- `.planning/notes/seed-structured-pane-rendering.md` — Seed: what the pane body should become, why deferred from V14

### Visual contract
- `.planning/sketches/V14-livework-mockup.html` — Pane-content visual contract (with D-07 collapsed-by-default deviation); distill to UI-SPEC via /gsd-ui-phase before plan-phase

### Protocol + SDK (frozen, consumed as-is)
- `.planning/PROTOCOL.md` — §4 endpoints, §6 SSE event taxonomy, §7 permission protocol (choices `a|A|d|y|n`), §8 abort, §10 session persistence
- `contracts/events.schema.json` — Authoritative 21-member event union (never hardcode the member set)
- `sdk/typescript/src/client/rest.ts` — `createSession`/`postMessage` surface
- `sdk/typescript/src/client/sse.ts` — `subscribeToEvents` (sets Bearer header; never raw EventSource)
- `sdk/typescript/src/client/permission.ts` — `replyPermission`, `PermissionChoice`

### Sidecar production home
- `crates/voss-app-core/src/sidecar.rs` — Spawn/handshake/reap implementation the Tauri command wraps (env vars, 60s timeout, stderr drain, stdin heartbeat, kill_on_drop)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/voss-app/src/org/cockpit/RunCommandBar.tsx` — `client?: RunNativeClient` socket (`createSession(spec)`); disabled-with-reason no-op when undefined. V15 injects the real client.
- `apps/voss-app/src/org/feedbackWritePath.ts` — `FollowUpClient` interface (`postMessage`); native-only write-path guard via `nativeSessionNodeId`.
- `apps/voss-app/src/org/live/sseClient.ts` — SSE consumer skeleton: routes events to `ingestEvent` (AttentionQueue) + live overlay; `liveLabel` 'live'|'snapshot' signal. Consumes SDK `subscribeToEvents` verbatim.
- `apps/voss-app/src/org/cockpit/runIntake.ts` — `RunTarget = 'native' | 'terminal'`; spec both start paths consume.
- `apps/voss-app/src/pane/ExitBanner.tsx` — Death-state visual language to reuse for D-11.
- Sidebar quick-launch spawn path (V14 chunk C) — grid-insertion behavior D-02 mirrors.
- Native-card bridge (`registerNativeCard`, `org/model/bridge.ts`) — D-06 attach registration.
- `crates/voss-app-core/src/sidecar.rs` — complete spawn/handshake/reap; gated integration test pattern (`VOSS_SIDECAR_SPIKE=1`).

### Established Patterns
- Disabled-with-reason discipline (decisionActions.ts) — every gated affordance states why; V15 degraded states must follow.
- Honest-data discipline (V14) — no fabricated liveness/streaming/cost; `liveLabel` only 'live' while a stream is actually connected.
- Solid render-layer rules — module-level createSignal + immutable spreads; no produce/structuredClone in tree utils called from render (DATA_CLONE_ERR history).
- Frozen-surface discipline — `crates/` v0.1 members untouched; only `voss-app-core` + `src-tauri` are live Rust members.
- Tauri IPC serde camelCase + contract test (V14 `AgentEntry` lesson) — new Tauri command payloads need the same treatment.

### Integration Points
- `apps/voss-app/src-tauri` — new Tauri command (e.g. `start_voss_serve(cwd)`) + managed state map cwd→`VossServe`.
- `PaneComponent.doSpawn` branch point (V14-11 added managed-spawn branch) — where pane-kind branching already happens; structured panes are a third kind alongside PTY/managed-PTY.
- App-level mount (V14 D-03 pattern) — where client construction + socket injection wires in once per app.
- `apps/voss-app/src/org/attention/attentionQueue.ts` `ingestEvent` — permission events feed here AND the inline gate; one reply loop clears both.

</code_context>

<specifics>
## Specific Ideas

- "Hand to Voss" / outcomes-only copy discipline (V14-10) applies to any new user-facing strings (boot placeholder, ended banner, attach affordance) — no cage/session-tree/pane jargon.
- Statusbar target state from the seed: `● live · voss serve :<port>` once a real server session backs a pane.
- D-07 is a deliberate mockup deviation — collapsed one-liners everywhere; expansion reveals the mockup's excerpt content on demand.

</specifics>

<deferred>
## Deferred Ideas

- Queue↔pane focus linking (clicking an AttentionQueue row focuses the owning pane) — surfaced as a candidate gray area, not discussed; fine to land later or fold into UI-SPEC if trivial.
- Attach-while-turn-busy semantics (409 handling nuance beyond honest error) — researcher can note; not a V15 requirement.
- Session list management (delete/rename from sidebar) — adjacent capability, own phase.

</deferred>

---

*Phase: V15-live-plane-integration*
*Context gathered: 2026-06-09*
