---
phase: A10-voss-app-status-bar
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src/status-bar/notificationStore.ts
  - apps/voss-app/src/status-bar/gitWatcher.ts
  - apps/voss-app/src/status-bar/Popover.tsx
  - apps/voss-app/src/status-bar/__tests__/notificationStore.test.ts
  - apps/voss-app/src/status-bar/__tests__/gitWatcher.test.ts
  - apps/voss-app/src/status-bar/__tests__/Popover.test.tsx
autonomous: true
requirements: [BAR-04, BAR-05, BAR-06, BAR-07]
must_haves:
  truths:
    - "addNotification adds to store AND calls showToast (D-05 unified stream)"
    - "markAllRead sets all entries to read:true (D-06)"
    - "Notification store caps at 100 entries in memory (BAR-07)"
    - "persistNotifications sends last 50 to Rust for disk write (D-07/SC4)"
    - "initNotificationStore loads from Rust and installs quit-save hook (D-07)"
    - "Git watcher bridge registers listen() before invoke() (Pitfall 6)"
    - "branch() signal updates when Tauri event fires"
    - "Only one popover can be open at a time (D-01/D-04)"
    - "Popover dismisses on click-outside and Esc"
  artifacts:
    - path: "apps/voss-app/src/status-bar/notificationStore.ts"
      provides: "NotificationEntry type, addNotification, markAllRead, clearAll, unreadCount, initNotificationStore, notifications store"
      exports: ["NotificationEntry", "addNotification", "markAllRead", "clearAll", "unreadCount", "initNotificationStore", "notifications", "_resetNotificationsForTest", "MAX_NOTIFICATIONS", "MAX_PERSISTED"]
    - path: "apps/voss-app/src/status-bar/gitWatcher.ts"
      provides: "branch signal, watchGitHead, stopGitWatch"
      exports: ["branch", "watchGitHead", "stopGitWatch"]
    - path: "apps/voss-app/src/status-bar/Popover.tsx"
      provides: "Generic Popover component with one-at-a-time enforcement"
      exports: ["default", "isPopoverOpen", "openPopover", "closePopover"]
  key_links:
    - from: "apps/voss-app/src/status-bar/notificationStore.ts"
      to: "apps/voss-app/src/command-palette/toast.tsx"
      via: "import showToast"
      pattern: "showToast\\(severity"
    - from: "apps/voss-app/src/status-bar/gitWatcher.ts"
      to: "@tauri-apps/api/event"
      via: "listen('voss://branch-changed')"
      pattern: "listen.*branch-changed"
---

<objective>
Frontend stores, services, and generic Popover component for the status bar.

Purpose: Build the three foundational frontend modules that the StatusBar UI
components (Plan 03) will consume: notification store (D-05/D-06/D-07),
git watcher bridge (D-09/D-10/D-11), and the generic Popover (D-01/D-04).
These are file-disjoint from Plan 01 (Rust) and can execute in parallel.

Output: Three TypeScript/TSX modules in `src/status-bar/` plus three test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A10-voss-app-status-bar/A10-CONTEXT.md
@.planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md
@.planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md
@.planning/phases/A10-voss-app-status-bar/A10-UI-SPEC.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From apps/voss-app/src/command-palette/toast.tsx:
```typescript
export type ToastSeverity = 'success' | 'warning' | 'error' | 'info';
export function showToast(severity: ToastSeverity, message: string): void;
export function _resetToastsForTest(): void;
```

From apps/voss-app/src/command-palette/keymapStorage.ts (listen-before-invoke pattern):
```typescript
// CRITICAL: listen() BEFORE invoke()
const unlisten = await listen<T>(EVENT_NAME, handler);
try {
  const initial = await invoke<T>('start_watcher', { ... });
  onUpdate(initial);
} catch (error) {
  unlisten();
  throw error;
}
```

From apps/voss-app/src/grid/sessionPersist.ts (quit-save pattern):
```typescript
import { getCurrentWindow } from '@tauri-apps/api/window';
const unlisten = await getCurrentWindow().onCloseRequested(async (event) => {
  event.preventDefault();
  // ... save ...
  await getCurrentWindow().close();
});
```

From apps/voss-app/src/command-palette/__tests__/keymapStorage.test.ts (Tauri mock pattern):
```typescript
const h = vi.hoisted(() => ({
  invoke: vi.fn(),
  listen: vi.fn(() => Promise.resolve(() => {})),
}));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('@tauri-apps/api/event', () => ({ listen: h.listen }));
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Notification store and git watcher bridge</name>
  <files>apps/voss-app/src/status-bar/notificationStore.ts, apps/voss-app/src/status-bar/gitWatcher.ts, apps/voss-app/src/status-bar/__tests__/notificationStore.test.ts, apps/voss-app/src/status-bar/__tests__/gitWatcher.test.ts</files>
  <read_first>
    - apps/voss-app/src/command-palette/toast.tsx (module-level signal store pattern, showToast signature, _resetToastsForTest)
    - apps/voss-app/src/command-palette/keymapStorage.ts (listen-before-invoke pattern, lines 83-106)
    - apps/voss-app/src/grid/sessionPersist.ts (installCloseSessionSave / onCloseRequested quit-save pattern, lines 82-110)
    - apps/voss-app/src/command-palette/__tests__/keymapStorage.test.ts (vi.hoisted Tauri mock pattern)
    - .planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md (Pattern 2: notificationStore, Pattern 5: persistence)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (notificationStore.ts and gitWatcher.ts sections)
    - .planning/phases/A10-voss-app-status-bar/A10-UI-SPEC.md (Notification Store Schema section)
  </read_first>
  <action>
    Create the `apps/voss-app/src/status-bar/` directory and two module files:

    **notificationStore.ts** — module-level `createStore` (NOT createSignal) per RESEARCH Pattern 2:
    - Export `NotificationEntry` interface: `{ id: number, severity: 'success'|'warning'|'error'|'info', message: string, source: string, timestamp: number, read: boolean }` per UI-SPEC schema.
    - Module-level `const [notifications, setNotifications] = createStore<NotificationEntry[]>([])`.
    - TWO constants for the dual-buffer design (BLOCKER 1 fix):
      - `export const MAX_NOTIFICATIONS = 100` — in-memory buffer size. This is what the bell popover shows (per BAR-07 "last 100 events").
      - `export const MAX_PERSISTED = 50` — what gets written to notifications.json on quit (per D-07 "last 50 entries" / SC4).
    - `addNotification(severity, message, source)`: create entry with `id: nextId++`, `message.slice(0, 120)`, `timestamp: Date.now()`, `read: false`; append to store sliced to last MAX_NOTIFICATIONS (100); call `showToast(severity as ToastSeverity, message)` per D-05 unified stream. Import `showToast` and `ToastSeverity` from `../command-palette/toast`.
    - `markAllRead()`: map all entries to `{ ...e, read: true }` per D-06.
    - `clearAll()`: set store to `[]`.
    - `unreadCount()`: filter `!e.read`, return `.length`.
    - `highestUnreadSeverity()`: return the highest severity among unread entries (error > warning > info > success) or `null` if none unread. Per UI-SPEC bell badge color contract.
    - `persistNotifications()`: helper that returns `[...notifications].slice(-MAX_PERSISTED)` — the last 50 entries for Rust to write. Used in the quit-save hook.
    - `initNotificationStore()`: returns `Promise<() => void>`. Calls `invoke<NotificationEntry[]>('load_notifications')`, slices to last MAX_NOTIFICATIONS (100), sets store. Then registers `getCurrentWindow().onCloseRequested` handler that calls `invoke('save_notifications', { entries: persistNotifications() })` then `getCurrentWindow().close()`. Returns the unlisten function. Follows `installCloseSessionSave` pattern from sessionPersist.ts.
    - `_resetNotificationsForTest()`: set store to `[]`, reset nextId to 1.
    - Export `notifications` (read-only getter).

    **gitWatcher.ts** — module-level `createSignal<string | null>(null)` per RESEARCH/PATTERNS:
    - Event constant `GIT_BRANCH_EVENT = 'voss://branch-changed'`.
    - Module-level `const [branch, setBranch] = createSignal<string | null>(null)`.
    - `watchGitHead(projectPath: string): Promise<void>` — cancel previous unlisten if any; `await listen<string | null>(GIT_BRANCH_EVENT, ...)` FIRST (Pitfall 6 ordering); then `await invoke<string | null>('watch_git_head', { projectPath })`; set initial branch; store unlisten fn. On error: call unlisten, set branch null, re-throw.
    - `stopGitWatch(): void` — call stored unlisten if any, set branch to null, clear ref.
    - Export `branch` signal.

    **notificationStore.test.ts** — follow keymapStorage.test.ts mock pattern:
    - `vi.hoisted` mock for `@tauri-apps/api/core` (invoke) and `@tauri-apps/api/event` (listen) and `@tauri-apps/api/window` (getCurrentWindow -> onCloseRequested mock).
    - Also mock `../command-palette/toast` so `showToast` calls are captured.
    - Tests: addNotification adds entry + calls showToast; addNotification caps at 100 (MAX_NOTIFICATIONS); message truncated to 120 chars; markAllRead sets all read:true; clearAll empties store; unreadCount returns correct count; highestUnreadSeverity returns correct severity ordering; persistNotifications returns last 50 entries when store has more than 50; _resetNotificationsForTest clears state.
    - `beforeEach` calls `_resetNotificationsForTest()` and resets mocks.

    **gitWatcher.test.ts** — follow keymapStorage.test.ts mock pattern:
    - Mock `@tauri-apps/api/core` and `@tauri-apps/api/event`.
    - Tests: watchGitHead calls listen before invoke (check call order); branch signal updates on mock event emission; stopGitWatch clears branch to null; watchGitHead handles invoke error (branch stays null, unlisten called).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/status-bar/__tests__/notificationStore.test.ts src/status-bar/__tests__/gitWatcher.test.ts 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - src/status-bar/notificationStore.ts exports: NotificationEntry, addNotification, markAllRead, clearAll, unreadCount, highestUnreadSeverity, initNotificationStore, notifications, persistNotifications, _resetNotificationsForTest, MAX_NOTIFICATIONS, MAX_PERSISTED
    - src/status-bar/notificationStore.ts imports showToast from ../command-palette/toast
    - src/status-bar/notificationStore.ts uses createStore (not createSignal) from solid-js/store
    - src/status-bar/notificationStore.ts contains `MAX_NOTIFICATIONS = 100` (in-memory cap per BAR-07)
    - src/status-bar/notificationStore.ts contains `MAX_PERSISTED = 50` (disk cap per D-07)
    - src/status-bar/notificationStore.ts addNotification slices to last MAX_NOTIFICATIONS (100)
    - src/status-bar/notificationStore.ts persistNotifications slices to last MAX_PERSISTED (50)
    - src/status-bar/notificationStore.ts initNotificationStore calls getCurrentWindow().onCloseRequested
    - src/status-bar/gitWatcher.ts exports: branch, watchGitHead, stopGitWatch
    - src/status-bar/gitWatcher.ts listen() call precedes invoke() call in watchGitHead
    - src/status-bar/gitWatcher.ts event constant is 'voss://branch-changed'
    - notificationStore.test.ts has at least 7 passing tests (including 100-cap and persistNotifications-50 tests)
    - gitWatcher.test.ts has at least 3 passing tests
    - tsc --noEmit exits 0
  </acceptance_criteria>
  <done>Notification store adds+caps at 100 in memory+persists last 50 on quit+resets entries; showToast called on every add (D-05); git watcher bridge follows listen-before-invoke pattern; both modules have passing unit tests</done>
</task>

<task type="auto">
  <name>Task 2: Generic Popover component with one-at-a-time enforcement</name>
  <files>apps/voss-app/src/status-bar/Popover.tsx, apps/voss-app/src/status-bar/__tests__/Popover.test.tsx</files>
  <read_first>
    - apps/voss-app/src/command-palette/CommandPalette.tsx (click-outside + Esc dismiss pattern)
    - .planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md (Pattern 3: Generic Popover)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (Popover.tsx section)
    - .planning/phases/A10-voss-app-status-bar/A10-UI-SPEC.md (Layout Contract, Popover Positioning, Interaction Contracts)
  </read_first>
  <action>
    Create `apps/voss-app/src/status-bar/Popover.tsx` per D-01/D-04:

    **Module-level one-at-a-time signal:**
    - `const [openPopoverId, setOpenPopoverId] = createSignal<string | null>(null)`
    - Export `isPopoverOpen(id: string): boolean` — returns `openPopoverId() === id`
    - Export `openPopover(id: string): void` — sets `openPopoverId(id)` (closing any other)
    - Export `closePopover(): void` — sets `openPopoverId(null)`
    - Export `_resetPopoverForTest(): void` — sets to null (test cleanup)

    **Popover component** — `export default function Popover(props: { id: string; anchor: HTMLElement | undefined; width: number; maxHeight?: number; children: JSX.Element })`:
    - Use `<Show when={isPopoverOpen(props.id)}>` wrapping `<Portal>` from `solid-js/web`. Portal is required because GridRoot uses `overflow:hidden` (RESEARCH anti-pattern).
    - Inner div: `ref={popoverEl}`, positioned via computed `position()` function:
      - `position: 'fixed'`, `bottom: '22px'` (opens upward from status bar per UI-SPEC).
      - `left` computed from `anchor.getBoundingClientRect().left`, edge-clamped: shift left if `left + width > window.innerWidth - 16`, floor at `16`.
      - `width: props.width + 'px'`, `max-height: props.maxHeight ? props.maxHeight + 'px' : undefined`.
      - `z-index: 20` per UI-SPEC structural constants.
      - Styling: `background: 'var(--bg-3)'`, `border: '1px solid var(--border)'`, `overflow-y: 'auto'`, `border-radius: '0px'` (Variant B absolute rule).
    - `onMount`: register `document.addEventListener('mousedown', handleClickOutside)` and `document.addEventListener('keydown', handleEsc)`.
    - `onCleanup`: remove both event listeners.
    - `handleClickOutside`: if click target is not inside popoverEl AND not inside anchor, call `closePopover()`.
    - `handleEsc`: if `e.key === 'Escape'`, call `closePopover()`.

    **Popover.test.tsx** — follow existing @testing-library/dom + solid-js/web pattern:
    - Test: opening popover shows content; closing via Esc hides content; click-outside closes popover; only one popover open at a time (open A, open B, A closes); toggle behavior (click cluster when already open closes popover); _resetPopoverForTest clears state.
    - Mock the Portal target or render to a container.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/status-bar/__tests__/Popover.test.tsx 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - src/status-bar/Popover.tsx exports default Popover component
    - src/status-bar/Popover.tsx exports isPopoverOpen, openPopover, closePopover, _resetPopoverForTest
    - Popover uses Portal from solid-js/web
    - Popover positioned with `bottom: '22px'` and `position: 'fixed'`
    - Popover z-index is 20
    - Popover background is var(--bg-3), border is 1px solid var(--border), border-radius is 0
    - Click-outside and Esc both call closePopover
    - Popover.test.tsx has at least 4 passing tests
    - tsc --noEmit exits 0
  </acceptance_criteria>
  <done>Generic Popover component renders via Portal above the status bar, enforces one-at-a-time, dismisses on Esc and click-outside, all tests pass</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Tauri event -> frontend | Branch-changed events from Rust arrive as untyped payloads |
| notification message -> DOM | User-visible text rendered in UI |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A10-05 | Spoofing | notificationStore addNotification | mitigate | message.slice(0, 120) caps input length; Solid JSX auto-escapes text (no innerHTML) |
| T-A10-06 | DoS | notificationStore | mitigate | MAX_NOTIFICATIONS = 100 in-memory hard cap; MAX_PERSISTED = 50 disk cap; slice enforced on every add and persist |
| T-A10-07 | Tampering | gitWatcher event payload | accept | Payload is string|null from same-process Rust; no cross-origin risk; type assertion at listen() generic |
| T-A10-SC | Tampering | npm/pip/cargo installs | accept | No new dependencies; all imports from existing solid-js, @tauri-apps/api |
</threat_model>

<verification>
```bash
# All new tests
cd apps/voss-app && pnpm vitest run src/status-bar/__tests__/

# Type check
cd apps/voss-app && npx tsc --noEmit

# No new deps
git diff HEAD -- apps/voss-app/package.json | grep -c '^\+.*"dependencies"' || echo "no new deps"
```
</verification>

<success_criteria>
- notificationStore.ts, gitWatcher.ts, Popover.tsx all created in src/status-bar/
- All three test files pass
- tsc --noEmit exits 0
- No new npm dependencies added
- D-05 unified stream verified (addNotification calls showToast)
- D-01/D-04 one-at-a-time enforcement verified in Popover tests
- MAX_NOTIFICATIONS = 100 (in-memory, per BAR-07)
- MAX_PERSISTED = 50 (disk, per D-07)
- persistNotifications() returns last 50 entries for quit-save
</success_criteria>

<output>
Create `.planning/phases/A10-voss-app-status-bar/A10-02-SUMMARY.md` when done
</output>
