# Phase V11: ADE Org Integration — Pattern Map

**Mapped:** 2026-06-07
**Files analyzed:** 22 (new/modified)
**Analogs found:** 22 / 22

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src-tauri/src/lib.rs` (modify) | middleware/command | request-response | `src-tauri/src/lib.rs` `git_log` + `list_dir` | exact |
| `src/org/types.ts` | model | transform | `src/swarm/swarmTypes.ts` | role-match |
| `src/org/orgStore.ts` | store/service | request-response | `src/grid/sync.ts` + `src/workspaces/workspaceStore.ts` | role-match |
| `src/org/OrgViewShell.tsx` | component | request-response | `src/App.tsx` + `src/components/ContextPanel.tsx` | role-match |
| `src/org/panels/RosterPanel.tsx` | component | CRUD | `src/components/sidebar/AgentSidebar.tsx` | role-match |
| `src/org/panels/BoardPanel.tsx` | component | CRUD | `src/grid/BudgetBar.tsx` (card pattern) | role-match |
| `src/org/panels/SessionTreePanel.tsx` | component | CRUD | `src/components/ContextPanel.tsx` | role-match |
| `src/org/panels/AuditPanel.tsx` | component | CRUD | `src/components/ContextPanel.tsx` | role-match |
| `src/org/panels/VerdictPanel.tsx` | component | CRUD | `src/components/ContextPanel.tsx` | role-match |
| `src/org/panels/BudgetPanel.tsx` | component | CRUD | `src/grid/BudgetBar.tsx` | role-match |
| `src/org/panels/ScopePanel.tsx` | component | CRUD | `src/components/ContextPanel.tsx` | role-match |
| `src/org/panels/DiffPanel.tsx` | component | CRUD | `src/components/ContextPanel.tsx` | role-match |
| `src/org/panels/BlockedPanel.tsx` | component | request-response | `src/components/modal/AgentLaunchModal.tsx` | role-match |
| `src/org/panels/ReplayPanel.tsx` | component | event-driven | `src/grid/BudgetBar.tsx` + replay reducer | partial-match |
| `src/org/replayReducer.ts` | utility | transform | `src/grid/tree.ts` (pure fns) | role-match |
| `src/org/decisionActions.ts` | service | request-response | `src/grid/sync.ts` (invoke wrapper) | role-match |
| `src/org/orgStyles.css` | config | — | `src/styles/variant-b.css` + `src/components/modal/modal.css` | exact |
| `src/org/__tests__/replayReducer.test.ts` | test | transform | `src/grid/__tests__/a6-acceptance.test.tsx` | exact |
| `src/org/__tests__/boardPanel.test.tsx` | test | CRUD | `src/grid/__tests__/BudgetBar.test.tsx` | exact |
| `src/org/__tests__/fixtures/node-root.json` | test fixture | — | (new; schema from RESEARCH.md) | — |
| `src/org/__tests__/fixtures/node-child.json` | test fixture | — | (new; schema from RESEARCH.md) | — |
| `src/App.tsx` (modify) | component | event-driven | `src/App.tsx` workspace CSS toggle pattern | exact |

---

## Pattern Assignments

### `src-tauri/src/lib.rs` — `load_run`, `enumerate_runs`, `run_decision` additions

**Analog:** `src-tauri/src/lib.rs` lines 863–971 (`list_dir` + `git_log`)

**Import/struct pattern** (lines 863–870, 928–931):
```rust
#[derive(Debug, serde::Serialize)]
struct DirEntry {
    name: String,
    is_dir: bool,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    children: Vec<DirEntry>,
}

#[derive(Debug, serde::Serialize)]
struct GitCommit {
    hash: String,
    message: String,
    timestamp_secs: i64,
}
```

**Subprocess pattern** (lines 936–971 — `git_log`, the direct model for `load_run` and `run_decision`):
```rust
#[tauri::command]
fn git_log(workspace_path: String, limit: usize) -> Result<Vec<GitCommit>, String> {
    let output = std::process::Command::new("git")
        .args([
            "-C",
            &workspace_path,
            "log",
            &format!("-{}", limit),
            "--format=%H %ct %s",
        ])
        .output()
        .map_err(|e| e.to_string())?;

    if !output.status.success() {
        return Ok(Vec::new());  // graceful degradation
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    // ... parse stdout ...
    Ok(commits)
}
```

Key points:
- `std::process::Command::new(binary).args([...]).output()` — use `.arg()` per argument, never shell string interpolation (command injection guard).
- `map_err(|e| e.to_string())` — propagates as `Result<T, String>` matching the `invoke()` Tauri error contract.
- Graceful degradation: non-success exit returns empty/`Ok(None)` rather than Err for expected-absent cases.

**Directory enumerate pattern** (lines 884–920 — `read_dir_shallow`, model for `enumerate_runs`):
```rust
fn read_dir_shallow(path: &std::path::Path, depth: u32) -> Vec<DirEntry> {
    let rd = match std::fs::read_dir(path) {
        Ok(rd) => rd,
        Err(_) => return Vec::new(),
    };
    let mut entries: Vec<DirEntry> = rd
        .filter_map(|e| e.ok())
        .filter_map(|e| {
            let name = e.file_name().to_string_lossy().into_owned();
            let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
            // ... filter, build struct ...
            Some(DirEntry { name, is_dir, children })
        })
        .collect();
    entries.sort_by(|a, b| b.is_dir.cmp(&a.is_dir).then(a.name.cmp(&b.name)));
    entries
}
```

For `enumerate_runs`: filter for `is_dir` only (Pitfall 1 — flat `.json` session records are NOT run directories). Sort by `mtime_secs` descending.

**`cli_binary: String` parameter pattern** (lines 183–220 — `spawn_agent`):
```rust
async fn spawn_agent(
    ...
    cli_binary: String,
    cli_args: Vec<String>,
    ...
) -> Result<String, String> {
```
`load_run` and `run_decision` must accept `cli_binary: String` from the frontend (same pattern) because macOS Tauri processes inherit a minimal PATH where `voss` may not be discoverable. The frontend holds the configured binary path.

**Path traversal guard** (pattern from `is_voss_cli_binary` helper, lines 146–151, and `SKIP_DIRS` list, lines 871–883):
```rust
// For load_run: validate run_id before any filesystem access
if run_id.contains('/') || run_id.contains('\\') || run_id.contains("..") {
    return Err(format!("invalid run_id: {}", run_id));
}
```

**Handler registration** (lines 983–1042 — `tauri::generate_handler![]`):
```rust
.invoke_handler(tauri::generate_handler![
    // existing entries ...
    load_run,
    enumerate_runs,
    run_decision,
])
```
All three new commands must be added here. The `generate_handler!` macro requires the command `fn` to be in the same crate (cannot `pub use` cross-crate commands — see line 121 comment).

**File read pattern** (lines 61–78 — `get_theme_overrides`):
```rust
let raw = match std::fs::read_to_string(&path) {
    Ok(s) => s,
    Err(e) => {
        eprintln!("[voss-app] failed to read settings: {e}");
        return HashMap::new();  // or None / Ok(fallback)
    }
};
let data: MyStruct = match serde_json::from_str(&raw) {
    Ok(s) => s,
    Err(e) => {
        eprintln!("[voss-app] failed to parse settings: {e}");
        return fallback;
    }
};
```
Use this exact try-then-fallback pattern for reading node `.json` files and `run-final.json` — both are optional (Pitfall 5: `run-final.json` may be absent).

**`run_decision` stdout/stderr capture pattern:**
```rust
#[tauri::command]
fn run_decision(
    cli_binary: String,
    cwd: String,
    args: Vec<String>,  // e.g. ["approve", run_id, card_id]
) -> Result<DecisionResult, String> {
    let output = std::process::Command::new(&cli_binary)
        .args(&args)
        .current_dir(&cwd)
        .output()
        .map_err(|e| e.to_string())?;
    Ok(DecisionResult {
        success: output.status.success(),
        stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
        stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        exit_code: output.status.code().unwrap_or(-1),
    })
}
```
D-08 requires stdout/stderr/exit code captured and returned — pattern is `output.stdout`/`output.stderr` from `Command::output()`.

---

### `src/org/types.ts` — RunData + sub-types

**Analog:** `src/swarm/swarmTypes.ts` (lines 1–54)

**Structure pattern** (lines 1–54):
```typescript
// swarmTypes.ts — pure type/interface file, no imports, no logic
export type SwarmAgentStatus = 'pending' | 'running' | 'complete' | 'stuck' | 'error';

export interface SwarmManifest {
  id: string;
  goal: string;
  status: 'running' | 'complete' | 'cancelled';
  created: number;
  agents: SwarmAgent[];
}

export const SWARM_DIR = '.voss/swarm';
```

`src/org/types.ts` follows the same pattern: pure types, no imports, no side effects. Must include the V13.1 marker at the top:
```typescript
// V13.1-REPLACE: hand-authored stopgap — replace with codegen contract snapshot
// when Phase V13.1 TypeScript Local Client SDK lands.
```

Key interfaces to define (shapes verified from RESEARCH.md Upstream JSON Contracts):
- `RunData` — aggregate returned by `load_run` (board nodes, review sidecars, audit, session tree, run_final?)
- `SessionTreeNode` — from `.voss/sessions/<root_id>/<node_id>.json`
- `BoardTransition` / `Transition` — union type across `board.transition | em.ticket | em.routing | em.kill | em.rescope`
- `RunFinal` — from `run-final.json` (optional in `RunData`)
- `ReviewSidecar` — from `<node_id>.review.json`
- `AuditReport` — from `voss audit --format json`
- `RunEntry` — from `enumerate_runs` (run_id, mtime_secs, has_run_final)
- `DecisionResult` — from `run_decision` (success, stdout, stderr, exit_code)

---

### `src/org/orgStore.ts` — createSignal(runData) + load/refresh logic

**Analog:** `src/grid/sync.ts` (lines 1–57)

**Invoke wrapper pattern** (lines 1–20):
```typescript
import { invoke } from '@tauri-apps/api/core';
import type { GridStore } from './tree';

export async function syncGridToRust(state: GridStore): Promise<void> {
  await invoke('sync_grid', { newState: serialize(state) });
}
```

`orgStore.ts` follows the same `invoke<T>(commandName, params)` wrapper pattern. The store itself uses `createSignal`:

```typescript
import { createSignal } from 'solid-js';
import { invoke } from '@tauri-apps/api/core';
import type { RunData, RunEntry } from './types';

export const [runData, setRunData] = createSignal<RunData | null>(null);
export const [runEntries, setRunEntries] = createSignal<RunEntry[]>([]);
export const [loadError, setLoadError] = createSignal<string | null>(null);
export const [loading, setLoading] = createSignal(false);

export async function loadRun(runId: string, cwd: string, cliBinary: string): Promise<void> {
  setLoading(true);
  setLoadError(null);
  try {
    const data = await invoke<RunData>('load_run', { runId, cwd, cliBinary });
    setRunData(data);
  } catch (e) {
    setLoadError(String(e));
    setRunData(null);
  } finally {
    setLoading(false);
  }
}

export async function enumerateRuns(cwd: string): Promise<RunEntry[]> {
  return invoke<RunEntry[]>('enumerate_runs', { cwd });
}
```

**Proxy/clone safety** (from `sync.ts` lines 14–16):
```typescript
/** Deep structural clone — strips Solid store proxies to a plain object. */
function serialize(state: GridStore): GridStore {
  return JSON.parse(JSON.stringify(state)) as GridStore;
}
```
When extracting `RunData` fields to pass to the replay reducer, use this same `JSON.parse(JSON.stringify(x))` pattern (not `structuredClone`, not `produce` — Pitfall 3).

---

### `src/App.tsx` — Org/Run view toggle (modification)

**Analog:** `src/App.tsx` lines 1174–1218 (workspace CSS toggle) + lines 947–1018 (`onAppKey` keyboard handler)

**CSS display toggle pattern** (lines 1183–1213 — the definitive model, verified working for GridRoot PTY preservation):
```typescript
<Show when={shouldMount()}>
  <div
    data-workspace-id={workspaceId}
    style={{
      display: activeId() === workspaceId ? 'flex' : 'none',
      flex: '1',
      'min-height': '0',
      'flex-direction': 'column',
    }}
  >
    <GridRoot ... />
  </div>
</Show>
```

The Org/Run view toggle wraps the existing `<For each={workspaceIds()}>` block in a CSS-hidden div and adds `OrgViewShell` as a sibling. Critical: use `display: none` CSS, NOT `<Show>` around `GridRoot`. Using `<Show>` destroys PTY sessions (Pitfall 6).

**V11 toggle insertion point** — inside the `<div style={{ flex: '1', 'min-height': '0', 'min-width': '0', display: 'flex', 'flex-direction': 'column', position: 'relative' }}>` at line 1173:
```typescript
// NEW: add orgViewOpen signal at App() top (with other createSignal calls ~line 227)
const [orgViewOpen, setOrgViewOpen] = createSignal(false);

// NEW: in onAppKey (after existing Cmd+B handling, ~line 998):
if (e.metaKey && e.shiftKey && (e.key === 'o' || e.key === 'O')) {
  setOrgViewOpen(prev => !prev);
  e.preventDefault();
  e.stopImmediatePropagation();
  return;
}

// IN JSX: wrap existing For loop and ContextPanel in a display-toggled div,
// add OrgViewShell as a sibling:
<div style={{ display: orgViewOpen() ? 'none' : 'flex', flex: '1', 'min-height': '0', 'flex-direction': 'column', position: 'relative' }}>
  <For each={workspaceIds()}> {/* existing */ } </For>
  <ContextPanel ... />  {/* existing */}
</div>
<Show when={orgViewOpen()}>
  <OrgViewShell
    cwd={workspacePath() ?? ''}
    cliBinary={/* configured voss path */}
    onClose={() => setOrgViewOpen(false)}
  />
</Show>
```

**StatusBar button pattern** (from `StatusBar.tsx` lines 79–104 — existing agent count button):
```typescript
<button
  type="button"
  onClick={() => props.onToggleSidebar()}
  style={{
    background: 'rgba(255,91,31,0.15)',
    border: '1px solid var(--focus)',
    color: 'var(--focus)',
    'border-radius': '9999px',
    padding: '0 8px',
    height: '16px',
    // ...
  }}
>
```
The `Org` toggle button in StatusBar (left region per UI-SPEC) follows this exact button style when active. Inactive state: `color: var(--fg-3)`, `background: transparent`, `border: none`.

---

### `src/org/OrgViewShell.tsx` — Outer shell with header, tab bar, panel routing

**Analog:** `src/components/modal/AgentLaunchModal.tsx` (lines 65–372) + `src/App.tsx` JSX structure

**Component skeleton pattern** (from AgentLaunchModal lines 65–98):
```typescript
const OrgViewShell: Component<OrgViewShellProps> = (props) => {
  const [activeTab, setActiveTab] = createSignal<OrgPanelId>('roster');
  const [visible, setVisible] = createSignal(false);

  onMount(() => {
    requestAnimationFrame(() => setVisible(true));
    // auto-load most-recent run (D-04)
    void enumerateRuns(props.cwd).then(entries => {
      if (entries.length > 0) void loadRun(entries[0].run_id, props.cwd, props.cliBinary);
    });
  });
  // ...
};
```

**Tab bar pattern** (from AgentLaunchModal lines 196–210 — `.modal-tabs` / `.modal-tab`):
```typescript
<div class="org-tab-bar">
  <For each={ORG_TABS}>
    {(tab) => (
      <button
        class={`org-tab${activeTab() === tab.id ? ' org-tab--active' : ''}`}
        onClick={() => setActiveTab(tab.id)}
        role="tab"
        aria-selected={activeTab() === tab.id}
      >
        {tab.label}
      </button>
    )}
  </For>
</div>
```

**Show/For panel routing pattern** (from AgentLaunchModal lines 213–356):
```typescript
<Show when={activeTab() === 'roster'}>
  <RosterPanel data={runData()} />
</Show>
<Show when={activeTab() === 'board'}>
  <BoardPanel data={runData()} onCardSelect={setSelectedCardId} />
</Show>
// ... etc for all 10 panels
```

**Loading/error state pattern** (from AgentLaunchModal — visible signal + Show fallback, lines 92–96 and 180–188):
```typescript
// Loading state: centered spinner
<Show when={loading()}>
  <div class="org-spinner-overlay">⟳</div>
</Show>
// Error state: view-level centered error
<Show when={loadError()}>
  <div class="org-error-state">
    <h2>Run not found</h2>
    <p>The run "{currentRunId()}" could not be loaded...</p>
  </div>
</Show>
```

---

### `src/org/panels/BoardPanel.tsx` — 6-column Kanban

**Analog:** `src/grid/__tests__/BudgetBar.test.tsx` (for the data shape) + `src/components/StatusBar.tsx` (for inline CSS pattern)

**Budget bar color logic** (from `BudgetBar.tsx` — referenced in test lines 46–67):
```typescript
// Budget micro-bar color logic (same thresholds as BudgetBar component):
const barColor = (pct: number) =>
  pct >= 90 ? 'var(--accent-red)'
  : pct >= 70 ? 'var(--accent-amber)'
  : 'var(--accent-green)';
```

**CSS display/data rendering pattern** (from `StatusBar.tsx` lines 17–128 — inline styles, Show, For):
```typescript
export default function BoardPanel(props: { data: RunData | null; onCardSelect: (id: string) => void }) {
  return (
    <div style={{ display: 'flex', flex: '1', overflow: 'hidden' }}>
      <For each={COLUMNS}>
        {(col) => {
          const cards = () => cardsForColumn(props.data, col);
          return (
            <div style={{ flex: '1', 'overflow-y': 'auto', 'border-right': '1px solid var(--border)' }}>
              <div style={{ color: `var(--org-col-${colVar(col)})`, ... }}>
                {col} ({cards().length})
              </div>
              <For each={cards()}>
                {(card) => <BoardCard card={card} onSelect={props.onCardSelect} />}
              </For>
            </div>
          );
        }}
      </For>
    </div>
  );
}
```

**Risk tint pattern** (from UI-SPEC token definitions — no analog, use CSS vars):
```typescript
const riskTint = (risk: string) =>
  risk === 'high' ? 'var(--card-risk-high)'
  : risk === 'low' ? 'var(--card-risk-low)'
  : 'var(--card-risk-med)';
```

---

### `src/org/panels/BlockedPanel.tsx` — Decision flow with confirmation dialog

**Analog:** `src/components/modal/AgentLaunchModal.tsx` (entire file, lines 1–374) + `src/components/modal/modal.css`

**Dialog skeleton pattern** (from AgentLaunchModal lines 180–210):
```typescript
return (
  <div class="modal-backdrop" onClick={onBackdropClick} onKeyDown={onKeyDown}>
    <div
      ref={panelRef}
      class={`modal-panel${visible() ? ' modal-panel--visible' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <div class="modal-header">
        <span id="dialog-title" class="modal-header__title">{action}: {cardId}</span>
        <button class="modal-header__dismiss" onClick={onDismiss} aria-label="Close dialog">×</button>
      </div>
      {/* CLI preview block — D-07 */}
      <div class="org-cli-preview">
        <div class="org-cli-preview__label">Command to run:</div>
        <pre class="org-cli-preview__code">{cliCommand()}</pre>
      </div>
      {/* Result area — initially hidden, D-08 */}
      <Show when={result()}>
        <div class={result()!.success ? 'org-result--success' : 'org-result--failure'}>
          {result()!.success ? '✓ Done' : '✗ Failed'}
          <pre>{result()!.success ? result()!.stdout.slice(0, 200) : result()!.stderr}</pre>
        </div>
      </Show>
      <div class="modal-footer">
        <button onClick={onDismiss}>Keep Viewing</button>
        <button
          disabled={executing()}
          style={{ opacity: executing() ? '0.5' : '1' }}
          onClick={handleConfirm}
        >
          Confirm
        </button>
      </div>
    </div>
  </div>
);
```

**Focus trap + Escape key pattern** (from AgentLaunchModal lines 163–173):
```typescript
const onBackdropClick = (e: MouseEvent) => {
  if (panelRef && !panelRef.contains(e.target as Node)) {
    props.onDismiss();
  }
};
const onKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') { e.preventDefault(); props.onDismiss(); }
};
```

**Opacity enter animation** (from AgentLaunchModal lines 92–96 + modal.css lines 22–23):
```css
/* modal.css pattern */
.modal-panel {
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 150ms ease-out, transform 150ms ease-out;
}
.modal-panel--visible { opacity: 1; transform: translateY(0); }
```
```typescript
// Pattern for decision dialog:
const [visible, setVisible] = createSignal(false);
onMount(() => requestAnimationFrame(() => setVisible(true)));
```

**Auto-close after success** (D-08 — 1500ms delay):
```typescript
createEffect(() => {
  const r = result();
  if (r?.success) {
    const timer = setTimeout(() => {
      props.onDismiss();
      void refreshRun();  // auto-refresh load_run
    }, 1500);
    onCleanup(() => clearTimeout(timer));
  }
});
```

---

### `src/org/replayReducer.ts` — Pure reducer for board/card state at step N

**Analog:** `src/grid/tree.ts` (pure utility pattern) + session tests showing pure-function structure

**Pure-function pattern** (from `a6-acceptance.test.tsx` style — functions that take plain objects and return plain objects, no side effects):
```typescript
// replayReducer.ts — pure module, no Solid imports, no invoke
import type { SessionTreeNode, BoardFrame, CardSnapshot } from './types';

export function computeBoardAtStep(nodes: SessionTreeNode[], step: number): BoardFrame {
  // Collect all board.transition entries across all nodes, in order
  const allTransitions = collectBoardTransitions(nodes);
  const sliced = allTransitions.slice(0, step + 1);

  // Build column map with plain object spreads (no produce, no structuredClone)
  const columns: Record<string, CardSnapshot[]> = {
    Backlog: [], Planned: [], InProgress: [], InReview: [], Done: [], Blocked: [],
  };

  for (const t of sliced) {
    const prev = columns[t.from];
    if (prev) columns[t.from] = prev.filter(c => c.id !== t.nodeId);
    const snap: CardSnapshot = { id: t.nodeId, role: t.role, risk: t.risk, status: t.to, budget: t.budget };
    columns[t.to] = [...(columns[t.to] ?? []), snap];
  }

  return {
    columns,
    step,
    eventLabel: allTransitions[step]?.label ?? '',
  };
}
```

**Critical constraint** — no `produce()`, no `structuredClone()`, no Solid store access. Use plain spreads and `JSON.parse(JSON.stringify(x))` for deep clones. The function must receive plain deserialized objects (already through `invoke()`) and return plain object literals. See memory `voss-app-solid-produce-no-structuredclone`.

---

### `src/org/decisionActions.ts` — Invoke wrapper for run_decision

**Analog:** `src/grid/sync.ts` (lines 1–57)

**Invoke wrapper pattern** (from `sync.ts` lines 1–20):
```typescript
import { invoke } from '@tauri-apps/api/core';
import type { DecisionResult } from './types';

export type DecisionAction = 'approve' | 'reject' | 'unblock';

export function buildDecisionCommand(
  action: DecisionAction,
  runId: string,
  cardId: string,
): string {
  // Returns the literal CLI command string shown in the dialog (D-07)
  return `voss ${action} ${runId} ${cardId}`;
}

export async function runDecision(
  cliBinary: string,
  cwd: string,
  action: DecisionAction,
  runId: string,
  cardId: string,
): Promise<DecisionResult> {
  return invoke<DecisionResult>('run_decision', {
    cliBinary,
    cwd,
    args: [action, runId, cardId],
  });
}
```

---

### `src/org/orgStyles.css` — V11-specific CSS variable additions

**Analog:** `src/styles/variant-b.css` (lines 1–51) + `src/components/modal/modal.css` (lines 1–294)

**Token declaration pattern** (from `variant-b.css` lines 1–51 — scoped `:root` block):
```css
/* V11 org-panel token extensions — apply in OrgViewShell component scope */
/* These extend variant-b.css; do NOT redefine base tokens */
:root {
  --org-col-backlog:     var(--fg-3);
  --org-col-todo:        var(--fg-2);
  --org-col-in-progress: var(--accent-cyan);
  --org-col-in-review:   var(--accent-amber);
  --org-col-done:        var(--accent-green);
  --org-col-blocked:     var(--accent-red);
  --unsupported-flag:    var(--accent-red);
  --card-risk-low:  rgba(94, 194, 106, 0.08);
  --card-risk-med:  rgba(232, 184, 108, 0.08);
  --card-risk-high: rgba(232, 123, 123, 0.10);
  --role-planner:  #ff5b1f;
  --role-executor: var(--accent-cyan);
  --role-reviewer: var(--accent-amber);
  --role-watcher:  var(--fg-2);
  --role-user:     var(--accent-green);
}
```

**Component CSS pattern** (from `modal.css` lines 1–294 — BEM-like class naming, no raw hex, CSS vars only):
```css
/* V11 panel tab bar */
.org-tab-bar {
  display: flex;
  height: 36px;
  background: var(--bg-1);
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}
.org-tab {
  padding: 0 14px;
  font-family: var(--font-ui), Inter, system-ui, sans-serif;
  font-size: 11px;
  font-weight: 500;
  color: var(--fg-2);
  border: none;
  background: transparent;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  transition: color 120ms ease;
}
.org-tab:hover { color: var(--fg-1); }
.org-tab--active {
  color: var(--fg-0);
  border-bottom-color: var(--focus);
}
```

---

### `src/org/__tests__/replayReducer.test.ts` — Reducer unit tests

**Analog:** `src/grid/__tests__/a6-acceptance.test.tsx` (lines 1–249)

**Test structure pattern** (lines 1–12):
```typescript
import { describe, it, expect, vi } from 'vitest';
// Tauri mock — reducer has no invoke calls but import chain may have:
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));
import { computeBoardAtStep } from '../replayReducer';
import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';

describe('replayReducer', () => {
  it('starts all cards at Backlog at step 0', () => {
    const frame = computeBoardAtStep([nodeRoot, nodeChild], 0);
    expect(frame.columns['Backlog']).toHaveLength(/* known count from fixture */);
  });

  it('advances card to InProgress at the correct step', () => {
    const frame = computeBoardAtStep([nodeRoot, nodeChild], 1);
    const card = frame.columns['InProgress']?.find(c => c.id === nodeChild.id);
    expect(card).toBeDefined();
  });
});
```

**Key test patterns from analog:**
- `vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))` — always mock Tauri at the top of test files (lines 12–13 of a6-acceptance.test.tsx).
- Describe blocks mapped to requirement IDs (e.g. VADE-10).
- Pure logic tests: no render, no DOM, no `mount()` helper needed for reducer tests.

---

### `src/org/__tests__/boardPanel.test.tsx` — Panel rendering tests

**Analog:** `src/grid/__tests__/BudgetBar.test.tsx` (lines 1–93)

**Mount/render/cleanup pattern** (lines 1–18):
```typescript
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});
```

**Fixture import pattern** (from BudgetBar.test.tsx lines 20–26 — BASE fixture object):
```typescript
import auditReport from './fixtures/audit-report.json';
import nodeRoot from './fixtures/node-root.json';
import type { RunData } from '../types';

// Assemble a minimal RunData from fixtures
const FIXTURE_RUN_DATA: RunData = {
  run_id: nodeRoot.root_id,
  session_tree: { root_id: nodeRoot.root_id, nodes: [nodeRoot] },
  audit: auditReport,
  run_final: null,
  // ...
};
```

---

## Shared Patterns

### Tauri `invoke()` import
**Source:** `src/grid/sync.ts` line 1 + `src/App.tsx` line 1
**Apply to:** `orgStore.ts`, `decisionActions.ts`
```typescript
import { invoke } from '@tauri-apps/api/core';
```

### SolidJS reactive primitives import
**Source:** `src/App.tsx` lines 2–12
**Apply to:** `OrgViewShell.tsx`, `BlockedPanel.tsx`, `ReplayPanel.tsx`, `orgStore.ts`
```typescript
import { createSignal, createMemo, createEffect, onMount, onCleanup, Show, For } from 'solid-js';
```

### CSS variable tokens — no raw hex
**Source:** `src/styles/variant-b.css` + `src/components/modal/modal.css`
**Apply to:** `orgStyles.css` and all panel inline styles
- All background, foreground, border, and accent values via CSS vars only.
- Theme token source of truth is `variant-b.json` at `src/themes/bundled/variant-b.json`. Note: the active Voss Ignite theme (V11-UI-SPEC) uses `--focus: #ff5b1f` (orange), but `variant-b.json` uses `--focus: #5a7cff` (blue). V11-UI-SPEC governs the org panels — use the Voss Ignite values from the UI-SPEC token table, not variant-b.json values.

### `vi.mock('@tauri-apps/api/core', ...)` in every test file
**Source:** `src/grid/__tests__/a6-acceptance.test.tsx` line 12, `src/__tests__/App.test.tsx` line 123
**Apply to:** All `src/org/__tests__/*.test.{ts,tsx}` files
```typescript
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));
```

### Graceful degradation — never throw for missing optional data
**Source:** `lib.rs` `git_log` lines 948–951 (return empty on non-success), `get_theme_overrides` lines 63–77 (return empty on read error)
**Apply to:** `load_run` (return `run_final: null` when absent), `enumerate_runs` (return `[]` on missing dir)
```rust
// Pattern: match fs errors to empty/fallback rather than Err
Err(_) => return Vec::new(),
```

### `display: none` CSS hide (not `Show` unmount) for persistent components
**Source:** `src/App.tsx` lines 1183–1213
**Apply to:** `App.tsx` modification — GridRoot area must use CSS `display: none`, never `<Show>`, when Org view is active.
```typescript
style={{ display: orgViewOpen() ? 'none' : 'flex', flex: '1', ... }}
```

### Produce/proxy hand-clone for replay reducer outputs
**Source:** `src/grid/sync.ts` lines 14–16 (`JSON.parse(JSON.stringify(x))`)
**Apply to:** `replayReducer.ts` — all output objects must be plain, not Solid store proxies
```typescript
// Safe deep clone before passing to reducer:
const plainNodes = JSON.parse(JSON.stringify(runData()!.session_tree.nodes)) as SessionTreeNode[];
const frame = computeBoardAtStep(plainNodes, step());
```

### `onMount` + `requestAnimationFrame` for enter animation
**Source:** `src/components/modal/AgentLaunchModal.tsx` lines 94–97
**Apply to:** `OrgViewShell.tsx`, decision dialog in `BlockedPanel.tsx`
```typescript
const [visible, setVisible] = createSignal(false);
onMount(() => requestAnimationFrame(() => setVisible(true)));
```

### `modal.css` class naming + token usage
**Source:** `src/components/modal/modal.css`
**Apply to:** `orgStyles.css` — reuse `.modal-backdrop`, `.modal-panel`, `.modal-header`, `.modal-footer`, `.modal-btn-primary` for decision confirmation dialog. Org-specific additions use `.org-*` prefix.

---

## No Analog Found

All new files have analogs. The following have partial analogs only (planner should also use RESEARCH.md Code Examples):

| File | Role | Data Flow | Note |
|---|---|---|---|
| `src/org/panels/ReplayPanel.tsx` | component | event-driven | No existing step-scrubbing UI in codebase. Use `createSignal(step)` + Back/Forward buttons pattern from BudgetBar/StatusBar, plus `computeBoardAtStep` output rendered like BoardPanel. |
| `src/org/panels/SessionTreePanel.tsx` | component | CRUD | No existing tree-view component. Use `For` + recursive indentation pattern; `createSignal<string\|null>` for selected node ID. |
| `src/org/__tests__/fixtures/*.json` | test fixture | — | Author from RESEARCH.md Upstream JSON Contracts section. No real `.voss/sessions/` subdirs exist in current dev env (confirmed in RESEARCH.md Environment Availability). |

---

## Theme Note: Voss Ignite vs. variant-b.json

V11-UI-SPEC references "Voss Ignite" tokens. The active `variant-b.json` in the codebase uses different token values (e.g. `--focus: #5a7cff` blue vs. UI-SPEC `--focus: #ff5b1f` orange, `--bg-0: #0a0b0e` vs. UI-SPEC `#0b0a09`). The UI-SPEC values govern V11 panels. The org-panel CSS must declare or override these in `orgStyles.css` `:root` block if the active theme does not match. The planner should verify the active theme at implementation time and declare V11-specific overrides scoped to `.org-view-shell` if needed, rather than patching `:root` globally.

---

## Metadata

**Analog search scope:** `apps/voss-app/src/`, `apps/voss-app/src-tauri/src/`
**Files scanned:** `lib.rs`, `App.tsx`, `StatusBar.tsx`, `swarmTypes.ts`, `sync.ts`, `variant-b.css`, `variant-b.json`, `modal.css`, `AgentLaunchModal.tsx`, `ContextPanel.tsx`, `BudgetBar.test.tsx`, `a6-acceptance.test.tsx`, `App.test.tsx`, `vitest.config.ts`
**Pattern extraction date:** 2026-06-07
