import { describe, it, expect } from 'vitest';

import {
  collectLeaves,
  makePane,
  makeSplit,
  recomputeIndices,
  type PaneLeaf,
  type TreeNode,
} from '../tree';
import { computePaneRects, type Rect } from '../geometry';
import {
  applyPreset,
  LAYOUT_PRESETS,
  nextPreset,
} from '../layoutPresets';

/**
 * A4-01 preset model tests. Pure: no DOM, Solid, or Tauri.
 *
 * The hard safety invariants A4 inherits from A3 D-04 are encoded here:
 * preset switches must preserve the exact set of pane ids and must never
 * spawn filler panes for under-capacity layouts.
 */

function makePanes(n: number): PaneLeaf[] {
  return Array.from({ length: n }, () => makePane());
}

/** Right-skewed chain — produces a starting tree of N leaves in inorder. */
function chain(orientation: 'H' | 'V', leaves: PaneLeaf[]): TreeNode {
  if (leaves.length === 1) return leaves[0];
  return makeSplit(orientation, leaves[0], chain(orientation, leaves.slice(1)));
}

const COUNTS = [1, 2, 3, 4, 6, 9, 16, 17] as const;

describe('layoutPresets — cycle (D-05)', () => {
  it('custom snaps to fanout', () => {
    expect(nextPreset('custom')).toBe('fanout');
  });

  it('full cycle: fanout -> pipeline -> swarm -> watchers -> fanout', () => {
    expect(nextPreset('fanout')).toBe('pipeline');
    expect(nextPreset('pipeline')).toBe('swarm');
    expect(nextPreset('swarm')).toBe('watchers');
    expect(nextPreset('watchers')).toBe('fanout');
  });

  it('LAYOUT_PRESETS lists exactly the four presets in cycle order', () => {
    expect([...LAYOUT_PRESETS]).toEqual([
      'fanout',
      'pipeline',
      'swarm',
      'watchers',
    ]);
  });
});

describe('layoutPresets — preserves pane ids (A3 D-04)', () => {
  for (const n of COUNTS) {
    for (const preset of LAYOUT_PRESETS) {
      it(`${preset} preserves pane ids for ${n} pane${n === 1 ? '' : 's'}`, () => {
        const leaves = makePanes(n);
        const root = chain('H', leaves);
        recomputeIndices(root);
        const before = new Set(collectLeaves(root).map((l) => l.id));
        const next = applyPreset(root, preset);
        const after = new Set(collectLeaves(next).map((l) => l.id));
        expect(after.size).toBe(n);
        expect(after).toEqual(before);
      });
    }
  }
});

describe('layoutPresets — preserves cwd/shell per leaf', () => {
  it('fanout keeps each leaf cwd/shell intact', () => {
    const leaves = Array.from({ length: 4 }, (_, i) =>
      makePane({ cwd: `/tmp/${i}`, shell: i % 2 === 0 ? 'zsh' : 'bash' }),
    );
    const root = chain('H', leaves);
    recomputeIndices(root);
    const byId = new Map(
      collectLeaves(root).map((l) => [l.id, { cwd: l.cwd, shell: l.shell }]),
    );
    const next = applyPreset(root, 'fanout');
    for (const l of collectLeaves(next)) {
      expect(l.cwd).toBe(byId.get(l.id)!.cwd);
      expect(l.shell).toBe(byId.get(l.id)!.shell);
    }
  });
});

describe('layoutPresets — no filler panes (D-04 under-capacity)', () => {
  for (const preset of LAYOUT_PRESETS) {
    it(`${preset} on a single pane yields exactly one leaf`, () => {
      const root = chain('H', makePanes(1));
      const next = applyPreset(root, preset);
      expect(collectLeaves(next)).toHaveLength(1);
    });

    it(`${preset} on N panes yields exactly N leaves (no fillers)`, () => {
      for (const n of COUNTS) {
        const root = chain('H', makePanes(n));
        const next = applyPreset(root, preset);
        expect(collectLeaves(next)).toHaveLength(n);
      }
    });
  }
});

describe('layoutPresets — focus-independent construction (D-01)', () => {
  it('applyPreset result depends only on pane id order, not starting tree shape', () => {
    const leaves = makePanes(6);
    const orderedIds = leaves.map((l) => l.id);

    // Two structurally different starting trees with the same inorder id sequence
    const treeA = chain('H', leaves);
    const treeB = chain('V', leaves);

    for (const preset of LAYOUT_PRESETS) {
      const a = applyPreset(treeA, preset);
      const b = applyPreset(treeB, preset);
      expect(collectLeaves(a).map((l) => l.id)).toEqual(orderedIds);
      expect(collectLeaves(b).map((l) => l.id)).toEqual(orderedIds);
    }
  });
});

describe('layoutPresets — reuses existing PaneLeaf objects (no clones)', () => {
  it('fanout output references the same leaf objects as the input tree', () => {
    const leaves = makePanes(4);
    const root = chain('H', leaves);
    const refsBefore = new Set(collectLeaves(root));
    const next = applyPreset(root, 'fanout');
    for (const leaf of collectLeaves(next)) {
      expect(refsBefore.has(leaf)).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Silhouette tests (Task 2): validate visual arrangement against a stable
// 1200×800 fixture using the A3 `computePaneRects` geometry function.
// ---------------------------------------------------------------------------

const W = 1200;
const H = 800;

function rectsFor(root: TreeNode): Map<string, Rect> {
  return computePaneRects(root, W, H);
}

function inorderIds(root: TreeNode): string[] {
  return collectLeaves(root).map((l) => l.id);
}

describe('layoutPresets — fanout silhouette (D-01)', () => {
  it('4 panes: pane#1 anchored top-left, receivers form right vertical column', () => {
    const root = applyPreset(chain('H', makePanes(4)), 'fanout');
    const ids = inorderIds(root);
    const rects = rectsFor(root);
    const r1 = rects.get(ids[0])!;

    // Pane #1 lives in the left primary slot.
    expect(r1.x).toBe(0);
    expect(r1.y).toBe(0);
    expect(r1.h).toBe(H);

    // Receivers all start at the same x (single vertical column) and are
    // strictly to the right of pane #1.
    const recRects = ids.slice(1).map((id) => rects.get(id)!);
    const recXs = new Set(recRects.map((r) => r.x));
    expect(recXs.size).toBe(1);
    expect([...recXs][0]).toBeGreaterThan(r1.x + r1.w - 1);

    // Receivers stack top → bottom in inorder.
    const ys = recRects.map((r) => r.y);
    expect(ys).toEqual([...ys].sort((a, b) => a - b));
  });
});

describe('layoutPresets — pipeline silhouette (D-01, D-04 equal row)', () => {
  it('6 panes: single H row — same y, same h, near-equal widths', () => {
    const root = applyPreset(chain('V', makePanes(6)), 'pipeline');
    const ids = inorderIds(root);
    const rects = ids.map((id) => rectsFor(root).get(id)!);

    expect(new Set(rects.map((r) => r.y)).size).toBe(1);
    expect(new Set(rects.map((r) => r.h)).size).toBe(1);
    expect(rects.map((r) => r.x)).toEqual(
      [...rects.map((r) => r.x)].sort((a, b) => a - b),
    );

    // Count-weighted balance → widths within 1px of each other.
    const widths = rects.map((r) => r.w);
    expect(Math.max(...widths) - Math.min(...widths)).toBeLessThanOrEqual(1);
  });

  it('pane #1 is the leftmost slot', () => {
    const root = applyPreset(chain('V', makePanes(5)), 'pipeline');
    const ids = inorderIds(root);
    expect(rectsFor(root).get(ids[0])!.x).toBe(0);
  });
});

describe('layoutPresets — swarm silhouette (D-03, D-04)', () => {
  it('4 panes: 2×2 grid', () => {
    const root = applyPreset(chain('H', makePanes(4)), 'swarm');
    const ids = inorderIds(root);
    const r = rectsFor(root);
    const [a, b, c, d] = ids.map((id) => r.get(id)!);

    // Top row shares y; bottom row shares y; rows differ.
    expect(a.y).toBe(b.y);
    expect(c.y).toBe(d.y);
    expect(c.y).toBeGreaterThan(a.y);
    // Columns line up across rows.
    expect(a.x).toBe(c.x);
    expect(b.x).toBe(d.x);
  });

  it('9 panes: 3×3 grid (3 unique xs, 3 unique ys)', () => {
    const root = applyPreset(chain('H', makePanes(9)), 'swarm');
    const rects = [...rectsFor(root).values()];
    expect(new Set(rects.map((r) => r.x)).size).toBe(3);
    expect(new Set(rects.map((r) => r.y)).size).toBe(3);
  });

  it('16 panes: 4×4 grid (4 unique xs, 4 unique ys)', () => {
    const root = applyPreset(chain('H', makePanes(16)), 'swarm');
    const rects = [...rectsFor(root).values()];
    expect(new Set(rects.map((r) => r.x)).size).toBe(4);
    expect(new Set(rects.map((r) => r.y)).size).toBe(4);
  });

  it('17 panes: all 17 ids preserved and spill lives inside the last 4×4 cell', () => {
    const leaves = makePanes(17);
    const beforeIds = leaves.map((l) => l.id);
    const root = applyPreset(chain('H', leaves), 'swarm');

    // No pane destroyed.
    const afterIds = inorderIds(root);
    expect(new Set(afterIds)).toEqual(new Set(beforeIds));
    expect(afterIds).toHaveLength(17);

    // Pane #16 and #17 (inorder positions 15 and 16) live in the last 4×4
    // cell, side by side. Their union should equal the rect of pane #15's
    // cell in a hypothetical 16-pane 4×4 layout (same outer geometry, no
    // spill).
    const r17 = rectsFor(root);
    const r16Pane = r17.get(afterIds[15])!;
    const r17Pane = r17.get(afterIds[16])!;
    expect(r16Pane.y).toBe(r17Pane.y);
    expect(r16Pane.h).toBe(r17Pane.h);
    // They touch (1px border between them).
    expect(r17Pane.x).toBe(r16Pane.x + r16Pane.w + 1);

    // Cell #14 (other bottom-row cells) has full-row height like a regular
    // 4×4 cell and is wider than the spilled half-cells.
    const r15Pane = r17.get(afterIds[14])!;
    expect(r15Pane.h).toBe(r16Pane.h);
    expect(r15Pane.w).toBeGreaterThan(r16Pane.w);
  });
});

describe('layoutPresets — watchers silhouette (D-01)', () => {
  it('4 panes: main on top spanning full width, watchers along bottom row', () => {
    const root = applyPreset(chain('H', makePanes(4)), 'watchers');
    const ids = inorderIds(root);
    const r = rectsFor(root);
    const main = r.get(ids[0])!;
    const watchers = ids.slice(1).map((id) => r.get(id)!);

    expect(main.x).toBe(0);
    expect(main.y).toBe(0);
    expect(main.w).toBe(W);

    // Watchers share a y strictly below main and span full width together.
    const wys = new Set(watchers.map((rr) => rr.y));
    expect(wys.size).toBe(1);
    expect([...wys][0]).toBeGreaterThan(main.y + main.h - 1);
    expect(watchers.map((rr) => rr.x)).toEqual(
      [...watchers.map((rr) => rr.x)].sort((a, b) => a - b),
    );
  });

  it('2 panes: main on top, single watcher on bottom (V split)', () => {
    const root = applyPreset(chain('H', makePanes(2)), 'watchers');
    const ids = inorderIds(root);
    const r = rectsFor(root);
    const main = r.get(ids[0])!;
    const watcher = r.get(ids[1])!;
    expect(main.x).toBe(0);
    expect(watcher.x).toBe(0);
    expect(watcher.w).toBe(W);
    expect(watcher.y).toBeGreaterThan(main.y + main.h - 1);
  });
});

