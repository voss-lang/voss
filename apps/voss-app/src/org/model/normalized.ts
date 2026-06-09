// V14 normalized UI data model (VCKP-01). Pure type/interface module: no Solid
// imports, no logic, no side effects — mirrors the boardDerive.ts / types.ts
// pure-module convention so it stays fixture-testable.
//
// This overlay extends the snapshot plane (`RunData`/`SessionTreeNode` from
// ../types) with live-plane fields. It MUST NOT edit the D-02-guarded `RunData`
// or `guards.ts` — the overlay lives only here (RESEARCH §4, Pitfall 2).

import type { RunData, SessionTreeNode } from '../types';

// --- Capability tier (D-13, VCKP-13) -----------------------------------------

export type CapabilityTier = 'A' | 'B' | 'C';

// --- Card: snapshot fields + optional live overlay ---------------------------

/**
 * A board card: the snapshot-derived fields (id/title/column/role/risk/scope/
 * budget) plus optional live-overlay fields bound via the id-bridge (VCKP-02).
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

// --- Agent: live-plane participant -------------------------------------------

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

// --- SessionNode: normalized view over the snapshot session tree -------------

/** Normalized session-tree node; aliases the snapshot `SessionTreeNode`. */
export interface SessionNode extends SessionTreeNode {}

// --- Evidence + Decision -----------------------------------------------------

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

// --- Run: top-level normalized model -----------------------------------------

/** The merged model: the snapshot run spine overlaid with live cards/agents. */
export interface Run {
  runId: string;
  snapshot: RunData | null;
  cards: Card[];
  agents: Agent[];
}
