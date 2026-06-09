// V14 snapshot+live adapters (VCKP-01). Pure module: no Solid imports, no
// reactive-store cloning helpers — plain reads + hand-built object literals.
// Mirrors the boardDerive.ts convention so buildModel stays fixture-testable.
//
// buildModel takes the snapshot `RunData` as the spine (via cardsFromRunData)
// and overlays live registry/budget fields by card->pane, WITHOUT touching the
// D-02-guarded `RunData`/`guards.ts` (Pitfall 2). The overlay lives only in the
// normalized model (../model/normalized.ts).

import type { RunData } from '../types';
import type { BudgetEntry } from '../../pane/budgetRegistry';
import { cardsFromRunData } from '../boardDerive';
import type { Card, Agent, Run } from './normalized';

/**
 * Live-plane participant as serialized by `get_active_agents` (camelCase mirror
 * of agent_registry.rs). No TS type ships for this shape yet, so declare it here.
 */
export interface AgentEntry {
  paneId: string;
  sessionId: string;
  cliBinary: string;
  cliArgs: string;
  cwd: string;
  status: string;
  lastSeen: number;
}

/** A minimal card->pane resolver; the plan-02 bridge will satisfy this shape. */
export interface CardBridge {
  paneIdForCard(cardId: string): string | undefined;
}

/**
 * Merge the snapshot spine with the live registry/budget planes into one Run.
 *
 * - Cards come from `cardsFromRunData(snapshot)` (the spine; card `id` IS the
 *   `sessionNodeId`).
 * - Each card is overlaid with `paneId` (via the bridge), `liveBudget` (from the
 *   budgets map by resolved paneId), and `liveStatus` (registry status, falling
 *   back to budget freshness).
 * - Null-tolerant: `buildModel(null, [], {}, bridge)` returns an empty-cards Run.
 */
export function buildModel(
  snapshot: RunData | null,
  liveAgents: AgentEntry[],
  budgets: Record<string, BudgetEntry>,
  bridge: CardBridge,
): Run {
  const statusByPane: Record<string, string> = {};
  for (const a of liveAgents) statusByPane[a.paneId] = a.status;

  const cards: Card[] = cardsFromRunData(snapshot).map((c) => {
    const paneId = bridge.paneIdForCard(c.id);
    const liveBudget = paneId ? budgets[paneId]?.cost_usd : undefined;
    const liveStatus = paneId
      ? statusByPane[paneId] ?? (budgets[paneId] ? 'running' : undefined)
      : undefined;

    const card: Card = {
      id: c.id,
      title: c.title,
      column: c.column,
      role: c.role,
      risk: c.risk,
      scope: c.title,
      budget: { limit: c.limit, spent: c.spent },
      sessionNodeId: c.id,
    };
    if (paneId !== undefined) card.paneId = paneId;
    if (liveBudget !== undefined) card.liveBudget = liveBudget;
    if (liveStatus !== undefined) card.liveStatus = liveStatus;
    return card;
  });

  return {
    runId: snapshot?.run_id ?? '',
    snapshot,
    cards,
    agents: registryToAgents(liveAgents, budgets),
  };
}

/**
 * Project the live registry (+ budgets) into roster Agents for the overlay.
 * Pure mapping; no snapshot dependency.
 */
export function registryToAgents(
  liveAgents: AgentEntry[],
  budgets: Record<string, BudgetEntry>,
): Agent[] {
  return liveAgents.map((a) => {
    const budget = budgets[a.paneId];
    return {
      id: a.sessionId,
      role: '',
      provider: a.cliBinary,
      model: budget?.model ?? '',
      status: a.status,
      paneId: a.paneId,
      budget: { spent: budget?.cost_usd ?? 0, limit: 0 },
      permissionMode: '',
    };
  });
}
