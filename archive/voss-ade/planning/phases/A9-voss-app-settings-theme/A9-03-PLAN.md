---
phase: A9
plan: "03"
title: "Settings panel + sidebar + search + 7 category sections"
wave: 2
depends_on: ["A9-01", "A9-02"]
files_modified:
  - apps/voss-app/src/settings/SettingsPanel.tsx
  - apps/voss-app/src/settings/SettingsSidebar.tsx
  - apps/voss-app/src/settings/SettingsSearch.tsx
  - apps/voss-app/src/settings/SettingsSection.tsx
  - apps/voss-app/src/settings/sections/AppearanceSection.tsx
  - apps/voss-app/src/settings/sections/TerminalSection.tsx
  - apps/voss-app/src/settings/sections/LayoutSection.tsx
  - apps/voss-app/src/settings/sections/KeybindingsSection.tsx
  - apps/voss-app/src/settings/sections/ProjectSection.tsx
  - apps/voss-app/src/settings/sections/UpdatesSection.tsx
  - apps/voss-app/src/settings/sections/TelemetrySection.tsx
  - apps/voss-app/src/settings/settings.css
autonomous: true
requirements: []
must_haves:
  truths:
    - "Full-screen overlay with z-index 50, Esc dismisses (D-01)"
    - "Fixed 160px sidebar with 7 categories, active highlight accent-blue (D-03)"
    - "Search bar filters to matches, hide non-matching rows (D-04)"
    - "Each section has 'Edit as JSON' link calling openSettingsJson (D-13)"
    - "Workspace badge on overridden rows with reset-to-default (D-05)"
    - "Telemetry section: two toggles OFF default with inline descriptions (D-14, D-15)"
    - "Updates section: version string + disabled 'Check for updates' button (D-16)"
    - "Appearance section surfaces theme dropdown, font dropdown, font size stepper, opacity slider, cursor radio, high-contrast toggle"
    - "All settings load from getMergedSettings() on mount"
    - "Setting changes call updateUserSetting() or updateWorkspaceSetting() immediately"
---

# A9-03: Settings Panel + 7 Category Sections

## Objective

Build the complete settings panel UI — the full-screen overlay container, sidebar navigation, search, and all 7 category sections with their form controls wired to the Tauri settings backend (A9-01). This is the main deliverable of A9.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Settings load fails on corrupt file | getMergedSettings() returns serde defaults (D-08); UI always renders |
| Setting save fails | updateUserSetting wraps error in toast via A7 toast component |
| Stale settings display after external edit | Not addressed in L1 (no file watcher for settings.json — A7 has keymap watcher, settings is rare-visit) |
| XSS via user-entered values | Settings values are typed (string/number/bool); no innerHTML anywhere |

## Tasks

### Task 1: SettingsPanel overlay + SettingsSidebar + SettingsSearch

<read_first>
- apps/voss-app/src/command-palette/CommandPalette.tsx (overlay pattern — z-index, Esc handler, backdrop)
- apps/voss-app/src/settings/settings.css (form control styles from A9-02)
- .planning/phases/A9-voss-app-settings-theme/A9-UI-SPEC.md § Settings Panel Layout Contract
- .planning/phases/A9-voss-app-settings-theme/A9-CONTEXT.md D-01, D-03, D-04
</read_first>

<action>
1. Create `apps/voss-app/src/settings/SettingsPanel.tsx`:
   - Props: `open: boolean`, `onClose: () => void`, `workspacePath?: string`
   - Full-screen overlay: `position: fixed`, `inset: 0`, `z-index: 50` (same as CommandPalette)
   - Titlebar remains visible above (overlay starts below 22px titlebar)
   - Contains SettingsSearch at top, SettingsSidebar left, scrollable form pane right
   - Esc key handler calls `onClose`
   - Click on backdrop (if visible) calls `onClose`
   - `role="dialog"`, `aria-label="Settings"`
   - On mount: calls `getMergedSettings(workspacePath)` to load current values into Solid signals
   - If `workspacePath` set: also calls `getWorkspaceSettings(workspacePath)` to populate override badges

2. Create `apps/voss-app/src/settings/SettingsSidebar.tsx`:
   - Props: `categories: string[]`, `active: string`, `onSelect: (cat: string) => void`
   - Fixed 160px width, bg-1 background
   - Category items: 13px --font-ui, weight 400 fg-2, padding 16px horizontal 8px vertical
   - Active: weight 600, fg-0, 2px left border accent-blue, bg-2
   - Hover: bg-2 on non-active items
   - Click calls onSelect
   - `role="tablist"`, each item `role="tab"`

3. Create `apps/voss-app/src/settings/SettingsSearch.tsx`:
   - Props: `query: string`, `onQueryChange: (q: string) => void`
   - 32px height, bg-3, border, full width
   - Placeholder: "Search settings..." in fg-3
   - × clear button when text present
   - Debounce: none (instant filter on each keystroke — < 50 settings is fast)

4. Add overlay + sidebar + search styles to `settings.css`.
</action>

<acceptance_criteria>
- SettingsPanel.tsx has `role="dialog"` and `aria-label="Settings"`
- SettingsSidebar.tsx has `role="tablist"` and renders 7 category items
- SettingsSearch.tsx renders input with placeholder "Search settings..."
- `npx tsc --noEmit` exits 0
- No raw hex values in TSX files
</acceptance_criteria>

### Task 2: SettingsSection wrapper + 7 category section components

<read_first>
- apps/voss-app/src/settings/SettingsPanel.tsx (just created — composition target)
- apps/voss-app/src/settings/SettingRow.tsx (from A9-02 — row layout)
- apps/voss-app/src/settings/controls/ (all controls from A9-02)
- apps/voss-app/src/settings/settingsStorage.ts (from A9-01 Task 3 — invoke wrappers)
- apps/voss-app/src/command-palette/keymapStorage.ts (A7 keymap profile API)
- .planning/phases/A9-voss-app-settings-theme/A9-CONTEXT.md D-05..D-16
- .planning/phases/A9-voss-app-settings-theme/A9-UI-SPEC.md § Copywriting Contract
</read_first>

<action>
1. Create `apps/voss-app/src/settings/SettingsSection.tsx`:
   - Props: `title: string`, `id: string`, `onEditJson: () => void`, `showWorkspaceJson?: boolean`, `onEditWorkspaceJson?: () => void`, `children: JSX.Element`
   - Section heading: 14px --font-ui weight 600 fg-0
   - "Edit as JSON" link: 11px --font-mono fg-2, underline on hover, calls onEditJson
   - If `showWorkspaceJson`: "Edit workspace JSON" link alongside
   - Section divider: 1px --border below heading
   - `id` attribute for scroll-to-section targeting from sidebar

2. Create 7 section components in `apps/voss-app/src/settings/sections/`:

   **AppearanceSection.tsx** — surfaces A8 theme engine:
   - Theme: Dropdown (12 bundled themes from A8 D-05)
   - Font Family: Dropdown (system fonts from A8 D-13)
   - Font Size: NumberStepper (min 8, max 32, step 1)
   - Line Height: NumberStepper (min 1.0, max 2.5, step 0.1)
   - Cursor Shape: RadioGroup (block/bar/underline)
   - Opacity: Slider (min 0.5, max 1.0, step 0.05)
   - High Contrast: Toggle

   **TerminalSection.tsx**:
   - Default Shell: Dropdown (populated from common shell paths or text input)
   - Scrollback Size: NumberStepper (min 1000, max 100000, step 1000)
   - Cursor Blink: Toggle
   - Bell: RadioGroup (visual/audible/none)

   **LayoutSection.tsx**:
   - Default Preset: Dropdown (fanout/pipeline/swarm/watchers/none)
   - Border Visible: Toggle
   - Focus Follows Mouse: Toggle

   **KeybindingsSection.tsx** (global-only, D-06):
   - Keymap Profile: Dropdown (vscode/tmux) — calls `saveKeymapProfile()` from A7
   - No workspace badge (global-only)

   **ProjectSection.tsx**:
   - Shows current project path (read-only)
   - No configurable settings in L1 (placeholder section)

   **UpdatesSection.tsx** (D-16):
   - Version display: "Version {version}" in mono
   - Check for updates: disabled button with tooltip "Coming in a future release"
   - Auto-update: Toggle (non-functional — persisted but not wired)

   **TelemetrySection.tsx** (D-14, D-15):
   - Crash Reports: Toggle (OFF default)
   - Description: "Anonymous crash reports help us fix bugs. No personal data is collected."
   - Usage Analytics: Toggle (OFF default)
   - Description: "Anonymous usage analytics help us prioritize features. No commands, file paths, or content are shared."
   - No workspace badge (global-only, D-06)

3. Each section receives the relevant settings signals + an `onUpdate` callback that calls the appropriate `updateUserSetting()` or `updateWorkspaceSetting()` from `settingsStorage.ts`. For overridable settings, check if workspace value differs from user value to show WorkspaceBadge.

4. Wire all sections into `SettingsPanel.tsx` body as `<For each={sections}>` or explicit JSX.
</action>

<acceptance_criteria>
- `npx tsc --noEmit` exits 0
- TelemetrySection has both toggles with descriptions matching D-15 copy exactly
- UpdatesSection has disabled button with tooltip text "Coming in a future release"
- KeybindingsSection calls `saveKeymapProfile` from keymapStorage (not settingsStorage)
- AppearanceSection renders Dropdown for theme with options for 12 themes
- Each section component has an `id` attribute for scroll targeting
- `grep -r 'openSettingsJson' apps/voss-app/src/settings/sections/` finds calls in at least 5 sections (each has "Edit as JSON")
</acceptance_criteria>

### Task 3: Search filter logic + sidebar scroll integration

<read_first>
- apps/voss-app/src/settings/SettingsPanel.tsx (composition root)
- apps/voss-app/src/settings/SettingsSearch.tsx (search input)
- apps/voss-app/src/settings/SettingsSidebar.tsx (sidebar nav)
- apps/voss-app/src/settings/SettingRow.tsx (row to filter)
</read_first>

<action>
1. In SettingsPanel.tsx, add search filter state:
   - `const [searchQuery, setSearchQuery] = createSignal('')`
   - Pass query to all SettingRow components
   - Each SettingRow checks if its label or description matches query (case-insensitive substring)
   - Non-matching rows get `display: none`
   - "No settings match '{query}'" message when zero matches

2. Sidebar click-to-scroll:
   - Each section has `id="settings-section-{category}"` 
   - Sidebar click: `document.getElementById('settings-section-' + category)?.scrollIntoView({behavior: 'smooth'})`
   - When search is active, sidebar click clears search first then scrolls

3. Track active section via scroll position:
   - IntersectionObserver on each section heading
   - Update active sidebar highlight to match visible section
   - Or simpler: update on scroll event by checking section offsets
</action>

<acceptance_criteria>
- Typing in search hides non-matching rows
- Clearing search restores all rows
- Sidebar click scrolls to section
- "No settings match" message appears when search produces zero results
- `npx tsc --noEmit` exits 0
</acceptance_criteria>
