// V24-05 (VADE2-05) — portal surface deep-link contract.
//
// Clicking a Task row deep-links to the corresponding pane/drawer via the real
// org/selection signals: a row whose card is bound to a pane (bridge B) fires
// requestOpenInGrid(paneId); an unbound card falls back to
// requestOpenInReview(cardId). No fabricated APIs — uses the real bridge,
// selection signals, and cardsFromRunData path through TasksSurface.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import TasksSurface from '../surfaces/tasks/TasksSurface';
import { setRunData, setLoading, setLoadError } from '../org/orgStore';
import {
  registerTerminalCard,
  __resetBridgeMaps,
} from '../org/model/bridge';
import {
  openInGridRequest,
  setOpenInGridRequest,
  openInReviewRequest,
  setOpenInReviewRequest,
} from '../org/selection';
import { __resetAttentionQueue } from '../org/attention/attentionQueue';
import type { RunData, SessionTreeNode } from '../org/types';

function node(partial: Partial<SessionTreeNode> & { id: string }): SessionTreeNode {
  return {
    root_id: 'root',
    parent_run_id: 'root',
    envelope: { limit: 100, spent: 10 },
    terminal_state: null,
    created_at: '2026-06-07T10:00:00Z',
    ended_at: null,
    transitions: [
      { kind: 'board.transition', from: 'Backlog', to: 'InProgress', outcome: '', verdict_snapshot: null },
    ],
    scope: null,
    role: 'executor',
    ...partial,
  };
}

function runWith(cardId: string, title: string): RunData {
  return {
    run_id: 'run-1',
    session_tree: {
      root_id: 'root',
      nodes: [
        node({ id: 'root', parent_run_id: null, role: null, scope: 'root' }),
        node({ id: cardId, scope: title }),
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
  setOpenInGridRequest(null);
  setOpenInReviewRequest(null);
  __resetBridgeMaps();
  __resetAttentionQueue();
  vi.restoreAllMocks();
});

describe('portalDeepLink — row click drives org/selection', () => {
  it('a card bound to a pane fires requestOpenInGrid(paneId)', () => {
    const paneId = 'pane-7';
    const cardId = registerTerminalCard(paneId); // cardToPane[cardId] = paneId
    setRunData(runWith(cardId, 'bound task'));
    const el = mount(() => <TasksSurface />);

    const row = el.querySelector('[aria-label="Open Task: bound task"]') as HTMLButtonElement;
    expect(row).toBeTruthy();
    fireEvent.click(row);

    expect(openInGridRequest()).toBe(paneId);
    expect(openInReviewRequest()).toBeNull();
  });

  it('an unbound card falls back to requestOpenInReview(cardId)', () => {
    setRunData(runWith('card-unbound', 'free task'));
    const el = mount(() => <TasksSurface />);

    const row = el.querySelector('[aria-label="Open Task: free task"]') as HTMLButtonElement;
    expect(row).toBeTruthy();
    fireEvent.click(row);

    expect(openInReviewRequest()).toBe('card-unbound');
    expect(openInGridRequest()).toBeNull();
  });
});
