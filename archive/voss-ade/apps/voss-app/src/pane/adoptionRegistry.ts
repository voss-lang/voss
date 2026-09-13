import { createSignal } from 'solid-js';

export type AdoptionEntry = {
  cardId: string;
/** Advisory budget (USD); at/over → the pane is stopped (budget-kill) */
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

export function __resetAdoptions(): void {
  setAdoptionByPaneId({});
}
