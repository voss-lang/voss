import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  type GridStore,
  type TreeNode,
  makePane,
  makeSplit,
  collectLeaves,
  recomputeIndices,
} from '../tree';
import {
  focusByIndex,
  focusByClick,
  cycleFocus,
  focusByDirection,
} from '../focus';

function store(root: TreeNode, focusedId: string): GridStore {
  return { root, focusedId };
}

// 2×2: H[ V[a,c], V[b,d] ] over 100×100.
// inorder = a,c,b,d → idx a1 c2 b3 d4. Rects: a{0,0,50,50} c{0,50,50,50}
// b{50,0,50,50} d{50,50,50,50}.
function grid2x2() {
  const a = makePane();
  const b = makePane();
  const c = makePane();
  const d = makePane();
  const root = makeSplit('H', makeSplit('V', a, c), makeSplit('V', b, d));
  recomputeIndices(root);
  return { a, b, c, d, root };
}

// 6-pane asymmetric: H[ V[a, H[b,c]], V[ H[d,e], f] ] → inorder a,b,c,d,e,f.
function grid6() {
  const a = makePane();
  const b = makePane();
  const c = makePane();
  const d = makePane();
  const e = makePane();
  const f = makePane();
  const root = makeSplit(
    'H',
    makeSplit('V', a, makeSplit('H', b, c)),
    makeSplit('V', makeSplit('H', d, e), f),
  );
  recomputeIndices(root);
  return { a, b, c, d, e, f, root };
}

describe('focus — numeric / click / cycle (GRD-03)', () => {
  beforeEach(() => h.invoke.mockClear());

  it('focusByIndex selects the pane at that geometric index', () => {
    const { a, c, b, d, root } = grid2x2();
    expect(collectLeaves(root).map((l) => l.index)).toEqual([1, 2, 3, 4]);
    const s = store(root, a.id);
    focusByIndex(s, 3);
    expect(s.focusedId).toBe(b.id); // index 3
    focusByIndex(s, 2);
    expect(s.focusedId).toBe(c.id);
    focusByIndex(s, 4);
    expect(s.focusedId).toBe(d.id);
    expect(h.invoke).toHaveBeenCalledWith('sync_grid', expect.anything());
  });

  it('focusByIndex(99) on a 4-pane tree is a silent no-op', () => {
    const { a, root } = grid2x2();
    const s = store(root, a.id);
    h.invoke.mockClear();
    focusByIndex(s, 99);
    expect(s.focusedId).toBe(a.id);
    expect(h.invoke).not.toHaveBeenCalled();
  });

  it('focusByClick sets focus directly; unknown id is a no-op', () => {
    const { a, d, root } = grid2x2();
    const s = store(root, a.id);
    focusByClick(s, d.id);
    expect(s.focusedId).toBe(d.id);
    h.invoke.mockClear();
    focusByClick(s, 'no-such-id');
    expect(s.focusedId).toBe(d.id);
    expect(h.invoke).not.toHaveBeenCalled();
  });

  it('cycleFocus wraps at both ends in index order', () => {
    const { a, f, root } = grid6();
    const s = store(root, f.id); // highest index (6)
    cycleFocus(s, 'next');
    expect(s.focusedId).toBe(a.id); // wrap → index 1
    cycleFocus(s, 'prev');
    expect(s.focusedId).toBe(f.id); // wrap back → index 6
  });
});

describe('focus — i3 edge-midpoint directional (GRD-03, D-03)', () => {
  beforeEach(() => h.invoke.mockClear());

  it('from the top-left pane: right→top-right, down→bottom-left', () => {
    const { a, b, c, root } = grid2x2();
    const s = store(root, a.id);
    focusByDirection(s, 'right', 100, 100);
    expect(s.focusedId).toBe(b.id);
    s.focusedId = a.id;
    focusByDirection(s, 'down', 100, 100);
    expect(s.focusedId).toBe(c.id);
  });

  it('from the bottom-right pane: left→bottom-left, up→top-right', () => {
    const { b, c, d, root } = grid2x2();
    const s = store(root, d.id);
    focusByDirection(s, 'left', 100, 100);
    expect(s.focusedId).toBe(c.id);
    s.focusedId = d.id;
    focusByDirection(s, 'up', 100, 100);
    expect(s.focusedId).toBe(b.id);
  });

  it('no candidate in that direction is a silent no-op', () => {
    const { a, root } = grid2x2();
    const s = store(root, a.id);
    h.invoke.mockClear();
    focusByDirection(s, 'left', 100, 100); // a is leftmost
    expect(s.focusedId).toBe(a.id);
    focusByDirection(s, 'up', 100, 100); // a is topmost
    expect(s.focusedId).toBe(a.id);
    expect(h.invoke).not.toHaveBeenCalled();
  });
});
