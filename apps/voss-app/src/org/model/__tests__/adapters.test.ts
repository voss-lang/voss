import { describe, it, expect } from 'vitest';

// VCKP-01: pure adapter `buildModel(snapshot, liveAgents, budgets, bridge)` that
// uses cardsFromRunData as the spine and overlays live-plane fields by the
// id-bridge. buildModel is pure (no Solid/produce), so it is fixture-testable
// like boardDerive.ts — imported eagerly here now that ../adapters exists.

import { buildModel, type AgentEntry, type CardBridge } from '../adapters';
import type { BudgetEntry } from '../../../pane/budgetRegistry';
import type { RunData } from '../../types';

// --- Golden fixtures ---------------------------------------------------------

// A minimal RunData whose single non-root node has id "C1" (snapshot card id IS
// the node id — boardDerive uses n.id). cardsFromRunData yields one card: C1.
const SNAPSHOT = {
  run_id: 'root-run',
  session_tree: {
    root_id: 'root-run',
    nodes: [
      {
        id: 'root-run',
        root_id: 'root-run',
        parent_run_id: null,
        envelope: { limit: 500000, spent: 1000 },
        terminal_state: null,
        created_at: '2026-06-07T10:00:00Z',
        ended_at: null,
        scope: 'root',
        role: 'user',
        transitions: [],
      },
      {
        id: 'C1',
        root_id: 'root-run',
        parent_run_id: 'root-run',
        envelope: { limit: 200000, spent: 145000 },
        terminal_state: { exit_reason: 'done', final: true },
        created_at: '2026-06-07T10:02:00Z',
        ended_at: '2026-06-07T10:18:00Z',
        scope: 'implement board panel',
        role: 'backend',
        transitions: [
          { kind: 'em.ticket', id: 't-c1', card_id: 'C1', risk_tier: 'high', ts: '2026-06-07T10:02:10Z' },
          { kind: 'board.transition', from: 'InReview', to: 'Done', outcome: 'pass', verdict_snapshot: null },
        ],
      },
    ],
  },
} as unknown as RunData;

// Fake live registry: an agent running on pane P1 (mirrors live-registry.json).
const LIVE_AGENTS: AgentEntry[] = [
  {
    paneId: 'P1',
    sessionId: '0139377ff590',
    cliBinary: 'voss',
    cliArgs: '["chat"]',
    cwd: '/Users/benjaminmarks/Projects/Voss',
    status: 'running',
    lastSeen: 1749384474,
  },
];

// Budgets keyed by paneId; carries the live cost_usd we expect to surface.
const BUDGETS: Record<string, BudgetEntry> = {
  P1: {
    tokens_used: 1200,
    token_limit: 200000,
    cost_usd: 0.42,
    iteration: 3,
    model: 'sonnet-4-6',
    lastSeenMs: 1749384474000,
  },
};

// Bridge resolver: card C1 -> pane P1 (the keystone binding).
const BRIDGE: CardBridge = {
  paneIdForCard: (cardId) => (cardId === 'C1' ? 'P1' : undefined),
};

describe('adapters.buildModel — VCKP-01', () => {
  it('buildModel returns one Card per non-root snapshot node (cardsFromRunData spine)', () => {
    const run = buildModel(SNAPSHOT, LIVE_AGENTS, BUDGETS, BRIDGE);
    expect(run.cards).toHaveLength(1);
    expect(run.cards[0].id).toBe('C1');
    expect(run.runId).toBe('root-run');
  });

  it('each merged Card carries snapshot fields id/title/column/role/risk/budget from cardsFromRunData', () => {
    const card = buildModel(SNAPSHOT, LIVE_AGENTS, BUDGETS, BRIDGE).cards[0];
    expect(card.title).toBe('implement board panel');
    expect(card.role).toBe('backend');
    expect(card.risk).toBe('high');
    expect(card.column).toBe('Done');
    expect(card.budget).toEqual({ limit: 200000, spent: 145000 });
  });

  it("buildModel overlays paneId='P1' onto card 'C1' via the bridge (live-registry agent on P1)", () => {
    const card = buildModel(SNAPSHOT, LIVE_AGENTS, BUDGETS, BRIDGE).cards[0];
    expect(card.paneId).toBe('P1');
  });

  it("buildModel sets card.sessionNodeId = card id (C1 -> 'C1')", () => {
    const card = buildModel(SNAPSHOT, LIVE_AGENTS, BUDGETS, BRIDGE).cards[0];
    expect(card.sessionNodeId).toBe('C1');
  });

  it('buildModel overlays liveBudget onto a card from budgets[resolvedPaneId]', () => {
    const card = buildModel(SNAPSHOT, LIVE_AGENTS, BUDGETS, BRIDGE).cards[0];
    expect(card.liveBudget).toBe(0.42);
    expect(card.liveStatus).toBe('running');
  });

  it('buildModel is pure: a merged card carries snapshot title/role/risk/column AND paneId/liveBudget from ONE call', () => {
    const card = buildModel(SNAPSHOT, LIVE_AGENTS, BUDGETS, BRIDGE).cards[0];
    // snapshot plane
    expect(card.title).toBe('implement board panel');
    expect(card.role).toBe('backend');
    expect(card.risk).toBe('high');
    expect(card.column).toBe('Done');
    // live overlay plane
    expect(card.paneId).toBe('P1');
    expect(card.liveBudget).toBe(0.42);
    expect(card.liveStatus).toBe('running');
  });

  // --- Behavior 2: card with no bound pane -----------------------------------

  it('a card with no bound pane gets no paneId/liveBudget but keeps snapshot fields + sessionNodeId === own id', () => {
    const noBind: CardBridge = { paneIdForCard: () => undefined };
    const card = buildModel(SNAPSHOT, LIVE_AGENTS, BUDGETS, noBind).cards[0];
    expect(card.paneId).toBeUndefined();
    expect(card.liveBudget).toBeUndefined();
    expect(card.liveStatus).toBeUndefined();
    // snapshot fields survive
    expect(card.title).toBe('implement board panel');
    expect(card.role).toBe('backend');
    expect(card.risk).toBe('high');
    expect(card.column).toBe('Done');
    // sessionNodeId defaults to the card's own id
    expect(card.sessionNodeId).toBe('C1');
  });

  // --- Behavior 3: null tolerance (mirror boardDerive) -----------------------

  it('buildModel(null, [], {}, bridge) returns an empty-cards Run without throwing', () => {
    const run = buildModel(null, [], {}, BRIDGE);
    expect(run.cards).toEqual([]);
    expect(run.agents).toEqual([]);
    expect(run.snapshot).toBeNull();
    expect(run.runId).toBe('');
  });
});
