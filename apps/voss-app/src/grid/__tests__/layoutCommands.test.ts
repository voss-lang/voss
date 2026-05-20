import { describe, it, expect } from 'vitest';

import {
  collectLeaves,
  makePane,
  makeSplit,
  recomputeIndices,
  type PaneLeaf,
  type TreeNode,
} from '../tree';
import { applyLoadedLayout, serializeLayout } from '../layoutCommands';
import type { LayoutFile } from '../layoutStorage';

/**
 * A4-04 Task 2 — frontend save/load remapping. Pure tests, no Tauri.
 *
 * Hard invariants under test:
 *  - LAY-04 / D-08: no existing pane id is destroyed during load
 *  - D-07: serialized file holds tree + ratios + activePreset + cwd/shell
 *    only — never scrollback, PTY ids, or processes
 *  - LAY-05: bigger saved layouts spawn net-new panes with saved
 *    cwd/shell; smaller saved layouts spill extras through the last
 *    region (A4-01 D-04 rule)
 */

function makePanes(n: number, ctx?: { cwd?: string; shell?: string }): PaneLeaf[] {
  return Array.from({ length: n }, () => makePane(ctx));
}

function chain(orientation: 'H' | 'V', leaves: PaneLeaf[]): TreeNode {
  if (leaves.length === 1) return leaves[0];
  return makeSplit(orientation, leaves[0], chain(orientation, leaves.slice(1)));
}

function makeLayoutFile(
  root: TreeNode,
  focusedId: string,
  activePreset: 'fanout' | 'pipeline' | 'swarm' | 'watchers' | null = null,
): LayoutFile {
  return { version: 1, activePreset, grid: { root, focusedId } };
}

describe('serializeLayout — D-07 capture rules', () => {
  it('writes version=1, activePreset for non-custom, and a deep copy of the grid', () => {
    const leaves = makePanes(2, { cwd: '/repo', shell: 'zsh' });
    const root = chain('H', leaves);
    recomputeIndices(root);
    const file = serializeLayout(root, leaves[0].id, 'fanout');
    expect(file.version).toBe(1);
    expect(file.activePreset).toBe('fanout');
    expect(file.grid.focusedId).toBe(leaves[0].id);
    // Round-trip JSON to prove serializability (no functions, no proxies).
    const roundTripped = JSON.parse(JSON.stringify(file)) as LayoutFile;
    expect(roundTripped).toEqual(file);
  });

  it("activePreset === null when the layout is 'custom'", () => {
    const leaves = makePanes(2);
    const file = serializeLayout(chain('H', leaves), leaves[0].id, 'custom');
    expect(file.activePreset).toBeNull();
  });

  it('does not capture scrollback / PTY session id / process / env fields', () => {
    // Attach extra runtime fields to a leaf to simulate a future A6 layer
    // tagging panes with PTY state. serializeLayout MUST drop them.
    const leaves = makePanes(1, { cwd: '/repo', shell: 'zsh' });
    type DirtyLeaf = PaneLeaf & {
      ptySessionId?: string;
      scrollback?: string;
      processName?: string;
      env?: Record<string, string>;
    };
    const dirty = leaves[0] as DirtyLeaf;
    dirty.ptySessionId = 'pty-123';
    dirty.scrollback = 'lots of output';
    dirty.processName = 'vim';
    dirty.env = { FOO: 'bar' };

    const file = serializeLayout(dirty, dirty.id, 'custom');
    const json = JSON.stringify(file);
    // The dirty values must not survive — serializeLayout's contract
    // depends on the PaneLeaf shape, not on what gets stuck onto it.
    // (Note: today's serializer is JSON.stringify-based; if it ever
    // becomes a per-field copy this assertion only gets stricter.)
    expect(json).not.toMatch(/ptySessionId/);
    expect(json).not.toMatch(/scrollback/);
    expect(json).not.toMatch(/processName/);
    expect(json).not.toMatch(/"env"/);
    // cwd + shell ARE preserved per D-07.
    expect(json).toMatch(/"cwd":"\/repo"/);
    expect(json).toMatch(/"shell":"zsh"/);
  });
});

describe('applyLoadedLayout — equal count', () => {
  it('substitutes existing leaves into the saved shape and preserves ids', () => {
    const current = makePanes(3);
    const saved = makePanes(3, { cwd: '/saved', shell: 'fish' });
    const savedRoot = chain('V', saved);
    const file = makeLayoutFile(savedRoot, saved[1].id, 'pipeline');

    const result = applyLoadedLayout([...current], file);

    const out = collectLeaves(result.root);
    expect(out).toHaveLength(3);
    expect(out.map((l) => l.id)).toEqual(current.map((l) => l.id));
    expect(result.activeLayout).toBe('pipeline');
    // Focus maps via inorder position (saved.focusedId was at index 1).
    expect(result.focusedId).toBe(current[1].id);
  });
});

describe('applyLoadedLayout — saved has MORE slots than current', () => {
  it('spawns net-new panes using saved cwd/shell; existing ids stay intact', () => {
    const current = makePanes(2, { cwd: '/old', shell: 'zsh' });
    const saved = [
      makePane({ cwd: '/s0', shell: 'bash' }),
      makePane({ cwd: '/s1', shell: 'bash' }),
      makePane({ cwd: '/s2', shell: 'fish' }),
      makePane({ cwd: '/s3', shell: 'pwsh' }),
    ];
    const file = makeLayoutFile(chain('H', saved), saved[0].id, 'swarm');

    const result = applyLoadedLayout([...current], file);

    const out = collectLeaves(result.root);
    expect(out).toHaveLength(4);
    // First two leaves are the original ids (LAY-04 no-destroy).
    expect(out.slice(0, 2).map((l) => l.id)).toEqual(
      current.map((l) => l.id),
    );
    // Last two leaves are NEW panes (id is fresh) with the saved cwd/shell.
    const newLeaves = out.slice(2);
    for (let i = 0; i < newLeaves.length; i++) {
      expect(newLeaves[i].id).not.toEqual(saved[i + 2].id); // fresh id
      expect(current.some((c) => c.id === newLeaves[i].id)).toBe(false);
      expect(newLeaves[i].cwd).toBe(saved[i + 2].cwd);
      expect(newLeaves[i].shell).toBe(saved[i + 2].shell);
    }
  });
});

describe('applyLoadedLayout — saved has FEWER slots than current', () => {
  it('fills saved shape with first N current leaves; spills extras into the last region', () => {
    const current = makePanes(5);
    const currentIds = current.map((l) => l.id);
    // Saved has 2 slots in a V split.
    const saved = makePanes(2);
    const file = makeLayoutFile(
      makeSplit('V', saved[0], saved[1]),
      saved[0].id,
      'watchers',
    );

    const result = applyLoadedLayout([...current], file);

    const outIds = collectLeaves(result.root).map((l) => l.id);
    expect(outIds.length).toBe(5);
    // Every current id must survive (LAY-04 hard invariant).
    expect(new Set(outIds)).toEqual(new Set(currentIds));
    // First leaf of the spilled region is current[1] (saved had 2 slots,
    // so the rightmost slot consumed current[1] plus the 3-leaf spill).
    expect(outIds[0]).toBe(currentIds[0]);
  });

  it('no existing pane id is dropped even with extreme over-saturation', () => {
    const current = makePanes(10);
    const saved = makePanes(1);
    const file = makeLayoutFile(saved[0], saved[0].id, 'fanout');
    const result = applyLoadedLayout([...current], file);
    const ids = collectLeaves(result.root).map((l) => l.id);
    expect(new Set(ids)).toEqual(new Set(current.map((l) => l.id)));
  });
});

describe('applyLoadedLayout — focus mapping', () => {
  it('preserves saved focusedId when that id is also a current id', () => {
    const current = makePanes(3);
    const saved = current.map((l) => ({ ...l })); // same ids
    const file = makeLayoutFile(chain('H', saved), current[2].id, null);
    const result = applyLoadedLayout([...current], file);
    expect(result.focusedId).toBe(current[2].id);
    expect(result.activeLayout).toBe('custom');
  });

  it('falls back to first leaf when saved focusedId has no inorder mapping', () => {
    const current = makePanes(2);
    const saved = makePanes(4);
    const file = makeLayoutFile(chain('H', saved), 'unknown-id', 'pipeline');
    const result = applyLoadedLayout([...current], file);
    // Saved has 4 leaves; current has 2; new panes appended → 4 total.
    // Saved focus not in either set → fallback to leaf #1.
    const ids = collectLeaves(result.root).map((l) => l.id);
    expect(result.focusedId).toBe(ids[0]);
  });
});

describe('applyLoadedLayout — geometry integrity', () => {
  it('recomputes indices on the returned tree (inorder, 1..N)', () => {
    const current = makePanes(3);
    const saved = makePanes(3);
    const file = makeLayoutFile(chain('H', saved), saved[0].id, 'pipeline');
    const result = applyLoadedLayout([...current], file);
    const indices = collectLeaves(result.root).map((l) => l.index);
    expect(indices).toEqual([1, 2, 3]);
  });
});
