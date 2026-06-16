import { Show } from 'solid-js';
import Bell from 'lucide-solid/icons/bell';
import ChevronDown from 'lucide-solid/icons/chevron-down';
import Folder from 'lucide-solid/icons/folder';
import GitBranch from 'lucide-solid/icons/git-branch';
import Plus from 'lucide-solid/icons/plus';
import Search from 'lucide-solid/icons/search';
import WindowControls from './WindowControls';

/**
 * V24-09 — reference-design top chrome.
 *
 * Single 44px bar: window controls + project identity, centered section label,
 * search/composer trigger, notifications stub, "New task" CTA, safety chip, and
 * live chip. Layout presets and Plan/Edit/Auto toggles stay in the portal rail.
 */
export type TopChromeProps = {
  projectName?: string;
  gitBranch?: string | null;
  /** Uppercase portal section label (e.g. "WORKSPACES"). */
  sectionLabel: string;
  /** Live/snapshot data-source state (sseClient liveLabel, via App). */
  liveState?: 'live' | 'snapshot';
  /** Safety mode of the most-recently-created Task; chip hidden when absent. */
  currentSafetyMode?: 'Read only' | 'Can edit' | 'Autopilot';
  /** Opens the ⌘K "Ask Voss to…" composer. */
  onOpenComposer?: () => void;
};

function safetyColor(mode: 'Read only' | 'Can edit' | 'Autopilot'): string {
  if (mode === 'Autopilot') return 'var(--accent-red)';
  if (mode === 'Can edit') return 'var(--accent-amber)';
  return 'var(--fg-3)';
}

export default function TopChrome(props: TopChromeProps) {
  const titleText = () =>
    props.projectName && props.projectName.length > 0
      ? props.projectName
      : 'Voss ADE';
  const liveState = () => props.liveState ?? 'snapshot';

  const openComposer = () => props.onOpenComposer?.();

  return (
    <div
      style={{
        display: 'flex',
        'align-items': 'center',
        height: 'var(--topbar-height)',
        'flex-shrink': '0',
        background: 'var(--bg-0)',
        'border-bottom': '1px solid var(--border)',
        overflow: 'hidden',
      }}
    >
      {/* Left cluster — fixed width; no drag region on interactive children. */}
      <div
        style={{
          'flex-shrink': '0',
          display: 'flex',
          'align-items': 'center',
          gap: '8px',
          'padding-left': '4px',
        }}
      >
        <WindowControls />

        <svg
          viewBox="0 0 2048 2048"
          fill="none"
          aria-hidden="true"
          style={{
            width: '18px',
            height: '18px',
            'flex-shrink': '0',
            color: 'var(--primary)',
          }}
        >
          <path d="M332 471h278l566 908-136 226L332 471Z" fill="currentColor" />
          <path d="M1432 470h308l-503 724-144-197 339-527Z" fill="currentColor" />
        </svg>

        <button
          type="button"
          aria-label={`Project: ${titleText()}${props.gitBranch ? `, branch ${props.gitBranch}` : ''}`}
          onClick={() => {
            // TODO(V24-09): open project/branch picker menu.
          }}
          style={{
            display: 'flex',
            'align-items': 'center',
            gap: '6px',
            background: 'var(--bg-2)',
            color: 'var(--fg-0)',
            border: '1px solid var(--border)',
            'border-radius': 'var(--radius-md)',
            padding: '4px 10px',
            'font-family': 'var(--font-ui)',
            'font-size': '12px',
            'line-height': '1.2',
            cursor: 'pointer',
            'max-width': '240px',
          }}
        >
          <Folder size={14} color="currentColor" aria-hidden="true" strokeWidth={1.75} />
          <span
            style={{
              'font-weight': '600',
              color: 'var(--fg-0)',
              overflow: 'hidden',
              'text-overflow': 'ellipsis',
              'white-space': 'nowrap',
            }}
          >
            {titleText()}
          </span>
          <Show when={props.gitBranch}>
            {(branch) => (
              <span
                style={{
                  display: 'flex',
                  'align-items': 'center',
                  gap: '3px',
                  color: 'var(--fg-2)',
                  'flex-shrink': '0',
                }}
              >
                <GitBranch size={12} color="currentColor" aria-hidden="true" strokeWidth={1.75} />
                <span>{branch()}</span>
              </span>
            )}
          </Show>
          <ChevronDown size={14} color="var(--fg-2)" aria-hidden="true" strokeWidth={1.75} />
        </button>
      </div>

      {/* Center cluster — flex with drag spacers flanking the section label. */}
      <div
        style={{
          flex: '1',
          display: 'flex',
          'align-items': 'center',
          'min-width': '0',
          'align-self': 'stretch',
        }}
      >
        <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />
        <span
          data-tauri-drag-region
          style={{
            'flex-shrink': '0',
            color: 'var(--fg-3)',
            'font-family': 'var(--font-ui)',
            'font-size': '11px',
            'letter-spacing': '0.12em',
            'text-transform': 'uppercase',
            'user-select': 'none',
          }}
        >
          {props.sectionLabel}
        </span>
        <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />
      </div>

      {/* Right cluster — interactive controls only; NOT a drag region. */}
      <div
        style={{
          'flex-shrink': '0',
          display: 'flex',
          'align-items': 'center',
          gap: '8px',
          'margin-right': '12px',
        }}
      >
        <div
          role="search"
          style={{
            display: 'flex',
            'align-items': 'center',
            gap: '6px',
            background: 'var(--bg-2)',
            border: '1px solid var(--border)',
            'border-radius': 'var(--radius-md)',
            padding: '4px 8px',
            'min-width': '160px',
            cursor: 'text',
          }}
          onClick={openComposer}
        >
          <Search size={14} color="var(--fg-3)" aria-hidden="true" strokeWidth={1.75} />
          <input
            type="search"
            readOnly
            placeholder="Search…"
            aria-label="Search"
            onFocus={openComposer}
            onClick={(e) => {
              e.stopPropagation();
              openComposer();
            }}
            style={{
              flex: '1',
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--fg-1)',
              'font-family': 'var(--font-ui)',
              'font-size': '12px',
              'min-width': '0',
              cursor: 'pointer',
            }}
          />
          <span
            aria-hidden="true"
            style={{
              color: 'var(--fg-3)',
              'font-family': 'var(--font-mono)',
              'font-size': '10px',
              'line-height': '1',
              'flex-shrink': '0',
            }}
          >
            ⌘K
          </span>
        </div>

        <button
          type="button"
          aria-label="Notifications"
          onClick={() => {
            // TODO(V24-09): open notifications panel when wired.
          }}
          style={{
            display: 'flex',
            'align-items': 'center',
            'justify-content': 'center',
            background: 'transparent',
            border: 'none',
            color: 'var(--fg-2)',
            padding: '4px',
            cursor: 'pointer',
          }}
        >
          <Bell size={16} color="currentColor" aria-hidden="true" strokeWidth={1.75} />
        </button>

        <button
          type="button"
          onClick={() => {
            // TODO(V24-09): wire to new-task intake flow.
          }}
          style={{
            display: 'flex',
            'align-items': 'center',
            gap: '4px',
            background: 'var(--primary)',
            color: 'var(--on-primary)',
            border: 'none',
            'border-radius': 'var(--radius-md)',
            padding: '5px 10px',
            'font-family': 'var(--font-ui)',
            'font-size': '12px',
            'font-weight': '500',
            'line-height': '1',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--primary-hover)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--primary)';
          }}
        >
          <Plus size={14} color="currentColor" aria-hidden="true" strokeWidth={2} />
          New task
        </button>

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
    </div>
  );
}
