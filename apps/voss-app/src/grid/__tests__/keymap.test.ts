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
const onCycleLayout = vi.fn();
const onStructuralEdit = vi.fn();

function key(init: KeyboardEventInit): KeyboardEvent {
  const e = new KeyboardEvent('keydown', init);
  vi.spyOn(e, 'preventDefault');
  return e;
}
const D = (e: KeyboardEvent) =>
  dispatchKey(store, e, 800, 600, 8, 16, onClose, onCycleLayout, onStructuralEdit);

describe('keymap dispatch (GRD-02/03/04)', () => {
  beforeEach(() => {
    Object.values(ops).forEach((f) => f.mockClear());
    onClose.mockClear();
    onCycleLayout.mockClear();
    onStructuralEdit.mockClear();
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

  it('⌘G → onCycleLayout(store) and preventDefault; ⌘⇧G unmatched', () => {
    const g = key({ code: 'KeyG', key: 'g', metaKey: true });
    expect(D(g)).toBe(true);
    expect(onCycleLayout).toHaveBeenCalledTimes(1);
    expect(onCycleLayout).toHaveBeenCalledWith(store);
    expect(g.preventDefault).toHaveBeenCalled();

    // ⌘⇧G is reserved for future use — keymap leaves it for the PTY.
    const shifted = key({
      code: 'KeyG',
      key: 'G',
      metaKey: true,
      shiftKey: true,
    });
    expect(D(shifted)).toBe(false);
    expect(onCycleLayout).toHaveBeenCalledTimes(1);
    expect(shifted.preventDefault).not.toHaveBeenCalled();

    // ⌘⌥G is also unmatched (Alt path is reserved for focus/resize arrows).
    const alted = key({
      code: 'KeyG',
      key: 'g',
      metaKey: true,
      altKey: true,
    });
    expect(D(alted)).toBe(false);
    expect(onCycleLayout).toHaveBeenCalledTimes(1);
  });

  it('every structural edit fires onStructuralEdit before the op runs', () => {
    // splitFocused (⌘D)
    D(key({ code: 'KeyD', key: 'd', metaKey: true }));
    // forkFocused — keymap only does split/equalize/close directly today, but
    // ⌘⇧D maps to split V and should still count as structural.
    D(key({ code: 'KeyD', key: 'd', metaKey: true, shiftKey: true }));
    // ⌘W close
    D(key({ code: 'KeyW', key: 'w', metaKey: true }));
    // ⌘= equalize
    D(key({ code: 'Equal', key: '=', metaKey: true }));
    // ⌘⌥⇧→ resize (still structural — changes ratios)
    D(
      key({
        code: 'ArrowRight',
        key: 'ArrowRight',
        metaKey: true,
        altKey: true,
        shiftKey: true,
      }),
    );

    // 5 structural events fired.
    expect(onStructuralEdit).toHaveBeenCalledTimes(5);
    // No layout cycle fired during structural edits.
    expect(onCycleLayout).not.toHaveBeenCalled();
  });

  it('focus-only ops (⌘1, ⌘[, ⌘⌥→) do NOT fire onStructuralEdit', () => {
    D(key({ key: '3', code: 'Digit3', metaKey: true }));
    D(key({ key: '[', code: 'BracketLeft', metaKey: true }));
    D(
      key({
        code: 'ArrowRight',
        key: 'ArrowRight',
        metaKey: true,
        altKey: true,
      }),
    );
    expect(onStructuralEdit).not.toHaveBeenCalled();
  });

  it('⌘G does NOT mark structural — preset cycling preserves all panes', () => {
    D(key({ code: 'KeyG', key: 'g', metaKey: true }));
    expect(onCycleLayout).toHaveBeenCalledTimes(1);
    expect(onStructuralEdit).not.toHaveBeenCalled();
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
