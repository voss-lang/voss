import { For, Show, createSignal } from 'solid-js';
import type { RunData, SessionTreeNode } from '../types';
import { deriveColumn } from '../boardDerive';
import { currentRunId, currentCwd, currentCliBinary } from '../orgStore';
import DecisionDialog from '../DecisionDialog';
import type { DecisionAction } from '../decisionActions';

// VADE-09 — blocked-card list + decision flow. A card is blocked when its
// derived column is "Blocked" (reuses the verified boardDerive algorithm).
// Only `approve` has a non-interactive CLI surface; reject/unblock render
// disabled-with-explanation (one-write-path invariant — no invented behavior).

interface BlockedCard {
  id: string;
  reason: string;
}

function reasonFor(node: SessionTreeNode): string {
  const final = node.terminal_state?.final;
  if (typeof final === 'string' && final.length > 0) return final;
  let lastOutcome = '';
  for (const t of node.transitions) {
    if (t.kind === 'board.transition' && t.outcome) lastOutcome = t.outcome;
  }
  return lastOutcome || 'Blocked — no reason recorded';
}

function blockedCards(data: RunData | null): BlockedCard[] {
  if (!data) return [];
  return data.session_tree.nodes
    .filter((n) => deriveColumn(n) === 'Blocked')
    .map((n) => ({ id: n.id, reason: reasonFor(n) }));
}

const disabledBtn = {
  background: 'var(--bg-2)',
  border: '1px solid var(--border)',
  'border-radius': '3px',
  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
  'font-size': '11px',
  'font-weight': '500',
  height: '28px',
  padding: '0 8px',
  color: 'var(--fg-3)',
  cursor: 'not-allowed',
  opacity: '0.6',
} as const;

const NO_CLI_TITLE =
  'No non-interactive CLI command exists yet — use the harness sign-off';

export default function BlockedPanel(props: { data: RunData | null }) {
  const [dialogCard, setDialogCard] = createSignal<string | null>(null);
  const cards = () => blockedCards(props.data);
  const runId = () => currentRunId() ?? props.data?.run_id ?? '';

  return (
    <div class="org-panel">
      <Show
        when={cards().length > 0}
        fallback={<div class="org-empty">No blocked cards in this run.</div>}
      >
        <div style={{ flex: '1', 'overflow-y': 'auto' }}>
          <For each={cards()}>
            {(card) => (
              <div
                style={{
                  display: 'flex',
                  'align-items': 'center',
                  gap: '8px',
                  'min-height': '72px',
                  padding: '8px 16px',
                  'border-bottom': '1px solid var(--border)',
                }}
              >
                <div style={{ flex: '1', 'min-width': '0' }}>
                  <div
                    style={{
                      'font-family': 'var(--font-mono), monospace',
                      'font-size': '11px',
                      color: 'var(--accent-red)',
                    }}
                  >
                    {card.id}
                  </div>
                  <div
                    style={{
                      'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                      'font-size': '12px',
                      color: 'var(--fg-1)',
                      overflow: 'hidden',
                      display: '-webkit-box',
                      '-webkit-line-clamp': '2',
                      '-webkit-box-orient': 'vertical',
                    }}
                  >
                    {card.reason}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => setDialogCard(card.id)}
                    style={{
                      background: 'var(--bg-2)',
                      border: '1px solid var(--border)',
                      'border-radius': '3px',
                      'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                      'font-size': '11px',
                      'font-weight': '500',
                      height: '28px',
                      padding: '0 8px',
                      color: 'var(--accent-green)',
                      cursor: 'pointer',
                    }}
                  >
                    Approve
                  </button>
                  <button disabled aria-disabled="true" title={NO_CLI_TITLE} style={disabledBtn}>
                    Reject
                  </button>
                  <button disabled aria-disabled="true" title={NO_CLI_TITLE} style={disabledBtn}>
                    Unblock
                  </button>
                </div>
              </div>
            )}
          </For>
        </div>
      </Show>

      <Show when={dialogCard()}>
        {(cardId) => (
          <DecisionDialog
            action={'approve' satisfies DecisionAction}
            runId={runId()}
            cardId={cardId()}
            cwd={currentCwd()}
            cliBinary={currentCliBinary()}
            onDismiss={() => setDialogCard(null)}
          />
        )}
      </Show>
    </div>
  );
}
