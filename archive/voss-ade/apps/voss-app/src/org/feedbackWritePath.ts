import { resolveCard, cardToPane, cardToSessionNode } from './model/bridge';

export interface FollowUpClient {
  postMessage(sessionId: string, text: string): Promise<unknown>;
}

export type FollowUpResult =
  | { disabled: true; reason: string }
  | { disabled: false; sessionNodeId: string };

export const FOLLOWUP_DISABLED_REASON =
  'Comments need a running Voss session. This card comes from a saved run — nothing is live to receive a reply.';

export function nativeSessionNodeId(cardId: string): string | undefined {
  const registered = cardId in cardToSessionNode();
  if (!registered) return undefined;
  return resolveCard(
    { cardToPane: cardToPane(), cardToSessionNode: cardToSessionNode() },
    cardId,
  ).sessionNodeId;
}

export async function dispatchFollowUp(input: {
  cardId: string;
  comment: string;
  client: FollowUpClient | undefined;
  hasNativePath: boolean;
}): Promise<FollowUpResult> {
  const sessionNodeId = nativeSessionNodeId(input.cardId);
  if (!input.hasNativePath || !input.client || !sessionNodeId) {
    return { disabled: true, reason: FOLLOWUP_DISABLED_REASON };
  }
  await input.client.postMessage(sessionNodeId, input.comment);
  return { disabled: false, sessionNodeId };
}
