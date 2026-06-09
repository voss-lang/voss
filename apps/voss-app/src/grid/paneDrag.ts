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
  let escapeHandler: ((e: KeyboardEvent) => void) | null = null;

  const cleanup = (el?: HTMLElement, pointerId?: number) => {
    if (el && pointerId !== undefined && dragging) {
      el.releasePointerCapture(pointerId);
    }
    candidate = null;
    dragging = false;
    setState(null);
    setRects(new Map());
    document.body.classList.remove('pane-dragging');
    if (escapeHandler) {
      window.removeEventListener('keydown', escapeHandler);
      escapeHandler = null;
    }
  };

  const beginDrag = (
    c: Candidate,
    e: PointerEvent,
  ) => {
    dragging = true;
    c.el.setPointerCapture(e.pointerId);
    e.preventDefault();
    const snap = snapshotPaneRects();
    setRects(snap);
    setState({
      paneId: c.paneId,
      ghost: { x: e.clientX, y: e.clientY },
      header: { cwd: c.cwd, index: c.index },
      target: null,
    });
    document.body.classList.add('pane-dragging');
    escapeHandler = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') cleanup(c.el, e.pointerId);
    };
    window.addEventListener('keydown', escapeHandler);
  };

  const onPointerMove = (e: PointerEvent) => {
    if (!candidate) return;
    if (!dragging) {
      const dx = e.clientX - candidate.startX;
      const dy = e.clientY - candidate.startY;
      if (Math.hypot(dx, dy) > THRESHOLD_PX) {
        beginDrag(candidate, e);
      }
      return;
    }
    const snap = rects();
    const x = e.clientX;
    const y = e.clientY;
    const hit = hitTest(snap, x, y);
    const dragId = state()!.paneId;
    let target: PaneDragState['target'] = null;
    if (hit && hit !== dragId) {
      const r = snap.get(hit)!;
      target = { paneId: hit, zone: zoneAt(r, x, y) };
    }
    setState((prev) =>
      prev
        ? { ...prev, ghost: { x, y }, target }
        : null,
    );
  };

  const onPointerUp = (e: PointerEvent) => {
    if (!candidate) return;
    const c = candidate;
    if (dragging) {
      const cur = state();
      if (cur?.target) {
        const { paneId: dragId, target } = cur;
        setStore(
          produce((s) =>
            movePane(s, dragId, target.paneId, target.zone, dims()),
          ),
        );
      }
      cleanup(c.el, e.pointerId);
    } else {
      candidate = null;
    }
  };

  const onPointerCancel = (e: PointerEvent) => {
    if (!candidate) return;
    cleanup(candidate.el, e.pointerId);
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

    const move = (ev: PointerEvent) => onPointerMove(ev);
    const up = (ev: PointerEvent) => {
      onPointerUp(ev);
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      el.removeEventListener('pointercancel', cancel);
    };
    const cancel = (ev: PointerEvent) => {
      onPointerCancel(ev);
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      el.removeEventListener('pointercancel', cancel);
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', cancel);
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
