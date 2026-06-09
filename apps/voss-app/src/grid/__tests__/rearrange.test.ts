import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createStore, produce } from 'solid-js/store';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  type GridStore,
  type SplitNode,
  type TreeNode,
  makePane,
  makeSplit,
  collectLeaves,
  findLeaf,
} from '../tree';
import { cloneTree } from '../geometry';
import { swapPanes, movePane, simulateMoveViolates } from '../rearrange';

const CW = 8;
const CH = 16;
const FLOOR_W = 20 * CW;
const FLOOR_H = 5 * CH + 22;
const GENEROUS = { winW: 2000, winH: 1200, cw: CW, ch: CH };
const TIGHT = { winW: FLOOR_W, winH: FLOOR_H, cw: CW, ch: CH };

function store(root: TreeNode, focusedId: string): GridStore {
  return { root, focusedId };
}

function pane(id: string, cwd = '', shell = ''): TreeNode {
  return { kind: 'pane', id, cwd, shell, index: 1 };
}

function deepCloneTree(n: TreeNode): TreeNode {
  return cloneTree(n);
}

describe('rearrange — swapPanes', () => {
  it('2-pane H tree: swaps ids/cwd/shell, ratio untouched, indices reassigned', () => {
    const a = makePane({ cwd: '/a', shell: 'zsh' });
    const b = makePane({ cwd: '/b', shell: 'bash' });
    const aId = a.id;
    const bId = b.id;
    const root = makeSplit('H', a, b);
    const origRatio = (root as SplitNode).ratio;

    swapPanes(root, aId, bId);

    const leaves = collectLeaves(root);
    expect(leaves[0].id).toBe(bId);
    expect(leaves[0].cwd).toBe('/b');
    expect(leaves[1].id).toBe(aId);
    expect(leaves[1].cwd).toBe('/a');
    expect((root as SplitNode).ratio).toBe(origRatio);
    expect(leaves.map((l) => l.index)).toEqual([1, 2]);
  });

  it('deep tree: swap across different subtrees', () => {
    const a = makePane({ cwd: 'a' });
    const b = makePane({ cwd: 'b' });
    const c = makePane({ cwd: 'c' });
    const root = makeSplit('H', makeSplit('V', a, b), c);

    swapPanes(root, a.id, c.id);

    expect(findLeaf(root, a.id)?.cwd).toBe('c');
    expect(findLeaf(root, c.id)?.cwd).toBe('a');
  });

  it('self-swap / missing id: no-op', () => {
    const a = makePane();
    const b = makePane();
    const root = makeSplit('H', a, b);
    const before = deepCloneTree(root);

    swapPanes(root, a.id, a.id);
    expect(JSON.stringify(root)).toBe(JSON.stringify(before));

    swapPanes(root, a.id, 'missing');
    expect(JSON.stringify(root)).toBe(JSON.stringify(before));
  });
});

describe('rearrange — movePane center', () => {
  beforeEach(() => h.invoke.mockClear());

  it('delegates to swap, sets focusedId = dragId, syncs once', () => {
    const a = makePane();
    const b = makePane();
    const dragId = a.id;
    const s = store(makeSplit('H', a, b), dragId);

    expect(movePane(s, dragId, b.id, 'center')).toBe(true);
    expect(s.focusedId).toBe(dragId);
    expect(findLeaf(s.root, dragId)?.index).toBe(2);
    expect(h.invoke).toHaveBeenCalledTimes(1);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });
});

describe('rearrange — movePane edge', () => {
  beforeEach(() => h.invoke.mockClear());

  it('[A│B] drag A onto B/right → [B│A] H split, target first', () => {
    const a = pane('a');
    const b = pane('b');
    const s = store(makeSplit('H', a, b), 'a');

    expect(movePane(s, 'a', 'b', 'right', GENEROUS)).toBe(true);
    const root = s.root as SplitNode;
    expect(root.orientation).toBe('H');
    expect((root.left as { id: string }).id).toBe('b');
    expect((root.right as { id: string }).id).toBe('a');
    expect(s.focusedId).toBe('a');
    expect(h.invoke).toHaveBeenCalledTimes(1);
  });

  it('[A│B] drag A onto B/bottom → V split, target first', () => {
    const a = pane('a');
    const b = pane('b');
    const s = store(makeSplit('H', a, b), 'a');

    expect(movePane(s, 'a', 'b', 'bottom', GENEROUS)).toBe(true);
    const root = s.root as SplitNode;
    expect(root.orientation).toBe('V');
    expect((root.left as { id: string }).id).toBe('b');
    expect((root.right as { id: string }).id).toBe('a');
  });

  it('left/top ⇒ drag first', () => {
    const a = pane('a');
    const b = pane('b');
    const s = store(makeSplit('H', a, b), 'a');

    movePane(s, 'a', 'b', 'left', GENEROUS);
    const root = s.root as SplitNode;
    expect((root.left as { id: string }).id).toBe('a');
    expect((root.right as { id: string }).id).toBe('b');

    const s2 = store(makeSplit('H', pane('a'), pane('b')), 'a');
    movePane(s2, 'a', 'b', 'top', GENEROUS);
    const root2 = s2.root as SplitNode;
    expect(root2.orientation).toBe('V');
    expect((root2.left as { id: string }).id).toBe('a');
  });

  it('3-pane tree: detach collapses parent, balanceRatios equalizes', () => {
    const a = pane('a');
    const b = pane('b');
    const c = pane('c');
    const s = store(makeSplit('H', makeSplit('V', a, b), c), 'a');

    expect(movePane(s, 'a', 'c', 'left', GENEROUS)).toBe(true);
    expect(collectLeaves(s.root).map((l) => l.id).sort()).toEqual([
      'a',
      'b',
      'c',
    ]);
    expect(collectLeaves(s.root).map((l) => l.index)).toEqual([1, 2, 3]);

    const walk = (n: TreeNode): void => {
      if (n.kind !== 'split') return;
      const l = collectLeaves(n.left).length;
      const r = collectLeaves(n.right).length;
      expect(n.ratio).toBeCloseTo(l / (l + r));
      walk(n.left);
      walk(n.right);
    };
    walk(s.root);
  });

  it('drag === target: false, untouched, no sync', () => {
    const a = pane('a');
    const b = pane('b');
    const s = store(makeSplit('H', a, b), 'a');
    const before = deepCloneTree(s.root);

    expect(movePane(s, 'a', 'a', 'right', GENEROUS)).toBe(false);
    expect(JSON.stringify(s.root)).toBe(JSON.stringify(before));
    expect(h.invoke).not.toHaveBeenCalled();
  });
});

function stack7Panes(): TreeNode {
  const panes = Array.from({ length: 7 }, () => makePane());
  let right: TreeNode = panes[6];
  for (let i = 5; i >= 1; i--) {
    right = makeSplit('V', panes[i], right);
  }
  return makeSplit('H', panes[0], right);
}

describe('rearrange — produce integration', () => {
  beforeEach(() => h.invoke.mockClear());

  it('7-pane edge move mutates store.root inside produce', () => {
    const root = stack7Panes();
    const leaves = collectLeaves(root);
    const [store, setStore] = createStore({
      root,
      focusedId: leaves[1].id,
    });
    const before = JSON.stringify(store.root);

    setStore(
      produce((s) =>
        movePane(s, leaves[1].id, leaves[0].id, 'bottom', {
          winW: 1400,
          winH: 900,
          cw: 8,
          ch: 20,
        }),
      ),
    );

    expect(JSON.stringify(store.root)).not.toBe(before);
    expect(collectLeaves(store.root)).toHaveLength(7);
    expect(h.invoke).toHaveBeenCalledTimes(1);
  });
});

describe('rearrange — floor guard (GRD-05)', () => {
  beforeEach(() => h.invoke.mockClear());

  it('tight geom: edge move returns false, tree unchanged', () => {
    const a = makePane();
    const b = makePane();
    const c = makePane();
    const s = store(makeSplit('H', makeSplit('V', a, b), c), a.id);
    const before = deepCloneTree(s.root);

    expect(movePane(s, a.id, c.id, 'bottom', TIGHT)).toBe(false);
    expect(JSON.stringify(s.root)).toBe(JSON.stringify(before));
    expect(h.invoke).not.toHaveBeenCalled();
  });

  it('generous geom: edge move mutates', () => {
    const a = makePane();
    const b = makePane();
    const s = store(makeSplit('H', a, b), a.id);

    expect(movePane(s, a.id, b.id, 'right', GENEROUS)).toBe(true);
    expect(h.invoke).toHaveBeenCalledTimes(1);
  });

  it('simulateMoveViolates does not mutate input', () => {
    const a = makePane();
    const b = makePane();
    const c = makePane();
    const root = makeSplit('H', makeSplit('V', a, b), c);
    const before = deepCloneTree(root);

    simulateMoveViolates(root, a.id, c.id, 'bottom', TIGHT);
    expect(JSON.stringify(root)).toBe(JSON.stringify(before));
  });
});
