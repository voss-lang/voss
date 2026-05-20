import { createSignal, For } from 'solid-js';

/**
 * A7-03 Task 3 — minimal Variant B toast stack (D-16).
 *
 * Fixed bottom-right, max 3 visible, auto-dismiss (5s normal, 8s error).
 * Severity rail: success=green, warning=amber, error=red, info=cyan.
 * First consumer: keymap validation feedback (CMD-06).
 */

export type ToastSeverity = 'success' | 'warning' | 'error' | 'info';

export interface ToastItem {
  id: number;
  severity: ToastSeverity;
  message: string;
}

const RAIL_COLOR: Record<ToastSeverity, string> = {
  success: 'var(--accent-green)',
  warning: 'var(--accent-amber)',
  error: 'var(--accent-red)',
  info: 'var(--accent-cyan)',
};

const MAX_VISIBLE = 3;
const DISMISS_MS_NORMAL = 5000;
const DISMISS_MS_ERROR = 8000;

let nextId = 1;

// --- Shared toast store (module-level, one per app) --------------------------

const [toasts, setToasts] = createSignal<ToastItem[]>([]);

export function showToast(severity: ToastSeverity, message: string): void {
  const id = nextId++;
  const item: ToastItem = { id, severity, message };
  setToasts((prev) => [...prev, item].slice(-MAX_VISIBLE));
  const delay =
    severity === 'error' ? DISMISS_MS_ERROR : DISMISS_MS_NORMAL;
  setTimeout(() => dismissToast(id), delay);
}

export function dismissToast(id: number): void {
  setToasts((prev) => prev.filter((t) => t.id !== id));
}

/** Test-only: clear all toasts. */
export function _resetToastsForTest(): void {
  setToasts([]);
}

// --- Component ---------------------------------------------------------------

export default function ToastStack() {
  return (
    <div
      data-testid="toast-stack"
      aria-live="polite"
      style={{
        position: 'fixed',
        bottom: '16px',
        right: '16px',
        'z-index': 200,
        display: 'flex',
        'flex-direction': 'column',
        gap: '8px',
        'max-width': '320px',
        width: 'calc(100vw - 32px)',
        'pointer-events': 'none',
      }}
    >
      <For each={toasts()}>
        {(toast) => (
          <div
            data-testid="toast"
            data-severity={toast.severity}
            aria-live={
              toast.severity === 'error' ? 'assertive' : 'polite'
            }
            class="font-mono"
            style={{
              'min-height': '32px',
              padding: '8px 16px',
              background: 'var(--bg-3)',
              border: '1px solid var(--border-bright)',
              'border-left': `3px solid ${RAIL_COLOR[toast.severity]}`,
              'border-radius': '0px',
              color: 'var(--fg-0)',
              'font-size': '12px',
              'font-weight': 400,
              'pointer-events': 'auto',
            }}
          >
            {toast.message}
          </div>
        )}
      </For>
    </div>
  );
}
