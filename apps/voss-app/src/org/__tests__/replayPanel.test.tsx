import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import ReplayPanel from '../panels/ReplayPanel';
import type { RunData } from '../types';
import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';

// node-child has 4 board.transition entries → M = 4.
const FIXTURE_RUN_DATA = {
  run_id: 'a1b2c3d4e5f6',
  session_tree: { root_id: 'a1b2c3d4e5f6', nodes: [nodeRoot, nodeChild] },
  review: {},
  audit: null,
  run_final: null,
} as unknown as RunData;

// root only → no board.transition → M = 0.
const NO_TRANSITIONS = {
  run_id: 'a1b2c3d4e5f6',
  session_tree: { root_id: 'a1b2c3d4e5f6', nodes: [nodeRoot] },
  review: {},
  audit: null,
  run_final: null,
} as unknown as RunData;

const CHILD_ID = nodeChild.id;

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
});

const back = (r: HTMLElement) =>
  r.querySelector('[aria-label="Previous step"]') as HTMLButtonElement;
const fwd = (r: HTMLElement) =>
  r.querySelector('[aria-label="Next step"]') as HTMLButtonElement;
const col = (r: HTMLElement, key: string) =>
  r.querySelector(`[data-col="${key}"]`) as HTMLElement;

describe('ReplayPanel — VADE-10', () => {
  it('Back disabled at step 0; counter shows Step 1 / 4', () => {
    const root = mount(() => <ReplayPanel data={FIXTURE_RUN_DATA} />);
    expect(back(root).disabled).toBe(true);
    expect(back(root).getAttribute('aria-disabled')).toBe('true');
    expect(root.textContent).toContain('Step 1 / 4');
    // step 0 applies the 0th transition → child in Planned
    expect(col(root, 'Planned').querySelector(`[data-card-id="${CHILD_ID}"]`)).toBeTruthy();
  });

  it('Forward advances the counter and the board snapshot', () => {
    const root = mount(() => <ReplayPanel data={FIXTURE_RUN_DATA} />);
    fwd(root).click();
    expect(root.textContent).toContain('Step 2 / 4');
    // step 1 → child now in InProgress
    expect(col(root, 'InProgress').querySelector(`[data-card-id="${CHILD_ID}"]`)).toBeTruthy();
  });

  it('Forward disabled at the final step', () => {
    const root = mount(() => <ReplayPanel data={FIXTURE_RUN_DATA} />);
    fwd(root).click(); // 2
    fwd(root).click(); // 3
    fwd(root).click(); // 4 (final, index 3)
    expect(root.textContent).toContain('Step 4 / 4');
    expect(fwd(root).disabled).toBe(true);
  });

  it('renders the final-state notice', () => {
    const root = mount(() => <ReplayPanel data={FIXTURE_RUN_DATA} />);
    expect(root.textContent).toContain(
      'Audit, Verdict, Budget, and Scope panels show final-run state only.',
    );
    expect(root.textContent).toContain('REPLAY');
  });

  it('no transitions → empty state', () => {
    const root = mount(() => <ReplayPanel data={NO_TRANSITIONS} />);
    expect(root.textContent).toContain(
      'No transition history for this run. Replay requires persisted transitions.',
    );
    expect(root.querySelector('[aria-label="Next step"]')).toBeNull();
  });
});
