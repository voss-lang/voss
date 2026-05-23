/**
 * Shared reactive registry: pane id → budget state.
 * PaneComponent writes; sidebar / status bar reads.
 */
import { createSignal } from 'solid-js';
import type { BudgetState } from './pty-ipc';

export type BudgetEntry = BudgetState & { lastSeenMs: number };

const [budgetByPaneId, setBudgetByPaneId] = createSignal<
  Record<string, BudgetEntry>
>({});

export function registerPaneBudget(paneId: string, data: BudgetState): void {
  setBudgetByPaneId((prev) => {
    const existing = prev[paneId];
    if (
      existing &&
      existing.cost_usd === data.cost_usd &&
      existing.tokens_used === data.tokens_used &&
      existing.iteration === data.iteration &&
      existing.model === data.model
    ) {
      return prev;
    }
    return { ...prev, [paneId]: { ...data, lastSeenMs: Date.now() } };
  });
}

export function unregisterPaneBudget(paneId: string): void {
  setBudgetByPaneId((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { budgetByPaneId };
