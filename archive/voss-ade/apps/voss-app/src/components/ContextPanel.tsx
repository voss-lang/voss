import { Show, For } from 'solid-js';
import type { ContextData, FileContextEntry } from '../pane/pty-ipc';
import './ContextPanel.css';

export interface ContextPanelProps {
  open: boolean;
  context: ContextData | null;
  paneIndex?: number;
  paneCwd?: string;
  isAgentPane: boolean;
  onTogglePin?: (path: string, pinned: boolean) => void;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function stateColor(state: FileContextEntry['state']): string {
  if (state === 'full') return 'var(--accent)';
  if (state === 'compressed') return 'var(--warning)';
  return 'var(--text-3)';
}

function barColor(pct: number): string {
  if (pct >= 90) return 'var(--error)';
  if (pct >= 70) return 'var(--warning)';
  return 'var(--accent)';
}

function cwdBasename(cwd?: string): string {
  if (!cwd) return '';
  const parts = cwd.replace(/\/+$/, '').split('/');
  return parts[parts.length - 1] || cwd;
}

export default function ContextPanel(props: ContextPanelProps) {
  const pct = () => {
    const c = props.context;
    if (!c || !c.token_limit) return 0;
    return Math.min((c.total_tokens / c.token_limit) * 100, 100);
  };

  const showSummaryBar = () => {
    const c = props.context;
    return c && c.token_limit != null;
  };

  return (
    <div class={`context-panel${props.open ? ' open' : ''}`}>
      <Show
        when={props.isAgentPane && props.context}
        fallback={
          <div class="context-empty">
            No agent context — focus an agent pane
          </div>
        }
      >
        {/* Header (D-04) */}
        <div class="context-panel-header">
          <span>Context</span>
          <Show when={props.paneIndex != null}>
            <span class="meta">
              ●{props.paneIndex} {cwdBasename(props.paneCwd)}
            </span>
          </Show>
        </div>

        {/* Summary row (D-12) */}
        <div class="context-summary">
          <div class="context-summary-text">
            {formatTokens(props.context?.total_tokens ?? 0)}
            <Show when={props.context?.token_limit != null}>
              {' / '}
              {formatTokens(props.context!.token_limit!)} tokens
            </Show>
            <Show when={props.context?.token_limit == null}> tokens</Show>
          </div>
          <Show when={showSummaryBar()}>
            <div class="context-summary-bar">
              <div
                class="context-summary-fill"
                style={{
                  width: `${pct()}%`,
                  background: barColor(pct()),
                }}
              />
            </div>
          </Show>
        </div>

        {/* File list */}
        <div class="context-file-list">
          {/* Special rows (D-17) */}
          <Show when={(props.context?.system_tokens ?? 0) > 0}>
            <div class="context-special-row">
              <span>System prompt</span>
              <span>{formatTokens(props.context!.system_tokens)}</span>
            </div>
          </Show>
          <Show when={(props.context?.conversation_tokens ?? 0) > 0}>
            <div class="context-special-row">
              <span>Conversation</span>
              <span>{formatTokens(props.context!.conversation_tokens)}</span>
            </div>
          </Show>

          {/* File rows (D-13, D-15, D-16) */}
          <For each={props.context?.files ?? []}>
            {(file) => {
              const filePct = () => {
                const total = props.context?.total_tokens ?? 1;
                return Math.min((file.tokens / total) * 100, 100);
              };
              return (
                <div class={`context-file-row${file.pinned ? ' pinned' : ''}`}>
                  <div class="context-file-info">
                    <div class="context-file-name" title={file.path}>
                      {file.path}
                    </div>
                    <div class="context-file-tokens">
                      {formatTokens(file.tokens)}
                    </div>
                  </div>
                  <div class="context-file-bar">
                    <div
                      class="context-file-bar-fill"
                      style={{
                        width: `${filePct()}%`,
                        background: stateColor(file.state),
                      }}
                    />
                  </div>
                  <div
                    class="context-state-dot"
                    style={{ background: stateColor(file.state) }}
                  />
                  <button
                    class={`context-pin-btn${file.pinned ? ' active' : ''}`}
                    onClick={() =>
                      props.onTogglePin?.(file.path, !file.pinned)
                    }
                    title={file.pinned ? 'Unpin file' : 'Pin file'}
                  >
                    {file.pinned ? '📌' : '○'}
                  </button>
                </div>
              );
            }}
          </For>
        </div>
      </Show>
    </div>
  );
}
