import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { createStore } from 'solid-js/store';
import { fireEvent } from '@testing-library/dom';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
// Lightweight A2 pane stub — never boots a real PTY/xterm. Plain DOM node
// (no JSX in a hoisted factory); path is relative to THIS test file.
vi.mock('../../pane/PaneComponent', () => ({
  default: (p: { index?: number }) => {
    const d = document.createElement('div');
    d.setAttribute('data-testid', 'pane');
    d.setAttribute('data-idx', String(p.index ?? 1));
    return d;
  },
}));

import {
  type GridStore,
  type TreeNode,
  makePane,
  makeSplit,
} from '../tree';
import SplitNodeView from '../SplitNode';
import GridRoot, { minGridSize } from '../GridRoot';

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

const FOCUS_SEL = '[class*="inset_0_0_0_1px"]';
const dims = () => ({ winW: 1024, winH: 768, cw: 8, ch: 20 });

describe('SplitNode + DragHandle render (GRD-01, GRD-07)', () => {
  it('2×2 tree mounts exactly 4 panes; exactly one inset-shadow focus', () => {
    const [a, c, b, d] = [makePane(), makePane(), makePane(), makePane()];
    const [store, setStore] = createStore<GridStore>({
      root: makeSplit('H', makeSplit('V', a, c), makeSplit('V', b, d)),
      focusedId: a.id,
    });
    const el = mount(() => (
      <SplitNodeView
        node={store.root}
        store={store}
        setStore={setStore}
        path=""
        dims={dims}
      />
    ));
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(4);
    const focused = el.querySelectorAll(FOCUS_SEL);
    expect(focused).toHaveLength(1);
    expect(focused[0].getAttribute('data-pane-id')).toBe(a.id);
  });

  it('clicking an unfocused pane focuses it (focusByClick); shadow moves', () => {
    const [a, b] = [makePane(), makePane()];
    const [store, setStore] = createStore<GridStore>({
      root: makeSplit('H', a, b),
      focusedId: a.id,
    });
    const el = mount(() => (
      <SplitNodeView
        node={store.root}
        store={store}
        setStore={setStore}
        path=""
        dims={dims}
      />
    ));
    h.invoke.mockClear();
    fireEvent.click(el.querySelector(`[data-pane-id="${b.id}"]`)!);
    expect(store.focusedId).toBe(b.id);
    const focused = el.querySelectorAll(FOCUS_SEL);
    expect(focused).toHaveLength(1);
    expect(focused[0].getAttribute('data-pane-id')).toBe(b.id);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });

  it('a 6-pane asymmetric tree renders without error', () => {
    const p = () => makePane();
    const root = makeSplit(
      'H',
      makeSplit('V', p(), makeSplit('H', p(), p())),
      makeSplit('V', makeSplit('H', p(), p()), p()),
    );
    const [store, setStore] = createStore<GridStore>({
      root,
      focusedId: 'none',
    });
    const el = mount(() => (
      <SplitNodeView
        node={store.root}
        store={store}
        setStore={setStore}
        path=""
        dims={dims}
      />
    ));
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(6);
    expect(el.innerHTML).not.toMatch(/rounded|transition/);
  });
});

describe('GridRoot — container + keymap mount (GRD-01, GRD-03)', () => {
  it('renders .grid-root.bg-bg-0 with one default pane', () => {
    const el = mount(() => <GridRoot />);
    const gr = el.querySelector('.grid-root');
    expect(gr).toBeTruthy();
    expect(gr!.className).toContain('bg-bg-0');
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(1);
  });

  it('⌘\\ keydown reaches dispatchKey → splits to 2 panes', () => {
    const el = mount(() => <GridRoot />);
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(1);
    fireEvent.keyDown(window, {
      code: 'Backslash',
      key: '\\',
      metaKey: true,
    });
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(2);
  });
});

describe('GridRoot — GRD-05 window-shrink floor', () => {
  it('minGridSize keeps every pane ≥ 20×5 in a narrow window', () => {
    const [a, c, b, d] = [makePane(), makePane(), makePane(), makePane()];
    const root: TreeNode = makeSplit(
      'H',
      makeSplit('V', a, c),
      makeSplit('V', b, d),
    );
    const cw = 8;
    const ch = 20;
    const m = minGridSize(root, cw, ch);
    expect(m).toEqual({ w: 320, h: 244 });
    // Effective tile size clamps UP to the floor, never below the window.
    const effW = Math.max(100, m.w);
    const effH = Math.max(100, m.h);
    const leafW = 0.5 * effW; // each 2×2 leaf gets half each axis
    const leafH = 0.5 * effH;
    expect(Math.floor(leafW / cw)).toBeGreaterThanOrEqual(20);
    expect(Math.floor((leafH - 22) / ch)).toBeGreaterThanOrEqual(5);
  });
});
