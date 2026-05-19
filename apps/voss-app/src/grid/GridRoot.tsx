import { onMount, onCleanup, createSignal } from 'solid-js';
import { produce } from 'solid-js/store';
import { createGridStore, type GridStore, type TreeNode } from './tree';
import { dispatchKey } from './keymap';
import SplitNodeView, { type CloseUI } from './SplitNode';
import { requestCloseGated } from './CloseConfirmBanner';
import type { Dims } from './DragHandle';

/**
 * Grid container (GRD-01) + global keymap host + GRD-05 window-shrink floor.
 *
 * Integration contract (verified in A3-06, NOT here — A1 owns App.tsx):
 * App.tsx renders `<GridRoot />` in the body slot below the A1 titlebar.
 * `onCloseRequest` defaults to `closeFocused` so ⌘W works pre-A3-05; A3-05
 * passes the foreground-detection-gated variant.
 *
 * `--bg-0` shows only mid-drag / mid-close (never steady state). When the OS
 * window is too small to honor 20×5 for every pane, the inner grid is tiled
 * at `minGridSize` (≥ window) and clipped by `overflow-hidden` — panes keep
 * the floor, `--bg-0` is never sub-floored (GRD-05 window-shrink stop).
 */

const HEADER_PX = 22;
const FLOOR_COLS = 20;
const FLOOR_ROWS = 5;
// TODO(A3-06): read live xterm cell metrics from the A2 pane (A2 owns the
// value; PaneComponent does not yet expose it). A2 xterm = 13px / lineHeight
// 1.5 → ~8×20px cell; used only for the floor math, not layout.
const DEFAULT_CW = 8;
const DEFAULT_CH = 20;

/**
 * Smallest window px at which EVERY leaf still gets ≥ 20 cols × 5 rows given
 * the current ratios (pure — used for the GRD-05 shrink clamp).
 */
export function minGridSize(
  root: TreeNode,
  cw: number,
  ch: number,
): { w: number; h: number } {
  let needW = 0;
  let needH = 0;
  const walk = (n: TreeNode, wf: number, hf: number) => {
    if (n.kind === 'pane') {
      needW = Math.max(needW, (FLOOR_COLS * cw) / wf);
      needH = Math.max(needH, (FLOOR_ROWS * ch + HEADER_PX) / hf);
      return;
    }
    if (n.orientation === 'H') {
      walk(n.left, wf * n.ratio, hf);
      walk(n.right, wf * (1 - n.ratio), hf);
    } else {
      walk(n.left, wf, hf * n.ratio);
      walk(n.right, wf, hf * (1 - n.ratio));
    }
  };
  walk(root, 1, 1);
  return { w: Math.ceil(needW), h: Math.ceil(needH) };
}

export default function GridRoot(props: {
  onCloseRequest?: (store: GridStore) => void;
  closeUI?: CloseUI;
}) {
  const [store, setStore] = createGridStore();
  const [win, setWin] = createSignal({
    w: window.innerWidth,
    h: window.innerHeight,
  });

  const dims = (): Dims => ({
    winW: win().w,
    winH: win().h,
    cw: DEFAULT_CW,
    ch: DEFAULT_CH,
  });

  const grid = () => {
    const m = minGridSize(store.root, DEFAULT_CW, DEFAULT_CH);
    return { w: Math.max(win().w, m.w), h: Math.max(win().h, m.h) };
  };

  const onKey = (e: KeyboardEvent) => {
    if (!e.metaKey) return; // every A3 chord needs ⌘ — let the PTY have it
    setStore(
      produce((s) => {
        dispatchKey(
          s,
          e,
          win().w,
          win().h,
          DEFAULT_CW,
          DEFAULT_CH,
          props.onCloseRequest ??
            ((s) =>
              requestCloseGated(
                s,
                s.focusedId,
                () => props.closeUI?.isFg(s.focusedId) ?? false,
                () => {
                  /* ⌘W cross-pane banner is A3-06 (A2 fg not surfaced yet) */
                },
              )),
        );
      }),
    );
  };
  const onResize = () =>
    setWin({ w: window.innerWidth, h: window.innerHeight });

  onMount(() => {
    window.addEventListener('keydown', onKey);
    window.addEventListener('resize', onResize);
  });
  onCleanup(() => {
    window.removeEventListener('keydown', onKey);
    window.removeEventListener('resize', onResize);
  });

  return (
    <div class="grid-root bg-bg-0 w-full h-full overflow-hidden">
      <div style={{ width: `${grid().w}px`, height: `${grid().h}px` }}>
        <SplitNodeView
          node={store.root}
          store={store}
          setStore={setStore}
          path=""
          dims={dims}
          closeUI={props.closeUI}
        />
      </div>
    </div>
  );
}
