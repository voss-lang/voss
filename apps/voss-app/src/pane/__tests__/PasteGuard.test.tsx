import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import PasteGuard from '../PasteGuard';

let dispose: (() => void) | undefined;
function mount(el: HTMLElement, ui: () => unknown) {
  dispose = render(ui as () => never, el);
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

describe('PasteGuard (PTY-04)', () => {
  it('multi-line paste shows banner: first-line preview + (N lines) badge + Discard (not Cancel)', () => {
    const root = document.createElement('div');
    document.body.appendChild(root);
    const onSend = vi.fn();
    const onDiscard = vi.fn();
    mount(root, () => (
      <PasteGuard
        pendingText={'first-line\nsecond\nthird'}
        onSend={onSend}
        onDiscard={onDiscard}
      />
    ));

    expect(root.textContent).toContain('first-line');
    expect(root.textContent).toContain('(3 lines)');
    expect(root.textContent).toContain('Discard');
    expect(root.textContent).not.toContain('Cancel');
    // bypass hint copy is load-bearing (UI-SPEC §9)
    expect(root.textContent).toContain('⌘⇧V skips this');
  });

  it('Send button fires onSend; Discard button fires onDiscard', () => {
    const root = document.createElement('div');
    document.body.appendChild(root);
    const onSend = vi.fn();
    const onDiscard = vi.fn();
    mount(root, () => (
      <PasteGuard
        pendingText={'a\nb'}
        onSend={onSend}
        onDiscard={onDiscard}
      />
    ));

    const buttons = root.querySelectorAll('button');
    const send = Array.from(buttons).find((b) =>
      b.textContent?.includes('Send'),
    )!;
    const discard = Array.from(buttons).find((b) =>
      b.textContent?.includes('Discard'),
    )!;

    fireEvent.click(send);
    expect(onSend).toHaveBeenCalledTimes(1);
    fireEvent.click(discard);
    expect(onDiscard).toHaveBeenCalledTimes(1);
  });
});
