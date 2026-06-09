// Global selection store (VCKP-01/05). Hoists `selectedCardId` out of
// `OrgViewShell` local state into module-level Solid signals so the Board spine,
// card drawer, timeline rail, and gate bar all read one source of truth.
// Mirrors the module-level `createSignal` pattern in orgStore.ts exactly.

import { createSignal } from 'solid-js';

export const [selectedCardId, setSelectedCardId] = createSignal<string | null>(null);
export const [selectedRunId, setSelectedRunId] = createSignal<string | null>(null);
