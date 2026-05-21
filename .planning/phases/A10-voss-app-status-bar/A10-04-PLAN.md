---
phase: A10-voss-app-status-bar
plan: 04
type: execute
wave: 3
depends_on: [A10-01, A10-03]
files_modified:
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/status-bar/__tests__/a10-acceptance.test.tsx
autonomous: false
requirements: [BAR-01, BAR-02, BAR-03, BAR-04, BAR-05, BAR-06, BAR-07, BAR-08]
must_haves:
  truths:
    - "StatusBar is visible below GridRoot in the app flex column"
    - "Focused pane cwd/shell updates when focus changes in the grid"
    - "Pane count updates when panes are split or closed"
    - "Branch signal flows from git watcher through to left cluster"
    - "Notification store loads persisted entries on app mount"
    - "Git watcher starts on project open and stops on project switch"
    - "Project-less mode shows no-project fallback in status bar"
  artifacts:
    - path: "apps/voss-app/src/grid/GridRoot.tsx"
      provides: "getFocusedLeaf and getPaneCount on GridController"
      contains: "getFocusedLeaf"
    - path: "apps/voss-app/src/App.tsx"
      provides: "StatusBar mounted below GridRoot with all signals wired"
      contains: "StatusBar"
    - path: "apps/voss-app/src/status-bar/__tests__/a10-acceptance.test.tsx"
      provides: "BAR-01..08 acceptance test battery"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/status-bar/StatusBar.tsx"
      via: "import StatusBar"
      pattern: "import StatusBar from.*status-bar"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/status-bar/gitWatcher.ts"
      via: "import { branch, watchGitHead, stopGitWatch }"
      pattern: "import.*watchGitHead.*gitWatcher"
    - from: "apps/voss-app/src/grid/GridRoot.tsx"
      to: "apps/voss-app/src/grid/tree.ts"
      via: "findLeaf + collectLeaves for controller methods"
      pattern: "getFocusedLeaf.*findLeaf"
---

<objective>
App.tsx integration: mount StatusBar, wire signals, extend GridController, acceptance tests.

Purpose: Connect the StatusBar UI (Plan 03) and Rust backend (Plan 01) to the live app.
Extend GridController with `getFocusedLeaf` and `getPaneCount` so the center cluster
reactively displays focused pane info. Wire git watcher lifecycle to project open/switch.
Write the BAR-01..08 acceptance test battery.

Output: GridRoot.tsx extended, App.tsx wired, acceptance tests verifying all 8 requirements.
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
@.planning/phases/A10-voss-app-status-bar/A10-01-SUMMARY.md
@.planning/phases/A10-voss-app-status-bar/A10-02-SUMMARY.md
@.planning/phases/A10-voss-app-status-bar/A10-03-SUMMARY.md

<interfaces>
<!-- Key types from prior plans and existing codebase -->

From apps/voss-app/src/grid/GridRoot.tsx (existing GridController type):
```typescript
export type GridController = {
  applyPreset: (preset: LayoutPreset) => void;
  applyLoadedLayout: (file: LayoutFile) => void;
  applySession: (session: SessionFile) => void;
  splitFocused: (orientation: 'H' | 'V') => void;
  closeFocused: () => void;
  equalizePanes: () => void;
  cycleLayout: () => void;
  focusNext: () => void;
  focusPrev: () => void;
  focusIndex: (n: number) => void;
  focusDirection: (dir: 'left' | 'right' | 'up' | 'down') => void;
  resizeDirection: (dir: 'left' | 'right' | 'up' | 'down') => void;
  snapshot: () => { root: TreeNode; focusedId: string };
  // A10 adds:
  getFocusedLeaf: () => PaneLeaf | null;
  getPaneCount: () => number;
};
```

From apps/voss-app/src/grid/tree.ts:
```typescript
export function findLeaf(root: TreeNode, id: string): PaneLeaf | undefined;
export function collectLeaves(root: TreeNode): PaneLeaf[];
```

From apps/voss-app/src/App.tsx (existing imports + return JSX, lines 1-53, 398-460):
```typescript
// Existing signals:
const [project, setProject] = createSignal<ProjectInfo | null>(null);
let gridController: GridController | undefined;
// Existing JSX order: Titlebar → Show(GridRoot) → ToastStack → CommandPalette
```

From apps/voss-app/src/status-bar/StatusBar.tsx (Plan 03 output):
```typescript
export default function StatusBar(props: {
  project: ProjectInfo | null;
  branch: string | null;
  getFocusedLeaf: () => PaneLeaf | null;
  getPaneCount: () => number;
  onOpenProject: (path: string) => void;
  dispatchCommand: (id: string) => boolean;
});
```

From apps/voss-app/src/status-bar/gitWatcher.ts (Plan 02 output):
```typescript
export const branch: () => string | null;
export function watchGitHead(projectPath: string): Promise<void>;
export function stopGitWatch(): void;
```

From apps/voss-app/src/status-bar/notificationStore.ts (Plan 02 output):
```typescript
export function initNotificationStore(): Promise<() => void>;
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend GridController + wire StatusBar in App.tsx</name>
  <files>apps/voss-app/src/grid/GridRoot.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/GridRoot.tsx (full file — GridController type at lines 94-111, controllerRef callback construction)
    - apps/voss-app/src/App.tsx (full file — imports at 1-53, onMount at 358-386, return JSX at 398-460, handleOpenFolder/handleOpenRecent functions, dispatchCommandId)
    - apps/voss-app/src/grid/tree.ts (findLeaf, collectLeaves exports)
    - apps/voss-app/src/status-bar/StatusBar.tsx (props interface)
    - apps/voss-app/src/status-bar/gitWatcher.ts (watchGitHead, stopGitWatch, branch exports)
    - apps/voss-app/src/status-bar/notificationStore.ts (initNotificationStore export)
    - .planning/phases/A10-voss-app-status-bar/A10-RESEARCH.md (Pattern 4: focused pane signal, Pattern 6: App.tsx integration, Open Question 2: signal threading, Open Question 3: branch state on project change)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (App.tsx section, GridController extension section)
  </read_first>
  <action>
    **GridRoot.tsx changes** (additive only — existing methods untouched):

    1. Add `createMemo` to the solid-js import if not already present.

    2. Inside the GridRoot function body (where the store is created and the controller object is built), add two reactive memos:
       - `const focusedLeaf = createMemo(() => findLeaf(store.root, store.focusedId) ?? null);`
       - `const paneCount = createMemo(() => collectLeaves(store.root).length);`
       Note: `findLeaf` and `collectLeaves` are already imported from `./tree`.

    3. Extend the `GridController` TYPE definition (not the runtime object yet — the type at line ~94) with two new methods:
       - `getFocusedLeaf: () => PaneLeaf | null;`
       - `getPaneCount: () => number;`

    4. In the controller object construction (inside the component, where `controllerRef` is called), add:
       - `getFocusedLeaf: () => focusedLeaf(),`
       - `getPaneCount: () => paneCount(),`

    **App.tsx changes** (additive — no existing line removed):

    1. Add imports:
       - `import StatusBar from './status-bar/StatusBar';`
       - `import { branch, watchGitHead, stopGitWatch } from './status-bar/gitWatcher';`
       - `import { initNotificationStore } from './status-bar/notificationStore';`

    2. Add two local signals for StatusBar reactive props that bridge GridController into the render tree:
       - `const [statusFocusedLeaf, setStatusFocusedLeaf] = createSignal<PaneLeaf | null>(null);`
       - `const [statusPaneCount, setStatusPaneCount] = createSignal(0);`

    3. In the existing `controllerRef` callback (where `gridController = c` is set), add after the controller assignment:
       - Wire a reactive effect or polling update — simplest: just set the signals from the controller in the same callback. Since `controllerRef` fires once, use a `createEffect` (imported from solid-js) in the outer component scope that reads `gridController?.getFocusedLeaf()` and `gridController?.getPaneCount()` to drive the StatusBar signals. OR more simply: pass getter functions to StatusBar props that call through to the controller.
       - **Chosen approach** (per RESEARCH Open Question 2 recommendation — props drilling): Pass `getFocusedLeaf={() => gridController?.getFocusedLeaf() ?? null}` and `getPaneCount={() => gridController?.getPaneCount() ?? 0}` directly as StatusBar props. These are reactive because GridController methods call memos backed by the Solid store.

    4. In the `onMount` block, add:
       - `void initNotificationStore();` — load persisted notifications and install quit-save hook.
       - Git watcher start for current project: if `project()` is non-null at mount time, `void watchGitHead(project()!.path);`.

    5. Wire git watcher lifecycle to project changes. In `handleOpenFolder` (or wherever `setProject(info)` is called after a successful `openProject(path)` call):
       - Before `setProject(info)`: call `stopGitWatch()` to cancel any existing watcher.
       - After `setProject(info)`: call `void watchGitHead(info.path)` to start new watcher.
       - Same pattern in `handleOpenRecent` if it calls `openProject` and `setProject`.
       - This resolves RESEARCH Open Question 3 (branch state on project change).

    6. In the JSX return, insert `<StatusBar>` between the GridRoot `</Show>` closing tag and the `<ToastStack />` component:
       ```
       <StatusBar
         project={project()}
         branch={branch()}
         getFocusedLeaf={() => gridController?.getFocusedLeaf() ?? null}
         getPaneCount={() => gridController?.getPaneCount() ?? 0}
         onOpenProject={handleOpenRecent}
         dispatchCommand={dispatchCommandId}
       />
       ```
       StatusBar renders always (not inside the Show/when=showGrid guard) — it shows even in project-less mode (BAR-08 fallback).

    7. In `onCleanup`, add `stopGitWatch();` to clean up the watcher thread.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -10 && pnpm vitest run src/grid/ 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - GridController type includes getFocusedLeaf and getPaneCount methods
    - GridRoot.tsx contains createMemo for focusedLeaf and paneCount
    - App.tsx imports StatusBar, branch, watchGitHead, stopGitWatch, initNotificationStore
    - App.tsx JSX contains <StatusBar> between the GridRoot Show block and ToastStack
    - App.tsx onMount calls initNotificationStore()
    - App.tsx handleOpenFolder/handleOpenRecent calls stopGitWatch() before and watchGitHead() after project switch
    - App.tsx onCleanup calls stopGitWatch()
    - tsc --noEmit exits 0
    - Existing grid tests (src/grid/) still pass (no regression)
  </acceptance_criteria>
  <done>StatusBar mounted in App.tsx with reactive signal wiring; GridController extended; git watcher lifecycle tied to project open/switch; notification store loads on mount</done>
</task>

<task type="auto">
  <name>Task 2: BAR-01..08 acceptance tests</name>
  <files>apps/voss-app/src/status-bar/__tests__/a10-acceptance.test.tsx</files>
  <read_first>
    - apps/voss-app/src/status-bar/StatusBar.tsx (props interface, data-testid)
    - apps/voss-app/src/status-bar/LeftCluster.tsx (project/branch rendering)
    - apps/voss-app/src/status-bar/RightCluster.tsx (pane count, bell badge, cog)
    - apps/voss-app/src/status-bar/notificationStore.ts (addNotification, unreadCount, _resetNotificationsForTest)
    - apps/voss-app/src/status-bar/Popover.tsx (_resetPopoverForTest)
    - apps/voss-app/src/status-bar/__tests__/StatusBar.test.tsx (existing test patterns)
    - .planning/phases/A10-voss-app-status-bar/A10-VALIDATION.md (Success Criteria)
    - .planning/ROADMAP.md (BAR-01..08 requirements)
  </read_first>
  <action>
    Create the BAR-01..08 acceptance test file. This is the phase gate — every requirement must have a test.

    **Test setup:**
    - Mock Tauri APIs via vi.hoisted pattern (invoke, listen, getCurrentWindow).
    - Mock `../project/projectStorage` (listRecents returns mock data).
    - Import StatusBar, addNotification, _resetNotificationsForTest, _resetPopoverForTest.
    - Helper: `renderStatusBar(overrides)` function that renders `<StatusBar>` with default props merged with overrides.
    - `beforeEach`: reset notification store, reset popover, reset mocks.

    **Required tests (one per BAR requirement):**

    BAR-01: "left cluster shows project name and git branch" — render with `project: { path: '/x', name: 'voss', gitBranch: 'main' }` and `branch: 'main'`. Assert text contains `voss` and `main`.

    BAR-01 (D-11): "branch hidden when no git repo" — render with project but `branch: null`. Assert branch glyph `\u2387` is NOT in the text content.

    BAR-02: "center cluster shows focused pane cwd and shell" — render with `getFocusedLeaf` returning `{ kind: 'pane', id: '1', cwd: '~/projects', shell: 'zsh', index: 1 }`. Assert text contains `~/projects` and `zsh`.

    BAR-03: "right cluster shows pane count" — render with `getPaneCount: () => 4`. Assert text contains `4`.

    BAR-03: "bell badge shows unread count" — add 3 notifications via `addNotification`, render. Assert badge element exists with count `3`.

    BAR-03: "bell badge hidden when no unread" — render without notifications. Assert no badge element.

    BAR-04: "popover opens on cluster click and closes on Esc" — render, click the left cluster button, assert popover content (e.g., "Recent Projects" heading) is in DOM. Fire Esc keydown. Assert popover content is removed.

    BAR-05: "status bar renders at 22px with role toolbar" — render. Assert `data-testid="status-bar"` element exists with `role="toolbar"` and computed height style of `22px`.

    BAR-06: (unit-level, structural) "git watcher bridge is imported and connected" — this is a structural test. Assert that the gitWatcher module exports `branch` and `watchGitHead`. The 500ms latency requirement is validated at runtime; the structural test ensures the wiring exists.

    BAR-07: "notification store caps at 50 and clearAll works" — add 55 notifications, assert store length is 50. Call `clearAll()`, assert store length is 0.

    BAR-08: "project-less mode shows fallback text" — render with `project: null, branch: null`. Assert text contains "no project".
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/status-bar/__tests__/a10-acceptance.test.tsx 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - a10-acceptance.test.tsx has at least 11 tests (one per requirement + sub-cases)
    - BAR-01 test passes (project name + branch displayed)
    - BAR-01/D-11 test passes (branch hidden when null)
    - BAR-02 test passes (cwd + shell from focused leaf)
    - BAR-03 tests pass (pane count + bell badge + badge hidden)
    - BAR-04 test passes (popover open/close)
    - BAR-05 test passes (22px + role toolbar)
    - BAR-06 structural test passes
    - BAR-07 test passes (50 cap + clearAll)
    - BAR-08 test passes (no-project fallback)
    - All prior status-bar tests still pass
  </acceptance_criteria>
  <done>Full BAR-01..08 acceptance battery passes; all status-bar tests green; phase ready for verify-work</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Full status bar integrated into the voss-app: 22px strip below GridRoot with three
    clusters (left: project+branch, center: focused pane, right: pane count+bell+cog),
    click-to-popover details, notification store with persistence, and git HEAD file
    watcher with 200ms polling.
  </what-built>
  <how-to-verify>
    1. Run the app: `cd apps/voss-app && pnpm tauri dev`
    2. Verify the status bar is visible at the bottom — 22px dark strip below the grid.
    3. **BAR-01:** Confirm left cluster shows project name and git branch (e.g., "dev").
    4. **BAR-02:** Click different panes — confirm center cluster updates with focused pane's cwd and shell.
    5. **BAR-03:** Split panes (Cmd+D) — confirm pane count increments. Close panes (Cmd+W) — count decrements.
    6. **BAR-04:** Click left cluster — popover shows recent projects list. Click center — pane detail. Click bell — notifications. Esc closes. Only one popover at a time.
    7. **BAR-05:** Visually confirm 22px height, mono font, Variant B colors.
    8. **BAR-06:** In a pane, run `git checkout -b test-a10` then `git checkout dev`. Confirm branch name updates in the status bar within ~1 second.
    9. **BAR-08:** If possible, start without a project — confirm "no project" fallback text and hidden branch.
    10. **Bell badge:** If any notifications have fired (pane exit, etc.), confirm the bell shows a badge count. Click bell — badge clears.
  </how-to-verify>
  <resume-signal>Type "approved" or describe visual/functional issues</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GridController → StatusBar | Pane data crosses from grid store to status bar display |
| git watcher events → App.tsx | Branch change events from Rust thread arrive in frontend |
| persisted notifications.json → store | Loaded file contents populate the notification store |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A10-11 | Tampering | notifications.json load | mitigate | load_notifications returns empty vec on parse error (malformed file = graceful fallback, not crash) |
| T-A10-12 | DoS | GridController memos | accept | createMemo is reactive; recalculates only when store changes; no polling overhead |
| T-A10-13 | Repudiation | git watcher lifecycle | mitigate | stopGitWatch called in onCleanup and before project switch; prevents orphan watcher threads |
| T-A10-SC | Tampering | npm/pip/cargo installs | accept | No new dependencies |
</threat_model>

<verification>
```bash
# Full status-bar test suite
cd apps/voss-app && pnpm vitest run src/status-bar/

# Grid tests (regression check)
cd apps/voss-app && pnpm vitest run src/grid/

# Full frontend suite
cd apps/voss-app && pnpm vitest run

# Rust build
cargo build --package voss-app

# Rust tests
cargo test -p voss-app-core

# Type check
cd apps/voss-app && npx tsc --noEmit
```
</verification>

<success_criteria>
- StatusBar visible in the app below GridRoot
- All 8 BAR requirements have passing acceptance tests
- Full vitest suite green (no regressions in grid, command-palette, etc.)
- cargo build + cargo test green
- tsc --noEmit green
- Human verifies visual correctness and branch update latency
</success_criteria>

<output>
Create `.planning/phases/A10-voss-app-status-bar/A10-04-SUMMARY.md` when done
</output>
