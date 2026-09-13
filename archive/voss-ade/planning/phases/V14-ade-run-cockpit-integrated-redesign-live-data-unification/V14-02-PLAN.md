---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 02
type: execute
wave: 2
depends_on: ["V14-00", "V14-01"]
files_modified:
  - apps/voss-app/src/org/model/bridge.ts
  - apps/voss-app/src/org/model/__tests__/bridge.test.ts
autonomous: true
requirements: [VCKP-02]
must_haves:
  truths:
    - "With a fixture binding card C1 to pane P1 and node N1, resolveCard('C1') returns {paneId:'P1', sessionNodeId:'N1'}"
    - "A click handler test focuses pane P1 for a card bound to a live pane"
    - "A card with no live pane falls back to detail-open without error"
    - "The bridge follows the two-mechanism design: native runs store the create-response id into cardToSessionNode; terminal agents mint a client-side cardId passed as the spawn_agent sessionId arg, stored as cardToPane (zero Rust change)"
    - "registry.session_id is never directly joined to SessionTreeNode.id (Pitfall 1)"
  artifacts:
    - path: "apps/voss-app/src/org/model/bridge.ts"
      provides: "id-bridge: cardToPane/cardToSessionNode maps + resolveCard/resolvePane"
      contains: "export function resolveCard"
    - path: "apps/voss-app/src/org/model/__tests__/bridge.test.ts"
      provides: "VCKP-02 keystone test"
  key_links:
    - from: "apps/voss-app/src/org/model/bridge.ts"
      to: "apps/voss-app/src/pane/budgetRegistry.ts"
      via: "module-level signal-map + immutable update pattern"
      pattern: "createSignal<Record"
---

<objective>
VCKP-02 keystone: the id-bridge. A pure `resolveCard(maps, cardId) → {paneId?, sessionNodeId?}` resolver plus a signal-backed `cardToPane` map (terminal agents, client-minted) and `cardToSessionNode` map (native runs from the create-response, + snapshot node ids). This is the make-or-break correlation between the live plane (pane) and the snapshot plane (session node). The A1 finding from plan 00 dictates whether the native create-response id stores directly or needs a second lookup.

Purpose: Make every board card resolvable to its live pane and/or session node (G1/G2). Keystone — has an automated check (per validation contract).
Output: `bridge.ts` (pure resolver + signal maps), `bridge.test.ts` (green per acceptance).
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
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-00-SUMMARY.md

<interfaces>
From RESEARCH Code Examples (copy verbatim as the contract):
`export interface BridgeMaps { cardToPane: Record<string,string>; cardToSessionNode: Record<string,string>; }`
`export function resolveCard(maps: BridgeMaps, cardId: string): { paneId?: string; sessionNodeId?: string }` — returns `{ paneId: maps.cardToPane[cardId], sessionNodeId: maps.cardToSessionNode[cardId] ?? cardId }`.
From apps/voss-app/src/pane/budgetRegistry.ts:10-37: module-level `createSignal<Record<string,X>>({})` + immutable spread update (NO produce). Mirror for the signal-backed maps.
From apps/voss-app/src/pane/pty-ipc.ts:167-186: `spawnAgent({... sessionId, paneId ...})` → `invoke('spawn_agent', {sessionId, paneId})`. The `session_id` registry column already exists — pass `cardId` as `sessionId` for cockpit-bound terminal agents (Bridge B, zero Rust change).
A1_FINDING constant from plan 00 keystone-a1.test.ts — dictates native id storage.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: bridge.ts — resolveCard + signal-backed maps (two mechanisms)</name>
  <files>apps/voss-app/src/org/model/bridge.ts, apps/voss-app/src/org/model/__tests__/bridge.test.ts</files>
  <behavior>
    - resolveCard({cardToPane:{C1:'P1'}, cardToSessionNode:{C1:'N1'}}, 'C1') === {paneId:'P1', sessionNodeId:'N1'} (the canonical binding fixture).
    - resolveCard with an empty cardToSessionNode falls back to sessionNodeId === cardId (snapshot card id IS the node id).
    - A card present in neither map → {paneId: undefined, sessionNodeId: cardId} (no throw; click-fallback path).
    - registerTerminalCard(paneId) mints crypto.randomUUID() cardId, stores cardToPane[cardId]=paneId, returns cardId.
    - registerNativeCard(cardId, sessionID) stores cardToSessionNode[cardId]=sessionID per the A1 finding.
  </behavior>
  <read_first>
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-00-SUMMARY.md (A1_FINDING — governs native id storage)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md (Keystone section: two bridges, resolveCard contract, "What must be BUILT" items 2-4, "What must NOT be done")
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (bridge.ts pattern: resolveCard verbatim, signal-map storage, Bridge A/B conventions, Pitfall 1)
    - apps/voss-app/src/pane/budgetRegistry.ts:10-37 (signal-map + immutable update analog)
    - apps/voss-app/src/pane/pty-ipc.ts:167-186 (spawnAgent sessionId arg — Bridge B carrier)
    - apps/voss-app/src/org/__tests__/fixtures/bridge-binding.json (plan 00 — C1↔P1↔N1)
  </read_first>
  <action>
    Create `src/org/model/bridge.ts`. Export the pure `resolveCard(maps, cardId)` and `resolvePane(maps, paneId)` (reverse) functions verbatim from RESEARCH. Export module-level signals `cardToPane`/`cardToSessionNode` as `createSignal<Record<string,string>>({})` with immutable-spread setters (mirror budgetRegistry, NO produce — Pitfall 5). Export `registerTerminalCard(paneId): string` (mints `crypto.randomUUID()`, stores `cardToPane[cardId]=paneId`, returns the cardId to be passed as the `spawn_agent` `sessionId` arg — Bridge B), and `registerNativeCard(cardId, sessionID)` (stores `cardToSessionNode` per A1_FINDING — Bridge A). Provide a `paneIdForCard(cardId)` accessor (the resolver interface plan 01's `buildModel` consumes). NEVER join `registry.session_id` to `SessionTreeNode.id` directly (Pitfall 1). Flip the plan-00 `bridge.test.ts` skips to active and cover all five behaviors above, including the click-fallback (no-pane → sessionNode fallback without throw).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/model/__tests__/bridge.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - `resolveCard` returns `{paneId:'P1', sessionNodeId:'N1'}` for the binding fixture.
    - A no-pane card resolves to `{sessionNodeId: cardId}` without throwing (fallback path).
    - `registerTerminalCard` mints a UUID cardId and maps it to the pane; `registerNativeCard` stores per A1_FINDING.
    - `bridge.ts` uses no `produce`/`structuredClone`; maps are signal-backed with immutable updates.
    - Test asserts the two-mechanism separation (no direct registry.session_id↔node.id join).
  </acceptance_criteria>
  <done>The keystone resolves card↔pane↔node both ways; two mechanisms implemented; fixture test green.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org/model` green.
- `npx tsc --noEmit` clean.
- bridge.ts pure (no produce/structuredClone), signal-backed maps.
- Pitfall 1 honored: no direct session_id↔node id join.
</verification>

<success_criteria>
resolveCard returns {paneId,sessionNodeId} per the binding fixture; no-pane cards fall back without error; the two-bridge mechanism (native echo + terminal cardId-as-sessionId) is implemented with zero Rust change.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-02-SUMMARY.md` when done.
</output>
