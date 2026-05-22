import { Show } from 'solid-js';
import type { BudgetState } from '../pane/pty-ipc';

interface BudgetBarProps {
  budget: BudgetState;
  onClickDetail: (anchor: HTMLElement) => void;
}

function barFillPct(tokens_used: number, token_limit: number | null): number {
  if (token_limit == null) return 0;
  return Math.min((tokens_used / token_limit) * 100, 100);
}

function barFillColor(pct: number): string {
  if (pct < 70) return 'var(--accent-green)';
  if (pct < 90) return 'var(--accent-amber)';
  return 'var(--accent-red)';
}

function formatCost(cost_usd: number): string {
  if (cost_usd < 0.01) return `$${cost_usd.toFixed(4)}`;
  if (cost_usd < 100) return `$${cost_usd.toFixed(2)}`;
  return `$${Math.round(cost_usd)}`;
}

export default function BudgetBar(props: BudgetBarProps) {
  let buttonRef!: HTMLButtonElement;
  const pct = () => barFillPct(props.budget.tokens_used, props.budget.token_limit);
  const hasLimit = () => props.budget.token_limit != null;
  const label = () => {
    const cost = formatCost(props.budget.cost_usd);
    return hasLimit() ? `Budget: ${cost}, ${Math.round(pct())}% used` : `Cost: ${cost}`;
  };

  return (
    <button
      ref={buttonRef}
      type="button"
      aria-label={label()}
      style={{
        display: 'flex',
        'align-items': 'center',
        gap: '4px',
        background: 'transparent',
        border: 'none',
        padding: '0 4px',
        'flex-shrink': 0,
        cursor: 'default',
      }}
      onClick={() => props.onClickDetail(buttonRef)}
    >
      <span
        style={{
          color: 'var(--fg-2)',
          'font-size': '11px',
          'max-width': '44px',
          'white-space': 'nowrap',
          overflow: 'hidden',
        }}
      >
        {formatCost(props.budget.cost_usd)}
      </span>
      <Show when={hasLimit()}>
        <div
          style={{
            width: '48px',
            height: '4px',
            background: 'var(--bg-2)',
            position: 'relative',
            'flex-shrink': 0,
          }}
        >
          <div
            class="budget-bar-fill"
            style={{
              height: '4px',
              width: `${pct()}%`,
              'min-width': pct() > 0 ? '2px' : '0',
              background: barFillColor(pct()),
            }}
          />
        </div>
      </Show>
    </button>
  );
}
