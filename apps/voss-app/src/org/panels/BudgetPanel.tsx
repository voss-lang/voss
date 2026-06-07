import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — budget allocation/consumption. Filled by a downstream plan.
export default function BudgetPanel(props: { data: RunData | null }) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={<div class="org-empty">No budget data for this run.</div>}
      >
        <div class="org-empty">No budget data for this run.</div>
      </Show>
    </div>
  );
}
