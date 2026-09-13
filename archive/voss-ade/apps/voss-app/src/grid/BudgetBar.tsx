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
      {/* V14 chunk C — mono cost with the hot treatment ≥ $1 (mockup
          .pcost.hot), matching the grid PaneHeader's agent-cost colors. */}
      <span
        style={{
          color: props.budget.cost_usd >= 1 ? 'var(--focus)' : 'var(--fg-2)',
          'font-family': 'var(--font-mono)',
          'font-size': '11px',
          'font-weight': props.budget.cost_usd >= 1 ? '600' : '400',
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
