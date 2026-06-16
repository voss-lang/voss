// V24-07 (VADE2-07) — reduced-motion fallback Event Trace list.
//
// Driven by the SAME liveGraphPatches() signal that animates the connectors —
// a display toggle, not a second data source. Always populated; collapsed in
// motion mode, expanded + pinned under reduced motion so no information is
// motion-only (the a11y parity bar). Rows: [timestamp] [edge type]
// [source → destination]. Bounded slice (T-V24-07-D).

import { type Component, For, Show } from 'solid-js';
import { liveGraphPatches } from '../../org/live/sseClient';

export interface EventTraceListProps {
  /** Expanded + pinned under reduced motion; collapsed (count only) in motion. */
  expanded: boolean;
}

const MAX_ROWS = 50;

function fmtTime(ts: number): string {
  const d = new Date(ts);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

const EventTraceList: Component<EventTraceListProps> = (props) => {
  // Most-recent first, bounded.
  const rows = () => liveGraphPatches().slice(-MAX_ROWS).slice().reverse();

  return (
    <div
      class={`swarm-trace${props.expanded ? ' swarm-trace--expanded' : ''}`}
      aria-label="Event trace"
    >
      <div class="swarm-trace__title">Event trace</div>
      <Show
        when={props.expanded}
        fallback={
          <div class="swarm-trace__hint">{rows().length} live events</div>
        }
      >
        <ul class="swarm-trace__list">
          <For each={rows()}>
            {(p) => (
              <li class="swarm-trace__row">
                <span class="swarm-trace__time">{fmtTime(p.timestamp)}</span>
                <span class="swarm-trace__type">{p.edgeType}</span>
                <span class="swarm-trace__path">
                  {p.source} → {p.toNodeId}
                </span>
              </li>
            )}
          </For>
        </ul>
      </Show>
    </div>
  );
};

export default EventTraceList;
