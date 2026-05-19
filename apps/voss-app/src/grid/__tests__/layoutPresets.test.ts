import { describe, it, expect } from 'vitest';

import {
  collectLeaves,
  makePane,
  makeSplit,
  recomputeIndices,
  type PaneLeaf,
  type TreeNode,
} from '../tree';
import {
  applyPreset,
  LAYOUT_PRESETS,
  nextPreset,
  type LayoutPreset,
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
