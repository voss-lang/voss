import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';

// VCKP-05 single-selection acceptance: ONE selection action must drive all four
// cockpit regions (Board, detail drawer, timeline rail, gate bar).
//
// Tauri `invoke` is mocked exactly like orgView.test.tsx — dispatch on command
// name so CockpitShell's onMount load path (enumerate_runs → load_run) resolves
// the fixture run below instead of hitting a real backend.
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn((cmd: string) => {
    if (cmd === 'enumerate_runs') {
      return Promise.resolve([
        { run_id: 'run-c1', mtime_secs: 1, has_run_final: false },
      ]);
    }
    if (cmd === 'load_run') return Promise.resolve(makeRun());
    return Promise.resolve(undefined);
  }),
}));

import CockpitShell from '../CockpitShell';
import { setSelectedCardId } from '../../selection';
import type { RunData } from '../../types';

// A run whose single board card is C1 (parent_run_id set → non-root card), with
// a review sidecar + audit so the drawer and gate bar have real C1 content.
function makeRun(): RunData {
  return {
    run_id: 'run-c1',
    session_tree: {
      root_id: 'root1',
      nodes: [
        {
          id: 'root1',
          root_id: 'root1',
          parent_run_id: null,
          envelope: { limit: 500000, spent: 30000 },
          terminal_state: null,
          created_at: '2026-06-07T10:00:00Z',
          ended_at: null,
          transitions: [],
          scope: 'root',
          role: 'user',
        },
        {
          id: 'C1',
          root_id: 'root1',
          parent_run_id: 'root1',
          envelope: { limit: 200000, spent: 145000 },
          terminal_state: { exit_reason: 'done', final: true },
          created_at: '2026-06-07T10:02:00Z',
          ended_at: '2026-06-07T10:18:00Z',
          scope: 'implement the C1 board card',
          role: 'backend',
          transitions: [
            {
              kind: 'em.ticket',
              id: 't-c1',
              card_id: 'C1',
              risk_tier: 'high',
              ts: '2026-06-07T10:02:10Z',
            },
            {
              kind: 'board.transition',
              from: 'Backlog',
              to: 'Done',
              outcome: 'pass',
              verdict_snapshot: null,
            },
          ],
        },
      ],
    },
    review: {
      C1: {
        a_verification: {
          result: 'PASS',
          test_path_or_rubric: 'tests/c1_test.py',
          notes: 'C1 verification notes',
        },
        b_verdict: null,
        final_outcome: 'pass',
      },
    },
    audit: {
      run_id: 'run-c1',
      idea: 'demo',
      principles: [],
      team_config: { source: 'cli', roster_ids: [] },
      snapshot: {
        root_id: 'root1',
        nodes: ['root1', 'C1'],
        cards: [
          {
            node_id: 'C1',
            column: 'Done',
            risk_tier: 'high',
            retry_count: 0,
            is_killed: false,
          },
        ],
        kills: [],
        rescopes: [],
        routings: [],
        verdicts: [],
        liveness: [],
        leak6: { status: 'ok', evidence: '', mitigation_present: true },
        run_final: null,
      },
      review_sidecars: {},
      run_final: null,
      signoff_ack: null,
      calibration: null,
      sections_missing: [],
      unsupported_claims: ['claim-1', 'claim-2'],
    },
    run_final: null,
  } as unknown as RunData;
}

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  // selection.ts uses module-level (global) signals — reset so this test does
  // not leak the C1 selection into the rest of the suite.
  setSelectedCardId(null);
});

// Poll until `pred()` is truthy (the run loads async: onMount → enumerate_runs
// → load_run promise chain), consistent with how orgView's load path resolves.
async function waitFor(pred: () => boolean, tries = 50): Promise<void> {
  for (let i = 0; i < tries; i++) {
    if (pred()) return;
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
  }
  throw new Error('waitFor: condition never became true');
}

const region = (root: HTMLElement, label: string): HTMLElement =>
  root.querySelector(`[aria-label="${label}"]`) as HTMLElement;

describe('VCKP-05 — one selection drives all four cockpit regions', () => {
  it('selecting C1 once highlights board + fills drawer + references node + reflects envelope', async () => {
    const root = mount(() => (
      <CockpitShell cwd="/tmp" cliBinary="voss" onClose={() => {}} />
    ));

    // The run loads asynchronously; wait until the C1 board card is rendered.
    await waitFor(() => !!root.querySelector('[data-card-id="C1"]'));

    // VCKP-06 graceful-degrade: with no stream connected, the cockpit renders
    // the live/snapshot label in its default 'snapshot' state and keeps the
    // manual-refresh affordance visible.
    const liveLabelEl = root.querySelector('.cockpit-live-label') as HTMLElement;
    expect(liveLabelEl).toBeTruthy();
    expect(liveLabelEl.textContent).toContain('snapshot');

    const board = region(root, 'Board spine');
    const drawer = region(root, 'Card detail');
    const rail = region(root, 'Timeline and replay');
    const gate = region(root, 'Gate bar');

    // --- Pre-selection: drawer + gate bar in their empty states -------------
    const card = board.querySelector('[data-card-id="C1"]') as HTMLElement;
    expect(card).toBeTruthy();
    // Not yet selected → no focus ring.
    expect(card.style.border).not.toContain('--focus');
    expect(drawer.textContent).toContain('Select a card to see its details.');
    expect(gate.textContent).toContain('No card selected.');

    // --- ONE action ---------------------------------------------------------
    setSelectedCardId('C1');

    // 1. Board highlights C1 (selected → --focus border + box-shadow ring).
    const selCard = board.querySelector('[data-card-id="C1"]') as HTMLElement;
    expect(selCard.style.border).toContain('--focus');
    expect(selCard.style['box-shadow' as any]).toContain('--focus');

    // 2. Detail drawer leaves its empty state and shows C1 content. The DiffPanel
    //    card-picker echoes the active card id, and the C1 review sidecar's
    //    a_verification surfaces in the drawer.
    expect(drawer.textContent).not.toContain('Select a card to see its details.');
    expect(drawer.textContent).toContain('C1');
    expect(drawer.textContent).toContain('tests/c1_test.py');
    expect(drawer.textContent).toContain('C1 verification notes');

    // 3. Timeline rail references C1's node. V14 chunk B: the rail is the
    //    horizontal milestone track (one data-node-id node per card), so C1's
    //    node is addressable directly — and the selection effect highlights it
    //    (.cockpit-rail__selected). Same selection-drives-rail semantic, new
    //    DOM (selector adaptation only).
    const railNode = rail.querySelector('[data-node-id="C1"]') as HTMLElement;
    expect(railNode).toBeTruthy();
    await waitFor(() => railNode.classList.contains('cockpit-rail__selected'));

    // 4. Gate bar reflects C1's envelope {limit:200000, spent:145000} and the
    //    audit's unsupported-claims count (2).
    expect(gate.textContent).not.toContain('No card selected.');
    expect(gate.textContent).toContain('145000/200000');
    expect(gate.textContent).toContain('2'); // unsupported_claims.length
  });
});
