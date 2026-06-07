import { createSignal, onMount, onCleanup, Show } from 'solid-js';
import {
  buildDecisionCommand,
  runDecision,
  type DecisionAction,
} from './decisionActions';
import { refreshRun } from './orgStore';
import type { DecisionResult } from './types';

// VADE-09 — decision confirmation dialog (D-07/D-08). Shows the EXACT CLI
// command before execution, shells it via run_decision (the sole write path —
// this component never touches the filesystem), renders inline success/failure,
// and auto-closes + refreshes the run 1500ms after a successful decision.

export default function DecisionDialog(props: {
  action: DecisionAction;
  runId: string;
  cardId: string;
  cwd: string;
  cliBinary: string;
  onDismiss: () => void;
}) {
  const [visible, setVisible] = createSignal(false);
  const [executing, setExecuting] = createSignal(false);
  const [result, setResult] = createSignal<DecisionResult | null>(null);

  let panelRef: HTMLDivElement | undefined;
  let closeTimer: ReturnType<typeof setTimeout> | undefined;

  const command = () =>
    buildDecisionCommand(props.action, props.runId, props.cwd);
  const titleId = `decision-title-${props.cardId}`;

  onMount(() => {
    requestAnimationFrame(() => setVisible(true));
    panelRef?.focus();
  });
  onCleanup(() => {
    if (closeTimer) clearTimeout(closeTimer);
  });

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      props.onDismiss();
    }
  };
  const onBackdropClick = (e: MouseEvent) => {
    if (panelRef && !panelRef.contains(e.target as Node)) props.onDismiss();
  };

  const onConfirm = async () => {
    setExecuting(true);
    try {
      const r = await runDecision(
        props.cliBinary,
        props.cwd,
        props.action,
        props.runId,
      );
      setResult(r);
      if (r.success) {
        closeTimer = setTimeout(() => {
          props.onDismiss();
          void refreshRun(props.cwd, props.cliBinary); // D-08 auto-refresh
        }, 1500);
      }
    } catch (e) {
      setResult({ success: false, stdout: '', stderr: String(e), exit_code: -1 });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div
      onClick={onBackdropClick}
      onKeyDown={onKeyDown}
      style={{
        position: 'fixed',
        inset: '0',
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        'align-items': 'center',
        'justify-content': 'center',
        'z-index': '100',
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabindex="-1"
        style={{
          width: '480px',
          background: 'var(--bg-3)',
          border: '1px solid var(--border-bright)',
          opacity: visible() ? '1' : '0',
          transform: visible() ? 'scale(1)' : 'scale(0.96)',
          transition: 'opacity 150ms ease-out, transform 150ms ease-out',
        }}
      >
        {/* Header */}
        <div
          style={{
            height: '48px',
            'box-sizing': 'border-box',
            display: 'flex',
            'align-items': 'center',
            padding: '0 16px',
            'border-bottom': '1px solid var(--border)',
          }}
        >
          <span
            id={titleId}
            style={{
              flex: '1',
              'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
              'font-size': '16px',
              'font-weight': '500',
              color: 'var(--fg-0)',
            }}
          >
            {props.action.charAt(0).toUpperCase() + props.action.slice(1)}:{' '}
            {props.cardId}
          </span>
          <button
            aria-label="Close dialog"
            onClick={() => props.onDismiss()}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--fg-2)',
              'font-size': '16px',
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>

        {/* CLI preview (D-07: exact command) */}
        <div style={{ margin: '16px' }}>
          <div
            style={{
              'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
              'font-size': '11px',
              'font-weight': '500',
              color: 'var(--fg-3)',
              'margin-bottom': '4px',
            }}
          >
            Command to run:
          </div>
          <pre
            style={{
              margin: '0',
              background: 'var(--bg-2)',
              'border-left': '2px solid var(--focus)',
              padding: '8px 16px',
              'font-family': 'var(--font-mono), monospace',
              'font-size': '11px',
              color: 'var(--fg-0)',
              'white-space': 'pre-wrap',
            }}
          >
            {command()}
          </pre>
        </div>

        {/* Result */}
        <Show when={result()}>
          {(r) => (
            <div style={{ margin: '0 16px 16px' }}>
              <div
                style={{
                  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                  'font-size': '12px',
                  color: r().success ? 'var(--accent-green)' : 'var(--accent-red)',
                }}
              >
                {r().success ? '✓ Done' : '✗ Failed'}
              </div>
              <pre
                style={{
                  margin: '4px 0 0',
                  'font-family': 'var(--font-mono), monospace',
                  'font-size': '11px',
                  color: 'var(--fg-2)',
                  'white-space': 'pre-wrap',
                }}
              >
                {r().success ? r().stdout.slice(0, 200) : r().stderr}
              </pre>
            </div>
          )}
        </Show>

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            'justify-content': 'flex-end',
            gap: '8px',
            padding: '0 16px 16px',
          }}
        >
          <button
            onClick={() => props.onDismiss()}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              'border-radius': '3px',
              color: 'var(--fg-2)',
              'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
              'font-size': '11px',
              'font-weight': '500',
              padding: '4px 12px',
              cursor: 'pointer',
            }}
          >
            Keep Viewing
          </button>
          <button
            disabled={executing()}
            onClick={() => void onConfirm()}
            style={{
              background: 'var(--focus)',
              border: 'none',
              'border-radius': '3px',
              color: 'var(--fg-0)',
              'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
              'font-size': '11px',
              'font-weight': '500',
              padding: '4px 12px',
              cursor: 'pointer',
              opacity: executing() ? '0.5' : '1',
            }}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
