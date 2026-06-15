// V24-05 (VADE2-05) — Tasks mission-control surface: status grouping.
//
// Managed work reads like a status system: fixture runs spanning each status
// (InProgress / Blocked / InReview / Done) appear under the correct UI-SPEC
// group (ACTIVE / BLOCKED / REVIEWING / DONE). Mirrors swarmReconcile.test.ts
// pure-fixture discipline + the cockpit tauri-mock for the data-loading import.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import TasksSurface from '../TasksSurface';
import { cardsFromRunData } from '../../../org/boardDerive';
import { setRunData, setLoading, setLoadError } from '../../../org/orgStore';
import { __resetBridgeMaps } from '../../../org/model/bridge';
import { __resetAttentionQueue } from '../../../org/attention/attentionQueue';
import type { RunData, SessionTreeNode, Transition } from '../../../org/types';

function node(partial: Partial<SessionTreeNode> & { id: string }): SessionTreeNode {
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

function boardTo(to: string): Transition {
  return { kind: 'board.transition', from: 'Backlog', to, outcome: '', verdict_snapshot: null };
}

// A run with one non-root node per status column.
function makeRun(): RunData {
  return {
    run_id: 'run-1',
    session_tree: {
      root_id: 'root',
      nodes: [
        node({ id: 'root', parent_run_id: null, scope: 'root run', role: null }),
        node({ id: 'c-active', scope: 'active task', role: 'executor', transitions: [boardTo('InProgress')] }),
        node({ id: 'c-review', scope: 'review task', role: 'reviewer', transitions: [boardTo('InReview')] }),
        node({ id: 'c-done', scope: 'done task', role: 'executor', terminal_state: { exit_reason: 'done', final: null } }),
        node({ id: 'c-blocked', scope: 'blocked task', role: 'executor', terminal_state: { exit_reason: 'killed', final: null } }),
      ],
    },
    review: {},
    audit: null,
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
  __resetBridgeMaps();
  __resetAttentionQueue();
  vi.restoreAllMocks();
});

describe('cardsFromRunData — fixture spans each status column', () => {
  it('derives one card per status (InProgress/InReview/Done/Blocked)', () => {
    const cards = cardsFromRunData(makeRun());
    expect(cards.filter((c) => c.column === 'InProgress')).toHaveLength(1);
    expect(cards.filter((c) => c.column === 'InReview')).toHaveLength(1);
    expect(cards.filter((c) => c.column === 'Done')).toHaveLength(1);
    expect(cards.filter((c) => c.column === 'Blocked')).toHaveLength(1);
  });
});

describe('TasksSurface — status grouping', () => {
  it('renders ACTIVE/BLOCKED/REVIEWING/DONE group headers for a spanning run', () => {
    setRunData(makeRun());
    const el = mount(() => <TasksSurface />);
    const groupNames = Array.from(
      el.querySelectorAll('.surface-group__name'),
    ).map((n) => n.textContent?.trim());
    expect(groupNames).toContain('ACTIVE');
    expect(groupNames).toContain('BLOCKED');
    expect(groupNames).toContain('REVIEWING');
    expect(groupNames).toContain('DONE');
  });

  it('places each Task under its correct group', () => {
    setRunData(makeRun());
    const el = mount(() => <TasksSurface />);
    const groupOf = (name: string): string => {
      const headers = Array.from(el.querySelectorAll('.surface-group'));
      for (const g of headers) {
        if (g.querySelector('.surface-group__name')?.textContent?.trim() === name) {
          return g.textContent ?? '';
        }
      }
      return '';
    };
    expect(groupOf('ACTIVE')).toContain('active task');
    expect(groupOf('REVIEWING')).toContain('review task');
    expect(groupOf('DONE')).toContain('done task');
    expect(groupOf('BLOCKED')).toContain('blocked task');
  });

  it('is null-tolerant — empty/null runData shows the empty state, no crash', () => {
    setRunData(null);
    const el = mount(() => <TasksSurface />);
    expect(el.querySelector('.surface-group')).toBeNull();
    expect(el.textContent).toContain('No active Tasks');
  });
});
