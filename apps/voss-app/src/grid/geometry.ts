import {
  type TreeNode,
  balanceRatios,
  findLeaf,
  makePane,
  makeSplit,
} from './tree';

/**
 * Pixel geometry + the 20×5 hard-floor predicate (GRD-05). Pure: no DOM,
 * no Solid store, no Tauri. A 1px split border sits between split children
 * (A3-UI-SPEC "Split Border"); the 22px pane header is INSIDE each pane and
 * is subtracted only when converting pixels → terminal rows.
 */

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export const HEADER_PX = 22;
export const FLOOR_COLS = 20;
export const FLOOR_ROWS = 5;

/** One pixel rect per leaf, tiling the full area minus 1px split borders. */
export function computePaneRects(
  root: TreeNode,
  winW: number,
  winH: number,
): Map<string, Rect> {
  const out = new Map<string, Rect>();
  const walk = (n: TreeNode, x: number, y: number, w: number, h: number) => {
    if (n.kind === 'pane') {
      out.set(n.id, { x, y, w, h });
      return;
    }
    if (n.orientation === 'H') {
      const leftW = Math.floor((w - 1) * n.ratio);
      const rightW = w - 1 - leftW;
      walk(n.left, x, y, leftW, h);
      walk(n.right, x + leftW + 1, y, rightW, h);
    } else {
      const topH = Math.floor((h - 1) * n.ratio);
      const botH = h - 1 - topH;
      walk(n.left, x, y, w, topH);
      walk(n.right, x, y + topH + 1, w, botH);
    }
  };
  walk(root, 0, 0, winW, winH);
  return out;
}

/** Terminal cols/rows a pixel rect yields at cell size (cw, ch). */
export function paneColsRows(
  rect: Rect,
  cw: number,
  ch: number,
): { cols: number; rows: number } {
  return {
    cols: Math.floor(rect.w / cw),
    rows: Math.floor((rect.h - HEADER_PX) / ch),
  };
}

/** True iff ANY leaf falls below 20 cols OR 5 rows (GRD-05 hard floor). */
export function wouldViolateFloor(
  root: TreeNode,
  winW: number,
  winH: number,
  cw: number,
  ch: number,
): boolean {
  for (const rect of computePaneRects(root, winW, winH).values()) {
    const { cols, rows } = paneColsRows(rect, cw, ch);
    if (cols < FLOOR_COLS || rows < FLOOR_ROWS) return true;
  }
  return false;
}

/**
 * Pure structural deep-copy. NOT `structuredClone` — at the render layer
 * `root` is a Solid `produce` draft proxy, which `structuredClone` rejects
 * (DATA_CLONE_ERR). The tree is a tiny discriminated union, so a hand walk
 * is both proxy-safe and faster.
 */
export function cloneTree(n: TreeNode): TreeNode {
  return n.kind === 'pane'
    ? { ...n }
    : { ...n, left: cloneTree(n.left), right: cloneTree(n.right) };
}

/**
 * Pre-flight guard for split/fork: build the post-split tree in a clone and
 * test the floor WITHOUT mutating the input.
 */
export function simulateSplitViolates(
  root: TreeNode,
  focusedId: string,
  orientation: 'H' | 'V',
  winW: number,
  winH: number,
  cw: number,
  ch: number,
): boolean {
  const clone = cloneTree(root);
  const target = findLeaf(clone, focusedId);
  if (!target) return false;

  const replacement = makeSplit(
    orientation,
    { ...target },
    makePane({ cwd: target.cwd, shell: target.shell }),
  );

  const swap = (n: TreeNode): TreeNode => {
    if (n.kind === 'pane') return n.id === focusedId ? replacement : n;
    return { ...n, left: swap(n.left), right: swap(n.right) };
  };
  const next = swap(clone);
  balanceRatios(next); // floor reflects the Warp auto-equalized geometry
  return wouldViolateFloor(next, winW, winH, cw, ch);
}
