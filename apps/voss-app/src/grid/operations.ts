import {
  type GridStore,
  type TreeNode,
  balanceRatios,
  collectLeaves,
  findLeaf,
  makePane,
  makeSplit,
  recomputeIndices,
} from './tree';
import { simulateSplitViolates } from './geometry';
import { markStructuralChange } from './sync';

/**
 * Structural tree mutations (GRD-02) with the 20×5 floor guard (GRD-05) and
 * D-04 close behavior. Pure operations on the `GridStore` shape — the render
 * layer (A3-04/05) calls these inside `setStore(produce(...))`; here they
 * mutate the passed object and fire `markStructuralChange` on success.
 *
 * `geom` (window + cell dims) is optional: when supplied, split/fork run the
 * GRD-05 pre-flight and silent-no-op if it would breach the floor. Pure
 * structural callers (and most unit fixtures) omit it.
 */
export interface GridGeom {
  winW: number;
  winH: number;
  cw: number;
  ch: number;
}

/** Replace the leaf `id` with `replacement`, rebuilding the spine. */
function replaceLeaf(
  node: TreeNode,
  id: string,
  replacement: TreeNode,
): TreeNode {
  if (node.kind === 'pane') return node.id === id ? replacement : node;
  return {
    ...node,
    left: replaceLeaf(node.left, id, replacement),
    right: replaceLeaf(node.right, id, replacement),
  };
}

/**
 * Remove leaf `id`; the sibling subtree expands to fill (D-04). Returns the
 * new root (or null if `id` was the only pane) plus the leaf to focus (first
 * inorder leaf of the expanded sibling).
 */
function closeLeaf(
  node: TreeNode,
  id: string,
): { root: TreeNode | null; focus: string | null } {
  if (node.kind === 'pane') {
    return node.id === id ? { root: null, focus: null } : { root: node, focus: null };
  }
  const isTarget = (c: TreeNode) => c.kind === 'pane' && c.id === id;
  if (isTarget(node.left)) {
    return { root: node.right, focus: collectLeaves(node.right)[0].id };
  }
  if (isTarget(node.right)) {
    return { root: node.left, focus: collectLeaves(node.left)[0].id };
  }
  const l = closeLeaf(node.left, id);
  if (l.root !== node.left || l.focus !== null) {
    return { root: { ...node, left: l.root as TreeNode }, focus: l.focus };
  }
  const r = closeLeaf(node.right, id);
  if (r.root !== node.right || r.focus !== null) {
    return { root: { ...node, right: r.root as TreeNode }, focus: r.focus };
  }
  return { root: node, focus: null };
}

function insertSibling(
  store: GridStore,
  orientation: 'H' | 'V',
  newLeaf: TreeNode,
  geom?: GridGeom,
): void {
  if (
    geom &&
    simulateSplitViolates(
      store.root,
      store.focusedId,
      orientation,
      geom.winW,
      geom.winH,
      geom.cw,
      geom.ch,
    )
  ) {
    return; // GRD-05 silent no-op — no change, no sync
  }
  const old = findLeaf(store.root, store.focusedId);
  if (!old) return;
  store.root = replaceLeaf(
    store.root,
    store.focusedId,
    makeSplit(orientation, { ...old }, newLeaf),
  );
  recomputeIndices(store.root);
  store.focusedId = (newLeaf as { id: string }).id;
  markStructuralChange(store);
}

/** ⌘\ (H, new pane right) / ⌘⇧\ (V, new pane below) — 50/50 sibling. */
export function splitFocused(
  store: GridStore,
  orientation: 'H' | 'V',
  geom?: GridGeom,
): void {
  insertSibling(store, orientation, makePane(), geom);
}

/** ⌘D — fork: new sibling inherits cwd+shell, fresh id ⇒ fresh PTY. */
export function forkFocused(store: GridStore, geom?: GridGeom): void {
  const old = findLeaf(store.root, store.focusedId);
  if (!old) return;
  insertSibling(
    store,
    'H',
    makePane({ cwd: old.cwd, shell: old.shell }),
    geom,
  );
}

/** ⌘W — close: sibling expands + focus moves; last pane respawns (D-04). */
export function closeFocused(store: GridStore): void {
  const res = closeLeaf(store.root, store.focusedId);
  if (res.root === null) {
    const fresh = makePane();
    store.root = fresh;
    store.focusedId = fresh.id;
    recomputeIndices(store.root);
    markStructuralChange(store);
    return;
  }
  store.root = res.root;
  store.focusedId = res.focus ?? collectLeaves(res.root)[0].id;
  recomputeIndices(store.root);
  markStructuralChange(store);
}

/** ⌘= — reset every split ratio to 0.5 recursively. */
export function equalizeAll(store: GridStore): void {
  equalizeRatios(store.root);
  markStructuralChange(store);
}
