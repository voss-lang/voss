// V24-10 (VADE2-10) — Context surface wraps the shipped ContextPanel.
//
// Asserts the surface renders a Context tabpanel, shows file rows from ContextData
// (agent pane), and falls back to the panel's own empty state when there is no
// agent context. No new data path — it just forwards props to ContextPanel.

import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'solid-js/web';
import ContextSurface from '../ContextSurface';
import type { ContextData } from '../../../pane/pty-ipc';

function ctx(): ContextData {
  return {
    system_tokens: 100,
    conversation_tokens: 200,
    total_tokens: 1000,
    token_limit: 4000,
    files: [
      { path: 'src/app.ts', tokens: 400, state: 'full', pinned: false },
      { path: 'src/pinned.ts', tokens: 300, state: 'full', pinned: true },
    ],
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
});

describe('ContextSurface', () => {
  it('renders a Context tabpanel with file rows from ContextData (agent pane)', () => {
    const el = mount(() => (
      <ContextSurface context={ctx()} isAgentPane={true} />
    ));
    const panel = el.querySelector('[role="tabpanel"][aria-label="Context"]');
    expect(panel).toBeTruthy();

    // Surface header band (parity with Memory), always present.
    expect(el.querySelector('.surface__header .surface__title')?.textContent).toBe(
      'Context',
    );

    const rows = el.querySelectorAll('.context-file-row');
    expect(rows.length).toBe(2);
    expect(el.textContent).toContain('src/app.ts');
    expect(el.textContent).toContain('src/pinned.ts');
  });

  it('shows the empty state when there is no agent context', () => {
    const el = mount(() => (
      <ContextSurface context={null} isAgentPane={false} />
    ));
    expect(el.querySelector('[role="tabpanel"][aria-label="Context"]')).toBeTruthy();
    // Full-canvas surface uses the shared centered card, not ContextPanel's
    // narrow-drawer empty text.
    expect(el.querySelector('.surface-empty__card')).toBeTruthy();
    expect(el.textContent).toContain('No context to show');
    expect(el.querySelector('.context-empty')).toBeNull();
    expect(el.querySelectorAll('.context-file-row').length).toBe(0);
  });
});
