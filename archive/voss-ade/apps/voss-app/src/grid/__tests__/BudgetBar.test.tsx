import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import BudgetBar from '../BudgetBar';
import type { BudgetState } from '../../pane/pty-ipc';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

const BASE: BudgetState = {
  tokens_used: 500,
  token_limit: 1000,
  cost_usd: 0.05,
  iteration: 3,
  model: 'claude-3',
};

describe('BudgetBar', () => {
  it('renders cost text', () => {
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={() => {}} />);
    expect(el.textContent).toContain('$0.05');
  });

  it('renders bar track when token_limit is set', () => {
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={() => {}} />);
    expect(el.querySelector('.budget-bar-fill')).toBeTruthy();
  });

  it('does not render bar track when token_limit is null (D-07)', () => {
    const el = mount(() => (
      <BudgetBar budget={{ ...BASE, token_limit: null }} onClickDetail={() => {}} />
    ));
    expect(el.querySelector('.budget-bar-fill')).toBeNull();
  });

  it('bar fill color is accent-green below 70% (D-08)', () => {
    // 500/1000 = 50% → green
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={() => {}} />);
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(fill.style.background).toContain('var(--accent-green)');
  });

  it('bar fill color is accent-amber at 80% (D-08)', () => {
    const el = mount(() => (
      <BudgetBar budget={{ ...BASE, tokens_used: 800 }} onClickDetail={() => {}} />
    ));
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(fill.style.background).toContain('var(--accent-amber)');
  });

  it('bar fill color is accent-red at 95% (D-08)', () => {
    const el = mount(() => (
      <BudgetBar budget={{ ...BASE, tokens_used: 950 }} onClickDetail={() => {}} />
    ));
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(fill.style.background).toContain('var(--accent-red)');
  });

  it('calls onClickDetail with the button element on click (D-09)', () => {
    const spy = vi.fn();
    const el = mount(() => <BudgetBar budget={BASE} onClickDetail={spy} />);
    fireEvent.click(el.querySelector('button')!);
    expect(spy).toHaveBeenCalledWith(expect.any(HTMLButtonElement));
  });

  it('cost format: <$0.01 shows 4dp', () => {
    const el = mount(() => (
      <BudgetBar budget={{ ...BASE, cost_usd: 0.0012 }} onClickDetail={() => {}} />
    ));
    expect(el.textContent).toContain('$0.0012');
  });

  it('bar width clamped to 100% when over-limit', () => {
    const el = mount(() => (
      <BudgetBar
        budget={{ ...BASE, tokens_used: 1500, token_limit: 1000 }}
        onClickDetail={() => {}}
      />
    ));
    const fill = el.querySelector('.budget-bar-fill') as HTMLElement;
    expect(parseFloat(fill.style.width)).toBeLessThanOrEqual(100);
  });
});
