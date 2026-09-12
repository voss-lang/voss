import { type Component, type JSX, Show } from 'solid-js';
import './surfaces.css';

export interface SurfaceEmptyProps {
/** Inline icon (e.g. an SVG glyph). Sits in a tinted tile above the title */
  icon?: JSX.Element;
  title: string;
  hint?: JSX.Element;
/** Optional CTA. Only pass when there's a real action to run */
  action?: { label: string; onClick: () => void };
}

const SurfaceEmpty: Component<SurfaceEmptyProps> = (props) => (
  <div class="surface-empty">
    <div class="surface-empty__card">
      <Show when={props.icon}>
        <div class="surface-empty__icon" aria-hidden="true">
          {props.icon}
        </div>
      </Show>
      <p class="surface-empty__title">{props.title}</p>
      <Show when={props.hint}>
        <p class="surface-empty__hint">{props.hint}</p>
      </Show>
      <Show when={props.action}>
        {(action) => (
          <button
            type="button"
            class="surface-empty__action"
            onClick={() => action().onClick()}
          >
            {action().label}
          </button>
        )}
      </Show>
    </div>
  </div>
);

export default SurfaceEmpty;
