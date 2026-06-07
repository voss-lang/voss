import { For, Show } from 'solid-js';
import type { RunData, AuditReport } from '../types';

// VADE-04 — renders the V9 audit JSON: summary sections, claims-vs-evidence
// with the unsupported-EM-claim ⚑ flag, and the residual-risk (leak6) section.
// Diffs / tests_evals are intentionally NOT rendered (Pitfall 4 — always in
// sections_missing for the V2-V7 substrate).

const sectionHeader = {
  'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
  'font-size': '11px',
  'font-weight': '500',
  'text-transform': 'uppercase',
  'letter-spacing': '0.08em',
  color: 'var(--fg-3)',
  padding: '8px 16px 4px',
  'border-bottom': '1px solid var(--border)',
} as const;

const bodyText = {
  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
  'font-size': '12px',
  color: 'var(--fg-1)',
  padding: '4px 16px',
} as const;

function badgeColor(kind: 'supported' | 'partial' | 'unsupported'): string {
  return kind === 'supported'
    ? 'var(--accent-green)'
    : kind === 'partial'
      ? 'var(--accent-amber)'
      : 'var(--accent-red)';
}

export default function AuditPanel(props: { data: RunData | null }) {
  const audit = (): AuditReport | null => props.data?.audit ?? null;
  const unsupported = () => new Set(audit()?.unsupported_claims ?? []);

  return (
    <div class="org-panel">
      <Show
        when={audit()}
        fallback={<div class="org-empty">No audit data for this run.</div>}
      >
        {(a) => (
          <div style={{ flex: '1', 'overflow-y': 'auto' }}>
            {/* Summary */}
            <div style={sectionHeader}>IDEA</div>
            <div style={bodyText}>{a().idea}</div>

            <div style={sectionHeader}>PRINCIPLES</div>
            <For each={a().principles}>
              {([k, t]) => (
                <div style={bodyText}>
                  {k}: {t}
                </div>
              )}
            </For>

            <div style={sectionHeader}>TEAM</div>
            <div style={bodyText}>
              {a().team_config.source} · {a().team_config.roster_ids.join(', ')}
            </div>

            <div style={sectionHeader}>SNAPSHOT</div>
            <div style={bodyText}>
              cards {a().snapshot.cards.length} · kills{' '}
              {a().snapshot.kills.length} · rescopes{' '}
              {a().snapshot.rescopes.length} · routings{' '}
              {a().snapshot.routings.length}
            </div>

            {/* Claims vs evidence */}
            <div style={sectionHeader}>CLAIMS</div>
            <For each={a().snapshot.cards}>
              {(card) => {
                const isUnsupported = unsupported().has(card.node_id);
                return (
                  <div
                    style={{
                      display: 'flex',
                      'align-items': 'center',
                      gap: '8px',
                      'min-height': '32px',
                      padding: '4px 16px',
                      background: isUnsupported
                        ? 'rgba(232,123,123,0.06)'
                        : 'transparent',
                    }}
                  >
                    <Show when={isUnsupported}>
                      <span
                        aria-label="Unsupported claim"
                        style={{
                          color: 'var(--unsupported-flag)',
                          'font-family': 'var(--font-mono), monospace',
                          'font-size': '13px',
                        }}
                      >
                        ⚑
                      </span>
                    </Show>
                    <span
                      style={{
                        flex: '1',
                        'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                        'font-size': '12px',
                        color: 'var(--fg-1)',
                      }}
                    >
                      {card.node_id} ({card.column})
                    </span>
                    <span
                      style={{
                        'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                        'font-size': '11px',
                        'font-weight': '500',
                        color: badgeColor(
                          isUnsupported ? 'unsupported' : 'supported',
                        ),
                      }}
                    >
                      {isUnsupported ? 'unsupported' : 'supported'}
                    </span>
                  </div>
                );
              }}
            </For>

            {/* Residual risk */}
            <div style={sectionHeader}>RESIDUAL RISK</div>
            <Show
              when={a().snapshot.leak6}
              fallback={<div style={bodyText}>—</div>}
            >
              {(leak) => (
                <div style={bodyText}>
                  <div>status: {leak().status}</div>
                  <div>evidence: {leak().evidence}</div>
                  <div>
                    mitigation present: {leak().mitigation_present ? 'yes' : 'no'}
                  </div>
                </div>
              )}
            </Show>
          </div>
        )}
      </Show>
    </div>
  );
}
