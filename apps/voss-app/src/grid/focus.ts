import {
  type GridStore,
  type TreeNode,
  collectLeaves,
  findLeaf,
} from './tree';
import { markStructuralChange } from './sync';

/**
 * Focus selection (GRD-03): numeric, i3 edge-midpoint directional, click,
 * cycle. Pure tree logic — no DOM, no JSX (the click handler lives in the
 * A3-04 render layer and calls `focusByClick`). Does NOT import
 * `geometry.ts` (A3-02 owns that file in this same wave — file-ownership
 * isolation); the minimal rect math is re-derived locally in `rectsOf`.
 *
 * Every successful focus change fires `markStructuralChange` (GRD-08 — the
 * Rust mirror tracks `focusedId`).
 */

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Pure ratio-split rect per leaf over `winW`×`winH`. Self-contained (no
 * `geometry.ts` import). The i3 algorithm only needs relative positions, so
 * the 1px split border is intentionally omitted — it shifts no adjacency.
 */
function rectsOf(root: TreeNode, winW: number, winH: number): Map<string, Rect> {
  const out = new Map<string, Rect>();
  const walk = (n: TreeNode, x: number, y: number, w: number, h: number) => {
    if (n.kind === 'pane') {
      out.set(n.id, { x, y, w, h });
      return;
    }
    if (n.orientation === 'H') {
      const lw = w * n.ratio;
      walk(n.left, x, y, lw, h);
      walk(n.right, x + lw, y, w - lw, h);
    } else {
      const th = h * n.ratio;
      walk(n.left, x, y, w, th);
      walk(n.right, x, y + th, w, h - th);
    }
  };
  walk(root, 0, 0, winW, winH);
  return out;
}

/** ⌘1–⌘9 — set focus to the leaf whose geometric index === n; else no-op. */
export function focusByIndex(store: GridStore, n: number): void {
  const hit = collectLeaves(store.root).find((l) => l.index === n);
  if (!hit) return; // GRD-03: indices >count (and >9 keybindings) never match
  store.focusedId = hit.id;
  markStructuralChange(store);
}

/** Click — direct set (called from the A3-04 PaneLeaf click handler). */
export function focusByClick(store: GridStore, paneId: string): void {
  if (!findLeaf(store.root, paneId)) return;
  store.focusedId = paneId;
  markStructuralChange(store);
}

/** ⌘[ / ⌘] — prev/next in inorder (= geometric index) order, wrap both ends. */
export function cycleFocus(store: GridStore, dir: 'next' | 'prev'): void {
  const leaves = collectLeaves(store.root); // inorder == index order
  if (leaves.length < 2) return;
  const i = leaves.findIndex((l) => l.id === store.focusedId);
  if (i < 0) return;
  const n = leaves.length;
  const j = dir === 'next' ? (i + 1) % n : (i - 1 + n) % n;
  store.focusedId = leaves[j].id;
  markStructuralChange(store);
}

/**
 * ⌘⌥arrow — i3/sway "nearest to the focused edge-midpoint" (D-03).
 * Deterministic from layout alone, no focus-history state. No-op if no
 * candidate lies in `dir`.
 */
export function focusByDirection(
  store: GridStore,
  dir: 'left' | 'right' | 'up' | 'down',
  winW: number,
  winH: number,
): void {
  const rects = rectsOf(store.root, winW, winH);
  const f = rects.get(store.focusedId);
  if (!f) return;

  const horizontal = dir === 'left' || dir === 'right';
  // Focused-edge midpoint projected along the move axis.
  const mid = horizontal ? f.y + f.h / 2 : f.x + f.w / 2;
  const EPS = 0.5;

  let bestId: string | null = null;
  let bestAxis = Infinity;
  let bestPerp = Infinity;

  for (const [id, r] of rects) {
    if (id === store.focusedId) continue;

    // Candidate must be strictly on the requested side.
    let axisGap: number;
    if (dir === 'right') axisGap = r.x - (f.x + f.w);
    else if (dir === 'left') axisGap = f.x - (r.x + r.w);
    else if (dir === 'down') axisGap = r.y - (f.y + f.h);
    else axisGap = f.y - (r.y + r.h);
    if (axisGap < -EPS) continue;

    // Must share an overlapping perpendicular span (true adjacency, not a
    // shared corner).
    const overlap = horizontal
      ? r.y < f.y + f.h - EPS && r.y + r.h > f.y + EPS
      : r.x < f.x + f.w - EPS && r.x + r.w > f.x + EPS;
    if (!overlap) continue;

    // Perpendicular distance from the projected midpoint to the candidate's
    // span (clamped) — the i3 nearest-to-midpoint tie-break.
    const lo = horizontal ? r.y : r.x;
    const hi = horizontal ? r.y + r.h : r.x + r.w;
    const clamped = Math.max(lo, Math.min(mid, hi));
    const perp = Math.abs(clamped - mid);
    const axis = Math.max(0, axisGap);

    if (
      axis < bestAxis - EPS ||
      (axis <= bestAxis + EPS && perp < bestPerp)
    ) {
      bestAxis = axis;
      bestPerp = perp;
      bestId = id;
    }
  }

  if (!bestId) return;
  store.focusedId = bestId;
  markStructuralChange(store);
}
