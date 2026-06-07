import {
  createSignal,
  onMount,
  onCleanup,
  Show,
  For,
  type Component,
} from 'solid-js';
import './orgStyles.css';
import {
  runData,
  runEntries,
  loadError,
  loading,
  currentRunId,
  loadRun,
  enumerateRuns,
  refreshRun,
} from './orgStore';
import type { RunData } from './types';
import RosterPanel from './panels/RosterPanel';
import BoardPanel from './panels/BoardPanel';
import SessionTreePanel from './panels/SessionTreePanel';
import AuditPanel from './panels/AuditPanel';
import VerdictPanel from './panels/VerdictPanel';
import BudgetPanel from './panels/BudgetPanel';
import ScopePanel from './panels/ScopePanel';
import DiffPanel from './panels/DiffPanel';
import BlockedPanel from './panels/BlockedPanel';
import ReplayPanel from './panels/ReplayPanel';

type OrgPanelId =
  | 'roster'
  | 'board'
  | 'tree'
  | 'audit'
  | 'verdict'
  | 'budget'
  | 'scope'
  | 'diff'
  | 'blocked'
  | 'replay';

// EXACT labels per UI-SPEC Panel Tab Bar.
const ORG_TABS: Array<{ id: OrgPanelId; label: string }> = [
  { id: 'roster', label: 'Roster' },
  { id: 'board', label: 'Board' },
  { id: 'tree', label: 'Tree' },
  { id: 'audit', label: 'Audit' },
  { id: 'verdict', label: 'Verdict' },
  { id: 'budget', label: 'Budget' },
  { id: 'scope', label: 'Scope' },
  { id: 'diff', label: 'Diff' },
  { id: 'blocked', label: 'Blocked' },
  { id: 'replay', label: 'Replay' },
];

function shortRunId(id: string | null): string {
  if (!id) return '—';
  return id.length > 12 ? `${id.slice(0, 12)}…` : id;
}

const OrgViewShell: Component<{
  cwd: string;
  cliBinary: string;
  onClose: () => void;
}> = (props) => {
  const [activeTab, setActiveTab] = createSignal<OrgPanelId>('roster');
  const [pickerOpen, setPickerOpen] = createSignal(false);
  const [selectedCardId, setSelectedCardId] = createSignal<string | null>(null);

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
      if (
        pickerOpen() &&
        pickerRef &&
        !pickerRef.contains(e.target as Node)
      ) {
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

  const data = (): RunData | null => runData();

  const pickRun = (runId: string) => {
    setPickerOpen(false);
    void loadRun(runId, props.cwd, props.cliBinary);
  };

  return (
    <div class="org-view-shell" role="region" aria-label="Org/Run view">
      {/* Header (28px) */}
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

      {/* Panel tab bar (36px) */}
      <div class="org-tab-bar" role="tablist" aria-label="Org panels">
        <For each={ORG_TABS}>
          {(tab) => (
            <button
              class={`org-tab${activeTab() === tab.id ? ' org-tab--active' : ''}`}
              role="tab"
              aria-selected={activeTab() === tab.id}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          )}
        </For>
      </div>

      {/* Active panel area */}
      <div class="org-panel-area" role="tabpanel">
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
            <Show when={activeTab() === 'roster'}>
              <RosterPanel data={data()} />
            </Show>
            <Show when={activeTab() === 'board'}>
              <BoardPanel
                data={data()}
                onCardSelect={setSelectedCardId}
                selectedCardId={selectedCardId()}
              />
            </Show>
            <Show when={activeTab() === 'tree'}>
              <SessionTreePanel data={data()} />
            </Show>
            <Show when={activeTab() === 'audit'}>
              <AuditPanel data={data()} />
            </Show>
            <Show when={activeTab() === 'verdict'}>
              <VerdictPanel data={data()} />
            </Show>
            <Show when={activeTab() === 'budget'}>
              <BudgetPanel data={data()} />
            </Show>
            <Show when={activeTab() === 'scope'}>
              <ScopePanel data={data()} />
            </Show>
            <Show when={activeTab() === 'diff'}>
              <DiffPanel
                data={data()}
                selectedCardId={selectedCardId()}
                onCardSelect={setSelectedCardId}
              />
            </Show>
            <Show when={activeTab() === 'blocked'}>
              <BlockedPanel data={data()} />
            </Show>
            <Show when={activeTab() === 'replay'}>
              <ReplayPanel data={data()} />
            </Show>
          </Show>
        </Show>
      </div>
    </div>
  );
};

export default OrgViewShell;
