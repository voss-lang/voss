import type { Card, Agent } from './model/normalized';


interface SwarmAgent {
  id: string;
  paneId?: string;
  cli?: string;
  status?: string;
  task?: string;
}

interface SwarmManifest {
  id?: string;
  goal?: string;
  status?: string;
  created?: number;
  agents?: SwarmAgent[];
}

/**
 * Map a swarm agent status onto an EXISTING board column key (BoardPanel
 * COLUMNS). Null-tolerant: unknown/undefined falls back to 'Backlog'. Never
 */
export function swarmStatusToColumn(status: string | undefined): string {
  switch (status) {
    case 'running':
      return 'InProgress';
    case 'complete':
      return 'Done';
    case 'pending':
    default:
      return 'Backlog';
  }
}

export interface SwarmReconcileResult {
  rosterRows: Agent[];
  cards: Card[];
  idea?: string;
}

/**
 * Reconcile a swarm manifest into roster rows (Agent) + cards (Card). Mirrors
 * boardDerive cardsFromRunData null-tolerance: a missing manifest yields empty
 */
export function reconcileSwarm(
  manifest: SwarmManifest | null | undefined,
): SwarmReconcileResult {
  if (!manifest) return { rosterRows: [], cards: [] };

  const agents = manifest.agents ?? [];

  const rosterRows: Agent[] = agents.map((a) => ({
    id: a.id,
    role: a.task ?? '',
    provider: a.cli ?? '',
    model: '',
    status: a.status ?? 'pending',
    paneId: a.paneId,
    budget: { spent: 0, limit: 0 },
    permissionMode: 'swarm',
  }));

  const cards: Card[] = agents.map((a) => ({
    id: a.id,
    title: a.task ?? a.id,
    column: swarmStatusToColumn(a.status),
    role: a.cli ?? null,
    risk: 'med',
    scope: null,
    budget: { limit: 0, spent: 0 },
    paneId: a.paneId,
  }));

  const result: SwarmReconcileResult = { rosterRows, cards };
  if (manifest.goal !== undefined) result.idea = manifest.goal;
  return result;
}
