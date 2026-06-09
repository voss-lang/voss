// VCKP-05 — persistent Card detail drawer (D-02/D-07/D-08).
//
// Composes the EXISTING V11 panel bodies as drawer sections — it does NOT
// rewrite any panel internals (D-02 reuse-not-rewrite). Panels are imported
// verbatim from ../panels/* and wired with the SAME prop signatures the old
// OrgViewShell tab switch used (OrgViewShell.tsx:211-248).
//
// Selection is the single global source of truth (../selection). When no card
// is selected the drawer renders a no-selection empty state (D-08), mirroring
// the `<Show ... fallback>` idiom in BoardPanel.tsx:149-155.

import { Show } from 'solid-js';
import type { RunData } from '../types';
import { runData } from '../orgStore';
import { selectedCardId, setSelectedCardId, requestOpenInGrid } from '../selection';
import { paneIdForCard } from '../model/bridge';
import AuditPanel from '../panels/AuditPanel';
import VerdictPanel from '../panels/VerdictPanel';
import DiffPanel from '../panels/DiffPanel';
import ScopePanel from '../panels/ScopePanel';
import BudgetPanel from '../panels/BudgetPanel';
import BlockedPanel from '../panels/BlockedPanel';

/**
 * Persistent drawer. Reads the global `selectedCardId()` / `runData()`. A
 * `data` prop is accepted so CockpitShell may pass the snapshot explicitly, but
 * it defaults to the global `runData()` accessor to keep the shell wiring thin.
 */
export default function CardDrawer(props: { data?: RunData | null }) {
  const data = (): RunData | null =>
    props.data !== undefined ? props.data : runData();
  // D-07: the bound live pane for the selected card (undefined for pure
  // snapshot cards). Drives the "Open in grid" disabled-with-reason state.
  const boundPaneId = (): string | undefined => {
    const id = selectedCardId();
    return id ? paneIdForCard(id) : undefined;
  };

  return (
    <Show
      when={selectedCardId()}
      fallback={
        <div class="org-panel">
          <div class="org-empty">Select a card to see its details.</div>
        </div>
      }
    >
      <div
        class="org-panel"
        style={{
          'flex-direction': 'column',
          gap: '12px',
          'overflow-y': 'auto',
          padding: '12px',
        }}
      >
        {/* D-07: read-only live-pane peek (stub — pane-output tail lands later) */}
        <section
          style={{
            border: '1px solid var(--border)',
            background: 'var(--bg-2)',
            padding: '8px',
            display: 'flex',
            'flex-direction': 'column',
            gap: '8px',
          }}
        >
          <div
            style={{
              'font-family': 'var(--font-mono), monospace',
              'font-size': '11px',
              color: 'var(--fg-3)',
            }}
          >
            {selectedCardId()}
          </div>
          <Show
            when={boundPaneId()}
            fallback={
              <div style={{ color: 'var(--fg-3)', 'font-size': '11px' }}>
                No live pane bound to this card.
              </div>
            }
          >
            <div style={{ color: 'var(--fg-3)', 'font-size': '11px' }}>
              Live pane output preview unavailable.
            </div>
          </Show>
          <button
            type="button"
            onClick={() => {
              const p = boundPaneId();
              if (p) requestOpenInGrid(p);
            }}
            disabled={!boundPaneId()}
            title={
              boundPaneId() ? 'Open this card in the grid' : 'No live pane bound to this card'
            }
            style={{
              'align-self': 'flex-start',
              'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
              'font-size': '11px',
              padding: '4px 8px',
              background: 'var(--bg-3)',
              color: boundPaneId() ? 'var(--fg-0)' : 'var(--fg-3)',
              border: '1px solid var(--border)',
              cursor: boundPaneId() ? 'pointer' : 'not-allowed',
            }}
          >
            Open in grid
          </button>
        </section>

        {/* Existing panel bodies reused verbatim (D-02). */}
        <VerdictPanel data={data()} />
        <DiffPanel
          data={data()}
          selectedCardId={selectedCardId()}
          onCardSelect={setSelectedCardId}
        />
        <ScopePanel data={data()} />
        <BudgetPanel data={data()} />
        <BlockedPanel data={data()} />
        <AuditPanel data={data()} />
      </div>
    </Show>
  );
}
