import { type Component, For, Show } from 'solid-js';

export interface UsageEntry {
  name: string;
  tokensUsed: number;
}

export interface UsageSectionProps {
  entries: UsageEntry[];
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

const UsageSection: Component<UsageSectionProps> = (props) => {
  const total = () => props.entries.reduce((sum, e) => sum + e.tokensUsed, 0);

  return (
    <Show when={props.entries.length > 0} fallback={<div class="sidebar-empty">No usage data</div>}>
      <div style={{ padding: '4px 12px' }}>
        <div style={{ display: 'flex', 'justify-content': 'space-between', 'font-family': "'JetBrains Mono', ui-monospace, monospace", 'font-size': '11px', 'font-weight': '600', color: 'var(--fg-1)', 'margin-bottom': '4px' }}>
          <span>Total</span>
          <span>{formatTokens(total())} tokens</span>
        </div>
        <For each={props.entries}>
          {(entry) => (
            <div style={{ display: 'flex', 'justify-content': 'space-between', 'font-family': "'JetBrains Mono', ui-monospace, monospace", 'font-size': '11px', color: 'var(--fg-3)', padding: '1px 0' }}>
              <span>{entry.name}</span>
              <span>{formatTokens(entry.tokensUsed)}</span>
            </div>
          )}
        </For>
      </div>
    </Show>
  );
};

export default UsageSection;
