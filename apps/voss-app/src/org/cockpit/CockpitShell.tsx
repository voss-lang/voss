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
import BoardPanel from '../panels/BoardPanel';
import SessionTreePanel from '../panels/SessionTreePanel';
import ReplayPanel from '../panels/ReplayPanel';
import CardDrawer from './CardDrawer';
import GateBar from './GateBar';
import RunCommandBar from './RunCommandBar';

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

  let pickerRef: HTMLDivElement | undefined;

  onMount(() => {
    // D-04: auto-load the most-recent run on open.
    void enumerateRuns(props.cwd).then((entries) => {
      if (entries.length > 0) {
        void loadRun(entries[0].run_id, props.cwd, props.cliBinary);
      }
    });

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

      {/* D-03: always-on RunCommandBar strip, present above the 4-region grid
          regardless of selection/mode. Native client is gated/mock in V14. */}
      <RunCommandBar cwd={props.cwd} cliBinary={props.cliBinary} />

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
            <div class="cockpit-grid">
              <div class="cockpit-board" aria-label="Board spine">
                <BoardPanel
                  data={runData()}
                  onCardSelect={setSelectedCardId}
                  selectedCardId={selectedCardId()}
                />
              </div>

              <div class="cockpit-drawer" aria-label="Card detail">
                <CardDrawer />
              </div>

              <div class="cockpit-rail" aria-label="Timeline and replay">
                <SessionTreePanel data={runData()} />
                <ReplayPanel data={runData()} />
              </div>

              <div class="cockpit-gate" aria-label="Gate bar">
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
