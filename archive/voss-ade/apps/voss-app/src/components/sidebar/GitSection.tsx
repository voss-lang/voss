import { type Component, createEffect, createSignal, For, Show, onMount, onCleanup } from 'solid-js';
import { invoke } from '@tauri-apps/api/core';

type GitCommit = {
  hash: string;
  message: string;
  timestamp_secs: number;
};

export interface GitSectionProps {
  workspacePath: string | null;
}

function relativeTimestamp(epochSecs: number): string {
  const diffSec = Math.round(Date.now() / 1000 - epochSecs);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  const d = new Date(epochSecs * 1000);
  return d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
}

const GitSection: Component<GitSectionProps> = (props) => {
  const [commits, setCommits] = createSignal<GitCommit[]>([]);
  const [isGitRepo, setIsGitRepo] = createSignal(true);
  const [loaded, setLoaded] = createSignal(false);

  const fetchLog = () => {
    const wp = props.workspacePath;
    if (!wp) {
      setCommits([]);
      setLoaded(false);
      return;
    }
    invoke<GitCommit[]>('git_log', { workspacePath: wp, limit: 10 })
      .then((result) => {
        setCommits(result);
        setIsGitRepo(result.length > 0);
        setLoaded(true);
      })
      .catch(() => {
        setCommits([]);
        setIsGitRepo(false);
        setLoaded(true);
      });
  };

  createEffect(() => {
    // Re-fetch when workspacePath changes
    props.workspacePath;
    fetchLog();
  });

  // Refresh on window focus
  const onFocus = () => fetchLog();
  onMount(() => window.addEventListener('focus', onFocus));
  onCleanup(() => window.removeEventListener('focus', onFocus));

  return (
    <Show
      when={props.workspacePath}
      fallback={<div class="sidebar-empty">No project open</div>}
    >
      <Show
        when={commits().length > 0}
        fallback={
          loaded()
            ? <div class="sidebar-empty">{isGitRepo() ? 'No commits yet' : 'Not a git repository'}</div>
            : <div class="sidebar-empty">Loading...</div>
        }
      >
        <For each={commits()}>
          {(commit) => (
            <div
              class="session-row"
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-2)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <span class="session-time">{relativeTimestamp(commit.timestamp_secs)}</span>
              <span class="session-desc" title={commit.message}>{commit.message}</span>
            </div>
          )}
        </For>
      </Show>
    </Show>
  );
};

export default GitSection;
