import { createSignal } from 'solid-js';

export const [selectedCardId, setSelectedCardId] = createSignal<string | null>(null);
export const [selectedRunId, setSelectedRunId] = createSignal<string | null>(null);

export const [openInGridRequest, setOpenInGridRequest] = createSignal<string | null>(null);

export function requestOpenInGrid(paneId: string): void {
  setOpenInGridRequest(paneId);
}

export const [openInReviewRequest, setOpenInReviewRequest] = createSignal<string | null>(null);

export function requestOpenInReview(cardId: string): void {
  setOpenInReviewRequest(cardId);
}
