import { createSignal } from 'solid-js';

export interface BridgeMaps {
  cardToPane: Record<string, string>; // terminal agents (client-minted)
  cardToSessionNode: Record<string, string>; // native runs (harness sessionID) + snapshot node ids
}

export function resolveCard(
  maps: BridgeMaps,
  cardId: string,
): { paneId?: string; sessionNodeId?: string } {
  return {
    paneId: maps.cardToPane[cardId],
    sessionNodeId: maps.cardToSessionNode[cardId] ?? cardId, // snapshot: card id === node id
  };
}

export function resolvePane(
  maps: BridgeMaps,
  paneId: string,
): string | undefined {
  for (const cardId in maps.cardToPane) {
    if (maps.cardToPane[cardId] === paneId) return cardId;
  }
  return undefined;
}

const [cardToPane, setCardToPane] = createSignal<Record<string, string>>({});
const [cardToSessionNode, setCardToSessionNode] = createSignal<
  Record<string, string>
>({});

export function registerTerminalCard(paneId: string): string {
  const cardId = crypto.randomUUID();
  setCardToPane((prev) => ({ ...prev, [cardId]: paneId }));
  return cardId;
}

export function registerNativeCard(cardId: string, sessionID: string): void {
  setCardToSessionNode((prev) => ({ ...prev, [cardId]: sessionID }));
}

export function paneIdForCard(cardId: string): string | undefined {
  return cardToPane()[cardId];
}

export { cardToPane, cardToSessionNode };

export function __resetBridgeMaps(): void {
  setCardToPane({});
  setCardToSessionNode({});
}
