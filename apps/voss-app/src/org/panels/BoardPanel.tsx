import { For, Show } from 'solid-js';
import type { RunData } from '../types';
import { cardsFromRunData, type BoardCard } from '../boardDerive';

// VADE-02 — 6-column Kanban. Columns render harness keys (data-col) with the
// UI-SPEC display labels; cards are grouped by their derived column.
const COLUMNS: Array<{ key: string; label: string; color: string }> = [
  { key: 'Backlog', label: 'Backlog', color: 'var(--org-col-backlog)' },
  { key: 'Planned', label: 'Todo', color: 'var(--org-col-todo)' },
  { key: 'InProgress', label: 'In Progress', color: 'var(--org-col-in-progress)' },
  { key: 'InReview', label: 'In Review', color: 'var(--org-col-in-review)' },
  { key: 'Done', label: 'Done', color: 'var(--org-col-done)' },
  { key: 'Blocked', label: 'Blocked', color: 'var(--org-col-blocked)' },
];

function riskTint(risk: string): string {
  return risk === 'high'
    ? 'var(--card-risk-high)'
    : risk === 'low'
      ? 'var(--card-risk-low)'
      : 'var(--card-risk-med)';
}

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

function BoardCardView(props: {
  card: BoardCard;
  selected: boolean;
  onSelect: () => void;
}) {
  const pct = () =>
    props.card.limit > 0 ? (props.card.spent / props.card.limit) * 100 : 0;
  const rc = () => roleColor(props.card.role);
  return (
    <div
      role="listitem"
      data-card-id={props.card.id}
      onClick={() => props.onSelect()}
      style={{
        'min-height': '64px',
        background: `linear-gradient(${riskTint(props.card.risk)}, ${riskTint(props.card.risk)}), var(--bg-2)`,
        border: props.selected ? '1px solid var(--focus)' : '1px solid var(--border)',
        'box-shadow': props.selected ? '0 0 0 1px var(--focus)' : 'none',
        margin: '0 8px 4px',
        padding: '8px',
        cursor: 'pointer',
        display: 'flex',
        'flex-direction': 'column',
        gap: '4px',
      }}
    >
      <div style={{ 'font-family': 'var(--font-mono), monospace', 'font-size': '11px', color: 'var(--fg-3)' }}>
        {props.card.id}
      </div>
      <div
        style={{
          'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
          'font-size': '12px',
          color: 'var(--fg-0)',
          overflow: 'hidden',
          display: '-webkit-box',
          '-webkit-line-clamp': '2',
          '-webkit-box-orient': 'vertical',
        }}
      >
        {props.card.title}
      </div>
      <Show when={props.card.role}>
        <span
          style={{
            'align-self': 'flex-start',
            'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
            'font-size': '11px',
            'font-weight': '500',
            color: rc(),
            background: 'color-mix(in srgb, currentColor 20%, transparent)',
            'border-radius': '3px',
            padding: '0 4px',
          }}
        >
          {props.card.role}
        </span>
      </Show>
      <span
        style={{
          'align-self': 'flex-start',
          'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
          'font-size': '11px',
          'font-weight': '500',
          'border-radius': '9999px',
          padding: '0 4px',
          color:
            props.card.risk === 'high'
              ? 'var(--accent-red)'
              : props.card.risk === 'low'
                ? 'var(--accent-green)'
                : 'var(--accent-amber)',
          background: 'var(--bg-2)',
        }}
      >
        {props.card.risk}
      </span>
      <div style={{ height: '4px', background: 'var(--bg-3)', width: '100%' }}>
        <div
          style={{
            height: '100%',
            width: `${Math.min(100, pct())}%`,
            background: budgetColor(pct()),
          }}
        />
      </div>
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
                  'font-weight': '500',
                  'text-transform': 'uppercase',
                  'letter-spacing': '0.08em',
                  padding: '8px',
                  height: '32px',
                  'box-sizing': 'border-box',
                  display: 'flex',
                  'align-items': 'center',
                  gap: '4px',
                  'border-bottom': '1px solid var(--border)',
                }}
              >
                {col.label}
                <span style={{ 'font-family': 'var(--font-mono), monospace', color: 'var(--fg-3)' }}>
                  ({colCards(col.key).length})
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
