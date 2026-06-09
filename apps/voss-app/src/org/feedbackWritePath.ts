// VCKP-09 (best-effort) — inline feedback write path.
//
// The ONLY follow-up write path in PROTOCOL v1 is `POST /session/:id/message`
// (§5) — NATIVE sessions only. A snapshot card has no running session, so the
// affordance must render disabled-with-reason (decisionActions.ts discipline:
// never a silent no-op, never a fake affordance).
//
// Pure aside from the injected client: no solid-js import; bridge signal
// access goes through the exported module accessors (adopt.ts convention).

import { resolveCard, cardToPane, cardToSessionNode } from './model/bridge';

/** The V13.1 client surface this path needs (rest.ts postMessage, injectable). */
export interface FollowUpClient {
  postMessage(sessionId: string, text: string): Promise<unknown>;
}

export type FollowUpResult =
  | { disabled: true; reason: string }
  | { disabled: false; sessionNodeId: string };

/** Plain-language disabled reason — surfaces verbatim in the drawer. */
export const FOLLOWUP_DISABLED_REASON =
  'Comments need a running Voss session. This card comes from a saved run — nothing is live to receive a reply.';

/**
 * The native sessionNodeId for a card, or undefined for a snapshot-only card.
 * Native cards are the ones registered via registerNativeCard (Bridge A) —
 * resolveCard's snapshot FALLBACK (sessionNodeId = cardId) is deliberately not
 * treated as a write target: a snapshot node id has no live session behind it.
 */
export function nativeSessionNodeId(cardId: string): string | undefined {
  const registered = cardId in cardToSessionNode();
  if (!registered) return undefined;
  return resolveCard(
    { cardToPane: cardToPane(), cardToSessionNode: cardToSessionNode() },
    cardId,
  ).sessionNodeId;
}

/**
 * Dispatch a follow-up comment to the card's bound native session, or return
 * disabled-with-reason when no write path exists (snapshot card, or no live
 * client connected). Nothing is dispatched on the disabled path.
 */
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
