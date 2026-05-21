---
phase: A10-voss-app-status-bar
plan: 03
type: execute
wave: 2
depends_on: [A10-02]
files_modified:
  - apps/voss-app/src/status-bar/StatusBar.tsx
  - apps/voss-app/src/status-bar/LeftCluster.tsx
  - apps/voss-app/src/status-bar/CenterCluster.tsx
  - apps/voss-app/src/status-bar/RightCluster.tsx
  - apps/voss-app/src/status-bar/RecentProjectsPopover.tsx
  - apps/voss-app/src/status-bar/PaneDetailPopover.tsx
  - apps/voss-app/src/status-bar/NotificationsPopover.tsx
  - apps/voss-app/src/status-bar/__tests__/StatusBar.test.tsx
autonomous: true
requirements: [BAR-01, BAR-02, BAR-03, BAR-04, BAR-05, BAR-08]
must_haves:
  truths:
    - "StatusBar renders as a 22px strip with three clusters (BAR-05)"
    - "Left cluster shows project name + branch, or no-project fallback (BAR-01/BAR-08)"
    - "Branch hidden entirely when no git repo (D-11)"
    - "Center cluster shows focused pane cwd and shell (BAR-02)"
    - "Right cluster shows pane count, bell with badge, and settings cog (BAR-03)"
    - "Click left cluster opens RecentProjectsPopover (D-02)"
    - "Click center cluster opens PaneDetailPopover (D-03)"
    - "Click bell opens NotificationsPopover and clears badge (D-06)"
    - "Click cog dispatches open-settings command (A9)"
    - "Popovers are mutually exclusive — opening one closes another (D-01)"
  artifacts:
    - path: "apps/voss-app/src/status-bar/StatusBar.tsx"
      provides: "Root StatusBar component composing three clusters"
      exports: ["default"]
    - path: "apps/voss-app/src/status-bar/LeftCluster.tsx"
      provides: "Project + branch display with left popover"
      exports: ["default"]
    - path: "apps/voss-app/src/status-bar/RightCluster.tsx"
      provides: "Pane count + bell + cog with notifications popover"
      exports: ["default"]
  key_links:
    - from: "apps/voss-app/src/status-bar/StatusBar.tsx"
      to: "apps/voss-app/src/status-bar/Popover.tsx"
      via: "import Popover, { openPopover, closePopover, isPopoverOpen }"
      pattern: "import.*Popover"
    - from: "apps/voss-app/src/status-bar/RightCluster.tsx"
      to: "apps/voss-app/src/status-bar/notificationStore.ts"
      via: "import { unreadCount, highestUnreadSeverity, markAllRead }"
      pattern: "import.*notificationStore"
    - from: "apps/voss-app/src/status-bar/LeftCluster.tsx"
      to: "apps/voss-app/src/status-bar/RecentProjectsPopover.tsx"
      via: "popover content children"
      pattern: "RecentProjectsPopover"
---

<objective>
StatusBar component tree: root strip, three clusters, three popover content panels.

Purpose: Build the entire visible status bar UI. Three clusters (left: project+branch,
center: focused pane, right: pane count+bell+cog) plus three popover content components
(recent projects, pane detail card, notifications list). Consumes the stores and
Popover component from Plan 02.

Output: 7 component files in `src/status-bar/` plus a StatusBar integration test file.
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
@.planning/phases/A10-voss-app-status-bar/A10-02-SUMMARY.md

<interfaces>
<!-- From Plan 02 outputs -->

From apps/voss-app/src/status-bar/notificationStore.ts:
```typescript
export interface NotificationEntry {
  id: number;
  severity: 'success' | 'warning' | 'error' | 'info';
  message: string;
  source: string;
  timestamp: number;
  read: boolean;
}
export const notifications: NotificationEntry[];
export function addNotification(severity, message, source): void;
export function markAllRead(): void;
export function clearAll(): void;
export function unreadCount(): number;
export function highestUnreadSeverity(): NotificationEntry['severity'] | null;
```

From apps/voss-app/src/status-bar/gitWatcher.ts:
```typescript
export const branch: () => string | null;  // Solid signal accessor
export function watchGitHead(projectPath: string): Promise<void>;
export function stopGitWatch(): void;
```

From apps/voss-app/src/status-bar/Popover.tsx:
```typescript
export default function Popover(props: {
  id: string; anchor: HTMLElement | undefined;
  width: number; maxHeight?: number; children: JSX.Element;
}): JSX.Element;
export function isPopoverOpen(id: string): boolean;
export function openPopover(id: string): void;
export function closePopover(): void;
```

From apps/voss-app/src/grid/tree.ts:
```typescript
export type PaneLeaf = { kind: 'pane'; id: string; cwd: string; shell: string; index: number; };
export function collectLeaves(root: TreeNode): PaneLeaf[];
export function findLeaf(root: TreeNode, id: string): PaneLeaf | undefined;
```

From apps/voss-app/src/project/projectStorage.ts:
```typescript
export type ProjectInfo = { path: string; name: string; gitBranch: string | null; };
export async function listRecents(): Promise<string[]>;
export async function openProject(path: string): Promise<ProjectInfo>;
```

From apps/voss-app/src/components/titlebar/Titlebar.tsx (styling pattern):
```typescript
// 22px height, flex-shrink:0, background var(--bg-0), border-bottom 1px solid var(--border)
// font-size: 11px, font-family var(--font-mono), font-weight 400
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: StatusBar root + three cluster components</name>
  <files>apps/voss-app/src/status-bar/StatusBar.tsx, apps/voss-app/src/status-bar/LeftCluster.tsx, apps/voss-app/src/status-bar/CenterCluster.tsx, apps/voss-app/src/status-bar/RightCluster.tsx</files>
  <read_first>
    - apps/voss-app/src/components/titlebar/Titlebar.tsx (22px height, flex layout, Variant B token styling pattern)
    - apps/voss-app/src/status-bar/Popover.tsx (openPopover, closePopover, isPopoverOpen imports)
    - apps/voss-app/src/status-bar/notificationStore.ts (unreadCount, highestUnreadSeverity, markAllRead imports)
    - apps/voss-app/src/project/projectStorage.ts (ProjectInfo type, listRecents)
    - .planning/phases/A10-voss-app-status-bar/A10-UI-SPEC.md (Layout Contract, Cluster Layout, Glyph inventory, Color, Typography, Named Structural Constants)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (StatusBar.tsx, cluster sections)
  </read_first>
  <action>
    Create four component files mirroring the Titlebar pattern:

    **StatusBar.tsx** — root container, per UI-SPEC Layout Contract:
    - Props: `project: ProjectInfo | null`, `branch: string | null`, `getFocusedLeaf: () => PaneLeaf | null`, `getPaneCount: () => number`, `onOpenProject: (path: string) => void`, `dispatchCommand: (id: string) => boolean`.
    - Outer div: `role="toolbar"`, `display: flex`, `align-items: center`, `height: '22px'`, `flex-shrink: '0'`, `background: 'var(--bg-0)'`, `border-top: '1px solid var(--border)'`, `overflow: 'hidden'`, `position: 'relative'`, `z-index: 10` per UI-SPEC structural constants.
    - Three children: `<LeftCluster>`, `<CenterCluster>`, `<RightCluster>` — pass appropriate props down.
    - Data-testid: `data-testid="status-bar"`.

    **LeftCluster.tsx** — project + branch per BAR-01/BAR-08/D-11:
    - Props: `project: ProjectInfo | null`, `branch: string | null`, `onOpenProject: (path: string) => void`.
    - Flex container: `flex: '1'`, `justify-content: 'flex-start'`, `align-items: 'center'`, `overflow: 'hidden'`.
    - Button element with `aria-label` that describes current state (e.g., "Project: voss, Branch: main. Open recent projects" or "No project. Open recent projects").
    - Label derivation:
      - Project exists + branch exists: `\u25C6 ${project.name} \u00B7 \u2387 ${branch}` (glyphs: diamond, separator dot, branch). Branch text max 32 chars with `text-overflow: ellipsis`.
      - Project exists + branch null (detached): `\u25C6 ${project.name} \u00B7 \u2387 (detached)` — `(detached)` in `--fg-3`.
      - Project exists + no git (branch undefined passed as null, D-11): `\u25C6 ${project.name}` — no branch segment at all.
      - No project (BAR-08): `\u25C6 no project \u00B7 \u2318O to open` in `--fg-2`.
    - Glyph `\u25C6` in `--fg-2`, label text in `--fg-1`, separator `\u00B7` in `--fg-3`.
    - Click: toggle left popover via `isPopoverOpen('left') ? closePopover() : openPopover('left')`.
    - Contains `<Popover id="left" anchor={anchorEl} width={240} maxHeight={320}>` with `<RecentProjectsPopover>` as children.
    - Styling: font 11px, `--font-mono`, weight 400, padding `0 8px`, `background: transparent`, `border: none`, `cursor: pointer`. Hover: `background: 'var(--bg-1)'`. Open state: `background: 'var(--bg-2)'`.
    - Keyboard focus: `box-shadow: inset 0 0 0 1px var(--focus)` per UI-SPEC accessibility.

    **CenterCluster.tsx** — focused pane info per BAR-02:
    - Props: `getFocusedLeaf: () => PaneLeaf | null`.
    - Positioned absolutely centered: `position: 'absolute'`, `left: '50%'`, `transform: 'translateX(-50%)'`, `white-space: 'nowrap'`.
    - Button element with `aria-label` describing pane state.
    - Label: `\u25A2 ${leaf.cwd} \u00B7 ${leaf.shell}` when leaf exists. Use `--fg-2` for glyph, `--fg-1` for text, `--fg-3` for separator.
    - No pane focused: display nothing (empty — center cluster hides when no grid shown).
    - Click: toggle center popover. `<Popover id="center" anchor={anchorEl} width={280}>` with `<PaneDetailPopover>`.
    - Same styling pattern as LeftCluster (11px, mono, hover/open states).

    **RightCluster.tsx** — pane count + bell + cog per BAR-03:
    - Props: `getPaneCount: () => number`, `dispatchCommand: (id: string) => boolean`.
    - Flex container: `justify-content: 'flex-end'`, `align-items: 'center'`, `padding-right: '8px'`.
    - Three items:
      1. **Pane count span** (not clickable): `\u25A2${count}` in `--fg-2` (e.g., `\u25A24`), 11px, `--font-mono`.
      2. **Bell button**: `\uD83D\uDD14` glyph (or fallback `\u25CB`), 28px min-width. Badge: `<Show when={unreadCount() > 0}>` — 16px circle, positioned top-right of bell, `--accent-green` background (or `--accent-red`/`--accent-amber` per `highestUnreadSeverity()`), count text in `--bg-0` at 10px. Show count 1-99, then "99+" for 100+. `aria-label="Notifications, N unread"`. Click: toggle bell popover; on open, call `markAllRead()` per D-06. `<Popover id="bell" anchor={bellRef} width={320} maxHeight={320}>` with `<NotificationsPopover>`.
      3. **Cog button**: `\u2699` glyph, 28px width. `aria-label="Settings"`. Click: `dispatchCommand('open-settings')` per A9. No popover for cog.
    - All buttons: same styling pattern, hover `--bg-1`, focus `box-shadow: inset 0 0 0 1px var(--focus)`.
    - Gap between items: 8px (sm spacing).

    All components use inline `style={{}}` with Variant B token references only. No inline hex values. No border-radius.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - StatusBar.tsx has role="toolbar" and data-testid="status-bar"
    - StatusBar.tsx height is 22px with flex-shrink:0 and border-top: 1px solid var(--border)
    - LeftCluster.tsx renders diamond glyph + project name + branch (or no-project fallback)
    - LeftCluster.tsx hides branch segment entirely when branch prop is null (D-11)
    - LeftCluster.tsx shows "no project" + shortcut hint when project is null (BAR-08)
    - CenterCluster.tsx renders pane cwd + shell from getFocusedLeaf()
    - RightCluster.tsx renders pane count, bell button with conditional badge, cog button
    - Bell badge uses highestUnreadSeverity() to pick accent color
    - Bell popover open calls markAllRead() (D-06)
    - Cog click calls dispatchCommand('open-settings')
    - All styling uses var(--token) references only — no inline hex
    - tsc --noEmit exits 0
  </acceptance_criteria>
  <done>StatusBar root + three clusters render with correct content, glyphs, and popover triggers per UI-SPEC</done>
</task>

<task type="auto">
  <name>Task 2: Three popover content components + StatusBar tests</name>
  <files>apps/voss-app/src/status-bar/RecentProjectsPopover.tsx, apps/voss-app/src/status-bar/PaneDetailPopover.tsx, apps/voss-app/src/status-bar/NotificationsPopover.tsx, apps/voss-app/src/status-bar/__tests__/StatusBar.test.tsx</files>
  <read_first>
    - apps/voss-app/src/status-bar/StatusBar.tsx (props interface, cluster composition)
    - apps/voss-app/src/status-bar/LeftCluster.tsx (RecentProjectsPopover usage)
    - apps/voss-app/src/status-bar/RightCluster.tsx (NotificationsPopover usage, markAllRead call)
    - apps/voss-app/src/status-bar/notificationStore.ts (notifications store, NotificationEntry type, clearAll)
    - apps/voss-app/src/project/projectStorage.ts (listRecents, openProject)
    - .planning/phases/A10-voss-app-status-bar/A10-UI-SPEC.md (Popover Content Specs — all three popover layouts, Copywriting Contract, Notification Store Schema, Bell Badge Contract)
    - .planning/phases/A10-voss-app-status-bar/A10-PATTERNS.md (popover content sections)
  </read_first>
  <action>
    Create three popover content components and one test file:

    **RecentProjectsPopover.tsx** — per D-02 and UI-SPEC Left Popover:
    - Props: `project: ProjectInfo | null`, `onOpenProject: (path: string) => void`.
    - On mount: call `listRecents()` (from `../project/projectStorage`) → store result in local signal.
    - Header row: "Recent Projects" heading, 11px `--font-mono` weight 500, `--fg-2`, `--bg-3`, 24px height, 8px padding.
    - `<For each={recents()}>` rendering rows: 32px height, 8px padding, 12px `--font-mono` `--fg-1`, `\u25C6` prefix in `--fg-2`. Hover `--bg-2`. Active project (matching `props.project?.path`): `--fg-0` text, `--accent-blue` left border 2px, `aria-current="true"`.
    - Row click: call `props.onOpenProject(path)`, then `closePopover()`.
    - Empty state: "No recent projects" centered in `--fg-3` 12px.
    - Role: `role="list"` on list container, `role="listitem"` on each row.

    **PaneDetailPopover.tsx** — per D-03 and UI-SPEC Center Popover:
    - Props: `getLeaf: () => PaneLeaf | null`.
    - Header row: "Pane Detail" heading, same style as RecentProjectsPopover header.
    - Field rows (24px each): label column (52px, right-aligned, 11px `--fg-2`) + value column (12px `--fg-1`, ellipsis overflow).
    - Fields: `cwd:` → `getLeaf()?.cwd`, `shell:` → `getLeaf()?.shell`, `pid:` → show `\u2014` (em dash — PID not available in PaneLeaf per RESEARCH Open Question 1), `index:` → `getLeaf()?.index`, `cmd:` → hidden when no running command (always hidden in L1 since PaneLeaf has no running-command field; use `<Show when={false}>` placeholder).
    - Read fields inside JSX reactive context (NOT destructured outside — Pitfall 5 from RESEARCH).
    - No pane: "No pane focused" centered in `--fg-3` 12px.

    **NotificationsPopover.tsx** — per D-05/D-06 and UI-SPEC Right Popover:
    - No props needed — reads `notifications` directly from `../status-bar/notificationStore`.
    - Header row: "Notifications" heading left, "Clear all" button right. Header: 11px weight 500 `--fg-2`. "Clear all": 11px `--fg-2`, hover `--fg-1`, click calls `clearAll()`.
    - `<For each={notifications}>` rendering rows: 40px height, severity dot `\u25CF` glyph colored per severity (success=`--accent-green`, warning=`--accent-amber`, error=`--accent-red`, info=`--accent-cyan`), message text 12px (unread `--fg-0`, read `--fg-2`), relative timestamp 11px `--fg-3` below message.
    - Relative timestamp helper: inline function. < 60s: "just now". < 3600s: `N minute(s) ago`. < 86400s: `N hour(s) ago`. Else: month+day string (e.g., "May 19"). Use singular/plural correctly.
    - Row separator: `border-bottom: '1px solid var(--border)'`.
    - Empty state: "No notifications" centered in `--fg-3` 12px.
    - Role: `role="list"`, `role="listitem"`, `aria-live="polite"` on container.

    **StatusBar.test.tsx** — integration-level tests for the assembled bar:
    - Mock Tauri APIs (invoke, listen, getCurrentWindow) via vi.hoisted pattern.
    - Mock `../project/projectStorage` listRecents.
    - Tests: StatusBar renders with data-testid "status-bar"; left cluster shows project name and branch; left cluster shows "no project" fallback when project is null (BAR-08); branch hidden when branch is null (D-11); center cluster shows cwd and shell from focused leaf; right cluster shows pane count; bell badge visible when unread > 0; bell badge hidden when unread = 0; cog button calls dispatchCommand with 'open-settings'.
    - beforeEach: reset notification store, reset popover state, reset mocks.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/status-bar/__tests__/StatusBar.test.tsx 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - RecentProjectsPopover.tsx calls listRecents() on mount and renders rows with role="list"
    - RecentProjectsPopover.tsx active project row has aria-current="true" and --accent-blue left border
    - RecentProjectsPopover.tsx empty state shows "No recent projects"
    - PaneDetailPopover.tsx reads leaf fields inside JSX (not destructured outside)
    - PaneDetailPopover.tsx shows "No pane focused" when getLeaf returns null
    - PaneDetailPopover.tsx pid field shows em dash (PID not available)
    - NotificationsPopover.tsx reads notifications from notificationStore
    - NotificationsPopover.tsx "Clear all" calls clearAll()
    - NotificationsPopover.tsx relative timestamp: "just now" for <60s
    - NotificationsPopover.tsx empty state shows "No notifications"
    - StatusBar.test.tsx has at least 6 passing tests covering BAR-01, BAR-03, BAR-05, BAR-08
    - tsc --noEmit exits 0
  </acceptance_criteria>
  <done>Three popover content panels render per UI-SPEC with correct styling and behavior; StatusBar integration tests verify cluster content and popover triggers</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| listRecents() → UI | User filesystem paths rendered in popover |
| notification messages → DOM | Event messages rendered as text nodes |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A10-08 | Spoofing | RecentProjectsPopover | accept | Paths come from Rust open_project (already validated by A5); Solid JSX auto-escapes |
| T-A10-09 | Spoofing | NotificationsPopover | mitigate | Messages already capped at 120 chars by addNotification; Solid JSX auto-escapes (no innerHTML) |
| T-A10-10 | Information Disclosure | PaneDetailPopover | accept | Shows cwd/shell/index of user's own pane — no cross-user risk |
| T-A10-SC | Tampering | npm/pip/cargo installs | accept | No new dependencies |
</threat_model>

<verification>
```bash
# Component tests
cd apps/voss-app && pnpm vitest run src/status-bar/__tests__/StatusBar.test.tsx

# All status-bar tests so far
cd apps/voss-app && pnpm vitest run src/status-bar/

# Type check
cd apps/voss-app && npx tsc --noEmit
```
</verification>

<success_criteria>
- 7 component files exist in src/status-bar/
- StatusBar.test.tsx passes with at least 6 tests
- All prior Plan 02 tests still pass (no regression)
- tsc --noEmit exits 0
- All text uses Variant B tokens only
</success_criteria>

<output>
Create `.planning/phases/A10-voss-app-status-bar/A10-03-SUMMARY.md` when done
</output>
