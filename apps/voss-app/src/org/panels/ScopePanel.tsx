import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — declared vs actual scope. Filled by a downstream plan.
export default function ScopePanel(props: { data: RunData | null }) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={<div class="org-empty">No scope data for this run.</div>}
      >
        <div class="org-empty">No scope data for this run.</div>
      </Show>
    </div>
  );
}
