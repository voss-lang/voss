/**
 * V14-12 gap-fix (VCKP-12 wiring): adopted-pane registry.
 *
 * "Let Voss manage this agent" adoption is forward-only and tier C. The
 * adoption happens AFTER the pane spawned, so enforcement state cannot be
 * frozen into the transport opts at construction — PaneComponent reads this
 * signal per budget_update event to apply the budget-stop, and roster surfaces
 * read the tier. Mirrors budgetRegistry.ts (module signal, immutable spread).
 */
import { createSignal } from 'solid-js';

export type AdoptionEntry = {
  cardId: string;
  /** Advisory budget (USD); at/over → the pane is stopped (budget-kill). */
  budgetUsd: number;
  tier: 'C';
};

const [adoptionByPaneId, setAdoptionByPaneId] = createSignal<
  Record<string, AdoptionEntry>
>({});

export function registerAdoption(paneId: string, entry: AdoptionEntry): void {
  setAdoptionByPaneId((prev) => ({ ...prev, [paneId]: entry }));
}

export function unregisterAdoption(paneId: string): void {
  setAdoptionByPaneId((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { adoptionByPaneId };

/** Test-only reset (module signal is global). */
export function __resetAdoptions(): void {
  setAdoptionByPaneId({});
}
