import type { RunData, SessionTreeNode } from '../types';

export type CapabilityTier = 'A' | 'B' | 'C';

export interface Card {
  id: string;
  title: string;
  column: string;
  role: string | null;
  risk: string;
  scope: string | null;
  budget: { limit: number; spent: number };

  paneId?: string;
  sessionNodeId?: string;
  liveBudget?: number;
  liveStatus?: string;
}

export interface Agent {
  id: string;
  role: string;
  provider: string;
  model: string;
  status: string;
  cardId?: string;
  sessionNodeId?: string;
  paneId?: string;
  budget: { spent: number; limit: number };
  permissionMode: string;
  capabilityTier?: CapabilityTier;
}

export interface SessionNode extends SessionTreeNode {}

export interface Evidence {
  id: string;
  cardId?: string;
  sessionNodeId?: string;
  kind: string;
  ref: string;
  notes?: string;
}

export interface Decision {
  id: string;
  cardId?: string;
  decision: string;
  rationale?: string;
  ts: string;
}

export interface Run {
  runId: string;
  snapshot: RunData | null;
  cards: Card[];
  agents: Agent[];
}
