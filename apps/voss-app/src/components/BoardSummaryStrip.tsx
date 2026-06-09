// V14 chunk C — Live Work board summary strip (mockup .summary / .scol).
//
// A thin, read-only digest of the loaded run's board, mounted by App UNDER the
// RunCommandBar inside the Live-Work-only container (Run Review shows the full
// board, so the strip never renders there). Data is the snapshot plane:
// cardsFromRunData(runData()) — the exact deriveColumn columns the cockpit
// board renders. No run loaded (zero cards) → renders NOTHING (no dead
// chrome). Clicking a chip is the opt-in jump to Run Review (App flips
// orgViewOpen).
//
// Styling: A12 tokens only, inline styles (mirrors StatusBar). Column dot
// colors match the cockpit board's --org-col-* RESOLUTIONS — those tokens are
// scoped to .org-view-shell and unavailable out here, so the base tokens they
// resolve to are used directly.

import { createMemo, For, Show } from 'solid-js';
import { runData } from '../org/orgStore';
import { cardsFromRunData } from '../org/boardDerive';

const COLUMNS: Array<{ key: string; label: string; color: string }> = [
  { key: 'Backlog', label: 'Backlog', color: 'var(--fg-3)' },
  { key: 'Planned', label: 'Planned', color: 'var(--fg-2)' },
  { key: 'InProgress', label: 'In Progress', color: 'var(--accent-cyan)' },
  { key: 'InReview', label: 'In Review', color: 'var(--accent-amber)' },
  { key: 'Done', label: 'Done', color: 'var(--accent-green)' },
  { key: 'Blocked', label: 'Blocked', color: 'var(--accent-red)' },
];

export type BoardSummaryStripProps = {
  /** Opt-in jump to Run Review (App flips orgViewOpen). */
  onOpen: () => void;
};

export default function BoardSummaryStrip(props: BoardSummaryStripProps) {
  const counts = createMemo(() => {
    const cards = cardsFromRunData(runData());
    const byColumn: Record<string, number> = {};
    for (const card of cards) {
      byColumn[card.column] = (byColumn[card.column] ?? 0) + 1;
    }
    return { total: cards.length, byColumn };
  });

  return (
    <Show when={counts().total > 0}>
      <div
        role="region"
        aria-label="Board summary"
        style={{
          flex: '0 0 auto',
          display: 'flex',
          'align-items': 'center',
          gap: '8px',
          padding: '4px 12px',
          background: 'var(--bg-0)',
          'border-bottom': '1px solid var(--border)',
          'overflow-x': 'auto',
          'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
        }}
      >
        <span
          style={{
            'font-size': '11px',
            'font-weight': '600',
            'text-transform': 'uppercase',
            'letter-spacing': '0.08em',
            color: 'var(--fg-3)',
            'flex-shrink': '0',
          }}
        >
          RUN
        </span>
        <For each={COLUMNS}>
          {(col) => (
            <button
              type="button"
              title="Open Run Review"
              onClick={() => props.onOpen()}
              style={{
                display: 'inline-flex',
                'align-items': 'center',
                gap: '4px',
                'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                'font-size': '11px',
                color: 'var(--fg-2)',
                background: 'var(--bg-2)',
                border: '1px solid var(--border)',
                'border-radius': '4px',
                padding: '4px 8px',
                'white-space': 'nowrap',
                cursor: 'pointer',
                'flex-shrink': '0',
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: '6px',
                  height: '6px',
                  'border-radius': '50%',
                  background: col.color,
                }}
              />
              <span>{col.label}</span>
              <span style={{ color: 'var(--fg-0)', 'font-weight': '600' }}>
                {counts().byColumn[col.key] ?? 0}
              </span>
            </button>
          )}
        </For>
      </div>
    </Show>
  );
}
