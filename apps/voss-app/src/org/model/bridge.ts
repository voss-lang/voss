// V14 id-bridge keystone (VCKP-02). Correlates the live plane (pane) and the
// snapshot plane (session node) for every board card via two distinct
// mechanisms:
//
//   Bridge A — native runs: the harness create-response `id` (sessionID =
//     uuid4().hex[:12]) IS the snapshot node id (verified A1, V14-00). Store it
//     DIRECTLY into cardToSessionNode — no second lookup.
//   Bridge B — terminal agents: no harness session exists. Mint a client-side
//     cardId (crypto.randomUUID()), store cardToPane[cardId]=paneId, and pass
//     the cardId as the `spawn_agent` sessionId arg (zero Rust change; the
//     session_id column already exists).
//
// Pitfall 1: registry.session_id is a SEPARATE namespace and is NEVER joined to
// SessionTreeNode.id directly. Bridge A keys on the create-response id; Bridge B
// keys on the client-minted cardId. The two maps never cross.
//
// Pure resolveCard/resolvePane: no Solid imports inside them, no
// produce/structuredClone (Pitfall 5). Signal-backed maps mirror
// budgetRegistry.ts — module-level createSignal<Record> + immutable spread.

import { createSignal } from 'solid-js';

export interface BridgeMaps {
  cardToPane: Record<string, string>; // terminal agents (client-minted)
  cardToSessionNode: Record<string, string>; // native runs (harness sessionID) + snapshot node ids
}

/**
 * Pure resolver: card id -> { paneId?, sessionNodeId? }.
 *
 * `sessionNodeId` falls back to `cardId` because for snapshot/native cards the
 * card id IS the session node id (A1 finding). A card present in neither map
 * resolves to `{ paneId: undefined, sessionNodeId: cardId }` without throwing —
 * the click-fallback (detail-open) path.
 */
export function resolveCard(
  maps: BridgeMaps,
  cardId: string,
): { paneId?: string; sessionNodeId?: string } {
  return {
    paneId: maps.cardToPane[cardId],
    sessionNodeId: maps.cardToSessionNode[cardId] ?? cardId, // snapshot: card id === node id
  };
}

/**
 * Pure reverse resolver: pane id -> cardId (the card whose cardToPane === paneId),
 * or undefined if no card is bound to that pane.
 */
export function resolvePane(
  maps: BridgeMaps,
  paneId: string,
): string | undefined {
  for (const cardId in maps.cardToPane) {
    if (maps.cardToPane[cardId] === paneId) return cardId;
  }
  return undefined;
}

// --- Signal-backed live maps (mirror budgetRegistry.ts: module-level signal +
// immutable spread update, NO produce/structuredClone). ---

const [cardToPane, setCardToPane] = createSignal<Record<string, string>>({});
const [cardToSessionNode, setCardToSessionNode] = createSignal<
  Record<string, string>
>({});

/**
 * Bridge B: bind a cockpit-launched terminal agent to its pane. Mints a
 * client-side cardId, stores cardToPane[cardId]=paneId, and returns the cardId —
 * the caller passes it as the `spawn_agent` sessionId arg so the correlation
 * survives a registry round-trip (zero Rust change).
 */
export function registerTerminalCard(paneId: string): string {
  const cardId = crypto.randomUUID();
  setCardToPane((prev) => ({ ...prev, [cardId]: paneId }));
  return cardId;
}

/**
 * Bridge A: bind a native run's card to its session node. Per the A1 finding,
 * the create-response `sessionID` IS the snapshot node id, so it is stored
 * DIRECTLY into cardToSessionNode (no second lookup, no registry.session_id
 * join — Pitfall 1).
 */
export function registerNativeCard(cardId: string, sessionID: string): void {
  setCardToSessionNode((prev) => ({ ...prev, [cardId]: sessionID }));
}

/**
 * The card->pane resolver interface plan 01's `buildModel` consumes
 * (CardBridge.paneIdForCard). Reads the live cardToPane signal.
 */
export function paneIdForCard(cardId: string): string | undefined {
  return cardToPane()[cardId];
}

export { cardToPane, cardToSessionNode };

/**
 * Test-only reset: clears both live maps back to {}. The module signals are
 * global, so tests call this in afterEach to prevent register* state leakage.
 */
export function __resetBridgeMaps(): void {
  setCardToPane({});
  setCardToSessionNode({});
}
