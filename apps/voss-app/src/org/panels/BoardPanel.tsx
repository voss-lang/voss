import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — the 6-column Kanban board. Filled by a downstream plan.
// Accepts onCardSelect/selectedCardId so it can drive the Diff panel (UI-SPEC).
export default function BoardPanel(props: {
  data: RunData | null;
  onCardSelect?: (cardId: string) => void;
  selectedCardId?: string | null;
}) {
  return (
    <div class="org-panel">
      <Show
        when={props.data}
        fallback={<div class="org-empty">No board data for this run.</div>}
      >
        <div class="org-empty">No board data for this run.</div>
      </Show>
    </div>
  );
}
