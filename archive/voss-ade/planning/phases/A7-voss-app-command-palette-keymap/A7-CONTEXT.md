# Phase A7: voss-app Command Palette + Keymap - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

A7 adds the command palette (`⌘P` quick-open, `⌘⇧P` all commands) and a keymap system (named profiles + custom `.voss/keymap.json` override) to voss-app. This is the discoverability and muscle-memory layer for everything A1-A6 built. A7 also introduces the central command registry that unifies keyboard dispatch, palette search, and native OS menus under one source of truth — replacing the A3 pure-switch `keymap.ts` with registry-based dispatch.

A7 ships a minimal toast component (first consumer: keymap validation errors per CMD-06), reused by A8/A9/A10.

**Out of scope (fenced to other phases):**
- Workspace tabs, multi-project — A8
- Theme engine, appearance polish, accessibility — A8
- Settings UI (two-pane form) — A9
- Status bar — A10
- File-open in ⌘P (no editor in L1) — L4
- Agent pane semantics, cost meter — L2+

</domain>

<decisions>
## Implementation Decisions

Scope (WHAT) is fixed by ROADMAP CMD-01..07. These are HOW decisions from discussion.

### Command registry architecture
- **D-01:** **Central typed registry** — one `CommandRegistry` (`Map<string, Command>`) with `{id, label, category, keybinding?, handler}`. Single source of truth for palette, keyboard dispatch, and native menus. Lives at `src/command-palette/registry.ts`.
- **D-02:** **Registry dispatch replaces `keymap.ts`** — existing A3 pure-switch `dispatchKey` is retired. All chords (A3 grid chords, A4 `⌘G`, palette triggers, tmux prefix) become registry entries. Single dispatch path: window keydown → lookup registry by chord → call handler. Zero-regression migration of existing A3/A4 bindings.
- **D-03:** **Single `AppContext` object** — built once at `App.tsx` mount, threaded into registry. Holds `gridStore`, `project`, `activeLayout`, `saveCurrentLayout`, `loadLayoutByName`, `applyDefaultLayout`, and any other cross-module state. Handlers destructure what they need.
- **D-04:** **Auto-generate native OS menus from registry** — Tauri native menu items built from registry entries at app init. Categories map to menu groups (Window, Pane, Layout, Project, Settings, Help). Menu click → same handler. Keeps menus in sync with palette automatically.

### ⌘P quick-open scope
- **D-05:** **⌘P shows saved layouts + recent projects** in L1. Layout selection = apply layout. Recent selection = open project. Extensible — L4 adds files to this same list later. No stub/placeholder.
- **D-06:** **One `CommandPalette` component, two modes** — `quick` (⌘P: layouts + recents) and `full` (⌘⇧P: all commands). Same fuzzy engine, same Variant B styling, same dismiss behavior. Less code, consistent UX.
- **D-07:** **Simple substring match + recency boost** for fuzzy. Case-insensitive. Recent commands get a fixed score boost (CMD-04). No external fuzzy lib — ~80 lines of scoring logic. ~50 commands doesn't need fzf sophistication.
- **D-08:** **Centered overlay** — palette renders as a centered overlay (like VSCode). Esc or click-outside dismisses. While open, keystrokes go to palette input — PTY does NOT receive them. Focus returns to previously-focused pane on dismiss.
- **D-09:** **Right-aligned chord hints** in palette rows — each command row shows keybinding in dim text (e.g., `Split Right  ⌘D`). Read from same registry entry. Teaches muscle memory.

### tmux ⌘B prefix mode
- **D-10:** **Timed 1.5s prefix window** — press `⌘B` → enter prefix state. Small `[⌘B…]` indicator in focused pane header (accent color). Next keypress (no `⌘` needed) dispatches tmux-mapped command. Timeout or Esc cancels. Unrecognized key → cancel + pass to PTY. Matches real tmux behavior. Mapped chords: `%` split V, `"` split H, `o` next pane, `x` close pane, `c` new pane. `z` zoom and `[` scroll mode deferred (no zoom/scroll-mode in L1).
- **D-11:** **Named profiles — switching replaces active keybinding map.** Two built-in profiles: `vscode` (default) and `tmux`. tmux profile inherits all vscode bindings + adds `⌘B` prefix chords. User picks profile via settings or palette command "Switch Keymap Profile."
- **D-12:** **Active profile persisted in `~/.config/voss-app/settings.json`** under `"keymap.profile": "vscode" | "tmux"`. User-global, matches A1 D-09 path lock. Rust reads on launch.

### `.voss/keymap.json` override semantics
- **D-13:** **Additive merge + unbind via null** — `keymap.json` entries merge ON TOP of active profile. Override: set command ID to new chord. Unbind: set command ID to `null`. Unmentioned commands keep profile defaults. VSCode keybindings.json semantics. Schema: `{ version: 1, bindings: { "command.id": { key: "chord" } | null } }`.
- **D-14:** **Hot-reload via Rust file watcher** — fs watcher on `.voss/keymap.json`. On change: re-validate, merge over active profile, push updated bindings to frontend via Tauri event. Edit → instant effect.
- **D-15:** **Per-entry validation, partial apply** — valid entries apply, invalid entries (bad key syntax, unknown command ID, conflicting chord) are skipped + each surfaced as a toast (CMD-06). Valid subset still works. Non-destructive.
- **D-16:** **A7 ships the toast component** — no toast system exists yet. A7 ships a minimal toast: fixed-position bottom-right, auto-dismiss 5s, Variant B tokens. Keymap validation is first consumer. Reused by A8/A9/A10.

### Claude's / Planner's Discretion
- Exact `Command` type shape beyond the locked fields (id, label, category, keybinding, handler) — planner may add `icon`, `when` (context guard), `source` (profile vs override), etc.
- Registry initialization pattern (static array vs. per-module `register()` calls at import time) — planner's call, bounded by D-01 (central registry, single Map).
- `AppContext` exact field set — planner extends based on what commands need. D-03 locks the pattern (single object, built once).
- Palette visual layout within Variant B (row height, max visible rows, input styling, category glyph affordances per CMD-07) — planner/UI.
- Toast component exact layout (stack direction, animation, max visible toasts) — planner, within Variant B tokens.
- `⌘B` prefix indicator exact placement within 22px pane header — planner, within existing PaneHeader chrome.
- Whether `⌘T` (new pane) is in v0 command catalog — CONCEPT mentions it but FEATURES L1.5.3 lists "fork" not "new pane." Planner resolves.
- Native menu update strategy on profile/keymap change — planner picks (rebuild menu vs. update accelerators).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & cross-A constraints
- `.planning/ROADMAP.md` Phase A7 (~line 1274) — CMD-01..07, proposed success criteria, cross-cutting constraints (web component not Tauri menus for palette, native menus wrap same registry).

### Product concept (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §4 (~line 124) — planned directory structure: `src/command-palette/` is the canonical location. `voss-app-core` covers "palette" on Rust side.
- `apps/voss-app/CONCEPT.md` §2.1 (~line 42) — v0 spec includes command palette `⌘⇧P`, keybindings with VSCode-default + tmux additions.
- `apps/voss-app/FEATURES.md` §L1.5 (~line 150) — Command Palette: quick-open, all commands, v0 command catalog (Window · Pane · Layout · Project · Settings · Help), recent commands.
- `apps/voss-app/FEATURES.md` §L1.6.4 (~line 188) — Keybinding profiles: VSCode-default, tmux-friendly `⌘B` prefix, custom `.voss/keymap.json`.

### Prior-phase decisions A7 builds on (do not re-litigate)
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-01/D-02 (Variant B CSS-var token SSOT; palette and toast use existing tokens), D-09 (Rust/Tauri owns persisted IO; `~/.config/voss-app/settings.json` path lock for profile persistence, `.voss/keymap.json` read/write is Rust-side).
- `.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md` — D-04 (never destroy panes). A3 keymap.ts chords migrated to registry entries by D-02.
- `.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md` — D-05 (⌘G cycle, already in keymap.ts via `onCycleLayout` callback), D-07 (saved layouts = `.voss/layouts/<name>.json`; palette ⌘P lists these).
- `.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md` — D-06 (open_project Rust command), D-09 (recents at `~/.config/voss-app/recents.json`; palette ⌘P lists these).
- `.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md` — deferred "Reset layout" / "Clear session" palette commands into A7.

### Source code (A7 substrate)
- `apps/voss-app/src/grid/keymap.ts` — existing 120-line pure-switch dispatch. **Will be replaced** by registry-based dispatch (D-02). Read to understand current chord set that must be migrated.
- `apps/voss-app/src/App.tsx` — composition root. Lines 46-84: A4 callable seams (`saveCurrentLayout`, `loadLayoutByName`, `applyDefaultLayout`) explicitly waiting for A7 palette wiring. Comment: "A7's palette will import them directly from this module."
- `apps/voss-app/src/grid/GridRoot.tsx` — owns window keydown listener that currently calls `dispatchKey`. A7 rewires this to registry dispatch.
- `apps/voss-app/src/pane/PaneHeader.tsx` — 22px pane header where D-10 `[⌘B…]` prefix indicator renders.
- `apps/voss-app/src/styles/variant-b.css` — token system for palette and toast styling.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/voss-app/src/grid/keymap.ts` — A3/A4 chord definitions (⌘D split, ⌘⇧D split V, ⌘W close, ⌘G cycle, ⌘= equalize, ⌘[/] cycle focus, ⌘1-9 numeric focus, ⌘⌥arrow directional focus, ⌘⌥⇧arrow resize). All migrate to registry entries.
- `apps/voss-app/src/App.tsx:46-84` — A4 layout closures already built and waiting for palette wiring. `saveCurrentLayout(workspacePath, name)`, `loadLayoutByName(workspacePath, name)`, `applyDefaultLayout(workspacePath)`.
- `apps/voss-app/src/grid/layoutStorage.ts` — `loadLayout`, `saveLayout`, `loadDefaultLayout` Tauri invoke wrappers. ⌘P quick-open calls these for layout entries.
- `apps/voss-app/src/pane/ExitBanner.tsx` / `CloseConfirmBanner.tsx` — Variant B chrome precedent for overlay/banner components. Toast follows same token system.
- `apps/voss-app/src/pane/PaneHeader.tsx` — mount point for `[⌘B…]` prefix indicator.

### Established Patterns
- **Solid signals = UI SSOT; Rust/Tauri owns persisted IO** (A1 D-09). Profile in settings.json + keymap.json read/write = Rust-side. Palette state (open/mode/query) = Solid signals.
- **Variant B CSS-var tokens** (A1 D-01/02). Palette and toast use `--bg-0..3`, `--fg-0..3`, `--border`, `--focus`.
- **Cross-crate `#[tauri::command]` pattern** (A2-05, A4-03). New keymap commands in `voss-app-core` (new module `keymap.rs` or `commands.rs`); thin app wrappers in `apps/voss-app/src-tauri/src/lib.rs`.
- **Injected callbacks** (A3 keymap.ts pattern: `onCloseRequest`, `onCycleLayout`, `onStructuralEdit`). Registry replaces injection — commands self-describe their handler.

### Integration Points
- New directory `apps/voss-app/src/command-palette/` — `registry.ts` (CommandRegistry, Command type, AppContext), `CommandPalette.tsx` (overlay component, quick/full modes), `fuzzy.ts` (substring match + recency scoring).
- New file `apps/voss-app/src/command-palette/toast.ts` + `Toast.tsx` — minimal toast system.
- `apps/voss-app/src/App.tsx` — builds `AppContext`, initializes registry, renders `<CommandPalette />` overlay, wires `⌘P`/`⌘⇧P` registry entries.
- `apps/voss-app/src/grid/GridRoot.tsx` — window keydown rewired from `dispatchKey` to registry dispatch.
- New Rust module `crates/voss-app-core/src/keymap.rs` — `KeymapProfile`, `load_keymap_overrides`, `validate_keymap`, fs watcher setup. App-level Tauri wrappers in `apps/voss-app/src-tauri/src/lib.rs`.
- `apps/voss-app/src-tauri/src/lib.rs` — native menu generation from registry data (Tauri `Menu` / `MenuItem` APIs).

</code_context>

<specifics>
## Specific Ideas

- **Registry-first architecture** is the key insight. By replacing keymap.ts with registry dispatch, every command is discoverable (palette), bindable (profiles/overrides), and surfaceable (native menus) from one source. No parallel data structures.
- **⌘P as layouts + recents** is the right L1 scope. Users have named things (layouts from A4, projects from A5) — ⌘P lets them jump to those. L4 adds files naturally to the same list. No stub, no placeholder.
- **tmux prefix = modal state timeout**, not a chord modifier. The 1.5s window matches real tmux behavior. The `[⌘B…]` indicator is subtle but sufficient — power users who chose the tmux profile know what it means.
- **Additive keymap override** matches user expectations from VSCode. Partial apply + per-error toast (D-15) means one typo doesn't break everything — critical for a file users edit by hand.
- **Toast component is a natural byproduct.** CMD-06 requires surfacing keymap errors, and no toast exists yet. Shipping a minimal toast in A7 seeds infrastructure A8/A9/A10 need without over-building.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within A7 scope. Adjacent capabilities are fenced to their owning phases:
- Workspace tab management commands → A8
- Theme switching commands → A8 (theme engine)
- Settings UI for keybinding editing → A9
- Status bar interactions → A10
- File search in ⌘P → L4 (editor pane)
- Zoom pane (`⌘B z` in tmux) → future (no zoom in L1)
- Scroll mode (`⌘B [` in tmux) → future

</deferred>

---

*Phase: A7-voss-app-command-palette-keymap*
*Context gathered: 2026-05-20*
