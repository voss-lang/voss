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
      class={`font-mono ${props.focused ? 'bg-bg-2' : 'bg-bg-1'}`}
      style={{
        display: 'flex',
        'align-items': 'center',
        height: '22px',
        'min-height': '22px',
        padding: '0 10px',
        'font-size': '11px',
        'font-weight': 400,
        overflow: 'hidden',
      }}
    >
      <span
        class={dotClass()}
        style={{ opacity: props.focused ? 1 : 0.6, 'font-size': '8px' }}
        aria-label={exited() ? 'Shell exited' : 'Shell running'}
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
      <span style={{ flex: 1 }} />
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
