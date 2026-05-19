import {
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
 * D-01: leaves are placed in stable inorder so pane #1 always fills the
 *       preset's primary slot.
 * D-06: every entry recomputes geometry fresh from pane count — stateless.
 *
 * Ratios are assigned per-builder via `chainEqualSlots` so each direct
 * child of a chain split occupies an equal share of its parent's axis.
 * This preserves preset silhouettes (e.g. swarm's 4×4 grid stays a 4×4
 * grid even when the last cell hosts spill panes) instead of devolving to
 * Warp's leaf-equal-area rule, which is only correct for manually-built
 * trees in A3.
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
  return next;
}

// --- Internals ---------------------------------------------------------------

function makeSplitNode(
  orientation: 'H' | 'V',
  ratio: number,
  left: TreeNode,
  right: TreeNode,
): SplitNode {
  return { kind: 'split', orientation, ratio, left, right };
}

/**
 * Right-skewed chain of N direct children where each child occupies an
 * equal share of its parent along `orientation` (ratios 1/N, 1/(N-1), …,
 * 1/2). Each `child` is treated atomically — its internal leaf count does
 * NOT affect the chain's outer ratios, which is what gives a swarm spill
 * cell the same column width as its non-split neighbours.
 */
function chainEqualSlots(
  orientation: 'H' | 'V',
  children: readonly TreeNode[],
): TreeNode {
  const n = children.length;
  if (n === 1) return children[0];
  return makeSplitNode(
    orientation,
    1 / n,
    children[0],
    chainEqualSlots(orientation, children.slice(1)),
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

/**
 * Fanout: pane #1 in the left primary slot; remaining panes form a single
 * right-side vertical column. Outer H split is 50/50 so the source pane
 * reads as the dominant region, with receivers stacked equally inside the
 * right half.
 */
function buildFanout(leaves: PaneLeaf[]): TreeNode {
  if (leaves.length === 1) return leaves[0];
  const [primary, ...rest] = leaves;
  return makeSplitNode(
    'H',
    0.5,
    primary,
    chainEqualSlots('V', rest),
  );
}

/** Pipeline: single left-to-right H row with N equal-width slots. */
function buildPipeline(leaves: PaneLeaf[]): TreeNode {
  return chainEqualSlots('H', leaves);
}

/**
 * Watchers: pane #1 main on top (full width), remaining panes stacked into
 * a single bottom H row. Outer V split is 50/50 so the main region reads
 * as the primary surface even as the watcher count grows.
 */
function buildWatchers(leaves: PaneLeaf[]): TreeNode {
  if (leaves.length === 1) return leaves[0];
  const [primary, ...rest] = leaves;
  return makeSplitNode(
    'V',
    0.5,
    primary,
    chainEqualSlots('H', rest),
  );
}

/**
 * Swarm: near-square grid up to 4×4 (D-03). For N>16, fill a 4×4 grid and
 * spill remaining panes into the last cell via an H chain (D-04). The
 * outer 4×4 silhouette is preserved because each row uses equal-slot
 * ratios — the spill cell consumes the same column width as a non-split
 * neighbour, with its own panes split inside that column.
 */
function buildSwarm(leaves: PaneLeaf[]): TreeNode {
  const n = leaves.length;
  if (n === 1) return leaves[0];

  const cap = 4;

  if (n <= cap * cap) {
    // Near-square: cols = ceil(sqrt(n)) capped at 4, rows = ceil(n/cols).
    // Partial last row is allowed (no filler panes — D-04).
    const cols = Math.min(cap, Math.ceil(Math.sqrt(n)));
    const rows = Math.ceil(n / cols);
    const rowNodes: TreeNode[] = [];
    let i = 0;
    for (let r = 0; r < rows; r++) {
      const cells = Math.min(cols, n - i);
      const rowLeaves = leaves.slice(i, i + cells);
      rowNodes.push(chainEqualSlots('H', rowLeaves));
      i += cells;
    }
    return chainEqualSlots('V', rowNodes);
  }

  // Overflow (n > 16): full 4×4 grid; last cell of the last row hosts the
  // spill chain so the grid's outer silhouette stays a 4×4.
  const cols = cap;
  const rows = cap;
  const rowNodes: TreeNode[] = [];
  for (let r = 0; r < rows - 1; r++) {
    rowNodes.push(chainEqualSlots('H', leaves.slice(r * cols, (r + 1) * cols)));
  }
  const lastRowStart = (rows - 1) * cols;
  const lastRowLeading = leaves.slice(lastRowStart, lastRowStart + cols - 1);
  const spillLeaves = leaves.slice(lastRowStart + cols - 1);
  const spillCell: TreeNode =
    spillLeaves.length === 1 ? spillLeaves[0] : chainEqualSlots('H', spillLeaves);
  rowNodes.push(chainEqualSlots('H', [...lastRowLeading, spillCell]));
  return chainEqualSlots('V', rowNodes);
}
