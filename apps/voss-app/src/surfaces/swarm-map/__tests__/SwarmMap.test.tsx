// V24-06 (VADE2-06) — SwarmMap render smoke. Full-fixture render shows every
// node-type shape in a radial arrangement; no-data render shows the honest empty
// state with zero node shapes (no fabricated graph). Mirrors cockpit.test.tsx
// tauri-mock harness.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import SwarmMap from '../SwarmMap';
import { setRunData, setLoading, setLoadError } from '../../../org/orgStore';
import {
  attentionQueue,
  ingestSnapshotDecisions,
  __resetAttentionQueue,
} from '../../../org/attention/attentionQueue';
import { __resetBridgeMaps } from '../../../org/model/bridge';
import type {
  RunData,
  SessionTreeNode,
  Transition,
  AuditReport,
} from '../../../org/types';

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

function fullRun(): RunData {
  const routing: Transition = {
    kind: 'em.routing',
    id: 'r1',
    card_id: 'cardA',
    chosen_role: 'executor',
    candidates_considered: ['executor'],
    rationale_text: 'fit',
    ts: '2026-06-07T10:01:00Z',
  };
  const audit = {
    idea: 'Ship the swarm map',
    review_sidecars: {
      cardA: {
        a_verification: { result: 'pass', test_path_or_rubric: 'tests/a.test.ts', notes: '' },
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
        node({ id: 'cardB', role: 'reviewer', scope: 'review' }),
        node({
          id: 'cardC',
          role: 'executor',
          scope: 'blocked',
          terminal_state: { exit_reason: 'killed', final: null },
        }),
      ],
    },
    review: {},
    audit,
    run_final: null,
  };
}

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  setRunData(null);
  setLoading(false);
  setLoadError(null);
  __resetAttentionQueue();
  __resetBridgeMaps();
  vi.restoreAllMocks();
});

const typeSel = (t: string) => `[data-node-type="${t}"]`;

describe('SwarmMap — full-fixture radial render', () => {
  it('renders objective/agent/work/artifact/alert node shapes', () => {
    const run = fullRun();
    ingestSnapshotDecisions(run); // blocked node → real attention alert
    expect(attentionQueue().length).toBeGreaterThan(0);
    setRunData(run);
    const el = mount(() => <SwarmMap />);

    for (const t of ['objective', 'agent', 'work', 'artifact', 'alert']) {
      expect(el.querySelector(typeSel(t)), `node type ${t}`).toBeTruthy();
    }
  });

  it('arranges nodes radially — objective at centre, agents on a ~120px ring', () => {
    setRunData(fullRun());
    const el = mount(() => <SwarmMap />);

    const obj = el.querySelector(typeSel('objective')) as SVGGElement;
    const dist = (n: Element) =>
      Math.hypot(
        Number(n.getAttribute('data-x')),
        Number(n.getAttribute('data-y')),
      );
    expect(dist(obj)).toBeLessThan(10); // objective at cluster centre

    const agents = Array.from(el.querySelectorAll(typeSel('agent')));
    expect(agents.length).toBeGreaterThan(0);
    expect(agents.some((a) => dist(a) > 100 && dist(a) < 140)).toBe(true);
  });

  it('renders edges, each carrying an edge-type', () => {
    const run = fullRun();
    ingestSnapshotDecisions(run);
    setRunData(run);
    const el = mount(() => <SwarmMap />);
    const edges = Array.from(el.querySelectorAll('[data-edge-type]'));
    expect(edges.length).toBeGreaterThan(0);
  });
});

describe('SwarmMap — honest empty state', () => {
  it('with no run data shows the empty state and zero node shapes', () => {
    setRunData(null);
    const el = mount(() => <SwarmMap />);
    expect(el.textContent).toContain('No run data yet');
    expect(el.querySelectorAll('[data-node-type]').length).toBe(0);
  });
});
