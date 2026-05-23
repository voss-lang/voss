import type { Component } from 'solid-js';

export interface AgentItemProps {
  paneId: string;
  cliBinary: string;
  model: string;
  role: string;
  costUsd: number;
  isStreaming: boolean;
  isActive: boolean;
  onContextMenu?: (e: MouseEvent) => void;
  onClick?: () => void;
}

const AgentItem: Component<AgentItemProps> = (props) => {
  const displayName = () =>
    props.cliBinary.charAt(0).toUpperCase() + props.cliBinary.slice(1);

  const costLabel = () => `$${props.costUsd.toFixed(2)}`;

  const roleColor = () => `var(--role-${props.role})`;

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
      <span
        class={`agent-cost${props.costUsd > 1.0 ? ' agent-cost--hot' : ''}`}
      >
        {costLabel()}
      </span>
    </div>
  );
};

export default AgentItem;
