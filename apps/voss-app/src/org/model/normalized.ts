import type { RunData, SessionTreeNode } from '../types';


export type CapabilityTier = 'A' | 'B' | 'C';


/**
 * A board card: the snapshot-derived fields (id/title/column/role/risk/scope/
 * budget) plus optional live-overlay fields bound via the id-bridge (-02)
 */
export interface Card {
  // Snapshot fields (from cardsFromRunData / CardSnapshot)
  id: string;
  title: string;
  column: string;
  role: string | null;
  risk: string;
  scope: string | null;
  budget: { limit: number; spent: number };

  // Live overlay (bridge-resolved; absent for pure-snapshot cards)
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


/** Normalized session-tree node; aliases the snapshot `SessionTreeNode` */
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


/** The merged model: the snapshot run spine overlaid with live cards/agents */
export interface Run {
  runId: string;
  snapshot: RunData | null;
  cards: Card[];
  agents: Agent[];
}
