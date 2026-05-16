# voss-app — Concept

> Status: **concept**, not spec. Decisions locked below survive into spec phase; open questions must close before `/gsd:plan-phase`.

## 1. Mission

**voss-app is a desktop code editor with the Voss harness as its agent substrate.** From the outside, it looks like Cursor / Zed / VSCode — file tree, tabbed editor, integrated terminal, source control, command palette, search. Inside, every AI surface is powered by Voss processes running in the background: not vendor-controlled chat, but user-programmable agent loops written in `.voss`, isolated per cell, replayable, auditable, budget-bounded.

**The bet:** a developer should be able to use voss-app like any modern editor and never need to know what a "harness cell" is — until the moment they want to program their own reviewer, spawn a parallel agent, or replay a turn. Then the substrate is right there.

**Primary user (v0):** developers who already use Cursor/Zed and want the AI parts to be transparent, programmable, and not phoning home. Not "AI for non-devs," not "raw harness for Voss devs only."

**Core value prop:** "It's a real editor. The AI is yours. Every turn is on disk."

**Anti-mission:**
- Not a chat client (chat is one surface, not the product).
- Not a terminal-first power tool (Warp/Wave own that lane).
- Not a multi-agent orchestration dashboard with no editor (the grid is *inside* the editor, not the editor's replacement).
- Not a vendor-locked AI loop (`.voss` is user code; harness is open).

## 2. Product Shape — ADE Feature Surface

voss-app is a **table-stakes IDE first**. The Voss substrate enables differentiated AI surfaces *on top of* that. v0 ships the table stakes plus exactly one differentiated AI surface (reviewer-as-pair-programmer).

### 2.1 Table-stakes (must work like a normal editor)

| Surface | v0 scope | Notes |
|---|---|---|
| Workspace | Open folder; recent workspaces list | Project = folder + `.voss/` config dir |
| File explorer | Tree view, expand/collapse, new file/folder, rename, delete | Right-click context menu |
| Editor | Monaco multi-tab, split view (vertical/horizontal) | Monaco LSP client (TS/Python/Rust day one) |
| Integrated terminal | xterm.js + native PTY, multiple tabs | Same pane can be "promoted" to a Voss cell |
| Source control | Git status, stage hunks, commit, branch switch, diff view | Reuse `git2` via Rust core, render in TS |
| Global search | ripgrep-backed, replace-across-files, regex | Side panel |
| Command palette | `⌘P` files · `⌘⇧P` commands | Voss commands live here too |
| Settings | UI for theme, keybindings, models, providers, policies | JSON-backed, editable as file |
| Status bar | Branch · errors · line/col · language · **Voss cell count · session $** | Cost meter persistent |
| Keybindings | VSCode-default profile out of the box | Vim/Emacs profiles v1 |
| Themes | Dark default (variant B sketch), light optional | User CSS overrides |
| Notifications | Toast surface for agent events, cost thresholds, errors | Dismissable, queued |

This is the "boring" layer. It must feel right, or the differentiated surfaces never get used.

### 2.2 Differentiated AI surfaces (where Voss shines)

| Surface | What it does | v0? |
|---|---|---|
| **Voss Sidebar Panel** | Default-shown right panel. Houses the main cell + reviewer cell. Replaces "AI chat sidebar" of Cursor/Zed. | ✅ v0 |
| **Inline reviewer pins** | Reviewer critique surfaces as clickable margin pins in editor gutter, linked to specific lines | ✅ v0 |
| **⌘K inline edit** | Select code → ⌘K → prompt → diff preview → accept/reject. Backed by a Voss cell spawned ad-hoc. | ✅ v0 |
| **Ghost-text autocomplete** | Cursor-style inline completion. Backed by a Voss cell with `loop.completion.voss`. | ❌ v1 — needs LSP-level integration |
| **Terminal-as-cell promotion** | Right-click terminal tab → "Promote to Voss cell" → runs an agent in that PTY context | ✅ v0 |
| **Cell Grid mode** | Full-window 2×2/3×3 grid (sketch 001 design) — power users compose pipelines/swarms | ❌ v1 — backlog from sketch 001 |
| **Diff-before-commit reviewer** | Pre-commit cell auto-reviews staged diff, blocks/warns/passes | ❌ v1 |
| **File-tree agent badges** | Tree icons show which files agents touched in current session | ✅ v0 (basic, just colored badge) |
| **Turn replay scrubber** | Scrub through past turns, see tool calls, branch from any point | ❌ v1 |
| **Voss cost dashboard** | Per-project, per-cell, per-model spend over time | ❌ v1 |
| **DSL editor with LSP** | `.voss` files get full LSP — completion, diagnostics, hover | ❌ v1 (basic syntax highlight v0) |
| **Multi-model bench cell** | Same prompt → N models → vote/diff | ❌ v2 |

### 2.3 v0 product surface, end-to-end

User opens voss-app. Looks like Cursor:

- Left sidebar: file tree.
- Center: tabbed Monaco editor.
- Right sidebar: **Voss panel** (collapsible, default-open). Two stacked cells: `main` (the user's driver agent) + `reviewer` (Haiku-class, attached to `main`).
- Bottom: integrated terminal pane (can be promoted to cell).
- Top: command palette `⌘⇧P`.
- Status bar: branch, errors, **session $0.42 · 2 cells**.

User types in `main` cell, agent works, edits files, runs tools. Reviewer cell critiques after each turn-end. Critiques surface both inside reviewer cell *and* as margin pins in the relevant editor lines. User `⌘.` applies a reviewer fix, or clicks pin to navigate.

That's v0. Familiar shape, novel guts.

## 3. v0 Killer Demo — Reviewer-as-Pair-Programmer (Refined)

The single thing v0 must do flawlessly *inside the editor shell*:

> User edits code in Monaco. Hits `⌘K`, asks `main` cell to refactor a function. Main cell streams tokens into the Voss panel and a diff into the editor. Reviewer cell watches each tool call, posts a critique pin in the editor gutter on line 47 ("LoopRunner ctor takes max_iterations but isn't passed through — breaks T1-04"). User clicks pin, sees critique, hits `⌘.`, reviewer's suggested edit applies as a new diff. Commit.

That's it. Two cells, one editor, reviewer-as-pair-programmer surfaced via *gutter pins + sidebar*, not via a grid.

**Why this demo (refined):**
- Lives inside familiar editor UI — no "learn the grid" tax for v0 users.
- Forces the hard infra anyway (subprocess isolation, event bus, streaming tokens, tool-call inspection, diff rendering, gutter decorations).
- Reviewer pattern already lives in `voss/harness/agent/reviewer.voss` — reuses existing harness.
- Story sells to a Cursor user in 30 seconds: "Same shape, but the AI is yours, programmable, replayable, and there's a second model watching every move."

**Out of v0:** grid layouts, broadcast, swarm-on-worktrees, ghost-text autocomplete, replay scrubber, cost dashboard, multi-model bench. All in v1+ backlog.

## 4. Locked Decisions

| Layer | Decision |
|---|---|
| Shell | **Tauri** — Rust core + webview UI |
| UI framework | **Solid** — signal-based, token-rate streaming friendly |
| Styling | Tailwind. Dark theme = sketch 001 Variant B (Minimal Tile). |
| Editor | **Monaco** — full LSP client, multi-tab, gutter decorations API (needed for reviewer pins) |
| Terminal | **xterm.js** + native PTY via Tauri command bridge |
| Source control | `git2` Rust crate in core, render diff/status in Solid UI |
| Search | ripgrep subprocess, structured output streamed to UI |
| Cell process model | **Subprocess per cell** — each cell = own `voss` Python subprocess over JSONL stdio |
| Cell IPC | JSONL framed over stdio + Unix-socket event bus for cell-to-cell |
| State ownership | Shell owns layout/bus/cell-registry. Each Voss process owns its session/turns/memory. |
| Storage | SQLite per project (Voss harness already persists sessions); project metadata in `.voss/` |
| Build | pnpm workspace at root + extend existing Cargo workspace |
| Distribution | DMG / AppImage / MSI via Tauri updater. `@vosslang/cli` unchanged. |
| Monorepo path | `apps/voss-app/` (TS+Tauri+Solid) + `crates/voss-app-core/` (Rust shell core) + `crates/voss-app-ipc/` (typed JSONL protocol) |
| Reviewer trigger | **Per-turn** — fires once on main's `turn_end`. Sees full turn summary + tool calls. ~1 Haiku turn per main turn. |
| Terminal default | **Plain xterm** — shell by default. Right-click → "Promote to Voss cell" converts. Voss is opt-in per pane. |
| v0 AI scope | **Minimal** — reviewer pins + `⌘K` inline edit. No ghost-text autocomplete in v0 (v1 via LSP inline-completions). No chat-on-selection. |
| Loop authoring | **Curated defaults shipped in `apps/voss-app/loops/`** (`main.voss`, `reviewer.voss`). User forks to project `.voss/` to customize. 95% of users never touch. |

## 5. Agent Substrate (How Voss Runs Underneath)

A **cell** = single Voss harness subprocess. Owns: pid, cwd, env, model, provider, budget, `.voss` loop, session SQLite, JSONL stdio pipe, event-bus subscription.

A cell is sovereign. The shell never reaches inside to mutate state. Cells communicate via the event bus only.

**Event bus** (Unix socket, shell-brokered):
```
turn_start    {cell_id, turn_id, prompt}
turn_token    {cell_id, turn_id, token, role}
tool_call     {cell_id, turn_id, tool, args}
tool_result   {cell_id, turn_id, tool, result, duration_ms}
turn_end      {cell_id, turn_id, summary, cost_usd, tokens}
error         {cell_id, type, message}
dsl_reload    {cell_id, file, reason}
file_touched  {cell_id, path, op}  # for file-tree badges
```

Other cells subscribe in `.voss`:
```voss
on_event(pane: "main", type: "turn_end") {
  inject_context(pane.last_turn.summary)
}
```

The editor shell *also* subscribes — that's how reviewer pins, file-tree badges, cost meters, toast notifications, and status bar updates flow into the UI.

Cells outlive editor sessions: kill the app, reopen the project, cells resume from their last session state.

## 6. Stack Detail

### Frontend — `apps/voss-app/src/`
- Solid (reactivity, signal updates per streamed token without React reconciler overhead)
- Tailwind (variant B design tokens)
- Monaco (vendored, lazy-loaded per workspace open)
- xterm.js (terminal pane)
- Existing Voss render logic ported to TS for cell views

### Tauri shell — `apps/voss-app/src-tauri/`
- Thin Rust binary, wraps `voss-app-core`
- Window/menu/tray/OS-integration
- Bridges Solid UI ↔ Rust core via Tauri commands + events
- Auto-updater config

### `crates/voss-app-core/`
- **Workspace manager** — open folder, recent list, `.voss/` config read/write
- **File system service** — watcher, atomic writes, conflict detection
- **Cell supervisor** — spawn/kill `voss` subprocesses, restart-on-crash policy
- **Event bus broker** — Unix socket server, pub/sub
- **Git service** — `git2`-backed status/stage/commit/diff/branch
- **Search service** — ripgrep subprocess wrapper, streaming results
- **PTY service** — terminal pane backend (portable-pty)
- **LSP host** — orchestrate language servers per workspace
- **Settings + keybindings persistence**

### `crates/voss-app-ipc/`
- Typed JSONL schema for cell ↔ shell + cell ↔ cell events
- Rust types ↔ TS types generated from same source (ts-rs or typeshare)
- Versioned envelope

### Voss harness — `voss/` (unchanged path)
- voss-app spawns existing entry point with new `--ipc-mode jsonl` flag
- Existing harness (`agent.py`, `tools.py`, `permissions.py`, `recorder.py`, `tui/renderer.py`) reused as-is
- New `voss/harness/bridge_mode.py` emits events on the contract above

## 7. Permission & Trust Model (v0)

- Per-project policy in `.voss/policy.yaml`.
- Default: read-only tools auto-approve · file writes prompt with diff preview · shell exec prompts with arg preview.
- Reviewer cell is **policy-constrained read-only** — cannot edit files or run shell. Enforced at cell-config level.
- Existing `voss/harness/permissions.py` handles enforcement; shell renders the prompt UX as a Tauri-native dialog.
- Worktree-isolated agents (v1) can run on `auto-approve` policy since blast radius is bounded.

## 8. Monorepo Layout

```
voss/                            # python harness (unchanged)
crates/
  voss-app-core/                 # rust: workspace, cells, bus, git, search, pty
  voss-app-ipc/                  # rust: typed JSONL protocol
  ...existing frozen rust spike  # reference only
apps/
  voss-app/
    CONCEPT.md                   # this file
    src/                         # solid + tailwind UI
      editor/                    # monaco wiring
      terminal/                  # xterm + PTY bridge
      sidebar/                   # voss panel, file tree, search, scm
      grid/                      # v1 grid mode (stubbed v0)
      command-palette/
      status-bar/
    src-tauri/                   # tauri shell, depends on voss-app-core
    loops/                       # ships default `.voss` loops
      main.voss
      reviewer.voss
      completion.voss            # v1
    package.json
    tailwind.config.ts
shared/
  voss-events/                   # ts+rust schema generation
package.json                     # pnpm workspace root
Cargo.toml                       # cargo workspace root (extend existing)
```

## 9. v0 Build Order (rough)

1. **Spike A**: Tauri + Solid + Monaco loads a file. Save works. Status bar shows branch.
2. **Spike B**: Spawn one `voss` subprocess from Rust, render its streaming tokens in Solid panel.
3. **Spike C**: Two cells (main + reviewer), event bus, reviewer subscribes to main's `turn_end`.
4. **Spike D**: Reviewer critique → gutter pin in Monaco. Click pin → side panel detail.
5. **Spike E**: `⌘K` selection-prompt → diff preview → apply.
6. **Spike F**: Integrated terminal (xterm.js + PTY). Promote-to-cell command.
7. **Spike G**: Git status/stage/commit UI.
8. **Spike H**: Global search (ripgrep).
9. **Spike I**: Command palette.
10. **Spike J**: Settings UI + theming + keybindings persistence.

Spikes A–E = the differentiated demo. F–J = the table-stakes shell. Don't ship v0 without both.

## 10. Open Conceptual Questions

Closed (this session):
- Shell tech: **Tauri**
- Cell isolation: **subprocess-per-cell**
- v0 killer demo: **reviewer-as-pair-programmer inside the editor shell** (gutter pins + sidebar, not grid)
- Reviewer trigger: **per-turn** (on main's `turn_end`)
- Terminal philosophy: **plain xterm + promote-to-cell**
- v0 AI scope: **minimal** (reviewer pins + ⌘K only; no ghost-text in v0)
- Loop authoring: **curated defaults in `apps/voss-app/loops/`, opt-in fork to project `.voss/`**

Still open — should close before spec phase:

1. **Public name.** voss-app is working name. Candidates: Voss Studio · Voss · Voss Grid · Voss IDE · fresh name.
2. **Cell crash policy.** Auto-restart on Voss process crash? Surface for user action? Reviewer must never auto-restart silently mid-edit.
3. **Existing harness reuse.** Does `apps/voss-app/loops/main.voss` derive from `voss/harness/agent/loop.voss` or fork? Sync strategy if shared.
4. **Session boundary.** Project-level shared session (cells share context, memory primitives scoped to project) vs cell-level isolated.
5. **Distribution channel.** Direct DMG/AppImage/MSI · Homebrew cask · `@vosslang/cli voss app` subcommand · all three?
6. **Telemetry & privacy.** Local-only default. Opt-in anonymous usage? Crash reports?
7. **`⌘K` cell lifecycle.** Spawn ad-hoc cell per ⌘K invocation (clean, slow) · long-lived `edit` cell reused across invocations (fast, context-bleed risk)?
8. **Pin staleness.** When main cell edits a line that has a reviewer pin attached, does the pin migrate, invalidate, or stick?

## 11. Reference Artifacts

- Sketch 001 (`.planning/sketches/001-voss-grid-shell/`) — Variant B (Minimal Tile) for design tokens, header conventions, glyph affordances. **NB:** sketch 001 was a grid-mode mockup. v0 ships the editor shell first; grid is v1. Design tokens still apply.
- Existing harness: `voss/harness/agent/loop.voss`, `voss/harness/agent/reviewer.voss`, `voss/harness/render.py`, `voss/harness/tui/renderer.py`.
- Frozen Rust spike: `crates/` — reference for IPC and PTY choices.
- Competitor reference points: **Cursor** (chat-sidebar + ⌘K + ghost-text), **Zed** (native speed, AI panel, terminal), **Warp** (terminal blocks, AI mode), **VSCode** (extension surface, Monaco, debugger).
