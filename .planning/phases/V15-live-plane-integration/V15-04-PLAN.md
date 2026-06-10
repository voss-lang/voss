---
phase: V15-live-plane-integration
plan: 04
type: execute
wave: 4
depends_on: ["V15-03"]
files_modified:
  - apps/voss-app/src/pane/ProtocolPane.tsx
  - apps/voss-app/src/pane/ProtocolPane.css
  - apps/voss-app/src/pane/ExitBanner.tsx
  - apps/voss-app/src/org/attention/attentionQueue.ts
  - apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx
  - apps/voss-app/src/org/attention/__tests__/attentionQueue.test.tsx
autonomous: true
requirements: [VLIVE-05, VLIVE-07]
must_haves:
  truths:
    - "A permission.updated event renders an inline gate (Deny / Allow once / Allow for scope) in the pane AND a queue row simultaneously"
    - "Replying from either surface issues one POST /session/:id/permission (d/a/A) and clears the pending state in BOTH surfaces"
    - "Cold start shows an in-pane 'Starting…' boot placeholder with an elapsed counter until the stream connects (D-10)"
    - "Spawn failure shows an in-pane error with the stderr tail and a Retry start button (D-12)"
    - "Server death mid-run appends an ended banner, dims the pane, flips liveLabel to snapshot, and disables follow-up with reason; the next native run respawns fresh (D-11)"
  artifacts:
    - path: "apps/voss-app/src/org/attention/attentionQueue.ts"
      provides: "resolveAttentionItem(id) — the inverse of pushItem; clears a queue row by id"
      exports: ["resolveAttentionItem"]
    - path: "apps/voss-app/src/pane/ProtocolPane.tsx"
      provides: "Live inline permission gate (replyPermission + dual-surface clear) + boot/error/ended lifecycle states"
      contains: "replyPermission"
    - path: "apps/voss-app/src/pane/ExitBanner.tsx"
      provides: "Optional message + showRestart props (default unchanged) for the [session ended] no-restart server-death case"
      contains: "showRestart"
  key_links:
    - from: "apps/voss-app/src/pane/ProtocolPane.tsx"
      to: "replyPermission (SDK)"
      via: "gate button → replyPermission(client, sessionId, {id, choice}) then resolveAttentionItem(`permission:${id}`)"
      pattern: "replyPermission"
    - from: "apps/voss-app/src/pane/ProtocolPane.tsx"
      to: "resolveAttentionItem"
      via: "dual-surface clear after a successful reply"
      pattern: "resolveAttentionItem"
---

<objective>
Make the permission gate live and add the three lifecycle-honesty states to `ProtocolPane`. A `permission.updated` event renders an interactive in-pane gate (Deny / Allow once / Allow for scope → §7 `d`/`a`/`A`) that shares one reply loop with the AttentionQueue: replying from either surface issues exactly one `POST /session/:id/permission` and clears both. Cold start, spawn failure, and server death each render a truthful in-pane state.

Purpose: Close VLIVE-05 (inline gate + shared reply loop) and VLIVE-07 (cold-start affordance, spawn-failure stderr surface, honest server-death degrade — no auto-restart). Nothing fakes liveness; every degraded state is visible with an outcomes-only string.
Output: `resolveAttentionItem` on the queue, the live gate + dual-surface clear in ProtocolPane, the boot/error/ended states (D-10/D-11/D-12) reusing ExitBanner, and tests proving one reply clears both surfaces and that server death disables follow-up while the next run respawns.
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

<interfaces>
<!-- Contracts the executor needs. Extracted from codebase + UI-SPEC. -->

From sdk/typescript/src/client/permission.ts:
```typescript
export type PermissionChoice = "a" | "A" | "d" | "y" | "n";
export async function replyPermission(client: VossClient, sessionId: string, args: { id: string; choice: PermissionChoice }): Promise<void>;
// POST /session/{session_id}/permission { v:1, id, choice } — requires Bearer (server 401 without). Throws VossApiError on !ok.
```

From apps/voss-app/src/org/attention/attentionQueue.ts (ADD resolveAttentionItem — mirror pushItem):
```typescript
// pushItem (83-88): setAttentionQueue(prev => prev.some(e=>e.id===item.id) ? prev : [...prev, item]);
// Permission items are stored with id === `permission:${ev.id}` (line 159) — the prefix is LOAD-BEARING.
// ingestEvent(ev, {cardId}) already enqueues the permission row (Plan 02 passes cardId).
export function __resetAttentionQueue(): void;   // afterEach reset
// MISSING today: a removal API. Add:  export function resolveAttentionItem(id: string): void  // filter out by id (immutable)
```

UI-SPEC §3 Inline Permission Gate (verbatim targets):
  .proto-permission-gate (border/bg color-mix accent-red, padding 8px 12px, radius 0; PINNED — never trimmed)
    __label "⚠ needs your approval · {dimension}"   (dimension: "tool"|"confidence"|"budget")
    __args  "{tool_name}: {args summary}" (mono)
    __btns → .proto-pgbtn (Deny=d / Allow once=a / Allow for {scope}=A); :disabled while in-flight
  After reply → .proto-permission-gate--resolved (opacity .5, btns hidden, __resolved-label "denied"|"allowed once"|"allowed for scope")
  Tab order Deny → Allow once → Allow for scope; Enter triggers; on POST error, re-enable buttons.

UI-SPEC §4 Boot (D-10): .proto-boot { __label "Starting…"; __elapsed "{N}s" (updates/sec); __sub "Cold start takes up to 60s" after 5s }
UI-SPEC §5 Spawn-failure (D-12): .proto-spawn-error { __heading "Could not start — {reason}"; __stderr <tail>; __retry "Retry start" → re-invoke start_voss_serve }
UI-SPEC §6 Ended (D-11): reuse <ExitBanner> inline in transcript flow; "[session ended]"; err-tier dot; NO Restart button; .pane--proto-ended { opacity .75 } (reduced-motion: no transition)
Copywriting Contract (forbidden terms: cage, Voss-native, PermissionGate, session-tree, partial lineage, "pane" as user noun). Follow-up disabled (server dead): "Server unavailable — start a new run to continue".

From apps/voss-app/src/pane/ExitBanner.tsx:
```typescript
export interface ExitBannerProps { exitCode: number; onRestart: () => void; }
// renders <span eb-dot>, <span eb-msg>[exited {code}]</span>, <button eb-restart>Restart</button>
// EXTEND: add optional `message?: string` (override "[exited N]") and `showRestart?: boolean` (default true). Server death passes message="[session ended]" showRestart={false}.
```
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pane gate → loopback permission POST | a user decision (allow/deny) crosses to the server; must carry Bearer and be idempotent per id |
| spawn-failure stderr → pane DOM | the captured stderr tail (process output) is rendered as text |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V15-07 | Elevation of Privilege | permission gate reply | mitigate | Replies go through the SDK `replyPermission` (Bearer-authed; server enforces 401 without token — spike-proven). Buttons disable immediately on click to prevent a double-POST; on POST error the gate re-enables (no silent allow). The dual-surface clear runs ONLY after the POST resolves — never optimistically grant. |
| T-V15-05 | Tampering / XSS | spawn-error stderr render | mitigate | The stderr tail and gate args render via Solid text bindings (`{stderr}`), never innerHTML. Carried from Plan 03 discipline. |
| T-V15-11 | Spoofing | dual-surface id mismatch | mitigate | The queue row id is `permission:${ev.id}`; the clear MUST use the identical prefixed id (load-bearing). A test asserts the prefix so a refactor cannot silently desync the two surfaces. |
</threat_model>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: resolveAttentionItem + live inline permission gate with dual-surface clear</name>
  <files>apps/voss-app/src/org/attention/attentionQueue.ts, apps/voss-app/src/pane/ProtocolPane.tsx, apps/voss-app/src/pane/ProtocolPane.css, apps/voss-app/src/org/attention/__tests__/attentionQueue.test.tsx, apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx</files>
  <behavior>
    - resolveAttentionItem(`permission:${id}`) removes exactly that queue row and leaves others intact (immutable)
    - A permission.updated event renders BOTH a pinned inline gate in the pane AND a queue row (ingestEvent already does the queue row)
    - Clicking Allow once disables all three buttons, calls replyPermission(client, sessionId, {id, choice:'a'}), and on success transitions the gate to --resolved "allowed once" AND removes the queue row via resolveAttentionItem
    - Deny maps to 'd' / Allow for scope maps to 'A'; the resolved label matches (denied / allowed for scope)
    - If replyPermission rejects, the buttons re-enable and the gate stays pending (no resolved state, no queue clear)
    - The gate is never trimmed by the D-08 cap (pinned)
  </behavior>
  <read_first>
    - apps/voss-app/src/org/attention/attentionQueue.ts (full — pushItem at 83-88 is the mirror for resolveAttentionItem; the permission id format `permission:${ev.id}` at line 159; __resetAttentionQueue at 348)
    - apps/voss-app/src/pane/ProtocolPane.tsx (Plan 03 — the permission.updated placeholder row you upgrade to a live gate; the local transcript signal; the client/session the gate needs — thread a `client: VossClient` prop into ProtocolPane if Plan 03 did not already)
    - sdk/typescript/src/client/permission.ts (replyPermission signature + PermissionChoice)
    - .planning/phases/V15-live-plane-integration/V15-UI-SPEC.md §3 (gate markup, button order, resolved states, tab order, disabled-on-inflight)
    - apps/voss-app/src/org/attention/__tests__/attentionQueue.test.tsx (the existing queue test structure to extend)
    - .planning/phases/V15-live-plane-integration/V15-PATTERNS.md (Permission Reply + Dual-Surface Clear pattern; the `permission:${id}` load-bearing note)
  </read_first>
  <action>
    Add to `attentionQueue.ts`: `export function resolveAttentionItem(id: string): void { setAttentionQueue((prev) => prev.filter((item) => item.id !== id)); }` (immutable filter — mirror pushItem's spread discipline; no produce/structuredClone).

    In `ProtocolPane.tsx`, upgrade the permission.updated row from the Plan-03 placeholder to a live `.proto-permission-gate`. The pane needs the SDK client + sessionId to reply — ensure ProtocolPane receives a `client: VossClient` prop (add it to the props interface and thread it from PaneComponent/App via the native-session record; if Plan 03 did not include `client` on the native record, extend the record to carry it). Render the three `.proto-pgbtn` buttons (Deny/Allow once/Allow for {scope}) in tab order; derive the scope label from a path in `args` else "session". A local `gateState` per permission id tracks `'pending' | 'inflight' | 'resolved'` and the resolved choice. On click: set inflight (buttons `disabled`), `await replyPermission(props.client, props.sessionId, { id: ev.id, choice })`; on success set resolved + call `resolveAttentionItem(\`permission:${ev.id}\`)` (the prefix is load-bearing — T-V15-11); on throw, revert to pending (buttons re-enable). The gate row is pinned (already excluded from the D-08 trim in Plan 03). Render the resolved `.proto-permission-gate--resolved` label per choice. All text via escaped bindings (T-V15-05).

    Fill the `.proto-permission-gate` CSS skeleton from Plan 03 with the UI-SPEC §3 styles (color-mix accent-red border/bg, .proto-pgbtn variants incl. --deny/--allow-scope, :focus-visible outline, :disabled opacity, --resolved state) using tokens only, radius 0.

    Tests: extend `attentionQueue.test.tsx` to assert `resolveAttentionItem('permission:abc')` removes only that row. Extend `ProtocolPane.test.tsx`: inject a permission.updated event; assert the inline `.proto-permission-gate` renders AND `ingestEvent` produced a queue row; click Allow once with a mocked `replyPermission` resolving; assert one `replyPermission` call with `{id, choice:'a'}`, the gate shows `--resolved` "allowed once", and the queue row is gone; separately assert a rejecting `replyPermission` re-enables the buttons and keeps the queue row.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/org/attention/__tests__/attentionQueue.test.tsx src/pane/__tests__/ProtocolPane.test.tsx 2>&1 | tail -18</automated>
  </verify>
  <acceptance_criteria>
    - `attentionQueue.ts` exports `resolveAttentionItem`; the test proves single-row removal by prefixed id
    - `ProtocolPane.tsx` calls `replyPermission(` and `resolveAttentionItem(` with the `permission:${id}` prefix (grep both)
    - `ProtocolPane.test.tsx`: Allow once → one replyPermission call `{choice:'a'}` → gate `--resolved` + queue row removed; reject → buttons re-enabled, row retained
    - The reply clears BOTH surfaces only AFTER the POST resolves (no optimistic grant) — T-V15-07
    - No `innerHTML`/`produce(`/`structuredClone(` added (grep, comment-filtered, 0)
    - `npx --no vitest run src/org/attention/__tests__/attentionQueue.test.tsx src/pane/__tests__/ProtocolPane.test.tsx` exits 0
  </acceptance_criteria>
  <done>One permission event yields a live inline gate + a queue row; one reply (d/a/A) POSTs once and clears both surfaces; a failed POST leaves both pending.</done>
</task>

<task type="auto">
  <name>Task 2: Boot / spawn-failure / server-death lifecycle states (D-10/D-11/D-12)</name>
  <files>apps/voss-app/src/pane/ProtocolPane.tsx, apps/voss-app/src/pane/ProtocolPane.css, apps/voss-app/src/pane/ExitBanner.tsx, apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx</files>
  <read_first>
    - apps/voss-app/src/pane/ProtocolPane.tsx (the bootState signal from Plan 03 — 'booting'|'live'|'ended'|'error'; the connectLiveStream finally that sets ended; where to branch boot vs transcript)
    - apps/voss-app/src/pane/ExitBanner.tsx (full — the props you extend with message?/showRestart?)
    - .planning/phases/V15-live-plane-integration/V15-UI-SPEC.md §4 Boot, §5 Spawn-failure, §6 Ended (exact copy strings, the no-restart server-death rule, .pane--proto-ended dim + reduced-motion)
    - apps/voss-app/src/org/live/sidecarClient.ts (startVossServe — the Retry button re-invokes it; spawn failure surfaces the Err string which carries the stderr tail from sidecar.rs)
    - .planning/phases/V15-live-plane-integration/V15-PATTERNS.md (ExitBanner reuse for D-11; error-state Show guard pattern)
  </read_first>
  <action>
    Extend `ExitBanner.tsx`: add optional `message?: string` (defaults to the existing `[exited {code}]`) and `showRestart?: boolean` (defaults true; when false the Restart button is not rendered). Keep all existing behavior identical when the new props are absent (PTY panes unaffected).

    In `ProtocolPane.tsx`, render by `bootState()`:
    - `'booting'` (D-10): show `.proto-boot` with "Starting…", an elapsed counter that ticks each second from mount (use a setInterval cleared in onCleanup; the counter is DOM text, not a CSS animation — reduced-motion safe), and the "Cold start takes up to 60s" sub-line only after 5s elapsed. Transition to the transcript when the first event arrives (set bootState 'live' on first onEvent).
    - `'error'` (D-12): when `startVossServe`/stream setup fails, show `.proto-spawn-error` with the heading "Could not start — {one-line reason}", the stderr tail (from the Err string) in `.proto-spawn-error__stderr` (text binding — T-V15-05), and a "Retry start" button that re-invokes `startVossServe(cwd)` and resets bootState to 'booting'. (ProtocolPane needs the cwd to retry — thread it from the native record or accept an `onRetry` callback prop that App provides via the openAttachedPane/native-run seam.)
    - `'ended'` (D-11): when the stream ends due to server death (the connectLiveStream finally with no clean `final`/`session.idle` already seen), append an inline `<ExitBanner message="[session ended]" showRestart={false} exitCode={1} />` into the transcript flow (NOT position:absolute), add `.pane--proto-ended` (opacity .75; reduced-motion: no transition) to the pane, set the module `liveLabel` to 'snapshot' for this session (its handle aborts), and signal follow-up disabled-with-reason "Server unavailable — start a new run to continue" (call props.onEnded so App/CardDrawer reflect it). Distinguish clean idle (`session.idle`/`final` → exitCode 0, "[session ended]" still, but this is the normal end) from death — both show the ended row; death additionally flips write affordances. No auto-restart watchdog: the NEXT native run respawns fresh (Plan 02/03 path already does — nothing to add here).

    Fill the `.proto-boot`, `.proto-spawn-error`, `.proto-ended-row`, `.pane--proto-ended` CSS from the Plan-03 skeleton per UI-SPEC §4-6 (tokens only, radius 0, mono tabular elapsed counter, reduced-motion no-transition for the dim).

    Tests (extend ProtocolPane.test.tsx): assert the boot placeholder renders "Starting…" before any event and the transcript replaces it after the first event; simulate a spawn error (inject a failing setup) → `.proto-spawn-error` with the stderr text + a Retry button that calls startVossServe again; simulate server death (stream ends without final/idle) → an ExitBanner with "[session ended]" and NO Restart button, `.pane--proto-ended` applied, and onEnded fired.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/pane/__tests__/ 2>&1 | tail -14 && npx --no tsc --noEmit 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `ExitBanner.tsx` accepts `message?` and `showRestart?`; absent → byte-identical behavior (PTY ExitBanner test still green)
    - `ProtocolPane.tsx` renders `.proto-boot` "Starting…" + elapsed when booting, `.proto-spawn-error` with stderr tail + "Retry start" on error, and an inline `<ExitBanner ... showRestart={false}>` "[session ended]" + `.pane--proto-ended` on death
    - The "Retry start" button calls `startVossServe(` (grep)
    - Server-death path sets liveLabel 'snapshot' and fires onEnded (follow-up disabled-with-reason "Server unavailable — start a new run to continue")
    - Forbidden copy terms absent from the new strings (grep ProtocolPane.tsx for: cage, Voss-native, PermissionGate, session-tree → 0)
    - Full pane suite green: `npx --no vitest run src/pane/__tests__/` exits 0; `tsc --noEmit` no new errors
  </acceptance_criteria>
  <done>Cold start, spawn failure (with stderr + retry), and server death (ended banner, dim, snapshot, disabled follow-up) all render truthfully; no auto-restart; next run respawns via the existing path.</done>
</task>

</tasks>

<verification>
- `cd apps/voss-app && npx --no vitest run src/pane/__tests__/ src/org/attention/__tests__/attentionQueue.test.tsx` exits 0
- `npx --no tsc --noEmit` no new errors vs. baseline
- grep: `replyPermission` + `resolveAttentionItem('permission:` in ProtocolPane; `resolveAttentionItem` exported from attentionQueue; `showRestart` in ExitBanner
- grep: forbidden copy terms absent from ProtocolPane new strings
</verification>

<success_criteria>
- Permission event → inline gate + queue row; one reply (d/a/A → POST /permission) clears both; failed POST leaves both pending (VLIVE-05, T-V15-07/T-V15-11)
- Cold start placeholder (60s budget), spawn-failure stderr + retry, honest server-death degrade with disabled follow-up; next run respawns (VLIVE-07)
- ExitBanner reuse is backward-compatible; PTY panes unaffected
- All rendered server/process text is escaped (T-V15-05)
</success_criteria>

<output>
Create `.planning/phases/V15-live-plane-integration/V15-04-SUMMARY.md` when done
</output>
