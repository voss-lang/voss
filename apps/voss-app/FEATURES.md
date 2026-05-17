# voss-app — Feature Catalog (Layer-Ordered)

> Companion to `CONCEPT.md`. Concept defines *why* and *how*. This doc defines *what*, organized by the three-layer build order.
>
> **L1** = Terminal-grid scaffold (v0) — zero Voss
> **L2** = Voss harness substrate (v1) — promote-to-cell
> **L3** = `.voss` DSL features (v2)
> **L4+** = Deferred surfaces (editor / file tree / SCM / etc.)
> **⛔** = Never

---

# LAYER 1 — Terminal-Grid Scaffold (v0)

The entire v0 binary. **Zero Voss code.** Ships as a competitive grid-native terminal app.

## L1.1 Application Shell

### L1.1.1 Window & chrome
- Native window via Tauri (macOS, Linux, Windows).
- Custom titlebar (traffic lights mac · close/min/max linux/win): project name · current layout preset switcher · cost meter stub (`$0.00`).
- System tray icon (linux/win) · menu bar (mac).
- Full-screen, zoom, multi-monitor support.

### L1.1.2 Themes
- Dark default = sketch 001 Variant B tokens.
- Color tokens: `--bg-0..3`, `--fg-0..3`, `--border`, `--focus`, accent colors (green/amber/red/cyan/magenta/blue).
- Mono font: JetBrains Mono default, configurable.
- Light theme deferred to L4+.

### L1.1.3 Distribution
- Tauri-built DMG (mac, arm64+x64), AppImage (linux x64+arm64), MSI (win x64).
- Auto-updater via Tauri updater (GitHub Releases backend).
- Code signing on mac/win (cert procurement = open question).

## L1.2 Workspace & Project

### L1.2.1 Open folder
- Folder picker via `⌘O` or empty-state button.
- Drag-drop folder onto app icon to open.
- App opens **with or without** a project — terminal panes work either way.

### L1.2.2 Recent workspaces
- Last 10 folders. Pinned favorites. Cleared via command palette.

### L1.2.3 `.voss/` directory
- Created lazily on first action that needs it (settings write, layout save).
- Empty in L1 except for `settings.json` if user customizes.
- Forward-compat: schema versioned `{"version": 1}`.

### L1.2.4 Project metadata
- Project name = folder basename, editable.
- Git branch auto-read via `git2` if `.git/` present.
- No semantic "project type" detection in L1.

## L1.3 Grid Layout Engine

### L1.3.1 Pane model
- Each pane = independent xterm + PTY.
- Pane state: cwd, shell, scrollback, dimensions, focus.
- Panes are rectangular tiles in a binary-split tree (same model as tmux/i3).

### L1.3.2 Split operations
- `⌘\` split horizontal (new pane right of focused).
- `⌘⇧\` split vertical (new pane below focused).
- `⌘D` fork pane (duplicate cwd + shell, fresh scrollback).
- `⌘W` close pane (with confirm if shell is running a process).

### L1.3.3 Navigation
- `⌘1`-`⌘9` focus pane by index.
- `⌘⌥←/→/↑/↓` focus directional neighbor.
- Click anywhere in a pane = focus.
- `⌘[`/`⌘]` cycle panes.

### L1.3.4 Resize
- Drag pane border to resize.
- `⌘⌥⇧←/→/↑/↓` resize focused pane in 5% increments.
- `⌘=` equalize all panes.

### L1.3.5 Layout presets
- Titlebar switcher: `fanout · pipeline · swarm · watchers`.
- L1 semantics: pure visual templates.
  - **fanout** = single source pane left, 2–4 panes right column
  - **pipeline** = left-to-right row of equal panes
  - **swarm** = N×N equal grid (2×2 default, up to 4×4)
  - **watchers** = main pane top, 2–3 thin watcher panes bottom
- `⌘G` cycles presets. Switching reorders existing panes, doesn't kill them.
- L2 will overload presets with semantic meaning (e.g., "swarm" implies worktrees) — L1 ignores semantics.

### L1.3.6 Save layout
- Current layout (pane tree + cwds + sizes) persisted to `.voss/layouts/<name>.json`.
- "Save layout as…" + "Load layout…" in command palette.

## L1.4 Terminal Panes (xterm + PTY)

### L1.4.1 PTY backend
- `portable-pty` Rust crate spawns shells natively.
- Inherits user env, sets `TERM=xterm-256color`, `COLORTERM=truecolor`.

### L1.4.2 Shell selection
- Default = `$SHELL` env var.
- Configurable per workspace + per pane (settings).
- Supports zsh / bash / fish / sh / pwsh / nu / any binary on PATH.

### L1.4.3 Pane chrome
- 22px header (sketch 001 Variant B): `●` dot · pane index · cwd basename · shell name · process indicator.
- Right side: pane menu `⋯` (close, fork, rename, save scrollback).
- Inset-shadow + bg-lift on focus (no border ring).

### L1.4.4 Scrollback
- 10k lines default per pane (configurable).
- `⌘F` find in scrollback.
- `⌘⇧K` clear scrollback.
- Scrollback persisted on quit (last 2k lines) for restore.

### L1.4.5 Copy / paste
- `⌘C` copy selection (or interrupt if no selection — configurable).
- `⌘V` paste with bracketed-paste safety (warn on multi-line paste with newlines).
- `⌘⇧V` paste literal.

### L1.4.6 Process indicator
- Header shows current foreground command (parsed via PTY title sequence `OSC 0`).
- Spinner dot when stdin-blocked or sleeping > 1s.

### L1.4.7 Exit behavior
- Shell exits → pane shows `[exited 0]` banner with "restart" button. Doesn't auto-close. (Subject to open question Q3.)

### L1.4.8 Hyperlinks
- `OSC 8` hyperlink support — `⌘+click` opens URL.
- File-path detection in output → `⌘+click` opens in OS default app.

### L1.4.9 Images & sixel
- L4+. Not in v0.

## L1.5 Command Palette

### L1.5.1 Quick-open
- `⌘P` — opens folder/file picker. L1 picks folder only (no editor). v0 stretch: jump to layout by name.

### L1.5.2 All commands
- `⌘⇧P` — every command, fuzzy match.

### L1.5.3 v0 command catalog
- **Window:** new window, close window, toggle full-screen, zoom in/out, reset zoom.
- **Pane:** split H, split V, close, fork, focus N, focus next/prev, resize, equalize, rename, save scrollback.
- **Layout:** switch preset (fanout/pipeline/swarm/watchers), save layout, load layout, equalize.
- **Project:** open folder, open recent, close project, reveal `.voss/` in finder.
- **Settings:** open settings, edit settings JSON, switch theme, switch keymap profile.
- **Help:** docs, keybindings cheatsheet, about, report issue.

### L1.5.4 Recent commands
- Recent commands sticky in fuzzy ranking.

## L1.6 Settings

### L1.6.1 Settings storage
- User-level: `~/.config/voss-app/settings.json` (or platform equivalent).
- Workspace-level: `.voss/settings.json` (workspace wins for overlapping keys).

### L1.6.2 Settings UI
- Two-pane: search + category nav left, form right.
- "Edit as JSON" link in every section → opens raw file in OS default editor (L4+ will offer in-app editor).

### L1.6.3 Settings categories (L1)
- **Appearance:** theme · font family · font size · line height · cursor shape.
- **Terminal:** default shell · scrollback size · bracketed-paste warnings · cursor blink · bell.
- **Layout:** default preset · pane border visibility · focus follows mouse.
- **Keybindings:** profile (VSCode default, tmux additions) · custom map.
- **Project:** auto-restore panes on open · default project folder.
- **Updates:** auto-check · channel (stable/beta).
- **Telemetry:** OFF default · crash reports opt-in · usage analytics opt-in.

### L1.6.4 Keybinding profiles
- VSCode-default ships baseline.
- "tmux-friendly" additions: `⌘B` prefix mode for nostalgic users.
- Custom map via `.voss/keymap.json` — overrides any profile.

## L1.7 Status Bar

### L1.7.1 Left cluster
- Project name (clickable → recent workspaces).
- Git branch (read-only display in L1, full SCM in L4+).

### L1.7.2 Center cluster
- Active pane: cwd · shell · pid.

### L1.7.3 Right cluster
- Pane count: `▢ 4`.
- Cost meter stub: `$0.00` (active in L2).
- Notification bell with badge.
- Settings cog (click → settings).

### L1.7.4 Click-to-detail
- Each cluster expandable on click (popover).

## L1.8 Notifications

### L1.8.1 Toast surface
- Bottom-right, stacked, 6s auto-dismiss (sticky errors).
- Categories: info · success · warn · error.

### L1.8.2 v0 sources
- Pane process exited non-zero.
- Layout saved/loaded.
- Settings reload.
- Update available.
- App-level errors.

### L1.8.3 Notification log
- Bell icon → last 100 notifications.
- Clear all.

## L1.9 Session Persistence

### L1.9.1 What persists across restart
- Open project.
- Pane tree (layout) — geometry preserved.
- Per-pane: cwd, shell, last 2k scrollback lines.
- Focused pane.
- Active layout preset.

### L1.9.2 What does NOT persist
- Running processes (panes restart with `[restored]` banner; user re-launches commands).
- Live PTY state (signals, env mutations after spawn).

### L1.9.3 Storage
- `.voss/session.json` per project.
- `~/.config/voss-app/global-session.json` for project-less mode.

## L1.10 Onboarding

### L1.10.1 First-run wizard
- Welcome screen → pick theme → pick shell → done.
- No API keys requested in L1 (no Voss yet).

### L1.10.2 Empty-state UI
- New window with no project: prompt to "Open folder" or "Start without a project".
- Empty pane area: keyboard hint `⌘\` to split.

### L1.10.3 In-app help
- Help menu: keybindings cheatsheet (modal), docs link, changelog.

---

## L1 Acceptance Criteria (v0 ship gate)

ALL of these must work, repeatable, without bugs:

1. Install voss-app on mac/linux/win from official artifact.
2. Open app → empty state.
3. Open a folder. Status bar shows project name + git branch.
4. Split into 2×2 grid via 3 splits.
5. Each pane runs an independent shell with project cwd.
6. `⌘1-4` focus works. Click-to-focus works.
7. Switch layout preset to `pipeline` → panes reorder, none killed.
8. Resize pane via mouse drag and keyboard.
9. Save layout as "build-watch". Reload layout from palette.
10. Run `vim`, `htop`, `tmux` inside a pane — full TTY support including alt-screen.
11. Copy text from one pane, paste into another.
12. Quit app. Reopen. Project + panes restored (processes re-launched by user).
13. Open settings, change theme, font size, shell. Persists across restart.
14. Customize a keybinding. Persists.
15. No crashes or PTY leaks over a 24-hour soak test with 8 active panes.

If any of 1–15 fails, L1/v0 doesn't ship.

---

# LAYER 2 — Voss Harness Substrate (v1)

Adds: any pane can be **promoted to a Voss cell**. Voss harness now in the binary or bundled. Agent UX enters the app.

## L2.1 Cell Promotion

### L2.1.1 Promote command
- Pane menu (`⋯`) → "Promote to Voss cell".
- Confirms: kill current shell? (Y/N — default N: shell hidden, kept alive for restore).
- Spawns `voss --ipc-mode jsonl --cwd ... --loop main.voss` in place.

### L2.1.2 Cell HUD (header replaces pane header)
- `● role · model · cwd · iter N/M · cost · ⟳ loop.voss`
- Identical to sketch 001 Variant B cell header.

### L2.1.3 Demote
- "Demote to shell" reverses promotion. Cell session preserved in `.voss/sessions.sqlite`.

## L2.2 Cell Lifecycle

### L2.2.1 Spawn / kill / restart
- Spawn: fork `voss` subprocess with cell config (JSON via stdin).
- Kill: SIGTERM, fallback SIGKILL after 5s.
- Restart: same config, fresh session OR resume from last (user choice).

### L2.2.2 Crash policy
- Voss process exits non-zero → red banner with stderr tail.
- Auto-restart only if cell was idle > 30s before crash.
- Reviewer cell: never auto-restart while main is mid-write.

### L2.2.3 Persistence
- `.voss/sessions.sqlite` managed by harness — turns, tool calls, costs.
- Layout file (`.voss/layouts/<name>.json`) lists cells with config refs.

## L2.3 Cell Render

### L2.3.1 Streaming tokens
- Token-by-token append to pane body.
- Inline cursor block during stream.

### L2.3.2 Glyph-prefix line types
- `❯` user message
- `⏵` tool call (dim color)
- `※` reviewer critique (amber)
- `⊕` patch / diff
- Plain (no glyph) = assistant text

### L2.3.3 Tool call cards
- Expandable inline blocks showing tool name, args (truncated), result (truncated).
- Click to expand full.

### L2.3.4 Diff rendering
- File writes shown as `+/-` colored lines inline.
- Click to open full diff in modal.

## L2.4 Permissions UX

### L2.4.1 Approval prompts
- Native Tauri dialog or in-app modal.
- File write: filename + diff preview · Accept / Reject / Always-this-file.
- Shell exec: command + cwd · Accept / Reject / Always-this-exact-cmd.
- Network fetch: URL · Accept / Reject / Always-this-domain.

### L2.4.2 Policy editor
- Settings → Permissions → GUI for `.voss/policy.yaml`.
- Rules: tool · glob/regex · decision.

### L2.4.3 Reviewer constraints
- Reviewer cell locked to read-only tools — enforced at cell config, UI prevents promotion of reviewer with write tools.

## L2.5 Cost & Budgets

### L2.5.1 Live meter
- Status bar `$0.42` updates per token.
- Click → popover with per-cell + per-model breakdown.

### L2.5.2 Budgets
- Per-cell `max_cost_usd` (cell suspends at limit).
- Per-project session budget.
- Toast on $1 / $5 / $20 thresholds (configurable).

## L2.6 Reviewer-as-Pair-Programmer (the L2 demo)

### L2.6.1 Attach reviewer
- Pane menu → "Attach reviewer". Spawns reviewer cell in a new pane (below or right of main, based on layout preset).
- Reviewer config: `loop: reviewer.voss`, model defaults to haiku-class, read-only policy locked.

### L2.6.2 Trigger
- Reviewer subscribes to main cell's `turn_end` event.
- Fires once per main turn. Sees full turn summary + tool history.

### L2.6.3 Critique surface (L2 — terminal-grid only)
- Critiques appear in reviewer's pane body, glyph-prefixed `※`.
- Severity color (amber / red / green).
- No editor gutter pins in L2 (no editor pane exists yet — pushed to L4+).

### L2.6.4 Apply suggestion
- Reviewer suggestion includes a proposed patch (when applicable).
- `⌘.` applies the patch to filesystem (with permission prompt).

## L2.7 Multi-Cell Wiring (basic)

### L2.7.1 Event bus
- Unix-socket broker in `voss-app-core`.
- Events: `turn_start · turn_token · tool_call · tool_result · turn_end · error · dsl_reload · file_touched`.

### L2.7.2 Subscribers (v1)
- Reviewer cells subscribed to a named target cell.
- Status bar subscribed to cost + cell-count.
- Notifications subscribed to severity-high events.

### L2.7.3 No DSL wiring yet
- L2 hard-codes the reviewer subscription pattern.
- General `.voss` event wiring is L3.

## L2.8 Cell Configuration UI

### L2.8.1 Config form
- Pane menu → "Cell config…" opens form: name · role · model · provider · loop file · cwd · max_iterations · max_cost_usd · tools allowlist · policy ref.

### L2.8.2 Inline model swap
- Header model dropdown swaps model for next turn.

### L2.8.3 Loop selector
- Loop dropdown picks from `apps/voss-app/loops/` defaults + project `.voss/loops/` overrides (L3 fully utilizes the override path).

---

## L2 Acceptance Criteria

1. Promote any pane → spawns `voss` subprocess, header swaps to cell HUD.
2. Type prompt in cell. Tokens stream. Tool calls appear inline. Files get written (with permission prompts).
3. Attach reviewer to a cell. Reviewer fires after each main turn. Critique appears in reviewer pane.
4. Reviewer suggests an edit. `⌘.` applies it. Permission prompt approves.
5. Status bar cost meter updates live.
6. Kill app mid-stream. Reopen. Cell session resumes from last completed turn.
7. Cell crashes (forced). Red banner shown. Restart works.
8. Demote cell back to shell. Cell session preserved.

---

# LAYER 3 — `.voss` DSL Features (v2)

Adds: users program their own agents. Curated loop library shipped. Hot-reload. Inter-cell wiring via DSL.

## L3.1 Curated Loop Library

### L3.1.1 Shipped loops
- `main.voss` — generic driver agent.
- `reviewer.voss` — critique loop with severity rubric.
- `executor.voss` — receives plans, applies changes.
- `watcher.voss` — fs/git event triggers, no LLM by default.
- `planner.voss` — high-level decomposition, hands off to executor.

### L3.1.2 Loop discovery
- "Loop gallery" command palette entry browses shipped + project-local loops with descriptions.

### L3.1.3 Fork to project
- "Fork loop to project" command copies shipped loop into `.voss/loops/<name>.voss` for editing.

## L3.2 Hot-Reload

### L3.2.1 Save → reload
- Saving a `.voss` file triggers `dsl_reload` event for any cell using that file.
- Next iteration uses new loop. Mid-iteration changes deferred.

### L3.2.2 Hot-reload indicator
- Cell header shows `⟳ loop.voss` magenta badge briefly after reload.

### L3.2.3 Failure handling
- Parse errors surface as toast + cell stays on old loop.

## L3.3 Inter-Cell DSL Wiring

### L3.3.1 Subscribe primitive
```voss
on_event(pane: "main", type: "turn_end") {
  critique(context: pane.last_turn)
}
```
Any cell can subscribe to any other cell's events.

### L3.3.2 Inject primitive
```voss
inject_context(pane.last_turn.summary)
```
Pull data from another cell into this one's next turn.

### L3.3.3 Spawn primitive
```voss
spawn(loop: "executor.voss", pane: "right") { plan: this.plan }
```
A cell can spawn another cell programmatically.

### L3.3.4 Pane addressing
- Named panes (`main`, `reviewer`, `executor`) declared in `.voss/layouts/<name>.json`.
- Positional (`pane.right`, `pane.below`).
- Tagged (`pane[role: "reviewer"]`).

## L3.4 DSL Editor Surface

### L3.4.1 Syntax highlighting
- `.voss` files highlighted in pane scrollback (when shown via `cat` or similar).
- Future Monaco editor pane (L4+) will get full LSP.

### L3.4.2 In-app loop viewer
- Cell header `⟳` indicator clickable → opens loop file in OS default editor.
- Reload triggered automatically on file save (watched).

## L3.5 Layout Preset Semantics

L3 promotes presets from visual templates to behavioral templates.

- **fanout** = source cell broadcasts to N receivers. Auto-wires `on_event(pane:"source", type:"turn_end") { ... }` in receivers.
- **pipeline** = sequential context flow. Each cell injects predecessor's last turn.
- **swarm** = N worktrees, same prompt, race semantics. Worktrees managed by L3 worktree service.
- **watchers** = passive subscribers to a main cell. Auto-attach reviewer + test-watcher + lint-watcher.

Selecting a preset offers "wire as preset" — user can decline and keep purely visual.

---

## L3 Acceptance Criteria

1. Save a `.voss` file → cell hot-reloads, magenta indicator flashes.
2. Write `on_event(pane:"main", type:"turn_end") { ... }` in reviewer.voss → reviewer wakes on main turn end.
3. "Fork loop to project" creates editable copy. Edits persist.
4. Select "fanout" layout preset → choose "wire as preset" → broadcast actually works (source turn end fans out to 3 receivers).
5. Parse error in `.voss` shows toast, doesn't crash cell.

---

# LAYER 4+ — Deferred Surfaces

**Status:** uncommitted. Evaluate after L3 ships. Not promised.

## L4.A Editor Pane
- Monaco multi-tab inside a pane slot.
- LSP integration (TS, Python, Rust day one).
- Gutter pins for reviewer critique (reviewer cell would need to know about the editor — adds coupling).
- `⌘K` selection → diff preview → apply.
- Ghost-text autocomplete via dedicated completion cell.

## L4.B File Tree Pane
- Sidebar tree, expand/collapse, ops.
- Agent-touched badges (consumes `file_touched` events from L2).
- Drag-to-context-inject.

## L4.C Source Control Pane
- Git status, stage hunks, commit, branch ops.
- Diff viewer.
- Pre-commit reviewer hook.
- Worktree manager (powers L3 "swarm" preset properly).

## L4.D Search Pane
- ripgrep-backed find/replace.
- Send-results-to-cell.

## L4.E Replay & Audit
- Turn timeline scrubber.
- Branch-from-turn (fork a cell at turn N into a new cell).
- Export session as JSONL.

## L4.F Cells Overview
- Cross-project cells dashboard. Bulk kill/restart.

## L4.G Cost Dashboard
- Historical charts. Per-project, per-model.

## L4.H ⌘K Inline Edit (outside editor pane)
- Even without Monaco, selection in terminal output could feed ⌘K. Possible L2 if scoped down.

---

# What voss-app is NOT (cross-layer)

- ⛔ Cloud-hosted sessions — local-first only.
- ⛔ Anonymous telemetry on by default.
- ⛔ Vendor lock on agent loops — `.voss` is always editable.
- ⛔ Chat-only mode as the primary surface.
- ⛔ Built-in debugger UI.
- ⛔ Visual builder for `.voss` (text-first; defer indefinitely).
- ⛔ Always-on agent rewrite of every keystroke.
- ⛔ Voss exposed before user opts in — L1 user can ignore Voss forever.

---

# Spec-Phase Readiness Checklist

Before invoking `/gsd:spec-phase` for L1:

- [ ] Layer ordering locked (✅ this doc)
- [ ] L1 feature list complete (✅ this doc)
- [ ] L1 acceptance criteria defined (✅ this doc)
- [ ] Variant B aesthetic locked (✅ sketch 001)
- [ ] Tauri + Solid + xterm + portable-pty stack confirmed (✅ CONCEPT §6)
- [ ] Monorepo layout decided (✅ CONCEPT §8)
- [ ] Open questions in CONCEPT §10 closed (⏳ 9 remaining)
- [ ] Public ship name decided (⏳ working: voss-app)
- [ ] Default shell behavior on pane open (⏳)
- [ ] Pane lifecycle on shell exit (⏳)
- [ ] Distribution channel + signing strategy (⏳)
- [ ] Telemetry policy (⏳)

Once `⏳` rows close, spec-phase can lock the L1 contract.
