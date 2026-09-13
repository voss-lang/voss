import { type Component, For, Show } from 'solid-js';

export interface ActivityEvent {
  id: string;
  type: 'completion' | 'error';
  description: string;
  timestamp: number;
}

export interface ActivitySectionProps {
  events: ActivityEvent[];
}

function relativeTime(epochMs: number): string {
  const diffSec = Math.round((Date.now() - epochMs) / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h`;
  return `${Math.round(diffHr / 24)}d`;
}

const ActivitySection: Component<ActivitySectionProps> = (props) => {
  return (
    <Show when={props.events.length > 0} fallback={<div class="sidebar-empty">No activity yet</div>}>
      <For each={props.events}>
        {(event) => (
          <div class="session-row">
            <span class="session-time">{relativeTime(event.timestamp)}</span>
            <span class="session-desc" style={{ color: event.type === 'error' ? 'var(--accent-red)' : 'var(--fg-1)' }}>{event.description}</span>
          </div>
        )}
      </For>
    </Show>
  );
};

export default ActivitySection;
