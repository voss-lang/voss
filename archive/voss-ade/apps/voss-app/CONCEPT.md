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

## 9. v0 Build Order — Phases A1–A11

Strict sequential dependencies (DAG enables some parallel work). Each phase passes its acceptance gate before downstream phases start. Phase IDs locked in root `.planning/ROADMAP.md` (A-prefix track).

1. **A1 — Tauri Shell** — Tauri + Solid empty window, titlebar, theme tokens, local build only (`pnpm tauri dev` + unsigned smoke artifact). **No release pipeline** — deferred to A11.
2. **A2 — PTY Pane** — One xterm pane wired to native PTY. Full TTY (vim/htop/tmux). Scrollback, copy/paste. (deps: A1)
3. **A3 — Grid Engine** — Binary-split tree. Splits, focus, resize, close, `⌘1-9` nav. (deps: A2)
4. **A4 — Layout Presets** — `fanout · pipeline · swarm · watchers`. `⌘G` cycle. Save/load. Pure visual templates in L1. (deps: A3)
5. **A5 — Project Open** — Folder picker, recents, `.voss/` lazy create, git branch read, project-less mode. (deps: A1)
6. **A6 — Session Persist** — Pane tree + cwds + scrollback restore. Extends to multi-workspace persistence with A8. (deps: A3, A5)
7. **A7 — Cmd Palette + Keymap** — `⌘P`/`⌘⇧P`, VSCode default profile + tmux additions, custom map. (deps: A3)
8. **A8 — Workspaces, UX Polish, & Theming** — Workspace tab bar (Warp-style), VSCode theme import engine, appearance polish, accessibility, setting profiles, platform-native feel. (deps: A1, A3, A5, A7)
9. **A9 — Settings + Theme** — Two-pane settings UI, JSON-backed, surfaces themes/profiles from A8, telemetry consent. (deps: A8)
10. **A10 — Status Bar** — Project · branch · pane count · cost stub · notifications. Workspace-aware. (deps: A5, A8, A9)
11. **A11 — Onboarding + Release Pipeline** — First-run wizard, empty state, 24hr soak, **+ full release pipeline** (signing, 3 channels, auto-update, version-sync). **v0 ship gate.** (deps: all)

That's v0. No Voss yet. L2 phases (Voss substrate) and L3 phases (`.voss` DSL) lock once A11 ships.

**Dependency DAG** enables parallel work:
- A1 unblocks A2, A5
- A2 unblocks A3
- A3 unblocks A4, A6, A7
- A5 unblocks A6, A8
- A7 unblocks A8
- A8 unblocks A9, A10
- A9 unblocks A10
- A11 integrates all

## 10. Decisions Log (closed 2026-05-16)

All L1 spec-blocking questions closed.

| # | Question | Decision | Impact |
|---|---|---|---|
| Q1 | Public ship name | **Voss ADE** | Branding lockstep across docs, marketing, dist channels. Internal slug `voss-app` retained as repo / package name. |
| Q2 | Default shell on pane open | **Auto-launch `$SHELL` immediately** | New panes spawn user's shell instantly. Warp/iTerm parity. Affects A2. |
| Q3 | Pane lifecycle on shell exit | **Banner + Restart button (pane stays open)** | `[exited N]` banner with restart action. Pane never auto-closes. Affects A2 (PTY-07). |
| Q4 | Layout preset semantics in L1 | **Pure visual templates** | L1 presets reorder geometry only. L2 will overlay behavioral semantics. Clean layer boundary. Affects A4. |
| Q5 | Project-less mode | **Yes — first-class** | App launches w/o folder. Empty state offers "Open folder" or "Start without project". Project-less panes inherit `$HOME`. Affects A5, A6 (global-session.json). |
| Q6 | Cost meter stub UX | **Hide entirely in L1** | No cost slot in status bar v0. L2 release adds the slot — minor status-bar reflow accepted. Preserves "zero Voss exposure in L1" goal. Affects A9 (BAR scope shrinks). |
| Q7 | `.voss/` dir creation timing | **Lazy** | `.voss/` created on first action needing it (settings/layout write). Project open alone leaves filesystem untouched. Affects A5, A6. |
| Q8 | Distribution channel | **All three: Direct DMG/AppImage/MSI + Homebrew cask + `@vosslang/cli voss app` subcommand** | Maximum availability. **Release pipeline is a final gate, not an A1 concern** (2026-05-16 clarification) — all signing / channel / version-sync work moved out of A1 into **A11** (REL-01..0N). App does not release until A1–A10 built. Cert procurement (REL-02) is the long-pole — kick off during A1, wire in A11. |
| Q9 | Telemetry & privacy | **OFF default, opt-in toggles** | Settings exposes two switches (anonymous crash reports, anonymous usage analytics), both clearly labelled, both OFF until consent. No first-run nag. No network call without consent. Affects A9 (CFG-06) + A11 (OBD-06). |

**Scope alerts surfaced by these answers:**

- **A1 shrinks back to local-build-only** — release pipeline (signing, 3 channels, auto-update, version-sync) consolidated into **A11**. A1 only needs `pnpm tauri dev` + an unsigned local `pnpm tauri build` smoke artifact. Release = final gate (app ships only after A1–A10 done).
- **A8 added (2026-05-19)** — Workspaces (Warp-style tab bar), VSCode theme engine, appearance polish, accessibility, profiles, platform-native feel. Old A8 (Settings + Theme) renumbered to A9.
- **A11 grows** — absorbs all distribution: OBD-* (onboarding) + REL-* (release pipeline). Three channels version-synced from one tag. A11 is the v0 ship gate.
- **Cert procurement is the long-pole** — REL-02 (mac Developer ID + notarization, win Authenticode) has external lead time. Start procurement during A1 even though wiring lands in A11.
- **A10 (formerly A9) shrinks slightly** — Q6 removes the cost meter from L1 status bar entirely. Re-add planned in the L2 release that introduces cell promotion.
- **Voss ADE branding** — Q1 means `Voss ADE` is the user-facing name everywhere it appears (window title, About, README, marketing). `voss-app` stays as internal slug (repo dir, package name, slug in URLs).

## 11. Reference Artifacts

- Sketch 001 (`.planning/sketches/001-voss-grid-shell/`) — Variant B (Minimal Tile) is the locked aesthetic. Cell rendering in sketch maps to L2+ when promoted; L1 panes use same chrome minus the agent HUD elements (no model/iter/cost-per-cell).
- Existing harness: `voss/harness/...` — untouched in L1, integrated in L2.
- Frozen Rust spike: `crates/` — reference for PTY and IPC choices when L2 starts.
- Competitor reference: **Warp** (terminal blocks, AI mode), **Wezterm** (config-driven, fast), **tmux/Zellij** (multiplexer grid). voss-app is closer to Wezterm+grid than any of them at L1.
