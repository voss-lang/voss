import { Show } from 'solid-js';

/**
 * Warp-style per-pane header — one 22px row: status + index, centered session
 * title, trailing menu (GRD-06). Grid owns this chrome; PaneComponent hides
 * its internal header when `embeddedInGrid`.
 */
export interface PaneHeaderProps {
  index: number;
  focused: boolean;
  cwd: string;
  shell: string;
  /** Foreground process / session title (from procRegistry when live). */
  process?: string;
  dotState?: 'running' | 'exited';
  prefixActive?: boolean;
  prefixReserved?: boolean;
  isAgent?: boolean;
  roleColor?: string;
  isStreaming?: boolean;
  costUsd?: number;
  onToggleMenu: () => void;
  onDragPointerDown?: (e: PointerEvent) => void;
}

function basename(p: string): string {
  const parts = p.replace(/\/+$/, '').split('/');
  return parts[parts.length - 1] || p;
}

/** Session title: live process name, else cwd, else shell. */
export function paneSessionTitle(
  process: string | undefined,
  cwd: string,
  shell: string,
): string {
  const p = process?.trim();
  if (p) return p;
  if (cwd) return basename(cwd) || cwd;
  if (shell) return shell;
  return 'Terminal';
}

export default function PaneHeader(props: PaneHeaderProps) {
  const exited = () => props.dotState === 'exited';
  const dotClass = () => (exited() ? 'text-accent-red' : 'text-accent-green');
  const title = () =>
    paneSessionTitle(props.process, props.cwd, props.shell);

  return (
    <div
      data-pane-header-grab
      class={`pane-header-bar font-ui ${props.focused && props.isAgent ? '' : props.focused ? 'bg-bg-2' : 'bg-bg-1'}`}
      style={{
        display: 'grid',
        'grid-template-columns': 'auto 1fr auto',
        'align-items': 'center',
        position: 'relative',
        height: 'var(--pane-header-height, 22px)',
        'min-height': 'var(--pane-header-height, 22px)',
        padding: '0 6px 0 10px',
        'font-size': '11px',
        'font-weight': 400,
        overflow: 'hidden',
        'touch-action': 'none',
        ...(props.focused && props.isAgent
          ? { background: 'var(--focus-soft)' }
          : {}),
      }}
      onPointerDown={(e) => props.onDragPointerDown?.(e)}
    >
      <Show when={props.isAgent}>
        <span
          style={{
            position: 'absolute',
            left: '0',
            top: '0',
            bottom: '0',
            width: '3px',
            background: props.focused
              ? 'var(--focus)'
              : `var(${props.roleColor ?? '--role-user'})`,
          }}
        />
      </Show>

      <div
        class="pane-header-bar__left"
        style={{
          display: 'flex',
          'align-items': 'center',
          gap: '6px',
          'padding-left': props.isAgent ? '4px' : '0',
        }}
      >
        <span
          class={
            props.isAgent
              ? props.isStreaming
                ? 'pane-dot--streaming'
                : ''
              : dotClass()
          }
          style={{
            opacity: props.focused ? 1 : 0.6,
            'font-size': '8px',
            ...(props.isAgent
              ? { color: `var(${props.roleColor ?? '--role-user'})` }
              : {}),
          }}
          aria-label={
            props.isAgent
              ? props.isStreaming
                ? 'Agent streaming'
                : 'Agent idle'
              : exited()
                ? 'Shell exited'
                : 'Shell running'
          }
        >
          ●
        </span>
        <span
          class={props.focused ? 'text-fg-3' : 'text-fg-3'}
          style={{ 'font-size': '10px', opacity: 0.8 }}
          data-pane-index={props.index}
        >
          {props.index}
        </span>
      </div>

      <span
        class={props.focused ? 'text-fg-0' : 'text-fg-2'}
        data-testid="pane-session-title"
        style={{
          'text-align': 'center',
          overflow: 'hidden',
          'text-overflow': 'ellipsis',
          'white-space': 'nowrap',
          'min-width': 0,
          padding: '0 8px',
        }}
        title={title()}
      >
        {title()}
      </span>

      <div
        class="pane-header-bar__right"
        style={{
          display: 'flex',
          'align-items': 'center',
          gap: '4px',
        }}
      >
        <Show when={props.isAgent && props.costUsd != null}>
          <span
            data-testid="agent-cost"
            style={{
              'font-family': 'var(--font-mono)',
              'font-size': '11px',
              color:
                (props.costUsd ?? 0) > 1.0 ? 'var(--focus)' : 'var(--fg-2)',
              'white-space': 'nowrap',
            }}
          >
            ${(props.costUsd ?? 0).toFixed(2)}
          </span>
        </Show>
        <Show when={props.prefixReserved}>
          <span
            data-testid="prefix-indicator"
            style={{
              width: '72px',
              'text-align': 'right',
              'font-size': '11px',
              'font-weight': 400,
              color: props.prefixActive ? 'var(--accent-amber)' : 'transparent',
              'flex-shrink': 0,
            }}
          >
            {props.prefixActive ? '[Cmd+B...]' : ''}
          </span>
        </Show>
        <button
          type="button"
          class={props.focused ? 'text-fg-1' : 'text-fg-3'}
          aria-label="Pane menu"
          style={{
            background: 'transparent',
            border: 'none',
            padding: '0 6px',
            cursor: 'default',
            'font-size': '14px',
            'line-height': 1,
          }}
          onClick={() => props.onToggleMenu()}
        >
          ⋯
        </button>
      </div>
    </div>
  );
}
