# voss-app — Concept

> Status: **concept**, not spec. Decisions locked below survive into spec phase; open questions must close before `/gsd:plan-phase`.

## 1. Mission

**voss-app is a desktop terminal-based ADE — a grid-native terminal first, an agent substrate second.** It looks and feels like a power-user terminal (Warp / Wezterm / iTerm lineage) with a grid layout as the primary metaphor (sketch 001 Variant B). The Voss harness and the `.voss` language are roadmap layers added *on top of* a working terminal app, not the v0 deliverable.

**The bet:** ship a great terminal grid app first. Earn the right to integrate agents underneath. Most "agentic IDE" attempts fail by trying to ship the agent stack before the chrome works. voss-app inverts that order.

**Primary user:** developers who live in tmux/Warp/Wezterm and want a faster, grid-native terminal with optional agent powers waiting in the wings. v0 ships to that user with zero Voss exposure.

**Three-layer build, in strict order:**

| Layer | Goal | What ships |
|---|---|---|
| **L1 — Scaffold (v0)** | Terminal-grid ADE that holds its own against Warp | Tauri + Solid + xterm + PTY · grid layout · layout presets · command palette · settings · theme · session persistence. **Zero Voss.** |
| **L2 — Voss substrate (v1)** | Any pane can become an agent cell | Promote-to-cell · subprocess-per-cell over JSONL · streaming token render · tool-call inspector · permission prompts · cost meter · reviewer-as-pair-programmer demo |
| **L3 — `.voss` DSL features (v2)** | Users program their agents | Hot-reload `.voss` · inter-cell event wiring · curated loop library · DSL editor with syntax highlight (LSP optional later) |
| **L4+ — Surfaces (deferred)** | Editor / file tree / SCM if demand exists | Monaco editor pane, file-tree pane, SCM pane, search pane — **not committed to**, evaluated post-L3 |

**Core value prop (per layer):**
- L1: "Grid-native terminal. Tmux ergonomics, modern UX."
- L2: "Promote any pane to an agent. Watch it work, intervene, replay."
- L3: "Your agents are your code. Wire them in `.voss`."

**Anti-mission:**
- ⛔ Not a code editor with AI bolted on (Cursor/Zed own that lane).
- ⛔ Not a chat client.
- ⛔ Not a vendor-locked agent loop.
- ⛔ Not v0-with-Voss-bolted-on — the substrate is opt-in per pane forever.

## 2. v0 (Layer 1) — Terminal-Grid Scaffold

The whole app, v0, with **zero Voss code in the binary**.

### 2.1 What v0 IS

- Tauri shell (Rust core + Solid webview UI).
- Grid of terminal panes. Each pane = xterm.js + native PTY (portable-pty crate).
- Layout presets switcher in titlebar: `fanout · pipeline · swarm · watchers`. (In L1 these are pure layout templates — 1×N, N×1, 2×2, sidebar+main. They become semantically meaningful when L2 lands.)
- Sketch 001 Variant B aesthetic: 22px headers, thin 1px borders, mono everywhere, glyph-prefix lines (`❯` user, `⏵` output), inset-shadow focus.
- Project = folder. App opens a folder, all panes inherit that cwd. `.voss/` dir created (empty in v0, used later).
- Session persistence: panes restore (cwd, shell, scrollback truncated) across relaunch.
- Command palette `⌘⇧P`: split, focus, swap layout, open project, settings.
- Status bar: project · branch (read from git) · pane count · cost meter (stub showing `$0.00` until L2).
- Keybindings (VSCode-default profile + tmux-friendly additions): `⌘1-9` focus, `⌘\` split horizontal, `⌘⇧\` split vertical, `⌘D` fork pane (copy state), `⌘W` close, `⌘T` new pane.
- Settings UI for theme, font, shell, keymap.

### 2.2 What v0 is NOT

- ❌ No Voss harness subprocess code.
- ❌ No JSONL IPC.
- ❌ No agent UI (no "promote to cell", no streaming, no tool inspector).
- ❌ No Monaco / file tree / SCM / search panes.
- ❌ No `.voss` files mentioned in UI.

The cost meter stub and `.voss/` dir are the only forward-references — they exist so L2 doesn't need a schema migration.

### 2.3 v0 success criteria

A user can install voss-app and use it as their daily terminal for a week without ever seeing the word "Voss" in the UI beyond the app name. Tmux/Warp users prefer it for the grid ergonomics. That's the bar.

## 3. v1 (Layer 2) — Voss Substrate

Adds: every pane can be **promoted to a Voss cell**. Promotion = stop the shell, spawn `voss --ipc-mode jsonl --cwd ... --loop ...` in its place. Pane header changes to cell HUD (model · cwd · iter · cost). Pane body renders streaming turns. Tool calls inspectable. Permission prompts native.

v1 also lands:
- Reviewer-as-pair-programmer demo (main cell + reviewer cell auto-attached, reviewer fires on `turn_end`).
- Live cost meter (status bar comes alive).
- Permissions UX (file write / shell exec dialogs).
- Cell crash handling (red banner + restart).

Critically, v1 ships *as an opt-in feature*. Open a pane, type commands like always. Right-click → "Promote to Voss cell" when you want agent powers. The terminal user can ignore Voss forever and the app still serves them.

## 4. v2 (Layer 3) — `.voss` DSL Features

Adds:
- Hot-reload `.voss` files (save → next iteration uses new logic).
- Inter-cell event wiring via DSL (`on_event(pane: "main", type: "turn_end") { ... }`).
- Curated loop library shipped in `apps/voss-app/loops/` (`main.voss`, `reviewer.voss`, `executor.voss`).
- Project-level overrides at `.voss/loops/`.
- Basic syntax highlighting for `.voss` in any future editor pane (full LSP deferred).

## 5. Layer 4+ — Deferred Surfaces

Tracked but uncommitted. Evaluate after L3 ships and we have real users.

- Monaco editor pane (multi-tab, LSP, gutter pins for reviewer critique).
- File tree pane (with agent-touched badges from L2 event bus).
- SCM pane (git status, stage, commit, diff).
- Global search pane (ripgrep).
- ⌘K inline edit (selection → diff preview).
- Pre-commit reviewer hook.
- Turn replay scrubber.

These were prematurely committed in earlier concept rounds. They might land — or voss-app might stay pure terminal-grid + agent-substrate forever. Decide post-L3.

## 6. Locked Decisions (cross-layer)

| Layer | Decision |
|---|---|
| Shell | **Tauri** — Rust core + webview UI |
| UI framework | **Solid** — signal reactivity, token-streaming friendly |
| Styling | Tailwind. Theme = sketch 001 Variant B tokens. |
| Terminal emulator | xterm.js (vendored) |
| PTY backend | `portable-pty` Rust crate |
| Cell process model (L2) | Subprocess-per-cell — own `voss` Python subprocess over JSONL stdio |
| Cell IPC (L2) | JSONL framed over stdio + Unix-socket event bus for cell-to-cell |
| State ownership | Shell owns layout + bus + cell registry. Voss processes own their own session/turns/memory. |
| Storage | SQLite per project under `.voss/sessions.sqlite` (managed by harness when L2 lands; empty in L1). |
| Build | pnpm workspace at root + extend existing Cargo workspace. |
| Distribution | DMG / AppImage / MSI via Tauri updater. |
| Monorepo path | `apps/voss-app/` + `crates/voss-app-core/` + `crates/voss-app-ipc/` (last two empty until L2). |
| Reviewer trigger (L2) | **Per-turn** — fires on main's `turn_end` |
| Loop authoring (L3) | **Curated defaults in `apps/voss-app/loops/`** with opt-in fork to project `.voss/loops/` |

## 7. Agent Substrate Spec (deferred until L2 design phase)

Event bus contract, cell config schema, IPC envelope — all preserved in earlier concept revisions but explicitly out of scope for v0 scaffold. Will reopen at start of L2 spec phase.

## 8. Monorepo Layout

```
voss/                            # python harness (unchanged, used only in L2+)
crates/
  voss-app-core/                 # rust: workspace, panes, PTY, layout, settings, palette
                                 #       (cells supervisor + event bus added in L2)
  voss-app-ipc/                  # empty in L1; lands in L2
  ...existing frozen rust spike  # reference only
apps/
  voss-app/
    CONCEPT.md                   # this file
    FEATURES.md                  # feature catalog mapped to L1/L2/L3
    src/                         # solid + tailwind UI
      grid/                      # pane layout engine
      pane/                      # xterm-backed pane component
      command-palette/
      status-bar/
      settings/
      titlebar/                  # preset switcher, cost meter, project name
      theme/                     # variant B tokens
    src-tauri/                   # tauri shell, depends on voss-app-core
    loops/                       # L3 — empty in L1/L2
    package.json
    tailwind.config.ts
shared/
  voss-events/                   # empty in L1; lands in L2
package.json                     # pnpm workspace root
Cargo.toml                       # cargo workspace root
```

## 9. v0 Build Order

Strict sequential. Each spike must pass acceptance before the next starts.

1. **Spike L1-A**: Tauri + Solid shell loads. Empty window with titlebar. Builds DMG.
2. **Spike L1-B**: One xterm pane wired to PTY. Type, see output. Resize. Scrollback.
3. **Spike L1-C**: Grid engine. Split horizontal/vertical. Focus follows click + `⌘1-9`. Close pane.
4. **Spike L1-D**: Layout presets. `⌘G` cycles fanout/pipeline/swarm/watchers (templates only).
5. **Spike L1-E**: Project open. Folder picker. `.voss/` dir auto-created. cwd propagates.
6. **Spike L1-F**: Session persistence — panes restore across relaunch.
7. **Spike L1-G**: Command palette + keymap profile.
8. **Spike L1-H**: Settings UI. Theme tokens applied. Font/shell config persists.
9. **Spike L1-I**: Status bar live (branch from `git2`, pane count, cost meter stub).
10. **Spike L1-J**: Variant B theme polish + onboarding flow.

That's v0. No Voss yet.

## 10. Open Conceptual Questions

Closed:
- Three-layer build order locked
- Shell tech (Tauri), cell isolation (subprocess), reviewer trigger (per-turn), loop authoring (curated + opt-in fork) all preserved for L2/L3

Still open — should close before L1 spec phase:

1. **Public name.** voss-app working name. Ship name candidates: Voss Grid · Voss Term · Voss · fresh name. Recommend **Voss Grid** for terminal-first positioning.
2. **Default shell behavior on pane open.** Auto-launch `$SHELL` or empty pane awaiting user input?
3. **Pane lifecycle on shell exit.** Close pane, keep open with "exited" indicator, or auto-restart shell?
4. **Layout preset semantics in L1.** Just visual templates, or do they constrain future cell semantics (e.g., "swarm" assumes worktrees)?
5. **Project-less mode.** Can voss-app open without a folder (like Warp's no-project mode)? Or always require a workspace folder?
6. **Cost meter stub UX in L1.** Hide entirely, show `$0.00`, or show "no cells yet" placeholder?
7. **`.voss/` dir creation timing.** On project open (always), on first L2 cell promotion (lazy), or user-prompted?
8. **Distribution channel.** DMG/AppImage/MSI direct · Homebrew cask · `@vosslang/cli voss app` subcommand?
9. **Telemetry & privacy.** Local-only default; opt-in toggles in settings.

## 11. Reference Artifacts

- Sketch 001 (`.planning/sketches/001-voss-grid-shell/`) — Variant B (Minimal Tile) is the locked aesthetic. Cell rendering in sketch maps to L2+ when promoted; L1 panes use same chrome minus the agent HUD elements (no model/iter/cost-per-cell).
- Existing harness: `voss/harness/...` — untouched in L1, integrated in L2.
- Frozen Rust spike: `crates/` — reference for PTY and IPC choices when L2 starts.
- Competitor reference: **Warp** (terminal blocks, AI mode), **Wezterm** (config-driven, fast), **tmux/Zellij** (multiplexer grid). voss-app is closer to Wezterm+grid than any of them at L1.
