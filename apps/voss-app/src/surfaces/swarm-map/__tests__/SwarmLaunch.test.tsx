// V24 swarm surface — launch intake copy and compact overlay mode.

import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'solid-js/web';
import SwarmLaunch from '../SwarmLaunch';
import { __resetLiveServer } from '../../../org/live/liveServer';

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
  __resetLiveServer();
});

describe('SwarmLaunch', () => {
  it('renders the full empty-state orchestra intake', () => {
    const el = mount(() => <SwarmLaunch />);
    expect(el.textContent).toContain('No orchestra running');
    expect(el.textContent).toContain('Launch orchestra');
    expect(el.querySelector('textarea')?.getAttribute('placeholder')).toBe(
      'What should the orchestra do?',
    );
  });

  it('omits the empty-state heading in compact mode', () => {
    const el = mount(() => <SwarmLaunch compact />);
    expect(el.textContent).not.toContain('No orchestra running');
    expect(el.textContent).toContain('Launch orchestra');
  });
});
