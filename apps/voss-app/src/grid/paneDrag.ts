import { createSignal, type Accessor } from 'solid-js';
import { produce, type SetStoreFunction, type Store } from 'solid-js/store';
import type { GridStore, TreeNode } from './tree';
import { leafCount } from './tree';
import type { Rect } from './geometry';
import type { Dims } from './DragHandle';
import { hitTest, zoneAt, type DropZone } from './dropZone';
import { movePane } from './rearrange';

export interface PaneDragState {
  paneId: string;
  ghost: { x: number; y: number };
  header: { cwd: string; index: number };
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
  cwd: string;
  index: number;
}

const THRESHOLD_PX = 5;

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
  let activePointerId: number | null = null;
  let captureEl: HTMLElement | null = null;
  let snapRects: ReadonlyMap<string, Rect> = new Map();
  let dropTarget: PaneDragState['target'] = null;
  let escapeHandler: ((e: KeyboardEvent) => void) | null = null;

  const captureOpts: AddEventListenerOptions = { capture: true };

  const removeWindowListeners = () => {
    window.removeEventListener('pointermove', onWindowPointerMove, captureOpts);
    window.removeEventListener('pointerup', onWindowPointerUp, captureOpts);
    window.removeEventListener(
      'pointercancel',
      onWindowPointerCancel,
      captureOpts,
    );
    window.removeEventListener(
      'lostpointercapture',
      onLostPointerCapture,
      captureOpts,
    );
  };

  const cleanup = () => {
    const el = captureEl;
    const pid = activePointerId;
    candidate = null;
    dragging = false;
    activePointerId = null;
    captureEl = null;
    snapRects = new Map();
    dropTarget = null;
    removeWindowListeners();
    if (el && pid !== null) {
      try {
        el.releasePointerCapture(pid);
      } catch {
        // capture already released
      }
    }
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
    c.el.setPointerCapture(e.pointerId);
    e.preventDefault();
    snapRects = snapshotPaneRects();
    setRects(snapRects);
    dropTarget = null;
    setState({
      paneId: c.paneId,
      ghost: { x: e.clientX, y: e.clientY },
      header: { cwd: c.cwd, index: c.index },
      target: null,
    });
    document.body.classList.add('pane-dragging');
    escapeHandler = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') cleanup();
    };
    window.addEventListener('keydown', escapeHandler);
  };

  const onWindowPointerMove = (e: PointerEvent) => {
    if (activePointerId !== null && e.pointerId !== activePointerId) return;
    if (!candidate) return;

    if (!dragging) {
      const dx = e.clientX - candidate.startX;
      const dy = e.clientY - candidate.startY;
      if (Math.hypot(dx, dy) > THRESHOLD_PX) {
        beginDrag(candidate, e);
      }
      return;
    }

    const x = e.clientX;
    const y = e.clientY;
    const dragId = candidate.paneId;
    dropTarget = targetAt(snapRects, dragId, x, y);
    setState((prev) =>
      prev ? { ...prev, ghost: { x, y }, target: dropTarget } : null,
    );
  };

  const finishDrag = (e: PointerEvent) => {
    if (!candidate) return;
    const dragId = candidate.paneId;
    const wasDragging = dragging;

    if (wasDragging) {
      const target =
        dropTarget ??
        targetAt(snapRects, dragId, e.clientX, e.clientY);
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
    if (activePointerId !== null && e.pointerId !== activePointerId) return;
    finishDrag(e);
  };

  const onWindowPointerCancel = (e: PointerEvent) => {
    if (activePointerId !== null && e.pointerId !== activePointerId) return;
    cleanup();
  };

  const onLostPointerCapture = (e: PointerEvent) => {
    if (!dragging || activePointerId !== e.pointerId) return;
    cleanup();
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
      cwd: leaf.cwd,
      index: leaf.index,
    };
    activePointerId = e.pointerId;
    captureEl = el;

    window.addEventListener('pointermove', onWindowPointerMove, captureOpts);
    window.addEventListener('pointerup', onWindowPointerUp, captureOpts);
    window.addEventListener('pointercancel', onWindowPointerCancel, captureOpts);
    window.addEventListener(
      'lostpointercapture',
      onLostPointerCapture,
      captureOpts,
    );
  };

  return { state, rects, onHeaderPointerDown };
}

function findPaneMeta(
  root: TreeNode,
  id: string,
): { cwd: string; index: number } | null {
  if (root.kind === 'pane') {
    return root.id === id ? { cwd: root.cwd, index: root.index } : null;
  }
  return (
    findPaneMeta(root.left, id) ?? findPaneMeta(root.right, id)
  );
}
