import { describe, it, expect, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import RestoreBanner from '../RestoreBanner';

/**
 * A6-05 Task 1 — RestoreBanner component tests.
 *
 * Verifies:
 * - Exact copy "Session restored - N lines"
 * - Height 22px
 * - No dismiss button
 * - Various line counts (0, 1, 2000)
 */

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

describe('RestoreBanner', () => {
  it('renders exact copy "Session restored - N lines" for 0 lines', () => {
    const el = mount(() => <RestoreBanner lineCount={0} />);
    const banner = el.querySelector('[data-testid="restore-banner"]')!;
    expect(banner.textContent).toContain('Session restored - 0 lines');
  });

  it('renders exact copy for 1 line', () => {
    const el = mount(() => <RestoreBanner lineCount={1} />);
    const banner = el.querySelector('[data-testid="restore-banner"]')!;
    expect(banner.textContent).toContain('Session restored - 1 lines');
  });

  it('renders exact copy for 2000 lines', () => {
    const el = mount(() => <RestoreBanner lineCount={2000} />);
    const banner = el.querySelector('[data-testid="restore-banner"]')!;
    expect(banner.textContent).toContain('Session restored - 2000 lines');
  });

  it('has height 22px', () => {
    const el = mount(() => <RestoreBanner lineCount={42} />);
    const banner = el.querySelector('[data-testid="restore-banner"]') as HTMLElement;
    expect(banner.style.height).toBe('22px');
  });

  it('contains no button elements (no dismiss button)', () => {
    const el = mount(() => <RestoreBanner lineCount={10} />);
    const buttons = el.querySelectorAll('button');
    expect(buttons).toHaveLength(0);
  });
});
