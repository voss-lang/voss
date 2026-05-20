import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { render } from 'solid-js/web';
import ToastStack, {
  showToast,
  _resetToastsForTest,
} from '../toast';

/**
 * A7-03 Task 3 — toast stack tests.
 *
 * Verifies exact A7-UI-SPEC copy, severity rails, max visible count,
 * and assertive live-region for errors.
 */

let dispose: (() => void) | undefined;
function mount() {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(() => <ToastStack />, root);
  return root;
}
beforeEach(() => _resetToastsForTest());
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  _resetToastsForTest();
});

describe('ToastStack — copy and severity', () => {
  it('success toast shows "Keymap updated" copy', () => {
    mount();
    showToast('success', 'Keymap updated');
    const toast = document.querySelector('[data-testid="toast"]')!;
    expect(toast.textContent).toBe('Keymap updated');
    expect(toast.getAttribute('data-severity')).toBe('success');
  });

  it('error toast shows "Keymap entry ignored" copy', () => {
    mount();
    showToast('error', 'Keymap entry ignored: unknown command "bad.cmd"');
    const toast = document.querySelector('[data-testid="toast"]')!;
    expect(toast.textContent).toContain('Keymap entry ignored');
    expect(toast.getAttribute('data-severity')).toBe('error');
  });

  it('warning toast renders with warning severity', () => {
    mount();
    showToast('warning', 'Keymap conflict ignored');
    const toast = document.querySelector('[data-testid="toast"]')!;
    expect(toast.getAttribute('data-severity')).toBe('warning');
  });

  it('info toast renders with info severity', () => {
    mount();
    showToast('info', 'Keymap profile changed');
    const toast = document.querySelector('[data-testid="toast"]')!;
    expect(toast.getAttribute('data-severity')).toBe('info');
  });
});

describe('ToastStack — max visible', () => {
  it('renders at most 3 toasts', () => {
    mount();
    showToast('info', 'one');
    showToast('info', 'two');
    showToast('info', 'three');
    showToast('info', 'four');

    const visible = document.querySelectorAll('[data-testid="toast"]');
    expect(visible).toHaveLength(3);
    // Newest at end (four displaces one)
    expect(visible[2].textContent).toBe('four');
  });
});

describe('ToastStack — ARIA', () => {
  it('error toasts use aria-live="assertive"', () => {
    mount();
    showToast('error', 'bad chord');
    const toast = document.querySelector('[data-testid="toast"]')!;
    expect(toast.getAttribute('aria-live')).toBe('assertive');
  });

  it('success/info toasts use aria-live="polite"', () => {
    mount();
    showToast('success', 'ok');
    const toast = document.querySelector('[data-testid="toast"]')!;
    expect(toast.getAttribute('aria-live')).toBe('polite');
  });

  it('toast stack container has aria-live="polite"', () => {
    mount();
    const stack = document.querySelector('[data-testid="toast-stack"]')!;
    expect(stack.getAttribute('aria-live')).toBe('polite');
  });
});
