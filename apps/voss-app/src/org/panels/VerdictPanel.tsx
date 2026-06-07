import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — Reviewer-A / Reviewer-B verdicts. Filled by a downstream plan.
export default function VerdictPanel(props: { data: RunData | null }) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={<div class="org-empty">No verdict data for this run.</div>}
      >
        <div class="org-empty">No verdict data for this run.</div>
      </Show>
    </div>
  );
}
