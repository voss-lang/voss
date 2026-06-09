import { createSignal, type Accessor } from 'solid-js';
import { produce, type SetStoreFunction, type Store } from 'solid-js/store';
import type { GridStore, TreeNode } from './tree';
import { leafCount } from './tree';
import type { Rect } from './geometry';
import type { Dims } from './DragHandle';
import { hitTest, zoneAt, type DropZone } from './dropZone';
import { movePane } from './rearrange';
import { paneSessionTitle } from './PaneHeader';
import { procByPaneId } from '../pane/procRegistry';

export interface PaneDragState {
  paneId: string;
  ghost: { x: number; y: number };
  header: { title: string; index: number };
  target: { paneId: string; zone: DropZone } | null;
}

export interface PaneDragController {
  state: Accessor<PaneDragState | null>;
  rects: Accessor<ReadonlyMap<string, Rect>>;
  onHeaderPointerDown: (e: PointerEvent, paneId: string) => void;
}

interface Candidate {
  paneId: string;
  startX: number;
  startY: number;
  el: HTMLElement;
  title: string;
  index: number;
}

const THRESHOLD_PX = 5;
const captureOpts: AddEventListenerOptions = { capture: true };

function snapshotPaneRects(): Map<string, Rect> {
  const out = new Map<string, Rect>();
  for (const el of document.querySelectorAll('[data-pane-id]')) {
    const id = el.getAttribute('data-pane-id');
    if (!id) continue;
    const r = el.getBoundingClientRect();
    out.set(id, { x: r.x, y: r.y, w: r.width, h: r.height });
  }
  return out;
}

function targetAt(
  rects: ReadonlyMap<string, Rect>,
  dragId: string,
  x: number,
  y: number,
): PaneDragState['target'] {
  const hit = hitTest(rects, x, y);
  if (!hit || hit === dragId) return null;
  const r = rects.get(hit)!;
  return { paneId: hit, zone: zoneAt(r, x, y) };
}

export function createPaneDrag(
  store: Store<GridStore>,
  setStore: SetStoreFunction<GridStore>,
  dims: () => Dims,
): PaneDragController {
  const [state, setState] = createSignal<PaneDragState | null>(null);
  const [rects, setRects] = createSignal<ReadonlyMap<string, Rect>>(
    new Map(),
  );

  let candidate: Candidate | null = null;
  let dragging = false;
  let captureEl: HTMLElement | null = null;
  let capturePointerId: number | null = null;
  let snapRects: ReadonlyMap<string, Rect> = new Map();
  let dropTarget: PaneDragState['target'] = null;
  let lastX = 0;
  let lastY = 0;
  let escapeHandler: ((e: KeyboardEvent) => void) | null = null;

  const removeWindowListeners = () => {
    window.removeEventListener('pointermove', onWindowPointerMove, captureOpts);
    window.removeEventListener('pointerup', onWindowPointerUp, captureOpts);
    window.removeEventListener('pointercancel', onWindowPointerCancel, captureOpts);
    window.removeEventListener('mouseup', onWindowMouseUp, captureOpts);
  };

  const cleanup = () => {
    const el = captureEl;
    candidate = null;
    dragging = false;
    captureEl = null;
    snapRects = new Map();
    dropTarget = null;
    removeWindowListeners();
    if (el && capturePointerId !== null) {
      try {
        el.releasePointerCapture(capturePointerId);
      } catch {
        // ignore
      }
    }
    capturePointerId = null;
    setState(null);
    setRects(new Map());
    document.body.classList.remove('pane-dragging');
    if (escapeHandler) {
      window.removeEventListener('keydown', escapeHandler);
      escapeHandler = null;
    }
  };

  const beginDrag = (c: Candidate, e: PointerEvent) => {
    dragging = true;
    capturePointerId = e.pointerId;
    try {
      c.el.setPointerCapture(e.pointerId);
    } catch {
      // WKWebView may reject capture — window listeners still handle the drag.
    }
    e.preventDefault();
    snapRects = snapshotPaneRects();
    setRects(snapRects);
    dropTarget = null;
    lastX = e.clientX;
    lastY = e.clientY;
    setState({
      paneId: c.paneId,
      ghost: { x: lastX, y: lastY },
      header: { title: c.title, index: c.index },
      target: null,
    });
    document.body.classList.add('pane-dragging');
    escapeHandler = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') cleanup();
    };
    window.addEventListener('keydown', escapeHandler);
  };

  const onWindowPointerMove = (e: PointerEvent) => {
    if (!candidate) return;

    if (!dragging) {
      const dx = e.clientX - candidate.startX;
      const dy = e.clientY - candidate.startY;
      if (Math.hypot(dx, dy) > THRESHOLD_PX) {
        beginDrag(candidate, e);
      }
      return;
    }

    lastX = e.clientX;
    lastY = e.clientY;
    const dragId = candidate.paneId;
    dropTarget = targetAt(snapRects, dragId, lastX, lastY);
    setState((prev) =>
      prev ? { ...prev, ghost: { x: lastX, y: lastY }, target: dropTarget } : null,
    );
  };

  const finishDrag = (clientX: number, clientY: number) => {
    if (!candidate) return;
    const dragId = candidate.paneId;
    const wasDragging = dragging;

    if (wasDragging) {
      const x = clientX || lastX;
      const y = clientY || lastY;
      const target =
        dropTarget ?? targetAt(snapRects, dragId, x, y);
      if (target) {
        setStore(
          produce((s) =>
            movePane(s, dragId, target.paneId, target.zone, dims()),
          ),
        );
      }
    }
    cleanup();
  };

  const onWindowPointerUp = (e: PointerEvent) => {
    if (!candidate) return;
    finishDrag(e.clientX, e.clientY);
  };

  const onWindowPointerCancel = () => {
    if (!candidate) return;
    cleanup();
  };

  /** WKWebView/Tauri sometimes delivers mouseup without a matching pointerup. */
  const onWindowMouseUp = (e: MouseEvent) => {
    if (!candidate || !dragging) return;
    if (e.button !== 0) return;
    finishDrag(e.clientX, e.clientY);
  };

  const onHeaderPointerDown = (e: PointerEvent, paneId: string) => {
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest('button')) return;
    if (leafCount(store.root as TreeNode) === 1) return;

    const leaf = findPaneMeta(store.root as TreeNode, paneId);
    if (!leaf) return;

    const el = e.currentTarget as HTMLElement;
    candidate = {
      paneId,
      startX: e.clientX,
      startY: e.clientY,
      el,
      title: leaf.title,
      index: leaf.index,
    };
    captureEl = el;
    lastX = e.clientX;
    lastY = e.clientY;

    window.addEventListener('pointermove', onWindowPointerMove, captureOpts);
    window.addEventListener('pointerup', onWindowPointerUp, captureOpts);
    window.addEventListener('pointercancel', onWindowPointerCancel, captureOpts);
    window.addEventListener('mouseup', onWindowMouseUp, captureOpts);
  };

  return { state, rects, onHeaderPointerDown };
}

function findPaneMeta(
  root: TreeNode,
  id: string,
): { title: string; index: number } | null {
  if (root.kind === 'pane') {
    if (root.id !== id) return null;
    return {
      title: paneSessionTitle(
        procByPaneId()[id],
        root.cwd,
        root.shell,
      ),
      index: root.index,
    };
  }
  return (
    findPaneMeta(root.left, id) ?? findPaneMeta(root.right, id)
  );
}
