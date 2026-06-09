import {
  type GridStore,
  type PaneLeaf,
  type TreeNode,
  balanceRatios,
  collectLeaves,
  findLeaf,
  makeSplit,
  recomputeIndices,
} from './tree';
import { cloneTree, wouldViolateFloor } from './geometry';
import { replaceLeaf, type GridGeom } from './operations';
import { markStructuralChange } from './sync';
import type { DropZone } from './dropZone';

/**
 * Remove leaf `id`; sibling subtree expands in place. Returns the removed leaf
 * (unlike closeLeaf which discards it).
 */
function detachLeaf(
  node: TreeNode,
  id: string,
): { root: TreeNode | null; leaf: PaneLeaf | null } {
  if (node.kind === 'pane') {
    if (node.id === id) {
      return { root: null, leaf: { ...node } };
    }
    return { root: node, leaf: null };
  }
  const isTarget = (c: TreeNode) => c.kind === 'pane' && c.id === id;
  if (isTarget(node.left)) {
    const leaf = { ...(node.left as PaneLeaf) };
    return { root: node.right, leaf };
  }
  if (isTarget(node.right)) {
    const leaf = { ...(node.right as PaneLeaf) };
    return { root: node.left, leaf };
  }
  const l = detachLeaf(node.left, id);
  if (l.root !== node.left || l.leaf !== null) {
    return {
      root: { ...node, left: l.root as TreeNode },
      leaf: l.leaf,
    };
  }
  const r = detachLeaf(node.right, id);
  if (r.root !== node.right || r.leaf !== null) {
    return {
      root: { ...node, right: r.root as TreeNode },
      leaf: r.leaf,
    };
  }
  return { root: node, leaf: null };
}

/** Swap payload fields in place; ratios untouched. */
export function swapPanes(root: TreeNode, idA: string, idB: string): void {
  if (idA === idB) return;
  const a = findLeaf(root, idA);
  const b = findLeaf(root, idB);
  if (!a || !b) return;
  const aId = a.id;
  const aCwd = a.cwd;
  const aShell = a.shell;
  a.id = b.id;
  a.cwd = b.cwd;
  a.shell = b.shell;
  b.id = aId;
  b.cwd = aCwd;
  b.shell = aShell;
  recomputeIndices(root);
}

/** Pre-flight: would an edge move violate the 20×5 floor? Does not mutate input. */
export function simulateMoveViolates(
  root: TreeNode,
  dragId: string,
  targetId: string,
  zone: DropZone,
  geom: GridGeom,
): boolean {
  if (zone === 'center' || dragId === targetId) return false;
  const clone = cloneTree(root);
  const { root: afterDetach, leaf } = detachLeaf(clone, dragId);
  if (!afterDetach || !leaf) return false;
  const target = findLeaf(afterDetach, targetId);
  if (!target) return false;
  const orientation = zone === 'left' || zone === 'right' ? 'H' : 'V';
  const dragFirst = zone === 'left' || zone === 'top';
  const next = replaceLeaf(
    afterDetach,
    targetId,
    makeSplit(
      orientation,
      dragFirst ? leaf : { ...target },
      dragFirst ? { ...target } : leaf,
    ),
  );
  balanceRatios(next);
  return wouldViolateFloor(
    next,
    geom.winW,
    geom.winH,
    geom.cw,
    geom.ch,
  );
}

/** Drag-drop entry point. Returns true if the store was mutated. */
export function movePane(
  store: GridStore,
  dragId: string,
  targetId: string,
  zone: DropZone,
  geom?: GridGeom,
): boolean {
  if (dragId === targetId) return false;

  if (zone === 'center') {
    swapPanes(store.root, dragId, targetId);
    store.focusedId = dragId;
    markStructuralChange(store);
    return true;
  }

  // Operate on a plain tree clone (proxy-safe; matches layoutCommands pattern).
  const working = cloneTree(store.root);
  if (geom && simulateMoveViolates(working, dragId, targetId, zone, geom)) {
    return false;
  }

  const { root, leaf } = detachLeaf(working, dragId);
  if (!root || !leaf) return false;

  const target = findLeaf(root, targetId);
  if (!target) return false;

  const orientation = zone === 'left' || zone === 'right' ? 'H' : 'V';
  const dragFirst = zone === 'left' || zone === 'top';

  store.root = replaceLeaf(
    root,
    targetId,
    makeSplit(
      orientation,
      dragFirst ? leaf : { ...target },
      dragFirst ? { ...target } : leaf,
    ),
  );
  recomputeIndices(store.root);
  balanceRatios(store.root);
  store.focusedId = dragId;
  markStructuralChange(store);
  return true;
}
