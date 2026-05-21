import { createSignal } from 'solid-js';
import { produce, type SetStoreFunction, type Store } from 'solid-js/store';
import type { GridStore } from './tree';
import { resizeByDrag } from './resize';
import { markDragSettled } from './sync';

/**
 * Transparent 6px drag overlay centered on the 1px split border (A3-UI-SPEC
 * "Drag Handle" — no visible track/thumb/glyph, the cursor change is the only
 * affordance). Pointer math lives here; the 20×5 clamp lives in
 * `resizeByDrag` (A3-03, silent — cursor stays, no toast).
 *
 * Cadence (A3-CONTEXT): NO sync per pointer-move (resizeByDrag never syncs);
 * exactly one `markDragSettled` on pointer-up.
 *
 * A8-04: hover uses token-only background tint (`--border-bright` via CSS);
 * dimensions stay fixed at 6px. Active drag disables split-child transitions
 * on the parent wrap via `onDragActive`.
 */
export interface Dims {
  winW: number;
  winH: number;
  cw: number;
  ch: number;
}

export default function DragHandle(props: {
  store: Store<GridStore>;
  setStore: SetStoreFunction<GridStore>;
  path: string;
  orientation: 'H' | 'V';
  spanRect: () => DOMRect | undefined;
  dims: () => Dims;
  onHover: (hot: boolean) => void;
  onDragActive?: (active: boolean) => void;
}) {
  const [hot, setHot] = createSignal(false);
  const [dragging, setDragging] = createSignal(false);

  const onPointerDown = (e: PointerEvent) => {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setDragging(true);
    props.onDragActive?.(true);
    e.preventDefault();
  };

  const onPointerMove = (e: PointerEvent) => {
    if (!dragging()) return;
    const rect = props.spanRect();
    if (!rect) return;
    const ratio =
      props.orientation === 'H'
        ? (e.clientX - rect.left) / rect.width
        : (e.clientY - rect.top) / rect.height;
    const d = props.dims();
    props.setStore(
      produce((s) =>
        resizeByDrag(s, props.path, ratio, d.winW, d.winH, d.cw, d.ch),
      ),
    );
  };

  const endDrag = (e: PointerEvent) => {
    if (!dragging()) return;
    setDragging(false);
    props.onDragActive?.(false);
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    markDragSettled(props.store); // single drag-end mirror sync
  };

  const enter = () => {
    setHot(true);
    props.onHover(true);
  };
  const leave = () => {
    setHot(false);
    props.onHover(false);
  };

  const horizontal = props.orientation === 'H';
  return (
    <div
      data-drag-handle
      data-orientation={horizontal ? 'H' : 'V'}
      data-hot={hot() ? 'true' : 'false'}
      data-drag-active={dragging() ? 'true' : undefined}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onPointerEnter={enter}
      onPointerLeave={leave}
    />
  );
}
