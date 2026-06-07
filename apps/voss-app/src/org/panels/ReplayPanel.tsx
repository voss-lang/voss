import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — step-through replay of the run's transition history.
// Powered by computeBoardAtStep (Plan 01); filled by a downstream plan.
export default function ReplayPanel(props: { data: RunData | null }) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={
          <div class="org-empty">
            No transition history for this run. Replay requires persisted
            transitions.
          </div>
        }
      >
        <div class="org-empty">
          No transition history for this run. Replay requires persisted
          transitions.
        </div>
      </Show>
    </div>
  );
}
