# voss-app — Feature Catalog

> Companion to `CONCEPT.md`. Concept defines the *why* and *how*. This doc defines the *what* — every user-facing surface, what it does, what ships in v0 vs later, and how it touches the Voss substrate.
>
> **Legend:** ✅ v0 ships · ⏳ v1 backlog · 🔮 v2+ · ⛔ never

---

## A. Workspace & Project

### A1. Open / recent workspaces ✅
- Open folder picker. Drag-drop folder onto app icon.
- Recent workspaces list (last 10), pinned favorites.
- "Workspace" = filesystem folder + `.voss/` config dir (auto-created on first open).
- Multi-root workspaces ⏳ — v0 single root only.

### A2. Project config (`.voss/`) ✅
- `.voss/policy.yaml` — permission policy (read auto, write prompt, exec prompt).
- `.voss/loops/*.voss` — project-specific loop overrides (fallback to `apps/voss-app/loops/`).
- `.voss/sessions.sqlite` — per-cell session persistence (managed by Voss harness).
- `.voss/secrets/` — gitignored, encrypted at rest. API keys per-project.
- `.voss/cells.json` — saved cell layouts (main + reviewer config).

### A3. Workspace state restore ✅
- Reopen project → cells resume from last session.
- Editor tabs restore. Terminal tabs restore (shell only — cell terminals require user confirm to respawn).
- Last focused pane restored.

### A4. Multi-window ⏳
- One project per window v0. Multi-window v1.

---

## B. File Explorer

### B1. Tree view ✅
- Standard expand/collapse tree.
- Lazy load deep dirs.
- Respects `.gitignore` (toggle to show hidden).
- File icons by extension.

### B2. File operations ✅
- New file, new folder, rename, delete, duplicate, copy path, reveal in OS.
- Right-click context menu.
- Keyboard: `↑/↓` nav, `↵` open, `F2` rename, `⌫` delete (prompt).

### B3. Agent activity badges ✅
- Files touched by a cell this session get a colored dot in tree.
  - Green = clean edit applied
  - Amber = pending reviewer pin
  - Red = reviewer blocked
- Hover → tooltip "modified by `main` · 14:02"
- Dot clears on commit.

### B4. Drag to context ⏳
- Drag file from tree → drop on Voss cell input → injects path as context.

### B5. Search & filter ✅
- Filter box at top of tree (`⌘⇧F` from anywhere).
- Filters by filename substring.

---

## C. Editor (Monaco)

### C1. Multi-tab editor ✅
- Tabs across top, drag to reorder, drag to split.
- Unsaved indicator (dot in tab).
- `⌘W` close, `⌘⇧T` reopen, `⌘P` quick open.
- Pinned tabs.

### C2. Split view ✅
- Vertical and horizontal splits, up to 4 panes.
- Drag tab to edge to split.

### C3. LSP integration ✅
- Day-one languages: TypeScript, Python, Rust.
- Hover, go-to-definition, find-references, rename symbol, completion (LSP-driven, not AI), diagnostics in gutter.
- Format-on-save (configurable).
- LSP servers managed by `voss-app-core` LSP host.

### C4. Gutter pins (reviewer surface) ✅
- Reviewer turn_end produces critique → pin glyph `※` in gutter at target line.
- Severity color: amber medium, red high, green positive (rare).
- Click pin → reviewer detail in side panel (full critique + suggested fix preview).
- Hover pin → tooltip.
- Pin "staleness" — when the line is edited after pin created, pin is marked stale (dimmed, struck-through glyph). Stale pins auto-clear on next reviewer turn.
- Multiple pins per line collapse to badge with count.

### C5. ⌘K inline edit ✅
- Select code (or place caret) → `⌘K` → floating prompt input.
- Prompt → ad-hoc Voss cell spawns with selection as context, streams diff.
- Diff renders inline as ghost-text overlay on selection.
- `⌘.` accept, `Esc` reject, `⌘⌫` reject + retry.
- Cell tears down after accept/reject. (Lifecycle is "ephemeral" — fresh context each invocation.)
- Cell selection: per-project default model (configurable; ships with `claude-sonnet-4-6`).

### C6. Ghost-text autocomplete ⏳
- v1. Wired via Monaco inline-completions API + dedicated low-latency completion cell (Haiku-class or local model).

### C7. Right-click → "Ask Voss" ⏳
- v1. Right-click selection → opens ad-hoc cell in side panel pre-loaded with selection.

### C8. Code lens / inline actions ⏳
- v1. Reviewer suggestions can render as code-lens above the line: "💡 reviewer: thread max_iterations through ctor · Apply".

### C9. Themes ✅
- Dark default (sketch 001 Variant B tokens).
- Light theme ⏳.
- User CSS override via `.voss/theme.css`.

### C10. Editor settings ✅
- Font family, size, line height, tab size, indent guides, word wrap, render whitespace, ruler at N cols.
- Configurable per workspace via `.voss/settings.json`.

---

## D. Integrated Terminal

### D1. xterm + PTY ✅
- Native PTY via `portable-pty` Rust crate.
- xterm.js renders.
- Default shell from `$SHELL` (zsh/bash/fish).
- Inherits workspace cwd.

### D2. Multi-tab terminal pane ✅
- New tab `⌘T` (when terminal pane focused).
- Splits `⌘\` horizontal, `⌘⇧\` vertical.
- Tab names = cwd basename, editable.

### D3. Promote-to-cell ✅
- Right-click terminal tab → "Promote to Voss cell".
- Existing PTY snapshot becomes initial context.
- Cell spawns w/ `tools: [bash, fs_read, fs_write, ...]`.
- Visual indicator: tab gets `●` colored dot, header switches to cell HUD (model, cost, iter).
- Demote back to plain shell via same menu.

### D4. Voss output rendering ✅
- When promoted, output renders with B's glyph-prefix lines (`❯` user, `⏵` tool, `※` reviewer).
- Plain shell mode = raw xterm.

### D5. Send-to-cell pipe ⏳
- Right-click selection in terminal output → "Send to Voss cell" → injects as context.

### D6. Find in terminal ✅
- `⌘F` searches scrollback.

---

## E. Source Control (Git)

### E1. Status pane ✅
- Sidebar tab showing: staged · unstaged · untracked · merge conflicts.
- File-level diff stats (+N -M).
- Click file → diff view in editor.

### E2. Stage / unstage ✅
- Click ⊕ next to file (stage all) or specific hunks (stage hunk).
- Drag hunks between staged/unstaged.

### E3. Commit ✅
- Inline message input (multi-line, conventional-commit syntax highlighting).
- `⌘⏎` commit.
- Signing config respected.
- AI-suggest commit message ⏳ (v1, requires a small Voss cell call).

### E4. Branch ops ✅
- Status bar shows current branch · click → switcher with search.
- Create branch, checkout existing, delete (with confirm).
- Pull / push / fetch — buttons + keybinds.

### E5. Diff view ✅
- Side-by-side or inline.
- Reviewer pins overlay in diff view (so reviewer can flag staged hunks before commit).

### E6. Log / history ⏳
- Commit graph view v1.

### E7. Worktree manager ⏳
- v1 for grid swarm mode. Spawn N worktrees from one branch, attach cells.

### E8. Pre-commit reviewer hook ⏳
- v1. Auto-spawn reviewer cell on stage → critique pending commit → block / warn / pass.

---

## F. Global Search

### F1. Find in files ✅
- `⌘⇧F` opens search panel.
- ripgrep-backed, streaming results.
- Regex, case, whole-word, file include/exclude globs.

### F2. Replace in files ✅
- Toggle to replace mode.
- Preview before apply, per-occurrence accept/reject.

### F3. Ask Voss about results ⏳
- v1. "Send all results to a Voss cell as context."

### F4. Search by symbol ✅
- LSP-backed workspace symbol search (`⌘T`).

---

## G. Command Palette

### G1. Quick-open files ✅
- `⌘P` — fuzzy file open.

### G2. All commands ✅
- `⌘⇧P` — every command in the app, fuzzy.
- Categories: View, Edit, Git, Voss, Cell, Terminal, Search, Settings, Help.
- Recent commands stickier in ranking.

### G3. Voss-specific commands ✅
Catalog (v0):
- `Voss: Spawn new cell`
- `Voss: Attach reviewer to active cell`
- `Voss: Detach reviewer`
- `Voss: Reload loop (`⌘L`)` — hot-reload cell's `.voss` file
- `Voss: Switch model for active cell`
- `Voss: Show session cost`
- `Voss: Show event log` — debug stream of bus events
- `Voss: Replay last turn` ⏳
- `Voss: Open .voss policy`
- `Voss: Fork loop to project` — copies default into `.voss/loops/`

### G4. Inline command args ⏳
- Commands can accept inline args: `Voss: Spawn cell with model claude-haiku-4-5`.

---

## H. Voss Panel (the differentiated AI surface)

### H1. Default layout ✅
- Right side panel, collapsible (`⌘⇧V` toggle).
- Top: `main` cell (full height by default).
- Bottom (collapsed by default): `reviewer` cell — expands when first critique arrives.
- Both render exactly like sketch 001 Variant B cells: 22px header, glyph-prefix lines, inset-shadow focus, monospace.

### H2. Cell controls ✅
- Header has: role label · model picker (dropdown) · cwd indicator · iter `N/M` · session cost · `⟳ loop.voss` hot-reload indicator.
- Footer: prompt input (`❯`), broadcast hint dim.
- `⌘L` reloads cell's `.voss` from disk.
- `⌘.` applies highlighted reviewer suggestion.

### H3. Cell persistence ✅
- Cell state in `.voss/sessions.sqlite` (managed by Voss harness).
- Surviving restart: turns, tool history, last model/loop.

### H4. Cell crash handling ✅
- If `voss` subprocess dies, cell shows red banner with stderr tail + "Restart" button.
- **Reviewer cell:** never auto-restarts if main cell is mid-write (file lock held). Manual restart only.
- Main cell auto-restarts on crash if last turn was idle > 30s; otherwise prompts.

### H5. Swap loop / model live ✅
- Header dropdown switches model — next turn uses new model.
- File menu → "Edit cell's loop" opens `.voss` in editor. Save triggers hot-reload (event `dsl_reload`).

### H6. Cell history navigation ✅
- Scrollback in cell body. Jump to turn N via outline at top.
- "Time-travel" ⏳ — branch from any past turn into a new cell.

### H7. Multi-cell grid mode ⏳
- v1. Full-window grid layout (sketch 001 Variant B). Layout presets: fanout · pipeline · swarm · watchers. Press `⌘G` to switch in/out.

### H8. Cell config UI ✅
- "Configure cell…" opens form: name, model, provider, max_iterations, max_cost_usd, loop file path, tools allowlist.

---

## I. Status Bar

### I1. Left cluster ✅
- Git branch (clickable → branch switcher).
- Errors `⊗ N` / warnings `△ N` (clickable → problems panel).
- LSP status (`✓ pyright` / `⊘ no server`).

### I2. Center cluster ✅
- Current file: language · encoding · EOL · indent · line:col.

### I3. Right cluster ✅
- **Voss cells active:** `● 2 cells` (clickable → cells overview).
- **Session cost:** `$0.42` (clickable → cost breakdown).
- **Token bar:** thin gradient bar showing consumed / budget.
- Notifications counter `🔔 N`.

### I4. Click-to-detail ✅
- All right-cluster items expand to popover with detail (per-cell cost, recent events, etc).

---

## J. Settings

### J1. Settings UI ✅
- File: `.voss/settings.json` (workspace) and `~/.voss/settings.json` (user) — workspace wins.
- JSON-backed, with GUI form. Two-pane: search + form on left, raw JSON on right (editable, validated).

### J2. Categories ✅
- Editor (font, theme, formatting)
- Voss (default model, default loops, max iter, max cost)
- Permissions (default policy)
- Keybindings (profile selector + custom map)
- Git (signing, commit template)
- LSP (server paths)
- Terminal (shell, font, scrollback)
- Telemetry (off by default; opt-in toggles)

### J3. Keybinding profiles ✅
- Ships: VSCode (default), Vim-mode ⏳, Emacs ⏳.
- Custom map via `.voss/keymap.json`.

### J4. Provider/auth ✅
- Manage API keys (Anthropic, OpenAI, others via litellm).
- Stored via OS keychain (existing `voss/harness/auth.py` integration).
- Per-project override.

### J5. Sync settings ⏳
- v1 — sync user settings via GitHub gist or own cloud.

---

## K. Notifications

### K1. Toast surface ✅
- Bottom-right corner, stacked, auto-dismiss after 6s (sticky for errors).
- Categories: info, success, warn, error.
- Click → optional detail action.

### K2. Sources ✅
- Cell `turn_end` if cell not focused → "main: completed turn 5".
- Reviewer critique posted (high severity only).
- Cost threshold hit ($1, $5, $20 configurable).
- Cell crashed.
- File conflict on external change.
- Git push/pull complete.

### K3. Notification log ✅
- Status bar bell icon → history of last 100 notifications.

---

## L. Cells Lifecycle & Substrate

### L1. Cell spawn ✅
- Triggered by: app open (restore), user clicks "+ cell" in panel, command palette, ⌘K (ephemeral).
- Spawn = fork `voss --ipc-mode jsonl --cell-id X --loop Y --cwd Z`.
- Cold start ~300ms target.

### L2. Cell config schema ✅
```json
{
  "id": "main",
  "name": "main",
  "role": "driver",
  "model": "claude-sonnet-4-6",
  "provider": "anthropic",
  "loop": "main.voss",
  "cwd": "${workspace}",
  "max_iterations": 12,
  "max_cost_usd": 5.00,
  "tools": ["fs_read", "fs_write", "bash", "grep"],
  "policy": "workspace-default"
}
```

### L3. Cell-to-cell wiring ✅
- Reviewer cell subscribes to main's events via `.voss`:
  ```voss
  on_event(pane: "main", type: "turn_end") {
    critique(context: pane.last_turn)
  }
  ```
- Subscriptions registered with shell broker on cell startup.

### L4. Cell budgets ✅
- Per-cell `max_cost_usd` enforced inside the harness (existing Voss feature).
- Per-project budget aggregate in status bar.
- Hard limit: cell suspends, surface in UI for user to raise or kill.

### L5. Replay ⏳
- v1 — every event in `sessions.sqlite`, scrubber UI to step backward.

### L6. Cells overview pane ⏳
- v1 — list all cells across all projects, kill/restart in bulk.

---

## M. Permissions UX

### M1. Approval prompts ✅
- File write: native dialog with diff preview · Accept / Reject / Accept always for this file / Open in editor.
- Shell exec: dialog with full command + cwd · Accept / Reject / Accept always for this exact cmd.
- Network fetch: domain + path · Accept / Reject / Accept always for domain.

### M2. Policy editor ✅
- Settings → Permissions opens GUI for `.voss/policy.yaml`.
- Rules: tool name + glob/regex + decision (auto / prompt / deny).
- Reviewer cell policy locked to read-only (UI prevents elevation).

### M3. Approval inbox ⏳
- v1 — queue multiple prompts so user can batch-review.

---

## N. Cost & Budgets

### N1. Live meter ✅
- Status bar shows session total.
- Click → popover with per-cell + per-model breakdown.

### N2. Thresholds & alerts ✅
- Configurable: $1, $5, $20 — toast on cross.
- Hard ceiling per cell (`max_cost_usd`) suspends cell.

### N3. Historical dashboard ⏳
- v1 — daily/weekly chart, per-project, per-model.

---

## O. Replay & Audit ⏳ (v1)

- Turn timeline scrubber inside Voss panel.
- Branch-from-turn — spawn a new cell with state at turn N.
- Export session as JSONL for sharing/debugging.

---

## P. Extensions / Plugins 🔮 (v2+)

- `.voss` files as installable workflows (marketplace deferred indefinitely).
- Theme packs.
- Custom LSP additions.
- Native ext API only if there's user demand.

---

## Q. Onboarding ✅

- First-run wizard: pick a provider, paste API key, validate, pick default model.
- Sample project: clone a small repo, open it, walk through ⌘K + reviewer demo.
- "What's a cell?" tooltip on first sidebar interaction.
- Help menu links to docs + Discord/GitHub.

---

## R. What's Explicitly Not in voss-app

- ⛔ Cloud-hosted sessions — local-first only.
- ⛔ Anonymous telemetry on by default.
- ⛔ Vendor lock on agent loops — `.voss` is always editable.
- ⛔ Chat-only mode as the primary surface.
- ⛔ Built-in debugger UI (defer to LSP / DAP integration v2+).
- ⛔ Visual builder for `.voss` (text-first; GUI builder is v2+ at earliest).
- ⛔ Always-on agent rewrite of every keystroke (user owns the keyboard).

---

## v0 Feature Acceptance (the door to spec phase)

For v0 to ship, ALL of these must be true in a real workspace:

1. Open a folder. Tabs persist across restart.
2. Edit a Python file with LSP completion + diagnostics.
3. Save the file. Watcher updates tree.
4. Stage + commit via SCM pane.
5. Open terminal, run `pytest`.
6. Promote terminal to Voss cell.
7. Type prompt in Voss panel `main` cell. Cell streams. Edits a file.
8. Reviewer cell auto-runs on main's `turn_end`. Posts a pin in editor gutter.
9. Click pin → see critique. `⌘.` applies suggested edit.
10. Status bar shows live cost + cell count.
11. `⌘K` on a selection → diff preview → accept.
12. Quit + relaunch — everything resumes.

If any of 1–12 fails, v0 doesn't ship.
