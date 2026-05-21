# Phase A10: voss-app Status Bar - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

A10 delivers a bottom status bar for voss-app: three clusters (left: project + git branch, center: focused pane info, right: pane count + notification bell + settings cog) each with click-to-popover detail panels. Fixed 22px height, Variant B tokens, mono font. Workspace-aware — all displayed info scopes to the active workspace.

A10 builds on: A1 (Variant B tokens + Rust IO seam), A5 (project/recents/git-read), A7 (command registry + toast system), A8 (workspace model), A9 (settings overlay + cog trigger).

**Out of scope (fenced to other phases):**
- Cost meter — Q6 decision: no cost slot in L1. Added in L2 with cell promotion.
- Branch switching / full SCM — L4+
- Agent/cell notifications — L2+
- Settings UI surface — A9 (cog just triggers `⌘,` command)
- Onboarding empty state — A11

</domain>

<decisions>
## Implementation Decisions

Scope (WHAT) is fixed by ROADMAP BAR-01..08. These are HOW decisions from discussion.

### Popover content & behavior
- **D-01:** **Click-outside + Esc dismissal.** Standard popover: click cluster to open, click anywhere else or Esc to close. Only one popover open at a time. Matches command palette dismiss pattern (A7 D-08).
- **D-02:** **LEFT popover = recent projects list.** Click project name → popover shows recent workspaces/projects (reuses A5 recents list). Click entry = switch project. Branch shown as read-only detail below project name. No branch switcher in L1.
- **D-03:** **CENTER popover = pane detail card.** Shows focused pane's full path (cwd), shell name + version, PID, pane index, and running command if any. Read-only informational. No pane-switching actions.
- **D-04:** **One generic `<Popover>` component.** Single `<Popover anchor={el} content={...}>` reused by all three clusters. Consistent positioning, dismiss behavior, and animation. Each cluster passes different content children.

### Notification store vs toasts
- **D-05:** **Unified event stream.** Every notification event goes to BOTH toast (ephemeral, auto-dismiss per A7 timing) AND notification store (persistent, bell badge). Toast = real-time flash surface; bell = history. Single event pipeline, two consumers.
- **D-06:** **Opening bell popover clears badge.** Click bell → popover opens → unread badge resets to 0. All shown notifications marked as read. Matches GitHub/Slack pattern.
- **D-07:** **Global `notifications.json` persistence.** `~/.config/voss-app/notifications.json` — single file, last 50 entries, written on quit (same write-on-quit pattern as A6 session save). App-level, not per-workspace.
- **D-08:** **L1.8.2 event sources as-is.** Five sources: pane exit non-zero, layout saved/loaded, settings reload, update available, app-level errors. No additions in L1. L2 adds agent/cell events.

### Git info depth & detection
- **D-09:** **Branch name only.** Just the current branch name (e.g., `main`, `feature/auth`). No dirty indicator, no ahead/behind. Matches "read-only display in L1" (FEATURES). Dirty/ahead-behind deferred to L4 SCM.
- **D-10:** **Rust file watcher on `.git/HEAD`.** Tauri/Rust watches `.git/HEAD` for changes. On change, re-read branch name, push update to frontend via Tauri event. Near-instant detection, satisfies 500ms latency requirement (BAR-06). Standard approach (VSCode does similar).
- **D-11:** **Hide branch when no git repo.** When project has no `.git/` (project-less mode or non-git folder), branch segment disappears entirely. Left cluster shows only project name or "no project · ⌘O to open" (BAR-08). No placeholder text.

### Claude's / Planner's Discretion
- Popover visual design (width, padding, arrow/no-arrow, shadow depth) — within Variant B tokens.
- Popover positioning logic (above bar, edge-clamped to viewport) — standard approach.
- Notification store schema shape (timestamp, severity, message, source, read flag) — planner designs.
- Bell badge visual (dot vs count number vs both) — planner picks within Variant B.
- Git watcher debounce/rate-limiting strategy — planner picks, bounded by 500ms latency.
- Settings cog implementation — triggers existing `⌘,` registry command (A9). Just a button.
- Pane count display format (`▢ 4` per FEATURES or planner's variant) — minor styling.
- Status bar left/center/right flex layout proportions — planner picks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & cross-A constraints
- `.planning/ROADMAP.md` Phase A10 (~line 1387) — BAR-01..08, proposed success criteria, cross-cutting constraints (Q6 no cost meter, workspace-scoped).

### Product concept (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §4 (~line 137) — planned directory structure: `src/status-bar/` is canonical location.
- `apps/voss-app/CONCEPT.md` §10 Q6 — cost meter hidden in L1; slot added in L2.
- `apps/voss-app/FEATURES.md` §L1.7 (~line 193) — Status bar clusters: left (project/branch), center (pane cwd/shell/pid), right (pane count/bell/cog). §L1.7.4 click-to-detail popovers.
- `apps/voss-app/FEATURES.md` §L1.8 (~line 211) — Notifications: toast surface (L1.8.1), v0 sources (L1.8.2), notification log via bell (L1.8.3).

### Prior-phase decisions A10 builds on (do not re-litigate)
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-01/D-02 (Variant B CSS-var token system; status bar uses same `--bg-0..3` / `--fg-0..3` / `--border` tokens), D-09 (Rust/Tauri owns file IO; `~/.config/voss-app/` path lock for `notifications.json`).
- `.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md` — Project state, recents list, git-read mechanics. D-02 popover reuses A5 recents data.
- `.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md` — D-01 (central command registry; cog click dispatches registry command), D-16 (toast component exists; D-05 unified stream extends toast to also write notification store).
- `.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md` — D-01 (all workspaces stay mounted; status bar reads active workspace signals), D-04 (workspaces.json + per-workspace sessions).
- A9 discussion checkpoint — settings panel = full-screen overlay, `⌘,` shortcut (also via cog in A10 status bar).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/command-palette/toast.tsx` — Toast system (A7 D-16). D-05 extends this: every `showToast()` call also writes to the notification store. Module-level signal pattern reusable for notification store.
- `src/project/projectStorage.ts` — `listRecents()`, `openProject()`, `defaultCwd()`. D-02 left popover reuses this for recent projects list.
- `src/components/titlebar/Titlebar.tsx` — 22px height, Variant B tokens, flex layout. Status bar mirrors this pattern at the bottom.

### Established Patterns
- Module-level Solid signals for app-wide stores (toast uses `createSignal` at module scope).
- Tauri commands for Rust↔frontend communication (`invoke()` for reads, `listen()` for events).
- CSS custom properties for all styling (Variant B token system).
- `~/.config/voss-app/` for persisted files (settings.json, sessions).

### Integration Points
- `App.tsx` — status bar renders below `<GridRoot>`, above nothing. New `<StatusBar>` component in the main flex column.
- `src/grid/GridRoot.tsx` — provides pane count and focused pane info signals.
- A8 workspace store (when built) — provides active workspace, project, pane tree.
- A7 command registry — settings cog triggers existing open-settings command.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within Variant B aesthetic.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: A10-voss-app-status-bar*
*Context gathered: 2026-05-20*
