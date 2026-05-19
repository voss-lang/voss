import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  type GridStore,
  type TreeNode,
  type SplitNode,
  makePane,
  makeSplit,
  collectLeaves,
} from '../tree';
import {
  computePaneRects,
  paneColsRows,
  wouldViolateFloor,
  simulateSplitViolates,
} from '../geometry';
import {
  splitFocused,
  forkFocused,
  closeFocused,
  equalizeAll,
} from '../operations';

const CW = 8;
const CH = 16;
// Window exactly at floor for ONE pane: 20 cols wide, 5 rows + 22px header.
const FLOOR_W = 20 * CW; // 160
const FLOOR_H = 5 * CH + 22; // 102

function store(root: TreeNode, focusedId: string): GridStore {
  return { root, focusedId };
}

describe('geometry — 20×5 floor (GRD-05)', () => {
  it('computePaneRects: single pane tiles the full area', () => {
    const p = makePane();
    const rects = computePaneRects(p, 800, 600);
    expect(rects.get(p.id)).toEqual({ x: 0, y: 0, w: 800, h: 600 });
  });

  it('a pane exactly 20 cols × 5 rows does NOT violate the floor', () => {
    const p = makePane();
    expect(wouldViolateFloor(p, FLOOR_W, FLOOR_H, CW, CH)).toBe(false);
    const { cols, rows } = paneColsRows(
      computePaneRects(p, FLOOR_W, FLOOR_H).get(p.id)!,
      CW,
      CH,
    );
    expect(cols).toBe(20);
    expect(rows).toBe(5);
  });

  it('wouldViolateFloor true when a leaf is below floor', () => {
    const root = makeSplit('H', makePane(), makePane());
    // 25 cols total → each child ~12 cols < 20 → violates
    expect(wouldViolateFloor(root, 25 * CW, FLOOR_H, CW, CH)).toBe(true);
  });

  it('simulateSplitViolates: H-splitting a 30-col pane violates (child ~15 cols)', () => {
    const p = makePane();
    const s = store(p, p.id);
    expect(
      simulateSplitViolates(s.root, s.focusedId, 'H', 30 * CW, 600, CW, CH),
    ).toBe(true);
    // wide window → same split is fine
    expect(
      simulateSplitViolates(s.root, s.focusedId, 'H', 100 * CW, 600, CW, CH),
    ).toBe(false);
  });
});

describe('operations — split/fork/close/equalize (GRD-02, D-04)', () => {
  beforeEach(() => h.invoke.mockClear());

  it('splitFocused("H") makes a 50/50 right sibling, recomputes indices, syncs', () => {
    const p = makePane();
    const s = store(p, p.id);
    splitFocused(s, 'H');
    expect(s.root.kind).toBe('split');
    const root = s.root as SplitNode;
    expect(root.orientation).toBe('H');
    expect(root.ratio).toBe(0.5);
    expect(root.left.kind).toBe('pane');
    expect((root.left as { id: string }).id).toBe(p.id); // old leaf = left
    expect(s.focusedId).toBe((root.right as { id: string }).id); // new = right, focused
    expect(collectLeaves(s.root).map((l) => l.index)).toEqual([1, 2]);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });

  it('splitFocused("V") makes a vertical (stacked) sibling', () => {
    const p = makePane();
    const s = store(p, p.id);
    splitFocused(s, 'V');
    expect((s.root as SplitNode).orientation).toBe('V');
  });

  it('forkFocused inherits cwd+shell with a fresh distinct id', () => {
    const p = makePane({ cwd: '/work/voss', shell: 'zsh' });
    const s = store(p, p.id);
    forkFocused(s);
    const leaves = collectLeaves(s.root);
    const child = leaves.find((l) => l.id !== p.id)!;
    expect(child.cwd).toBe('/work/voss');
    expect(child.shell).toBe('zsh');
    expect(child.id).not.toBe(p.id);
  });

  it('under-floor split is a silent no-op: tree unchanged, no sync', () => {
    const p = makePane();
    const s = store(p, p.id);
    const before = JSON.stringify(s);
    splitFocused(s, 'H', { winW: 30 * CW, winH: 600, cw: CW, ch: CH });
    expect(JSON.stringify(s)).toBe(before); // deep-equal unchanged
    expect(h.invoke).not.toHaveBeenCalled();
  });

  it('closeFocused: sibling subtree expands and receives focus', () => {
    // V[ a , H[b,c] ]; close a → root becomes H[b,c], focus first leaf of it
    const a = makePane();
    const b = makePane();
    const c = makePane();
    const s = store(makeSplit('V', a, makeSplit('H', b, c)), a.id);
    closeFocused(s);
    expect(s.root.kind).toBe('split');
    expect((s.root as SplitNode).orientation).toBe('H');
    expect(collectLeaves(s.root).map((l) => l.id)).toEqual([b.id, c.id]);
    expect(s.focusedId).toBe(b.id); // first leaf of expanded sibling
    expect(collectLeaves(s.root).map((l) => l.index)).toEqual([1, 2]);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });

  it('closing the last pane respawns exactly one fresh default leaf focused (D-04)', () => {
    const p = makePane();
    const s = store(p, p.id);
    closeFocused(s);
    expect(s.root.kind).toBe('pane');
    const leaves = collectLeaves(s.root);
    expect(leaves).toHaveLength(1);
    expect(leaves[0].id).not.toBe(p.id); // fresh pane
    expect(s.focusedId).toBe(leaves[0].id);
    expect(leaves[0].index).toBe(1);
  });

  it('closeFocused deep target: spine rebuilt, indices contiguous', () => {
    // V[ H[a,b], H[c,d] ] close c → V[ H[a,b], d ]
    const a = makePane();
    const b = makePane();
    const c = makePane();
    const d = makePane();
    const s = store(
      makeSplit('V', makeSplit('H', a, b), makeSplit('H', c, d)),
      c.id,
    );
    closeFocused(s);
    expect(collectLeaves(s.root).map((l) => l.id)).toEqual([a.id, b.id, d.id]);
    expect(collectLeaves(s.root).map((l) => l.index)).toEqual([1, 2, 3]);
  });

  it('equalizeAll balances ratios so every leaf is equal-area (Warp) + syncs', () => {
    // V[ H[p,p], p ] — 3 leaves. Equal area ⇒ root V ratio = 2/3 (left holds
    // 2 of 3 leaves), inner H ratio = 0.5.
    const root = makeSplit(
      'V',
      makeSplit('H', makePane(), makePane()),
      makePane(),
    );
    (root as SplitNode).ratio = 0.2;
    ((root as SplitNode).left as SplitNode).ratio = 0.85;
    const s = store(root, collectLeaves(root)[0].id);
    equalizeAll(s);
    expect((s.root as SplitNode).ratio).toBeCloseTo(2 / 3, 5);
    expect(((s.root as SplitNode).left as SplitNode).ratio).toBe(0.5);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });

  it('repeated splitFocused tiles N panes equal (no geometric shrink)', () => {
    // 5 ⌘D-style H splits → 6 equal columns; every leaf ≈ 1/6 width at a
    // wide window (the "only 4 max" bug = missing auto-equalize).
    const p = makePane();
    const s = store(p, p.id);
    for (let i = 0; i < 5; i++) splitFocused(s, 'H');
    const rects = computePaneRects(s.root, 6000, 800);
    const widths = [...rects.values()].map((r) => r.w);
    const min = Math.min(...widths);
    const max = Math.max(...widths);
    expect(collectLeaves(s.root)).toHaveLength(6);
    expect(max - min).toBeLessThanOrEqual(2); // equal within rounding
  });
});
