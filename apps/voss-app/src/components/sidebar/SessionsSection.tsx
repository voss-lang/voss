import { type Component, For, Show } from 'solid-js';

export interface SessionsSectionProps {
  sessions: {
    id: string;
    description: string;
    startedAt: number;
    stoppedAt: number | null;
  }[];
}

function relativeTime(epochMs: number): string {
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  const diffMs = epochMs - Date.now();
  const diffSec = Math.round(diffMs / 1000);
  const absSec = Math.abs(diffSec);

  if (absSec < 60) return rtf.format(diffSec, 'second');
  const diffMin = Math.round(diffSec / 60);
  const absMin = Math.abs(diffMin);
  if (absMin < 60) return rtf.format(diffMin, 'minute');
  const diffHr = Math.round(diffMin / 60);
  const absHr = Math.abs(diffHr);
  if (absHr < 24) return rtf.format(diffHr, 'hour');
  const diffDay = Math.round(diffHr / 24);
  return rtf.format(diffDay, 'day');
}

const SessionsSection: Component<SessionsSectionProps> = (props) => {
  return (
    <Show
      when={props.sessions.length > 0}
      fallback={<div class="sidebar-empty">No sessions yet</div>}
    >
      <For each={props.sessions}>
        {(session) => (
          <div class="session-row">
            <span class="session-time">
              {relativeTime(session.startedAt)}
            </span>
            <span class="session-desc">{session.description}</span>
          </div>
        )}
      </For>
    </Show>
  );
};

export default SessionsSection;
