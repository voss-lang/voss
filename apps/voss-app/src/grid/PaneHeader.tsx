import { Show } from 'solid-js';

/**
 * 22px Variant B per-pane header (GRD-06, A3-UI-SPEC "Pane Header Contract").
 *
 * A3's only additive segments over the A2 header model are the numeric index
 * and the `⋯` trigger; cwd/shell come from the leaf, dot-state/process are
 * A2-owned values surfaced via props (A2's `PaneComponent` does not expose
 * them yet — see A3-05 SUMMARY deviation; `process=""` ⇒ hidden, never a
 * dash). Focused header lifts to `bg-bg-2`, unfocused `bg-bg-1`; instant
 * repaint, no CSS animation, no boundary stroke (GRD-07).
 */
export interface PaneHeaderProps {
  index: number;
  focused: boolean;
  cwd: string;
  shell: string;
  /** A2-owned shell health (default 'running' until A2 surfaces it). */
  dotState?: 'running' | 'exited';
  /** A2-owned foreground command; '' ⇒ segment hidden. */
  process?: string;
  /** A7: show `[Cmd+B...]` prefix indicator (focused pane only). */
  prefixActive?: boolean;
  /** A7: reserve indicator width under tmux profile to avoid header shift. */
  prefixReserved?: boolean;
  /** A12: whether pane runs an agent CLI. */
  isAgent?: boolean;
  /** A12: CSS variable for role color (e.g. '--role-planner'). */
  roleColor?: string;
  /** A12: agent is currently streaming output. */
  isStreaming?: boolean;
  /** A12: agent accumulated cost in USD. */
  costUsd?: number;
  onToggleMenu: () => void;
}

function Pipe() {
  return (
    <span class="text-fg-3" style={{ margin: '0 4px' }} aria-hidden="true">
      │
    </span>
  );
}

export default function PaneHeader(props: PaneHeaderProps) {
  const exited = () => props.dotState === 'exited';
  const dotClass = () => (exited() ? 'text-accent-red' : 'text-accent-green');
  // Color tiers (A3-UI-SPEC table): primary = cwd/process, secondary = index/⋯.
  const primary = () => (props.focused ? 'text-fg-0' : 'text-fg-2');
  const secondary = () => (props.focused ? 'text-fg-1' : 'text-fg-3');

  return (
    <div
      class={`font-mono ${props.focused && props.isAgent ? '' : props.focused ? 'bg-bg-2' : 'bg-bg-1'}`}
      style={{
        display: 'flex',
        'align-items': 'center',
        position: 'relative',
        height: 'var(--pane-header-height, 22px)',
        'min-height': 'var(--pane-header-height, 22px)',
        padding: '0 8px 0 12px',
        'font-size': '11px',
        'font-weight': 400,
        overflow: 'hidden',
        ...(props.focused && props.isAgent ? { background: 'var(--focus-soft)' } : {}),
      }}
    >
      {/* A12: role-colored accent bar for agent panes */}
        <Show when={props.isAgent}>
          <span
            style={{
              position: 'absolute',
              left: '0',
              top: '0',
              bottom: '0',
              width: '3px',
              background: props.focused ? 'var(--focus)' : `var(${props.roleColor ?? '--role-user'})`,
            }}
          />
        </Show>
        <span
          class={props.isAgent
            ? (props.isStreaming ? 'pane-dot--streaming' : '')
            : dotClass()}
          style={{
            opacity: props.focused ? 1 : 0.6,
            'font-size': '8px',
            ...(props.isAgent ? {
              color: `var(${props.roleColor ?? '--role-user'})`,
            } : {}),
          }}
          aria-label={props.isAgent
            ? (props.isStreaming ? 'Agent streaming' : 'Agent idle')
            : (exited() ? 'Shell exited' : 'Shell running')}
        >
          ●
        </span>
      <Pipe />
      <span
        class={secondary()}
        style={{ 'font-size': '10px' }}
        data-pane-index={props.index}
      >
        {props.index}
      </span>
      <Pipe />
      <span
        class={primary()}
        style={{
          overflow: 'hidden',
          'text-overflow': 'ellipsis',
          'white-space': 'nowrap',
          'min-width': 0,
        }}
      >
        {props.cwd}
      </span>
      <Pipe />
      <span class={primary()}>{props.shell}</span>
      <Show when={props.process}>
        <Pipe />
        <span class={primary()} style={{ 'white-space': 'nowrap' }}>
          {props.process}
        </span>
      </Show>
      <Show when={props.isAgent && props.costUsd != null}>
          <Pipe />
          <span
            data-testid="agent-cost"
            style={{
              'font-family': 'var(--font-mono)',
              'font-size': '11px',
              color: (props.costUsd ?? 0) > 1.0 ? 'var(--focus)' : 'var(--fg-2)',
              'white-space': 'nowrap',
            }}
          >
            ${(props.costUsd ?? 0).toFixed(2)}
          </span>
        </Show>
        <span style={{ flex: 1 }} />
      {/* A7: tmux prefix indicator — reserved 72px, visible only when active + focused */}
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
        class={secondary()}
        aria-label="Pane menu"
        style={{
          background: 'transparent',
          border: 'none',
          padding: '0 4px',
          cursor: 'default',
          'font-size': '11px',
        }}
        onClick={() => props.onToggleMenu()}
      >
        ⋯
      </button>
    </div>
  );
}
