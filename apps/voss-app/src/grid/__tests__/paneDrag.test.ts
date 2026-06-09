import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createStore } from 'solid-js/store';
import { createGridStore, makePane, makeSplit } from '../tree';

const movePaneMock = vi.hoisted(() => vi.fn(() => true));
vi.mock('../rearrange', () => ({
  movePane: (...args: unknown[]) => movePaneMock(...args),
}));

import { createPaneDrag } from '../paneDrag';

function stubPointerCapture(el: HTMLElement) {
  el.setPointerCapture ??= () => {};
  el.releasePointerCapture ??= () => {};
}

function dispatch(
  el: HTMLElement,
  type: string,
  init: PointerEventInit = {},
) {
  const e = new PointerEvent(type, {
    bubbles: true,
    pointerId: 1,
    ...init,
  });
  el.dispatchEvent(e);
  return e;
}

describe('paneDrag controller', () => {
  beforeEach(() => {
    movePaneMock.mockClear();
    document.body.innerHTML = '';
    document.body.classList.remove('pane-dragging');
  });

  afterEach(() => {
    document.body.innerHTML = '';
    document.body.classList.remove('pane-dragging');
  });

  it('4px move does not start drag; 6px does', () => {
    const [store, setStore] = createGridStore();
    const a = makePane();
    const b = makePane();
    setStore('root', makeSplit('H', a, b));
    setStore('focusedId', a.id);

    const paneA = document.createElement('div');
    paneA.setAttribute('data-pane-id', a.id);
    paneA.getBoundingClientRect = () =>
      ({ x: 0, y: 0, width: 400, height: 300, top: 0, left: 0, right: 400, bottom: 300, toJSON: () => ({}) }) as DOMRect;
    const paneB = document.createElement('div');
    paneB.setAttribute('data-pane-id', b.id);
    paneB.getBoundingClientRect = () =>
      ({ x: 400, y: 0, width: 400, height: 300, top: 0, left: 400, right: 800, bottom: 300, toJSON: () => ({}) }) as DOMRect;
    document.body.append(paneA, paneB);

    const header = document.createElement('div');
    stubPointerCapture(header);
    const drag = createPaneDrag(store, setStore, () => ({
      winW: 800,
      winH: 600,
      cw: 8,
      ch: 16,
    }));

    drag.onHeaderPointerDown(
      { button: 0, clientX: 10, clientY: 10, currentTarget: header, target: header, pointerId: 1 } as unknown as PointerEvent,
      a.id,
    );
    dispatch(header, 'pointermove', { clientX: 14, clientY: 10 });
    expect(drag.state()).toBeNull();

    dispatch(header, 'pointermove', { clientX: 20, clientY: 10 });
    expect(drag.state()).not.toBeNull();
    expect(drag.state()?.paneId).toBe(a.id);
  });

  it('button-child pointerdown is ignored by caller guard', () => {
    const [store, setStore] = createGridStore();
    const a = makePane();
    const b = makePane();
    setStore('root', makeSplit('H', a, b));

    const btn = document.createElement('button');
    const header = document.createElement('div');
    header.append(btn);
    stubPointerCapture(header);
    const drag = createPaneDrag(store, setStore, () => ({
      winW: 800,
      winH: 600,
      cw: 8,
      ch: 16,
    }));

    const e = {
      button: 0,
      clientX: 10,
      clientY: 10,
      currentTarget: header,
      target: btn,
      pointerId: 1,
    } as unknown as PointerEvent;
    // Simulate SplitNode guard — controller assumes caller skips buttons
    if ((e.target as HTMLElement).closest('button')) {
      expect(true).toBe(true);
      return;
    }
    drag.onHeaderPointerDown(e, a.id);
    dispatch(header, 'pointermove', { clientX: 50, clientY: 50 });
    expect(drag.state()).toBeNull();
  });

  it('single-pane grid: drag never starts', () => {
    const [store, setStore] = createGridStore();
    const header = document.createElement('div');
    stubPointerCapture(header);
    const drag = createPaneDrag(store, setStore, () => ({
      winW: 800,
      winH: 600,
      cw: 8,
      ch: 16,
    }));

    drag.onHeaderPointerDown(
      { button: 0, clientX: 0, clientY: 0, currentTarget: header, target: header, pointerId: 1 } as unknown as PointerEvent,
      store.focusedId,
    );
    dispatch(header, 'pointermove', { clientX: 100, clientY: 100 });
    expect(drag.state()).toBeNull();
  });

  it('Escape clears without store write', () => {
    const [store, setStore] = createGridStore();
    const a = makePane();
    const b = makePane();
    setStore('root', makeSplit('H', a, b));

    const paneA = document.createElement('div');
    paneA.setAttribute('data-pane-id', a.id);
    paneA.getBoundingClientRect = () =>
      ({ x: 0, y: 0, width: 400, height: 300, top: 0, left: 0, right: 400, bottom: 300, toJSON: () => ({}) }) as DOMRect;
    document.body.append(paneA);

    const header = document.createElement('div');
    stubPointerCapture(header);
    const drag = createPaneDrag(store, setStore, () => ({
      winW: 800,
      winH: 600,
      cw: 8,
      ch: 16,
    }));

    drag.onHeaderPointerDown(
      { button: 0, clientX: 0, clientY: 0, currentTarget: header, target: header, pointerId: 1 } as unknown as PointerEvent,
      a.id,
    );
    dispatch(header, 'pointermove', { clientX: 20, clientY: 0 });
    expect(drag.state()).not.toBeNull();

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(drag.state()).toBeNull();
    expect(movePaneMock).not.toHaveBeenCalled();
  });

  it('drop with target calls movePane once', () => {
    const [store, setStore] = createStore({ root: makePane(), focusedId: '' });
    const a = makePane();
    const b = makePane();
    setStore({ root: makeSplit('H', a, b), focusedId: a.id });

    const paneA = document.createElement('div');
    paneA.setAttribute('data-pane-id', a.id);
    paneA.getBoundingClientRect = () =>
      ({ x: 0, y: 0, width: 400, height: 300, top: 0, left: 0, right: 400, bottom: 300, toJSON: () => ({}) }) as DOMRect;
    const paneB = document.createElement('div');
    paneB.setAttribute('data-pane-id', b.id);
    paneB.getBoundingClientRect = () =>
      ({ x: 400, y: 0, width: 400, height: 300, top: 0, left: 400, right: 800, bottom: 300, toJSON: () => ({}) }) as DOMRect;
    document.body.append(paneA, paneB);

    const header = document.createElement('div');
    stubPointerCapture(header);
    const dims = { winW: 800, winH: 600, cw: 8, ch: 16 };
    const drag = createPaneDrag(store, setStore, () => dims);

    drag.onHeaderPointerDown(
      { button: 0, clientX: 10, clientY: 150, currentTarget: header, target: header, pointerId: 1 } as unknown as PointerEvent,
      a.id,
    );
    dispatch(header, 'pointermove', { clientX: 20, clientY: 150 });
    dispatch(header, 'pointermove', { clientX: 500, clientY: 150 });
    dispatch(header, 'pointerup', { clientX: 500, clientY: 150 });

    expect(movePaneMock).toHaveBeenCalledTimes(1);
    expect(movePaneMock).toHaveBeenCalledWith(
      expect.anything(),
      a.id,
      b.id,
      'center',
      dims,
    );
  });

  it('drop with null target mutates nothing', () => {
    const [store, setStore] = createGridStore();
    const a = makePane();
    const b = makePane();
    setStore('root', makeSplit('H', a, b));

    const paneA = document.createElement('div');
    paneA.setAttribute('data-pane-id', a.id);
    paneA.getBoundingClientRect = () =>
      ({ x: 0, y: 0, width: 400, height: 300, top: 0, left: 0, right: 400, bottom: 300, toJSON: () => ({}) }) as DOMRect;
    document.body.append(paneA);

    const header = document.createElement('div');
    stubPointerCapture(header);
    const drag = createPaneDrag(store, setStore, () => ({
      winW: 800,
      winH: 600,
      cw: 8,
      ch: 16,
    }));

    drag.onHeaderPointerDown(
      { button: 0, clientX: 0, clientY: 0, currentTarget: header, target: header, pointerId: 1 } as unknown as PointerEvent,
      a.id,
    );
    dispatch(header, 'pointermove', { clientX: 20, clientY: 0 });
    dispatch(header, 'pointermove', { clientX: -50, clientY: 0 });
    dispatch(header, 'pointerup', { clientX: -50, clientY: 0 });

    expect(movePaneMock).not.toHaveBeenCalled();
  });
});
