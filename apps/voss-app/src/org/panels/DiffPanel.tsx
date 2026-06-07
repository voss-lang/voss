import { Show } from 'solid-js';
import type { RunData } from '../types';

// V11-03 stub — diff + verification drilldown for a card. Filled downstream.
// Navigated to via a board card click (selectedCardId) or its own picker.
export default function DiffPanel(props: {
  data: RunData | null;
  selectedCardId?: string | null;
  onCardSelect?: (cardId: string) => void;
}) {
  return (
    <div class="org-panel">
      <Show
        when={props.selectedCardId}
        fallback={
          <div class="org-empty">Select a card to view its diff.</div>
        }
      >
        <div class="org-empty">No diff recorded for this card.</div>
      </Show>
    </div>
  );
}
