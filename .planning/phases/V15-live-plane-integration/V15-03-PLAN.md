---
phase: V15-live-plane-integration
plan: 03
type: execute
wave: 3
depends_on: ["V15-02"]
files_modified:
  - apps/voss-app/src/pane/ProtocolPane.tsx
  - apps/voss-app/src/pane/ProtocolPane.css
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx
autonomous: true
requirements: [VLIVE-04]
must_haves:
  truths:
    - "A native RunCommandBar run auto-opens a structured pane in the Live Work grid (D-01/D-02 grid path)"
    - "The structured pane renders user→task header, tool lines (collapsed), plan prose, stream.delta/finalize, and final as dedicated DOM per the UI-SPEC"
    - "An out-of-set union member (e.g. cognition_loaded) renders as a generic one-line row — nothing is silently dropped"
    - "Tool lines render collapsed one-liners by default; clicking expands args/result (D-07 mockup deviation)"
    - "The transcript DOM is capped (~300 events) trim-oldest; the task header and pending permission rows are pinned (D-08)"
    - "External CLI / adopted / voss chat PTY panes still render via xterm; the full existing pane suite passes unmodified"
  artifacts:
    - path: "apps/voss-app/src/pane/ProtocolPane.tsx"
      provides: "Structured protocol pane body: AgentEvent[] transcript → dedicated rows + generic fallback, onEvent-fed via connectLiveStream, sticky-bottom autoscroll, D-08 cap"
      exports: ["default"]
      min_lines: 120
    - path: "apps/voss-app/src/pane/ProtocolPane.css"
      provides: ".protocol-pane + .proto-* classes from UI-SPEC §1-2 (task hdr, tool row, plan, stream, final, thinking, generic) — Variant B radius 0, A12 token vocabulary"
      contains: ".protocol-pane"
    - path: "apps/voss-app/src/pane/PaneComponent.tsx"
      provides: "Third doSpawn branch + Show body switch: nativeSessionId → ProtocolPane (no PTY); PTY path untouched"
      contains: "nativeSessionId"
  key_links:
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "ProtocolPane"
      via: "Show when={props.nativeSessionId} renders <ProtocolPane …/> in place of the xterm body"
      pattern: "ProtocolPane"
    - from: "apps/voss-app/src/pane/ProtocolPane.tsx"
      to: "connectLiveStream onEvent"
      via: "onEvent appends each AgentEvent to the local transcript signal"
      pattern: "onEvent"
    - from: "apps/voss-app/src/App.tsx"
      to: "nativeSessionByPaneId"
      via: "native run stores {sessionId, baseUrl, token} per new pane id; threaded GridRoot→SplitNode→PaneComponent"
      pattern: "nativeSessionByPaneId"
---

<objective>
Build the `ProtocolPane` structured pane body that renders the PROTOCOL §6 event union as DOM (per the V15-UI-SPEC), add the third `doSpawn` branch to `PaneComponent` so native RunCommandBar sessions render structured instead of xterm, and thread a per-pane `nativeSessionByPaneId` map App→GridRoot→SplitNode→PaneComponent. This delivers the one approved-mockup element V14 deliberately skipped: the pane body.

Purpose: Voss-native runs graduate from raw PTY bytes to a structured transcript — EM task header, collapsed tool lines (D-07), plan prose, stream deltas, final — with a generic fallback row so no §6 member is dropped (all 21 covered). PTY panes (external CLI / adopted / voss chat) are physically untouched.
Output: `ProtocolPane.tsx` + `ProtocolPane.css`, the `PaneComponent` branch, the App-level native-pane plumbing (incl. the attach seam Plans 04/05 consume), and a `ProtocolPane.test.tsx` covering every dedicated row + the generic fallback + the D-08 cap.
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
@apps/voss-app/src/org/live/sseClient.ts
@apps/voss-app/src/org/live/vossClientBuild.ts

<interfaces>
<!-- Contracts the executor needs. Extracted from codebase + UI-SPEC. -->

The §6 event union — 21 members (authoritative: contracts/events.schema.json, discriminator `type`):
  user · thinking · plan · tool · stream.delta · stream.finalize · final · permission.updated
  · banner · clarify · status · cognition_loaded · cognition_overflow · principles_overflow
  · warning · probable · budget.updated · confidence.updated · gate.updated · server.connected · session.idle
DEDICATED rows (8, per UI-SPEC Event Coverage Table): user, thinking, plan, tool, stream.delta, stream.finalize, final, permission.updated.
GENERIC fallback row (13): all the rest. permission.updated's inline GATE lands in Plan 04 — THIS plan renders it as a placeholder/generic-pinned row that Plan 04 upgrades; never drop it.

From sdk/typescript/src/client/sse.ts:
```typescript
export type AgentEvent = components["schemas"]["EventEnvelope"]["event"];   // discriminated by `type`
// Field shapes (from RESEARCH/schema): tool = {name, state:"pending"|"ok"|"error", summary, args};
// final = {text, confidence?, cost_usd?}; plan = {text, confidence?}; user = {task};
// permission.updated = {id, tool_name, args, dimension}  (NO session_id — Pitfall 3).
```

From apps/voss-app/src/org/live/sseClient.ts (extended by Plan 02):
```typescript
export interface ConnectLiveStreamArgs { baseUrl; sessionId; token; stream?; onEvent?: (ev: AgentEvent)=>void; cardId?: string; }
export function connectLiveStream(args): LiveStreamHandle;   // { abort(): void }
```

From apps/voss-app/src/pane/PaneComponent.tsx (EXTEND — lines 45-62 PaneProps, 284-313 doSpawn, 569-668 body render):
```typescript
export interface PaneProps { id?; cwd?; shell?; index?; agentConfig?: AgentConfig; workspacePath?; embeddedInGrid?; /* + add native* props */ }
// doSpawn (284-313): branch 1 managed agent, branch 2 unmanaged agent, branch 3 plain shell.
// Body: <div ref={bodyRef} class="pane-body"> holds the xterm. ExitBanner already imported (line 20).
// setDot('running'|'loading'|'exited') drives the header status dot.
```

From apps/voss-app/src/pane/ExitBanner.tsx (reuse for Plan 04/05 ended state; THIS plan only wires the prop hole):
```typescript
export interface ExitBannerProps { exitCode: number; onRestart: () => void; }   // renders [exited {code}] + Restart button
// UI-SPEC wants "[session ended]" + NO restart for server death → add optional { message?: string; showRestart?: boolean } props (one-line extension), default to current behavior.
```

From apps/voss-app/src/App.tsx + grid/GridRoot.tsx + grid/SplitNode.tsx (threading path):
```typescript
// MountedWorkspace (App 167-214) holds agentConfigByPaneId: Accessor<Record<string,AgentConfig>>. Add nativeSessionByPaneId similarly.
// GridRoot props (137): agentConfigByPaneId?: Record<string, AgentConfig>; passed to SplitNode (443). Add nativeSessionByPaneId? alongside.
// SplitNode forwards agentConfig to PaneComponent per-leaf. Add the native-session forward the same way.
// Native run grid insertion (D-02): const before = ctrl.snapshot().focusedId; ctrl.splitFocused('H'); const newId=...; if(newId===before) return; (App 319-322 / 365-372)
```

UI-SPEC class contract (verbatim targets — see V15-UI-SPEC.md §1-2 for full CSS):
  .protocol-pane (overflow-y:auto; padding 8px 12px; bg var(--bg-0); font-mono 11px; user-select:text)
  .proto-task-hdr / __glyph(▸,--focus) / __text(--fg-0,600)
  .proto-tool-row (collapsed: __glyph ⏺ state-colored, __name --fg-1, __summary --fg-2 ellipsis, __state ✓/✗/…, __chevron ›); --expanded adds __expanded-body (bg --bg-2, args+result)
  .proto-plan-row (prose, font-ui, border-left 2px --border-bright) + .proto-plan-conf (10px, amber if <0.7)
  .proto-stream-block (--fg-0) + .proto-stream-cursor (cyan blink, removed on finalize); --settled (--fg-1)
  .proto-final-row (__text --fg-0, __meta 10px "conf {x} · ${cost}")
  .proto-thinking-row (italic --fg-3 "… {label}")
  .proto-generic-row (__type mono --fg-3, __summary ellipsis; amber overrides for warning/probable/overflow)
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| server event stream → pane DOM | untrusted event payload text (tool args, stream deltas, final text) is rendered into the transcript |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V15-05 | Tampering / XSS | ProtocolPane event rendering | mitigate | Render ALL event text via Solid's default text-node interpolation (`{value}`), NEVER `innerHTML`/`<div innerHTML=…>`. Solid escapes text bindings; the generic fallback's JSON.stringify and the tool summary are text nodes. No `dangerouslySetInnerHTML`-equivalent anywhere in ProtocolPane. |
| T-V15-06 | (regression) | PTY pane suite | mitigate | The protocol branch is additive — guarded by `props.nativeSessionId`. When absent, PaneComponent behaves exactly as today. The full `src/pane/__tests__/` suite must pass unmodified (regression gate). |
</threat_model>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: ProtocolPane component + CSS (dedicated rows + generic fallback + D-08 cap)</name>
  <files>apps/voss-app/src/pane/ProtocolPane.tsx, apps/voss-app/src/pane/ProtocolPane.css, apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx</files>
  <behavior>
    - Given a session, ProtocolPane subscribes via connectLiveStream and appends each event to a LOCAL createSignal<AgentEvent[]> transcript (one signal per pane instance — never module-level, Pitfall 4)
    - A `user` event renders .proto-task-hdr with the task text; a `tool` event renders a collapsed .proto-tool-row with state-colored glyph + name + summary; a `plan` renders .proto-plan-row prose; stream.delta accumulates into .proto-stream-block; stream.finalize settles it (--settled, cursor removed); `final` renders .proto-final-row with conf/cost meta; `thinking` renders .proto-thinking-row
    - An out-of-set member (cognition_loaded) renders exactly one .proto-generic-row with the type label and a summary; nothing is dropped
    - Clicking a tool row toggles .proto-tool-row--expanded showing args/result (D-07); collapsed is the default and shows NO excerpt
    - When the transcript exceeds CAP=300, the oldest non-pinned events are trimmed; the first `user` (task header) and any `permission.updated` rows are never trimmed (D-08)
    - permission.updated renders a pinned placeholder row (full interactive gate is Plan 04); it is never silently dropped
  </behavior>
  <read_first>
    - .planning/phases/V15-live-plane-integration/V15-UI-SPEC.md (§1 container, §2a-2g every row variant with exact class names + token colors, Event Coverage Table, D-07 deviation record, Animations table) — this is the authoritative visual contract
    - apps/voss-app/src/org/live/sseClient.ts (the connectLiveStream/onEvent contract + the for-await/abort pattern to mirror locally)
    - apps/voss-app/src/pane/pane.css (existing .pane-body conventions + how pane CSS is structured — ProtocolPane.css follows the same token vocabulary, no raw hex)
    - apps/voss-app/src/styles/variant-b.css (the --bg-*/--fg-*/--accent-*/--tool/--focus tokens ProtocolPane.css consumes; Variant B radius 0 rule)
    - .planning/phases/V15-live-plane-integration/V15-PATTERNS.md (ProtocolPane.tsx section: local-signal pattern, appendEvent/trimOldest with pins, for-await, immutable spread rule)
    - apps/voss-app/src/pane/__tests__/scrollbackRegistry.test.ts (a vitest+jsdom pane test for structure reference) and apps/voss-app/src/org/live/__tests__/mockSseStream.ts (the async-generator stream you inject in tests)
  </read_first>
  <action>
    Create `apps/voss-app/src/pane/ProtocolPane.tsx` exporting a default `ProtocolPane(props: { sessionId: string; baseUrl: string; token: string; onEnded?: () => void })`. Hold LOCAL signals: `events = createSignal<AgentEvent[]>([])`, `expanded = createSignal<Set<number>>(new Set())` (which tool rows are open, by index). On mount, call `connectLiveStream({ baseUrl: props.baseUrl, sessionId: props.sessionId, token: props.token, cardId: props.sessionId, onEvent: appendEvent })` and store the handle; `onCleanup(() => handle.abort())`. Implement `appendEvent(ev)` with the D-08 cap: `setEvents(prev => trimOldest([...prev, ev], 300))` where `trimOldest` is a pure module function that removes oldest entries whose `type` is NOT `'user'`-at-index-0 and NOT `'permission.updated'` until length ≤ cap (immutable; spread, never produce/structuredClone).

    Render the transcript with `<For each={events()}>` switching on `ev.type` to the dedicated row components (task hdr, tool, plan, stream, final, thinking) and a `.proto-generic-row` default for every other member. Map the §6 union via a `switch` whose `default:` is the generic row — never add a case that is not in the union. For `stream.delta`/`stream.finalize` (D-09), accumulate consecutive deltas into one growing `.proto-stream-block` (a derived view that coalesces adjacent stream events) with the V14 honest streaming pulse cursor, stripping the cursor and settling to `--settled` plain prose when a finalize arrives. Sticky-bottom auto-scroll: keep the scroll pinned to the bottom on new events unless the user has scrolled up >20px (detect via scroll position), resuming auto-scroll when they return to within 20px of the bottom (D-09). The generic row's summary uses the first present field in priority `message → label → task → text → JSON.stringify(payload).slice(0,80)`. Tool rows are collapsed by default; an `onClick` toggles the index in `expanded()`; expanded shows args (key:value) + result excerpt (truncate ~20 lines). Render permission.updated as a pinned `.proto-permission-gate` placeholder row with the warning label + args (Plan 04 makes the buttons live). ALL text via `{…}` text bindings — never innerHTML (T-V15-05).

    Create `apps/voss-app/src/pane/ProtocolPane.css` implementing every class in the UI-SPEC §1-2 (and the `.proto-permission-gate` skeleton, `.proto-boot`, `.proto-spawn-error`, `.proto-ended-row`, `.statusbar-live-indicator` shells so Plans 04/05 only fill behavior) using token vars only, `border-radius: 0` (Variant B) except where the spec says otherwise, and the `proto-pulse`/`proto-cursor-blink` keyframes. Do not add `!important` to animations (the shell-wide reduced-motion kill switch already covers them).

    Create `apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx`: render with an injected async-generator stream (reuse/extend mockSseStream) and assert — task header text present; a tool event yields a collapsed `.proto-tool-row` with no excerpt visible; clicking it reveals `.proto-tool-row--expanded`; a plan event yields `.proto-plan-row`; stream.delta then stream.finalize yields a settled `.proto-stream-block--settled`; a final event yields `.proto-final-row`; a `cognition_loaded` event yields exactly one `.proto-generic-row` (assert nothing dropped: row count === event count for a scripted sequence with no coalescing); push >300 events and assert the task-header row survives while an early non-pinned row is gone.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/pane/__tests__/ProtocolPane.test.tsx 2>&1 | tail -18</automated>
  </verify>
  <acceptance_criteria>
    - `ProtocolPane.tsx` exists, exports default, holds LOCAL (in-component) `createSignal<AgentEvent[]>` (grep: no module-level transcript signal)
    - `ProtocolPane.css` contains `.protocol-pane`, `.proto-task-hdr`, `.proto-tool-row`, `.proto-plan-row`, `.proto-stream-block`, `.proto-final-row`, `.proto-generic-row`
    - No `innerHTML` / `dangerouslySet` token anywhere in ProtocolPane.tsx (grep returns 0) — T-V15-05
    - No `produce(` / `structuredClone(` in ProtocolPane.tsx (grep, comment-filtered, returns 0)
    - `ProtocolPane.test.tsx` asserts: collapsed tool row (no excerpt) → click → expanded; generic row for cognition_loaded; settled stream block; D-08 task-header pin survives a >300-event flood
    - `npx --no vitest run src/pane/__tests__/ProtocolPane.test.tsx` exits 0
  </acceptance_criteria>
  <done>ProtocolPane renders the full §6 union (8 dedicated + generic fallback), collapsed tool lines with click-expand, coalesced stream blocks, and the D-08 capped/pinned transcript — all via escaped text bindings.</done>
</task>

<task type="auto">
  <name>Task 2: PaneComponent protocol branch + native-pane threading (App→GridRoot→SplitNode)</name>
  <files>apps/voss-app/src/pane/PaneComponent.tsx, apps/voss-app/src/grid/GridRoot.tsx, apps/voss-app/src/grid/SplitNode.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/pane/PaneComponent.tsx (lines 1-62 imports+PaneProps, 284-313 doSpawn, 569-668 body render — you add native* props, a doSpawn early-return for native panes, and a Show that swaps the body to ProtocolPane)
    - apps/voss-app/src/grid/GridRoot.tsx (lines 137 + 443 — the agentConfigByPaneId prop + its forward to SplitNode; add nativeSessionByPaneId alongside)
    - apps/voss-app/src/grid/SplitNode.tsx (how it forwards agentConfig to each leaf PaneComponent — mirror for the native-session record)
    - apps/voss-app/src/App.tsx (lines 167-214 MountedWorkspace — add nativeSessionByPaneId signal; 280-385 the native run path — store the record on the new pane id after the D-02 split; 1400-1420 the GridRoot mount — pass the new map)
    - apps/voss-app/src/org/live/vossClientBuild.ts + sidecarClient.ts (the client/handshake the native run already builds in Plan 02 — reuse, do not rebuild)
    - .planning/phases/V15-live-plane-integration/V15-PATTERNS.md (PaneComponent doSpawn third-branch + Show body-switch patterns; App grid-insertion D-02)
  </read_first>
  <action>
    Extend `PaneProps` in `PaneComponent.tsx` with optional `nativeSessionId?: string; nativeBaseUrl?: string; nativeToken?: string;` (the discriminator is `nativeSessionId`). In `doSpawn`, add an early `if (props.nativeSessionId) { setDot('running'); return; }` BEFORE the agentConfig branches — protocol panes never spawn a PTY. In the body render, wrap the existing xterm `<div ref={bodyRef} class="pane-body">` in `<Show when={props.nativeSessionId} fallback={<existing pane-body>}>` and render `<ProtocolPane sessionId={props.nativeSessionId!} baseUrl={props.nativeBaseUrl!} token={props.nativeToken!} onEnded={() => setExitCode(1)} />` in the truthy slot (import ProtocolPane). Do NOT alter any PTY code path (T-V15-06).

    Thread a per-pane native-session map: in `App.tsx` `MountedWorkspace`, add `nativeSessionByPaneId: Accessor<Record<string, { sessionId: string; baseUrl: string; token: string }>>` + its setter (mirror `agentConfigByPaneId` exactly, lines 175-176 + 192-194 + 210-211). In the native run handler (the Bridge-A path that already builds the client in Plan 02), after the D-02 split yields `newId`, set `ws.setNativeSessionByPaneId({ ...ws.nativeSessionByPaneId(), [newId]: { sessionId, baseUrl, token } })` so the new pane renders ProtocolPane (D-01/D-03: one pane per native run). When the app is in Run Review, flip to Live Work focused on the new pane (D-01) — reuse the existing review→grid flip the codebase already has (openInGridRequest / orgViewOpen=false).

    Pass the map down: add `nativeSessionByPaneId?: Record<string, {…}>` to `GridRoot` props and forward it to `SplitNode` (mirror line 443); in `SplitNode`, forward the matching record's fields as `nativeSessionId`/`nativeBaseUrl`/`nativeToken` to each leaf `PaneComponent` (mirror the agentConfig forward). Pass `nativeSessionByPaneId={ws()!.nativeSessionByPaneId()}` at the GridRoot mount in App.tsx.

    Leave an exported App-level seam for Plans 04/05: expose a `openAttachedPane(record: { sessionId; baseUrl; token })` helper (same D-02 split + map-set as a native run, minus createSession) so the attach surface (Plan 05) and AC suite need not re-touch App.tsx — Plan 05 imports/uses it. Keep it a thin wrapper over the same insertion path.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/pane/__tests__/ 2>&1 | tail -12 && npx --no tsc --noEmit 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `PaneComponent.tsx` PaneProps contains `nativeSessionId`, `nativeBaseUrl`, `nativeToken`
    - `doSpawn` returns early (no PTY spawn) when `props.nativeSessionId` is set
    - The body render has a `<Show when={props.nativeSessionId}` that renders `<ProtocolPane`
    - `GridRoot.tsx` and `SplitNode.tsx` forward the native-session record to PaneComponent (grep `nativeSessionByPaneId` in GridRoot; `nativeSessionId=` in SplitNode)
    - `App.tsx` MountedWorkspace has `nativeSessionByPaneId` + setter and an `openAttachedPane` helper
    - The full existing pane suite passes unmodified: `npx --no vitest run src/pane/__tests__/` exits 0 (T-V15-06)
    - `tsc --noEmit` reports no new errors vs. baseline
  </acceptance_criteria>
  <done>Native runs open a structured ProtocolPane via the D-02 grid path; PTY panes are untouched (suite green); the App-level attach seam is exposed for Plans 04/05.</done>
</task>

</tasks>

<verification>
- `cd apps/voss-app && npx --no vitest run src/pane/__tests__/` exits 0 (ProtocolPane + the full unmodified PTY suite — T-V15-06)
- `npx --no tsc --noEmit` no new errors vs. baseline
- grep: `ProtocolPane` referenced from PaneComponent; `onEvent` used in ProtocolPane; `nativeSessionByPaneId` in App + GridRoot
- grep: zero `innerHTML`/`dangerouslySet`/`produce(`/`structuredClone(` in ProtocolPane.tsx
</verification>

<success_criteria>
- Structured pane renders header/tool/plan/stream/final per UI-SPEC; an out-of-set member renders a generic row, nothing dropped (VLIVE-04)
- Tool lines collapsed by default, click-expand (D-07); transcript capped + task/permission pinned (D-08)
- External CLI / adopted / voss chat panes still render via PTY; full pane suite unmodified (VLIVE-04 acceptance, T-V15-06)
- All event text rendered via escaped text bindings — no XSS surface (T-V15-05)
</success_criteria>

<output>
Create `.planning/phases/V15-live-plane-integration/V15-03-SUMMARY.md` when done
</output>
