import {
  balanceRatios,
  collectLeaves,
  recomputeIndices,
  type PaneLeaf,
  type SplitNode,
  type TreeNode,
} from './tree';

/**
 * A4 layout presets — pure visual tree rewrites (LAY-01..05, LAY-08).
 *
 * No DOM, no Solid, no Tauri. Operates on the A3 binary-split tree and
 * reuses existing `PaneLeaf` objects so pane ids, cwd, shell, and any
 * downstream PTY identity are preserved across preset switches (extends
 * A3 D-04: never destroy panes).
 *
 * D-01: leaves are placed in stable inorder (`collectLeaves` post-recompute)
 *       so pane #1 always fills the preset's primary slot.
 * D-06: every entry recomputes geometry fresh from pane count — stateless.
 * Ratios are Warp count-weighted via `balanceRatios` (memory:
 * voss-app-balance-ratios) so leaves end up equal-area regardless of
 * subtree shape.
 */
export type LayoutPreset = 'fanout' | 'pipeline' | 'swarm' | 'watchers';
export type ActiveLayout = LayoutPreset | 'custom';

/** Fixed ⌘G cycle order (D-05). Iteration in this order = next preset. */
export const LAYOUT_PRESETS: readonly LayoutPreset[] = [
  'fanout',
  'pipeline',
  'swarm',
  'watchers',
] as const;

/**
 * Next preset for the ⌘G cycle (D-05). A `custom` layout snaps to fanout —
 * the cycle start — rather than guessing which preset the manual edits
 * resemble. Within the cycle, wrap watchers → fanout.
 */
export function nextPreset(active: ActiveLayout): LayoutPreset {
  if (active === 'custom') return LAYOUT_PRESETS[0];
  const idx = LAYOUT_PRESETS.indexOf(active);
  return LAYOUT_PRESETS[(idx + 1) % LAYOUT_PRESETS.length];
}

/**
 * Build a fresh visual tree for `preset` over the existing leaves of `root`,
 * in inorder. Returns a new root; never destroys leaves, never spawns
 * fillers. Caller is responsible for swapping `root` in the GridStore.
 */
export function applyPreset(root: TreeNode, preset: LayoutPreset): TreeNode {
  const leaves = collectLeaves(root); // inorder, stable
  const next = buildPreset(preset, leaves);
  recomputeIndices(next);
  balanceRatios(next);
  return next;
}

// --- Internals ---------------------------------------------------------------

function makeSplitNode(
  orientation: 'H' | 'V',
  left: TreeNode,
  right: TreeNode,
): SplitNode {
  // 0.5 placeholder — `balanceRatios` overwrites after the full tree is built.
  return { kind: 'split', orientation, ratio: 0.5, left, right };
}

/** Right-skewed chain of N nodes — N-1 splits along one axis. */
function chain(orientation: 'H' | 'V', nodes: readonly TreeNode[]): TreeNode {
  if (nodes.length === 1) return nodes[0];
  return makeSplitNode(
    orientation,
    nodes[0],
    chain(orientation, nodes.slice(1)),
  );
}

function buildPreset(preset: LayoutPreset, leaves: PaneLeaf[]): TreeNode {
  switch (preset) {
    case 'fanout':
      return buildFanout(leaves);
    case 'pipeline':
      return buildPipeline(leaves);
    case 'swarm':
      return buildSwarm(leaves);
    case 'watchers':
      return buildWatchers(leaves);
  }
}

/** Pane#1 left primary; remaining panes form a right-side vertical column. */
function buildFanout(leaves: PaneLeaf[]): TreeNode {
  if (leaves.length === 1) return leaves[0];
  const [primary, ...rest] = leaves;
  return makeSplitNode('H', primary, chain('V', rest));
}

/** Single left-to-right H row across all panes (LAY-03 pipeline). */
function buildPipeline(leaves: PaneLeaf[]): TreeNode {
  return chain('H', leaves);
}

/** Pane#1 main top; remaining panes form a bottom H row of watchers. */
function buildWatchers(leaves: PaneLeaf[]): TreeNode {
  if (leaves.length === 1) return leaves[0];
  const [primary, ...rest] = leaves;
  return makeSplitNode('V', primary, chain('H', rest));
}

/**
 * Near-square grid up to 4×4 (D-03). For N>16, fill the first 15 cells in
 * a 4×4 grid and spill remaining panes into the last cell via an H chain
 * (D-04 — split the last region, never drop a pane).
 */
function buildSwarm(leaves: PaneLeaf[]): TreeNode {
  const n = leaves.length;
  if (n === 1) return leaves[0];

  const cap = 4;

  if (n <= cap * cap) {
    // Near-square: cols = ceil(sqrt(n)) capped at 4, rows = ceil(n/cols).
    const cols = Math.min(cap, Math.ceil(Math.sqrt(n)));
    const rows = Math.ceil(n / cols);
    const rowNodes: TreeNode[] = [];
    let i = 0;
    for (let r = 0; r < rows; r++) {
      const cells = Math.min(cols, n - i);
      const rowLeaves = leaves.slice(i, i + cells);
      rowNodes.push(chain('H', rowLeaves));
      i += cells;
    }
    return chain('V', rowNodes);
  }

  // Overflow (n > 16): fill first 3 rows × 4 cols + first 3 cells of row 4,
  // then last cell holds an H chain of the remaining panes (panes 16..n-1).
  const cols = cap;
  const rows = cap;
  const rowNodes: TreeNode[] = [];
  for (let r = 0; r < rows - 1; r++) {
    rowNodes.push(chain('H', leaves.slice(r * cols, (r + 1) * cols)));
  }
  const lastRowStart = (rows - 1) * cols;
  const lastRowLeading = leaves.slice(lastRowStart, lastRowStart + cols - 1);
  const spill = leaves.slice(lastRowStart + cols - 1);
  const spillCell: TreeNode = spill.length === 1 ? spill[0] : chain('H', spill);
  rowNodes.push(chain('H', [...lastRowLeading, spillCell]));
  return chain('V', rowNodes);
}
