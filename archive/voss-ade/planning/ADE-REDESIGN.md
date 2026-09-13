# ADE Redesign — Left Sidebar + Warm Site Palette

Implementation plan for transforming Voss ADE from "terminal multiplexer" to "SOTA agent development environment."

Winner: **Sketch 002 Variant A** — collapsible left sidebar with agent list, quick launch, file tree, and history. Warm site palette (#0b0a09 bg, #ff5b1f accent, Poppins/Inter/JetBrains Mono).

---

## Phase 1: Theme Migration (warm palette)

**Goal**: Replace cool blue-gray tokens with warm site-aligned palette. Zero functional changes.

### Files to modify

| File | Change |
|------|--------|
| `src/styles/variant-b.css` | Replace all token values with warm palette (see below) |
| `src/index.css` | Update any hardcoded colors to use CSS vars |
| `src/pane/pane.css` | Verify all colors reference vars, no raw hex |
| `src/components/workspace/workspace.css` | Same |
| `src/components/ContextPanel.css` | Same |

### Token mapping

```
OLD (cool blue-gray)          → NEW (warm site)
--bg-0: #0a0b0e               → #0b0a09
--bg-1: #11131a               → #131110
--bg-2: #171a23               → #1a1714
--bg-3: #1f232e               → #221f1b
--border: #262b38             → #1d1a16
--border-bright: #353b4a      → #2e2924
--focus: #5a7cff              → #ff5b1f
--focus-glow: rgba(90,124,255,0.18) → rgba(255,91,31,0.18)
--fg-0: #e8eaf0               → #f5f1ea
--fg-1: #aab0c0               → #c4beb5
--fg-2: #6a7080               → #8a847a
--fg-3: #444a5a               → #5a554d
--accent-green: #6fd28f       → #5ec26a
--accent-amber: #e8b86c       → #e8b86c (keep)
--accent-red: #e87b7b         → #e87b7b (keep)
--accent-cyan: #6cc7d4        → #6cc7d4 (keep)
--accent-magenta: #c084d4     → #c084d4 (keep)
--accent-blue: #7aa2ff        → #7aa2ff (keep — NOT used as focus anymore)
```

### New tokens to add

```css
/* Focus soft tint for backgrounds */
--focus-soft: rgba(255, 91, 31, 0.14);
--focus-hover: #ff7a47;

/* Agent role semantic colors */
--role-planner: #ff5b1f;
--role-executor: #6cc7d4;
--role-reviewer: #e8b86c;
--role-watcher: #8a847a;
--role-user: #5ec26a;

/* Typography additions */
--font-display: "Poppins", system-ui, sans-serif;

/* Layout */
--sidebar-w: 280px;
```

### Font loading

Add Google Fonts import for Poppins to `index.html` (Tauri entry):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
```

Inter and JetBrains Mono already loaded.

### Verify

- `pnpm dev` — app renders with warm palette
- All existing tests pass
- No raw hex values in component CSS (grep check)
- Focused pane border uses orange instead of blue
- Status bar, titlebar, tabs all warm

---

## Phase 2: Sidebar Component

**Goal**: Create `AgentSidebar.tsx` — collapsible left panel with agent list.

### New files

| File | Purpose |
|------|---------|
| `src/components/sidebar/AgentSidebar.tsx` | Main sidebar component |
| `src/components/sidebar/sidebar.css` | Sidebar styles |
| `src/components/sidebar/AgentItem.tsx` | Single agent row |
| `src/components/sidebar/QuickLaunch.tsx` | Launch buttons (Claude/Codex/Gemini) |

### AgentSidebar.tsx design

```
┌─────────────────────────┐
│ [V logo] ···· [◀ close] │  ← sidebar-header (44px)
├─────────────────────────┤
│ AGENTS                  │
│ ● Claude Planner  $0.42 │
│ ● Codex Executor  $0.18 │
│ ● Gemini Reviewer $0.07 │
├─────────────────────────┤
│ QUICK LAUNCH            │
│ [● Claude] [● Codex]   │
│ [● Gemini]              │
├─────────────────────────┤
│ FILES                   │
│ ▾ src/                  │
│   ▸ components/         │
│   ● App.tsx             │
├─────────────────────────┤
│ HISTORY                 │
│ 2m ago  Refactored grid │
│ 18m    Added detection  │
└─────────────────────────┘
```

### Props

```typescript
interface AgentSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  agents: AgentInfo[];           // from existing agentConfigByPaneId
  onAgentClick: (paneId: string) => void;
  onLaunch: (cli: string) => void;
  projectPath: string | null;
}
```

### Key details

- **Width**: 280px, animates to 0 on collapse (CSS transition 250ms cubic-bezier)
- **Left accent**: 2px orange bar (`--focus`) on left edge via `::before`
- **Sections**: AGENTS, QUICK LAUNCH, FILES, HISTORY — each with uppercase 10px label
- **Agent items**: 7px status dot (role color + glow), name (Inter 12px 500), model (mono 10px dim), role badge (pill, 9px uppercase), cost (mono 10px)
- **Quick Launch**: 3 buttons in flex row, 1px border, hover → orange border + soft bg
- **Files**: basic tree from project root (read dir via Tauri `list_dir` command)
- **History**: from git log or session history (timestamps + descriptions)
- **Collapse**: `⌘B` keybinding (already handled in App.tsx for prefix mode — need to repurpose or use `⌘\` instead)
- When collapsed, show thin expand handle (16×48px) on left edge of grid area

### Sidebar expand button

When collapsed, a small `▸` button appears at left edge of grid:
```css
.sidebar-expand {
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 16px; height: 48px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-left: none;
  border-radius: 0 3px 3px 0;
  z-index: 10;
}
```

### Verify

- Sidebar renders with agent list
- Collapse/expand animates smoothly
- Agent items show correct role colors
- Quick launch buttons have hover states
- Grid resizes via ResizeObserver (not manual width calc)

---

## Phase 3: Layout Integration

**Goal**: Wire sidebar into App.tsx layout. Grid sits beside sidebar, not inside it.

### Files to modify

| File | Change |
|------|--------|
| `src/App.tsx` | Add sidebar state, wrap grid area in flex row with sidebar |
| `src/grid/GridRoot.tsx` | No changes needed — grid fills its container |

### Layout structure (after)

```
┌─────────────────────────────────────────────┐
│ Titlebar                                     │  38px
├─────────────────────────────────────────────┤
│ WorkspaceTabBar                              │  32px
├──────────┬──────────────────────────────────┤
│ Agent    │                                   │
│ Sidebar  │  GridRoot                         │  flex: 1
│ 280px    │  (binary-split tree)              │
│          │                                   │
├──────────┴──────────────────────────────────┤
│ StatusBar                                    │  26px
└─────────────────────────────────────────────┘
```

### App.tsx changes

```tsx
// New state
const [sidebarCollapsed, setSidebarCollapsed] = createSignal(
  localStorage.getItem('voss:sidebarCollapsed') === 'true'
);
const toggleSidebar = () => {
  setSidebarCollapsed(prev => {
    const next = !prev;
    localStorage.setItem('voss:sidebarCollapsed', String(next));
    return next;
  });
};

// In render, wrap grid area:
<div style={{ display: 'flex', flex: '1', 'min-height': '0', overflow: 'hidden' }}>
  <AgentSidebar
    collapsed={sidebarCollapsed()}
    onToggle={toggleSidebar}
    agents={agentListForSidebar()}
    onAgentClick={(paneId) => gridController()?.focusPaneById(paneId)}
    onLaunch={(cli) => { /* spawn agent in new pane */ }}
    projectPath={activeMounted()?.project()?.path ?? null}
  />
  <div style={{ flex: '1', 'min-height': '0', display: 'flex', 'flex-direction': 'column' }}>
    {/* existing GridRoot / SetupWindow content */}
  </div>
</div>
```

### Keybinding

Add `sidebar.toggle` command to registry:
```typescript
{ id: 'sidebar.toggle', label: 'Toggle Sidebar', keybinding: 'Cmd+Shift+B', handler: () => toggleSidebar() }
```

Note: `⌘B` is taken by prefix mode. Use `⌘⇧B` for sidebar.

### Agent list derivation

Derive sidebar agent list from existing `agentConfigByPaneId`:
```typescript
const agentListForSidebar = createMemo(() => {
  const configs = activeMounted()?.agentConfigByPaneId() ?? {};
  return Object.entries(configs).map(([paneId, config]) => ({
    paneId,
    name: config.cliBinary,
    model: config.cliArgs.find(a => a.startsWith('--model'))?.split('=')[1] ?? 'default',
    role: detectRole(config),  // from agentDetect.ts
    cost: contextByPaneId()[paneId]?.cost ?? 0,
    status: 'running',  // from process registry
  }));
});
```

### Verify

- App renders with sidebar + grid side by side
- Sidebar collapse doesn't break grid resize
- Agent list updates reactively when agents start/stop
- `⌘⇧B` toggles sidebar
- Grid pane focus works when sidebar is open/closed
- Session persist/restore works with sidebar state

---

## Phase 4: Agent Launch Flow

**Goal**: Quick Launch buttons spawn agents in new panes.

### Files to modify

| File | Change |
|------|--------|
| `src/components/sidebar/QuickLaunch.tsx` | Launch button click handler |
| `src/pane/pty-ipc.ts` | Expose `spawnAgent(cli, args, cwd)` |
| `src/grid/operations.ts` | Add `splitWithAgent(orientation, agentConfig)` |

### Launch flow

1. User clicks "Claude" button in sidebar
2. `onLaunch('claude')` fires up to App.tsx
3. App calls `gridController.splitFocused('H')` to create new pane
4. New pane spawns with `claude --dangerously-skip-permissions` (or user's preferred args)
5. Agent detection picks up the process → sidebar updates reactively

### Quick Launch config

```typescript
const AGENT_PRESETS = [
  { id: 'claude', label: 'Claude', cli: 'claude', color: '#ff5b1f' },
  { id: 'codex', label: 'Codex', cli: 'codex', color: '#6cc7d4' },
  { id: 'gemini', label: 'Gemini', cli: 'gemini', color: '#e8b86c' },
] as const;
```

### Verify

- Click Claude → new pane opens with claude running
- Sidebar agent list updates within 1s
- Works with sidebar open and collapsed
- Agent pane has correct role color in header

---

## Phase 5: Titlebar + Branding Polish

**Goal**: Apply site branding to titlebar. Logo mark, Poppins font, warm styling.

### Files to modify

| File | Change |
|------|--------|
| `src/components/titlebar/Titlebar.tsx` | Add logo SVG, use Poppins for app name |
| `src/components/titlebar/PresetSwitcher.tsx` | Warm palette on hover states |
| `src/components/StatusBar.tsx` | Add agent count badge (orange pill), warm styling |

### Titlebar changes

- Left: traffic lights (existing) + Voss logo mark (20px inline SVG, `--focus` fill)
- Center: project name in Poppins 500 (was monospace)
- Right: preset switcher (existing) — update hover to orange

### Status bar agent badge

Right side of status bar: orange pill showing "● 3 agents · $0.67"
- Pulls from same `agentListForSidebar` memo
- Clicking badge toggles sidebar (secondary entry point)

### Verify

- Logo renders at correct size
- Poppins loads and displays
- Agent badge shows correct count and cost sum
- Badge click toggles sidebar

---

## Phase 6: Pane Chrome Warmth

**Goal**: Apply warm accent treatment to terminal pane headers and borders (from sketch 003-B "Warm Accent" patterns).

### Files to modify

| File | Change |
|------|--------|
| `src/grid/PaneHeader.tsx` | Add 3px left accent bar in role color |
| `src/pane/pane.css` | Focused pane: orange left edge + focus-soft bg tint |

### Pane header enhancement

- Left 3px accent bar colored by agent role (orange/cyan/amber/green)
- Regular shell panes: no accent bar (or dim `--fg-3` bar)
- Focused agent pane: full-height 3px orange bar + `--focus-soft` background
- Cost display turns orange when > $1.00

### Streaming indicator

- Agent panes actively streaming: pulsing orange dot (CSS animation) instead of static dot
- Done: checkmark icon, fades to dim after 3s

### Verify

- Agent panes have role-colored accent bars
- Regular shell panes look clean without bars
- Focused pane has visible orange treatment
- Streaming animation is smooth, not distracting

---

## Phase 7: File Tree (basic)

**Goal**: Populate the FILES section with actual project directory listing.

### New files

| File | Purpose |
|------|---------|
| `src/components/sidebar/FileTree.tsx` | Recursive directory tree |

### Implementation

- Use Tauri `invoke('list_dir', { path })` (or existing FS command)
- Start collapsed at project root
- Click directory → expand/collapse
- Click file → no action yet (future: open in editor pane)
- Icons: `▾`/`▸` for dirs, `●` for files
- Truncate at 2 levels deep initially, expand on click
- Files section gets `flex: 1; overflow-y: auto` for scrolling

### Verify

- Tree shows real project files
- Expand/collapse works
- Scroll within section works
- Empty state when no project selected

---

## Phase 8: History / Sessions

**Goal**: Show recent session activity in the HISTORY section.

### Implementation options

1. **Git log** (simplest): `git log --oneline -10` from project root
2. **Session timestamps**: track when agent sessions start/end
3. **Hybrid**: git commits + agent session starts

Start with git log — lowest effort, most useful.

### Files to modify

| File | Change |
|------|--------|
| `src/components/sidebar/History.tsx` | New component |
| `src/project/projectStorage.ts` | Add `getRecentCommits(path, limit)` |

### Display

```
HISTORY
2m ago   feat: add sidebar         (git)
18m ago  Refactored grid layout    (git)
1h ago   Claude session ended      (session)
```

### Verify

- Shows real git log entries with relative timestamps
- Updates on focus (not polling)
- Graceful empty state for non-git dirs

---

## Build Order

```
Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
  │         │    │
  │         │    └── 4,5,6 can parallelize after 3
  │         │
  │         └── 2 is the big component build
  │
  └── 1 is pure CSS, zero risk
```

**Critical path**: 1 → 2 → 3 (sidebar exists and is wired in)
**Parallelizable after 3**: 4 (launch), 5 (branding), 6 (chrome), 7 (files), 8 (history)

### Effort estimates not provided (per CLAUDE.md guidelines)

### Testing strategy

Each phase:
1. Existing tests must pass (no regression)
2. Visual verify in `pnpm dev`
3. New component tests for sidebar, file tree, history
4. Integration: sidebar + grid resize, sidebar + session persist

---

## Design Tokens Reference (final palette)

Extracted from sketch 002-A and site globals.css:

```css
/* Background */     #0b0a09 → #131110 → #1a1714 → #221f1b
/* Foreground */     #f5f1ea → #c4beb5 → #8a847a → #5a554d
/* Border */         #1d1a16 / #2e2924
/* Focus */          #ff5b1f / rgba(255,91,31,0.14) / rgba(255,91,31,0.18)
/* Roles */          planner=#ff5b1f  executor=#6cc7d4  reviewer=#e8b86c  user=#5ec26a
/* Fonts */          Poppins (display) / Inter (UI) / JetBrains Mono (terminal)
/* Radius */         0 default, 3px small, 6px medium, 9999px pills
/* Sidebar */        280px width, 2px orange left accent
/* Status bar */     26px, orange agent badge pill
/* Pane headers */   28px, 3px role-color left accent bar
```
