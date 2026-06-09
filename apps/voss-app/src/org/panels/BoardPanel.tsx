import { For, Show } from 'solid-js';
import type { RunData, ReviewSidecar } from '../types';
import { cardsFromRunData, type BoardCard } from '../boardDerive';
import { paneIdForCard } from '../model/bridge';

// VADE-02 — 6-column Kanban, restyled in V14 chunk B to the cockpit mockup
// .card/.colhdr: role-colored left accent, title-first cards, badge row
// (id / risk·tier / mono budget / ● live / A·B reviewer dots), mini progress
// bar, and count-pill column headers (WIP-colored for In Progress).
// Columns render harness keys (data-col) with the mockup display labels;
// cards are grouped by their derived column. The selection contract is
// unchanged: data-card-id + onCardSelect(card.id).
const COLUMNS: Array<{ key: string; label: string; color: string }> = [
  { key: 'Backlog', label: 'Backlog', color: 'var(--org-col-backlog)' },
  { key: 'Planned', label: 'Planned', color: 'var(--org-col-todo)' },
  { key: 'InProgress', label: 'In Progress', color: 'var(--org-col-in-progress)' },
  { key: 'InReview', label: 'In Review', color: 'var(--org-col-in-review)' },
  { key: 'Done', label: 'Done', color: 'var(--org-col-done)' },
  { key: 'Blocked', label: 'Blocked', color: 'var(--org-col-blocked)' },
];

function budgetColor(pct: number): string {
  return pct >= 90
    ? 'var(--accent-red)'
    : pct >= 70
      ? 'var(--accent-amber)'
      : 'var(--accent-green)';
}

function roleColor(role: string | null): string {
  switch (role) {
    case 'planner':
    case 'pm':
      return 'var(--role-planner)';
    case 'reviewer':
    case 'reviewer-a':
    case 'reviewer-b':
      return 'var(--role-reviewer)';
    case 'watcher':
      return 'var(--role-watcher)';
    case 'user':
      return 'var(--role-user)';
    default:
      return 'var(--role-executor)';
  }
}

// Risk badge tint (mockup .b.risk-*): token text on a color-mix soft fill.
function riskBadgeColor(risk: string): string {
  return risk === 'high'
    ? 'var(--accent-red)'
    : risk === 'low'
      ? 'var(--accent-green)'
      : 'var(--accent-amber)';
}

// A/B reviewer dot (mockup .abdot): verdict-tinted, grey while pending.
function verdictDotColor(verdict: string | null | undefined): string {
  if (!verdict) return 'var(--fg-3)';
  const v = verdict.toUpperCase();
  if (v === 'PASS') return 'var(--accent-green)';
  if (v === 'FAIL' || v === 'BLOCK') return 'var(--accent-red)';
  return 'var(--accent-amber)';
}

const badgeBase = {
  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
  'font-size': '11px',
  padding: '0 4px',
  'border-radius': '4px',
  background: 'var(--bg-3)',
  color: 'var(--fg-2)',
  'white-space': 'nowrap',
} as const;

function BoardCardView(props: {
  card: BoardCard;
  selected: boolean;
  onSelect: () => void;
  sidecar: ReviewSidecar | null;
}) {
  const pct = () =>
    props.card.limit > 0 ? (props.card.spent / props.card.limit) * 100 : 0;
  const rc = () => roleColor(props.card.role);
  // V14 chunk B: ● live badge when the id-bridge binds this card to a pane.
  const live = () => paneIdForCard(props.card.id) !== undefined;
  return (
    <div
      role="listitem"
      data-card-id={props.card.id}
      onClick={() => props.onSelect()}
      style={{
        background: 'var(--bg-2)',
        // Border stays a uniform shorthand (selection ring assertions read
        // style.border); the mockup's 3px role-colored left accent is the
        // inset box-shadow stripe below.
        border: props.selected ? '1px solid var(--focus)' : '1px solid var(--border)',
        'box-shadow': props.selected
          ? '0 0 0 1px var(--focus), inset 3px 0 0 var(--focus)'
          : `inset 3px 0 0 ${rc()}`,
        'border-radius': '6px',
        margin: '0 8px 8px',
        padding: '8px 8px 8px 12px',
        cursor: 'pointer',
        display: 'flex',
        'flex-direction': 'column',
        gap: '4px',
      }}
    >
      {/* Title first (mockup .card .ct): 12px fg-0, 2-line clamp. */}
      <div
        style={{
          'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
          'font-size': '12px',
          color: 'var(--fg-0)',
          'line-height': '1.3',
          overflow: 'hidden',
          display: '-webkit-box',
          '-webkit-line-clamp': '2',
          '-webkit-box-orient': 'vertical',
        }}
      >
        {props.card.title}
      </div>

      {/* Badge row (mockup .badges): id · risk·tier · budget · role · live · A/B. */}
      <div
        style={{
          display: 'flex',
          'flex-wrap': 'wrap',
          gap: '4px',
          'align-items': 'center',
        }}
      >
        <span
          style={{
            'font-family': 'var(--font-mono), monospace',
            'font-size': '11px',
            color: 'var(--fg-3)',
          }}
        >
          {props.card.id}
        </span>
        <span
          style={{
            ...badgeBase,
            color: riskBadgeColor(props.card.risk),
            background: `color-mix(in srgb, ${riskBadgeColor(props.card.risk)} 16%, transparent)`,
          }}
        >
          risk·{props.card.risk}
        </span>
        <Show when={props.card.limit > 0}>
          <span
            style={{
              ...badgeBase,
              'font-family': 'var(--font-mono), monospace',
              'font-variant-numeric': 'tabular-nums',
            }}
          >
            {props.card.spent}/{props.card.limit}
          </span>
        </Show>
        <Show when={props.card.role}>
          <span style={{ ...badgeBase, color: rc() }}>{props.card.role}</span>
        </Show>
        <Show when={live()}>
          <span
            style={{
              ...badgeBase,
              color: 'var(--accent-cyan)',
              background:
                'color-mix(in srgb, var(--accent-cyan) 16%, transparent)',
            }}
          >
            ● live
          </span>
        </Show>
        <Show when={props.sidecar}>
          {(sc) => (
            <span
              aria-label="Reviewer A/B verdicts"
              style={{
                display: 'inline-flex',
                gap: '4px',
                'align-items': 'center',
                'margin-left': 'auto',
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  'border-radius': '50%',
                  background: verdictDotColor(sc().a_verification?.result),
                }}
              />
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  'border-radius': '50%',
                  background: verdictDotColor(sc().b_verdict?.verdict),
                }}
              />
            </span>
          )}
        </Show>
      </div>

      {/* Mini progress bar (mockup .miniprog): spent/limit %. */}
      <Show when={props.card.limit > 0}>
        <div
          style={{
            height: '4px',
            background: 'var(--bg-3)',
            'border-radius': '2px',
            overflow: 'hidden',
            width: '100%',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, pct())}%`,
              background: budgetColor(pct()),
            }}
          />
        </div>
      </Show>
    </div>
  );
}

export default function BoardPanel(props: {
  data: RunData | null;
  onCardSelect?: (cardId: string) => void;
  selectedCardId?: string | null;
}) {
  const cards = () => cardsFromRunData(props.data);
  const colCards = (key: string) => cards().filter((c) => c.column === key);
  const sidecarFor = (id: string): ReviewSidecar | null =>
    props.data?.review[id] ?? null;

  return (
    <Show
      when={props.data}
      fallback={
        <div class="org-panel">
          <div class="org-empty">No board data for this run.</div>
        </div>
      }
    >
      <div class="org-panel" style={{ 'flex-direction': 'row', overflow: 'hidden' }}>
        <For each={COLUMNS}>
          {(col) => (
            <div
              class="org-board-col"
              data-col={col.key}
              role="list"
              style={{
                flex: '1',
                'min-width': '0',
                'overflow-y': 'auto',
                'border-right': '1px solid var(--border)',
              }}
            >
              <div
                class="org-board-col__header"
                style={{
                  color: col.color,
                  'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
                  'font-size': '11px',
                  'font-weight': '600',
                  'text-transform': 'uppercase',
                  'letter-spacing': '0.04em',
                  padding: '8px',
                  height: '32px',
                  'box-sizing': 'border-box',
                  display: 'flex',
                  'align-items': 'center',
                  gap: '4px',
                  background: 'var(--bg-1)',
                  'border-bottom': '1px solid var(--border)',
                }}
              >
                {col.label}
                {/* Count pill (mockup .colhdr .cn) — WIP-colored for In Progress. */}
                <span
                  class="org-board-col__count"
                  style={{
                    'margin-left': 'auto',
                    'font-family': 'var(--font-mono), monospace',
                    'font-variant-numeric': 'tabular-nums',
                    'font-size': '11px',
                    color:
                      col.key === 'InProgress' && colCards(col.key).length > 0
                        ? 'var(--accent-amber)'
                        : 'var(--fg-3)',
                    background: 'var(--bg-3)',
                    'border-radius': '8px',
                    padding: '0 6px',
                  }}
                >
                  {colCards(col.key).length}
                </span>
              </div>
              <Show
                when={colCards(col.key).length > 0}
                fallback={
                  <div
                    style={{
                      color: 'var(--fg-3)',
                      'font-size': '11px',
                      'text-align': 'center',
                      'margin-top': '24px',
                    }}
                  >
                    No cards
                  </div>
                }
              >
                <div style={{ 'padding-top': '8px' }}>
                  <For each={colCards(col.key)}>
                    {(card) => (
                      <BoardCardView
                        card={card}
                        selected={card.id === props.selectedCardId}
                        onSelect={() => props.onCardSelect?.(card.id)}
                        sidecar={sidecarFor(card.id)}
                      />
                    )}
                  </For>
                </div>
              </Show>
            </div>
          )}
        </For>
      </div>
    </Show>
  );
}
