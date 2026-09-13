import type { RunData } from '../types';
import type { BudgetEntry } from '../../pane/budgetRegistry';
import { cardsFromRunData } from '../boardDerive';
import type { Card, Agent, Run } from './normalized';

export interface AgentEntry {
  paneId: string;
  sessionId: string;
  cliBinary: string;
  cliArgs: string;
  cwd: string;
  status: string;
  lastSeen: number;
}

export interface CardBridge {
  paneIdForCard(cardId: string): string | undefined;
}

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
