# Phase A10: voss-app Status Bar - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** A10-voss-app-status-bar
**Areas discussed:** Popover content & behavior, Notification store vs toasts, Git info depth & detection

---

## Popover content & behavior

### Q1: How should popovers dismiss?

| Option | Description | Selected |
|--------|-------------|----------|
| Click-outside + Esc | Standard popover: click cluster to open, click anywhere else or Esc to close. One popover at a time. Matches command palette dismiss (A7 D-08). | ✓ |
| Click toggles (same cluster closes) | Click cluster to open, click same again to close, click different swaps. Click-outside also dismisses. | |
| You decide | Planner picks dismiss UX within standard conventions. | |

**User's choice:** Click-outside + Esc

### Q2: What shows in the LEFT popover (project/branch cluster)?

| Option | Description | Selected |
|--------|-------------|----------|
| Recent projects list | Click project name → recents. Click one = switch project. Branch read-only below. No branch switcher in L1. | ✓ |
| Project detail + recents | Current project path, git remote, branch, last opened, PLUS recents below. Richer info panel. | |
| You decide | Planner determines content depth. | |

**User's choice:** Recent projects list

### Q3: What shows in the CENTER popover (focused pane info)?

| Option | Description | Selected |
|--------|-------------|----------|
| Pane detail card | Focused pane full path (cwd), shell name+version, PID, pane index, running command. Read-only. | ✓ |
| Pane list for workspace | ALL panes in workspace as compact list. Click row = focus pane. Doubles as navigator. | |
| You decide | Planner picks. | |

**User's choice:** Pane detail card

### Q4: Component structure?

| Option | Description | Selected |
|--------|-------------|----------|
| One generic Popover | Single `<Popover anchor={el} content={...}>` reused by all clusters. Consistent positioning/dismiss/animation. DRY. | ✓ |
| You decide | Planner picks, likely one generic anyway. | |
| Distinct per cluster | Each cluster has own popover component. More flexibility, more code. | |

**User's choice:** One generic Popover

---

## Notification store vs toasts

### Q1: How do toasts and the notification bell relate?

| Option | Description | Selected |
|--------|-------------|----------|
| Unified stream | Every event → BOTH toast (ephemeral) AND notification store (persistent, bell badge). Toast = real-time; bell = history. | ✓ |
| Separate routing | Some toast-only, some bell-only, some both. Explicit routing rules. | |
| You decide | Planner designs routing. | |

**User's choice:** Unified stream

### Q2: What clears the bell badge?

| Option | Description | Selected |
|--------|-------------|----------|
| Opening the bell popover | Click bell → popover opens → badge resets to 0. All marked read. | ✓ |
| Explicit 'Mark all read' | Badge persists until user clicks Clear button inside popover. | |
| You decide | Planner picks. | |

**User's choice:** Opening the bell popover

### Q3: Where does notification store persist?

| Option | Description | Selected |
|--------|-------------|----------|
| Global notifications.json | `~/.config/voss-app/notifications.json`. Single file, last 50, written on quit. App-level. | ✓ |
| Per-workspace in session | Each workspace session includes notifications array. Workspace-scoped. | |
| You decide | Planner picks. | |

**User's choice:** Global notifications.json

### Q4: L1 notification sources?

| Option | Description | Selected |
|--------|-------------|----------|
| Ship L1.8.2 as-is | 5 sources: pane exit non-zero, layout saved/loaded, settings reload, update available, app errors. | ✓ |
| Add git branch change | Also notify on branch changes. | |
| You decide | Planner picks. | |

**User's choice:** Ship L1.8.2 as-is

---

## Git info depth & detection

### Q1: How much git info shows in the status bar?

| Option | Description | Selected |
|--------|-------------|----------|
| Branch name only | Just branch name. No dirty/ahead-behind. Matches "read-only display in L1." | ✓ |
| Branch + dirty indicator | Branch + single dot when uncommitted changes exist. | |
| Branch + dirty + ahead/behind | Full git status line. Approaches IDE-level. | |

**User's choice:** Branch name only

### Q2: How should branch changes be detected?

| Option | Description | Selected |
|--------|-------------|----------|
| Rust file watcher on .git/HEAD | Tauri/Rust watches `.git/HEAD`. On change → re-read → Tauri event to frontend. Near-instant. | ✓ |
| Poll every 2s | Rust timer reads `.git/HEAD` every 2s. Simpler but up to 2s latency. | |
| You decide | Planner picks within 500ms requirement. | |

**User's choice:** Rust file watcher on .git/HEAD

### Q3: Non-git folder display?

| Option | Description | Selected |
|--------|-------------|----------|
| Hide branch entirely | Branch segment disappears. Left cluster shows only project name or BAR-08 fallback. | ✓ |
| Show dimmed 'no repo' | Dimmed text placeholder. Consistent width. | |
| You decide | Planner picks. | |

**User's choice:** Hide branch entirely

---

## Claude's Discretion

- Popover visual design (width, padding, arrow, shadow) — within Variant B tokens
- Popover positioning logic — standard approach
- Notification store schema shape — planner designs
- Bell badge visual (dot vs count) — planner picks
- Git watcher debounce strategy — within 500ms requirement
- Settings cog implementation — triggers ⌘, command
- Pane count display format — minor styling
- Status bar flex layout proportions — planner picks

## Deferred Ideas

None — discussion stayed within phase scope.
