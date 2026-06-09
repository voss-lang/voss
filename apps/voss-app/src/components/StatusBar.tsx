import { Show, createMemo } from 'solid-js';
import { procByPaneId } from '../pane/procRegistry';
import { isKnownAgentCli } from '../pane/agentDetect';
import '../org/attention/attentionPanel.css';

export type StatusBarProps = {
  workspaceName: string | undefined;
  paneCount: number;
  focusedPaneId: string | undefined;
  gitBranch: string | null | undefined;
  contextPanelOpen: boolean;
  onToggleContextPanel: () => void;
  agentCount: number;
  totalCost: number;
  onToggleSidebar: () => void;
  orgViewOpen: boolean;
  onToggleOrgView: () => void;
  // VCKP-04 AttentionQueue pill (D-05/D-06). Count + blocking flag flow from App
  // (mirrors agentCount); clicking toggles the dockable AttentionPanel.
  attentionCount: number;
  attentionBlocking: boolean;
  onToggleAttention: () => void;
};

export default function StatusBar(props: StatusBarProps) {
  const focusedProc = createMemo(() => {
    const id = props.focusedPaneId;
    if (!id) return undefined;
    return procByPaneId()[id];
  });

  const procIsAgent = createMemo(() => {
    const proc = focusedProc();
    return proc ? isKnownAgentCli(proc) : false;
  });

  return (
    <div
      style={{
        display: 'flex',
        'align-items': 'center',
        height: '22px',
        'flex-shrink': '0',
        background: 'var(--bg-0)',
        'border-top': '1px solid var(--border)',
        'font-family': 'var(--font-mono)',
        'font-size': '11px',
        color: 'var(--fg-2)',
        padding: '0 8px',
        overflow: 'hidden',
      }}
    >
      {/* Left: workspace name + Org toggle + pane count */}
      <div style={{ 'white-space': 'nowrap', display: 'flex', 'align-items': 'center', gap: '6px' }}>
        <Show when={props.workspaceName}>
          <span>{props.workspaceName}</span>
          <span style={{ margin: '0 0 0 2px' }}>&middot;</span>
        </Show>
        <button
          type="button"
          title="Toggle Org/Run view (Cmd+Shift+O)"
          onClick={() => props.onToggleOrgView()}
          style={{
            background: props.orgViewOpen ? 'rgba(255,91,31,0.15)' : 'transparent',
            border: props.orgViewOpen ? '1px solid var(--focus)' : '1px solid transparent',
            color: props.orgViewOpen ? 'var(--focus)' : 'var(--fg-3)',
            'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
            'font-size': '11px',
            'font-weight': '500',
            cursor: 'pointer',
            padding: '0 4px',
            height: '16px',
            display: 'inline-flex',
            'align-items': 'center',
          }}
        >
          Org
        </button>
        <span>
          {props.paneCount} pane{props.paneCount !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Center: focused pane process name */}
      <div
        style={{
          flex: '1',
          'text-align': 'center',
          overflow: 'hidden',
          'text-overflow': 'ellipsis',
          'white-space': 'nowrap',
        }}
      >
        <Show when={focusedProc()}>
          <span
            style={{
              color: procIsAgent() ? 'var(--accent-cyan)' : 'var(--fg-1)',
            }}
          >
            {focusedProc()}
          </span>
        </Show>
      </div>

      {/* Right: context panel toggle (F4 D-09) + git branch */}
      <div style={{ 'white-space': 'nowrap', display: 'flex', 'align-items': 'center', gap: '4px' }}>
        <Show when={props.attentionCount > 0}>
          <button
            type="button"
            class={props.attentionBlocking ? 'attn-pill--pulse' : undefined}
            title="Toggle attention queue"
            onClick={() => props.onToggleAttention()}
            style={{
              background: 'rgba(255,91,31,0.15)',
              border: '1px solid var(--focus)',
              color: 'var(--focus)',
              'border-radius': '9999px',
              padding: '0 8px',
              height: '16px',
              display: 'inline-flex',
              'align-items': 'center',
              'font-family': 'var(--font-mono)',
              'font-size': '11px',
              cursor: 'pointer',
              'white-space': 'nowrap',
              gap: '4px',
            }}
          >
            <span>{props.attentionBlocking ? '⚠' : '◆'}</span>
            <span>{props.attentionCount}</span>
          </button>
        </Show>
        <Show when={props.agentCount > 0}>
          <button
            type="button"
            onClick={() => props.onToggleSidebar()}
            style={{
              background: 'rgba(255,91,31,0.15)',
              border: '1px solid var(--focus)',
              color: 'var(--focus)',
              'border-radius': '9999px',
              padding: '0 8px',
              height: '16px',
              display: 'inline-flex',
              'align-items': 'center',
              'font-family': 'var(--font-mono)',
              'font-size': '11px',
              cursor: 'pointer',
              'white-space': 'nowrap',
              gap: '4px',
            }}
          >
            <span>●</span>
            <span>
              {props.agentCount} agent{props.agentCount !== 1 ? 's' : ''} · ${props.totalCost.toFixed(2)}
            </span>
          </button>
        </Show>
        <button
          type="button"
          title="Toggle context panel (Cmd+I)"
          onClick={() => props.onToggleContextPanel()}
          style={{
            background: props.contextPanelOpen ? 'var(--bg-2)' : 'transparent',
            color: props.contextPanelOpen ? 'var(--accent)' : 'var(--fg-2)',
            border: 'none',
            'font-family': 'var(--font-mono)',
            'font-size': '11px',
            cursor: 'pointer',
            padding: '0 6px',
            'border-radius': '3px',
          }}
        >
          Ctx
        </button>
        <Show when={props.gitBranch}>
          <span>{props.gitBranch}</span>
        </Show>
      </div>
    </div>
  );
}
