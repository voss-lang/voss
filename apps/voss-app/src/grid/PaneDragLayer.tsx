import { Show } from 'solid-js';
import { highlightRect } from './dropZone';
import type { PaneDragController } from './paneDrag';

export default function PaneDragLayer(props: { drag: PaneDragController }) {
  return (
    <Show when={props.drag.state()}>
      {(state) => (
        <div class="pane-drag-overlay">
          <Show when={state().target}>
            {(target) => {
              const r = () =>
                props.drag.rects().get(target().paneId);
              return (
                <Show when={r()}>
                  {(rect) => {
                    const hl = () =>
                      highlightRect(rect(), target().zone);
                    return (
                      <div
                        class="pane-drag-highlight"
                        style={{
                          left: `${hl().x}px`,
                          top: `${hl().y}px`,
                          width: `${hl().w}px`,
                          height: `${hl().h}px`,
                        }}
                      />
                    );
                  }}
                </Show>
              );
            }}
          </Show>
          <div
            class="pane-drag-ghost"
            style={{
              transform: `translate3d(${state().ghost.x + 8}px, ${state().ghost.y + 8}px, 0)`,
            }}
          >
            {state().header.index} · {state().header.title}
          </div>
        </div>
      )}
    </Show>
  );
}
