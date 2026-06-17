import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { createStore } from 'solid-js/store';
import { fireEvent } from '@testing-library/dom';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
// Lightweight A2 pane stub — never boots a real PTY/xterm. Plain DOM node
// (no JSX in a hoisted factory); path is relative to THIS test file.
// MUST read `p.id` like the real component does: Solid JSX props are lazy
// getters, so a prop expression that throws only surfaces when accessed —
// a mock that ignores `id` masks render-time crashes in the leaf branch.
vi.mock('../../pane/PaneComponent', () => ({
  default: (p: { id: string; index?: number }) => {
    const d = document.createElement('div');
    d.setAttribute('data-testid', 'pane');
    d.setAttribute('data-mock-pane-id', String(p.id));
    d.setAttribute('data-idx', String(p.index ?? 1));
    return d;
  },
}));

const keymap = vi.hoisted(() => ({ dispatchKey: vi.fn() }));
vi.mock('../keymap', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../keymap')>();
  keymap.dispatchKey.mockImplementation(actual.dispatchKey);
  return { dispatchKey: keymap.dispatchKey };
});

import {
  type GridStore,
  type TreeNode,
  collectLeaves,
  makePane,
  makeSplit,
} from '../tree';
import SplitNodeView from '../SplitNode';
import GridRoot, { minGridSize, type GridController } from '../GridRoot';

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

const FOCUS_SEL = '.grid-pane-leaf--focused';
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

  it('sizes the inner tile to the visible grid container, not the window', () => {
    const originalRect = HTMLElement.prototype.getBoundingClientRect;
    const originalInnerWidth = window.innerWidth;
    const originalInnerHeight = window.innerHeight;
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 1200,
    });
    Object.defineProperty(window, 'innerHeight', {
      configurable: true,
      value: 900,
    });
    HTMLElement.prototype.getBoundingClientRect = function () {
      if ((this as HTMLElement).classList?.contains('grid-root')) {
        return {
          x: 0,
          y: 0,
          width: 720,
          height: 480,
          top: 0,
          left: 0,
          right: 720,
          bottom: 480,
          toJSON: () => ({}),
        } as DOMRect;
      }
      return originalRect.call(this);
    };

    try {
      const el = mount(() => <GridRoot />);
      const gr = el.querySelector('.grid-root') as HTMLElement;
      const tile = gr.firstElementChild as HTMLElement;
      expect(tile.style.width).toBe('720px');
      expect(tile.style.height).toBe('480px');
      expect(el.querySelector('[aria-label="Pane menu"]')).toBeTruthy();
    } finally {
      HTMLElement.prototype.getBoundingClientRect = originalRect;
      Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        value: originalInnerWidth,
      });
      Object.defineProperty(window, 'innerHeight', {
        configurable: true,
        value: originalInnerHeight,
      });
    }
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

  it('inactive grid ignores keydown — dispatchKey not called', () => {
    keymap.dispatchKey.mockClear();
    mount(() => <GridRoot active={() => false} />);
    fireEvent.keyDown(window, {
      code: 'Backslash',
      key: '\\',
      metaKey: true,
    });
    expect(keymap.dispatchKey).not.toHaveBeenCalled();
  });

  it('active grid still handles keydown when active prop returns true', () => {
    keymap.dispatchKey.mockClear();
    const el = mount(() => <GridRoot active={() => true} />);
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(1);
    fireEvent.keyDown(window, {
      code: 'Backslash',
      key: '\\',
      metaKey: true,
    });
    expect(keymap.dispatchKey).toHaveBeenCalled();
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(2);
  });

  it('⌘G calls onCycleLayout with the next preset and preserves pane ids', () => {
    let active: 'fanout' | 'pipeline' | 'swarm' | 'watchers' | 'custom' =
      'custom';
    const onLayoutChange = vi.fn((next: typeof active) => {
      active = next;
    });
    const el = mount(() => (
      <GridRoot
        activeLayout={() => active}
        onLayoutChange={onLayoutChange}
      />
    ));
    // Grow to 3 panes manually so the preset transform has work to do.
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(3);
    // Manual edits flagged the layout as custom.
    expect(onLayoutChange).toHaveBeenLastCalledWith('custom');

    onLayoutChange.mockClear();
    fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
    expect(onLayoutChange).toHaveBeenLastCalledWith('fanout');
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(3);

    fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
    expect(onLayoutChange).toHaveBeenLastCalledWith('pipeline');
    fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
    expect(onLayoutChange).toHaveBeenLastCalledWith('swarm');
    fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
    expect(onLayoutChange).toHaveBeenLastCalledWith('watchers');
    fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
    expect(onLayoutChange).toHaveBeenLastCalledWith('fanout');
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(3);
  });

  it('manual structural edits after a preset flip activeLayout back to custom', () => {
    let active: 'fanout' | 'pipeline' | 'swarm' | 'watchers' | 'custom' =
      'custom';
    const onLayoutChange = vi.fn((next: typeof active) => {
      active = next;
    });
    mount(() => (
      <GridRoot
        activeLayout={() => active}
        onLayoutChange={onLayoutChange}
      />
    ));
    // Start with one pane → split → cycle to pipeline → manual split.
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
    expect(active).toBe('fanout');
    fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
    expect(active).toBe('pipeline');
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    expect(active).toBe('custom');
  });
});

describe('GridRoot — pane drag rearrange', () => {
  function stubPointerCapture(el: Element) {
    const h = el as HTMLElement;
    h.setPointerCapture ??= () => {};
    h.releasePointerCapture ??= () => {};
  }

  function dragHeader(
    grab: HTMLElement,
    moves: { x: number; y: number }[],
  ) {
    stubPointerCapture(grab);
    grab.dispatchEvent(
      new PointerEvent('pointerdown', {
        bubbles: true,
        button: 0,
        clientX: moves[0].x,
        clientY: moves[0].y,
        pointerId: 1,
      }),
    );
    for (const m of moves.slice(1, -1)) {
      window.dispatchEvent(
        new PointerEvent('pointermove', {
          bubbles: true,
          clientX: m.x,
          clientY: m.y,
          pointerId: 1,
        }),
      );
    }
    const last = moves[moves.length - 1];
    window.dispatchEvent(
      new PointerEvent('pointerup', {
        bubbles: true,
        clientX: last.x,
        clientY: last.y,
        pointerId: 1,
      }),
    );
  }

  it('header drag over another pane center swaps ids and syncs once', () => {
    let ctrl: GridController | undefined;
    const el = mount(() => (
      <GridRoot controllerRef={(c) => { ctrl = c; }} />
    ));
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(3);

    const before = collectLeaves(ctrl!.snapshot().root);
    const dragId = before[0].id;
    const targetId = before[1].id;

    const dragPane = el.querySelector(
      `[data-pane-id="${dragId}"]`,
    ) as HTMLElement;
    const targetPane = el.querySelector(
      `[data-pane-id="${targetId}"]`,
    ) as HTMLElement;
    dragPane.getBoundingClientRect = () =>
      ({
        x: 0,
        y: 0,
        width: 400,
        height: 300,
        top: 0,
        left: 0,
        right: 400,
        bottom: 300,
        toJSON: () => ({}),
      }) as DOMRect;
    targetPane.getBoundingClientRect = () =>
      ({
        x: 400,
        y: 0,
        width: 400,
        height: 300,
        top: 0,
        left: 400,
        right: 800,
        bottom: 300,
        toJSON: () => ({}),
      }) as DOMRect;
    const dragRect = dragPane.getBoundingClientRect();
    const targetRect = targetPane.getBoundingClientRect();
    const grab = dragPane.querySelector(
      '[data-pane-header-grab]',
    ) as HTMLElement;

    h.invoke.mockClear();
    dragHeader(grab, [
      { x: dragRect.left + 10, y: dragRect.top + 10 },
      { x: dragRect.left + 20, y: dragRect.top + 10 },
      {
        x: targetRect.left + targetRect.width / 2,
        y: targetRect.top + targetRect.height / 2,
      },
    ]);

    const after = collectLeaves(ctrl!.snapshot().root);
    expect(after[0].id).toBe(targetId);
    expect(after[1].id).toBe(dragId);
    expect(ctrl!.snapshot().focusedId).toBe(dragId);
    expect(h.invoke).toHaveBeenCalledTimes(1);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());

    // The DOM must reflect the swap, not just the store: each leaf wrapper
    // re-rendered its PaneComponent keyed by the (swapped) pane id.
    for (const wrap of el.querySelectorAll('[data-pane-id]')) {
      const inner = wrap.querySelector('[data-mock-pane-id]');
      expect(inner?.getAttribute('data-mock-pane-id')).toBe(
        wrap.getAttribute('data-pane-id'),
      );
    }
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
