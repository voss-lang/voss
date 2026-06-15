// V24-06 (VADE2-06) — the no-fake-signal guard. The load-bearing test of the
// phase: every rendered edge MUST carry a real, non-empty `source`, and the
// derive MUST NOT infer an edge from co-presence. Mirrors swarmReconcile.test.ts
// pure-fixture discipline.

import { describe, it, expect } from 'vitest';

import { deriveSwarmGraph } from '../swarmMapDerive';
import type {
  RunData,
  SessionTreeNode,
  Transition,
  AuditReport,
} from '../../../org/types';
import type { AttentionItem } from '../../../org/attention/attentionQueue';

function node(
  partial: Partial<SessionTreeNode> & { id: string },
): SessionTreeNode {
  return {
    root_id: 'root',
    parent_run_id: 'root',
    envelope: { limit: 100, spent: 10 },
    terminal_state: null,
    created_at: '2026-06-07T10:00:00Z',
    ended_at: null,
    transitions: [],
    scope: null,
    role: null,
    ...partial,
  };
}

const KNOWN_SOURCE = /^(board_transition:|sse_event:|audit_artifact:)/;

// Two agents co-present in a run, but NO transitions/audit/attention.
function partialRun(): RunData {
  return {
    run_id: 'run-partial',
    session_tree: {
      root_id: 'root',
      nodes: [
        node({ id: 'root', parent_run_id: null, role: null }),
        node({ id: 'cardA', role: 'executor', scope: 'do A' }),
        node({ id: 'cardB', role: 'reviewer', scope: 'do B' }),
      ],
    },
    review: {},
    audit: null,
    run_final: null,
  };
}

// A run exercising every node + edge type from real signals.
function fullRun(): RunData {
  const routing: Transition = {
    kind: 'em.routing',
    id: 'r1',
    card_id: 'cardA',
    chosen_role: 'executor',
    candidates_considered: ['executor', 'reviewer'],
    rationale_text: 'best fit',
    ts: '2026-06-07T10:01:00Z',
  };
  const reviewT: Transition = {
    kind: 'board.transition',
    from: 'InProgress',
    to: 'InReview',
    outcome: 'ok',
    verdict_snapshot: {
      conf: 0.9,
      source: 'B',
      tier: 'med',
      verdict: 'pass',
      notes: '',
      evidence_refs: [],
      domain_inferred: 'code',
    },
  };
  const audit = {
    idea: 'Ship the swarm map',
    review_sidecars: {
      cardA: {
        a_verification: {
          result: 'pass',
          test_path_or_rubric: 'tests/a.test.ts',
          notes: '',
        },
        b_verdict: null,
        final_outcome: 'pass',
      },
    },
  } as unknown as AuditReport;

  return {
    run_id: 'run-full',
    session_tree: {
      root_id: 'root',
      nodes: [
        node({ id: 'root', parent_run_id: null, role: null }),
        node({ id: 'cardA', role: 'executor', scope: 'impl', transitions: [routing] }),
        node({ id: 'cardB', role: 'reviewer', scope: 'review', transitions: [reviewT] }),
        node({
          id: 'cardC',
          role: 'executor',
          scope: 'blocked work',
          terminal_state: { exit_reason: 'killed', final: null },
        }),
      ],
    },
    review: {},
    audit,
    run_final: null,
  };
}

function attn(): AttentionItem[] {
  return [
    { id: 'p1', kind: 'permission', cardId: 'cardA', summary: 'Permission: Write', deepLink: {} },
    { id: 'b1', kind: 'budget', cardId: 'cardB', summary: 'Budget exceeded', deepLink: {} },
  ];
}

describe('deriveSwarmGraph — null tolerance', () => {
  it('empty runs → no nodes and no edges, never throws', () => {
    expect(() => deriveSwarmGraph([], [])).not.toThrow();
    expect(deriveSwarmGraph([], [])).toEqual({ nodes: [], edges: [] });
  });

  it('null runData → objective placeholder(s) only, zero edges', () => {
    const { nodes, edges } = deriveSwarmGraph([{ runData: null, liveOverlay: {} }], []);
    expect(nodes.length).toBeGreaterThan(0);
    expect(nodes.every((n) => n.type === 'placeholder')).toBe(true);
    expect(edges.length).toBe(0);
  });
});

describe('deriveSwarmGraph — NO-FAKE-SIGNAL guard (VADE2-06)', () => {
  it('partial RunData with no transitions yields zero edges (no co-presence inference)', () => {
    const { edges } = deriveSwarmGraph([{ runData: partialRun(), liveOverlay: {} }], []);
    expect(edges.length).toBe(0);
    // Vacuously true here, but the contract holds for any edge that exists.
    expect(edges.every((e) => typeof e.source === 'string' && e.source.length > 0)).toBe(true);
  });

  it('every edge on a full run carries a real, non-empty source', () => {
    const { edges } = deriveSwarmGraph([{ runData: fullRun(), liveOverlay: {} }], attn());
    expect(edges.length).toBeGreaterThan(0);
    expect(edges.every((e) => typeof e.source === 'string' && e.source.length > 0)).toBe(true);
    expect(edges.every((e) => KNOWN_SOURCE.test(e.source))).toBe(true);
  });
});

describe('deriveSwarmGraph — full fixture exercises every node type', () => {
  it('produces objective, agent, work, artifact, and alert nodes', () => {
    const { nodes } = deriveSwarmGraph([{ runData: fullRun(), liveOverlay: {} }], attn());
    const types = new Set(nodes.map((n) => n.type));
    expect(types.has('objective')).toBe(true);
    expect(types.has('agent')).toBe(true);
    expect(types.has('work')).toBe(true);
    expect(types.has('artifact')).toBe(true);
    expect(types.has('alert')).toBe(true);
  });

  it('renders one objective per run across multiple runs', () => {
    const { nodes } = deriveSwarmGraph(
      [
        { runData: fullRun(), liveOverlay: {} },
        { runData: partialRun(), liveOverlay: {} },
      ],
      [],
    );
    expect(nodes.filter((n) => n.type === 'objective')).toHaveLength(2);
  });
});
