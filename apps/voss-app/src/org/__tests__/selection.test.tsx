import { describe, it, expect, afterEach } from 'vitest';
import { render } from 'solid-js/web';

import { selectedCardId, setSelectedCardId } from '../selection';

// --- Test harness (mirrors boardPanel.test.tsx) ------------------------------

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
  // selection.ts uses module-level (global) signals — reset so this test
  // does not leak state into the rest of the suite.
  setSelectedCardId(null);
});

// --- Two trivial surfaces, each reading the global selectedCardId signal ------

function SurfaceA() {
  return <div data-surface="A">{selectedCardId() ?? 'none'}</div>;
}

function SurfaceB() {
  return <div data-surface="B">{selectedCardId() ?? 'none'}</div>;
}

// --- VCKP-01: one selection action observed by >=2 distinct surfaces ----------

describe('selection store — one action observed by >=2 surfaces', () => {
  it('setSelectedCardId(C1) is reflected by two independent rendered surfaces', () => {
    const root = mount(() => (
      <>
        <SurfaceA />
        <SurfaceB />
      </>
    ));

    const a = root.querySelector('[data-surface="A"]') as HTMLElement;
    const b = root.querySelector('[data-surface="B"]') as HTMLElement;
    expect(a.textContent).toBe('none');
    expect(b.textContent).toBe('none');

    // One action.
    setSelectedCardId('C1');

    // Both distinct surfaces observe it via the shared global signal.
    expect(a.textContent).toBe('C1');
    expect(b.textContent).toBe('C1');
  });
});
