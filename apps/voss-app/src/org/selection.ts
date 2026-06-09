// Global selection store (VCKP-01/05). Hoists `selectedCardId` out of
// `OrgViewShell` local state into module-level Solid signals so the Board spine,
// card drawer, timeline rail, and gate bar all read one source of truth.
// Mirrors the module-level `createSignal` pattern in orgStore.ts exactly.

import { createSignal } from 'solid-js';

export const [selectedCardId, setSelectedCardId] = createSignal<string | null>(null);
export const [selectedRunId, setSelectedRunId] = createSignal<string | null>(null);

// D-07 Open-in-grid request. CardDrawer (and any other Review-plane surface)
// fires this with a bound pane id; App watches it, flips orgViewOpen(false) and
// focuses the pane, then clears the request. Module-level signal mirrors the
// selection signals above — CardDrawer cannot import App's local signals.
export const [openInGridRequest, setOpenInGridRequest] = createSignal<string | null>(null);

export function requestOpenInGrid(paneId: string): void {
  setOpenInGridRequest(paneId);
}

// V14 chunk C — the reverse jump: a live-grid surface (the pane header card
// chip) fires this with a bound card id; App watches it, selects the card and
// flips orgViewOpen(true), then clears the request. Opt-in only (chip click).
export const [openInReviewRequest, setOpenInReviewRequest] = createSignal<string | null>(null);

export function requestOpenInReview(cardId: string): void {
  setOpenInReviewRequest(cardId);
}
