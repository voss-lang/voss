// Polls because ObserveClient's drop counter is not reactive.

import { Show, createSignal, onCleanup, onMount } from 'solid-js';
import { liveServer } from '../org/live/liveServer';
import { getObserveSettings } from '../org/live/sidecarClient';
import {
  observeContextForWorkspace,
  observeQueueStats,
} from '../pane/observeClient';

type CaptureState = 'active' | 'paused';

const POLL_MS = 5000;

export default function ObserveStatusDot() {
  const [state, setState] = createSignal<CaptureState | null>(null);
  const [dropped, setDropped] = createSignal(0);

  async function refresh(): Promise<void> {
    setDropped(observeQueueStats().dropped);
    const server = liveServer();
    if (!server?.cwd) {
      setState(null);
      return;
    }
    try {
      const ctx = await observeContextForWorkspace(server.cwd, server.sidecarId);
      const repos = await getObserveSettings(server.sidecarId);
      const enrollment = repos[ctx.repositoryId];
      setState(
        !enrollment?.enabled ? null : enrollment.paused || !enrollment.capture ? 'paused' : 'active',
      );
    } catch {
      // Sidecar unreachable: keep the last known state; the dropped count
      // (updated above) is the signal that matters here.
    }
  }

  onMount(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), POLL_MS);
    onCleanup(() => clearInterval(timer));
  });

  const title = () => {
    const base =
      state() === 'active'
        ? 'Command capture active'
        : 'Command capture paused';
    return dropped() > 0
      ? `${base} · ${dropped()} event${dropped() !== 1 ? 's' : ''} dropped (sidecar unreachable)`
      : base;
  };

  return (
    <Show when={state()}>
      {(s) => (
        <span
          aria-label="Observation capture"
          title={title()}
          style={{
            display: 'inline-flex',
            'align-items': 'center',
            gap: '4px',
            'white-space': 'nowrap',
          }}
        >
          <span
            style={{
              color:
                s() === 'active' ? 'var(--accent-green)' : 'var(--accent-amber)',
            }}
          >
            ●
          </span>
          <span>
            {s() === 'active' ? 'capturing' : 'paused'}
            {dropped() > 0 ? ` · dropped ${dropped()}` : ''}
          </span>
        </span>
      )}
    </Show>
  );
}
