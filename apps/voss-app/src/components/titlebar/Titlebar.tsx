import { Show } from 'solid-js';
import WindowControls from './WindowControls';

/**
 * A1 titlebar shell. Window controls, drag regions, title text, the Voss logo,
 * the LIVE/snapshot chip, and the 28px height all stay unchanged.
 *
 * V24-03 (VADE2-03) demoted the preset switcher and the Live Work / Run Review
 * mode toggle out of the titlebar: the App root now mounts `TopChrome`
 * (quiet chrome) instead, and layout presets live in the portal rail's layout
 * menu. This component is retained for the legacy A1/A5 chrome tests; it no
 * longer surfaces any preset or mode-toggle controls.
 *
 * Props are optional so existing A1/A5 tests that render `<Titlebar />`
 * continue to work; when omitted the chip reads 'snapshot' (the sseClient
 * default) and the title falls back to 'Voss ADE'.
 */
export type TitlebarProps = {
  projectName?: string;
  /** Live/snapshot data-source state (sseClient liveLabel, via App). */
  liveState?: 'live' | 'snapshot';
};

export default function Titlebar(props: TitlebarProps = {}) {
  // Empty project names fall back too; only a non-empty open project replaces the brand.
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

      {/* Left drag spacer — the drag attribute belongs on the spacer ONLY, never on  */}
      {/* the outer container or any button-bearing child (RESEARCH Pitfall 1).        */}
      <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />

      {/* projectName: A5-05 wires this from App.tsx project() signal; 'Voss ADE' is the project-less / pre-open fallback (CONCEPT §10 Q1). */}
      {/* Drag attr on the text element itself so clicking the title drags the    */}
      {/* window (matches macOS standard titlebar behavior). Safe because the div */}
      {/* contains plain text only — no buttons / interactive children.           */}
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
            'font-size': '13px',
            'font-family': 'var(--font-display)',
            'font-weight': '500',
          }}
        >
          {titleText()}
        </span>
      </div>

      {/* Right drag spacer */}
      <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />

      {/* V14 chunk A — LIVE/snapshot chip (mockup .livechip). Pulsing cyan
          dot only while a live stream is connected; muted 'snapshot'
          otherwise. The CockpitShell header keeps its own VCKP-06 label. */}
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
