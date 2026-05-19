import { describe, it, expect, vi, beforeEach } from 'vitest';

// --- Mock @tauri-apps/api/core for the sync.ts bridge tests -----------------
const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  createGridStore,
  makePane,
  makeSplit,
  recomputeIndices,
  equalizeRatios,
  findLeaf,
  collectLeaves,
  type TreeNode,
} from '../tree';
import { markStructuralChange, markDragMove, markDragSettled } from '../sync';

// 2×2 tree (3 splits): V[ H[a,b], H[c,d] ]
function build2x2(): TreeNode {
  const a = makePane();
  const b = makePane();
  const c = makePane();
  const d = makePane();
  return makeSplit('V', makeSplit('H', a, b), makeSplit('H', c, d));
}

describe('tree model (GRD-01)', () => {
  it('single PaneLeaf root has index 1 after recomputeIndices', () => {
    const root = makePane();
    root.index = 99;
    recomputeIndices(root);
    expect(root.index).toBe(1);
  });

  it('createGridStore: root is one default pane, focusedId = its id', () => {
    const [g] = createGridStore();
    expect(g.root.kind).toBe('pane');
    if (g.root.kind === 'pane') {
      expect(g.focusedId).toBe(g.root.id);
      expect(g.root.index).toBe(1);
    }
  });

  it('makeSplit always sets ratio === 0.5', () => {
    const s = makeSplit('H', makePane(), makePane());
    expect(s.ratio).toBe(0.5);
  });

  it('2×2 tree → inorder indices [1,2,3,4], no gaps', () => {
    const root = build2x2();
    recomputeIndices(root);
    expect(collectLeaves(root).map((l) => l.index)).toEqual([1, 2, 3, 4]);
  });

  it('removing the index-2 leaf renumbers contiguously 1..3 (no sparse)', () => {
    // root = V[ H[a,b], H[c,d] ]; drop b → V[ a, H[c,d] ]
    const a = makePane();
    const c = makePane();
    const d = makePane();
    const root: TreeNode = makeSplit('V', a, makeSplit('H', c, d));
    recomputeIndices(root);
    expect(collectLeaves(root).map((l) => l.index)).toEqual([1, 2, 3]);
  });

  it('≥6-pane asymmetric tree indexes inorder with no gaps', () => {
    // V[ H[1, V[2,3]], H[V[4,5], 6] ]
    const root: TreeNode = makeSplit(
      'V',
      makeSplit('H', makePane(), makeSplit('V', makePane(), makePane())),
      makeSplit('H', makeSplit('V', makePane(), makePane()), makePane()),
    );
    recomputeIndices(root);
    const idx = collectLeaves(root).map((l) => l.index);
    expect(idx).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it('equalizeRatios sets every SplitNode.ratio to 0.5 at all depths', () => {
    const root = build2x2() as Extract<TreeNode, { kind: 'split' }>;
    root.ratio = 0.2;
    (root.left as Extract<TreeNode, { kind: 'split' }>).ratio = 0.9;
    (root.right as Extract<TreeNode, { kind: 'split' }>).ratio = 0.1;
    equalizeRatios(root);
    const ratios: number[] = [];
    const walk = (n: TreeNode) => {
      if (n.kind === 'split') {
        ratios.push(n.ratio);
        walk(n.left);
        walk(n.right);
      }
    };
    walk(root);
    expect(ratios.every((r) => r === 0.5)).toBe(true);
    expect(ratios.length).toBe(3);
  });

  it('findLeaf locates a leaf by id; collectLeaves is inorder', () => {
    const root = build2x2();
    const leaves = collectLeaves(root);
    expect(leaves).toHaveLength(4);
    const target = leaves[2];
    expect(findLeaf(root, target.id)).toBe(target);
    expect(findLeaf(root, 'nope')).toBeUndefined();
  });
});

describe('sync.ts Solid→Rust bridge (GRD-08)', () => {
  beforeEach(() => h.invoke.mockClear());

  const state = () => {
    const [g] = createGridStore();
    return g;
  };

  it('markStructuralChange triggers exactly one invoke(sync_grid) synchronously', () => {
    markStructuralChange(state());
    expect(h.invoke).toHaveBeenCalledTimes(1);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });

  it('N drag-move calls + one markDragSettled → exactly one invoke total', () => {
    const g = state();
    for (let i = 0; i < 10; i++) markDragMove(g);
    expect(h.invoke).toHaveBeenCalledTimes(0); // coalesced — no sync during drag
    markDragSettled(g);
    expect(h.invoke).toHaveBeenCalledTimes(1);
  });

  it('payload key set is { newState: { root, focusedId } }', () => {
    markStructuralChange(state());
    const [, payload] = h.invoke.mock.calls[0];
    expect(Object.keys(payload)).toEqual(['newState']);
    expect(Object.keys(payload.newState).sort()).toEqual(
      ['focusedId', 'root'].sort(),
    );
  });
});
