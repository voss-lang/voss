---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 06
type: summary
wave: 4
status: complete
depends_on: ["V14-04", "V14-05"]
requirements: [VCKP-06]
---

# V14-06 Summary — VCKP-06 SSE Consumer + live/snapshot label (GATED, best-effort)

Status: **COMPLETE**. src/org/live + src/org/cockpit: 14 passed. src/org: 85 passed. tsc clean. Phase NOT blocked — no-stream degrades to snapshot.

## Artifacts

Task 1 (consumer):
- `src/org/live/sseClient.ts` — first org-view SSE consumer.
  - `connectLiveStream({baseUrl, sessionId, token, stream?}): { abort() }` — consumes `subscribeToEvents` (SDK, Bearer header) by default OR an injected `stream` async-iterable (test/mock). `for await` routes each event → `ingestEvent(ev)` (attention queue) + `applyOverlay(ev)` (live overlay). AbortController teardown; try/catch/finally resets liveLabel→'snapshot' on end/abort/error (never throws).
  - `liveLabel` — module-level `createSignal<'live'|'snapshot'>('snapshot')`, exported Accessor. 'live' while connected, 'snapshot' default.
  - `liveOverlay` — module-level session-keyed `createSignal<Record<string,LiveOverlayEntry>>({})` (budget/status/confidence/gate per session; immutable spread, mirror budgetRegistry). NEW signal because SSE plane is session-keyed vs budgetRegistry pane-keyed.
  - `__resetLiveStream()` test reset.
  - NO raw EventSource. NO node:child_process/launcher (Pitfall 4 — webview consume-only).
- `src/org/live/__tests__/sseClient.test.ts` — plan-00 placeholder flipped active; 5 tests: mock stream→overlay+queue+liveLabel 'live'; no-stream→'snapshot' no throw; budget.updated overlay no manual refresh; AbortController clean teardown + label reset.

Task 2 (surface):
- `src/org/cockpit/CockpitShell.tsx` — `.cockpit-live-label` in header after Refresh button, bound to liveLabel(): "● live" vs "snapshot", aria-label "Data source: <state>". Refresh affordance stays visible (snapshot fallback). NO auto stream start (no handshake in V14) → default 'snapshot'.
- `src/org/cockpit/cockpitStyles.css` — `.cockpit-live-label` (var(--font-mono), 10px uppercase), --snapshot (--fg-3), --live (--accent-green). No new --xxx.
- `src/org/cockpit/__tests__/cockpit.test.tsx` — added assertion: label renders 'snapshot' by default.

## Decisions / notes for downstream

- **Session correlation:** `sessionKeyOf(ev)` reads `ev.sessionID` first (mock/PROTOCOL §6 correlation key), falls back to `ev.session_id` (raw SDK snake_case). Type-specific fields read only AFTER narrowing by `ev.type`. permission.updated has neither key → overlay skipped (still routes to queue via ingestEvent, which uses ingest-context cardId).
- **Test routing assertion nuance:** mock budget.updated (spent 1200 < limit 10000) does NOT create an attention item (ingestEvent enqueues budget only on threshold crossing spent>=limit). So queue-routing asserted via the gate.updated item; budget update asserted via liveOverlay. Both prove no-manual-refresh routing.
- **No auto-connect in V14:** real {port,token} handshake deferred (V13.1 server gated). Cockpit default = snapshot; label flips to 'live' only when connectLiveStream is called (mock today, real server later). When the handshake lands, wire connectLiveStream into CockpitShell onMount guarded by handshake availability.
- **liveOverlay not yet consumed by board/cards:** sseClient writes the session-keyed overlay, but wiring it into buildModel's card.liveBudget/liveStatus (plan-01 overlay fields) is a future step — current test asserts the overlay signal updates, not the rendered card. Flag for a later wave if live card values must visibly update.

## Verification
- `npx vitest run src/org/live/__tests__/sseClient.test.ts` → 5 passed.
- `npx vitest run src/org/live src/org/cockpit` → 14 passed.
- `npx vitest run src/org` → 85 passed.
- `npx tsc --noEmit` → clean.
- Guards: no raw EventSource, no node launcher import, subscribeToEvents imported from SDK.
