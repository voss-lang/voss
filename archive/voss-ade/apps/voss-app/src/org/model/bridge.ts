import { createSignal } from 'solid-js';

export interface BridgeMaps {
  cardToPane: Record<string, string>; // terminal agents (client-minted)
  cardToSessionNode: Record<string, string>; // native runs (harness sessionID) + snapshot node ids
}

/**
 * Pure resolver: card id -> { paneId?, sessionNodeId? }
 * `sessionNodeId` falls back to `cardId` because for snapshot/native cards the
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
 * Pure reverse resolver: pane id -> cardId (the card whose cardToPane === paneId)
 * or undefined if no card is bound to that pane
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

// immutable spread update, NO produce/structuredClone). ---

const [cardToPane, setCardToPane] = createSignal<Record<string, string>>({});
const [cardToSessionNode, setCardToSessionNode] = createSignal<
  Record<string, string>
>({});

/**
 * Bridge B: bind a cockpit-launched terminal agent to its pane. Mints a
 * client-side cardId, stores cardToPane[cardId]=paneId, and returns the cardId
 */
export function registerTerminalCard(paneId: string): string {
  const cardId = crypto.randomUUID();
  setCardToPane((prev) => ({ ...prev, [cardId]: paneId }));
  return cardId;
}

/**
 * Bridge A: bind a native run's card to its session node. Per the A1 finding
 * the create-response `sessionID` IS the snapshot node id, so it is stored
 */
export function registerNativeCard(cardId: string, sessionID: string): void {
  setCardToSessionNode((prev) => ({ ...prev, [cardId]: sessionID }));
}

/**
 * The card->pane resolver interface 's `buildModel` consumes
 * (CardBridge.paneIdForCard). Reads the live cardToPane signal
 */
export function paneIdForCard(cardId: string): string | undefined {
  return cardToPane()[cardId];
}

export { cardToPane, cardToSessionNode };

/**
 * Test-only reset: clears both live maps back to {}. The module signals are
 * global, so tests call this in afterEach to prevent register* state leakage
 */
export function __resetBridgeMaps(): void {
  setCardToPane({});
  setCardToSessionNode({});
}
