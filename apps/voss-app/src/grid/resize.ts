import {
  type GridStore,
  type SplitNode,
  type TreeNode,
  equalizeRatios,
} from './tree';
import { markStructuralChange } from './sync';

/**
 * Resize (GRD-04) with the 20×5 floor clamp (GRD-05 resize half). Pure tree
 * logic — no DOM/pointer events (the A3-04 DragHandle owns pointer capture
 * and feeds `requestedRatio`). Does NOT import `geometry.ts` (A3-02 owns
 * that file in this same wave — file-ownership isolation); the floor math is
 * re-derived locally in `rectsOf` + `violatesFloor`.
 *
 * Split nodes have no `id` (the A3-01 wire shape round-trips with the Rust
 * mirror — adding an id would break GRD-08). Splits are therefore addressed
 * by a deterministic PATH string from the root: "" = root, then "L"/"R"
 * appended per descent (e.g. "LR" = root.left.right). The A3-04 DragHandle
 * computes the same path while rendering — see `splitPath`.
 *
 * Cadence (A3-CONTEXT): keyboard fires `markStructuralChange` per 5% step;
 * drag does NOT sync per move — the A3-04 drag-end caller fires
 * `markDragSettled` once on pointer-up.
 */

const HEADER_PX = 22;
const FLOOR_COLS = 20;
const FLOOR_ROWS = 5;
const STEP = 0.05;
const MIN_RATIO = 0.05;
const MAX_RATIO = 0.95;

interface Rect {
  w: number;
  h: number;
}

function rectsOf(root: TreeNode, winW: number, winH: number): Rect[] {
  const out: Rect[] = [];
  const walk = (n: TreeNode, w: number, h: number) => {
    if (n.kind === 'pane') {
      out.push({ w, h });
      return;
    }
    if (n.orientation === 'H') {
      const lw = w * n.ratio;
      walk(n.left, lw, h);
      walk(n.right, w - lw, h);
    } else {
      const th = h * n.ratio;
      walk(n.left, w, th);
      walk(n.right, w, h - th);
    }
  };
  walk(root, winW, winH);
  return out;
}

/** True iff ANY leaf falls below 20 cols OR 5 rows (22px header per pane). */
function violatesFloor(
  root: TreeNode,
  winW: number,
  winH: number,
  cw: number,
  ch: number,
): boolean {
  for (const r of rectsOf(root, winW, winH)) {
    const cols = Math.floor(r.w / cw);
    const rows = Math.floor((r.h - HEADER_PX) / ch);
    if (cols < FLOOR_COLS || rows < FLOOR_ROWS) return true;
  }
  return false;
}

/** Deterministic path → the SplitNode it addresses, or null. */
function findSplitByPath(root: TreeNode, path: string): SplitNode | null {
  let node: TreeNode = root;
  for (const step of path) {
    if (node.kind !== 'split') return null;
    node = step === 'L' ? node.left : node.right;
  }
  return node.kind === 'split' ? node : null;
}

/** Path string of the SplitNode bounding `leafId` on the given axis, or null. */
export function splitPath(
  root: TreeNode,
  leafId: string,
  orientation: 'H' | 'V',
): string | null {
  let found: string | null = null;
  const walk = (n: TreeNode, path: string, axisPath: string | null): boolean => {
    if (n.kind === 'pane') {
      if (n.id === leafId) {
        found = axisPath;
        return true;
      }
      return false;
    }
    const here = n.orientation === orientation ? path : axisPath;
    return walk(n.left, path + 'L', here) || walk(n.right, path + 'R', here);
  };
  walk(root, '', null);
  return found;
}

/**
 * Clamp `ratio` to the nearest value (snapping toward 0.5) at which BOTH
 * child subtrees keep every pane ≥ 20×5. Pure — caller mutates.
 */
function clampRatio(
  root: TreeNode,
  node: SplitNode,
  ratio: number,
  winW: number,
  winH: number,
  cw: number,
  ch: number,
): number {
  const want = Math.min(MAX_RATIO, Math.max(MIN_RATIO, ratio));
  const original = node.ratio;
  const ok = (r: number): boolean => {
    node.ratio = r;
    const bad = violatesFloor(root, winW, winH, cw, ch);
    node.ratio = original;
    return !bad;
  };
  if (ok(want)) return want;
  // Snap toward 0.5 until in-bounds (silent — cursor stays, no toast).
  const dir = want > 0.5 ? -1 : 1;
  for (let r = want; dir > 0 ? r <= 0.5 : r >= 0.5; r += dir * 0.005) {
    const rr = Math.round(r * 1000) / 1000;
    if (ok(rr)) return rr;
  }
  return ok(0.5) ? 0.5 : original;
}

/**
 * Drag a split border (addressed by path). Clamps so neither subtree breaches
 * the 20×5 floor; mutates ONLY that split node's ratio (every other split is
 * byte-identical). Does NOT sync — the A3-04 drag-end caller fires
 * `markDragSettled` once on pointer-up.
 */
export function resizeByDrag(
  store: GridStore,
  splitNodeId: string,
  requestedRatio: number,
  winW: number,
  winH: number,
  cw: number,
  ch: number,
): void {
  const node = findSplitByPath(store.root, splitNodeId);
  if (!node) return;
  node.ratio = clampRatio(store.root, node, requestedRatio, winW, winH, cw, ch);
}

/**
 * ⌘⌥⇧arrow — adjust the focused pane's bounding split ratio by ±5%, clamped
 * at the floor. right/down → +5%, left/up → −5%. No-op if no bounding split
 * of the matching axis exists. Syncs per step (A3-CONTEXT keyboard cadence).
 */
export function resizeByKeyboard(
  store: GridStore,
  dir: 'left' | 'right' | 'up' | 'down',
  winW: number,
  winH: number,
  cw: number,
  ch: number,
): void {
  const orientation: 'H' | 'V' =
    dir === 'left' || dir === 'right' ? 'H' : 'V';
  const path = splitPath(store.root, store.focusedId, orientation);
  if (path === null) return; // single pane / no bounding split this axis
  const node = findSplitByPath(store.root, path);
  if (!node) return;
  const delta = dir === 'right' || dir === 'down' ? STEP : -STEP;
  const next = clampRatio(
    store.root,
    node,
    node.ratio + delta,
    winW,
    winH,
    cw,
    ch,
  );
  if (next === node.ratio) return; // clamped at floor — no overshoot, no sync
  node.ratio = next;
  markStructuralChange(store);
}

/**
 * ⌘= — reset every split ratio to 0.5. Cohesion re-export for the resize
 * keymap group; `operations.equalizeAll` (A3-02) is identical — A3-04 binds
 * exactly ONE (prefer `operations.equalizeAll`), the executor must not
 * double-bind.
 */
export function equalizeAllRatios(store: GridStore): void {
  equalizeRatios(store.root);
  markStructuralChange(store);
}
