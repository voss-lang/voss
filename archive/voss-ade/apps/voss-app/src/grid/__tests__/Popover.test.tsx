import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import Popover from '../Popover';

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

function makeAnchor(): HTMLElement {
  const el = document.createElement('button');
  el.getBoundingClientRect = () =>
    ({ top: 10, left: 50, right: 100, bottom: 30, width: 50, height: 20, x: 50, y: 10, toJSON() {} }) as DOMRect;
  document.body.appendChild(el);
  return el;
}

describe('Popover', () => {
  it('renders children', () => {
    const anchor = makeAnchor();
    const el = mount(() => (
      <Popover anchor={anchor} onClose={() => {}}>
        <span data-testid="content">hello</span>
      </Popover>
    ));
    expect(el.querySelector('[data-testid="content"]')).toBeTruthy();
  });

  it('calls onClose on Escape keydown (D-10)', () => {
    const anchor = makeAnchor();
    const onClose = vi.fn();
    mount(() => (
      <Popover anchor={anchor} onClose={onClose}>
        <span>body</span>
      </Popover>
    ));
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose on outside click (D-10)', () => {
    const anchor = makeAnchor();
    const onClose = vi.fn();
    mount(() => (
      <Popover anchor={anchor} onClose={onClose}>
        <span>body</span>
      </Popover>
    ));
    const outside = document.createElement('div');
    document.body.appendChild(outside);
    fireEvent.click(outside);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does NOT call onClose on click inside popover', () => {
    const anchor = makeAnchor();
    const onClose = vi.fn();
    const el = mount(() => (
      <Popover anchor={anchor} onClose={onClose}>
        <button type="button">inner</button>
      </Popover>
    ));
    const inner = el.querySelector('button[type="button"]')!;
    fireEvent.click(inner);
    expect(onClose).not.toHaveBeenCalled();
  });
});
