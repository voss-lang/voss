import { For, Show } from 'solid-js';
import type { RunData, ReviewSidecar } from '../types';

// VADE-05 — Reviewer-A and Reviewer-B in two visually-separated half-panes.
// A (left) header --role-reviewer; B (right) header --accent-magenta.

function verdictColor(label: string): string {
  const v = label.toUpperCase();
  if (v === 'PASS') return 'var(--accent-green)';
  if (v === 'FAIL' || v === 'BLOCK') return 'var(--accent-red)';
  if (v === 'DEFER') return 'var(--accent-amber)';
  return 'var(--fg-1)';
}

function entries(data: RunData | null): Array<[string, ReviewSidecar]> {
  if (!data) return [];
  return Object.entries(data.review);
}

const halfStyle = {
  flex: '1',
  'min-width': '0',
  'overflow-y': 'auto',
  display: 'flex',
  'flex-direction': 'column',
} as const;

const headerBase = {
  height: '28px',
  'box-sizing': 'border-box',
  display: 'flex',
  'align-items': 'center',
  padding: '0 16px',
  background: 'var(--bg-1)',
  'border-bottom': '1px solid var(--border)',
  'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
  'font-size': '11px',
  'font-weight': '500',
  'text-transform': 'uppercase',
  'letter-spacing': '0.08em',
} as const;

const labelStyle = {
  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
  'font-size': '12px',
  'font-weight': '500',
} as const;

const monoMeta = {
  'font-family': 'var(--font-mono), monospace',
  'font-size': '11px',
  color: 'var(--fg-2)',
} as const;

const narrative = {
  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
  'font-size': '12px',
  color: 'var(--fg-1)',
  'white-space': 'pre-wrap',
} as const;

export default function VerdictPanel(props: { data: RunData | null }) {
  const all = () => entries(props.data);
  const hasA = () => all().some(([, s]) => s.a_verification != null);
  const hasB = () => all().some(([, s]) => s.b_verdict != null);

  return (
    <div class="org-panel" style={{ 'flex-direction': 'row' }}>
      {/* Reviewer A */}
      <div style={{ ...halfStyle, 'border-right': '1px solid var(--border)' }}>
        <div style={{ ...headerBase, color: 'var(--role-reviewer)' }}>REVIEWER A</div>
        <Show
          when={hasA()}
          fallback={<div class="org-empty">No Reviewer A verdict for this run.</div>}
        >
          <For each={all()}>
            {([nodeId, sidecar]) => (
              <Show when={sidecar.a_verification}>
                {(a) => (
                  <div style={{ padding: '8px 16px', 'border-bottom': '1px solid var(--border)', display: 'flex', 'flex-direction': 'column', gap: '4px' }}>
                    <div style={{ ...monoMeta, color: 'var(--fg-3)' }}>{nodeId}</div>
                    <div style={{ ...labelStyle, color: verdictColor(a().result) }}>
                      {a().result.toUpperCase()}
                    </div>
                    <div style={monoMeta}>{a().test_path_or_rubric}</div>
                    <div style={narrative}>{a().notes}</div>
                  </div>
                )}
              </Show>
            )}
          </For>
        </Show>
      </div>

      {/* Reviewer B */}
      <div style={halfStyle}>
        <div style={{ ...headerBase, color: 'var(--accent-magenta)' }}>REVIEWER B</div>
        <Show
          when={hasB()}
          fallback={<div class="org-empty">No Reviewer B verdict for this run.</div>}
        >
          <For each={all()}>
            {([nodeId, sidecar]) => (
              <Show when={sidecar.b_verdict}>
                {(b) => (
                  <div style={{ padding: '8px 16px', 'border-bottom': '1px solid var(--border)', display: 'flex', 'flex-direction': 'column', gap: '4px' }}>
                    <div style={{ ...monoMeta, color: 'var(--fg-3)' }}>{nodeId}</div>
                    <div style={{ ...labelStyle, color: verdictColor(b().verdict) }}>
                      {b().verdict.toUpperCase()}
                    </div>
                    <div style={monoMeta}>conf: {b().conf.toFixed(2)}</div>
                    <div style={monoMeta}>domain: {b().domain_inferred}</div>
                    <div style={narrative}>{b().notes}</div>
                  </div>
                )}
              </Show>
            )}
          </For>
        </Show>
      </div>
    </div>
  );
}
