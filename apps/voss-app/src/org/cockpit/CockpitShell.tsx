// VCKP-05 — integrated 4-region Run cockpit (D-01/D-02/D-08).
//
// Replaces the OrgViewShell tab switcher. The run-load + run-picker logic and
// the loading/error <Show> wrappers are LIFTED VERBATIM from OrgViewShell
// (OrgViewShell.tsx:74-110,184-209). The ORG_TABS/activeTab tab machinery is
// dropped entirely (D-01/D-02 — no legacy tab escape hatch).
//
// Four regions, driven by ONE global selection (../selection):
//   1. Board spine column  — BoardPanel (compact cards, onCardSelect)
//   2. Card detail drawer  — CardDrawer (persistent, composes panel bodies)
//   3. Timeline/replay rail — SessionTreePanel + ReplayPanel
//   4. Bottom gate bar     — GateBar
// Selecting a card once updates all four (single-selection acceptance).

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
import { liveLabel } from '../live/sseClient';
import { reconcileSwarm, type SwarmReconcileResult } from '../swarmReconcile';
import BoardPanel from '../panels/BoardPanel';
import SessionTreePanel from '../panels/SessionTreePanel';
import ReplayPanel from '../panels/ReplayPanel';
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
}> = (props) => {
  const [pickerOpen, setPickerOpen] = createSignal(false);
  const [swarmManifest, setSwarmManifest] = createSignal<unknown>(null);

  // VCKP-07 (GATED A13, best-effort): the swarm roster derives from the A13
  // .voss/swarm/manifest.json. reconcileSwarm is null-tolerant, so absence of a
  // manifest yields empty roster/cards and the section below stays unrendered.
  const swarm = (): SwarmReconcileResult =>
    reconcileSwarm(swarmManifest() as any);

  let pickerRef: HTMLDivElement | undefined;
  let railRef: HTMLDivElement | undefined;

  // UI-REVIEW 6a: the timeline rail REACTS to the global selection — selecting
  // a board card scrolls/highlights the matching session-tree row. Thin
  // adapter over the reused panel (D-02: no panel rewrite) via the
  // data-node-id attr SessionTreePanel already renders.
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
    // D-04: auto-load the most-recent run on open.
    void enumerateRuns(props.cwd).then((entries) => {
      if (entries.length > 0) {
        void loadRun(entries[0].run_id, props.cwd, props.cliBinary);
      }
    });

    // VCKP-07 (GATED A13, best-effort): read .voss/swarm/manifest.json if a
    // future read path exists. No read command / fs-plugin ships in V14, so this
    // degrades silently to no-swarm. We do NOT call a non-existent invoke (avoids
    // console noise); the "when present" path is covered by the swarmReconcile
    // adapter test, not faked here. Establish the null default explicitly.
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

  return (
    <div class="org-view-shell" role="region" aria-label="Run cockpit">
      {/* Header (28px) — lifted from OrgViewShell */}
      <div class="org-view-header">
        <button class="org-header-btn" onClick={() => props.onClose()}>
          ← Grid
        </button>
        <button
          class="org-header-btn org-run-label"
          aria-haspopup="listbox"
          aria-expanded={pickerOpen()}
          onClick={() => setPickerOpen((p) => !p)}
        >
          Run: {shortRunId(currentRunId())} ▾
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
        {/* VCKP-06: live/snapshot state label. Bound to the sseClient liveLabel
            signal; default 'snapshot' (no auto-stream / handshake in V14). Flips
            to 'live' only when a stream is connected (mock in tests / future
            server). Snapshot mode keeps the manual-refresh affordance above. */}
        <span
          class={`cockpit-live-label cockpit-live-label--${liveLabel()}`}
          aria-label={`Data source: ${liveLabel()}`}
        >
          {liveLabel() === 'live' ? '● live' : 'snapshot'}
        </span>

        <Show when={pickerOpen()}>
          <div class="org-run-picker" role="listbox" ref={pickerRef}>
            <Show
              when={runEntries().length > 0}
              fallback={<div class="org-run-picker__empty">No runs found</div>}
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

      {/* D-03: the RunCommandBar strip is mounted at App level ABOVE the
          grid/cockpit swap so it is present in BOTH Live Work and Run Review
          modes — it is intentionally NOT rendered here (no double strip). */}

      {/* Cockpit body — loading/error <Show> wrappers lifted from OrgViewShell */}
      <div class="cockpit-body">
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
                  The run "{currentRunId() ?? ''}" could not be loaded. Check
                  that the run ID is valid and try refreshing.
                </p>
                <button
                  class="org-error-state__refresh"
                  onClick={() => void refreshRun(props.cwd, props.cliBinary)}
                >
                  Refresh
                </button>
              </div>
            }
          >
            {/* 4-region grid: board spine | drawer | timeline rail / gate bar */}
            {/* VCKP-10: regions carry tabindex=0 in DOM order so keyboard
                focus traverses Board -> drawer -> timeline. */}
            <div class="cockpit-grid">
              <div class="cockpit-board" aria-label="Board spine" tabindex={0}>
                <div class="cockpit-region__label">Board</div>
                <BoardPanel
                  data={runData()}
                  onCardSelect={setSelectedCardId}
                  selectedCardId={selectedCardId()}
                />
              </div>

              <div class="cockpit-drawer" aria-label="Card detail" tabindex={0}>
                <div class="cockpit-region__label">Details</div>
                <CardDrawer />
              </div>

              <div
                class="cockpit-rail"
                aria-label="Timeline and replay"
                tabindex={0}
                ref={railRef}
              >
                <div class="cockpit-region__label">Timeline</div>
                <SessionTreePanel data={runData()} />
                <ReplayPanel data={runData()} />
                {/* VCKP-07: swarm roster — rendered only when a manifest
                    populated the roster. Invisible in the no-swarm default. */}
                <Show when={swarm().rosterRows.length > 0}>
                  <div class="cockpit-swarm" aria-label="Swarm roster">
                    <div class="cockpit-swarm__goal">{swarm().idea}</div>
                    <For each={swarm().rosterRows}>
                      {(a) => (
                        <div class="cockpit-swarm__row">
                          <span>{a.id}</span>
                          <span>{a.provider}</span>
                          <span>{a.status}</span>
                        </div>
                      )}
                    </For>
                  </div>
                </Show>
              </div>

              <div class="cockpit-gate" aria-label="Gate bar" tabindex={0}>
                <GateBar />
              </div>
            </div>
          </Show>
        </Show>
      </div>
    </div>
  );
};

export default CockpitShell;
