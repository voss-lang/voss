import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import AgentLaunchModal from '../AgentLaunchModal';

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

const defaultProps = () => ({
  onDismiss: vi.fn(),
  onLaunch: vi.fn(),
});

describe('AgentLaunchModal', () => {
  it('renders 6 CLI preset tabs', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const tabs = el.querySelectorAll('.modal-tab');
    expect(tabs).toHaveLength(6);
    const labels = Array.from(tabs).map((t) => t.textContent?.trim());
    expect(labels).toEqual(['Claude', 'Codex', 'Antigravity', 'OpenCode', 'Voss', 'Custom']);
  });

  it('Escape calls onDismiss', () => {
    const p = defaultProps();
    mount(() => <AgentLaunchModal {...p} />);
    fireEvent.keyDown(document.querySelector('.modal-backdrop')!, { key: 'Escape' });
    expect(p.onDismiss).toHaveBeenCalledOnce();
  });

  it('switching to Voss tab shows Voss config', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const vossTab = Array.from(el.querySelectorAll('.modal-tab')).find(
      (t) => t.textContent?.trim() === 'Voss',
    );
    fireEvent.click(vossTab!);
    // Should show command segmented with chat/do/resume/agent
    const buttons = el.querySelectorAll('.modal-segmented__btn');
    const labels = Array.from(buttons).map((b) => b.textContent?.trim());
    expect(labels).toContain('chat');
    expect(labels).toContain('do');
  });

  it('switching to Custom tab shows name and command inputs', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const customTab = Array.from(el.querySelectorAll('.modal-tab')).find(
      (t) => t.textContent?.trim() === 'Custom',
    );
    fireEvent.click(customTab!);
    const inputs = el.querySelectorAll('.modal-field');
    expect(inputs.length).toBeGreaterThanOrEqual(2);
  });

  it('Launch Agent button calls onLaunch', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const launchBtn = el.querySelector('.modal-btn-primary') as HTMLButtonElement;
    expect(launchBtn).toBeTruthy();
    fireEvent.click(launchBtn);
    expect(p.onLaunch).toHaveBeenCalledOnce();
    const config = p.onLaunch.mock.calls[0][0];
    expect(config).toHaveProperty('cliBinary');
    expect(config).toHaveProperty('cliArgs');
  });

  it('modal has correct ARIA attributes', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const dialog = el.querySelector('[role="dialog"]');
    expect(dialog).toBeTruthy();
    expect(dialog!.getAttribute('aria-modal')).toBe('true');
    expect(dialog!.getAttribute('aria-labelledby')).toBe('modal-title');
  });
});
