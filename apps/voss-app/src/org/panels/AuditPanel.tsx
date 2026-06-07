import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — the V9 audit JSON view. Filled by a downstream plan.
export default function AuditPanel(props: { data: RunData | null }) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={<div class="org-empty">No audit data for this run.</div>}
      >
        <div class="org-empty">No audit data for this run.</div>
      </Show>
    </div>
  );
}
