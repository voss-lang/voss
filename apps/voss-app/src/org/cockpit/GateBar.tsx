// VCKP-05 — bottom gate bar, extended in V14 chunk B to the mockup .gatebar:
// label + mini-bar + mono value per gate.
//
// Gates: Budget (selected card's envelope {limit, spent}, threshold-colored
// bar), Confidence (LIVE data only — the SSE overlay score or the normalized
// `liveCard.liveStatus` overlay; hidden on pure snapshots), Scope (declared
// scope text), Unsupported claims (AuditReport.unsupported_claims), and the
// right-aligned Sign-off state (RunFinal.sign_off + blocked-card count).
//
// Budget threshold coloring is COPIED verbatim from BoardPanel (budgetColor is
// a private helper there — not exported — so it is copied, not imported).
// Per-card confidence is NEVER a snapshot field — it renders only from live
// overlays, absent live data → hidden.

import { Show } from 'solid-js';
import type { RunData } from '../types';
import type { Card } from '../model/normalized';
import { runData } from '../orgStore';
import { selectedCardId } from '../selection';
import { liveOverlay } from '../live/sseClient';
import { deriveColumn } from '../boardDerive';

// COPIED from BoardPanel.tsx (private helper; copy not import).
function budgetColor(pct: number): string {
  return pct >= 90
    ? 'var(--accent-red)'
    : pct >= 70
      ? 'var(--accent-amber)'
      : 'var(--accent-green)';
}

const mono = {
  'font-family': 'var(--font-mono), monospace',
  'font-variant-numeric': 'tabular-nums',
} as const;

// Mockup .gate .gk — small uppercase gate label.
const gateKey = {
  color: 'var(--fg-3)',
  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
  'font-size': '11px',
  'text-transform': 'uppercase',
  'letter-spacing': '0.06em',
} as const;

const gateRow = {
  display: 'flex',
  'align-items': 'center',
  gap: '8px',
} as const;

// Mockup .gbar — mini progress track.
const barTrack = {
  width: '88px',
  height: '4px',
  background: 'var(--bg-3)',
  'border-radius': '2px',
  overflow: 'hidden',
} as const;

/**
 * Bottom bar reading the global `selectedCardId()` / `runData()`. A `data` prop
 * is accepted (defaults to global `runData()`) to keep CockpitShell wiring thin.
 * `liveCard` (normalized overlay) and the SSE liveOverlay are the only sources
 * for per-card confidence.
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

  // LIVE-only confidence: SSE overlay score (numeric, drives the bar) or the
  // normalized liveCard.liveStatus overlay (text) — never RunData.
  const overlayConfidence = (): number | undefined => {
    const id = selectedCardId();
    return id ? liveOverlay()[id]?.confidence : undefined;
  };
  const confidenceText = (): string | null => {
    const num = overlayConfidence();
    if (num !== undefined) return num.toFixed(2);
    return props.liveCard?.liveStatus ?? null;
  };

  // Sign-off state (run-level): RunFinal.sign_off, else blocked count.
  const runFinal = () => data()?.run_final ?? data()?.audit?.run_final ?? null;
  const blockedCount = () => {
    const d = data();
    if (!d) return 0;
    return d.session_tree.nodes.filter(
      (n) => n.parent_run_id !== null && deriveColumn(n) === 'Blocked',
    ).length;
  };
  const signOff = (): { text: string; color: string } => {
    const f = runFinal();
    if (f?.sign_off) {
      return f.sign_off.decision === 'approve'
        ? { text: 'approved', color: 'var(--accent-green)' }
        : { text: 'rejected', color: 'var(--accent-red)' };
    }
    if (blockedCount() > 0) {
      return {
        text: `locked · ${blockedCount()} blocked`,
        color: 'var(--accent-red)',
      };
    }
    if (f) return { text: 'ready', color: 'var(--accent-green)' };
    return { text: 'locked · run active', color: 'var(--fg-3)' };
  };

  // Component (not a shared node): both Show branches mount their own copy.
  const SignOffGate = () => (
    <Show when={data()}>
      <div style={{ ...gateRow, 'margin-left': 'auto' }}>
        <span style={gateKey}>Sign-off</span>
        <span style={{ ...mono, 'font-size': '11px', color: signOff().color }}>
          {signOff().text}
        </span>
      </div>
    </Show>
  );

  return (
    <Show
      when={selectedCardId()}
      fallback={
        <div
          style={{
            display: 'flex',
            'align-items': 'center',
            gap: '16px',
            padding: '0 12px',
            height: '100%',
            color: 'var(--fg-3)',
            'font-size': '11px',
          }}
        >
          No card selected.
          <SignOffGate />
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
        }}
      >
        {/* Budget: label + threshold-colored mini-bar + monospace numerics */}
        <div style={gateRow}>
          <span style={gateKey}>Budget</span>
          <div style={barTrack}>
            <div
              style={{
                height: '100%',
                width: `${Math.min(100, pct())}%`,
                background: budgetColor(pct()),
              }}
            />
          </div>
          <span style={{ ...mono, color: budgetColor(pct()) }}>
            {spent()}/{limit()}
          </span>
        </div>

        {/* Per-card confidence — LIVE overlay only, hidden when no live data */}
        <Show when={confidenceText()}>
          <div style={gateRow}>
            <span style={gateKey}>Confidence</span>
            <Show when={overlayConfidence() !== undefined}>
              <div style={barTrack}>
                <div
                  style={{
                    height: '100%',
                    width: `${Math.min(100, overlayConfidence()! * 100)}%`,
                    background: 'var(--accent-amber)',
                  }}
                />
              </div>
            </Show>
            <span style={{ ...mono, color: 'var(--fg-1)' }}>
              {confidenceText()}
            </span>
          </div>
        </Show>

        {/* Scope (declared) */}
        <Show when={scope()}>
          <div style={{ ...gateRow, 'min-width': '0' }}>
            <span style={gateKey}>Scope</span>
            <span
              style={{
                ...mono,
                color: 'var(--fg-1)',
                'min-width': '0',
                overflow: 'hidden',
                'text-overflow': 'ellipsis',
                'white-space': 'nowrap',
              }}
            >
              {scope()}
            </span>
          </div>
        </Show>

        {/* Unsupported-claims count (from AuditReport.unsupported_claims) */}
        <div style={gateRow}>
          <span style={gateKey}>Unsupported claims</span>
          <span
            style={{
              ...mono,
              color:
                unsupportedCount() > 0 ? 'var(--accent-amber)' : 'var(--fg-2)',
            }}
          >
            {unsupportedCount() > 0 ? `${unsupportedCount()} flagged` : '0'}
          </span>
        </div>

        {/* Sign-off state — right-aligned (run-level) */}
        <SignOffGate />
      </div>
    </Show>
  );
}
