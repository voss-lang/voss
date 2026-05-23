import type { Component } from 'solid-js';
import Popover from '../../grid/Popover';

export interface AgentContextMenuProps {
  anchor: HTMLElement;
  paneId: string;
  costUsd: number;
  onClose: () => void;
  onFocusPane: (paneId: string) => void;
  onStopAgent: (paneId: string) => void;
  onRestartAgent: (paneId: string) => void;
  onDetachAgent: (paneId: string) => void;
}

const menuItemStyle = {
  display: 'flex',
  'align-items': 'center',
  padding: '6px 12px',
  gap: '8px',
  cursor: 'pointer',
  color: 'var(--fg-1)',
  'font-family': "'Inter', system-ui, sans-serif",
  'font-size': '11px',
  background: 'transparent',
  border: 'none',
  width: '100%',
  'text-align': 'left' as const,
};

const separatorStyle = {
  height: '1px',
  background: 'var(--border)',
  margin: '2px 0',
};

const AgentContextMenu: Component<AgentContextMenuProps> = (props) => {
  const act = (fn: () => void) => {
    fn();
    props.onClose();
  };

  return (
    <Popover anchor={props.anchor} onClose={props.onClose}>
      <div style={{ padding: '4px 0' }}>
        <button
          style={menuItemStyle}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-2)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          onClick={() => act(() => props.onStopAgent(props.paneId))}
        >
          <span style={{ width: '16px' }}>■</span>
          <span>Stop</span>
        </button>
        <button
          style={menuItemStyle}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-2)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          onClick={() => act(() => props.onRestartAgent(props.paneId))}
        >
          <span style={{ width: '16px' }}>↻</span>
          <span>Restart</span>
        </button>
        <button
          style={menuItemStyle}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-2)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          onClick={() => act(() => props.onDetachAgent(props.paneId))}
        >
          <span style={{ width: '16px' }}>⊘</span>
          <span>Detach</span>
        </button>

        <div style={separatorStyle} />

        <button
          style={menuItemStyle}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-2)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          onClick={() => act(() => void navigator.clipboard.writeText(`$${props.costUsd.toFixed(2)}`))}
        >
          <span style={{ width: '16px' }}>⎘</span>
          <span>Copy cost</span>
        </button>
        <button
          style={menuItemStyle}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-2)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          onClick={() => act(() => props.onFocusPane(props.paneId))}
        >
          <span style={{ width: '16px' }}>◎</span>
          <span>Focus pane</span>
        </button>
      </div>
    </Popover>
  );
};

export default AgentContextMenu;
