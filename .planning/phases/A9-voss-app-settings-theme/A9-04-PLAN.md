---
phase: A9
plan: "04"
title: "App.tsx integration + ⌘, shortcut + hot-reload + acceptance"
wave: 3
depends_on: ["A9-03"]
files_modified:
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/command-palette/registry.ts
  - apps/voss-app/src/settings/settingsReload.ts
autonomous: false
requirements: []
must_haves:
  truths:
    - "⌘, opens settings overlay via command registry entry (D-02)"
    - "Settings overlay renders in App.tsx above grid, below palette z-order"
    - "Only one overlay at a time: opening settings closes palette, opening palette closes settings"
    - "Theme change via settings → applyThemeOverrides() → all panes + chrome update instantly (D-09)"
    - "Font change via settings → xterm.js setOption per terminal → all panes update instantly (D-09)"
    - "Shell change via settings → new panes only (D-10)"
    - "CFG-01 verified: change theme in UI → persists in settings.json → survives restart"
    - "CFG-02 verified: 7 categories visible in sidebar"
    - "CFG-03 verified: 'Edit as JSON' opens file in OS editor"
    - "CFG-06 verified: telemetry toggles OFF default, no network call occurs"
    - "CFG-07 verified: theme change → all panes update; shell change → only new panes"
---

# A9-04: App Integration + Hot-Reload + Acceptance

## Objective

Wire the settings panel into App.tsx, add `⌘,` shortcut to the command registry, implement the hot-reload dispatch that applies visual settings changes to live panes, and verify all CFG-01..07 acceptance criteria.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Settings overlay conflicts with command palette | Mutual exclusion: opening settings closes palette, opening palette closes settings |
| Theme switch leaves stale CSS vars | applyThemeOverrides() writes all vars atomically; no partial state possible |
| Font size change corrupts terminal layout | xterm.js setOption triggers internal reflow; ResizeObserver in PaneComponent fires fit() |

## Tasks

### Task 1: Add `settings.openSettings` to AppContext + ⌘, to registry

<read_first>
- apps/voss-app/src/command-palette/registry.ts (AppContext interface + v0Commands catalog)
- apps/voss-app/src/App.tsx (current AppContext construction + overlay state)
- .planning/phases/A9-voss-app-settings-theme/A9-CONTEXT.md D-02
</read_first>

<action>
1. Add to `AppContext` interface in `registry.ts`:
   - `openSettings: () => void`

2. Add to `v0Commands()` array:
   ```
   {
     id: 'settings.open',
     label: 'Open Settings',
     category: 'Settings',
     keybinding: 'Cmd+,',
     handler: (ctx) => ctx.openSettings(),
   }
   ```

3. In `App.tsx`:
   - Add `[settingsOpen, setSettingsOpen] = createSignal(false)`
   - Wire `openSettings` in appCtx: `openSettings: () => { dismissPalette(); setSettingsOpen(true); }`
   - Add ⌘, interception in `onAppKey` (capture phase, same pattern as ⌘P/⌘⇧P):
     - If `chord === 'Cmd+,'`: preventDefault, stopImmediatePropagation, openSettings
   - When palette opens: `setSettingsOpen(false)` (mutual exclusion)
   - When settings opens: `setPaletteMode(null)` (mutual exclusion)
</action>

<acceptance_criteria>
- `Cmd+,` in `normalizeChord` maps correctly (verify the comma key chord string)
- `npx tsc --noEmit` exits 0
- `grep 'settings.open' apps/voss-app/src/command-palette/registry.ts` finds the command definition
- `grep 'openSettings' apps/voss-app/src/App.tsx` finds the AppContext wiring
</acceptance_criteria>

### Task 2: Mount SettingsPanel in App.tsx

<read_first>
- apps/voss-app/src/App.tsx (overlay rendering — CommandPalette Show block as pattern)
- apps/voss-app/src/settings/SettingsPanel.tsx (from A9-03)
</read_first>

<action>
1. Import `SettingsPanel` in App.tsx.

2. Add a `<Show when={settingsOpen()}>` block rendering `<SettingsPanel>`:
   - Place BEFORE the CommandPalette Show block (both are z-50 but mutual exclusion prevents overlap)
   - Pass `open={settingsOpen()}`, `onClose={() => setSettingsOpen(false)}`, `workspacePath={project()?.path}`

3. The overlay is now live: ⌘, → settings appears, Esc → settings closes.
</action>

<acceptance_criteria>
- `grep 'SettingsPanel' apps/voss-app/src/App.tsx` finds import + JSX
- Settings and palette are mutually exclusive: opening one closes the other
- `npx tsc --noEmit` exits 0
</acceptance_criteria>

### Task 3: Hot-reload dispatch — `settingsReload.ts`

<read_first>
- apps/voss-app/src/theme/applyTheme.ts (applyThemeOverrides function)
- apps/voss-app/src/pane/PaneComponent.tsx (xterm.js Terminal instance, options)
- apps/voss-app/src/command-palette/keymapStorage.ts (loadKeymapProfile/saveKeymapProfile)
- .planning/phases/A9-voss-app-settings-theme/A9-CONTEXT.md D-09..D-12
</read_first>

<action>
Create `apps/voss-app/src/settings/settingsReload.ts`:

1. `reloadTheme(themeName: string): void`
   - Load theme JSON from bundled themes (A8 provides these — for now, stub with a switch on theme name returning a Record<string, string> of CSS var overrides)
   - Call `applyThemeOverrides(overrides)` — immediate, all panes + chrome

2. `reloadFont(family: string, size: number, lineHeight: number): void`
   - Query all xterm Terminal instances (via a registry or document query)
   - For each: `term.options.fontFamily = family; term.options.fontSize = size; term.options.lineHeight = lineHeight`
   - xterm.js automatically reflows on option change

3. `reloadCursorStyle(style: 'block' | 'bar' | 'underline'): void`
   - Same pattern: `term.options.cursorStyle = style` for each terminal

4. `reloadOpacity(value: number): void`
   - Set webview background alpha via Tauri window API or CSS on the document

5. Export a unified `applySettingChange(key: string, value: unknown): void` dispatcher:
   - Switch on key name → call the appropriate reload function
   - Keys not in the visual set (shell, scrollback, bell, etc.) → no-op (new-panes-only per D-10/D-11)

6. Wire `applySettingChange` into SettingsPanel: each setting's onChange calls `updateUserSetting(key, value)` then `applySettingChange(key, value)`.
</action>

<acceptance_criteria>
- `reloadTheme` calls `applyThemeOverrides` (import verified by grep)
- `reloadFont` sets `term.options.fontFamily`, `term.options.fontSize`, `term.options.lineHeight`
- `applySettingChange('defaultShell', '/bin/fish')` is a no-op (shell = new panes only)
- `npx tsc --noEmit` exits 0
</acceptance_criteria>

### Task 4: Acceptance verification — CFG-01..07

<read_first>
- .planning/ROADMAP.md Phase A9 (~line 1362) — CFG-01..07 + success criteria
- .planning/phases/A9-voss-app-settings-theme/A9-CONTEXT.md (all 16 decisions)
- apps/voss-app/src/settings/ (all files from A9-01..03)
</read_first>

<action>
Verify each CFG requirement and success criterion:

**CFG-01:** User settings at `~/.config/voss-app/settings.json`. Workspace at `.voss/settings.json`. Workspace wins.
- Verify: `grep 'settings.json' crates/voss-app-core/src/settings.rs` shows both paths
- Verify: `merge_settings` uses workspace value when present

**CFG-02:** Two-pane UI with 7 categories.
- Verify: SettingsSidebar renders 7 items matching: Appearance, Terminal, Layout, Keybindings, Project, Updates, Telemetry

**CFG-03:** Edit as JSON → OS default editor.
- Verify: `openSettingsJson` calls shell::open
- Verify: each section has "Edit as JSON" link

**CFG-04:** Theme tokens as CSS variables.
- Verify: `applyThemeOverrides` sets `--bg-0..3`, `--fg-0..3`, etc.

**CFG-05:** Font, cursor, scrollback, shell configurable.
- Verify: AppearanceSection has font/cursor controls, TerminalSection has shell/scrollback

**CFG-06:** Telemetry OFF default.
- Verify: `UserSettings::default()` has `telemetry_crash_reports: false`, `telemetry_usage_analytics: false`
- Verify: no `fetch` / `XMLHttpRequest` / `net` import in settings code

**CFG-07:** Hot-reload — next pane for shell, instant for theme.
- Verify: `applySettingChange('theme', ...)` calls `reloadTheme`
- Verify: `applySettingChange('defaultShell', ...)` is no-op

**Success Criteria:**
1. Change theme via UI → all panes + chrome update without restart
2. Change default shell via UI → next new pane uses it
3. Telemetry toggles persist; off-state prevents any network call

**Build gates:**
- `cargo build --manifest-path apps/voss-app/src-tauri/Cargo.toml` exits 0
- `npx tsc --noEmit` exits 0
- `npx vitest run src/settings` exits 0 (all A9-02 tests pass)
- `cargo test -p voss-app-core -- settings` exits 0

**Manual human verification required:**
- ⌘, opens settings overlay
- Theme change applies visually
- Edit as JSON opens OS editor
- Esc closes settings
</action>

<acceptance_criteria>
- All CFG-01..07 verified via grep/test/build commands above
- `cargo build` + `tsc` + `vitest src/settings` + `cargo test settings` all exit 0
- No `fetch(` or `XMLHttpRequest` in `apps/voss-app/src/settings/` (telemetry sends nothing)
- Human verifies: ⌘, works, theme change applies, Edit as JSON opens file
</acceptance_criteria>
