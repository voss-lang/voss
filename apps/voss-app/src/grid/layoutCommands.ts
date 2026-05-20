import {
  collectLeaves,
  makePane,
  recomputeIndices,
  type PaneLeaf,
  type SplitNode,
  type TreeNode,
} from './tree';
import type { ActiveLayout, LayoutPreset } from './layoutPresets';
import type { LayoutFile } from './layoutStorage';

/**
 * A4-04 Task 2 — frontend save/load remapping.
 *
 * Pure helpers: no DOM, no Solid, no Tauri. The Solid render layer owns
 * the produce/setStore wrap; these helpers convert tree shapes and never
 * destroy a pane (LAY-04, A3 D-04 extension).
 *
 * Save semantics (D-07): the on-disk file captures tree shape + split
 * ratios + active preset + per-pane cwd + per-pane shell only. PTY
 * session ids, scrollback, env mutations, and running processes are
 * NOT captured — that is A6's `session.json` concern.
 *
 * Load semantics (D-08): existing panes are remapped onto the saved
 * geometry by stable inorder index. Bigger saved layouts spawn fresh
 * panes for the missing slots using the saved cwd/shell; smaller saved
 * layouts preserve extras by spilling them into the last region (same
 * D-04 spill rule the A4-01 swarm overflow uses).
 */

const LAYOUT_VERSION = 1 as const;

/** Build a LayoutFile from the current grid + active preset. */
export function serializeLayout(
  root: TreeNode,
  focusedId: string,
  activeLayout: ActiveLayout,
): LayoutFile {
  // Whitelist-copy the tree so runtime fields attached by later layers
  // (PTY session ids, scrollback, processName, env mutations …) cannot
  // leak into the on-disk shape (D-07).
  return {
    version: LAYOUT_VERSION,
    activePreset: activeLayout === 'custom' ? null : activeLayout,
    grid: { root: cloneCanonical(root), focusedId },
  };
}

/** Recursively rebuild the tree, copying ONLY the canonical fields of each node. */
function cloneCanonical(n: TreeNode): TreeNode {
  if (n.kind === 'pane') {
    return {
      kind: 'pane',
      id: n.id,
      cwd: n.cwd,
      shell: n.shell,
      index: n.index,
    };
  }
  return {
    kind: 'split',
    orientation: n.orientation,
    ratio: n.ratio,
    left: cloneCanonical(n.left),
    right: cloneCanonical(n.right),
  };
}

/** Result of applying a loaded layout — pure return; caller assigns to store. */
export type LoadResult = {
  root: TreeNode;
  focusedId: string;
  activeLayout: ActiveLayout;
};

/**
 * Apply a loaded `LayoutFile` to the currently-open panes. Caller passes
 * `currentLeaves` (typically the result of `collectLeaves(store.root)
 * .map((l) => ({ ...l }))` — Solid proxy safe; memory:
 * voss-app-solid-produce-no-structuredclone). Returns a fresh tree
 * referencing those leaves (and any newly-spawned panes), plus the new
 * focused id and active layout label.
 *
 *  - Equal count → substitute existing leaves into the saved shape inorder.
 *  - Saved > current → spawn the missing leaves with saved cwd/shell;
 *    appended in inorder after the existing ones.
 *  - Saved < current → fill the saved shape with the first N existing
 *    leaves; spill the rest into the rightmost region via an H chain so
 *    no existing pane id is lost (LAY-04).
 */
export function applyLoadedLayout(
  currentLeaves: PaneLeaf[],
  loaded: LayoutFile,
): LoadResult {
  const savedLeaves = collectLeaves(loaded.grid.root);
  const c = currentLeaves.length;
  const s = savedLeaves.length;

  let root: TreeNode;
  let allLeaves: PaneLeaf[];

  if (s >= c) {
    // Spawn one fresh PaneLeaf per missing slot, inheriting saved
    // cwd/shell so the new panes boot into the right context (D-08).
    const newPanes = savedLeaves
      .slice(c)
      .map((sl) => makePane({ cwd: sl.cwd, shell: sl.shell }));
    allLeaves = [...currentLeaves, ...newPanes];
    root = rebuildShape(loaded.grid.root, allLeaves);
  } else {
    // Saved < current: spill extra existing panes into the last region.
    const fill = currentLeaves.slice(0, s);
    const spill = currentLeaves.slice(s);
    const base = rebuildShape(loaded.grid.root, fill);
    root = spillIntoLastRegion(base, spill);
    allLeaves = currentLeaves;
  }

  recomputeIndices(root);

  // Focus mapping: if the saved focusedId still names an existing leaf,
  // keep it; otherwise map the saved focused position onto the existing
  // leaf at the same inorder index; otherwise fall back to leaf #1.
  const focusedId = resolveFocus(loaded, savedLeaves, allLeaves);

  const activeLayout: ActiveLayout = loaded.activePreset
    ? (loaded.activePreset as LayoutPreset)
    : 'custom';
  return { root, focusedId, activeLayout };
}

// ---------------------------------------------------------------------------

function resolveFocus(
  loaded: LayoutFile,
  savedLeaves: readonly PaneLeaf[],
  allLeaves: readonly PaneLeaf[],
): string {
  const savedId = loaded.grid.focusedId;
  // 1. Direct id hit (most common when reloading the same workspace).
  if (allLeaves.some((l) => l.id === savedId)) return savedId;
  // 2. Inorder position from the saved tree → corresponding existing leaf.
  const savedIdx = savedLeaves.findIndex((l) => l.id === savedId);
  if (savedIdx >= 0 && savedIdx < allLeaves.length) {
    return allLeaves[savedIdx].id;
  }
  // 3. Fallback: focus the first leaf (D-04 — app never empty, at least
  // one leaf always exists).
  return allLeaves[0]!.id;
}

/**
 * Walk `template` (a saved tree) and substitute its inorder PaneLeaf
 * positions with `leaves[0..N]`. Returns a fresh tree — split ratios
 * come from the template; leaves come from the caller.
 */
function rebuildShape(
  template: TreeNode,
  leaves: readonly PaneLeaf[],
): TreeNode {
  let idx = 0;
  const walk = (n: TreeNode): TreeNode => {
    if (n.kind === 'pane') {
      const leaf = leaves[idx++];
      if (!leaf) {
        throw new Error(
          'rebuildShape: ran out of leaves — caller must supply at least template-leaf-count',
        );
      }
      return leaf;
    }
    return makeSplit(n.orientation, n.ratio, walk(n.left), walk(n.right));
  };
  return walk(template);
}

/**
 * Spill `extras` into the rightmost leaf of `tree` by replacing it with
 * an H chain of `[originalLeaf, ...extras]` using equal-slot ratios.
 * Mirrors the A4-01 swarm overflow rule (D-04) so no pane id is lost
 * when the saved geometry has fewer slots than the user has open.
 */
function spillIntoLastRegion(
  tree: TreeNode,
  extras: readonly PaneLeaf[],
): TreeNode {
  if (extras.length === 0) return tree;
  if (tree.kind === 'pane') {
    return chainEqualSlots('H', [tree, ...extras]);
  }
  return makeSplit(
    tree.orientation,
    tree.ratio,
    tree.left,
    spillIntoLastRegion(tree.right, extras),
  );
}

function makeSplit(
  orientation: 'H' | 'V',
  ratio: number,
  left: TreeNode,
  right: TreeNode,
): SplitNode {
  return { kind: 'split', orientation, ratio, left, right };
}

/**
 * Local copy of the A4-01 equal-slot chain builder. Duplicated here
 * intentionally so `layoutCommands.ts` stays decoupled from the preset
 * model's internal helpers — both files use the same Warp-derived
 * spill rule but neither depends on the other.
 */
function chainEqualSlots(
  orientation: 'H' | 'V',
  children: readonly TreeNode[],
): TreeNode {
  const n = children.length;
  if (n === 1) return children[0];
  return makeSplit(
    orientation,
    1 / n,
    children[0],
    chainEqualSlots(orientation, children.slice(1)),
  );
}
