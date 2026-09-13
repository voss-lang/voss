# Phase A7: voss-app Command Palette + Keymap - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** A7-voss-app-command-palette-keymap
**Areas discussed:** Command registry design, ⌘P quick-open scope in L1, tmux ⌘B prefix mode, keymap.json override semantics

---

## Command Registry Design

### Q1: How should the command system be organized?

| Option | Description | Selected |
|--------|-------------|----------|
| Central typed registry | One CommandRegistry Map with {id, label, category, keybinding?, handler}. Single source of truth. | ✓ |
| Distributed registration | Each module registers own commands at mount time. More decoupled but harder to enumerate. | |
| You decide | Planner picks the registry pattern. | |

**User's choice:** Central typed registry
**Notes:** None

### Q2: Should keymap.ts be refactored to dispatch through the registry?

| Option | Description | Selected |
|--------|-------------|----------|
| Registry dispatch replaces keymap.ts | Single dispatch path. A3 chords migrated to registry entries. | ✓ |
| Dual path — grid keeps switch, palette uses registry | keymap.ts stays for A3 grid chords. Registry additive. Two dispatch paths. | |
| You decide | Planner picks based on refactor risk. | |

**User's choice:** Registry dispatch replaces keymap.ts
**Notes:** None

### Q3: How should command handlers receive app context?

| Option | Description | Selected |
|--------|-------------|----------|
| Single AppContext object | One typed context object threaded into registry. Handlers destructure what they need. | ✓ |
| Scoped context per category | Each category gets a narrower context. More type-safe but more wiring. | |
| You decide | Planner picks the context threading pattern. | |

**User's choice:** Single AppContext object
**Notes:** None

### Q4: Where does the native OS menu fit?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generate from registry | Build Tauri native menu items from registry at init. Categories map to menu groups. | ✓ |
| Stub for A7, real wiring in A8 | Web palette only. Native menu minimal placeholder. | |
| You decide | Planner scopes based on effort. | |

**User's choice:** Auto-generate from registry
**Notes:** None

---

## ⌘P Quick-Open Scope in L1

### Q1: What should ⌘P show in L1?

| Option | Description | Selected |
|--------|-------------|----------|
| Saved layouts + recent projects | Fuzzy-match saved layout names (A4) + recent project folders (A5). | ✓ |
| Thin alias for ⌘⇧P | Same palette pre-filtered to quick actions. | |
| Stub with placeholder | Empty picker with "File search available in L4" message. | |
| You decide | Planner picks scope based on available data. | |

**User's choice:** Saved layouts + recent projects
**Notes:** None

### Q2: One component or two?

| Option | Description | Selected |
|--------|-------------|----------|
| One component, two modes | Single CommandPalette. ⌘P = quick mode, ⌘⇧P = full mode. Same engine. | ✓ |
| Two separate components | QuickOpen and CommandPalette distinct. Different data sources. | |

**User's choice:** One component, two modes
**Notes:** None

### Q3: How should fuzzy matching work?

| Option | Description | Selected |
|--------|-------------|----------|
| Simple substring + recency boost | Case-insensitive substring. Recent commands get score boost. ~80 lines. | ✓ |
| Proper fuzzy (fzf-style) | Character-skip fuzzy with gap penalty. More forgiving on typos. | |
| You decide | Planner picks based on catalog size. | |

**User's choice:** Simple substring + recency boost
**Notes:** None

### Q4: How should the palette dismiss?

| Option | Description | Selected |
|--------|-------------|----------|
| Overlay + Esc/click-outside dismiss | Centered overlay. PTY paused. Focus returns on dismiss. | ✓ |
| Inline at top of focused pane | Renders inside pane header area. | |
| You decide | Planner picks placement. | |

**User's choice:** Overlay + Esc/click-outside dismiss
**Notes:** None

### Q5: Should the palette show keybinding hints?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — right-aligned chord hints | Each row shows keybinding in dim text. Teaches muscle memory. | ✓ |
| No hints in L1 | Minimal palette. Keybindings via Help only. | |

**User's choice:** Yes — right-aligned chord hints
**Notes:** None

---

## tmux ⌘B Prefix Mode

### Q1: How should the ⌘B prefix window work?

| Option | Description | Selected |
|--------|-------------|----------|
| Timed window + subtle indicator | 1.5s window. [⌘B…] in pane header. Timeout/Esc cancels. | ✓ |
| Sticky until used or Esc | No timeout. Risk of forgotten prefix state. | |
| Defer to A8 | Ship VSCode-default + custom only. tmux deferred. | |
| You decide | Planner picks mechanics. | |

**User's choice:** Timed window + subtle indicator
**Notes:** Mapped chords: % split V, " split H, o next pane, x close, c new pane. z zoom and [ scroll deferred.

### Q2: How does tmux profile interact with registry?

| Option | Description | Selected |
|--------|-------------|----------|
| Named profiles — switch replaces active set | vscode (default) and tmux. tmux inherits vscode + adds prefix chords. | ✓ |
| tmux = additive layer | Always available alongside active profile. | |
| You decide | Planner picks profile model. | |

**User's choice:** Named profiles — switch replaces active set
**Notes:** None

### Q3: Where is the active profile persisted?

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.config/voss-app/settings.json | "keymap.profile": "vscode" \| "tmux". User-global. | ✓ |
| .voss/keymap.json | Project-scoped profile choice. | |
| You decide | Planner picks location. | |

**User's choice:** ~/.config/voss-app/settings.json
**Notes:** Matches A1 D-09 path lock.

---

## keymap.json Override Semantics

### Q1: How should .voss/keymap.json layer over the active profile?

| Option | Description | Selected |
|--------|-------------|----------|
| Additive merge + unbind via null | Entries merge on top. Null = unbind. VSCode semantics. | ✓ |
| Full replacement | File IS the keybinding map. Profile ignored. | |
| You decide | Planner picks merge model. | |

**User's choice:** Additive merge + unbind via null
**Notes:** Schema: { version: 1, bindings: { "command.id": { key: "chord" } | null } }

### Q2: Hot-reload or restart-only?

| Option | Description | Selected |
|--------|-------------|----------|
| Hot-reload via file watcher | Rust-side fs watcher. Re-validate + merge on change. Instant effect. | ✓ |
| Restart-only | Read once at launch. Simpler. | |
| Palette reload command | Manual trigger from palette. No background watcher. | |
| You decide | Planner picks strategy. | |

**User's choice:** Hot-reload via file watcher
**Notes:** None

### Q3: How should CMD-06 toast validation work?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-entry validation, partial apply | Valid entries apply. Invalid skipped + toasted. Non-destructive. | ✓ |
| All-or-nothing | Any error rejects entire file. | |
| You decide | Planner picks strategy. | |

**User's choice:** Per-entry validation, partial apply
**Notes:** None

### Q4: Toast component scope?

| Option | Description | Selected |
|--------|-------------|----------|
| A7 ships the toast component | Minimal: fixed-position bottom-right, auto-dismiss 5s, Variant B. First consumer = keymap validation. | ✓ |
| Defer toast to A8 | Keymap errors as console.warn + palette inline. | |
| You decide | Planner scopes based on effort. | |

**User's choice:** A7 ships the toast component
**Notes:** Reused by A8/A9/A10.

---

## Claude's Discretion

No areas were deferred to Claude's discretion during discussion. All questions answered by user. Planner has discretion on: Command type extensions (icon, when-guard, source), registry init pattern, AppContext field set, palette visual layout, toast layout, prefix indicator placement, ⌘T resolution, native menu update strategy.

## Deferred Ideas

None — discussion stayed within A7 scope.
