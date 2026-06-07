import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — blocked cards + decision flow. Filled by Plan 07.
export default function BlockedPanel(props: { data: RunData | null }) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={<div class="org-empty">No blocked cards in this run.</div>}
      >
        <div class="org-empty">No blocked cards in this run.</div>
      </Show>
    </div>
  );
}
