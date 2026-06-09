// VCKP-05 — bottom gate bar (budget / scope / confidence / claims).
//
// Reflects the SELECTED card's envelope {limit, spent} (SessionTreeNode.envelope,
// types.ts:10-13,84-95). Budget threshold coloring is COPIED verbatim from
// BoardPanel.tsx:24-30 (budgetColor is a private helper there — not exported —
// so it is copied, not imported, per the plan).
//
// Per-card confidence is a LIVE SSE event, never a snapshot field. It renders
// ONLY from the normalized model `Card.liveStatus` overlay passed via the
// optional `liveCard` prop — NEVER from RunData. Absent live card → hidden.

import { Show } from 'solid-js';
import type { RunData } from '../types';
import type { Card } from '../model/normalized';
import { runData } from '../orgStore';
import { selectedCardId } from '../selection';

// COPIED from BoardPanel.tsx:24-30 (private helper; copy not import).
function budgetColor(pct: number): string {
  return pct >= 90
    ? 'var(--accent-red)'
    : pct >= 70
      ? 'var(--accent-amber)'
      : 'var(--accent-green)';
}

const mono = {
  'font-family': 'var(--font-mono), monospace',
} as const;

/**
 * Bottom bar reading the global `selectedCardId()` / `runData()`. A `data` prop
 * is accepted (defaults to global `runData()`) to keep CockpitShell wiring thin.
 * `liveCard` is the only source for per-card confidence (live overlay).
 */
export default function GateBar(props: {
  data?: RunData | null;
  liveCard?: Card | null;
}) {
  const data = (): RunData | null =>
    props.data !== undefined ? props.data : runData();

  const node = () => {
    const id = selectedCardId();
    if (!id) return null;
    return data()?.session_tree.nodes.find((n) => n.id === id) ?? null;
  };

  const limit = () => node()?.envelope.limit ?? 0;
  const spent = () => node()?.envelope.spent ?? 0;
  const pct = () => (limit() > 0 ? (spent() / limit()) * 100 : 0);
  const scope = () => node()?.scope ?? null;

  const unsupportedCount = () => data()?.audit?.unsupported_claims.length ?? 0;

  // LIVE-only: per-card confidence comes from the live overlay, never RunData.
  const confidence = () => props.liveCard?.liveStatus ?? null;

  return (
    <Show
      when={selectedCardId()}
      fallback={
        <div
          style={{
            display: 'flex',
            'align-items': 'center',
            padding: '0 12px',
            height: '100%',
            color: 'var(--fg-3)',
            'font-size': '11px',
          }}
        >
          No card selected.
        </div>
      }
    >
      <div
        style={{
          display: 'flex',
          'align-items': 'center',
          gap: '16px',
          padding: '0 12px',
          height: '100%',
          'font-size': '11px',
          color: 'var(--fg-0)',
          background: 'var(--bg-1)',
          'border-top': '1px solid var(--border)',
        }}
      >
        {/* Budget: monospace numerics + threshold-colored bar */}
        <div style={{ display: 'flex', 'align-items': 'center', gap: '6px' }}>
          <span style={{ color: 'var(--fg-3)' }}>Budget</span>
          <span style={{ ...mono, color: budgetColor(pct()) }}>
            {spent()}/{limit()}
          </span>
          <div style={{ width: '64px', height: '4px', background: 'var(--bg-3)' }}>
            <div
              style={{
                height: '100%',
                width: `${Math.min(100, pct())}%`,
                background: budgetColor(pct()),
              }}
            />
          </div>
        </div>

        {/* Scope chip */}
        <Show when={scope()}>
          <span
            style={{
              ...mono,
              padding: '1px 6px',
              'border-radius': '3px',
              background: 'var(--bg-2)',
              color: 'var(--fg-2)',
              border: '1px solid var(--border)',
            }}
          >
            {scope()}
          </span>
        </Show>

        {/* Unsupported-claims count (from AuditReport.unsupported_claims) */}
        <div style={{ display: 'flex', 'align-items': 'center', gap: '4px' }}>
          <span style={{ color: 'var(--fg-3)' }}>Claims</span>
          <span
            style={{
              ...mono,
              color: unsupportedCount() > 0 ? 'var(--accent-amber)' : 'var(--fg-2)',
            }}
          >
            {unsupportedCount()}
          </span>
        </div>

        {/* Per-card confidence — LIVE overlay only, hidden when no live card */}
        <Show when={confidence()}>
          <div style={{ display: 'flex', 'align-items': 'center', gap: '4px' }}>
            <span style={{ color: 'var(--fg-3)' }}>Confidence</span>
            <span style={{ ...mono, color: 'var(--fg-2)' }}>{confidence()}</span>
          </div>
        </Show>
      </div>
    </Show>
  );
}
