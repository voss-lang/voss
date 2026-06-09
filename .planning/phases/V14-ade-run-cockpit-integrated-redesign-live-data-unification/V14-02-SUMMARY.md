---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 02
type: summary
wave: 2
status: complete
depends_on: ["V14-00", "V14-01"]
requirements: [VCKP-02]
---

# V14-02 Summary — VCKP-02 id-Bridge Keystone

Status: **COMPLETE**. Keystone resolves card↔pane↔node both ways. `src/org`: 67 passed | 4 todo | 0 fail. tsc clean. bridge.ts pure (signal-backed maps, no produce/structuredClone).

## Artifacts

- `src/org/model/bridge.ts` — pure resolvers + signal-backed maps + two register mechanisms:
  - `interface BridgeMaps { cardToPane; cardToSessionNode }` (Record<string,string> each).
  - `resolveCard(maps, cardId)` → `{ paneId: cardToPane[cardId], sessionNodeId: cardToSessionNode[cardId] ?? cardId }` (verbatim RESEARCH; `?? cardId` = snapshot card id IS node id, click-fallback without throw).
  - `resolvePane(maps, paneId)` → reverse lookup, cardId or undefined.
  - Module-level signals `cardToPane`/`cardToSessionNode` = `createSignal<Record<string,string>>({})`, immutable-spread setters (mirror budgetRegistry; NO produce — Pitfall 5).
  - `registerTerminalCard(paneId): string` — **Bridge B**: mints `crypto.randomUUID()` cardId, stores cardToPane[cardId]=paneId, returns cardId (caller passes as spawn_agent sessionId arg; zero Rust change).
  - `registerNativeCard(cardId, sessionID)` — **Bridge A**: stores cardToSessionNode[cardId]=sessionID DIRECTLY per A1 finding (native create-response id === node id, no second lookup).
  - `paneIdForCard(cardId): string | undefined` — reads live cardToPane signal; satisfies the `CardBridge` interface plan-01 buildModel consumes (verified vs adapters.ts).
  - `__resetBridgeMaps()` — test-only reset (global signals); setters not public.
- `src/org/model/__tests__/bridge.test.ts` — flipped 4 it.todo → active; 8 tests pass. Covers: fixture binding {paneId:'P1',sessionNodeId:'N1'}; empty cardToSessionNode → sessionNodeId===cardId; neither-map → {undefined, cardId} no throw; registerTerminalCard UUID+map; registerNativeCard A1 store; two-mechanism separation (native sessionID never appears as pane key). afterEach calls __resetBridgeMaps.

## Decisions

- **Pitfall 1 honored:** registry.session_id NEVER joined to SessionTreeNode.id. Bridge A keys on create-response id; Bridge B keys on client-minted cardId. Maps never cross. Dedicated test asserts a native sessionID is not resolvable as a pane.
- **buildModel wiring:** plan-01 buildModel takes a `{paneIdForCard}` param (no ../bridge import = no wave dep). At cockpit wire-up (later wave), pass `{ paneIdForCard }` from this module into buildModel.
- Purity grep hits are header-comment only; sole solid-js import is `createSignal`.

## Verification
- `npx vitest run src/org/model/__tests__/bridge.test.ts` → 8 passed.
- `npx vitest run src/org` → 13 files passed; 67 passed | 4 todo | 0 fail (remaining todos = adapters/sseClient downstream, not bridge).
- `npx tsc --noEmit` → clean.
- bridge.ts pure: no produce/structuredClone calls, signal-backed immutable maps.
