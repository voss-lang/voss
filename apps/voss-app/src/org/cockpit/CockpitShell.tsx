import {
  createSignal,
  createEffect,
  onMount,
  onCleanup,
  Show,
  For,
  type Component,
} from 'solid-js';
import './cockpitStyles.css';
import {
  runData,
  runEntries,
  loadError,
  loading,
  currentRunId,
  loadRun,
  enumerateRuns,
  refreshRun,
} from '../orgStore';
import { selectedCardId, setSelectedCardId } from '../selection';
import type { FollowUpClient } from '../feedbackWritePath';
import type { VossClient } from '../../../../../sdk/typescript/src/client/rest';
import { liveLabel } from '../live/sseClient';
import { cardsFromRunData } from '../boardDerive';
import { reconcileSwarm, type SwarmReconcileResult } from '../swarmReconcile';
import BoardPanel from '../panels/BoardPanel';
import CockpitSidebar from './CockpitSidebar';
import TimelineRail from './TimelineRail';
import CardDrawer from './CardDrawer';
import GateBar from './GateBar';

function shortRunId(id: string | null): string {
  if (!id) return '—';
  return id.length > 12 ? `${id.slice(0, 12)}…` : id;
}

const CockpitShell: Component<{
  cwd: string;
  cliBinary: string;
  onClose: () => void;

  followUpClient?: FollowUpClient;

  vossClient?: SidecarVossClient;

  onAttach?: (sessionId: string) => void;
}> = (props) => {
  const [pickerOpen, setPickerOpen] = createSignal(false);
  const [swarmManifest, setSwarmManifest] = createSignal<unknown>(null);

  const swarm = (): SwarmReconcileResult =>
    reconcileSwarm(swarmManifest() as any);

  let pickerRef: HTMLDivElement | undefined;
  let railRef: HTMLDivElement | undefined;

  createEffect(() => {
    const id = selectedCardId();
    if (!id || !railRef) return;
    const row = railRef.querySelector<HTMLElement>(`[data-node-id="${id}"]`);
    if (!row) return;
    railRef
      .querySelectorAll('.cockpit-rail__selected')
      .forEach((el) => el.classList.remove('cockpit-rail__selected'));
    row.classList.add('cockpit-rail__selected');
    row.scrollIntoView?.({ block: 'nearest' });
  });

  onMount(() => {
    void enumerateRuns(props.cwd).then((entries) => {
      if (entries.length > 0) {
        void loadRun(entries[0].run_id, props.cwd, props.cliBinary);
      }
    });

    setSwarmManifest(null);

    const onDocKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && pickerOpen()) {
        setPickerOpen(false);
        e.stopPropagation();
      }
    };
    const onDocClick = (e: MouseEvent) => {
      if (pickerOpen() && pickerRef && !pickerRef.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    };
    document.addEventListener('keydown', onDocKey, true);
    document.addEventListener('mousedown', onDocClick, true);
    onCleanup(() => {
      document.removeEventListener('keydown', onDocKey, true);
      document.removeEventListener('mousedown', onDocClick, true);
    });
  });

  const pickRun = (runId: string) => {
    setPickerOpen(false);
    void loadRun(runId, props.cwd, props.cliBinary);
  };

  const idea = (): string | null =>
    runData()?.audit?.idea ?? runData()?.run_final?.idea ?? null;

  const progress = () => {
    const cards = cardsFromRunData(runData());
    const count = (col: string) =>
      cards.filter((c) => c.column === col).length;
    return {
      total: cards.length,
      done: count('Done'),
      inflight: count('InProgress'),
      blocked: count('Blocked'),
    };
  };

  return (
    <div class="org-view-shell" role="region" aria-label="Run cockpit">
      {}

      <div class="cockpit-body">
        <div class="cockpit-grid">
          {}
          <aside class="cockpit-sidebar" aria-label="Team sidebar" tabindex={0}>
            <CockpitSidebar
              data={runData()}
              swarm={swarm()}
              vossClient={props.vossClient}
              onAttach={props.onAttach}
            />
          </aside>

          {}
          <div class="cockpit-main">
            {}
            <div class="cockpit-runhdr">
              <button class="org-header-btn" onClick={() => props.onClose()}>
                ← Grid
              </button>
              <button
                class="org-header-btn cockpit-runhdr__pick"
                aria-haspopup="listbox"
                aria-expanded={pickerOpen()}
                onClick={() => setPickerOpen((p) => !p)}
              >
                run {shortRunId(currentRunId())} ▾
              </button>
              <button
                class="org-header-btn"
                disabled={loading()}
                onClick={() => void refreshRun(props.cwd, props.cliBinary)}
              >
                <span
                  class={`org-refresh-glyph${loading() ? ' org-refresh-glyph--spinning' : ''}`}
                >
                  ↻
                </span>
                Refresh
              </button>
              {}
              <span
                class={`cockpit-live-label cockpit-live-label--${liveLabel()}`}
                aria-label={`Data source: ${liveLabel()}`}
              >
                {liveLabel() === 'live' ? '● live' : 'snapshot'}
              </span>

              <Show when={idea()}>
                <span class="cockpit-runhdr__idea">{idea()}</span>
              </Show>

              <Show when={progress().total > 0}>
                <span class="cockpit-runhdr__prog">
                  {progress().total} cards ·{' '}
                  <b class="cockpit-prog--done">{progress().done}</b> done ·{' '}
                  <b class="cockpit-prog--inflight">{progress().inflight}</b>{' '}
                  in-flight ·{' '}
                  <b class="cockpit-prog--blocked">{progress().blocked}</b>{' '}
                  blocked
                </span>
              </Show>

              <Show when={pickerOpen()}>
                <div class="org-run-picker" role="listbox" ref={pickerRef}>
                  <Show
                    when={runEntries().length > 0}
                    fallback={
                      <div class="org-run-picker__empty">No runs found</div>
                    }
                  >
                    <For each={runEntries()}>
                      {(entry) => (
                        <div
                          class={`org-run-picker__row${entry.run_id === currentRunId() ? ' org-run-picker__row--active' : ''}`}
                          role="option"
                          aria-selected={entry.run_id === currentRunId()}
                          onClick={() => pickRun(entry.run_id)}
                        >
                          <span>{shortRunId(entry.run_id)}</span>
                          <span>{entry.has_run_final ? 'final' : 'active'}</span>
                          <span class="org-run-picker__mtime">
                            {new Date(entry.mtime_secs * 1000).toLocaleString()}
                          </span>
                        </div>
                      )}
                    </For>
                  </Show>
                </div>
              </Show>
            </div>

            {}
            <Show
              when={!loading()}
              fallback={
                <div class="org-spinner" aria-label="Loading run">
                  <span class="org-spinner__glyph">⟳</span>
                </div>
              }
            >
              <Show
                when={!loadError()}
                fallback={
                  <div class="org-error-state">
                    <h2 class="org-error-state__heading">Run not found</h2>
                    <p class="org-error-state__body">
                      The run "{currentRunId() ?? ''}" could not be loaded.
                      Check that the run ID is valid and try refreshing.
                    </p>
                    <button
                      class="org-error-state__refresh"
                      onClick={() =>
                        void refreshRun(props.cwd, props.cliBinary)
                      }
                    >
                      Refresh
                    </button>
                  </div>
                }
              >
                <div class="cockpit-board" aria-label="Board spine" tabindex={0}>
                  <BoardPanel
                    data={runData()}
                    onCardSelect={setSelectedCardId}
                    selectedCardId={selectedCardId()}
                  />
                </div>

                <div
                  class="cockpit-rail"
                  aria-label="Timeline and replay"
                  tabindex={0}
                  ref={railRef}
                >
                  <TimelineRail
                    data={runData()}
                    onNodeSelect={setSelectedCardId}
                  />
                </div>
              </Show>
            </Show>
          </div>

          {}
          <div class="cockpit-drawer" aria-label="Card detail" tabindex={0}>
            <CardDrawer followUpClient={props.followUpClient} />
          </div>

          {}
          <div class="cockpit-gate" aria-label="Gate bar" tabindex={0}>
            <GateBar />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CockpitShell;
