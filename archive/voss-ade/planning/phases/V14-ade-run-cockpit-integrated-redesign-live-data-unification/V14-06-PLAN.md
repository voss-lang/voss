---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 06
type: execute
wave: 4
depends_on: ["V14-04", "V14-05"]
files_modified:
  - apps/voss-app/src/org/live/sseClient.ts
  - apps/voss-app/src/org/live/__tests__/sseClient.test.ts
  - apps/voss-app/src/org/cockpit/CockpitShell.tsx
autonomous: true
requirements: [VCKP-06]
must_haves:
  truths:
    - "A fixture/mock SSE stream drives a board+budget update in the cockpit with no manual refresh (test-verifiable now)"
    - "The UI renders a visible live-vs-snapshot state label: live under the mock stream, snapshot without one"
    - "GATED graceful-degrade: when no live server/stream is available, the cockpit falls back to snapshot + manual refresh and labels itself snapshot — never blocks the phase"
    - "The consumer reuses V13.1 subscribeToEvents (never raw EventSource — can't set the Bearer header); the webview never tries to start voss serve (Node-only launcher, Pitfall 4)"
  artifacts:
    - path: "apps/voss-app/src/org/live/sseClient.ts"
      provides: "SSE consumer wrapper + feature-detect + live/snapshot label signal"
      contains: "subscribeToEvents"
    - path: "apps/voss-app/src/org/live/__tests__/sseClient.test.ts"
      provides: "VCKP-06 mock-stream test"
  key_links:
    - from: "apps/voss-app/src/org/live/sseClient.ts"
      to: "apps/voss-app/src/org/attention/attentionQueue.ts"
      via: "route SSE events into the queue + model overlay by sessionID"
      pattern: "ingestEvent"
---

<objective>
VCKP-06 (GATED on V13.1, best-effort): consume the V13.1 SSE event union to drive live board/budget/confidence/gate updates in the cockpit, with a visible `live`/`snapshot` label and graceful snapshot fallback. Verified now via a mock stream (real `voss serve` deferred). This plan must NOT block the phase — absence of a live server degrades to snapshot.

Purpose: Close G5 (snapshot-only org view). First SSE consumer in the org view.
Output: sseClient wrapper (consumes `subscribeToEvents`, feature-detects, exposes a live/snapshot label signal), mock-stream test, wiring into CockpitShell.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-SPEC.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md

<interfaces>
From sdk/typescript/src/client/sse.ts: `subscribeToEvents(baseUrl, sessionId, token, signal): AsyncIterable<AgentEvent>` (async-generator, sets `Authorization: Bearer ${token}`). Consume verbatim — never raw EventSource.
From apps/voss-app/src/org/live/__tests__/mockSseStream.ts (plan 00): scripted async-generator of AgentEvents with sessionID.
From apps/voss-app/src/org/attention/attentionQueue.ts (plan 05): `ingestEvent(ev)`.
From apps/voss-app/src/org/model/adapters.ts (plan 01): the model overlay that live budget/status updates feed.
Pitfall 4: the V13.1 launcher imports node:child_process (Node-only) — the webview CANNOT start `voss serve`; it only consumes. Mock the stream in V14.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: sseClient wrapper + live/snapshot label + mock-stream test</name>
  <files>apps/voss-app/src/org/live/sseClient.ts, apps/voss-app/src/org/live/__tests__/sseClient.test.ts</files>
  <behavior>
    - Given the mockSseStream (budget.updated + gate.updated), connectLiveStream routes each event by sessionID into ingestEvent + the model overlay, and sets the liveLabel signal to 'live'.
    - With no stream/connection, liveLabel is 'snapshot' (default) and the cockpit uses the snapshot fallback (no throw).
    - A budget.updated event for the selected run updates the board/budget overlay without any manual refresh call.
    - AbortController stops the stream cleanly (no dangling generator).
  </behavior>
  <read_first>
    - sdk/typescript/src/client/sse.ts (subscribeToEvents — consume verbatim; Bearer header)
    - apps/voss-app/src/org/live/__tests__/mockSseStream.ts (plan 00 mock helper)
    - apps/voss-app/src/org/attention/attentionQueue.ts (ingestEvent from plan 05)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (sseClient pattern: consume-don't-reimplement, Pitfall 4, live/snapshot label)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md (Pattern 3 SSE consume + fallback)
  </read_first>
  <action>
    Create `sseClient.ts`: a `connectLiveStream({baseUrl, sessionId, token, stream?})` that consumes `subscribeToEvents` (or an injected `stream` async-iterable for tests/mock) inside `for await`, routing each event by `ev.sessionID` into `ingestEvent` (attention queue) and the model overlay (budget/status/confidence/gate). Expose a module-level `createSignal<'live'|'snapshot'>('snapshot')` `liveLabel` set to `'live'` while a stream is active for the selected run and reset to `'snapshot'` on end/abort/absence. Use an `AbortController` for teardown. NEVER raw EventSource (Bearer header). NEVER import the Node-only launcher (Pitfall 4) — the webview only consumes. Flip the plan-00 `sseClient.test.ts` skips to active and cover the four behaviors using `mockSseStream`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/live/__tests__/sseClient.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - Driving `mockSseStream` updates the board/budget overlay with no manual refresh and sets `liveLabel` to `'live'`.
    - With no stream, `liveLabel` is `'snapshot'` and no error is thrown.
    - `sseClient.ts` imports `subscribeToEvents` from the SDK (grep) and imports NO `node:child_process`/launcher.
    - AbortController teardown leaves no dangling stream.
  </acceptance_criteria>
  <done>Mock SSE drives live updates + label; snapshot fallback graceful; consumer-only (Pitfall 4 honored).</done>
</task>

<task type="auto">
  <name>Task 2: Render live/snapshot label in the cockpit (graceful-degrade)</name>
  <files>apps/voss-app/src/org/cockpit/CockpitShell.tsx</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (plan 03 — where the label renders)
    - apps/voss-app/src/org/live/sseClient.ts (task 1 — liveLabel signal)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-SPEC.md (VCKP-06 best-effort / graceful-degrade acceptance)
  </read_first>
  <action>
    In `CockpitShell.tsx`, render a small live/snapshot state label bound to the `liveLabel` signal (A12 tokens, monospace). When `liveLabel()==='snapshot'` keep the existing manual-refresh affordance visible (snapshot fallback). Do not start any stream automatically unless a `{port,token}` handshake is already available (it is not in V14 — so the default render is `snapshot`; the label only flips to `live` when a stream is connected, e.g. via the mock in tests). This keeps the phase unblocked when V13.1 / a real server is absent.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/cockpit/__tests__/cockpit.test.tsx && npx tsc --noEmit 2>&1 | grep -E "Cockpit|sseClient" || echo "clean"</automated>
  </verify>
  <acceptance_criteria>
    - The cockpit renders a `live`/`snapshot` label bound to `liveLabel`; default is `snapshot`.
    - Snapshot mode keeps the manual-refresh affordance; no automatic stream start without a handshake.
    - `cockpit.test.tsx` stays green.
  </acceptance_criteria>
  <done>Live/snapshot label renders; graceful-degrade to snapshot when no server; phase not blocked.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org/live src/org/cockpit` green; `npx tsc --noEmit` clean.
- Mock stream drives updates + `live` label; no-stream defaults to `snapshot`.
- No raw EventSource, no Node-only launcher import (Pitfall 4).
- V11 tests unregressed.
</verification>

<success_criteria>
A mock SSE stream drives live board/budget updates with no manual refresh and a visible `live` label; absence of a server degrades gracefully to `snapshot` without blocking the phase.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-06-SUMMARY.md` when done.
</output>
