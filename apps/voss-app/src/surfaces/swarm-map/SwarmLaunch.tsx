// V24 swarm surface — launch panel (shown in the empty state).
//
// A minimal intake (goal + builder count) that calls launchSwarm. Honest about
// connection state: disabled-with-reason when there is no live server. On success
// the map's createResource picks up the new active swarm id and renders it live.

import { type Component, createSignal, onMount, Show } from 'solid-js';
import {
  liveServer,
  connectLiveServer,
  canConnectLiveServer,
} from '../../org/live/liveServer';
import { launchSwarm } from '../../org/live/swarmLaunch';

interface SwarmLaunchProps {
  compact?: boolean;
  onClose?: () => void;
}

const SwarmLaunch: Component<SwarmLaunchProps> = (props) => {
  const [goal, setGoal] = createSignal('');
  const [builders, setBuilders] = createSignal(2);
  const [busy, setBusy] = createSignal(false);
  const [phase, setPhase] = createSignal<'connecting' | 'launching' | null>(null);
  const [note, setNote] = createSignal<string | null>(null);
  let goalRef: HTMLTextAreaElement | undefined;

  const connected = () => !!liveServer();
  // Launchable when already connected, or when we can spin up a server on
  // demand — the click spawns the sidecar first, then launches.
  const canLaunch = () =>
    goal().trim().length > 0 &&
    !busy() &&
    (connected() || canConnectLiveServer());

  onMount(() => {
    if (props.compact) queueMicrotask(() => goalRef?.focus());
  });

  async function onLaunch(): Promise<void> {
    if (!goal().trim()) return;
    setBusy(true);
    setNote(null);
    try {
      let srv = liveServer();
      if (!srv) {
        setPhase('connecting');
        srv = await connectLiveServer();
      }
      if (!srv) {
        setNote('Open a workspace folder to connect a live Voss server.');
        return;
      }
      setPhase('launching');
      await launchSwarm(srv, { goal: goal().trim(), builders: builders() });
      props.onClose?.();
    } catch (e) {
      const verb = phase() === 'connecting' ? 'connect' : 'launch orchestra';
      setNote(`Couldn't ${verb}: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
      setPhase(null);
    }
  }

  return (
    <div
      classList={{
        'swarm-launch': true,
        'swarm-launch--compact': !!props.compact,
      }}
      role="group"
      aria-label="Launch an orchestra"
    >
      <Show when={!props.compact}>
        <div class="swarm-launch__intro">
          <span class="swarm-launch__mark" aria-hidden="true" />
          <div>
            <p class="swarm-empty__title">Launch orchestra</p>
            <p class="swarm-empty__hint">
              No orchestra running. Give Voss a goal, then choose how many
              builders to assign.
            </p>
          </div>
        </div>
      </Show>

      <label class="swarm-launch__field">
        <span class="swarm-launch__label">Goal</span>
        <textarea
          ref={goalRef}
          class="swarm-launch__goal"
          aria-label="Orchestra goal"
          placeholder="Describe the work to coordinate..."
          rows="3"
          value={goal()}
          disabled={busy()}
          onInput={(e) => setGoal(e.currentTarget.value)}
        />
      </label>

      <div class="swarm-launch__row">
        <label class="swarm-launch__builders">
          <span>Builders</span>
          <input
            type="number"
            min="1"
            max="6"
            aria-label="Builder count"
            value={builders()}
            disabled={busy()}
            onChange={(e) =>
              setBuilders(Math.max(1, Math.min(6, e.currentTarget.valueAsNumber || 2)))
            }
          />
        </label>
        <button
          type="button"
          class="swarm-launch__btn"
          disabled={!canLaunch()}
          onClick={() => void onLaunch()}
        >
          {phase() === 'connecting'
            ? 'Connecting…'
            : phase() === 'launching'
              ? 'Launching…'
              : 'Launch orchestra'}
        </button>
      </div>

      <Show when={!connected()}>
        <p
          classList={{
            'swarm-launch__reason': true,
            'swarm-launch__reason--warn': !canConnectLiveServer(),
          }}
          role="note"
        >
          <span aria-hidden="true">●</span>
          {canConnectLiveServer()
            ? 'Launch will start a live Voss server for this workspace.'
            : 'Open a workspace to connect a live Voss server.'}
        </p>
      </Show>
      <Show when={note()}>
        <p class="swarm-launch__reason swarm-launch__reason--warn" role="alert">
          <span aria-hidden="true">●</span>
          {note()}
        </p>
      </Show>
    </div>
  );
};

export default SwarmLaunch;
