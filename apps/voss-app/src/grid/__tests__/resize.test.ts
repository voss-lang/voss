import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  type GridStore,
  type SplitNode,
  type TreeNode,
  makePane,
  makeSplit,
} from '../tree';
import { markDragSettled } from '../sync';
import {
  resizeByDrag,
  resizeByKeyboard,
  equalizeAllRatios,
  splitPath,
} from '../resize';

function store(root: TreeNode, focusedId: string): GridStore {
  return { root, focusedId };
}

// Cell 8×16, 22px header. Over 400×400 a 2-leaf H split is feasible only for
// ratio ∈ [0.4, 0.6] (floor(50·r) ≥ 20 cols both sides).
const CW = 8;
const CH = 16;
const W = 400;
const Hh = 400;

describe('resize — drag border + 20×5 clamp (GRD-04, GRD-05)', () => {
  beforeEach(() => h.invoke.mockClear());

  it('resizeByDrag clamps a floor-breaching ratio (snaps toward 0.5)', () => {
    const a = makePane();
    const b = makePane();
    const root = makeSplit('H', a, b);
    const s = store(root, a.id);
    resizeByDrag(s, '', 0.95, W, Hh, CW, CH); // "" = root split
    expect((s.root as SplitNode).ratio).toBeCloseTo(0.6, 5);
    // resulting geometry honors the 20-col floor on both sides
    expect(Math.floor((W * (s.root as SplitNode).ratio) / CW)).toBeGreaterThanOrEqual(20);
    expect(Math.floor((W * (1 - (s.root as SplitNode).ratio)) / CW)).toBeGreaterThanOrEqual(20);
  });

  it('resizeByDrag mutates ONLY the target split — siblings byte-identical', () => {
    // V[ H[a,b], H[c,d] ] — drag the root V split; the two child H splits
    // must keep ratio 0.5 exactly.
    const [a, b, c, d] = [makePane(), makePane(), makePane(), makePane()];
    const root = makeSplit('V', makeSplit('H', a, b), makeSplit('H', c, d));
    const s = store(root, a.id);
    resizeByDrag(s, '', 0.6, W, Hh, CW, CH);
    expect((s.root as SplitNode).ratio).toBeCloseTo(0.6, 5);
    expect(((s.root as SplitNode).left as SplitNode).ratio).toBe(0.5);
    expect(((s.root as SplitNode).right as SplitNode).ratio).toBe(0.5);
  });

  it('resizeByDrag does NOT sync per move; markDragSettled syncs once', () => {
    const root = makeSplit('H', makePane(), makePane());
    const s = store(root, (root.left as { id: string }).id);
    resizeByDrag(s, '', 0.55, W, Hh, CW, CH);
    resizeByDrag(s, '', 0.58, W, Hh, CW, CH);
    resizeByDrag(s, '', 0.6, W, Hh, CW, CH);
    expect(h.invoke).not.toHaveBeenCalled(); // coalesced — no per-move sync
    markDragSettled(s);
    expect(h.invoke).toHaveBeenCalledTimes(1);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });
});

describe('resize — keyboard 5% + equalize (GRD-04, GRD-05)', () => {
  beforeEach(() => h.invoke.mockClear());

  it('resizeByKeyboard steps 5% and syncs per step', () => {
    const a = makePane();
    const b = makePane();
    const root = makeSplit('H', a, b);
    const s = store(root, a.id);
    resizeByKeyboard(s, 'right', W, Hh, CW, CH);
    expect((s.root as SplitNode).ratio).toBeCloseTo(0.55, 5);
    expect(h.invoke).toHaveBeenCalledTimes(1);
  });

  it('repeated keyboard resize stops at the floor without overshoot', () => {
    const a = makePane();
    const b = makePane();
    const root = makeSplit('H', a, b);
    const s = store(root, a.id);
    for (let i = 0; i < 12; i++) resizeByKeyboard(s, 'right', W, Hh, CW, CH);
    const r = (s.root as SplitNode).ratio;
    expect(r).toBeLessThanOrEqual(0.6 + 1e-9); // never past the 20-col floor
    expect(Math.floor((W * (1 - r)) / CW)).toBeGreaterThanOrEqual(20);
  });

  it('resizeByKeyboard is a no-op with no bounding split on that axis', () => {
    const p = makePane();
    const s = store(p, p.id); // single pane
    resizeByKeyboard(s, 'right', W, Hh, CW, CH);
    expect(s.root.kind).toBe('pane');
    expect(h.invoke).not.toHaveBeenCalled();
    // V split exists but ⌘⌥⇧→ asks for an H axis → still a no-op
    const root = makeSplit('V', makePane(), makePane());
    const s2 = store(root, (root.left as { id: string }).id);
    resizeByKeyboard(s2, 'right', W, Hh, CW, CH);
    expect((s2.root as SplitNode).ratio).toBe(0.5);
  });

  it('splitPath finds the nearest bounding split of the requested axis', () => {
    // H[ a , V[b,c] ] — b's bounding H split is the root (""); its bounding
    // V split is "R".
    const a = makePane();
    const b = makePane();
    const c = makePane();
    const root = makeSplit('H', a, makeSplit('V', b, c));
    expect(splitPath(root, b.id, 'H')).toBe('');
    expect(splitPath(root, b.id, 'V')).toBe('R');
    expect(splitPath(a, 'no-id', 'H')).toBeNull();
  });

  it('equalizeAllRatios balances to equal-area leaves (Warp) and syncs', () => {
    const root = makeSplit(
      'V',
      makeSplit('H', makePane(), makePane()),
      makePane(),
    );
    (root as SplitNode).ratio = 0.2;
    ((root as SplitNode).left as SplitNode).ratio = 0.85;
    const s = store(root, (((root as SplitNode).left as SplitNode).left as { id: string }).id);
    equalizeAllRatios(s);
    expect((s.root as SplitNode).ratio).toBeCloseTo(2 / 3, 5); // 2 of 3 leaves left
    expect(((s.root as SplitNode).left as SplitNode).ratio).toBe(0.5);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });
});
