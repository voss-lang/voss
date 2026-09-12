import { Show } from 'solid-js';
import WindowControls from './WindowControls';
import PresetSwitcher from './PresetSwitcher';
import type {
  ActiveLayout,
  LayoutPreset,
} from '../../grid/layoutPresets';

/**
 * titlebar shell. Window controls, drag regions, title text, the Voss logo
 * the LIVE/snapshot chip, and the 28px height all stay unchanged
 */
export type TitlebarProps = {
  activeLayout?: ActiveLayout;
  layoutDisabled?: boolean;
  onLayoutSelect?: (preset: LayoutPreset) => void;
  projectName?: string;
    /** Live/snapshot data-source state (sseClient liveLabel, via App) */
  liveState?: 'live' | 'snapshot';
};

export default function Titlebar(props: TitlebarProps = {}) {
  // Empty project names fall back too; only a non-empty open project replaces the brand
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
      {/* Window controls platform-switched (mac: traffic lights; others: stub) */}
      <WindowControls />

      {/* Left drag spacer the drag attribute belongs on the spacer ONLY, never on */}
      {/* the outer container or any button-bearing child */}
      <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />

      {/* projectName: wires this from App.tsx project signal; 'Voss ADE' is the project-less / pre-open fallback (CONCEPT Q1) */}
      {/* Drag attr on the text element itself so clicking the title drags the */}
      {/* window (matches macOS standard titlebar behavior). Safe because the div */}
      {/* contains plain text only no buttons / interactive children */}
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

      {/* LIVE/snapshot chip ( .livechip). Pulsing cyan dot only while a live stream is connected; muted 'snapshot' */}
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
