import { For, Show, createSignal } from 'solid-js';
import type { RunData, ReviewSidecar } from '../types';

// VADE-08 — per-card verification drilldown.
// RESEARCH Pitfall 4: raw diff text NEVER persists in the V2-V7 substrate
// (sections_missing always contains diff_summary). So the per-card surface is
// the review sidecar's a_verification; the "No diff recorded" state is the
// verified reality, NOT a placeholder.

function outcomeColor(result: string): string {
  const v = result.toUpperCase();
  if (v === 'PASS') return 'var(--accent-green)';
  if (v === 'FAIL') return 'var(--accent-red)';
  return 'var(--fg-3)'; // SKIP / unknown
}

export default function DiffPanel(props: {
  data: RunData | null;
  selectedCardId?: string | null;
  onCardSelect?: (cardId: string) => void;
}) {
  const [pickerOpen, setPickerOpen] = createSignal(false);

  const cardIds = () => Object.keys(props.data?.review ?? {});
  const activeId = () => props.selectedCardId ?? null;
  const sidecar = (): ReviewSidecar | null => {
    const id = activeId();
    return id ? (props.data?.review[id] ?? null) : null;
  };

  return (
    <div class="org-panel">
      {/* Card picker */}
      <div
        style={{
          display: 'flex',
          'align-items': 'center',
          gap: '6px',
          height: '32px',
          padding: '0 16px',
          'border-bottom': '1px solid var(--border)',
          position: 'relative',
        }}
      >
        <span style={{ 'font-family': 'var(--font-ui), Inter, system-ui, sans-serif', 'font-size': '11px', 'font-weight': '500', color: 'var(--fg-2)' }}>
          Card:
        </span>
        <button
          onClick={() => setPickerOpen((o) => !o)}
          style={{
            background: 'transparent',
            border: 'none',
            'font-family': 'var(--font-mono), monospace',
            'font-size': '11px',
            color: 'var(--fg-1)',
            cursor: 'pointer',
          }}
        >
          {activeId() ?? '—'} ▾
        </button>
        <Show when={pickerOpen()}>
          <div class="org-run-picker" role="listbox" style={{ top: '32px', left: '16px', transform: 'none' }}>
            <Show when={cardIds().length > 0} fallback={<div class="org-run-picker__empty">No cards</div>}>
              <For each={cardIds()}>
                {(id) => (
                  <div
                    class="org-run-picker__row"
                    role="option"
                    aria-selected={id === activeId()}
                    onClick={() => {
                      props.onCardSelect?.(id);
                      setPickerOpen(false);
                    }}
                  >
                    {id}
                  </div>
                )}
              </For>
            </Show>
          </div>
        </Show>
      </div>

      <Show
        when={activeId()}
        fallback={<div class="org-empty">Select a card to view its diff.</div>}
      >
        {/* Diff view — always the explicit no-diff state in this substrate */}
        <div class="org-empty" style={{ 'min-height': '80px', flex: '0 0 auto' }}>
          No diff recorded for this card.
        </div>

        {/* Verification surface from a_verification */}
        <div
          style={{
            'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
            'font-size': '11px',
            'font-weight': '500',
            'text-transform': 'uppercase',
            'letter-spacing': '0.08em',
            color: 'var(--fg-3)',
            padding: '8px 16px 4px',
            'border-top': '1px solid var(--border)',
          }}
        >
          VERIFICATION
        </div>
        <Show
          when={sidecar()?.a_verification}
          fallback={
            <div style={{ padding: '4px 16px', 'font-family': 'var(--font-ui), Inter, system-ui, sans-serif', 'font-size': '12px', color: 'var(--fg-3)' }}>
              No verification recorded for this card.
            </div>
          }
        >
          {(a) => (
            <div style={{ padding: '4px 16px', display: 'flex', 'flex-direction': 'column', gap: '4px' }}>
              <span
                style={{
                  'align-self': 'flex-start',
                  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                  'font-size': '11px',
                  'font-weight': '500',
                  'border-radius': '9999px',
                  padding: '0 8px',
                  color: outcomeColor(a().result),
                  background: 'var(--bg-2)',
                }}
              >
                {a().result.toUpperCase()}
              </span>
              <span style={{ 'font-family': 'var(--font-mono), monospace', 'font-size': '11px', color: 'var(--fg-2)' }}>
                {a().test_path_or_rubric}
              </span>
              <span style={{ 'font-family': 'var(--font-ui), Inter, system-ui, sans-serif', 'font-size': '12px', color: 'var(--fg-1)', 'white-space': 'pre-wrap' }}>
                {a().notes}
              </span>
            </div>
          )}
        </Show>
      </Show>
    </div>
  );
}
