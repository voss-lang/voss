# Phase A10: voss-app Status Bar — Pattern Map

**Mapped:** 2026-05-20
**Files analyzed:** 14 new/modified files
**Analogs found:** 12 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/status-bar/StatusBar.tsx` | component | request-response | `src/components/titlebar/Titlebar.tsx` | exact |
| `src/status-bar/LeftCluster.tsx` | component | request-response | `src/components/titlebar/Titlebar.tsx` | role-match |
| `src/status-bar/CenterCluster.tsx` | component | request-response | `src/components/titlebar/Titlebar.tsx` | role-match |
| `src/status-bar/RightCluster.tsx` | component | request-response | `src/components/titlebar/Titlebar.tsx` | role-match |
| `src/status-bar/Popover.tsx` | component | event-driven | `src/command-palette/CommandPalette.tsx` | partial |
| `src/status-bar/RecentProjectsPopover.tsx` | component | request-response | `src/project/projectStorage.ts` + CommandPalette rows | partial |
| `src/status-bar/PaneDetailPopover.tsx` | component | request-response | `src/components/titlebar/Titlebar.tsx` | role-match |
| `src/status-bar/NotificationsPopover.tsx` | component | event-driven | `src/command-palette/toast.tsx` | partial |
| `src/status-bar/notificationStore.ts` | store | event-driven | `src/command-palette/toast.tsx` | exact |
| `src/status-bar/gitWatcher.ts` | service | event-driven | `src/command-palette/keymapStorage.ts` | exact |
| `crates/voss-app-core/src/git.rs` | utility | file-I/O | `crates/voss-app-core/src/project.rs` | role-match |
| `apps/voss-app/src-tauri/src/lib.rs` (modified) | config | event-driven | `src-tauri/src/lib.rs` lines 256–399 | exact (self) |
| `apps/voss-app/src/App.tsx` (modified) | config | request-response | `src/App.tsx` lines 395–454 | exact (self) |
| `src/status-bar/__tests__/notificationStore.test.ts` | test | — | `src/command-palette/__tests__/keymapStorage.test.ts` | role-match |

---

## Pattern Assignments

### `src/status-bar/StatusBar.tsx` (component, request-response)

**Analog:** `src/components/titlebar/Titlebar.tsx`

**Imports pattern** (lines 1–6):
```typescript
import LeftCluster from './LeftCluster';
import CenterCluster from './CenterCluster';
import RightCluster from './RightCluster';
import type { PaneLeaf } from '../grid/tree';
import type { ProjectInfo } from '../project/projectStorage';
```

**Container pattern** (lines 24–44 of Titlebar.tsx):
```tsx
export default function Titlebar(props: TitlebarProps = {}) {
  return (
    <div
      style={{
        display: 'flex',
        'align-items': 'center',
        height: 'var(--titlebar-height)',   // ← StatusBar uses same 22px constant
        'flex-shrink': '0',
        background: 'var(--bg-0)',
        'border-bottom': '1px solid var(--border)',  // ← StatusBar uses border-top
        overflow: 'hidden',
      }}
    >
```

**A10 deviation from Titlebar:** StatusBar has `border-top` (not `border-bottom`) and no `data-tauri-drag-region`. StatusBar props pass `project`, `branch`, `getFocusedLeaf`, `getPaneCount`, `dispatchCommand`, `onOpenProject` down to the three cluster subcomponents.

---

### `src/status-bar/LeftCluster.tsx` / `CenterCluster.tsx` / `RightCluster.tsx` (component, request-response)

**Analog:** `src/components/titlebar/Titlebar.tsx` (inner flex items)

**Cluster button pattern** — copy from Titlebar's inner text div style (lines 54–68):
```tsx
<button
  style={{
    'flex-shrink': '0',
    color: 'var(--fg-1)',
    'font-size': '11px',
    'font-family': 'var(--font-mono)',
    'font-weight': '400',
    'align-self': 'stretch',
    display: 'flex',
    'align-items': 'center',
    padding: '0 8px',
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
  }}
  onClick={handleClick}
>
  {label()}
</button>
```

**Conditional display pattern** — copy Titlebar's `titleText()` derived signal (lines 26–29):
```tsx
const titleText = () =>
  props.projectName && props.projectName.length > 0
    ? props.projectName
    : 'Voss ADE';
```
StatusBar clusters use the same pattern:
```tsx
const leftLabel = () =>
  props.project ? `◆ ${props.project.name}` : '◆ no project · ⌘O to open';
const branchLabel = () =>
  props.branch ? ` · ⎇ ${props.branch}` : '';
```

**Accessibility pattern from UI-SPEC:** `role="toolbar"` on StatusBar, `aria-label` on each cluster button, `role="list"` on popover lists.

---

### `src/status-bar/Popover.tsx` (component, event-driven)

**Analog:** `src/command-palette/CommandPalette.tsx` — closest for click-outside + Esc dismiss pattern.

**No existing popover component** in the codebase. Modeled on:

**Click-outside + Esc pattern** (CommandPalette.tsx lines 85–107):
```tsx
const onKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    e.preventDefault();
    props.onDismiss();
  }
};

const onBackdropClick = (e: MouseEvent) => {
  if (panelRef && !panelRef.contains(e.target as Node)) {
    props.onDismiss();
  }
};
```

**onMount focus pattern** (CommandPalette.tsx line 109):
```tsx
onMount(() => {
  inputRef?.focus();
});
```

**Key A10 difference from CommandPalette:** Popover uses `<Portal>` from `solid-js/web` (NOT `Show` with a backdrop div) because StatusBar is adjacent to `overflow:hidden` GridRoot. The module-level `openPopoverId` signal enforces one-at-a-time (D-04).

**Popover shell structure:**
```tsx
import { Show, onMount, onCleanup, createSignal, type JSX } from 'solid-js';
import { Portal } from 'solid-js/web';

const [openPopoverId, setOpenPopoverId] = createSignal<string | null>(null);

export function isPopoverOpen(id: string) { return openPopoverId() === id; }
export function openPopover(id: string) { setOpenPopoverId(id); }
export function closePopover() { setOpenPopoverId(null); }

export default function Popover(props: {
  id: string;
  anchor: HTMLElement | undefined;
  width: number;
  maxHeight?: number;
  children: JSX.Element;
}) {
  let popoverEl: HTMLDivElement | undefined;

  const handleClickOutside = (e: MouseEvent) => {
    if (
      popoverEl && !popoverEl.contains(e.target as Node) &&
      !props.anchor?.contains(e.target as Node)
    ) closePopover();
  };
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') closePopover();
  };

  onMount(() => {
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEsc);
  });
  onCleanup(() => {
    document.removeEventListener('mousedown', handleClickOutside);
    document.removeEventListener('keydown', handleEsc);
  });

  return (
    <Show when={isPopoverOpen(props.id)}>
      <Portal>
        <div ref={popoverEl} style={{ /* position:fixed, bottom:22px, z-index:20 */ }}>
          {props.children}
        </div>
      </Portal>
    </Show>
  );
}
```

---

### `src/status-bar/RecentProjectsPopover.tsx` (component, request-response)

**Analog:** `src/project/projectStorage.ts` + CommandPalette row rendering

**Import pattern** (projectStorage.ts lines 1–2, 50–60):
```typescript
import { invoke } from '@tauri-apps/api/core';
// ...
export async function listRecents(): Promise<string[]> {
  return invoke<string[]>('load_recents');
}
export async function openProject(path: string): Promise<ProjectInfo> {
  return invoke<ProjectInfo>('open_project', { path });
}
```

**Row render pattern** — copy CommandPalette `<For each={rows()}>` pattern (CommandPalette.tsx lines 74–100 of render section). Each row: 32px height, `--fg-1` text, `◆` prefix in `--fg-2`, hover `--bg-2`, active project `--accent-blue` left border 2px, `aria-current="true"`.

**Empty state pattern** from CommandPalette: when rows array is empty, show a centered placeholder message in `--fg-3`.

---

### `src/status-bar/PaneDetailPopover.tsx` (component, request-response)

**Analog:** `src/components/titlebar/Titlebar.tsx` (read-only display chrome)

**Read-only field row pattern** — no existing exact match; follows Titlebar inline display:
```tsx
// Read all fields inside JSX render context — NOT destructured outside (Pitfall 5)
<div>
  <span style={{ color: 'var(--fg-2)', 'font-size': '11px', width: '52px', 'text-align': 'right' }}>
    cwd:
  </span>
  <span style={{ color: 'var(--fg-1)', 'font-size': '12px', overflow: 'hidden', 'text-overflow': 'ellipsis' }}>
    {props.getLeaf()?.cwd ?? ''}
  </span>
</div>
```

**No pane state:** When `props.getLeaf()` returns null, render `No pane focused` in `--fg-3`. `cmd:` row is hidden when no running command (Show component).

---

### `src/status-bar/NotificationsPopover.tsx` (component, event-driven)

**Analog:** `src/command-palette/toast.tsx` — `<For each={toasts()}>` list rendering pattern

**For-each list pattern** (toast.tsx lines 74–99):
```tsx
<For each={toasts()}>
  {(toast) => (
    <div
      data-testid="toast"
      data-severity={toast.severity}
      aria-live={toast.severity === 'error' ? 'assertive' : 'polite'}
      class="font-mono"
      style={{
        background: 'var(--bg-3)',
        border: '1px solid var(--border-bright)',
        'border-left': `3px solid ${RAIL_COLOR[toast.severity]}`,
        color: 'var(--fg-0)',
        'font-size': '12px',
      }}
    >
      {toast.message}
    </div>
  )}
</For>
```

**A10 difference:** Notifications use `role="list"` + `role="listitem"`, severity dot glyph (`●`) instead of colored border-left, relative timestamp below each message, and `aria-live="polite"` on the container. On popover open: call `markAllRead()` from notificationStore. "Clear all" button calls `clearAll()`.

**Severity color map** — copy toast.tsx `RAIL_COLOR` pattern:
```typescript
const SEVERITY_COLOR = {
  success: 'var(--accent-green)',
  warning: 'var(--accent-amber)',
  error:   'var(--accent-red)',
  info:    'var(--accent-cyan)',
};
```

---

### `src/status-bar/notificationStore.ts` (store, event-driven)

**Analog:** `src/command-palette/toast.tsx` — exact match for module-level signal store pattern

**Module-level store pattern** (toast.tsx lines 30–52):
```typescript
// Module-level — one per app (single import context)
let nextId = 1;
const [toasts, setToasts] = createSignal<ToastItem[]>([]);

export function showToast(severity: ToastSeverity, message: string): void {
  const id = nextId++;
  const item: ToastItem = { id, severity, message };
  setToasts((prev) => [...prev, item].slice(-MAX_VISIBLE));
  const delay = severity === 'error' ? DISMISS_MS_ERROR : DISMISS_MS_NORMAL;
  setTimeout(() => dismissToast(id), delay);
}

/** Test-only: clear all toasts. */
export function _resetToastsForTest(): void {
  setToasts([]);
}
```

**A10 variant** — use `createStore<NotificationEntry[]>` (not `createSignal`) for fine-grained row-level reactivity. Copy the `_resetToastsForTest` → `_resetNotificationsForTest` naming convention exactly.

**Schema** (from UI-SPEC):
```typescript
export interface NotificationEntry {
  id: number;
  severity: 'success' | 'warning' | 'error' | 'info';
  message: string;    // max 120 chars — slice in addNotification()
  source: string;     // 'pane-exit' | 'layout-save' | 'settings-reload' | 'update' | 'app-error'
  timestamp: number;  // Date.now() Unix ms
  read: boolean;
}
```

**addNotification must call showToast** (D-05 unified stream):
```typescript
import { showToast, type ToastSeverity } from '../command-palette/toast';

export function addNotification(severity, message, source): void {
  // ... append to store ...
  showToast(severity as ToastSeverity, message);  // D-05: dual consumer
}
```

**Persistence init pattern** — copy `installCloseSessionSave` pattern from `src/grid/sessionPersist.ts` lines 82–110:
```typescript
import { getCurrentWindow } from '@tauri-apps/api/window';

export async function initNotificationStore(): Promise<() => void> {
  // Load persisted notifications on mount
  const saved = await invoke<NotificationEntry[]>('load_notifications');
  setNotifications(saved.slice(-50));

  // Write on quit — mirrors installCloseSessionSave
  const unlisten = await getCurrentWindow().onCloseRequested(async (event) => {
    event.preventDefault();
    await invoke('save_notifications', { entries: [...notifications] });
    await getCurrentWindow().close();
  });
  return unlisten;
}
```

---

### `src/status-bar/gitWatcher.ts` (service, event-driven)

**Analog:** `src/command-palette/keymapStorage.ts` — exact match

**listen-before-invoke pattern** (keymapStorage.ts lines 83–106):
```typescript
export async function watchWorkspaceKeymap(
  workspacePath: string,
  knownCommandIds: string[],
  knownChords: string[],
  onUpdate: (payload: KeymapUpdatePayload) => void,
): Promise<UnlistenFn> {
  // CRITICAL: listen() BEFORE invoke() — event may fire immediately on Rust side
  const unlisten = await listen<KeymapUpdatePayload>('voss://keymap-updated', (event) => {
    onUpdate(event.payload);
  });

  try {
    const initial = await invoke<KeymapUpdatePayload>('watch_keymap_overrides', {
      workspacePath,
      knownCommandIds,
      knownChords,
    });
    onUpdate(initial);
  } catch (error) {
    unlisten();
    throw error;
  }

  return unlisten;
}
```

**A10 variant** — module-level `createSignal<string | null>` instead of callback:
```typescript
import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { createSignal } from 'solid-js';

const GIT_BRANCH_EVENT = 'voss://branch-changed';
const [branch, setBranch] = createSignal<string | null>(null);
export { branch };

let unlistenBranch: UnlistenFn | undefined;

export async function watchGitHead(projectPath: string): Promise<void> {
  unlistenBranch?.();
  // listen() first — CRITICAL ordering (Pitfall 6)
  const unlisten = await listen<string | null>(GIT_BRANCH_EVENT, (event) => {
    setBranch(event.payload);
  });
  try {
    const initial = await invoke<string | null>('watch_git_head', { projectPath });
    setBranch(initial);
    unlistenBranch = unlisten;
  } catch (e) {
    unlisten();
    setBranch(null);
    throw e;
  }
}

export function stopGitWatch(): void {
  unlistenBranch?.();
  unlistenBranch = undefined;
  setBranch(null);
}
```

---

### `crates/voss-app-core/src/git.rs` (utility, file-I/O)

**Analog:** `crates/voss-app-core/src/project.rs` lines 92–98 — git2 branch reading

**project.rs git2 pattern** (lines 92–98):
```rust
fn read_git_branch(path: &Path) -> Option<String> {
    let repo = git2::Repository::discover(path).ok()?;
    let head = repo.head().ok()?;
    head.shorthand().map(|s| s.to_string())
}
```

**A10 variant** — `git.rs` uses direct `.git/HEAD` file read (NOT git2) for the polling hot path:
```rust
pub fn read_branch_from_head(head_path: &Path) -> Option<String> {
    // Faster than git2::Repository::discover for the polling loop
    let content = std::fs::read_to_string(head_path).ok()?;
    let content = content.trim();
    if let Some(branch) = content.strip_prefix("ref: refs/heads/") {
        Some(branch.to_string())
    } else {
        None // detached HEAD — frontend renders "(detached)"
    }
}

pub fn git_head_path(project_path: &Path) -> Option<std::path::PathBuf> {
    let head = project_path.join(".git").join("HEAD");
    if head.exists() { Some(head) } else { None }
}
```

git2 (`read_git_branch` from project.rs) is still used for the initial `open_project` call — git.rs contains only the fast-path helpers for the watcher loop.

---

### `apps/voss-app/src-tauri/src/lib.rs` (modified, event-driven)

**Analog:** `src-tauri/src/lib.rs` lines 256–399 — self-reference (keymap watcher + invoke_handler)

**State struct pattern** (lib.rs lines 262–265):
```rust
#[derive(Default)]
struct KeymapWatchState {
    stops: Mutex<HashMap<PathBuf, Arc<AtomicBool>>>,
}
```

**File stamp pattern** (lib.rs lines 268–287):
```rust
#[derive(Debug, PartialEq)]
struct KeymapFileStamp {
    exists: bool,
    modified: Option<SystemTime>,
    len: Option<u64>,
}

fn keymap_file_stamp(path: &Path) -> KeymapFileStamp {
    match std::fs::metadata(path) {
        Ok(metadata) => KeymapFileStamp {
            exists: true,
            modified: metadata.modified().ok(),
            len: Some(metadata.len()),
        },
        Err(_) => KeymapFileStamp { exists: false, modified: None, len: None },
    }
}
```

**Watcher command pattern** (lib.rs lines 314–358):
```rust
#[tauri::command]
fn watch_keymap_overrides(
    app: tauri::AppHandle,
    state: tauri::State<'_, KeymapWatchState>,
    workspace_path: String,
    // ...args...
) -> Result<KeymapValidationResult, String> {
    let workspace = PathBuf::from(workspace_path);
    let stop = Arc::new(AtomicBool::new(false));
    let previous = state
        .stops.lock()
        .map_err(|_| "could not watch keymap settings".to_string())?
        .insert(workspace.clone(), Arc::clone(&stop));
    if let Some(previous) = previous {
        previous.store(true, Ordering::Relaxed);  // cancel previous watcher
    }

    std::thread::spawn(move || {
        let mut last = keymap_file_stamp(&keymap_path);
        while !stop.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(500));
            let next = keymap_file_stamp(&keymap_path);
            if next == last { continue; }
            last = next;
            std::thread::sleep(Duration::from_millis(75));  // settle delay
            if let Err(e) = app.emit(KEYMAP_UPDATED_EVENT, payload) {
                eprintln!("[voss-app] keymap update event failed: {e}");
            }
        }
    });

    Ok(initial)
}
```

**invoke_handler registration** (lib.rs lines 369–396):
```rust
.manage(KeymapWatchState::default())
.invoke_handler(tauri::generate_handler![
    // ... existing commands ...
    watch_keymap_overrides,  // ← add watch_git_head, stop_git_watch, save_notifications, load_notifications next to this
])
```

**A10 additions to lib.rs:**
1. `GitWatchState` struct (parallel to `KeymapWatchState`)
2. `watch_git_head(app, state, project_path)` command — returns `Result<Option<String>, String>` (initial branch or None)
3. `stop_git_watch(state, project_path)` command — sets AtomicBool stop flag
4. `save_notifications(entries)` / `load_notifications()` commands — copy `save_session`/`load_session` pattern (lines 232–242)
5. `.manage(GitWatchState::default())` in `run()`
6. Register all 4 new commands in `generate_handler!`

**Save/load command pattern** (lib.rs lines 232–242):
```rust
#[tauri::command]
fn save_session(workspace_path: String, session: SessionFile) -> Result<(), String> {
    session::save_session(Path::new(&workspace_path), &session)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn load_session(workspace_path: String) -> Result<Option<SessionFile>, String> {
    session::load_session(Path::new(&workspace_path))
        .map_err(|e| e.to_string())
}
```

**Path helper pattern** (lib.rs lines 26–38 — `settings_path()`):
```rust
fn notifications_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("notifications.json")
}
```

---

### `apps/voss-app/src/App.tsx` (modified, request-response)

**Analog:** `src/App.tsx` — self-reference

**Import addition pattern** (App.tsx lines 1–53 — import block):
```typescript
// Add alongside existing imports:
import StatusBar from './status-bar/StatusBar';
import { watchGitHead, stopGitWatch, branch } from './status-bar/gitWatcher';
import { initNotificationStore } from './status-bar/notificationStore';
```

**Component mounting position** (App.tsx lines 398–454):
```tsx
return (
  <div style={{ display: 'flex', 'flex-direction': 'column', height: '100vh', ... }}>
    <Titlebar ... />
    <Show when={showGrid()} fallback={<SetupWindow ... />}>
      <div style={{ flex: '1', 'min-height': '0', background: 'var(--bg-0)' }}>
        <GridRoot ... controllerRef={(c) => { gridController = c; ... }} ... />
      </div>
    </Show>

    {/* A10: status bar — below GridRoot, above ToastStack */}
    <StatusBar
      project={project()}
      branch={branch()}
      getFocusedLeaf={() => /* gridController?.getFocusedLeaf() */ null}
      getPaneCount={() => /* gridController?.getPaneCount() */ 0}
      onOpenProject={handleOpenFolder}
      dispatchCommand={dispatchCommandId}
    />

    <ToastStack />           {/* ← stays last, z-index 200 */}
    {/* ... CommandPalette Show ... */}
  </div>
);
```

**onMount init pattern** (App.tsx lines 358–395 — existing onMount block):
```typescript
onMount(() => {
  // ... existing setup ...
  void initNotificationStore();        // A10: load notifications.json
  void watchGitHead(project()?.path ?? '');  // A10: start git watcher if project open
});
```

**GridController extension** — add to existing GridController type (GridRoot.tsx lines 94–111):
```typescript
export type GridController = {
  // ... existing methods ...
  getFocusedLeaf: () => PaneLeaf | null;   // A10: new
  getPaneCount: () => number;              // A10: new
};
```

---

### `src/status-bar/__tests__/notificationStore.test.ts` (test)

**Analog:** `src/command-palette/__tests__/keymapStorage.test.ts`

**Tauri mock pattern** (keymapStorage.test.ts lines 1–8):
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
  listen: vi.fn(() => Promise.resolve(() => {})),
}));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('@tauri-apps/api/event', () => ({ listen: h.listen }));
```

**beforeEach reset pattern** — copy `_resetToastsForTest` → `_resetNotificationsForTest` call:
```typescript
beforeEach(() => {
  h.invoke.mockReset();
  _resetNotificationsForTest();  // must call before each test — module-level store persists
});
```

---

## Shared Patterns

### Variant B Token-Only Styling
**Source:** `src/components/titlebar/Titlebar.tsx` (entire file — all styles via `var(--token)`)
**Apply to:** All A10 component files — StatusBar, cluster files, Popover, popover content files.
```tsx
// Correct:
style={{ background: 'var(--bg-0)', color: 'var(--fg-1)', 'font-size': '11px' }}
// Never:
style={{ background: '#0a0b0e', color: '#aab0c0' }}
```
No inline hex values. No border-radius. Font always `var(--font-mono)`.

### Module-Level Signal Store
**Source:** `src/command-palette/toast.tsx` lines 30–52
**Apply to:** `notificationStore.ts`, `gitWatcher.ts` (module-level `createSignal<string | null>`)
```typescript
// Pattern: module-level signal, exported getter, no React context needed
let nextId = 1;
const [toasts, setToasts] = createSignal<ToastItem[]>([]);
export function _resetToastsForTest(): void { setToasts([]); }
```

### Tauri invoke() Bridge
**Source:** `src/project/projectStorage.ts` lines 50–60, `src/command-palette/keymapStorage.ts` lines 46–75
**Apply to:** `gitWatcher.ts`, `notificationStore.ts` (persistence calls)
```typescript
import { invoke } from '@tauri-apps/api/core';
export async function openProject(path: string): Promise<ProjectInfo> {
  return invoke<ProjectInfo>('open_project', { path });
}
```

### listen() Before invoke() — Event Bridge Ordering
**Source:** `src/command-palette/keymapStorage.ts` lines 88–105
**Apply to:** `gitWatcher.ts` `watchGitHead()` function
```typescript
// CRITICAL: register listener BEFORE starting the Rust watcher
const unlisten = await listen<T>(EVENT_NAME, handler);
try {
  const initial = await invoke<T>('start_watcher_command', { ... });
  onUpdate(initial);
} catch (error) {
  unlisten();
  throw error;
}
```

### Quit Hook (onCloseRequested)
**Source:** `src/grid/sessionPersist.ts` lines 82–110
**Apply to:** `notificationStore.ts` `initNotificationStore()` — write notifications.json on quit
```typescript
import { getCurrentWindow } from '@tauri-apps/api/window';
const unlisten = await getCurrentWindow().onCloseRequested(async (event) => {
  event.preventDefault();
  // ... save ...
  await getCurrentWindow().close();
});
```

### Rust Polling Watcher with AtomicBool
**Source:** `src-tauri/src/lib.rs` lines 262–358 (KeymapWatchState + watch_keymap_overrides)
**Apply to:** New `GitWatchState` struct + `watch_git_head` command in `lib.rs`
```rust
// Verbatim copy with three changes:
// 1. Struct name: GitWatchState
// 2. Watched path: project_path/.git/HEAD  
// 3. Payload: Option<String> (branch name or None) instead of KeymapValidationResult
// 4. Poll interval: 200ms (not 500ms)
// 5. Settle delay: 50ms (not 75ms)
```

### ~/.config/voss-app/ Path Construction
**Source:** `src-tauri/src/lib.rs` lines 26–38 (`settings_path()`)
**Apply to:** `notifications_path()` helper in `lib.rs`
```rust
fn settings_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("settings.json")
}
```

### Solid spread clone (not structuredClone) for Proxy-safe data extraction
**Source:** Project memory `voss-app-solid-produce-no-structuredclone`
**Apply to:** `PaneDetailPopover.tsx` when reading PaneLeaf fields
```typescript
// CORRECT — read fields inside JSX reactive context
{props.getLeaf()?.cwd}

// WRONG — structuredClone throws DATA_CLONE_ERR on Solid store proxies
const leaf = structuredClone(props.getLeaf());
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/status-bar/Popover.tsx` | component | event-driven | No popover/tooltip component exists in the codebase; composed from CommandPalette patterns + Portal |

---

## Metadata

**Analog search scope:** `apps/voss-app/src/`, `apps/voss-app/src-tauri/src/`, `crates/voss-app-core/src/`
**Files scanned:** 14 (Titlebar.tsx, toast.tsx, keymapStorage.ts, CommandPalette.tsx, lib.rs, App.tsx, GridRoot.tsx, tree.ts, project.rs, projectStorage.ts, sessionPersist.ts, keymapStorage.test.ts + 2 others)
**Pattern extraction date:** 2026-05-20
