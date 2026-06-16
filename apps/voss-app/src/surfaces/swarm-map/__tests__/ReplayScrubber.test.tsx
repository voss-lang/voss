// V24-07 (VADE2-07) — replay scrubber drives the graph state. The range value
// reflects the step signal; moving it changes the projected frame
// (computeBoardAtStep) to the corresponding step. Signal-drive render mirror of
// liveReviewToggle.test.tsx + the ReplayPanel step pattern.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import ReplayScrubber from '../ReplayScrubber';
import type {
  RunData,
  SessionTreeNode,
  Transition,
  RunFinal,
} from '../../../org/types';

function bt(from: string, to: string): Transition {
  return { kind: 'board.transition', from, to, outcome: '', verdict_snapshot: null };
}

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

// Completed run: card 'a' moves Backlog→InProgress (step 0) then InProgress→Done
// (step 1), so the Done count changes between steps.
function completedRun(): RunData {
  return {
    run_id: 'r',
    session_tree: {
      root_id: 'root',
      nodes: [
        node({ id: 'root', parent_run_id: null }),
        node({
          id: 'a',
          role: 'executor',
          transitions: [bt('Backlog', 'InProgress'), bt('InProgress', 'Done')],
          terminal_state: { exit_reason: 'done', final: null },
        }),
      ],
    },
    review: {},
    audit: null,
    run_final: { kind: 'em.run_final', root_id: 'root', idea: 'x' } as unknown as RunFinal,
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
  vi.restoreAllMocks();
});

describe('ReplayScrubber — range drives the replay step', () => {
  it('starts at step 0 with an accessible range input', () => {
    const el = mount(() => <ReplayScrubber data={completedRun()} />);
    const range = el.querySelector('input[type="range"]') as HTMLInputElement;
    expect(range).toBeTruthy();
    expect(range.getAttribute('aria-label')).toBe('Replay timeline');
    expect(range.value).toBe('0');
    const root = el.querySelector('.replay-scrubber') as HTMLElement;
    expect(root.getAttribute('data-step')).toBe('0');
    expect(root.getAttribute('data-done')).toBe('0'); // not Done yet at step 0
  });

  it('scrubbing the range updates the projected frame', () => {
    const el = mount(() => <ReplayScrubber data={completedRun()} />);
    const range = el.querySelector('input[type="range"]') as HTMLInputElement;
    const root = el.querySelector('.replay-scrubber') as HTMLElement;

    fireEvent.input(range, { target: { value: '1' } });

    expect(range.value).toBe('1');
    expect(root.getAttribute('data-step')).toBe('1');
    expect(root.getAttribute('data-done')).toBe('1'); // card 'a' reaches Done at step 1
  });

  it('play/pause button carries a state-dependent aria-label', () => {
    const el = mount(() => <ReplayScrubber data={completedRun()} />);
    const play = el.querySelector('.replay-scrubber__play') as HTMLButtonElement;
    expect(play.getAttribute('aria-label')).toBe('Play replay');
    fireEvent.click(play);
    expect(play.getAttribute('aria-label')).toBe('Pause replay');
    fireEvent.click(play); // pause again so the interval is cleared before unmount
  });
});
