// V24-06 (VADE2-06) — Swarm Map right legend panel (200px).
//
// Shows the selected node's detail as kv rows (mirrors the cockpit kv-grid) plus
// a deep-link button for work nodes; "Select a node to inspect" when nothing is
// selected. No raw runId is surfaced as a label (D-09).

import { type Component, Show } from 'solid-js';
import type { SwarmNode } from './swarmMapDerive';

export interface SwarmMapLegendProps {
  node: SwarmNode | null;
  onOpen: (node: SwarmNode) => void;
}

const SwarmMapLegend: Component<SwarmMapLegendProps> = (props) => {
  return (
    <div class="swarm-legend" aria-label="Swarm node detail">
      <Show
        when={props.node}
        fallback={
          <div class="swarm-legend__empty">Select a node to inspect</div>
        }
      >
        {(node) => (
          <>
            <div class="swarm-legend__header">{node().label}</div>
            <div class="swarm-legend__kv">
              <span class="swarm-legend__k">Type</span>
              <span class="swarm-legend__v">{node().type}</span>
              <Show when={node().status}>
                <span class="swarm-legend__k">Status</span>
                <span class="swarm-legend__v">{node().status}</span>
              </Show>
            </div>
            <Show when={node().type === 'work'}>
              <button
                type="button"
                class="swarm-legend__open"
                onClick={() => props.onOpen(node())}
              >
                Open in grid →
              </button>
            </Show>
          </>
        )}
      </Show>
    </div>
  );
};

export default SwarmMapLegend;
