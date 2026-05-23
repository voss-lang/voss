# Phase A12: voss-app ADE Visual Redesign — Research

**Researched:** 2026-05-22
**Domain:** SolidJS UI composition, Tauri IPC, CSS theme catalog, agent detection integration
**Confidence:** HIGH

---

## Summary

A12 transforms voss-app from a functional terminal multiplexer into a visually coherent Agent Development Environment. The technical work divides cleanly into three categories: (1) CSS token replacement and theme catalog extension, (2) new SolidJS component tree (sidebar, modal, file tree), and (3) thin wiring into existing data signals (agentConfigByPaneId, contextByPaneId, procByPaneId). Crucially, all data required for the sidebar already exists as reactive SolidJS signals — the sidebar is a new consumer, not a new data source.

The most significant technical risk is Poppins font loading. The current Tauri CSP (`style-src 'self' 'unsafe-inline'`) explicitly blocks external font sources. Google Fonts cannot be used as specified in ADE-REDESIGN.md. Poppins must be downloaded and bundled locally as `public/fonts/`. This is a blocking constraint that affects ADE-01 and ADE-05.

The second notable gap is `focusPaneById` — this method does not exist in `GridController`. The bidirectional focus sync (D-22) requires adding it to the controller interface in `GridRoot.tsx` and wiring it through `operations.ts`. Similarly, `BudgetState` (cost data) is pane-local and has no shared registry; a `budgetByPaneId` registry module mirroring `procRegistry.ts` must be created for the sidebar's live cost display and the status bar badge.

The "Voss Ignite" theme is a new bundled JSON entry — the existing `themeCatalog.ts` pattern (import JSON, register in `BUNDLED_BY_ID`) is the exact mechanism. The theme's `cssVars` object must supply all 27 keys in `REQUIRED_CSS_VARS` (verified from `schema.ts`) plus the new tokens (`--focus-soft`, `--focus-hover`, `--role-*`, `--font-display`, `--sidebar-w`). New tokens live in the JSON only; `schema.ts` does not enforce them.

File tree and git log both require new Tauri backend commands — no `list_dir` or `git_log` commands exist in `src-tauri/src/lib.rs`.

**Primary recommendation:** Execute ADE-01 (theme + font bundling) first. All other plans depend on the warm token palette. After ADE-01, P2/P3 (sidebar component + layout integration) are the critical path. P4–P8 parallelize after P3.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Sidebar Scope & Sections**
- D-01: Sidebar has 4 sections in order: Agents → Sessions → Files → Git. No Quick Launch section in sidebar body.
- D-02: `+ Agent` button lives in the sidebar header (top-right, next to collapse chevron). Opens the agent launch modal.
- D-03: Sidebar is visible by default on app launch. Users collapse via `⌘⇧B`.
- D-04: Fixed width 280px. No user-resizable drag.
- D-05: Files section is read-only directory tree — expand/collapse dirs, see file names. Click does nothing (future: open in editor pane).
- D-06: Sessions section tracks agent session start/stop/complete — separate from Git section which shows recent commits.
- D-07: ContextPanel (right-side overlay, `⌘I`) coexists with sidebar. Two panels, two purposes.
- D-08: Sidebar Agents section shows only detected agent CLIs — regular shell panes do not appear.

**Theme Migration**
- D-09: Create new theme "Voss Ignite" as a catalog entry in existing theme system. Set as default. Variant B preserved as fallback theme.
- D-10: Full chrome + terminal retheme — xterm.js foreground/background/cursor/ANSI palette all warm-shifted.
- D-11: Selective rounding — 0 radius on panes/grid/panels. Small radius (3-6px) on interactive elements. Cards get 6px.
- D-12: Poppins for display headings only. Inter stays for UI labels/buttons. JetBrains Mono for terminal + code.
- D-13: Warm palette tokens: bg `#0b0a09→#131110→#1a1714→#221f1b`, fg `#f5f1ea→#c4beb5→#8a847a→#5a554d`, accent `#ff5b1f`, border `#1d1a16`/`#2e2924`.

**Agent Launch UX**
- D-14: `+ Agent` button opens a centered modal overlay. Dismiss with Escape.
- D-15: Modal offers 6 CLI presets: Claude, Codex, Antigravity (Gemini), OpenCode, Voss, Custom.
- D-16: Context-sensitive config panels — generic (model selector, effort, plan mode, skip permissions, task prompt) vs Voss-specific (chat/do/resume/skill/agent, mode, auth, task prompt).
- D-17: Full config modal scope in A12 — not deferred.
- D-18: Task prompt field optional. Empty = interactive mode.
- D-19: Agent spawns by splitting from the currently focused pane (horizontal split).
- D-20: Modal accessible via `+ Agent` button only — not via `⌘K` palette.
- D-21: Custom CLI entry persisted in settings.

**Sidebar ↔ Grid Interaction**
- D-22: Bidirectional focus sync — click agent in sidebar focuses its pane; focusing pane highlights agent in sidebar.
- D-23: Right-click context menu on agent items: Stop, Restart, Detach, Copy cost, Focus pane.
- D-24: Live cost/token display in agent rows — updates reactively from OSC telemetry, no polling.
- D-25: Drag to reorder agents in sidebar list. Visual preference only.

**Status Bar Agent Badge**
- D-26: Orange pill on right side of status bar: `● 3 agents · $1.42`. Count + total cost, live-updating.
- D-27: Clicking badge toggles sidebar open/closed. Secondary entry point.

**Titlebar Branding**
- D-28: Voss logo mark (18-20px inline SVG, `#ff5b1f` fill) placed left of project name. Layout: traffic lights → gap → logo → project name → preset switcher.
- D-29: Project name rendered in Poppins 500 (was monospace). Other titlebar elements stay Inter/mono.

**Animation & Transitions**
- D-30: Subtle and fast motion. Sidebar: 200ms slide. Modal: 150ms fade+scale. Pane focus: 100ms border. Agent streaming: pulsing dot. All respect `prefers-reduced-motion`.

### Claude's Discretion
- Exact ANSI color remapping for xterm warm palette (within the warm family, specific hue choices)
- Agent session tracking data structure (what persists, format)
- File tree implementation details (recursive readdir depth limits, debounce)
- Context menu positioning and dismissal behavior
- Drag-to-reorder implementation (SolidJS-compatible library or custom)

### Deferred Ideas (OUT OF SCOPE)
- Warp-style theme picker UI with card previews, filter tabs, search — belongs in A9 or new phase.
- File tree click-to-open — clicking a file opens it in an editor pane. Future phase.
- Agent session persistence — saving/restoring agent sessions across app restart. Depends on F1.
- Pane chrome accent bars — documented in ADE-REDESIGN.md Phase 6 but may split as separate plan.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ADE-01 | Theme migration: replace cool blue-gray token palette with warm site-aligned palette. All CSS vars, no raw hex. Font loading for Poppins. | New `voss-ignite.json` bundled theme + font bundling (CSP constraint requires local fonts). |
| ADE-02 | AgentSidebar component: collapsible left panel (280px), 2px orange left accent, sections for Agents/Sessions/Files/Git. Animates open/close. | Existing SolidJS patterns from WorkspaceTabBar/ContextPanel. New `AgentSidebar.tsx` + `sidebar.css`. |
| ADE-03 | Layout integration: sidebar sits outside grid tree in flex row. Grid resizes via ResizeObserver. `⌘⇧B` toggle. Sidebar state persists in localStorage. | App.tsx layout insertion point verified. `⌘⇧B` safe (does not conflict with existing bindings). |
| ADE-04 | Agent launch flow: modal with 6 CLI presets spawns agents in new panes. Agent detection updates sidebar reactively. | New `AgentLaunchModal.tsx`. Existing `spawn_agent` Tauri command. `agentConfigByPaneId` signal for detection. |
| ADE-05 | Titlebar + branding: Voss logo mark (20px SVG), Poppins display font for app name. Status bar orange agent count badge. | `Titlebar.tsx` + `StatusBar.tsx` modification points verified. Logo SVG available at `site/public/logo.svg`. |
| ADE-06 | Pane chrome warmth: 3px left accent bars in role color on agent pane headers. Focused agent pane gets orange edge + focus-soft bg. Streaming pulse animation. | `PaneHeader.tsx` + `index.css` `.grid-pane-leaf--focused` modification points verified. |
| ADE-07 | File tree: basic recursive directory listing from project root via Tauri FS. Expand/collapse, scroll within section. | No existing `list_dir` command — new Tauri command needed in `src-tauri/src/lib.rs`. |
| ADE-08 | History/sessions: git log entries with relative timestamps in sidebar History section. Updates on focus. | No existing `git_log` command — new Tauri command needed. Sessions section requires new `budgetByPaneId`-style registry or App.tsx derived signal. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Theme token application | Frontend (CSS vars injected via themeRuntime.ts) | — | Pattern already in `applyThemeOverrides()` |
| xterm.js ANSI warm palette | Frontend (themeRuntime.ts themeToXtermTheme) | — | All 16 ANSI values set via `terminal.options.theme` |
| Poppins font loading | Frontend (public/fonts + @font-face in index.css) | — | CSP blocks Google Fonts; must be local |
| Sidebar collapsed state | Frontend (localStorage + createSignal in App.tsx) | — | Same pattern as `contextPanelOpen` |
| Agent list for sidebar | Frontend (derived from agentConfigByPaneId + procByPaneId) | Tauri backend (get_active_agents) | Signal already exists in App.tsx |
| Live cost display in sidebar | Frontend (new budgetByPaneId module) | — | Mirrors procRegistry.ts pattern |
| Bidirectional focus sync | Frontend (focusedPaneId signal in App.tsx) | GridController (focusPaneById — new method) | No polling, pure reactive |
| File tree listing | Tauri backend (new list_dir command) | Frontend (FileTree.tsx component) | Filesystem access requires Rust layer |
| Git log for history | Tauri backend (new git_log command) | Frontend (Sessions.tsx component) | Shell command execution in Rust |
| Agent spawn from modal | Tauri backend (existing spawn_agent command) | Frontend (split + spawn flow) | spawn_agent already handles PTY + registry |
| Context menu for agents | Frontend (Popover.tsx, existing component) | — | DotMenu.tsx + Popover.tsx already in grid/ |
| Drag-to-reorder agents | Frontend (HTML5 Drag API — same as WorkspaceTabBar) | — | Visual only, no backend |

---

## Standard Stack

No new packages are installed in A12. The entire phase is CSS + SolidJS components within the existing stack.

### Core (existing, unchanged)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| solid-js | 1.9.13 | Reactive UI framework | createSignal, createMemo, For, Show |
| @tauri-apps/api | 2.11.0 | Tauri IPC invoke() | All backend calls |
| @xterm/xterm | 5.5.0 | Terminal emulator | Theme applied via terminal.options.theme |
| tailwindcss | 4.3.0 | CSS utilities | Used sparingly via @theme inline |

### New Assets (bundled, no npm install)
| Asset | Source | Usage |
|-------|--------|-------|
| Poppins 500 woff2 | Google Fonts static download | Display headings — must be local per CSP |
| Poppins 600 woff2 | Google Fonts static download | Section headings + modal title |
| Voss logo SVG | `site/public/logo.svg` (2 paths, #ff5b1f fill) | Inline in Titlebar + sidebar header |

**Installation:** No `npm install` required. Poppins font files must be downloaded from Google Fonts (static URL: `https://fonts.gstatic.com/s/poppins/...`) and placed at `apps/voss-app/public/fonts/poppins-500.woff2` and `apps/voss-app/public/fonts/poppins-600.woff2`.

---

## Package Legitimacy Audit

> **Not applicable.** Phase A12 installs zero new npm packages. All work is CSS and SolidJS component authoring within the existing dependency set.

---

## Architecture Patterns

### System Architecture Diagram

```
App.tsx
├── Titlebar (modified)
│   └── [logo SVG] + [Poppins project name]
├── WorkspaceTabBar (unchanged)
├── [flex row: sidebar + content]
│   ├── AgentSidebar (NEW)
│   │   ├── header: logo, + Agent button, collapse chevron
│   │   ├── AGENTS section ← agentConfigByPaneId() + budgetByPaneId()
│   │   ├── SESSIONS section ← sessionLog signal (app-level)
│   │   ├── FILES section ← invoke('list_dir') FileTree
│   │   └── GIT section ← invoke('git_log') commits
│   └── [workspace content]
│       ├── GridRoot (unchanged — fills flex: 1)
│       └── ContextPanel (unchanged — overlay, coexists)
├── StatusBar (modified)
│   └── [agent badge pill] ← agentConfigByPaneId() + budgetByPaneId()
├── AgentLaunchModal (NEW, conditional)
│   ├── CLI tabs (Claude/Codex/Antigravity/OpenCode/Voss/Custom)
│   ├── GenericAgentPanel / VossAgentPanel / CustomPanel
│   └── footer: Ctrl+Enter hint + Launch Agent button
└── [existing: CommandPalette, ToastStack, NewWorkspacePicker]
```

Data flows:
- `agentConfigByPaneId` (MountedWorkspace) → AgentSidebar + StatusBar badge
- `budgetByPaneId` (NEW module, written by PaneComponent) → AgentSidebar cost display + StatusBar total
- `focusedPaneId` (App.tsx signal) → AgentSidebar active highlight
- `gridController().focusPaneById(paneId)` (NEW method) → grid focus on sidebar click
- Tauri `list_dir(path)` → FileTree
- Tauri `git_log(path, limit)` → Git section

### Recommended Project Structure

```
apps/voss-app/
├── public/
│   └── fonts/
│       ├── poppins-500.woff2          # NEW (downloaded from Google Fonts)
│       └── poppins-600.woff2          # NEW
├── src/
│   ├── styles/
│   │   └── variant-b.css              # PRESERVED (renamed theme, kept as-is)
│   ├── themes/
│   │   └── bundled/
│   │       └── voss-ignite.json       # NEW
│   ├── components/
│   │   ├── sidebar/                   # NEW DIRECTORY
│   │   │   ├── AgentSidebar.tsx
│   │   │   ├── AgentItem.tsx
│   │   │   ├── FileTree.tsx
│   │   │   ├── GitSection.tsx
│   │   │   ├── SessionsSection.tsx
│   │   │   └── sidebar.css
│   │   ├── modal/                     # NEW DIRECTORY
│   │   │   ├── AgentLaunchModal.tsx
│   │   │   └── modal.css
│   │   ├── StatusBar.tsx              # MODIFIED
│   │   └── titlebar/
│   │       └── Titlebar.tsx           # MODIFIED
│   ├── pane/
│   │   └── budgetRegistry.ts          # NEW (mirrors procRegistry.ts)
│   ├── grid/
│   │   ├── GridRoot.tsx               # MODIFIED (add focusPaneById to GridController)
│   │   ├── PaneHeader.tsx             # MODIFIED (accent bar, streaming dot)
│   │   └── operations.ts              # MODIFIED (focusPaneById implementation)
│   └── index.css                      # MODIFIED (@font-face for Poppins, new role vars)
└── src-tauri/src/
    └── lib.rs                         # MODIFIED (new list_dir + git_log commands)
```

---

## Critical Technical Findings

### Finding 1: CSP Blocks Google Fonts — Poppins Must Be Local

**Status: BLOCKING for ADE-01 and ADE-05**

The Tauri app's Content Security Policy in `tauri.conf.json` is:

```
default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;
script-src 'self'; connect-src 'self' ipc: http://ipc.localhost
```

`fonts.googleapis.com` and `fonts.gstatic.com` are not in any allowlist. Any `<link>` to Google Fonts or any CSS `@import url('https://fonts.googleapis.com/...')` will be silently blocked by the webview.

**Resolution:** Download Poppins 500 and 600 woff2 files from Google Fonts static CDN and bundle them at `apps/voss-app/public/fonts/`. Add `@font-face` declarations to `src/index.css`. No CSP change needed.

```css
/* src/index.css — add after existing @import */
@font-face {
  font-family: 'Poppins';
  font-style: normal;
  font-weight: 500;
  src: url('/fonts/poppins-500.woff2') format('woff2');
  font-display: swap;
}
@font-face {
  font-family: 'Poppins';
  font-style: normal;
  font-weight: 600;
  src: url('/fonts/poppins-600.woff2') format('woff2');
  font-display: swap;
}
```

The ADE-REDESIGN.md references a Google Fonts `<link>` tag in `index.html` — that approach is blocked. Use local fonts instead.

---

### Finding 2: focusPaneById Does Not Exist in GridController

**Status: BLOCKING for D-22 (bidirectional focus sync)**

The `GridController` interface in `GridRoot.tsx` (lines 95–112) does not include `focusPaneById`. The ADE-REDESIGN.md references `gridController()?.focusPaneById(paneId)` in its App.tsx example code, but this call would currently fail silently.

The grid's `focus.ts` module already has `focusByIndex(store, n)` and `focusByDirection()`. The planner must add:

1. `focusPaneById(paneId: string) => void` to the `GridController` type in `GridRoot.tsx`
2. An implementation in `GridRoot.tsx` that walks the tree, finds the leaf with matching id, and sets `store.focusedId`
3. Expose it through the `controllerRef` callback

The `tree.ts` `collectLeaves()` function already exists and returns `PaneLeaf[]` with `id` fields — use it to find the target leaf.

---

### Finding 3: No budgetByPaneId Registry — Sidebar Has No Cost Source

**Status: BLOCKING for D-24 and D-26**

`BudgetState` (containing `cost_usd`) is currently a pane-local `createSignal` inside `PaneComponent.tsx` (line 100). There is no shared registry like `procByPaneId` or `contextByPaneId` for budget/cost data.

The sidebar's agent cost display (D-24) and the status bar badge total cost (D-26) both need live cost per pane. The solution is a new `budgetRegistry.ts` module mirroring `procRegistry.ts`:

```typescript
// src/pane/budgetRegistry.ts
import { createSignal } from 'solid-js';
import type { BudgetState } from './pty-ipc';

const [budgetByPaneId, setBudgetByPaneId] = createSignal<Record<string, BudgetState>>({});

export function registerPaneBudget(paneId: string, data: BudgetState): void {
  setBudgetByPaneId((prev) => ({ ...prev, [paneId]: data }));
}

export function unregisterPaneBudget(paneId: string): void {
  setBudgetByPaneId((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { budgetByPaneId };
```

`PaneComponent.tsx` calls `registerPaneBudget` in its `onBudgetUpdate` callback and `unregisterPaneBudget` in `onCleanup`. The sidebar and status bar read from `budgetByPaneId()` reactively.

---

### Finding 4: No list_dir or git_log Tauri Commands

**Status: BLOCKING for ADE-07 and ADE-08**

The Tauri backend (`src-tauri/src/lib.rs`) has no file listing or git commands. The registered command set ends with `write_context_pins`. For the file tree (ADE-07) and git log (ADE-08), two new Tauri commands must be added:

```rust
#[tauri::command]
fn list_dir(path: String) -> Result<Vec<DirEntry>, String>

#[derive(Debug, Serialize)]
struct DirEntry {
    name: String,
    is_dir: bool,
    children: Vec<DirEntry>,  // populated only for depth <= 2
}

#[tauri::command]
fn git_log(workspace_path: String, limit: usize) -> Result<Vec<GitCommit>, String>

#[derive(Debug, Serialize)]
struct GitCommit {
    hash: String,
    message: String,
    timestamp_secs: i64,  // Unix timestamp for relative formatting
}
```

`git_log` runs `git log --oneline -N --format="%H %ct %s"` via `std::process::Command`. Returns empty vec on non-git directories (graceful). The frontend formats relative timestamps in JS.

The Tauri capability file (`capabilities/default.json`) does not need modification — filesystem access via `std::fs` in the Rust backend is always permitted.

---

### Finding 5: Voss Ignite Theme — Extra Tokens Not in REQUIRED_CSS_VARS

The `schema.ts` `REQUIRED_CSS_VARS` array (27 vars, verified) does not include the new A12 tokens (`--focus-soft`, `--focus-hover`, `--role-planner`, `--role-executor`, `--role-reviewer`, `--role-watcher`, `--role-user`, `--font-display`, `--sidebar-w`, `--titlebar-height`). Schema validation in `validateTheme()` only checks the 27 required vars — new tokens pass silently.

The Voss Ignite JSON theme must supply all 27 required vars. The new tokens are added to `index.css` or `voss-ignite.json` cssVars for global CSS variable injection (via `applyThemeOverrides()` in `themeRuntime.ts`). They should go in the JSON so `applyThemeOverrides()` injects them at theme activation time.

The existing theme-switching infrastructure in `themeRuntime.ts` handles everything — `applyThemeOverrides()` injects all cssVars from the theme file, including non-required ones.

---

### Finding 6: Titlebar Height Must Increase (22px → 38px)

The current `--titlebar-height: 22px` is set in `variant-b.css`. The "Voss Ignite" theme uses 38px to accommodate the Poppins logo + project name. The Voss Ignite JSON should include `"--titlebar-height": "38px"` in cssVars, which will override the CSS variable for that theme.

However, `--titlebar-height` is NOT in `REQUIRED_CSS_VARS` in `schema.ts` — it's only in `variant-b.css`. If the theme JSON sets it, `applyThemeOverrides()` will inject it. If not, the old 22px value persists. The executor must ensure `--titlebar-height` is included in the Ignite theme cssVars.

Similarly, `--pane-header-height` will increase from 22px to 28px for the accent bar space. This is set via the theme or `index.css`.

---

### Finding 7: Drag-to-Reorder Pattern Already in Codebase

WorkspaceTabBar implements drag-to-reorder using the HTML5 Drag API (`draggable`, `onDragStart`, `onDragOver`, `onDrop` attributes). This is the established pattern in this codebase — no external library needed. The sidebar agent drag-to-reorder (D-25) should follow the same approach.

```typescript
// Pattern from WorkspaceTabBar.tsx (lines 170–188)
const onDragStart = (index: number, e: DragEvent) => {
  e.dataTransfer?.setData('text/plain', String(index));
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
};
const onDragOver = (e: DragEvent) => {
  e.preventDefault();
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
};
const onDrop = (toIndex: number, e: DragEvent) => {
  e.preventDefault();
  const from = Number(e.dataTransfer?.getData('text/plain'));
  if (!Number.isNaN(from) && from !== toIndex) {
    reorderAgents(from, toIndex);
  }
};
```

Reorder is visual-only (D-25) — agent order is a local `createSignal<string[]>` of paneIds. It does not persist across restarts and does not affect the grid layout.

---

### Finding 8: prefers-reduced-motion Already Handled Globally

`index.css` already applies `transition: none !important; animation: none !important` for `@media (prefers-reduced-motion: reduce)` and `html.reduced-motion`. All new CSS animations and transitions in A12 inherit this kill switch automatically — no per-component handling needed. The streaming pulse dot animation, sidebar slide, and modal transitions are all covered.

---

### Finding 9: Voss CLI Cmd Enum — Actual vs. Spec

The Voss CLI `Cmd` enum in `crates/voss-cli/src/lib.rs` has:
- `Chat` (default, no subcommand)
- `Do { task, mode, yes, auth }`
- `Agent { cmd: AgentCmd::Spawn { id, task, auth, mode } }`
- `Skill { cmd: SkillCmd::Run { id, args } }`
- `Resume { id }`
- `Sessions`, `Plugins`, `Plugin`, `Skills`, `Agents`

The CONTEXT D-16 Voss-specific config panel lists: command (chat/do/resume/skill/agent), mode (edit/plan), auth choice. This maps correctly to the actual CLI surface. The modal's Voss tab should expose `chat`, `do`, `agent spawn`, and `resume` — `Sessions`, `Plugins`, `Skills` are listing commands and don't take user tasks.

---

### Finding 10: Index.css global border-radius: 0 Conflict

`index.css` line ~42 sets:
```css
*, *::before, *::after {
  border-radius: 0;
}
```

This global reset will fight the A12 design's 3px and 6px radii on buttons, badges, and pills. All new A12 components using non-zero radius must set `border-radius` explicitly in inline styles or CSS modules (which they override the global via specificity). This is the existing pattern — `StatusBar.tsx` already uses inline `border-radius: '3px'` on the Ctx button.

---

### Finding 11: Agent Streaming State — PaneComponent Owns It

Currently, whether an agent is "streaming" is determined by whether `budget?.()` has a recent update. There is no shared "is-streaming" registry. For the pulsing dot animation in PaneHeader and the sidebar agent status, a `streamingByPaneId` signal or approach must be designed. Options:

1. Add a `streamingByPaneId` registry (like procRegistry) updated by PaneComponent on each budget_update event, reset after a timeout
2. Derive streaming state from the recency of the last budget update in the budgetByPaneId registry (timestamp comparison)
3. Use procByPaneId — if the agent CLI is the foreground process, it is likely streaming

Option 2 (derive from budget recency) is cleanest for the sidebar cost display, since budgetByPaneId is already being created. Add a `lastUpdateMs` field to the budget registry entry. Streaming = `Date.now() - lastUpdateMs < 5000`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sidebar animation | Manual JS animation | CSS `width` transition (200ms) | Already in established pattern; ResizeObserver handles grid reflow |
| Agent reorder | Custom drag library | HTML5 DragEvent API | WorkspaceTabBar already uses it; no new dep |
| Context menu | Custom popover logic | `Popover.tsx` (already in grid/) | Full-featured popover with click-outside dismiss |
| Modal overlay | Custom focus trap | Same pattern as CommandPalette.tsx | `role="dialog"`, `aria-modal="true"`, backdrop onClick dismiss |
| Relative timestamps | moment.js / date-fns | Inline JS Intl.RelativeTimeFormat | No new package; built-in browser API |
| WCAG contrast check | Custom tool | `contrastRatio()` from schema.ts | Already exported, already used in codebase |

---

## Common Pitfalls

### Pitfall 1: Google Fonts Blocked by CSP

**What goes wrong:** Developer adds `<link href="https://fonts.googleapis.com/...">` to `index.html` or `@import url(...)` in CSS. Poppins silently falls back to system-ui. Project name looks wrong; no error shown.

**Why it happens:** Tauri's CSP does not include `fonts.googleapis.com` or `fonts.gstatic.com`. The webview blocks the request without console errors visible during Tauri dev mode.

**How to avoid:** Bundle Poppins as `public/fonts/*.woff2` + `@font-face` in `index.css`. Never add external font URLs.

**Warning signs:** Titlebar project name renders in system-ui sans instead of the geometric Poppins.

---

### Pitfall 2: Border-radius Global Reset Fights Component Styles

**What goes wrong:** Buttons, badges, pills all render with 0px radius despite component code specifying `border-radius: 3px`. Design looks like old Variant B.

**Why it happens:** `index.css` sets `*, *::before, *::after { border-radius: 0; }` — a very high-specificity override that beats class-level rules unless inline styles or `!important` is used.

**How to avoid:** Use inline styles for border-radius on all new A12 interactive elements (same as existing StatusBar.tsx Ctx button pattern). Do not rely on CSS class specificity to override the global reset.

**Warning signs:** All buttons look square even after applying `border-radius: 3px` in a `.css` file.

---

### Pitfall 3: sidebar-w CSS Variable Missing When ContextPanel is Open

**What goes wrong:** When ContextPanel opens on the right and sidebar is open on the left, the grid is constrained from both sides. If `--sidebar-w` is not properly referenced in the flex layout, the grid overflows or the sidebar clips.

**Why it happens:** The layout in App.tsx uses a flex row. If sidebar width is hardcoded or the flex calculation doesn't account for ContextPanel's absolute positioning, columns fight.

**How to avoid:** ContextPanel uses `position: absolute; right: 0` (it's an overlay, per D-07 — both coexist). The sidebar is in the flex row. GridRoot fills `flex: 1` and has ResizeObserver. The two do not mathematically conflict — ContextPanel overlays on top of the grid area, it does not shrink it. Verify ContextPanel uses `position: absolute` not a flex child.

---

### Pitfall 4: agentConfigByPaneId Shows Wrong Agents in Sidebar

**What goes wrong:** Regular shell panes appear in the sidebar Agents section alongside Claude/Codex/etc.

**Why it happens:** `agentConfigByPaneId` is populated by `get_active_agents` from the SQLite registry. The registry only contains agent-spawned panes (via `spawn_agent` command). Shell panes spawned via `spawn_pty` are NOT in this registry.

**How to avoid:** Filter `agentConfigByPaneId` entries by checking `isKnownAgentCli(entry.cliBinary)` from `agentDetect.ts` before showing in the sidebar. This is D-08.

---

### Pitfall 5: focusPaneById Not in GridController — Silent No-op

**What goes wrong:** Clicking an agent in the sidebar does nothing. No error.

**Why it happens:** The ADE-REDESIGN.md code example calls `gridController()?.focusPaneById(paneId)` but this method does not exist — TypeScript optional chaining `?.` silently swallows the missing method call.

**How to avoid:** Add `focusPaneById` to the `GridController` type AND implement it before writing the sidebar click handler. Verify with a TypeScript build before testing in-app.

---

### Pitfall 6: Titlebar Height Change Breaks Existing Tests

**What goes wrong:** Titlebar snapshot tests or dimension tests that expect 22px fail after height changes to 38px.

**Why it happens:** `variant-b.css` hardcodes `--titlebar-height: 22px`. The Voss Ignite theme overrides this to 38px. Any test that boots with Variant B (the default in tests) will see 22px. Tests specifically testing Ignite will see 38px.

**How to avoid:** Check existing `Titlebar.test.tsx` for any hardcoded height expectations. Update them if they assert 22px. The theme-aware height is set via the CSS variable — tests that don't apply Ignite will still test at 22px (correct for Variant B).

---

### Pitfall 7: Streaming Detection Needs Explicit Design

**What goes wrong:** Pulsing dot animation either never stops (always "streaming") or never starts (always shows static dot) because the streaming state source is ambiguous.

**Why it happens:** There is no `isStreaming` field in the agent registry. The budget registry only records the last known cost.

**How to avoid:** Add `lastSeenMs: number` to the `budgetRegistry.ts` entry. Update it on every `budget_update` event. Consider streaming if `Date.now() - lastSeenMs < 3000` — Claude/Codex typically emit budget updates every few seconds during active use. The PaneHeader's dot and the sidebar dot both read from this calculation.

---

## Code Examples

### Theme JSON Structure (voss-ignite.json)

```json
{
  "id": "voss-ignite",
  "name": "Voss Ignite",
  "appearance": "dark",
  "cssVars": {
    "--bg-0": "#0b0a09",
    "--bg-1": "#131110",
    "--bg-2": "#1a1714",
    "--bg-3": "#221f1b",
    "--fg-0": "#f5f1ea",
    "--fg-1": "#c4beb5",
    "--fg-2": "#8a847a",
    "--fg-3": "#5a554d",
    "--border": "#1d1a16",
    "--border-bright": "#2e2924",
    "--focus": "#ff5b1f",
    "--focus-glow": "rgba(255,91,31,0.18)",
    "--focus-soft": "rgba(255,91,31,0.14)",
    "--focus-hover": "#ff7a47",
    "--accent-green": "#5ec26a",
    "--accent-amber": "#e8b86c",
    "--accent-red": "#e87b7b",
    "--accent-cyan": "#6cc7d4",
    "--accent-magenta": "#c084d4",
    "--accent-blue": "#7aa2ff",
    "--role-planner": "#ff5b1f",
    "--role-executor": "#6cc7d4",
    "--role-reviewer": "#e8b86c",
    "--role-watcher": "#8a847a",
    "--role-user": "#5ec26a",
    "--font-display": "\"Poppins\", system-ui, sans-serif",
    "--sidebar-w": "280px",
    "--titlebar-height": "38px",
    "--workspace-neutral": "#8a847a",
    "--workspace-red": "#e87b7b",
    "--workspace-orange": "#ff7a47",
    "--workspace-green": "#5ec26a",
    "--workspace-yellow": "#e8b86c",
    "--workspace-cyan": "#6cc7d4",
    "--workspace-blue": "#7aa2ff",
    "--workspace-purple": "#c084d4",
    "--window-opacity-bg": "rgba(11,10,9,0.88)"
  },
  "ansi": [
    "#1a1714", "#e87b7b", "#5ec26a", "#e8b86c",
    "#7aa2ff", "#c084d4", "#6cc7d4", "#c4beb5",
    "#5a554d", "#ff7070", "#7ad68a", "#f0c87c",
    "#99b8ff", "#d49ae4", "#8ad4de", "#f5f1ea"
  ],
  "cursor": "#ff5b1f",
  "cursorText": "#0b0a09",
  "selection": "rgba(255,91,31,0.25)"
}
```

Verification: 27 REQUIRED_CSS_VARS satisfied (checked against schema.ts). `ansi` is 16 hex values. `cursor`, `cursorText`, `selection` are optional extras.

---

### themeCatalog.ts Integration Pattern

```typescript
// src/themes/themeCatalog.ts — add these lines:
import vossIgnite from './bundled/voss-ignite.json';

// Add to BUNDLED_THEME_IDS array:
'voss-ignite',

// Add to BUNDLED_BY_ID:
'voss-ignite': vossIgnite as Theme,
```

`themeRuntime.ts` sets `DEFAULT_THEME = getBundledTheme('variant-b')!` on line 11. To make Ignite the default, change to `'voss-ignite'`. The `load_active_theme_id` Tauri command reads from settings.json — if null, the in-code default applies.

---

### Sidebar Collapsed State Pattern (matches contextPanelOpen)

```typescript
// App.tsx — add alongside contextPanelOpen:
const [sidebarCollapsed, setSidebarCollapsed] = createSignal(
  localStorage.getItem('voss:sidebarCollapsed') === 'true'
  // D-03: visible by default → falsy default is correct
);
const toggleSidebar = () => {
  setSidebarCollapsed((prev) => {
    const next = !prev;
    localStorage.setItem('voss:sidebarCollapsed', String(next));
    return next;
  });
};
```

---

### Agent List Derivation for Sidebar

```typescript
// In App.tsx, from existing agentConfigByPaneId:
const agentListForSidebar = createMemo(() => {
  const ws = activeMounted();
  if (!ws) return [];
  const configs = ws.agentConfigByPaneId();
  const budgets = budgetByPaneId(); // new budgetRegistry
  return Object.entries(configs)
    .filter(([, cfg]) => isKnownAgentCli(cfg.cliBinary)) // D-08
    .map(([paneId, cfg]) => ({
      paneId,
      cliBinary: cfg.cliBinary,
      model: cfg.cliArgs.find((a) => a.startsWith('--model'))?.split('=')[1] ?? 'default',
      costUsd: budgets[paneId]?.cost_usd ?? 0,
      isStreaming: budgets[paneId]
        ? Date.now() - (budgets[paneId].lastSeenMs ?? 0) < 3000
        : false,
    }));
});
```

---

### focusPaneById Implementation (GridController extension)

```typescript
// In GridRoot.tsx — add to GridController type:
focusPaneById: (paneId: string) => void;

// In the controller object returned via controllerRef:
focusPaneById: (paneId: string) => {
  const leaves = collectLeaves(store.root);
  const target = leaves.find((l) => l.id === paneId);
  if (!target) return;
  setStore(produce((s) => { s.focusedId = paneId; }));
  // Emit focus change so App.tsx updates focusedPaneId
  props.onFocusChange?.(paneId);
},
```

---

### Sidebar CSS — Collapse Transition

```css
/* sidebar.css */
.sidebar {
  width: var(--sidebar-w); /* 280px */
  flex-shrink: 0;
  overflow: hidden;
  background: var(--bg-1);
  border-right: 1px solid var(--border);
  transition: width 200ms cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.sidebar--collapsed {
  width: 0;
}

/* ::before left accent bar */
.sidebar::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: var(--focus);
  z-index: 1;
}

/* prefers-reduced-motion handled globally in index.css */
```

---

### Modal — CommandPalette Pattern Reference

The AgentLaunchModal follows the same structure as `CommandPalette.tsx`:
- Fixed position overlay with `background: rgba(0,0,0,0.6)`
- Panel `ref` for click-outside detection
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Focus trap on open via `onMount(() => { firstFocusableRef?.focus(); })`
- Escape key handler in `onKeyDown`
- The backdrop `onClick` calls `props.onDismiss()` if click is outside the panel

Key difference from CommandPalette: modal is 480px wide (not 680px) and centered (not top-aligned at `padding-top: 64px`).

---

### Agent Streaming Pulse CSS

```css
@keyframes voss-pulse {
  from { opacity: 1; }
  to   { opacity: 0.3; }
}

.agent-dot--streaming {
  animation: voss-pulse 0.8s ease-in-out infinite alternate;
}

/* prefers-reduced-motion kill switch inherits from index.css global */
```

---

### Tauri Rust Commands for File Tree and Git Log

```rust
// src-tauri/src/lib.rs — add after write_context_pins:

#[derive(Debug, Serialize)]
struct DirEntry {
    name: String,
    is_dir: bool,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    children: Vec<DirEntry>,
}

fn read_dir_shallow(path: &Path, depth: u32) -> Vec<DirEntry> {
    if depth == 0 { return Vec::new(); }
    let Ok(rd) = std::fs::read_dir(path) else { return Vec::new(); };
    let mut entries: Vec<DirEntry> = rd.filter_map(|e| e.ok()).map(|e| {
        let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
        let name = e.file_name().to_string_lossy().into_owned();
        let children = if is_dir && depth > 1 {
            read_dir_shallow(&e.path(), depth - 1)
        } else { Vec::new() };
        DirEntry { name, is_dir, children }
    }).collect();
    entries.sort_by(|a, b| b.is_dir.cmp(&a.is_dir).then(a.name.cmp(&b.name)));
    entries
}

#[tauri::command]
fn list_dir(path: String) -> Result<Vec<DirEntry>, String> {
    Ok(read_dir_shallow(Path::new(&path), 2))
}

#[derive(Debug, Serialize)]
struct GitCommit {
    hash: String,
    message: String,
    timestamp_secs: i64,
}

#[tauri::command]
fn git_log(workspace_path: String, limit: usize) -> Result<Vec<GitCommit>, String> {
    let out = std::process::Command::new("git")
        .args(["-C", &workspace_path, "log", &format!("-{limit}"),
               "--format=%H %ct %s"])
        .output()
        .map_err(|e| e.to_string())?;
    if !out.status.success() { return Ok(Vec::new()); }
    let parsed = String::from_utf8_lossy(&out.stdout)
        .lines()
        .filter_map(|line| {
            let mut parts = line.splitn(3, ' ');
            let hash = parts.next()?.to_string();
            let ts: i64 = parts.next()?.parse().ok()?;
            let msg = parts.next().unwrap_or("").to_string();
            Some(GitCommit { hash, timestamp_secs: ts, message: msg })
        })
        .collect();
    Ok(parsed)
}
```

Both commands must be added to `tauri::generate_handler![...]` in `run()`.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Variant B cool blue-gray theme | Voss Ignite warm amber/orange theme | New catalog entry; Variant B preserved |
| `--font-mono` everywhere | Poppins display + Inter UI + JetBrains Mono | Three-tier typography |
| Google Fonts `<link>` tag | Bundled local woff2 + @font-face | Required by Tauri CSP |
| No sidebar | 280px collapsible AgentSidebar | Agent-aware context panel |
| `contextByPaneId` only for cost | New `budgetByPaneId` for cost_usd | Enables sidebar + badge totals |

**Note:** The CONTEXT.md lists ADE-REDESIGN.md's `Quick Launch` section in sidebar — this is superseded by D-01 (CONTEXT.md decisions are authoritative). The sidebar has 4 sections (Agents/Sessions/Files/Git) and NO Quick Launch section. The `+ Agent` button opens the modal instead.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `focusPaneById` can be implemented by setting `store.focusedId` directly in a `setStore(produce(...))` call without triggering unintended rerender cascades | Code Examples | Grid may require additional bookkeeping; test with `onFocusChange` callback |
| A2 | Google Fonts woff2 static URLs are stable and can be downloaded once for bundling | Pitfall 1 | Font files could change checksum; use versioned URL |
| A3 | Streaming detection via `Date.now() - lastSeenMs < 3000` is a reasonable heuristic for Claude/Codex streaming | Finding 11 | Agents that pause for >3s between events would show as not-streaming |
| A4 | `git log` via `std::process::Command` works from Tauri's sandboxed environment without additional Tauri plugin permissions | Tauri Rust Commands | Some Tauri hardening configs could block child process spawning; test on target platform |
| A5 | Custom CLI presets (D-21) stored in settings.json can be persisted via existing `get_theme_overrides` settings path | Standard Stack | Might need a dedicated custom_agents section in settings |

---

## Open Questions

1. **Custom CLI persistence (D-21)**
   - What we know: settings.json at `~/.config/voss-app/settings.json` stores `theme` key only. No `custom_agents` key exists.
   - What's unclear: Should custom CLIs be added to the existing settings file or a new `custom-agents.json`?
   - Recommendation: Add a `custom_agents: Vec<CustomCli>` to `SettingsFile` struct in `lib.rs`. Expose `load_custom_agents` / `save_custom_agents` Tauri commands. Keep it in the existing settings path.

2. **Session tracking data for SESSIONS section (D-06)**
   - What we know: Agent sessions start when `spawn_agent` is called (SQLite registry). End when `mark_agent_stopped` is called.
   - What's unclear: Should the Sessions section read from the SQLite agent registry, or from a new in-memory event log in App.tsx?
   - Recommendation: Read from `get_active_agents` + filter for `status = 'stopped'` (last N stopped agents). Requires `get_recent_sessions(limit)` Tauri command or reading from the existing agent registry with a different query.

3. **WCAG AA contrast for --focus (#ff5b1f) on --bg-3 (#221f1b) at 11px**
   - What we know: The UI-SPEC explicitly calls this out as needing executor verification.
   - What's unclear: `contrastRatio('#ff5b1f', '#221f1b')` = ? (need calculation)
   - Recommendation: Calculate using the existing `contrastRatio()` function from schema.ts. If < 4.5:1, pair orange elements with `--fg-0` labels (as spec says). Planner should add a verification step.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|-------------|-----------|-------|
| Node.js / pnpm | Build, test | ✓ | Established in A1 |
| Rust / cargo | Tauri backend changes | ✓ | Established in A1 |
| git CLI | ADE-08 (git_log command) | ✓ (macOS standard) | Present on dev machine; Tauri child process |
| Poppins woff2 files | ADE-01 | ✗ (must download) | One-time download; no runtime dependency |

**Missing with one-time action:** Poppins woff2 files — download before first `pnpm dev` run.

---

## Validation Architecture

> nyquist_validation is enabled (config.json: `"nyquist_validation": true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.6 |
| Config file | `apps/voss-app/vitest.config.ts` |
| Quick run command | `pnpm --filter voss-app test` |
| Full suite command | `pnpm --filter voss-app test` (single suite, jsdom) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADE-01 | Voss Ignite JSON validates against schema | unit | `pnpm --filter voss-app test -- --grep "voss-ignite"` | ❌ Wave 0 |
| ADE-01 | REQUIRED_CSS_VARS all present in Ignite | unit | same | ❌ Wave 0 |
| ADE-02 | AgentSidebar renders collapsed (width=0) | unit | `pnpm --filter voss-app test -- --grep "AgentSidebar"` | ❌ Wave 0 |
| ADE-02 | AgentSidebar renders expanded (width=280px) | unit | same | ❌ Wave 0 |
| ADE-03 | Sidebar toggle adds to localStorage | unit | same | ❌ Wave 0 |
| ADE-04 | AgentLaunchModal mounts on `+ Agent` click | unit | `pnpm --filter voss-app test -- --grep "AgentLaunchModal"` | ❌ Wave 0 |
| ADE-05 | Titlebar renders Voss logo SVG path | unit | `pnpm --filter voss-app test -- --grep "Titlebar"` | ✅ (extend existing Titlebar.test.tsx) |
| ADE-06 | PaneHeader renders accent bar for agent pane | unit | `pnpm --filter voss-app test -- --grep "PaneChrome"` | ✅ (extend existing PaneChrome.test.tsx) |
| ADE-07 | FileTree renders empty state when path=null | unit | `pnpm --filter voss-app test -- --grep "FileTree"` | ❌ Wave 0 |
| ADE-08 | GitSection renders "Not a git repository" fallback | unit | `pnpm --filter voss-app test -- --grep "GitSection"` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pnpm --filter voss-app test`
- **Per wave merge:** `pnpm --filter voss-app test` (same — single suite)
- **Phase gate:** All existing tests green + new A12 tests green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx` — covers ADE-02, ADE-03
- [ ] `apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx` — covers ADE-04
- [ ] `apps/voss-app/src/themes/__tests__/voss-ignite.test.ts` — covers ADE-01 (schema conformance)
- [ ] `apps/voss-app/src/components/sidebar/__tests__/FileTree.test.tsx` — covers ADE-07
- [ ] `apps/voss-app/src/components/sidebar/__tests__/GitSection.test.tsx` — covers ADE-08

Existing tests to extend:
- `src/components/titlebar/__tests__/Titlebar.test.tsx` — add logo SVG assertion (ADE-05)
- `src/grid/__tests__/PaneChrome.test.tsx` — add accent bar assertion (ADE-06)

---

## Security Domain

> security_enforcement is enabled (absent in config = enabled).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Agent launch modal collects no credentials |
| V3 Session Management | No | localStorage only stores UI collapse state, not session tokens |
| V4 Access Control | No | No privilege-sensitive operations in sidebar UI |
| V5 Input Validation | Yes — Custom CLI command field | Sanitize command string before passing to Tauri spawn_agent; avoid shell injection |
| V6 Cryptography | No | No crypto operations |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via Custom CLI command field | Tampering | Pass CLI binary + args as separate Vec<String> to spawn_agent; never join into shell string |
| Path traversal in list_dir | Tampering | Canonicalize path in Rust before read_dir; verify it is under workspace_path |
| git log output injection | Spoofing | Format output server-side in Rust; parse strictly (splitn(3, ' ')); never eval |

**Custom CLI command (D-21) is the primary attack surface:** If the user types `rm -rf /` as the custom command, the frontend must pass it as `cli_binary = "rm"`, `cli_args = ["-rf", "/"]` — not as a shell string. The existing `spawn_agent` Tauri command already takes `cli_binary: String` and `cli_args: Vec<String>` separately, so this is naturally safe as long as the frontend never concatenates and passes to a shell.

---

## Sources

### Primary (HIGH confidence)

- Codebase: `apps/voss-app/src/themes/schema.ts` — REQUIRED_CSS_VARS (27 keys verified by inspection)
- Codebase: `apps/voss-app/src/themes/themeCatalog.ts` — bundle registration pattern confirmed
- Codebase: `apps/voss-app/src/themes/themeRuntime.ts` — applyThemeOverrides mechanism confirmed
- Codebase: `apps/voss-app/src-tauri/src/lib.rs` — full command surface confirmed, list_dir/git_log absent confirmed
- Codebase: `apps/voss-app/src/App.tsx` — layout structure, agentConfigByPaneId signal, contextPanelOpen pattern confirmed
- Codebase: `apps/voss-app/src/grid/GridRoot.tsx` — GridController interface confirmed, focusPaneById absent confirmed
- Codebase: `apps/voss-app/src/pane/procRegistry.ts` — registry pattern for budgetRegistry
- Codebase: `apps/voss-app/src/pane/pty-ipc.ts` — BudgetState type, cost_usd field confirmed
- Codebase: `apps/voss-app/src/components/workspace/WorkspaceTabBar.tsx` — HTML5 drag pattern confirmed
- Codebase: `apps/voss-app/src/index.css` — CSP constraints, global border-radius:0 reset, prefers-reduced-motion confirmed
- Codebase: `apps/voss-app/src-tauri/tauri.conf.json` — CSP string confirmed (blocks Google Fonts)
- Codebase: `site/public/logo.svg` — 2-path SVG, #ff5b1f fill, confirmed
- Codebase: `crates/voss-cli/src/lib.rs` — actual Cmd enum confirmed (chat/do/agent/skill/resume)
- Codebase: `apps/voss-app/vitest.config.ts` — test framework confirmed

### Secondary (MEDIUM confidence)

- ADE-REDESIGN.md Phase 1–8 — design intent document, written before A12 CONTEXT decisions locked; authoritative for token values but some structural decisions (Quick Launch section) superseded by D-01
- A12-CONTEXT.md D-01..D-30 — locked decisions, primary input
- A12-UI-SPEC.md — component contracts, spacing, typography, verified against codebase

---

## Metadata

**Confidence breakdown:**
- Theme system: HIGH — implementation pattern directly inspected
- Sidebar component: HIGH — pattern confirmed from ContextPanel + WorkspaceTabBar
- Font loading: HIGH — CSP constraint directly verified in tauri.conf.json
- Missing focusPaneById: HIGH — GridController interface directly read; method absent
- budgetRegistry gap: HIGH — procRegistry pattern confirmed; budget signal verified as pane-local
- Tauri backend gaps: HIGH — all commands directly enumerated in lib.rs
- Voss CLI surface: HIGH — lib.rs Cmd enum directly read
- Drag-to-reorder: HIGH — WorkspaceTabBar pattern directly inspected
- Git log via child process: MEDIUM — plausible in Tauri but not tested; see Open Question 4

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (stable stack — SolidJS 1.9.x, Tauri 2.x)
