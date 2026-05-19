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
}) {
  let dragging = false;

  const onPointerDown = (e: PointerEvent) => {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragging = true;
    e.preventDefault();
  };

  const onPointerMove = (e: PointerEvent) => {
    if (!dragging) return;
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

  const onPointerUp = (e: PointerEvent) => {
    if (!dragging) return;
    dragging = false;
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    markDragSettled(props.store); // single drag-end mirror sync
  };

  const [, setLocal] = createSignal(false); // keeps the hover handler cheap
  const enter = () => {
    setLocal(true);
    props.onHover(true);
  };
  const leave = () => {
    setLocal(false);
    props.onHover(false);
  };

  const horizontal = props.orientation === 'H';
  return (
    <div
      data-drag-handle
      style={{
        position: 'absolute',
        background: 'transparent',
        'z-index': 5,
        ...(horizontal
          ? {
              width: '6px',
              top: 0,
              bottom: 0,
              left: 'calc(100% - 3px)',
              cursor: 'col-resize',
            }
          : {
              height: '6px',
              left: 0,
              right: 0,
              top: 'calc(100% - 3px)',
              cursor: 'row-resize',
            }),
      }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerEnter={enter}
      onPointerLeave={leave}
    />
  );
}
