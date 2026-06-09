// V14 chunk B — horizontal timeline rail (mockup .timeline / .tl-track).
//
// Replaces the vertical SessionTreePanel+ReplayPanel rail position with a
// horizontal track of run milestones derived from the persisted board/card
// transitions: idea -> cards -> one node per card (terminal state colors it)
// -> sign-off. Done nodes are green, blocked red, in-flight nodes carry the
// focus ring (mockup .tl-node.cur).
//
// The derivation reuses the verified boardDerive column algorithm (D-02:
// restyle, don't re-derive wrong). Card nodes keep the `data-node-id` attr the
// CockpitShell selection effect already queries, so selecting a board card
// highlights its node here (.cockpit-rail__selected); clicking a node selects
// the card back (single global selection).

import { For, Show } from 'solid-js';
import type { RunData } from '../types';
import { cardsFromRunData } from '../boardDerive';

export type TimelineNodeState = 'done' | 'cur' | 'blocked' | 'pending';

export interface TimelineNodeView {
  key: string;
  label: string;
  state: TimelineNodeState;
  /** Present only for per-card nodes — wired to the global selection. */
  cardId?: string;
}

function shortId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

/** Pure milestone derivation: idea -> cards -> per-card terminal -> sign-off. */
export function timelineNodesFromRunData(
  data: RunData | null,
): TimelineNodeView[] {
  if (!data) return [];
  const cards = cardsFromRunData(data);
  const nodes: TimelineNodeView[] = [
    { key: 'idea', label: 'idea', state: 'done' },
    { key: 'cards', label: 'cards', state: cards.length > 0 ? 'done' : 'pending' },
  ];
  for (const c of cards) {
    const state: TimelineNodeState =
      c.column === 'Done'
        ? 'done'
        : c.column === 'Blocked'
          ? 'blocked'
          : c.column === 'InProgress' || c.column === 'InReview'
            ? 'cur'
            : 'pending';
    const glyph = state === 'done' ? '✓' : state === 'blocked' ? '⚠' : '';
    nodes.push({
      key: c.id,
      cardId: c.id,
      label: `${shortId(c.id)}${glyph}`,
      state,
    });
  }
  const final = data.run_final ?? data.audit?.run_final ?? null;
  nodes.push({
    key: 'sign-off',
    label: 'sign-off',
    state: final?.sign_off ? 'done' : 'pending',
  });
  return nodes;
}

/** Total persisted board.transition count (the replay step total). */
export function transitionCount(data: RunData | null): number {
  if (!data) return 0;
  let n = 0;
  for (const node of data.session_tree.nodes) {
    for (const t of node.transitions) if (t.kind === 'board.transition') n++;
  }
  return n;
}

export default function TimelineRail(props: {
  data: RunData | null;
  onNodeSelect?: (cardId: string) => void;
}) {
  const nodes = () => timelineNodesFromRunData(props.data);

  return (
    <Show
      when={nodes().length > 0}
      fallback={<div class="cockpit-tl-empty">No run loaded.</div>}
    >
      <div class="cockpit-tl-hdr">
        Run timeline
        <span class="cockpit-tl-hdr__meta">
          {transitionCount(props.data)} transitions
        </span>
      </div>
      <div class="cockpit-tl-track">
        <div class="cockpit-tl-line" />
        <For each={nodes()}>
          {(n) => (
            <div
              class={`cockpit-tl-node cockpit-tl-node--${n.state}${n.cardId ? ' cockpit-tl-node--card' : ''}`}
              data-node-id={n.cardId}
              role={n.cardId ? 'button' : undefined}
              onClick={() => {
                if (n.cardId) props.onNodeSelect?.(n.cardId);
              }}
            >
              <span class="cockpit-tl-node__pt" />
              <span class="cockpit-tl-node__lb">{n.label}</span>
            </div>
          )}
        </For>
      </div>
    </Show>
  );
}
