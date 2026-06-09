---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 00
type: summary
wave: 0
status: complete
requirements: [VCKP-01, VCKP-02, VCKP-06]
---

# V14-00 Summary — Wave 0 Scaffold

Status: **COMPLETE**. All 3 tasks green. `src/org` suite: 51 passed | 14 todo | 0 fail. `tsc --noEmit` clean for all new files.

## A1 KEYSTONE FINDING (gates plan 02 — read verbatim)

> A1 RESOLVED (verified against a real .voss/sessions tree): for a native run the create-response id (harness sessionID = uuid4().hex[:12], 12-hex) IS the snapshot node id (SessionTreeNode.id = the .voss/sessions/<id>.json filename stem, which equals the record JSON `id`). create-response-id === node-id, so Bridge A stores the create-response id DIRECTLY into cardToSessionNode — NO second lookup is needed for the single-node native case. (The app-minted agent_registry.session_id is a separate namespace and does NOT join; that is Bridge B / cardId↔paneId.) resolveCard's `cardToSessionNode[cardId] ?? cardId` fallback covers any future multi-node run-dir divergence without a silent mis-bind.

**Plan 02 gate decision:** Bridge A applies — store native create-response id directly into `cardToSessionNode`, no second lookup. Terminal-agent runs use Bridge B (client-side `cardId↔paneId`). Verified against a REAL `.voss/sessions` tree (12 records at repo root; flat `<id>.json`, every stem 12-hex, in-file `id` === stem). Not fixture-only.

Downstream note (non-blocking): real on-disk records are V4 flat session files with nested `runs[]`; one record nested a run with a distinct 12-hex id. If a future multi-run/multi-node directory layout appears, the `?? cardId` fallback in `resolveCard` surfaces divergence as a failing fixture, not a silent mis-bind.

## Artifacts created

Task 1 (types):
- `src/org/model/normalized.ts` — pure type module. Exports Run, Card, Agent, SessionNode, Evidence, Decision, CapabilityTier ('A'|'B'|'C'). Card has optional paneId/sessionNodeId/liveBudget/liveStatus overlay. Imports RunData/SessionTreeNode from ../types. No Solid imports. types.ts/guards.ts untouched (D-02 intact).
- `src/org/selection.ts` — module-level Solid signals: selectedCardId/setSelectedCardId, selectedRunId/setSelectedRunId. Mirrors orgStore.ts.

Task 2 (keystone + fixtures):
- `src/org/__tests__/fixtures/live-registry.json` — AgentEntry[] (camelCase), native agent on pane P1 with 12-hex sessionId `0139377ff590`; contrasting terminal-CLI agent on P2 (non-hex id, Bridge B).
- `src/org/__tests__/fixtures/bridge-binding.json` — cardToPane.C1="P1", cardToSessionNode.C1="N1", expected{cardId:C1,paneId:P1,sessionNodeId:N1}.
- `src/org/__tests__/keystone-a1.test.ts` — 7 passing tests. Globs real .voss/sessions, asserts 12-hex sessionID format, record id === filename stem, create-response-id === node-id. Exports A1_FINDING constant.

Task 3 (mock SSE + red tests):
- `src/org/live/__tests__/mockSseStream.ts` — async-generator yielding MockAgentEvent (AgentEvent & {sessionID}): a budget.updated + a gate.updated, each with sessionID.
- `src/org/model/__tests__/adapters.test.ts` — VCKP-01, 6 named it.todo, targets ../adapters (buildModel).
- `src/org/model/__tests__/bridge.test.ts` — VCKP-02, 1 active fixture test + 4 it.todo, targets ../bridge (resolveCard).
- `src/org/live/__tests__/sseClient.test.ts` — VCKP-06, 1 active mock-stream test + 4 it.todo, targets ../../live/sseClient.

## Notes for downstream plans

- **SDK type path:** `@vosslang/sdk` is NOT a voss-app dependency and no tsconfig alias exists. AgentEvent imported type-only via relative path `../../../../../../sdk/typescript/src/client/sse`. Type-only erases at runtime; tsc resolves under bundler + skipLibCheck.
- **sessionID vs session_id (load-bearing):** PLAN/PROTOCOL say events carry `sessionID`; the SDK's generated AgentEvent union actually uses `session_id` (snake_case) on BudgetUpdated/GateUpdated. mockSseStream yields `AgentEvent & {sessionID}` — both keys present. sseClient/adapter code must narrow by event `type` before reading `session_id`; use `sessionID` as the correlation key.
- No false-green: every unbuilt-module assertion is it.todo (no body, no collection-time import). Downstream plans flip todo→active.

## Verification
- `npx vitest run src/org` → 11 passed | 1 skipped files; 51 passed | 14 todo tests; 0 fail.
- `npx tsc --noEmit` → no errors in V14-00 files.
- D-02 / V11 panel tests + guards.test.ts unregressed.
