import { Show } from 'solid-js';
import WindowControls from './WindowControls';

/**
 * V24-03 (VADE2-03) — quiet top chrome.
 *
 * Replaces the preset-bearing `Titlebar` at the App root. The default chrome
 * carries ONLY: window controls + project/window identity, a `⌘K`
 * command-palette trigger, a safety-mode indicator chip, and the existing
 * live chip. The fanout/pipeline/swarm/watchers preset switcher and the raw
 * Plan/Edit/Auto mode-toggle group are intentionally absent — presets are
 * demoted to the portal rail's layout menu, and run intake moves to the ⌘K
 * composer.
 *
 * Structural analog: `Titlebar.tsx` (28px height, WindowControls, drag
 * spacers, Voss logo + project name, reused `.titlebar-livechip`). The chrome
 * height stays 28px (`--titlebar-height`) — do not change.
 *
 * `onOpenComposer` is wired to the VossComposer modal in V24-04; until then the
 * ⌘K trigger renders and is a safe no-op (same deferral as PortalRail's
 * "Ask Voss to…" trigger).
 */
export type TopChromeProps = {
  projectName?: string;
  /** Live/snapshot data-source state (sseClient liveLabel, via App). */
  liveState?: 'live' | 'snapshot';
  /** Safety mode of the most-recently-created Task; chip hidden when absent. */
  currentSafetyMode?: 'Read only' | 'Can edit' | 'Autopilot';
  /** Opens the ⌘K "Ask Voss to…" composer (wired in V24-04). */
  onOpenComposer?: () => void;
};

// Token-only text color per safety mode (UI-SPEC §Color — safety mode chips):
// "Read only" is the muted safe default; "Can edit" warns amber; "Autopilot"
// is the highest-risk red.
function safetyColor(mode: 'Read only' | 'Can edit' | 'Autopilot'): string {
  if (mode === 'Autopilot') return 'var(--accent-red)';
  if (mode === 'Can edit') return 'var(--accent-amber)';
  return 'var(--fg-3)';
}

export default function TopChrome(props: TopChromeProps = {}) {
  // Empty/absent project names fall back to the brand (same rule as Titlebar).
  const titleText = () =>
    props.projectName && props.projectName.length > 0
      ? props.projectName
      : 'Voss ADE';
  const liveState = () => props.liveState ?? 'snapshot';

  return (
    <div
      style={{
        display: 'flex',
        'align-items': 'center',
        height: 'var(--titlebar-height)',
        'flex-shrink': '0',
        background: 'var(--bg-0)',
        'border-bottom': '1px solid var(--border)',
        overflow: 'hidden',
      }}
    >
      {/* Window controls — platform-switched (mac: traffic lights; others: stub) */}
      <WindowControls />

      {/* Left drag spacer — drag attr belongs on the spacer ONLY, never on the */}
      {/* outer container or any button-bearing child (RESEARCH Pitfall 1).      */}
      <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />

      {/* Identity: Voss logo + project name (truncated 180px). Drag attr on the */}
      {/* text container is safe — plain text only, no interactive children.      */}
      <div
        data-tauri-drag-region
        style={{
          'flex-shrink': '0',
          'align-self': 'stretch',
          display: 'flex',
          'align-items': 'center',
          gap: '6px',
        }}
      >
        <svg
          viewBox="0 0 2048 2048"
          fill="none"
          style={{ width: '18px', height: '18px', 'flex-shrink': '0', color: 'var(--focus)' }}
        >
          <path d="M332 471h278l566 908-136 226L332 471Z" fill="currentColor" />
          <path d="M1432 470h308l-503 724-144-197 339-527Z" fill="currentColor" />
        </svg>
        <span
          style={{
            color: 'var(--fg-1)',
            'font-size': '12px',
            'font-family': 'var(--font-ui)',
            'max-width': '180px',
            overflow: 'hidden',
            'text-overflow': 'ellipsis',
            'white-space': 'nowrap',
          }}
        >
          {titleText()}
        </span>
      </div>

      {/* Right drag spacer */}
      <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />

      {/* Quiet right cluster (NOT a drag region — carries interactive controls). */}
      <div
        style={{
          'flex-shrink': '0',
          display: 'flex',
          'align-items': 'center',
          gap: '8px',
          'margin-right': '12px',
        }}
      >
        {/* ⌘K command-palette trigger → opens the "Ask Voss to…" composer. */}
        <button
          type="button"
          aria-label="Open command palette (⌘K)"
          onClick={() => props.onOpenComposer?.()}
          style={{
            background: 'var(--bg-2)',
            color: 'var(--fg-3)',
            border: '1px solid var(--border)',
            padding: '2px 8px',
            'font-family': 'var(--font-mono)',
            'font-size': '11px',
            'line-height': '1',
            cursor: 'pointer',
          }}
        >
          ⌘K
        </button>

        {/* Safety-mode chip — display-only; hidden when no Task mode is active. */}
        <Show when={props.currentSafetyMode}>
          {(mode) => (
            <div
              class="topchrome-modechip"
              aria-label={`Safety mode: ${mode()}`}
              style={{
                background: 'var(--bg-3)',
                color: safetyColor(mode()),
                border: '1px solid var(--border)',
                padding: '2px 8px',
                'font-family': 'var(--font-ui)',
                'font-size': '11px',
                'line-height': '1',
                'white-space': 'nowrap',
              }}
            >
              {mode()}
            </div>
          )}
        </Show>
      </div>

      {/* LIVE/snapshot chip — reuse the existing `.titlebar-livechip` as-is. */}
      <div
        class={`titlebar-livechip titlebar-livechip--${liveState()}`}
        aria-label={`Data source: ${liveState()}`}
      >
        <Show when={liveState() === 'live'}>
          <span class="titlebar-livechip__dot" />
        </Show>
        {liveState() === 'live' ? 'LIVE' : 'snapshot'}
      </div>
    </div>
  );
}
