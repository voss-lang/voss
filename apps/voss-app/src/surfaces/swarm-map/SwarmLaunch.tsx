// V24 Swarm Map — launch panel (shown in the empty state).
//
// A minimal intake (goal + builder count) that calls launchSwarm. Honest about
// connection state: disabled-with-reason when there is no live server. On success
// the map's createResource picks up the new active swarm id and renders it live.

import { type Component, createSignal, Show } from 'solid-js';
import { liveServer } from '../../org/live/liveServer';
import { launchSwarm } from '../../org/live/swarmLaunch';

const SwarmLaunch: Component = () => {
  const [goal, setGoal] = createSignal('');
  const [builders, setBuilders] = createSignal(2);
  const [busy, setBusy] = createSignal(false);
  const [note, setNote] = createSignal<string | null>(null);

  const connected = () => !!liveServer();
  const canLaunch = () => connected() && goal().trim().length > 0 && !busy();

  async function onLaunch(): Promise<void> {
    const srv = liveServer();
    if (!srv) {
      setNote('Not connected to a live Voss server.');
      return;
    }
    if (!goal().trim()) return;
    setBusy(true);
    setNote(null);
    try {
      await launchSwarm(srv, { goal: goal().trim(), builders: builders() });
    } catch (e) {
      setNote(`Couldn't launch swarm: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div class="swarm-launch" role="group" aria-label="Launch a swarm">
      <p class="swarm-empty__title">No swarm running</p>
      <p class="swarm-empty__hint">
        Describe a goal and launch a swarm — a coordinator decomposes it and
        builders work in parallel, live on this map.
      </p>

      <textarea
        class="swarm-launch__goal"
        aria-label="Swarm goal"
        placeholder="Ask the swarm to…"
        rows="2"
        value={goal()}
        disabled={busy()}
        onInput={(e) => setGoal(e.currentTarget.value)}
      />

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
          {busy() ? 'Launching…' : 'Launch swarm'}
        </button>
      </div>

      <Show when={!connected()}>
        <p class="swarm-launch__reason" role="note">
          Open a workspace to connect a live Voss server.
        </p>
      </Show>
      <Show when={note()}>
        <p class="swarm-launch__reason" role="alert">
          {note()}
        </p>
      </Show>
    </div>
  );
};

export default SwarmLaunch;
