import { createStore, type SetStoreFunction, type Store } from 'solid-js/store';

/**
 * A3 binary-split pane tree — the Solid source of truth (GRD-01, GRD-08).
 * Pure model: no rendering, no Tauri, no DOM. Field names are the wire
 * contract — the Rust mirror (`grid.rs`) round-trips these exact keys.
 *
 * orientation "H" = side-by-side (⌘\); "V" = stacked (⌘⇧\). ratio 0.0–1.0.
 */
export type SplitNode = {
  kind: 'split';
  orientation: 'H' | 'V';
  ratio: number;
  left: TreeNode;
  right: TreeNode;
};

export type PaneLeaf = {
  kind: 'pane';
  id: string;
  cwd: string;
  shell: string;
  index: number;
};

export type TreeNode = SplitNode | PaneLeaf;

export type GridStore = {
  root: TreeNode;
  focusedId: string;
};

/** A fresh default pane leaf (UUID id, index 1, caller-supplied cwd/shell). */
export function makePane(defaults?: {
  cwd?: string;
  shell?: string;
}): PaneLeaf {
  return {
    kind: 'pane',
    id: crypto.randomUUID(),
    cwd: defaults?.cwd ?? '',
    shell: defaults?.shell ?? '',
    index: 1,
  };
}

/** New split — ALWAYS ratio 0.5 (A3-CONTEXT D-02 50/50 insertion). */
export function makeSplit(
  orientation: 'H' | 'V',
  left: TreeNode,
  right: TreeNode,
): SplitNode {
  return { kind: 'split', orientation, ratio: 0.5, left, right };
}

/** Solid store: root = one default pane, focusedId = that leaf id. */
export function createGridStore(defaults?: {
  cwd?: string;
  shell?: string;
}): [Store<GridStore>, SetStoreFunction<GridStore>] {
  const root = makePane(defaults);
  return createStore<GridStore>({ root, focusedId: root.id });
}

/**
 * Geometric index recompute: inorder traversal (left/top subtree, then
 * right/bottom) assigning 1-based `index` to each leaf in encounter order.
 * Stable left-to-right, top-to-bottom, NO gaps (A3-CONTEXT discretion lock).
 */
export function recomputeIndices(root: TreeNode): void {
  let next = 1;
  const walk = (n: TreeNode): void => {
    if (n.kind === 'pane') {
      n.index = next++;
      return;
    }
    walk(n.left);
    walk(n.right);
  };
  walk(root);
}

/** Reset every SplitNode.ratio to 0.5 recursively (legacy even-split). */
export function equalizeRatios(root: TreeNode): void {
  if (root.kind !== 'split') return;
  root.ratio = 0.5;
  equalizeRatios(root.left);
  equalizeRatios(root.right);
}

/** Leaf count of a subtree. */
export function leafCount(root: TreeNode): number {
  return root.kind === 'pane'
    ? 1
    : leafCount(root.left) + leafCount(root.right);
}

/**
 * Warp-style locked-tiling equalize: set every split's ratio to
 * leaves(left)/leaves(node) so EVERY leaf ends up the same size on its axis
 * (a fresh pane shrinks the others evenly instead of geometrically halving
 * the focused one). This is the ⌘= behavior and the auto-equalize applied
 * after every split/fork/close (memory: voss-app-grid-warp-parity).
 */
export function balanceRatios(root: TreeNode): void {
  if (root.kind !== 'split') return;
  const l = leafCount(root.left);
  const r = leafCount(root.right);
  root.ratio = l / (l + r);
  balanceRatios(root.left);
  balanceRatios(root.right);
}

/** Find a pane leaf by id (inorder), or undefined. */
export function findLeaf(root: TreeNode, id: string): PaneLeaf | undefined {
  if (root.kind === 'pane') return root.id === id ? root : undefined;
  return findLeaf(root.left, id) ?? findLeaf(root.right, id);
}

/** All pane leaves in inorder (left-to-right, top-to-bottom). */
export function collectLeaves(root: TreeNode): PaneLeaf[] {
  if (root.kind === 'pane') return [root];
  return [...collectLeaves(root.left), ...collectLeaves(root.right)];
}
