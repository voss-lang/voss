# Phase A9: voss-app Settings + Theme - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

A9 delivers the **two-pane Settings UI** that surfaces and configures everything A8's engine layer provides (themes, fonts, vibrancy, profiles, accessibility) plus terminal/shell/scrollback, layout defaults, keybinding profile selection, and telemetry consent toggles. A9 = the configuration *surface*, not the engine.

A9 builds on: A1 (Variant B token system + Rust IO seam + `~/.config/voss-app/` path lock), A7 (command registry for `⌘,` shortcut + toast component), A8 (theme engine, font picker, vibrancy, profiles, high-contrast).

**Out of scope (fenced to other phases):**
- Theme engine, theme JSON files, custom theme schema — A8 (delivers the engine; A9 only surfaces it)
- Font enumeration, live preview logic — A8 (A9 renders the dropdown A8 provides)
- Named profiles engine (save/load/switch) — A8 (A9 surfaces profile switching in settings)
- Status bar (settings cog click target) — A10
- Onboarding wizard, first-run experience — A11
- Telemetry send/collection infrastructure — future (A9 only ships consent toggles)
- Auto-update mechanism — A11 (A9 renders placeholder section)
- In-app JSON editor — L4 (A9 uses OS default editor via CFG-03)

</domain>

<decisions>
## Implementation Decisions

Scope (WHAT) is fixed by ROADMAP CFG-01..07. These are HOW decisions from discussion.

### Settings panel hosting
- **D-01:** **Full-screen overlay.** Settings renders as a full-screen overlay covering the pane area (same z-layer as command palette but filling the content region). Esc dismisses, returns to panes. Panes remain mounted but hidden behind the overlay. Not a pane type — a dedicated overlay component at `src/settings/SettingsPanel.tsx`.
- **D-02:** **`⌘,` keyboard shortcut** opens settings (standard macOS/VSCode convention). Also reachable via `⌘⇧P` → "Open Settings" (A7 command registry entry). A10's status bar cog will also open settings when A10 lands.
- **D-03:** **Fixed sidebar nav** (~160px, always visible). 7 category labels stacked vertically (Appearance · Terminal · Layout · Keybindings · Project · Updates · Telemetry per CFG-02). Click category → scroll right pane to that section. Search bar spans full width above both panes.
- **D-04:** **Search filters to matches.** Typing in search hides non-matching setting rows (CSS display toggle). Clear search restores full list. VSCode pattern.

### Merge & override UX
- **D-05:** **Inline badge per setting row** for workspace overrides. Each setting row that differs from user-level shows a small "workspace" badge + a "reset to default" link. Hover badge → tooltip showing user-level value. VSCode pattern.
- **D-06:** **Most settings workspace-overridable.** Appearance (theme, font, opacity, cursor, high-contrast), Terminal (shell, scrollback, cursor blink, bell), Layout (default preset, border visibility, focus-follows-mouse) — all workspace-overridable. **Global-only:** Keybindings (profile + overrides), Updates, Telemetry. ~80% overridable.
- **D-07:** **Shallow merge by key.** Workspace `settings.json` keys overwrite user-level keys at top level. No deep-merge of nested objects. Schema is flat enough that deep-merge adds complexity without value. If workspace sets "font", it replaces the entire font block.
- **D-08:** **Runtime Rust validation.** Typed serde structs with `#[serde(default)]`. Unknown keys ignored, invalid values fall back to defaults, error logged to stderr. No JSONSchema file shipped. Matches A4/A6 fail-safe pattern (never crash on bad config).

### Hot-reload granularity
- **D-09:** **Visual settings apply immediately to all panes.** Theme, font family/size/line-height, opacity, cursor shape, high-contrast — all apply instantly to every open pane + chrome via `applyThemeOverrides()` + xterm.js `setOption()`. Non-destructive, instantly reversible.
- **D-10:** **Shell changes affect new panes only.** Changing default shell does not disrupt existing panes' running processes. Matches every terminal emulator's behavior.
- **D-11:** **Scrollback size changes affect new panes only.** xterm.js scrollback is set at Terminal construction; changing mid-session requires terminal recreation (lossy).
- **D-12:** **No "ask before retroactive" flow.** Visual changes are non-destructive (instant + reversible). Process/terminal settings only affect new panes. CFG-07's intent is satisfied by the new-panes-only rule for destructive settings. No explicit confirmation prompts needed.

### Edit-as-JSON & telemetry
- **D-13:** **OS default editor for "Edit as JSON."** Rust `shell::open()` on the settings.json file path. Link per category section: "Edit as JSON" opens user-level file; "Edit workspace JSON" opens `.voss/settings.json`. macOS → whatever handles `.json` (VS Code if associated, TextEdit otherwise). Matches CFG-03 literally.
- **D-14:** **Telemetry = consent toggles only.** Two UI switches: "Crash Reports" and "Usage Analytics", both OFF by default (CONCEPT Q9). Persisted as boolean flags in `settings.json`. No actual telemetry send/collection code — A9 only writes the consent flags. Future telemetry infrastructure reads these flags to gate network calls.
- **D-15:** **Inline descriptions for consent toggles.** Each toggle has 1-2 lines of plain English: "Anonymous crash reports help us fix bugs. No personal data is collected." / "Anonymous usage analytics help us prioritize features. No commands, file paths, or content are shared." Direct, honest, no legal-speak.
- **D-16:** **Updates section = placeholder.** Shows current version string. "Check for updates" button disabled with tooltip "Coming in a future release." Auto-update toggles present but non-functional. A11 (release pipeline) wires the real mechanism.

### Claude's / Planner's Discretion
- Settings overlay visual design (padding, row height, input styles, section dividers) — within Variant B tokens.
- Exact form control components (dropdown, slider, toggle, text input) — planner builds or picks, within Variant B token system.
- Category icon glyphs (if any) in sidebar nav — planner's call.
- Search implementation details (debounce timing, match highlighting, which fields are searchable) — planner's call.
- "Edit as JSON" link placement within each section (top-right corner, bottom of section, etc.) — planner's call.
- Settings.json schema field names and nesting — bounded by D-07 (shallow merge) and D-08 (serde typed structs with defaults).
- Whether the settings panel has a scrollbar on the right pane or per-section overflow — planner's call.
- Toast feedback for settings changes (e.g., "Theme changed to Dracula") — reuse A7 toast, planner decides which changes warrant a toast.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements & cross-A constraints
- `.planning/ROADMAP.md` Phase A9 (~line 1362) — CFG-01..07, proposed success criteria, cross-cutting constraints (CONCEPT Q9 telemetry, A8 theme engine dependency).

### Product concept (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` §10 Q7 — `.voss/` lazy creation (settings write triggers it).
- `apps/voss-app/CONCEPT.md` §10 Q9 — Telemetry policy: OFF default, opt-in toggles, no nag, no network without consent.
- `apps/voss-app/FEATURES.md` §L1.6 (~line 169) — Settings storage (L1.6.1), Settings UI (L1.6.2), Settings categories (L1.6.3), Keybinding profiles (L1.6.4).

### Prior-phase decisions A9 builds on (do not re-litigate)
- `.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md` — D-01/D-02 (Variant B CSS-var token system — settings UI uses same tokens), D-09 (Rust/Tauri owns persisted IO; `~/.config/voss-app/settings.json` path lock).
- `.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md` — D-01 (central command registry — `⌘,` "Open Settings" registers here), D-12 (keymap profile already in settings.json — A9 surfaces the profile picker), D-16 (toast component — A9 reuses for settings feedback).
- `.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md` — D-05 (12 bundled themes), D-06 (static JSON themes + `applyThemeOverrides()` runtime swap — A9 calls this on theme selection), D-07 (custom themes at `.voss/themes/`), D-08 (native vibrancy + opacity slider), D-12 (high-contrast = token override layer — A9 provides the toggle), D-13 (font dropdown + live preview — A9 surfaces this), D-14 (named profiles — A9 surfaces profile management).

### Source code (A9 substrate)
- `apps/voss-app/src/theme/applyTheme.ts` — `applyThemeOverrides(overrides)` function. Comment: "Called again by A8 settings UI on runtime theme change." D-09 calls this on theme selection.
- `apps/voss-app/src/command-palette/registry.ts` — A7 command registry. A9 adds `⌘,` "Open Settings" entry.
- `apps/voss-app/src/command-palette/keymapStorage.ts` — A7 keymap persistence. A9 Keybindings section surfaces profile switching via `saveKeymapProfile()`.
- `apps/voss-app/src/styles/variant-b.css` — CSS var token system. Settings overlay uses these tokens.
- `crates/voss-app-core/src/keymap.rs` — Rust keymap profile persistence. A9 settings reads/writes profile via existing Tauri commands.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/voss-app/src/theme/applyTheme.ts` — `applyThemeOverrides()` already iterates CSS vars onto `:root`. Theme switch in settings = load selected theme JSON + call this function. D-09 immediate-all-panes is free.
- `apps/voss-app/src/command-palette/keymapStorage.ts` — `loadKeymapProfile()`, `saveKeymapProfile()`, `loadKeymapOverrides()` already exist. Keybindings section in settings just calls these.
- `apps/voss-app/src/command-palette/registry.ts` — `CommandRegistry` for registering `⌘,` shortcut.
- A7 toast component — reuse for settings feedback ("Theme changed", "Profile saved").
- `apps/voss-app/src/pane/PaneComponent.tsx` — xterm.js Terminal instance. D-09 visual reload calls `term.options.fontFamily`, `term.options.fontSize`, etc.

### Established Patterns
- **Solid signals = UI SSOT; Rust/Tauri owns persisted IO** (A1 D-09). Settings values stored Rust-side. Frontend reads via Tauri commands, displays in form controls, writes back via Tauri commands.
- **Variant B CSS-var tokens** (A1 D-01/02). Settings overlay styled with `--bg-0..3`, `--fg-0..3`, `--border`, `--focus`.
- **Cross-crate `#[tauri::command]` pattern** (A2-05, A4-03, A7). New settings commands in `voss-app-core` (new module `settings.rs`); thin app wrappers in `apps/voss-app/src-tauri/src/lib.rs`.
- **Atomic write + fail-safe load** (A4 layouts.rs, A6 session.rs). Settings writes follow same pattern.
- **`.voss/` lazy on first write** (A4 D-09 / CONCEPT Q7). Workspace `settings.json` creates `.voss/` if needed.

### Integration Points
- New directory `apps/voss-app/src/settings/` — `SettingsPanel.tsx` (overlay component), form control components (Toggle, Dropdown, Slider, TextInput), category section components.
- New Rust module `crates/voss-app-core/src/settings.rs` — `UserSettings`, `WorkspaceSettings`, `MergedSettings`, load/save/merge, typed serde structs with defaults.
- `apps/voss-app/src/App.tsx` — renders `<SettingsPanel />` overlay (conditionally visible via signal), `⌘,` wired through command registry.
- `apps/voss-app/src-tauri/src/lib.rs` — new Tauri command registrations for settings CRUD + `open_settings_json` (shell::open).

</code_context>

<specifics>
## Specific Ideas

- **Settings is architecturally simple.** A8 builds all the engines (theme swap, font picker, vibrancy, profiles). A9 wraps those in form controls. The settings panel is a Solid component that reads current values, renders form controls, and calls Tauri commands to persist changes. No complex state management needed.
- **Full-screen overlay** matches the command palette pattern — user is in "settings mode" or "terminal mode," never both. No pane-tree complexity for a rare-visit destination.
- **Shallow merge** means workspace settings are easy to reason about in both UI and JSON. A user editing `.voss/settings.json` by hand sees exactly what their workspace overrides — no ambiguity about partial objects being deep-merged.
- **No ask-before flow** is the simplest correct answer. Visual changes are safe to apply instantly (reversible). Shell/scrollback are safe as new-panes-only. No setting in A9 scope warrants an interruption dialog.
- **Telemetry as consent-only** keeps A9 focused on UI. The flags exist in `settings.json` for future infrastructure to read. Zero network calls, zero dead code.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within A9 scope. Adjacent capabilities are fenced to their owning phases:
- Theme engine, theme catalog, custom theme schema — A8
- Status bar cog (alternative settings access point) — A10
- Auto-update check mechanism — A11 (A9 renders placeholder UI)
- Telemetry send/collection infrastructure — future
- In-app JSON editor (replaces OS default editor for settings) — L4
- Policy editor (`.voss/policy.yaml` GUI) — L2

</deferred>

---

*Phase: A9-voss-app-settings-theme*
*Context gathered: 2026-05-20*
