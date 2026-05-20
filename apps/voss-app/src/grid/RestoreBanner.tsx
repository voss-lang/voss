/**
 * A6-05 — session restore banner (D-07/D-08/D-09).
 *
 * 22px row below PaneHeader with Variant B dim fg. Reports the actual
 * restored line count. No dismiss button — auto-dismissed on first
 * keystroke in the pane (via `onFirstInput` in PaneComponent).
 */
export default function RestoreBanner(props: { lineCount: number }) {
  return (
    <div
      class="font-mono"
      data-testid="restore-banner"
      style={{
        display: 'flex',
        'align-items': 'center',
        width: '100%',
        height: '22px',
        padding: '0 10px',
        'border-bottom': '1px solid var(--border)',
        'font-size': '11px',
        'font-weight': 400,
        color: 'var(--fg-2)',
        background: 'var(--bg-1)',
      }}
    >
      Session restored - {props.lineCount} lines
    </div>
  );
}
