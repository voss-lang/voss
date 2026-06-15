// V24-05 (VADE2-05) — Tasks mission-control surface.
//
// Managed work as a Linear-like status system (not a toolbar). Reuses the
// existing board derivation (cardsFromRunData + deriveColumn) and the live
// id-bridge / adoption registries — no re-derivation. Rows deep-link to the
// corresponding pane (bridge B) or review drawer via org/selection. Blocked
// rows surface an inline attention action (never a new modal).
//
// Data source: the module-level orgStore signals (runData/loading/loadError) —
// the surface is mounted prop-less inside PortalShell, so all state is read from
// the shared store (mirrors BoardPanel). Copy uses PRODUCT.md vocabulary
// ("Tasks", "steps"/"cards" for board items — never "Runs", never "tasks"
// inside a Task).

import { type Component, createSignal, For, Show } from 'solid-js';
import '../surfaces.css';
import { runData, loading, loadError } from '../../org/orgStore';
import { cardsFromRunData, type BoardCard } from '../../org/boardDerive';
import { paneIdForCard } from '../../org/model/bridge';
import { adoptionByPaneId } from '../../pane/adoptionRegistry';
import { requestOpenInGrid, requestOpenInReview } from '../../org/selection';
import { attentionQueue, type AttentionItem } from '../../org/attention/attentionQueue';

export type GroupKey =
  | 'active'
  | 'blocked'
  | 'reviewing'
  | 'done'
  | 'adopted'
  | 'terminal-agent';

export interface GroupMeta {
  key: GroupKey;
  label: string;
  color: string;
}

// UI-SPEC §Component Inventory 4 group taxonomy + accent dots.
export const GROUPS: GroupMeta[] = [
  { key: 'active', label: 'ACTIVE', color: 'var(--accent-cyan)' },
  { key: 'blocked', label: 'BLOCKED', color: 'var(--accent-red)' },
  { key: 'reviewing', label: 'REVIEWING', color: 'var(--accent-amber)' },
  { key: 'done', label: 'DONE', color: 'var(--accent-green)' },
  { key: 'adopted', label: 'ADOPTED', color: 'var(--accent-green)' },
  { key: 'terminal-agent', label: 'TERMINAL AGENT', color: 'var(--fg-3)' },
];

// deriveColumn keys → display group (display-layer rename only; code keys
// unchanged, D-09). Anything off-taxonomy (e.g. Backlog) reads as active.
const COLUMN_TO_GROUP: Record<string, GroupKey> = {
  InProgress: 'active',
  Backlog: 'active',
  Blocked: 'blocked',
  InReview: 'reviewing',
  Done: 'done',
};

/**
 * Group a card by its real signals: a pane-bound card is a terminal agent
 * (adopted if the pane is in the adoption registry); otherwise its board column.
 */
export function groupForCard(card: BoardCard): GroupKey {
  const paneId = paneIdForCard(card.id);
  if (paneId && adoptionByPaneId()[paneId]) return 'adopted';
  if (paneId) return 'terminal-agent';
  return COLUMN_TO_GROUP[card.column] ?? 'active';
}

export function groupCards(cards: BoardCard[]): Record<GroupKey, BoardCard[]> {
  const out: Record<GroupKey, BoardCard[]> = {
    active: [],
    blocked: [],
    reviewing: [],
    done: [],
    adopted: [],
    'terminal-agent': [],
  };
  for (const card of cards) out[groupForCard(card)].push(card);
  return out;
}

/** Deep link: pane-bound card → grid; otherwise → review drawer. */
function openCard(card: BoardCard): void {
  const paneId = paneIdForCard(card.id);
  if (paneId) requestOpenInGrid(paneId);
  else requestOpenInReview(card.id);
}

/** A single Task row + its inline attention action. Self-contained expand state
 *  so it is reusable from OverviewSurface. */
export const TaskRow: Component<{ card: BoardCard; color: string }> = (props) => {
  const [expanded, setExpanded] = createSignal(false);
  const attn = (): AttentionItem | undefined =>
    attentionQueue().find((a) => a.cardId === props.card.id);

  return (
    <div class="surface-row-wrap">
      <div class="surface-row-line">
        <button
          type="button"
          class="surface-row"
          aria-label={`Open Task: ${props.card.title}`}
          onClick={() => openCard(props.card)}
        >
          <span class="surface-row__dot" style={{ background: props.color }} />
          <span class="surface-row__name">{props.card.title}</span>
          <Show when={props.card.role}>
            <span class="surface-row__meta">{props.card.role}</span>
          </Show>
          <span class="surface-row__meta surface-row__meta--cost">
            ${props.card.spent}
          </span>
        </button>
        <Show when={attn()}>
          <button
            type="button"
            class="surface-row__attn"
            aria-label={`Attention on Task: ${props.card.title}`}
            aria-expanded={expanded() ? 'true' : 'false'}
            onClick={() => setExpanded((v) => !v)}
          >
            !
          </button>
        </Show>
      </div>
      <Show when={expanded() && attn()}>
        <div class="surface-action" role="group" aria-label="Attention action">
          <span class="surface-action__desc">{attn()!.summary}</span>
          <button
            type="button"
            class="surface-action__btn"
            onClick={() => {
              requestOpenInReview(props.card.id);
              setExpanded(false);
            }}
          >
            Review →
          </button>
        </div>
      </Show>
    </div>
  );
};

const TasksSurface: Component = () => {
  const cards = () => cardsFromRunData(runData());
  const grouped = () => groupCards(cards());

  return (
    <div class="surface" role="tabpanel" aria-label="Tasks">
      <div class="surface__header">
        <span class="surface__title">Tasks</span>
        <span class="surface__count">{cards().length}</span>
      </div>
      <Show
        when={!loading()}
        fallback={
          <div class="org-spinner">
            <span class="org-spinner__glyph">⟳</span>
          </div>
        }
      >
        <Show
          when={!loadError()}
          fallback={
            <div class="org-error-state">
              <p class="org-error-state__heading">Couldn't load Tasks.</p>
              <p class="org-error-state__body">Check that Voss is running.</p>
            </div>
          }
        >
          <Show
            when={cards().length > 0}
            fallback={
              <div class="surface-empty">
                <p class="surface-empty__title">No active Tasks</p>
                <p class="surface-empty__hint">Use ⌘K to ask Voss to start one.</p>
              </div>
            }
          >
            <div class="surface__body">
              <For each={GROUPS}>
                {(group) => (
                  <Show when={grouped()[group.key].length > 0}>
                    <div class="surface-group">
                      <div class="surface-group__header">
                        <span
                          class="surface-group__dot"
                          style={{ background: group.color }}
                        />
                        <span class="surface-group__name">{group.label}</span>
                        <span class="surface-group__count">
                          {grouped()[group.key].length}
                        </span>
                      </div>
                      <For each={grouped()[group.key]}>
                        {(card) => <TaskRow card={card} color={group.color} />}
                      </For>
                    </div>
                  </Show>
                )}
              </For>
            </div>
          </Show>
        </Show>
      </Show>
    </div>
  );
};

export default TasksSurface;
