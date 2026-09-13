import { Show } from 'solid-js';
import type { BudgetState } from '../pane/pty-ipc';
import Popover from './Popover';

interface BudgetPopoverProps {
  budget: BudgetState;
  anchor: HTMLElement;
  onClose: () => void;
}

function fillPct(b: BudgetState): number {
  if (b.token_limit == null) return 0;
  return Math.min((b.tokens_used / b.token_limit) * 100, 100);
}

function fillColor(pct: number): string {
  if (pct < 70) return 'var(--accent-green)';
  if (pct < 90) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}

function fmtCost(cost_usd: number): string {
  if (cost_usd < 0.01) return `$${cost_usd.toFixed(4)}`;
  return `$${cost_usd.toFixed(2)}`;
}

const ROW: Record<string, string> = {
  display: 'flex',
  'align-items': 'center',
  height: '24px',
  padding: '0 8px',
  'border-bottom': '1px solid var(--border)',
};

const LABEL: Record<string, string> = {
  color: 'var(--fg-3)',
  'font-size': '11px',
  width: '44px',
  'text-align': 'right',
  'margin-right': '8px',
  'flex-shrink': '0',
};

const VALUE: Record<string, string> = {
  color: 'var(--fg-1)',
  'font-size': '12px',
  overflow: 'hidden',
  'text-overflow': 'ellipsis',
  'white-space': 'nowrap',
};

export default function BudgetPopover(props: BudgetPopoverProps) {
  const b = () => props.budget;
  const pct = () => fillPct(b());

  return (
    <Popover anchor={props.anchor} onClose={props.onClose}>
      <div role="dialog" aria-label="Budget Detail" class="font-mono">
        {/* Header */}
        <div
          style={{
            display: 'flex',
            'align-items': 'center',
            height: '24px',
            padding: '0 8px',
            background: 'var(--bg-3)',
            'border-bottom': '1px solid var(--border)',
          }}
        >
          <span style={{ color: 'var(--fg-2)', 'font-size': '11px', 'font-weight': 500 }}>
            Budget Detail
          </span>
        </div>

        {/* Expanded progress bar */}
        <Show when={b().token_limit != null}>
          <div style={{ padding: '4px 8px', 'border-bottom': '1px solid var(--border)' }}>
            <div style={{ height: '8px', background: 'var(--bg-2)' }}>
              <div
                style={{
                  height: '8px',
                  width: `${pct()}%`,
                  background: fillColor(pct()),
                }}
              />
            </div>
          </div>
        </Show>

        {/* tokens row */}
        <div style={ROW}>
          <span style={LABEL}>tokens:</span>
          <span style={VALUE}>
            {b().tokens_used.toLocaleString()}
            <Show when={b().token_limit != null}>
              {` / ${b().token_limit!.toLocaleString()}`}
            </Show>
          </span>
        </div>

        {/* limit row — hidden when null */}
        <Show when={b().token_limit != null}>
          <div style={ROW}>
            <span style={LABEL}>limit:</span>
            <span style={VALUE}>{b().token_limit!.toLocaleString()} tokens</span>
          </div>
        </Show>

        {/* model row */}
        <div style={ROW}>
          <span style={LABEL}>model:</span>
          <span style={{ ...VALUE, 'max-width': '24ch' }}>{b().model}</span>
        </div>

        {/* turns row */}
        <div style={ROW}>
          <span style={LABEL}>turns:</span>
          <span style={VALUE}>{b().iteration}</span>
        </div>

        {/* cost row */}
        <div style={{ ...ROW, 'border-bottom': 'none' }}>
          <span style={LABEL}>cost:</span>
          <span style={VALUE}>{fmtCost(b().cost_usd)}</span>
        </div>
      </div>
    </Popover>
  );
}
