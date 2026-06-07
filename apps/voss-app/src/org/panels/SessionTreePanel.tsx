import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — the parent→child session tree. Filled by a downstream plan.
export default function SessionTreePanel(props: { data: RunData | null }) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={
          <div class="org-empty">No session tree data for this run.</div>
        }
      >
        <div class="org-empty">No session tree data for this run.</div>
      </Show>
    </div>
  );
}
