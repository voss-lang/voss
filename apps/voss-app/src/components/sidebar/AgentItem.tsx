import { type Component, Show } from 'solid-js';

export interface AgentItemProps {
  paneId: string;
  cliBinary: string;
  model: string;
  role: string;
  costUsd: number;
  isStreaming: boolean;
  isActive: boolean;
  taskPrompt?: string;
  tokensUsed?: number;
  tokenLimit?: number | null;
  onContextMenu?: (e: MouseEvent) => void;
  onClick?: () => void;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

const AgentItem: Component<AgentItemProps> = (props) => {
  const displayName = () =>
    props.cliBinary.charAt(0).toUpperCase() + props.cliBinary.slice(1);

  const roleColor = () => `var(--role-${props.role})`;

  const tokenColor = () => {
    if (props.tokenLimit && props.tokensUsed != null && props.tokensUsed / props.tokenLimit > 0.8) {
      return 'var(--accent-amber)';
    }
    return 'var(--fg-3)';
  };

  return (
    <div
      class={`agent-item${props.isActive ? ' agent-item--active' : ''}`}
      draggable={true}
      onDragStart={(e) => {
        e.dataTransfer!.setData('text/plain', props.paneId);
      }}
      onContextMenu={(e) => props.onContextMenu?.(e)}
      onClick={() => props.onClick?.()}
    >
      {/* Row 1: status + name + model + role + streaming */}
      <div style={{ display: 'flex', 'align-items': 'center', gap: '6px', width: '100%' }}>
        <div
          class={`agent-dot${props.isStreaming ? ' agent-dot--streaming' : ''}`}
          style={{
            'border-radius': '9999px',
            background: roleColor(),
            'box-shadow': `0 0 4px ${roleColor()}`,
          }}
        />
        <span class="agent-name">{displayName()}</span>
        <span class="agent-model">{props.model}</span>
        <span
          class="agent-role"
          style={{
            'border-radius': '6px',
            background: `color-mix(in srgb, ${roleColor()} 20%, transparent)`,
            color: roleColor(),
          }}
        >
          {props.role}
        </span>
        <Show when={props.isStreaming}>
          <span style={{ 'margin-left': 'auto', 'font-size': '10px', color: 'var(--focus)' }}>streaming</span>
        </Show>
      </div>
      {/* Row 2: task (if present) */}
      <Show when={props.taskPrompt}>
        <div style={{ 'font-family': "'Inter', system-ui, sans-serif", 'font-size': '11px', color: 'var(--fg-2)', 'white-space': 'nowrap', overflow: 'hidden', 'text-overflow': 'ellipsis', width: '100%', 'padding-left': '13px' }}>
          {props.taskPrompt}
        </div>
      </Show>
      {/* Row 3: token usage */}
      <Show when={props.tokensUsed != null}>
        <div style={{ 'font-family': "'JetBrains Mono', ui-monospace, monospace", 'font-size': '11px', color: tokenColor(), 'padding-left': '13px' }}>
          {formatTokens(props.tokensUsed ?? 0)}{props.tokenLimit ? ` / ${formatTokens(props.tokenLimit)} tokens` : ' tokens'}
        </div>
      </Show>
    </div>
  );
};

export default AgentItem;
