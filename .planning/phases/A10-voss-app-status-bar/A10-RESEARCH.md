# Phase A10: voss-app Status Bar - Research

**Researched:** 2026-05-20
**Domain:** Tauri v2 Rust file watcher, Solid.js reactive stores, popover positioning, notification persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Click-outside + Esc dismissal. One popover open at a time.
- D-02: LEFT popover = recent projects list (reuses A5 recents). Click entry = switch project.
- D-03: CENTER popover = pane detail card (read-only: cwd, shell, version, PID, index, running command).
- D-04: One generic `<Popover>` component, reused by all three clusters.
- D-05: Unified event stream — every notification event → both toast AND notification store.
- D-06: Opening bell popover clears badge; all entries marked read.
- D-07: Global `notifications.json` at `~/.config/voss-app/`, last 50 entries, written on quit.
- D-08: L1.8.2 event sources as-is (5 sources). No additions in L1.
- D-09: Branch name only. No dirty/ahead-behind indicator.
- D-10: Rust file watcher on `.git/HEAD`. On change, re-read branch, push `branch-changed` Tauri event to frontend. 200ms debounce.
- D-11: Hide branch entirely when no git repo.

### Claude's Discretion
- Popover visual design (within Variant B tokens).
- Popover positioning logic (above bar, edge-clamped to viewport).
- Notification store schema shape (defined in A10-UI-SPEC.md).
- Bell badge visual (dot vs count number) — planner picks within Variant B.
- Git watcher debounce/rate-limiting strategy — planner picks, bounded by 500ms latency.
- Settings cog — triggers existing `open-settings` registry command (A9).
- Pane count display format.
- Status bar left/center/right flex layout proportions.

### Deferred Ideas (OUT OF SCOPE)
- None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BAR-01 | Left cluster: project name (click → recents), git branch (read-only) | A5 `listRecents()` exists; git branch already read at `open_project` time; file watcher pattern established |
| BAR-02 | Center cluster: focused pane cwd · shell · pid | GridStore has `PaneLeaf.cwd`/`shell`; pid requires new pane-info signal or Tauri command |
| BAR-03 | Right cluster: pane count, notifications bell + badge, settings cog | `collectLeaves(store.root).length` for count; notification store is new module; cog dispatches registry command |
| BAR-04 | Click clusters → popovers with full detail | Generic `<Popover>` component; upward positioning; one-at-a-time via module-level signal |
| BAR-05 | Status bar height fixed 22px, single dense line, mono font | Mirrors Titlebar pattern exactly |
| BAR-06 | Updates on every focus change + every git ref change (file watcher) | Polling watcher pattern in lib.rs established; 200ms debounce; `listen()` on frontend |
| BAR-07 | Notifications bell shows last 50 events (UI-SPEC says 50; ROADMAP says 100 — UI-SPEC wins), clearable | Module-level Solid store; write-on-quit via `before-quit` event |
| BAR-08 | Project-less mode: left cluster shows "no project · ⌘O to open" | `project()` signal already exists in App.tsx |
</phase_requirements>

---

## Summary

Phase A10 builds a 22px status bar strip at the bottom of the flex column in App.tsx, below GridRoot. The bar has three clusters (left: project+branch, center: focused pane info, right: pane count+bell+cog), each with a click-to-popover. This is a pure frontend Solid.js composition problem plus one new Rust file-watcher seam for git branch tracking.

The key technical insight is that the project already has all the required building blocks: the git2 crate (already used in `project.rs` for `read_git_branch`), the polling-based file-watcher pattern (established in `watch_keymap_overrides`), the `listen()`/`invoke()` event bridge pattern (established in `keymapStorage.ts`), and the module-level Solid signal pattern for app-wide stores (established in `toast.tsx`). A10 is composition, not invention.

The one genuinely new piece is the git HEAD watcher: a polling thread in lib.rs that watches `.git/HEAD` metadata, reads the branch on change via `git2`, and emits `voss://branch-changed` to the frontend. This mirrors `watch_keymap_overrides` exactly.

**Primary recommendation:** Follow the keymap watcher pattern for Rust file watching, the toast.tsx pattern for the notification store, and the Titlebar component pattern for the StatusBar component. No new crates needed — git2, dirs, serde_json are all already present.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Git branch display | Rust (voss-app-core + lib.rs) | Frontend (signal consumer) | git2 already lives in Rust; HEAD parsing is a filesystem op |
| Git HEAD file watching | Rust (lib.rs polling thread) | — | Established polling pattern; no new crate needed |
| Branch-changed event delivery | Tauri event bridge | — | `app.emit()` → `listen()` pattern already established |
| Pane count | Frontend (GridStore reactive) | — | `collectLeaves(store.root).length` is a pure store derivation |
| Focused pane info | Frontend (GridStore reactive) | — | `store.focusedId` + `findLeaf()` gives cwd/shell/index |
| Pane PID | Rust (optional) or Frontend signal | — | PTY session id is in PaneLeaf; PID requires a new `get_pty_pid` command or can be omitted (see Open Questions) |
| Notification store | Frontend module-level | Rust (write-on-quit) | Solid signal store at module scope; persistence via save-on-quit Tauri command |
| Notifications persistence | Rust (lib.rs) | Frontend (trigger) | `~/.config/voss-app/notifications.json` write follows session.json pattern |
| Popover positioning | Frontend (DOM calc) | — | Pure JS getBoundingClientRect + viewport clamp |
| App.tsx integration | Frontend (layout change) | — | StatusBar renders below GridRoot in existing flex column |
| Settings cog dispatch | Frontend | — | Dispatches existing `open-settings` registry command |

---

## Standard Stack

### Core (all already in the project — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| solid-js | 1.9.13 | Reactive UI, signals, stores | Project baseline [VERIFIED: package.json] |
| @tauri-apps/api | 2.11.0 | invoke(), listen(), event bridge | Project baseline [VERIFIED: package.json] |
| git2 | 0.20.4 | Read git HEAD, parse branch name | Already used in voss-app-core project.rs [VERIFIED: Cargo.lock] |
| serde / serde_json | workspace | JSON serialization for notifications.json | Already used throughout [VERIFIED: Cargo.toml] |
| dirs | workspace | `~/.config/voss-app/` path construction | Already used in lib.rs and session.rs [VERIFIED: Cargo.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| solid-js/store | (included) | `createStore` for notification list | Use for the notification array (supports fine-grained updates) |
| std::thread + AtomicBool | (std) | Polling file watcher | Use the keymap watcher pattern verbatim |
| std::time::Duration + SystemTime | (std) | File stamp comparison for watcher | Use the `KeymapFileStamp` pattern verbatim |

### No New Dependencies
A10 adds zero new npm packages and zero new Rust crates. All required functionality is available from existing workspace dependencies.

**Installation:** none required.

---

## Package Legitimacy Audit

> No new packages are introduced in Phase A10. All libraries used are pre-existing project dependencies.

| Package | Registry | Disposition |
|---------|----------|-------------|
| solid-js 1.9.13 | npm | Already installed — Approved |
| @tauri-apps/api 2.11.0 | npm | Already installed — Approved |
| git2 0.20.4 | crates.io | Already installed — Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
App.tsx (flex column, height:100vh)
  │
  ├── Titlebar (22px, flex-shrink:0)
  │
  ├── Show(when=showGrid)
  │     └── GridRoot (flex:1, min-height:0)
  │           └── [emits pane tree mutations to store]
  │
  └── StatusBar (22px, flex-shrink:0)          ← A10 NEW
        ├── LeftCluster
        │     ├── reads: project() signal from App.tsx
        │     ├── reads: branch signal from gitWatcher module
        │     └── click → Popover(RecentProjectsPopover)
        ├── CenterCluster
        │     ├── reads: focusedLeaf derived from GridStore signal
        │     └── click → Popover(PaneDetailPopover)
        └── RightCluster
              ├── reads: paneCount derived from GridStore signal
              ├── reads: notifications store (unreadCount)
              ├── bell click → Popover(NotificationsPopover)
              └── cog click → dispatchCommand('open-settings')

Tauri Rust (lib.rs)
  ├── git_watcher thread (polls .git/HEAD every 200ms)
  │     └── on change → app.emit("voss://branch-changed", branchName)
  ├── get_git_branch command (one-shot read on project open)
  ├── save_notifications command (called on before-quit)
  └── load_notifications command (called on app mount)

Frontend event bridge (gitWatcher.ts)
  ├── invoke('watch_git_head', {projectPath}) on project open
  ├── listen('voss://branch-changed', handler)
  └── invoke('stop_git_watch', {projectPath}) on project close
```

### Recommended Project Structure
```
apps/voss-app/src/status-bar/       ← canonical per CONCEPT.md §4
  StatusBar.tsx                     ← root, composes three clusters
  LeftCluster.tsx                   ← project + branch, left popover trigger
  CenterCluster.tsx                 ← focused pane info, center popover trigger
  RightCluster.tsx                  ← pane count + bell + cog
  Popover.tsx                       ← generic popover (D-04)
  RecentProjectsPopover.tsx         ← left popover content
  PaneDetailPopover.tsx             ← center popover content
  NotificationsPopover.tsx          ← bell popover content
  notificationStore.ts              ← module-level Solid store (D-05)
  gitWatcher.ts                     ← Tauri event bridge for branch
  __tests__/
    notificationStore.test.ts
    gitWatcher.test.ts
    StatusBar.test.tsx
    a10-acceptance.test.tsx
```

---

### Pattern 1: Polling File Watcher in Rust (established — copy keymap pattern)

**What:** A background thread polls `.git/HEAD` file metadata (mtime + size) every N ms. On change, reads the file contents, parses the branch name, and emits a Tauri event to the frontend.

**When to use:** Any file the user expects "near-instant" updates on, where a polling interval of 200ms is acceptable. D-10 specifies 200ms debounce; 500ms poll interval + 200ms settle delay achieves < 500ms total latency (matches BAR-06).

**Source:** `apps/voss-app/src-tauri/src/lib.rs` — `watch_keymap_overrides` function (lines 315-358) [VERIFIED: codebase read]

```rust
// Pattern: established in watch_keymap_overrides. Git HEAD variant:
const GIT_BRANCH_CHANGED_EVENT: &str = "voss://branch-changed";

#[derive(Default)]
struct GitWatchState {
    stops: Mutex<HashMap<PathBuf, Arc<AtomicBool>>>,
}

#[tauri::command]
fn watch_git_head(
    app: tauri::AppHandle,
    state: tauri::State<'_, GitWatchState>,
    project_path: String,
) -> Result<Option<String>, String> {
    let project = PathBuf::from(&project_path);
    let head_path = project.join(".git").join("HEAD");

    // Return initial branch name (None = not a git repo)
    let initial = read_branch_from_head(&head_path).ok();

    let stop = Arc::new(AtomicBool::new(false));
    // Cancel any previous watcher for this project
    if let Some(prev) = state.stops.lock()
        .map_err(|_| "lock error")?
        .insert(project.clone(), Arc::clone(&stop))
    {
        prev.store(true, Ordering::Relaxed);
    }

    std::thread::spawn(move || {
        let mut last = file_stamp(&head_path);
        while !stop.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(200));
            let next = file_stamp(&head_path);
            if next == last { continue; }
            last = next;
            // Settle delay: avoid thrash during rebase operations
            std::thread::sleep(Duration::from_millis(50));
            let branch = read_branch_from_head(&head_path)
                .ok()
                .flatten();
            if let Err(e) = app.emit(GIT_BRANCH_CHANGED_EVENT, branch) {
                eprintln!("[voss-app] branch-changed event failed: {e}");
            }
        }
    });

    Ok(initial)
}

fn read_branch_from_head(head_path: &Path) -> Result<Option<String>, String> {
    // Read .git/HEAD directly (faster than git2 for this hot path)
    // Format: "ref: refs/heads/main\n" or SHA for detached HEAD
    let content = std::fs::read_to_string(head_path)
        .map_err(|e| e.to_string())?;
    let content = content.trim();
    if let Some(branch) = content.strip_prefix("ref: refs/heads/") {
        Ok(Some(branch.to_string()))
    } else if content.starts_with("ref: refs/") {
        // Non-standard ref (e.g. during rebase)
        Ok(Some(content.to_string()))
    } else {
        // Detached HEAD: 40-char SHA
        Ok(None) // rendered as "(detached)" in UI
    }
}
```

**Key insight:** Reading `.git/HEAD` directly (not via git2) is both faster and simpler for this hot path. git2 is still needed for the initial `open_project` call (which already uses it). The file watcher only needs the cheap `read_to_string` path.

**Detached HEAD:** When HEAD contains a SHA (not a `ref:` prefix), the branch is `None`. The frontend renders `(detached)` per UI-SPEC. [ASSUMED]

---

### Pattern 2: Module-Level Solid Store for Notifications (established — mirrors toast.tsx)

**What:** Module-level `createStore` (or `createSignal` for simple arrays) at the top of `notificationStore.ts`. Exported `addNotification()` function mutates the store and calls `showToast()`. Components import the store getter directly.

**Source:** `apps/voss-app/src/command-palette/toast.tsx` — `createSignal<ToastItem[]>` at module scope. [VERIFIED: codebase read]

```typescript
// notificationStore.ts
import { createStore } from 'solid-js/store';
import { showToast, type ToastSeverity } from '../command-palette/toast';

export interface NotificationEntry {
  id: number;
  severity: 'success' | 'warning' | 'error' | 'info';
  message: string;          // max 120 chars
  source: string;           // 'pane-exit' | 'layout-save' | 'settings-reload' | 'update' | 'app-error'
  timestamp: number;        // Date.now() Unix ms
  read: boolean;
}

const MAX_NOTIFICATIONS = 50;
let nextId = 1;

// Module-level store — one per app (same pattern as toast.tsx createSignal)
const [notifications, setNotifications] = createStore<NotificationEntry[]>([]);

export { notifications };  // read-only export

export function addNotification(
  severity: NotificationEntry['severity'],
  message: string,
  source: string,
): void {
  const entry: NotificationEntry = {
    id: nextId++,
    severity,
    message: message.slice(0, 120),
    source,
    timestamp: Date.now(),
    read: false,
  };
  setNotifications((prev) => [...prev, entry].slice(-MAX_NOTIFICATIONS));
  // D-05: unified stream — also flash as toast
  showToast(severity as ToastSeverity, message);
}

export function markAllRead(): void {
  setNotifications((entries) =>
    entries.map((e) => ({ ...e, read: true }))
  );
}

export function clearAll(): void {
  setNotifications([]);
}

export function unreadCount(): number {
  return notifications.filter((e) => !e.read).length;
}

/** Test-only reset */
export function _resetNotificationsForTest(): void {
  setNotifications([]);
  nextId = 1;
}
```

**Note on store vs signal:** `createStore` is preferred over `createSignal<NotificationEntry[]>` because fine-grained reactivity lets individual row `read` updates avoid re-rendering the entire list. This is important for the notifications popover with up to 50 rows.

---

### Pattern 3: Generic Popover Component (new — no existing analog)

**What:** A Solid component that renders a `<div>` positioned above its anchor element, with click-outside and Esc-key dismissal. One-at-a-time enforced via a module-level `openPopoverId` signal.

**Source:** No existing popover in the codebase. Modeled after the CommandPalette click-outside dismissal pattern. [ASSUMED from A7 CommandPalette pattern]

```typescript
// Popover.tsx — simplified structure
import { Show, onMount, onCleanup, createSignal, type JSX } from 'solid-js';
import { Portal } from 'solid-js/web';

// Module-level: only one popover open at a time (D-01/D-04)
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

  const position = () => {
    if (!props.anchor) return { bottom: '22px', left: '0px' };
    const rect = props.anchor.getBoundingClientRect();
    const vw = window.innerWidth;
    let left = rect.left;
    // Edge-clamp: shift left if popover would overflow right edge
    const effectiveWidth = props.width;
    if (left + effectiveWidth > vw - 16) {
      left = vw - effectiveWidth - 16;
    }
    if (left < 16) left = 16;
    return {
      position: 'fixed' as const,
      bottom: '22px',   // status bar height — opens upward
      left: `${left}px`,
      width: `${props.width}px`,
      'z-index': 20,
    };
  };

  const handleClickOutside = (e: MouseEvent) => {
    if (
      popoverEl &&
      !popoverEl.contains(e.target as Node) &&
      !props.anchor?.contains(e.target as Node)
    ) {
      closePopover();
    }
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
        <div ref={popoverEl} style={position()}>
          {props.children}
        </div>
      </Portal>
    </Show>
  );
}
```

**Portal rationale:** Using `solid-js/web` `<Portal>` ensures the popover renders at `document.body` level, escaping any `overflow:hidden` ancestor (GridRoot uses `overflow:hidden`). Without Portal, popovers inside the grid would be clipped. [VERIFIED: GridRoot.tsx uses `overflow:hidden` — codebase read]

**Edge-clamp:** `getBoundingClientRect()` gives the anchor's position in viewport coordinates. Subtracting `props.width` from `window.innerWidth` gives the maximum safe left offset. This is pure DOM math, no extra libraries needed. [ASSUMED]

---

### Pattern 4: Focused Pane Signal from GridRoot

**What:** GridRoot currently owns the `store` (GridStore) internally and does not expose a reactive pane-info signal externally. StatusBar needs the focused pane's cwd, shell, and index to populate the center cluster.

**Options analyzed:**
1. **GridController extension** — Add `getFocusedLeaf` to `GridController` (already in App.tsx). Simple snap: `() => findLeaf(store.root, store.focusedId)`.
2. **Module-level store** — Lift a `focusedPaneInfo` signal to a module-level store, updated by GridRoot on focus change.
3. **Props drilling** — Pass `focusedLeaf` down from App.tsx to StatusBar as a prop, derived from GridController snapshot().

**Recommended approach (Option 1 + Props):** Extend `GridController` with a reactive getter `getFocusedLeaf: () => PaneLeaf | null`, backed by a computed memo inside GridRoot. App.tsx holds `gridController` ref and passes a derived accessor to StatusBar as a prop. This is the minimal-change path that keeps GridRoot as the single owner of pane state. [ASSUMED — planner must decide the signal threading path]

**Code pattern:**
```typescript
// In GridRoot.tsx, expose via GridController:
const focusedLeaf = createMemo(() =>
  findLeaf(store.root, store.focusedId)
);
// In GridController object:
getFocusedLeaf: () => focusedLeaf(),
getPaneCount: () => collectLeaves(store.root).length,
```

**PID**: `PaneLeaf` has no `pid` field. Getting the actual process ID requires either (a) a new Tauri command `get_pty_pid(session_id)` using `portable-pty` `Child::process_id()`, or (b) omitting PID in the pane detail card. The UI-SPEC lists `pid` as a field. See Open Questions.

---

### Pattern 5: Notifications Persistence on Quit

**What:** On app quit, write `notifications.json` to `~/.config/voss-app/`. On app mount, load it. Follows the session.json write-on-quit pattern (A6).

**Source:** `apps/voss-app/src-tauri/src/lib.rs` — `save_session`/`load_session` commands and the session persistence pattern in `sessionPersist.ts`. [VERIFIED: codebase read]

```typescript
// Frontend: call on before-quit (same as A6 installCloseSessionSave pattern)
// Rust: thin command wrappers in lib.rs
```

The Tauri `before-quit` event (or `CloseRequested` window event) is the right hook — same as A6. The frontend calls `invoke('save_notifications', { entries })` in the close handler.

---

### Pattern 6: App.tsx Integration

**What:** Add `<StatusBar>` to the flex column in App.tsx, below the GridRoot `<Show>` block, above `<ToastStack>`.

**Source:** `apps/voss-app/src/App.tsx` lines 398–468. [VERIFIED: codebase read]

```tsx
// App.tsx — insertion point (after the GridRoot Show block, before ToastStack)
<StatusBar
  project={project()}
  getBranch={branch}        // signal from gitWatcher module
  getFocusedLeaf={...}      // from GridController or derived memo
  getPaneCount={...}        // from GridController
  onOpenProject={handleOpenFolder}
  dispatchCommand={dispatchCommandId}
/>
```

The project signal (`project()`) already exists in App.tsx as `createSignal<ProjectInfo | null>`. The StatusBar reads it directly (prop or shared signal — planner decides prop threading vs module signal).

**Layout contract:** StatusBar is `flex-shrink: 0` and 22px height, same as Titlebar. The GridRoot wrapper div (currently `flex: 1; min-height: 0`) provides all remaining space. No layout changes needed to other components.

---

### Anti-Patterns to Avoid

- **Portal-less popover inside overflow:hidden container:** The StatusBar sits adjacent to GridRoot but the grid uses `overflow:hidden`. If `<Popover>` is a direct child of StatusBar without Portal, it cannot render above GridRoot. Always use `<Portal>` for the popover overlay div.
- **structuredClone on Solid store state:** As documented in memory `voss-app-solid-produce-no-structuredclone`, Solid produce drafts are Proxies and `structuredClone` throws `DATA_CLONE_ERR`. When reading pane leaf data for the popover, use `{ ...leaf }` spread clone, not structuredClone.
- **git2 in the hot-path watcher loop:** `git2::Repository::discover` + `repo.head()` has non-trivial overhead. Use direct `.git/HEAD` file reading in the polling loop (the fast path). git2 is appropriate only for the initial `open_project` call.
- **Tight polling interval:** The keymap watcher uses 500ms sleep. The git HEAD watcher should use 200ms (still well within the 500ms BAR-06 requirement) but avoid going below 100ms to prevent excessive CPU burn.
- **Blocking the main thread with file watch state:** All watcher threads must use `Arc<AtomicBool>` stop flags and `std::thread::sleep` (non-blocking). Never use `tokio::spawn` for file polling (the Tauri builder does not await cleanup of background tokio tasks on exit).
- **Missing stop_git_watch on project close:** If the user opens a different project, the previous watcher must be cancelled. The `GitWatchState` HashMap (keyed by project path) handles this — inserting a new stop signal cancels the previous one (same pattern as keymap watcher).
- **Notification store singleton pollution in tests:** The module-level store persists across test runs. Export `_resetNotificationsForTest()` and call it in `beforeEach`. See toast.tsx `_resetToastsForTest()` precedent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git HEAD parsing | Custom regex for `.git/HEAD` | `read_branch_from_head()` with simple `strip_prefix("ref: refs/heads/")` | The format is well-defined and simple; strip_prefix is sufficient |
| Popover click-outside | Custom event capture system | `document.addEventListener('mousedown', ...)` on mount/cleanup | This is a one-time DOM subscription; no library needed |
| Notification timestamp formatting | External date library | Inline `Date.now()` arithmetic | The format is simple: "just now" < 1min, "{N} minutes ago" < 1hr, "{N} hours ago" < 24hr, ISO date otherwise |
| File stamp comparison | `notify` crate | `std::fs::metadata` mtime + len comparison | Already proven in keymap watcher; `notify` would be an unnecessary new dep |
| Popover animation | CSS transition library | None — instant appear per UI-SPEC | Variant B has no animations; reduced motion is the default behavior |
| Portal rendering | Custom teleport implementation | `<Portal>` from `solid-js/web` | Already available in solid-js 1.9.13 [VERIFIED: package.json] |

**Key insight:** Every "hard" problem in this phase has already been solved by a prior phase. The planner should recognize A10 as a composition phase, not a research-heavy implementation phase.

---

## Common Pitfalls

### Pitfall 1: .git/HEAD Absent in Non-Git Projects
**What goes wrong:** The watcher thread tries to poll a path that doesn't exist. `std::fs::metadata` returns `Err`, but the thread keeps looping.
**Why it happens:** Watcher is started unconditionally on project open.
**How to avoid:** At `watch_git_head` call time, check if `.git/HEAD` exists. If not, return `Ok(None)` immediately without spawning a thread. D-11 says hide branch when no git repo — this is the Rust-side guard.
**Warning signs:** Thread spinning in the watcher with no events; CPU usage ticking up on non-git projects.

### Pitfall 2: Multiple Watchers on Re-Open
**What goes wrong:** User opens project A, then opens project B (same path). Two threads poll the same file.
**Why it happens:** `watch_git_head` is called twice without cancelling the first.
**How to avoid:** The `GitWatchState` HashMap pattern ensures the old stop flag is set when a new watcher is registered for the same key. This is a verbatim copy of the keymap watcher logic.

### Pitfall 3: `before-quit` Race on notifications.json Write
**What goes wrong:** The quit save of `notifications.json` races with an in-flight `addNotification` call.
**Why it happens:** The notification store is pure frontend JavaScript; there's no Mutex. If a notification arrives as the save is executing, it may not be included.
**How to avoid:** Accept this minor race — the window is tiny (< 1ms), and notifications are not critical data. Do not add a Mutex or complex synchronization. The CONTEXT D-07 "written on quit" policy accepts eventual consistency. Same policy as A6 session save.

### Pitfall 4: Popover Positioning When Status Bar Is Not at Bottom of Viewport
**What goes wrong:** On smaller windows or if the flex layout changes, `bottom: 22px` fixed positioning is correct only when the status bar is at the exact viewport bottom.
**Why it happens:** The status bar uses `flex-shrink: 0` in a `height: 100vh` column, so it IS always at the viewport bottom. But if this assumption breaks, the popover appears floating in mid-screen.
**How to avoid:** Assert during development that the status bar element is always `window.innerHeight - 22` pixels from top. The positioning is intentionally simple (fixed `bottom: 22px`) and only works because the status bar is the last flex item.

### Pitfall 5: Solid.js Proxy in Popover Content
**What goes wrong:** Passing a raw Solid store reactive leaf object into the popover `children` — if the popover closes and re-opens, the stale proxy reference causes TypeErrors.
**Why it happens:** Solid's store state objects are Proxy traps that are only valid inside reactive contexts (component render trees).
**How to avoid:** In `PaneDetailPopover`, read all fields from the leaf signal _inside_ the component's JSX render (not memoized outside). Use `props.getLeaf()?.cwd` directly in JSX rather than destructuring outside the reactive context.

### Pitfall 6: `listen()` Registration Before `invoke('watch_git_head')`
**What goes wrong:** The Tauri event listener for `voss://branch-changed` must be registered BEFORE the Rust watcher starts, or the first emission may be missed.
**Why it happens:** `app.emit()` on the Rust side fires as soon as the watcher detects a change. If the frontend hasn't called `listen()` yet, the event is lost.
**How to avoid:** In `gitWatcher.ts`, follow the exact pattern from `keymapStorage.ts` lines 83-106: `await listen(...)` first, then `await invoke('watch_git_head', ...)`. This is the established pattern.

---

## Code Examples

### Reading Branch from .git/HEAD (Rust — fast path)
```rust
// Source: codebase analysis of project.rs read_git_branch + HEAD file format
fn read_branch_from_head(head_path: &Path) -> Option<String> {
    let content = std::fs::read_to_string(head_path).ok()?;
    let content = content.trim();
    if let Some(branch) = content.strip_prefix("ref: refs/heads/") {
        Some(branch.to_string())
    } else {
        None // detached HEAD
    }
}
```

### Frontend Git Watcher Bridge (mirrors keymapStorage.ts)
```typescript
// Source: keymapStorage.ts watchWorkspaceKeymap pattern [VERIFIED: codebase read]
import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { createSignal } from 'solid-js';

const GIT_BRANCH_EVENT = 'voss://branch-changed';

const [branch, setBranch] = createSignal<string | null>(null);
export { branch };

let unlistenBranch: UnlistenFn | undefined;

export async function watchGitHead(projectPath: string): Promise<void> {
  unlistenBranch?.();
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

### Notifications Persistence Commands (Rust — mirrors save_session pattern)
```rust
// Source: session persistence pattern in lib.rs save_session [VERIFIED: codebase read]
// New commands to add to lib.rs invoke_handler:
#[tauri::command]
fn save_notifications(entries: Vec<serde_json::Value>) -> Result<(), String> {
    let path = dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("notifications.json");
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(&entries)
        .map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_notifications() -> Vec<serde_json::Value> {
    let path = dirs::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("voss-app")
        .join("notifications.json");
    let raw = match std::fs::read_to_string(&path) {
        Ok(s) => s,
        Err(_) => return Vec::new(),
    };
    serde_json::from_str(&raw).unwrap_or_default()
}
```

### Pane Count and Focused Leaf from GridController
```typescript
// Source: GridRoot.tsx collectLeaves + findLeaf + createMemo pattern [VERIFIED: codebase read]
// Add to GridController type and implementation:
getPaneCount: () => collectLeaves(store.root).length,
getFocusedLeaf: () => findLeaf(store.root, store.focusedId) ?? null,
```

### Popover Toggle Button Pattern
```typescript
// Source: CommandPalette toggle/dismiss pattern [ASSUMED from A7 pattern]
// In LeftCluster.tsx:
let anchorEl: HTMLButtonElement | undefined;

const handleClick = () => {
  if (isPopoverOpen('left-cluster')) {
    closePopover();
  } else {
    openPopover('left-cluster');
  }
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| notify crate for file watching | std::thread polling + AtomicBool | A7 established | No new crate; simpler; already proven |
| git2 for every HEAD read | Direct file read for hot path, git2 for discovery | A10 establishes | 10x faster for repeated polling |
| Context API for cross-component state | Module-level signals (toast.tsx pattern) | A7 established | Simpler, no Provider wrapping |

**Deprecated/outdated in this codebase:**
- `@tauri-apps/plugin-fs` `watch()` JavaScript API: The project does NOT use `@tauri-apps/plugin-fs` at all (not in package.json). The established pattern is Rust-side polling + `app.emit()` + `listen()`. Do not add the fs plugin for file watching.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `<Portal>` from `solid-js/web` is available | Pattern 3 | Would need to use a different teleport mechanism; solid-js/web is bundled with solid-js so risk is near-zero |
| A2 | `findLeaf(root, id)` exists and is exported from `tree.ts` | Pattern 4 | If not exported, need to add export or inline the search |
| A3 | GridController extension is the correct signal threading path for focused pane | Pattern 4 | If planner prefers a module-level store, the approach changes; see Open Questions |
| A4 | `beforeunload` / Tauri `close-requested` event is the right hook for notifications save | Pattern 5 | If the quit hook differs from A6, need to follow A6's actual hook |
| A5 | `.git/HEAD` format is stable (`ref: refs/heads/<branch>` or detached SHA) | Pattern 1 | Git has supported this format since 2005; no real risk |
| A6 | The cog button dispatching `open-settings` via registry is already wired by A9 | Architecture | If A9 does not register `open-settings` in the command registry, the cog handler needs its own wiring |
| A7 | PID is available from PTY session via `portable-pty` `Child::process_id()` | Open Questions | If PID is not available, the pid: field in PaneDetailPopover shows "—" |

---

## Open Questions

1. **PID for PaneDetailPopover (BAR-02)**
   - What we know: `PaneLeaf` has no `pid` field. The PTY session has a `Child` object. `portable-pty::Child` has a `process_id()` method returning `Option<u32>`.
   - What's unclear: Is `Child` still accessible after spawn, or is it consumed? The PtySession struct would need to expose pid.
   - Recommendation: Add `get_pty_pid(session_id)` to PtySession if `Child` exposes it, OR omit PID from the UI (show "—") in L1. The pane detail popover is purely informational; PID is a nice-to-have. Planner should check PtySession's stored fields before committing to the Rust command path.

2. **Focused pane signal threading to StatusBar**
   - What we know: GridRoot owns the store internally. App.tsx has a `gridController` ref but not a reactive accessor.
   - What's unclear: Should StatusBar receive a reactive accessor via props (cleanest for testability) or read a module-level signal that GridRoot updates on focus change?
   - Recommendation: Props drilling from App.tsx (pass `getFocusedLeaf` and `getPaneCount` as functions derived from the GridController memo). This avoids a module-level side channel while keeping GridRoot as the single store owner. The GridController type already accepts extension.

3. **Branch state when project changes**
   - What we know: When user switches project (via recent projects popover), `openSelectedProject` in App.tsx is called.
   - What's unclear: Is `stopGitWatch` called on the old project before `watchGitHead` on the new one?
   - Recommendation: Add `stopGitWatch()` call at the start of `openSelectedProject`, then `watchGitHead(info.path)` after the new project opens. This ensures clean transition.

4. **Notification store loading on app start**
   - What we know: `load_notifications` should be called on `onMount` in App.tsx (or in `notificationStore.ts` initialization).
   - What's unclear: Should `notificationStore.ts` self-initialize on import, or should App.tsx explicitly call an `initNotificationStore()` function?
   - Recommendation: Export an `initNotificationStore()` function (mirrors `installStructuralSessionAutosave` pattern from `sessionPersist.ts`). Called in App.tsx `onMount`. Avoids top-level async in the module.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | vitest, TypeScript | ✓ | 22.22.2 | — |
| pnpm | build, test | ✓ | 10.0.0 | — |
| cargo | Rust build | ✓ | 1.95.0-nightly | — |
| git2 crate | branch reading | ✓ | 0.20.4 (in Cargo.lock) | — |
| solid-js | frontend | ✓ | 1.9.13 (package.json) | — |
| @tauri-apps/api | event bridge | ✓ | 2.11.0 (package.json) | — |
| dirs crate | `~/.config/` path | ✓ | workspace dep | — |
| vitest | tests | ✓ | 4.1.6 (package.json) | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.
**New dependencies required:** none.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 4.1.6 |
| Config file | `apps/voss-app/vitest.config.ts` |
| Quick run command | `pnpm test` (from `apps/voss-app/`) |
| Full suite command | `pnpm test` (runs all `src/**/__tests__/**/*.test.{ts,tsx}`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BAR-01 | Left cluster shows project name and branch | unit | `pnpm test src/status-bar/__tests__/StatusBar.test.tsx` | ❌ Wave 0 |
| BAR-01 | Branch hidden when no git repo (D-11) | unit | `pnpm test src/status-bar/__tests__/LeftCluster.test.tsx` | ❌ Wave 0 |
| BAR-02 | Center cluster shows focused pane cwd/shell | unit | `pnpm test src/status-bar/__tests__/CenterCluster.test.tsx` | ❌ Wave 0 |
| BAR-03 | Pane count reflects leaf count | unit | `pnpm test src/status-bar/__tests__/RightCluster.test.tsx` | ❌ Wave 0 |
| BAR-03 | Bell badge shows unread count | unit | included in RightCluster test | ❌ Wave 0 |
| BAR-04 | Popover opens on click, closes on Esc/outside | unit | `pnpm test src/status-bar/__tests__/Popover.test.tsx` | ❌ Wave 0 |
| BAR-04 | Only one popover open at a time | unit | included in Popover test | ❌ Wave 0 |
| BAR-05 | StatusBar renders at 22px height | unit | included in StatusBar test | ❌ Wave 0 |
| BAR-06 | Git watcher emits branch-changed | unit | `pnpm test src/status-bar/__tests__/gitWatcher.test.ts` | ❌ Wave 0 |
| BAR-07 | addNotification adds to store + calls showToast | unit | `pnpm test src/status-bar/__tests__/notificationStore.test.ts` | ❌ Wave 0 |
| BAR-07 | clearAll empties store | unit | included in notificationStore test | ❌ Wave 0 |
| BAR-08 | No-project state renders correctly | unit | included in StatusBar/LeftCluster test | ❌ Wave 0 |
| BAR-01..08 | Full acceptance | integration | `pnpm test src/status-bar/__tests__/a10-acceptance.test.tsx` | ❌ Wave 0 |

### Tauri Mock Pattern (established — use vitest `vi.mock`)
```typescript
// Follow pattern from keymapStorage.test.ts:
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('@tauri-apps/api/event', () => ({ listen: h.listen }));
```

### Sampling Rate
- **Per task commit:** `pnpm test` from `apps/voss-app/` (runs all vitest tests, ~10s)
- **Per wave merge:** `pnpm test && cargo test -p voss-app-core && cargo build --package voss-app`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/status-bar/__tests__/notificationStore.test.ts` — covers BAR-07
- [ ] `src/status-bar/__tests__/gitWatcher.test.ts` — covers BAR-06
- [ ] `src/status-bar/__tests__/Popover.test.tsx` — covers BAR-04
- [ ] `src/status-bar/__tests__/StatusBar.test.tsx` — covers BAR-01, BAR-05, BAR-08
- [ ] `src/status-bar/__tests__/a10-acceptance.test.tsx` — covers BAR-01..08 integrated

---

## Security Domain

> `security_enforcement` not set to false; defaults enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (notification messages) | `message.slice(0, 120)` cap in `addNotification()` |
| V6 Cryptography | no | — |

### Known Threat Patterns for Status Bar

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Notification message injection (e.g., pane exit codes with HTML) | Spoofing/Tampering | Solid.js JSX auto-escapes text content; no `innerHTML` |
| Path traversal via project path in git watcher | Tampering | `watch_git_head` only watches `<project_path>/.git/HEAD`; project path is already validated by `open_project` |
| Unbounded notification accumulation | DoS (local) | 50-entry cap enforced in `addNotification()` |

---

## Sources

### Primary (HIGH confidence)
- `apps/voss-app/src-tauri/src/lib.rs` — `watch_keymap_overrides` pattern (lines 315–358); polling watcher with AtomicBool stop, `app.emit()` event push [VERIFIED: codebase read]
- `apps/voss-app/src/command-palette/toast.tsx` — module-level `createSignal<ToastItem[]>` store pattern [VERIFIED: codebase read]
- `apps/voss-app/src/command-palette/keymapStorage.ts` — `listen()`/`invoke()` event bridge pattern; `watch` → `listen` before `invoke` ordering [VERIFIED: codebase read]
- `apps/voss-app/src/App.tsx` — flex column layout; GridRoot below Titlebar; ToastStack; signal threading [VERIFIED: codebase read]
- `apps/voss-app/src/grid/GridRoot.tsx` — GridController type; `collectLeaves`; `store.focusedId` [VERIFIED: codebase read]
- `apps/voss-app/src/grid/tree.ts` — `PaneLeaf` shape; `collectLeaves`; `createGridStore` [VERIFIED: codebase read]
- `crates/voss-app-core/src/project.rs` — `read_git_branch` via git2; `ProjectInfo.git_branch` field [VERIFIED: codebase read]
- `crates/voss-app-core/Cargo.toml` — git2 0.20.x already present; no new Rust dep needed [VERIFIED: codebase read]
- `apps/voss-app/package.json` — solid-js 1.9.13; @tauri-apps/api 2.11.0; @tauri-apps/plugin-fs NOT installed [VERIFIED: codebase read]
- A10-UI-SPEC.md — full component inventory, all sizing constants, popover widths, color assignments [VERIFIED: file read]
- A10-CONTEXT.md — D-01..D-11 locked decisions [VERIFIED: file read]
- `.planning/ROADMAP.md` — BAR-01..08 requirements [VERIFIED: file read]
- Tauri v2 fs plugin docs (v2.tauri.app) — `watch()` JS API requires `@tauri-apps/plugin-fs`; NOT used in this project [CITED: v2.tauri.app/plugin/file-system]
- notify crate docs — Rust file watching alternative; not used (polling is sufficient) [CITED: docs.rs/notify]

### Secondary (MEDIUM confidence)
- `.git/HEAD` file format — `ref: refs/heads/<branch>` for normal branches, 40-char SHA for detached HEAD; stable since Git 2005 [CITED: standard git internals]
- `<Portal>` in solid-js/web — renders children at document.body; escapes overflow:hidden ancestors [ASSUMED from solid-js docs]

### Tertiary (LOW confidence)
- PID availability from `portable-pty` `Child::process_id()` — needs verification against actual PtySession fields [ASSUMED]
- `solid-js/store` `createStore` fine-grained reactivity advantage over `createSignal<T[]>` for notification list — standard Solid.js knowledge [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified from package.json, Cargo.toml, Cargo.lock
- Architecture: HIGH — all patterns verified from existing codebase; no invented patterns
- Pitfalls: HIGH — directly derived from prior-phase patterns (voss-app-solid-produce-no-structuredclone memory, keymap watcher review)
- Rust file watcher: HIGH — verbatim copy of proven `watch_keymap_overrides` pattern
- PID availability: LOW — needs code inspection of PtySession struct

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (stable dependencies; main risk is A9 `open-settings` command registration)
