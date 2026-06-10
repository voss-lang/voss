---
phase: V15-live-plane-integration
plan: 05
type: execute
wave: 4
depends_on: ["V15-03"]
files_modified:
  - apps/voss-app/src/org/cockpit/serverSessions.ts
  - apps/voss-app/src/org/cockpit/CockpitSidebar.tsx
  - apps/voss-app/src/org/cockpit/CockpitShell.tsx
  - apps/voss-app/src/org/cockpit/serverSessions.css
  - apps/voss-app/src/org/cockpit/__tests__/serverSessions.test.ts
autonomous: true
requirements: [VLIVE-06]
must_haves:
  truths:
    - "A cockpit sidebar 'Server sessions' section lists every session GET /session returns, newest first, with id/title/age"
    - "Clicking Attach opens a structured pane onto that session via the D-02 grid path and registers it as a native cockpit card"
    - "Attach works after app restart: a respawned sidecar lists the prior session, attach renders forward events, and a follow-up returns 202"
    - "The list reflects whatever GET /session returns — no source filtering (CLI voss chat sessions included)"
    - "Transcript backfill is NOT promised: attach renders new events forward (PROTOCOL v1 has no history endpoint)"
  artifacts:
    - path: "apps/voss-app/src/org/cockpit/serverSessions.ts"
      provides: "module-level session-list signal + refreshSessions(client) + attach handler that respawns the sidecar (if cold) then opens an attached pane"
      exports: ["serverSessions", "refreshSessions", "attachSession", "__resetServerSessions"]
    - path: "apps/voss-app/src/org/cockpit/CockpitSidebar.tsx"
      provides: "'Server sessions' collapsible section (D-04) — list rows + Attach action; empty state"
      contains: "Server sessions"
  key_links:
    - from: "apps/voss-app/src/org/cockpit/serverSessions.ts"
      to: "VossClient.listSessions"
      via: "refreshSessions(client) populates the signal"
      pattern: "listSessions"
    - from: "apps/voss-app/src/org/cockpit/CockpitSidebar.tsx"
      to: "attach handler (openAttachedPane seam)"
      via: "Attach button → onAttach(sessionId) → App openAttachedPane(record)"
      pattern: "onAttach"
---

<objective>
Add the "Server sessions" cockpit sidebar section (D-04 / VLIVE-06): list every session `GET /session` returns (newest first, no filtering), and let the user Attach a structured pane onto any of them — including after an app restart, where the section respawns the sidecar before listing. Attach lands a ProtocolPane via the same D-02 grid path as a native run and registers the session as a native cockpit card (D-06: attached ≡ started).

Purpose: Close VLIVE-06. A relaunch no longer strands `.voss/sessions` records — the user can re-open a structured pane onto a prior server session, subscribe forward, and post follow-ups. Transcript backfill is explicitly out (PROTOCOL v1 has no history endpoint; contracts frozen).
Output: `serverSessions.ts` (list signal + refresh + attach), the sidebar section + CSS, the CockpitShell prop threading, and a test driving list→attach against a mocked client.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/V15-live-plane-integration/V15-SPEC.md
@.planning/phases/V15-live-plane-integration/V15-UI-SPEC.md
@.planning/phases/V15-live-plane-integration/V15-RESEARCH.md
@.planning/phases/V15-live-plane-integration/V15-PATTERNS.md
@apps/voss-app/src/org/live/sidecarClient.ts
@apps/voss-app/src/org/live/vossClientBuild.ts

<interfaces>
<!-- Contracts the executor needs. Extracted from codebase + UI-SPEC. -->

From sdk/typescript/src/client/rest.ts:
```typescript
listSessions(): Promise<SessionInfo[]>;   // GET /session — SessionInfo = JsonObject (OPAQUE — see Wave 0 inspection note below)
export type SessionInfo = Record<string, unknown>;
```

⚠ SessionInfo shape is opaque (RESEARCH Open Question 1 / A1). Wave 0 step: inspect the real shape before building rows — run
`VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core sidecar -- --nocapture` is NOT the body; instead read `voss/api/routes/session.py` (or the saved-session schema) to learn which of {id, title, task, created_at} are present. Design rows to degrade gracefully: id is required (first 8 chars), title falls back to the id, age falls back to blank if no timestamp.

From apps/voss-app/src/org/cockpit/serverSessions.ts (NEW — mirror sseClient.ts module pattern):
```typescript
// const [serverSessions, setServerSessions] = createSignal<SessionInfo[]>([]);
// export async function refreshSessions(client: VossClient): Promise<void>  // try listSessions, degrade silently on error
// export async function attachSession(args): Promise<void>  // respawn sidecar if cold → openAttachedPane(record)
// export function __resetServerSessions(): void   // afterEach reset (mirror __resetLiveStream)
```

From apps/voss-app/src/App.tsx (the seam Plan 03 exposed — DO NOT re-touch App.tsx in this plan):
```typescript
// Plan 03 exposes openAttachedPane(record: { sessionId; baseUrl; token; client? }) — same D-02 split + nativeSessionByPaneId set as a native run, minus createSession.
// This plan calls that seam via a callback threaded into the sidebar (onAttach), so attach does not duplicate grid logic.
// registerNativeCard(sessionId, sessionId) (Bridge A) makes the attached session a native card (D-06).
```

From apps/voss-app/src/org/cockpit/CockpitSidebar.tsx (EXTEND — collapsible-section pattern):
```typescript
// Existing props: { data: RunData | null; swarm: SwarmReconcileResult }
// Existing collapsible pattern: const [sessionsOpen, setSessionsOpen] = createSignal(false); <button class="cs-section__toggle">…<Show when=…>
// ADD props: vossClient?: VossClient; onAttach?: (sessionId: string) => void   (section hidden when no client)
// Mounted in CockpitShell at line 156: <CockpitSidebar data={runData()} swarm={swarm()} /> — thread the two new props through CockpitShell.
```

UI-SPEC §7 "Server sessions" section (verbatim targets):
  .cockpit-sect header "Server sessions" (uppercase, Poppins 600, --fg-3)
  .cockpit-server-session-row { .css-row__id (mono 11px --fg-3, first 8 chars), .css-row__title (ui 12px --fg-1 ellipsis max 18ch), .css-row__age (mono 11px --fg-3, "3m"/"2h"/"1d"), .css-row__attach (button, --focus, opacity 0 → 1 on row hover) }
  Empty state: .cockpit-sidebar__empty "No previous sessions"
  newest-first (D-05), max-height 240px overflow-y auto. Attach copy = "Attach". No confirmation dialog.
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GET /session response → sidebar DOM | server-provided session metadata (id/title) rendered as text |
| Attach intent → sidecar respawn | attach may trigger a `start_voss_serve` if the server is cold (post-restart) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V15-08 | Spoofing / Tampering | attach via listed session | mitigate | Attach only acts on ids returned by the authenticated `GET /session` (Bearer-authed client). The respawn-if-cold path goes through `start_voss_serve` which validates cwd (Plan 01 T-V15-01). No arbitrary session id is attachable from user input — only list rows. |
| T-V15-05 | Tampering / XSS | session id/title render | mitigate | id/title/age render via Solid text bindings, never innerHTML. Carried discipline. |
| T-V15-12 | Information Disclosure | over-promising backfill | mitigate (honesty) | The UI never shows fabricated history; attach renders forward events only. No fake "loading transcript…" that implies backfill exists (PROTOCOL v1 has no history endpoint — SPEC boundary). |
</threat_model>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: serverSessions module — list signal + refresh + attach (respawn-if-cold)</name>
  <files>apps/voss-app/src/org/cockpit/serverSessions.ts, apps/voss-app/src/org/cockpit/__tests__/serverSessions.test.ts</files>
  <behavior>
    - refreshSessions(client) calls client.listSessions() and populates serverSessions() newest-first; on error it degrades to an empty/unchanged list without throwing
    - serverSessions() rows expose id (required), a title (falls back to id) and an age (blank if no timestamp) — robust to the opaque SessionInfo shape
    - attachSession({ cwd, sessionId, ensureClient, openAttachedPane }) ensures a live client (respawning the sidecar via startVossServe if cold — post-restart), then calls openAttachedPane({ sessionId, baseUrl, token, client }) and registerNativeCard(sessionId, sessionId) (D-06)
    - attachSession never promises transcript backfill — it only wires the forward stream + write path (no history fetch)
    - __resetServerSessions() clears the signal (test isolation)
  </behavior>
  <read_first>
    - apps/voss-app/src/org/live/sseClient.ts (the module-level signal + exported-function + __reset pattern this module mirrors exactly)
    - sdk/typescript/src/client/rest.ts (listSessions + SessionInfo opacity — lines 64-68, 21)
    - apps/voss-app/src/org/live/vossClientBuild.ts + sidecarClient.ts (buildVossClientFromHandshake + startVossServe — the respawn-if-cold path)
    - apps/voss-app/src/org/model/bridge.ts (registerNativeCard — Bridge A; D-06 attach registration)
    - voss/api/routes/session.py (Wave 0: read to learn the real SessionInfo field names {id/title/task/created_at} before designing row accessors — RESEARCH Open Question 1)
    - .planning/phases/V15-live-plane-integration/V15-PATTERNS.md (serverSessions.ts module pattern + test-reset)
  </read_first>
  <action>
    Create `apps/voss-app/src/org/cockpit/serverSessions.ts` mirroring `sseClient.ts`'s module structure: `const [serverSessions, setServerSessions] = createSignal<SessionInfo[]>([])` and `const [loading, setLoading] = createSignal(false)`. Export `async function refreshSessions(client: VossClient): Promise<void>` that sets loading, `try { setServerSessions(sortNewestFirst(await client.listSessions())) } catch { /* degrade silently */ } finally { setLoading(false) }`. Add pure accessors `sessionId(info)`, `sessionTitle(info)` (fallback to id), `sessionAgeLabel(info)` (relative "3m"/"2h"/"1d" from a created_at-like field, blank if absent) — use the real field names confirmed from the Wave-0 read of `session.py`; keep them defensive (optional chaining + fallbacks) given SessionInfo opacity (A1).

    Export `async function attachSession(args: { cwd: string; sessionId: string; ensureClient: (cwd: string) => Promise<{ baseUrl: string; token: string; client: VossClient }>; openAttachedPane: (r: { sessionId: string; baseUrl: string; token: string; client: VossClient }) => void }): Promise<void>` — call `ensureClient(args.cwd)` (this respawns the sidecar if cold, post-restart — T-V15-08), then `registerNativeCard(args.sessionId, args.sessionId)` (D-06), then `openAttachedPane({ sessionId: args.sessionId, baseUrl, token, client })`. No history fetch (T-V15-12). Export `__resetServerSessions()` clearing both signals.

    Create `serverSessions.test.ts`: mock a VossClient with `listSessions` returning two records; assert `refreshSessions` populates newest-first and that a throwing `listSessions` leaves the list empty without throwing. Assert `attachSession` calls `ensureClient(cwd)`, then `registerNativeCard(sessionId, sessionId)`, then `openAttachedPane` with the resolved `{sessionId, baseUrl, token, client}` — and that it performs NO history/transcript fetch (the mocked client's other methods are not called).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/org/cockpit/__tests__/serverSessions.test.ts 2>&1 | tail -14</automated>
  </verify>
  <acceptance_criteria>
    - `serverSessions.ts` exports `serverSessions`, `refreshSessions`, `attachSession`, `__resetServerSessions`
    - `refreshSessions` calls `listSessions` and degrades silently on error (test proves empty list, no throw)
    - `attachSession` order: `ensureClient` → `registerNativeCard(sessionId, sessionId)` → `openAttachedPane({sessionId, baseUrl, token, client})`; no extra client calls (no backfill — T-V15-12)
    - Row accessors tolerate missing title/timestamp (fallback to id / blank)
    - `npx --no vitest run src/org/cockpit/__tests__/serverSessions.test.ts` exits 0
  </acceptance_criteria>
  <done>The session-list signal, newest-first refresh, and respawn-if-cold attach (register native card + open forward pane, no backfill) exist and are tested against a mocked client.</done>
</task>

<task type="auto">
  <name>Task 2: 'Server sessions' sidebar section (D-04) + CockpitShell threading</name>
  <files>apps/voss-app/src/org/cockpit/CockpitSidebar.tsx, apps/voss-app/src/org/cockpit/CockpitShell.tsx, apps/voss-app/src/org/cockpit/serverSessions.css</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/CockpitSidebar.tsx (the existing collapsible-section pattern — createSignal(false) toggle + cs-section__toggle + <Show>; the props interface to extend; the For+list rendering of existing sections to mirror)
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (line 156 <CockpitSidebar data swarm /> — thread vossClient + onAttach through; this plan ADDS to CockpitShell's props the two values and forwards them — note Plan 02 already added followUpClient here, so coordinate: append, do not overwrite)
    - apps/voss-app/src/org/cockpit/serverSessions.ts (Task 1 — serverSessions(), refreshSessions, sessionId/sessionTitle/sessionAgeLabel accessors)
    - .planning/phases/V15-live-plane-integration/V15-UI-SPEC.md §7 (section header, row classes, empty state, hover-reveal Attach, max-height) + Copywriting Contract (section header "Server sessions", "Attach", "No previous sessions")
    - apps/voss-app/src/org/cockpit/cockpitStyles.css or orgStyles.css (where .cockpit-sect / .org-run-picker__row live — match the existing section + row look; serverSessions.css adds only the new .cockpit-server-session-row + .css-row__* classes with tokens, radius 0)
  </read_first>
  <action>
    Extend `CockpitSidebar.tsx` props with `vossClient?: VossClient` and `onAttach?: (sessionId: string) => void`. Add a fourth collapsible section "Server sessions" using the existing toggle pattern (`const [serverSessionsOpen, setServerSessionsOpen] = createSignal(false)`). When the section opens AND `props.vossClient` is present, call `refreshSessions(props.vossClient)` (createEffect on open). Render `<For each={serverSessions()}>` rows as `.cockpit-server-session-row` with `.css-row__id` (first 8 chars of sessionId), `.css-row__title` (sessionTitle), `.css-row__age` (sessionAgeLabel), and a `.css-row__attach` "Attach" button that calls `props.onAttach?.(sessionId(info))`. Show the `.cockpit-sidebar__empty` "No previous sessions" when the list is empty. When `props.vossClient` is undefined, hide the section entirely (no client = nothing to list). All text via escaped bindings (T-V15-05). Newest-first ordering comes from the signal (D-05) — no per-source filtering.

    Thread through `CockpitShell.tsx`: add `vossClient?: VossClient` and `onAttach?: (sessionId: string) => void` to CockpitShell props (alongside the `followUpClient?` added in Plan 02 — append), and forward both to `<CockpitSidebar data={runData()} swarm={swarm()} vossClient={props.vossClient} onAttach={props.onAttach} />` at line 156. (App.tsx already mounts CockpitShell; App passes `vossClient()?.client` and an `onAttach` that calls the Plan-03 `openAttachedPane` seam via `attachSession`. App.tsx wiring of these two props is a one-line-each addition that belongs to whichever of Plan 02/03 owns the CockpitShell mount — if not already present, add the two props at the CockpitShell mount; this is the only App.tsx touch and it is additive prop-passing, not logic.)

    Create `serverSessions.css` with the UI-SPEC §7 classes (`.cockpit-server-session-row`, `.css-row__id/__title/__age/__attach`, hover-reveal opacity, :focus-visible outline) using tokens only, radius 0, max-height 240px overflow-y auto on the list container. Import it from CockpitSidebar.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/org/cockpit/__tests__/ 2>&1 | tail -14 && npx --no tsc --noEmit 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `CockpitSidebar.tsx` renders a "Server sessions" section; rows show id (8 chars)/title/age + an "Attach" button calling `onAttach`
    - The section is hidden when `vossClient` is undefined; shows "No previous sessions" when the list is empty
    - `CockpitShell.tsx` forwards `vossClient` and `onAttach` to `<CockpitSidebar>` (grep both on the CockpitSidebar mount)
    - `serverSessions.css` contains `.cockpit-server-session-row` and `.css-row__attach`
    - Forbidden copy terms absent; strings match the Copywriting Contract ("Server sessions", "Attach", "No previous sessions")
    - No `innerHTML` in the new TSX (grep 0)
    - `npx --no vitest run src/org/cockpit/__tests__/` exits 0; `tsc --noEmit` no new errors
  </acceptance_criteria>
  <done>The cockpit sidebar lists server sessions (newest-first, unfiltered) with a hover-revealed Attach action that opens a forward structured pane via the D-02 seam; hidden cleanly when no sidecar client exists.</done>
</task>

</tasks>

<verification>
- `cd apps/voss-app && npx --no vitest run src/org/cockpit/__tests__/` exits 0
- `npx --no tsc --noEmit` no new errors vs. baseline
- grep: `listSessions` in serverSessions; `onAttach` in CockpitSidebar; `vossClient`/`onAttach` forwarded in CockpitShell
</verification>

<success_criteria>
- "Server sessions" section lists everything GET /session returns, newest first, unfiltered (VLIVE-06 / D-04 / D-05)
- Attach opens a structured pane via the D-02 grid path + registers a native card (D-06); works post-restart via respawn-if-cold (VLIVE-06, T-V15-08)
- No transcript backfill promised — forward events only (T-V15-12)
- Session metadata rendered as escaped text (T-V15-05)
</success_criteria>

<output>
Create `.planning/phases/V15-live-plane-integration/V15-05-SUMMARY.md` when done
</output>
