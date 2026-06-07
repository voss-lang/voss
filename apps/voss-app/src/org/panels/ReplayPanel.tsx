import { For, Show, createSignal } from 'solid-js';
import type { RunData, SessionTreeNode, CardSnapshot } from '../types';
import { computeBoardAtStep } from '../replayReducer';

// VADE-10 — step through persisted transitions; the board snapshot at each step
// is computed by the pure client-side reducer (D-05/D-06: board/card only).
// Other panels stay final-snapshot. The replay board is READ-ONLY.

const COLUMNS: Array<{ key: string; label: string; color: string }> = [
  { key: 'Backlog', label: 'Backlog', color: 'var(--org-col-backlog)' },
  { key: 'Planned', label: 'Todo', color: 'var(--org-col-todo)' },
  { key: 'InProgress', label: 'In Progress', color: 'var(--org-col-in-progress)' },
  { key: 'InReview', label: 'In Review', color: 'var(--org-col-in-review)' },
  { key: 'Done', label: 'Done', color: 'var(--org-col-done)' },
  { key: 'Blocked', label: 'Blocked', color: 'var(--org-col-blocked)' },
];

function countSteps(nodes: SessionTreeNode[]): number {
  let n = 0;
  for (const node of nodes) {
    for (const t of node.transitions) if (t.kind === 'board.transition') n++;
  }
  return n;
}

function riskTint(risk: string): string {
  return risk === 'high'
    ? 'var(--card-risk-high)'
    : risk === 'low'
      ? 'var(--card-risk-low)'
      : 'var(--card-risk-med)';
}

function ReplayCard(props: { card: CardSnapshot }) {
  return (
    <div
      role="listitem"
      data-card-id={props.card.id}
      style={{
        'min-height': '48px',
        background: `linear-gradient(${riskTint(props.card.risk)}, ${riskTint(props.card.risk)}), var(--bg-2)`,
        border: '1px solid var(--border)',
        margin: '0 8px 4px',
        padding: '8px',
        display: 'flex',
        'flex-direction': 'column',
        gap: '4px',
      }}
    >
      <div style={{ 'font-family': 'var(--font-mono), monospace', 'font-size': '11px', color: 'var(--fg-3)' }}>
        {props.card.id}
      </div>
      <Show when={props.card.role}>
        <span style={{ 'font-family': 'var(--font-ui), Inter, system-ui, sans-serif', 'font-size': '11px', color: 'var(--fg-2)' }}>
          {props.card.role}
        </span>
      </Show>
    </div>
  );
}

export default function ReplayPanel(props: { data: RunData | null }) {
  const [step, setStep] = createSignal(0);

  // Pitfall 3: strip Solid store proxies before the pure reducer.
  // NEVER produce()/structuredClone() here.
  const plainNodes = (): SessionTreeNode[] =>
    JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []));

  const total = () => countSteps(plainNodes());
  const frame = () => computeBoardAtStep(plainNodes(), step());

  const atStart = () => step() <= 0;
  const atEnd = () => step() >= total() - 1;

  return (
    <div class="org-panel">
      <Show
        when={total() > 0}
        fallback={
          <div class="org-empty">
            No transition history for this run. Replay requires persisted
            transitions.
          </div>
        }
      >
        {/* Controls bar */}
        <div
          style={{
            display: 'flex',
            'align-items': 'center',
            gap: '8px',
            height: '32px',
            'flex-shrink': '0',
            padding: '0 16px',
            background: 'var(--bg-1)',
            'border-bottom': '1px solid var(--border)',
          }}
        >
          <button
            aria-label="Previous step"
            aria-disabled={atStart()}
            disabled={atStart()}
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            style={{
              background: 'transparent',
              border: 'none',
              'font-family': 'var(--font-mono), monospace',
              'font-size': '14px',
              color: atStart() ? 'var(--fg-3)' : 'var(--fg-1)',
              cursor: atStart() ? 'default' : 'pointer',
            }}
          >
            ‹
          </button>
          <span
            style={{
              width: '6px',
              height: '6px',
              'border-radius': '50%',
              background: 'var(--focus)',
            }}
          />
          <span
            style={{
              'min-width': '64px',
              'text-align': 'center',
              'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
              'font-size': '11px',
              'font-weight': '500',
              color: 'var(--fg-2)',
            }}
          >
            Step {step() + 1} / {total()}
          </span>
          <button
            aria-label="Next step"
            aria-disabled={atEnd()}
            disabled={atEnd()}
            onClick={() => setStep((s) => Math.min(total() - 1, s + 1))}
            style={{
              background: 'transparent',
              border: 'none',
              'font-family': 'var(--font-mono), monospace',
              'font-size': '14px',
              color: atEnd() ? 'var(--fg-3)' : 'var(--fg-1)',
              cursor: atEnd() ? 'default' : 'pointer',
            }}
          >
            ›
          </button>
          <span
            style={{
              flex: '1',
              'min-width': '0',
              'margin-left': '16px',
              'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
              'font-size': '11px',
              color: 'var(--fg-2)',
              overflow: 'hidden',
              'text-overflow': 'ellipsis',
              'white-space': 'nowrap',
            }}
          >
            {frame().eventLabel}
          </span>
        </div>

        {/* Other-panels notice (D-06) */}
        <div
          style={{
            height: '24px',
            'flex-shrink': '0',
            display: 'flex',
            'align-items': 'center',
            'justify-content': 'center',
            'border-bottom': '1px solid var(--border)',
            'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
            'font-size': '11px',
            color: 'var(--fg-3)',
          }}
        >
          Audit, Verdict, Budget, and Scope panels show final-run state only.
        </div>

        {/* Read-only board snapshot */}
        <div style={{ flex: '1', 'min-height': '0', display: 'flex', overflow: 'hidden', position: 'relative' }}>
          <span
            style={{
              position: 'absolute',
              top: '4px',
              right: '8px',
              'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
              'font-size': '11px',
              'font-weight': '500',
              'letter-spacing': '0.12em',
              color: 'var(--fg-3)',
              'z-index': '1',
            }}
          >
            REPLAY
          </span>
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
                    'border-bottom': '1px solid var(--border)',
                  }}
                >
                  {col.label} ({(frame().columns[col.key] ?? []).length})
                </div>
                <div style={{ 'padding-top': '8px' }}>
                  <For each={frame().columns[col.key] ?? []}>
                    {(card) => <ReplayCard card={card} />}
                  </For>
                </div>
              </div>
            )}
          </For>
        </div>
      </Show>
    </div>
  );
}
