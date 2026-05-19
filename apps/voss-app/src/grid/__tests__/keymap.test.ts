import { describe, it, expect, vi, beforeEach } from 'vitest';

const ops = vi.hoisted(() => ({
  splitFocused: vi.fn(),
  forkFocused: vi.fn(),
  equalizeAll: vi.fn(),
  focusByIndex: vi.fn(),
  cycleFocus: vi.fn(),
  focusByDirection: vi.fn(),
  resizeByKeyboard: vi.fn(),
}));
vi.mock('../operations', () => ({
  splitFocused: ops.splitFocused,
  forkFocused: ops.forkFocused,
  equalizeAll: ops.equalizeAll,
}));
vi.mock('../focus', () => ({
  focusByIndex: ops.focusByIndex,
  cycleFocus: ops.cycleFocus,
  focusByDirection: ops.focusByDirection,
}));
vi.mock('../resize', () => ({ resizeByKeyboard: ops.resizeByKeyboard }));

import { dispatchKey } from '../keymap';
import type { GridStore } from '../tree';

const store = { root: { kind: 'pane' }, focusedId: 'x' } as unknown as GridStore;
const onClose = vi.fn();

function key(init: KeyboardEventInit): KeyboardEvent {
  const e = new KeyboardEvent('keydown', init);
  vi.spyOn(e, 'preventDefault');
  return e;
}
const D = (e: KeyboardEvent) => dispatchKey(store, e, 800, 600, 8, 16, onClose);

describe('keymap dispatch (GRD-02/03/04)', () => {
  beforeEach(() => {
    Object.values(ops).forEach((f) => f.mockClear());
    onClose.mockClear();
  });

  it('⌘D → split right (H); ⌘⇧D → split below (V) — Warp parity', () => {
    const a = key({ code: 'KeyD', key: 'd', metaKey: true });
    expect(D(a)).toBe(true);
    expect(ops.splitFocused).toHaveBeenCalledWith(store, 'H', expect.anything());
    expect(a.preventDefault).toHaveBeenCalled();

    const b = key({ code: 'KeyD', key: 'd', metaKey: true, shiftKey: true });
    expect(D(b)).toBe(true);
    expect(ops.splitFocused).toHaveBeenCalledWith(store, 'V', expect.anything());
  });

  it('⌘\\ / ⌘⇧\\ stay split aliases; ⌘= equalize; ⌘W → onCloseRequest', () => {
    expect(D(key({ code: 'Backslash', key: '\\', metaKey: true }))).toBe(true);
    expect(ops.splitFocused).toHaveBeenCalledWith(store, 'H', expect.anything());
    expect(
      D(key({ code: 'Backslash', key: '|', metaKey: true, shiftKey: true })),
    ).toBe(true);
    expect(ops.splitFocused).toHaveBeenCalledWith(store, 'V', expect.anything());
    expect(D(key({ code: 'Equal', key: '=', metaKey: true }))).toBe(true);
    expect(ops.equalizeAll).toHaveBeenCalledWith(store);
    expect(D(key({ code: 'KeyW', key: 'w', metaKey: true }))).toBe(true);
    expect(onClose).toHaveBeenCalledWith(store);
  });

  it('⌘1–⌘9 focusByIndex; ⌘0 unmatched; ⌘[ / ⌘] cycle', () => {
    expect(D(key({ key: '3', code: 'Digit3', metaKey: true }))).toBe(true);
    expect(ops.focusByIndex).toHaveBeenCalledWith(store, 3);
    const z = key({ key: '0', code: 'Digit0', metaKey: true });
    expect(D(z)).toBe(false);
    expect(z.preventDefault).not.toHaveBeenCalled();
    expect(D(key({ key: '[', code: 'BracketLeft', metaKey: true }))).toBe(true);
    expect(ops.cycleFocus).toHaveBeenCalledWith(store, 'prev');
    expect(D(key({ key: ']', code: 'BracketRight', metaKey: true }))).toBe(true);
    expect(ops.cycleFocus).toHaveBeenCalledWith(store, 'next');
  });

  it('⌘⌥arrow → focusByDirection; ⌘⌥⇧arrow → resizeByKeyboard', () => {
    expect(
      D(key({ code: 'ArrowRight', key: 'ArrowRight', metaKey: true, altKey: true })),
    ).toBe(true);
    expect(ops.focusByDirection).toHaveBeenCalledWith(store, 'right', 800, 600);
    expect(
      D(
        key({
          code: 'ArrowUp',
          key: 'ArrowUp',
          metaKey: true,
          altKey: true,
          shiftKey: true,
        }),
      ),
    ).toBe(true);
    expect(ops.resizeByKeyboard).toHaveBeenCalledWith(store, 'up', 800, 600, 8, 16);
  });

  it('unmatched chord (and non-⌘ key) returns false WITHOUT preventDefault', () => {
    const plain = key({ key: 'a', code: 'KeyA' }); // no meta → PTY pass-through
    expect(D(plain)).toBe(false);
    expect(plain.preventDefault).not.toHaveBeenCalled();
    const lone = key({ key: 'Meta', code: 'MetaLeft', metaKey: true, altKey: true });
    expect(D(lone)).toBe(false);
    expect(lone.preventDefault).not.toHaveBeenCalled();
  });
});
