---
phase: A8
slug: voss-app-workspaces-ux-polish-theming
status: approved
shadcn_initialized: false
preset: none
created: 2026-05-20
reviewed_at: 2026-05-20T20:36:00Z
---

# Phase A8 - UI Design Contract: Workspaces, UX Polish, and Theming

> Visual and interaction contract for Phase A8. A8 extends the Variant B terminal shell with workspace tabs, curated themes, minimal appearance/profile pickers, accessibility overlays, and platform-native polish. It must not introduce a two-pane settings UI, marketing copy, rounded card surfaces, agent/status-bar semantics, or a VSCode theme import engine.
> Sources: A8-CONTEXT.md, A8-RESEARCH.md, ROADMAP A8 UXP-01..30, A1/A3/A4/A7 UI-SPECs, `variant-b.css`, and current voss-app source.

---

## Design System

| Property | Value | Source |
|---|---|---|
| Tool | none (manual CSS + Tailwind v4) | Existing Solid/Tauri app |
| Preset | not applicable | no component library |
| Component library | none - hand-rolled Solid components only | A1/A3/A4/A7 contracts |
| Icon library | none - glyphs/text only (`+`, `x`, `...`, `*`, `W`, `T`, `P`) | Variant B density rule |
| Font (all chrome) | `--font-mono` | Existing Variant B |
| Terminal font fallback | JetBrains Mono, then system mono | A8 D-13 |

**shadcn gate:** not applicable. voss-app is Solid/Tauri, not React/Next.js, and no third-party UI registry is allowed in A8.

---

## Scope Boundary

A8 UI surfaces are minimal operational controls, not the full settings app.

Allowed A8 UI surfaces:

- Workspace tab bar below the titlebar.
- New workspace picker.
- Workspace tab context menu/popover.
- Command-palette sublists for `Switch Theme`, `Switch Profile`, and appearance commands when A7 is available.
- Minimal inline preview rows for theme/font/profile switching.
- Toasts for theme/profile/font/workspace feedback when A7 toast exists.

Forbidden in A8:

- A9 two-pane settings UI.
- Onboarding wizard.
- Status bar.
- File search.
- Agent/cost/semantic role badges.
- VSCode theme import UI.
- Custom hex color picker.
- Decorative cards, hero panels, gradients, blur-only decoration, or explanatory feature text.

If A7 command palette/toast is not implemented at A8 Wave 0, planner must gate or defer those command surfaces instead of creating a second palette/toast system.

---

## Token Inheritance Contract

A8 MUST continue to use the Variant B CSS variable architecture from `apps/voss-app/src/styles/variant-b.css`.

A8 may extend the theme schema, but component code must still consume variables, not literal colors:

- Core tokens: `--bg-0..3`, `--fg-0..3`, `--border`, `--border-bright`, `--focus`, `--focus-glow`.
- Existing semantic accents: `--accent-green`, `--accent-amber`, `--accent-red`, `--accent-cyan`, `--accent-magenta`, `--accent-blue`.
- New theme-schema tokens allowed only if backed by all 12 bundled themes and custom-theme validation:
  - `--ansi-0..15`
  - `--workspace-neutral`, `--workspace-red`, `--workspace-orange`, `--workspace-green`, `--workspace-yellow`, `--workspace-cyan`, `--workspace-blue`, `--workspace-purple`
  - `--window-opacity-bg` for opacity/vibrancy compositing

A8 MUST NOT:

- Use raw hex values in component code, except inside theme JSON files and high-contrast overlay constants.
- Add rounded corners to app chrome or picker surfaces.
- Use accent colors for generic hover state.
- Add a separate color system for light themes. Light themes fill the same token names.
- Animate layout with JavaScript or spring libraries.

---

## Spacing Scale

A8 inherits A1/A3/A4/A7 spacing and adds only workspace-specific fixed dimensions.

| Token | Value | A8 Usage |
|---|---:|---|
| xs | 4px | Dot gaps, tab close gap, popover row icon gaps |
| sm | 6px | Inherited macOS traffic-light gap |
| md | 8px | Tab internal gap, picker row vertical padding, popover padding |
| base | 10px | Tab horizontal padding, inherited titlebar rhythm |
| lg | 12px | Tabbar left/right inset, picker side padding |
| xl | 16px | Workspace picker section gap |
| 2xl | 24px | Empty workspace picker group separation |
| 3xl | 32px | Max outer margin for overlay/picker surfaces |

### Structural Constants

| Constant | Value | Usage |
|---|---:|---|
| Titlebar height | 22px | Inherited A1 |
| Workspace tabbar height | 28px | New row between titlebar and grid |
| Workspace tab min width | 120px | Keeps project names readable |
| Workspace tab max width | 220px | Prevents one tab consuming the row |
| Workspace tab height | 24px | Fits inside 28px row with 2px top/bottom inset |
| Dot diameter | 8px | Workspace accent color dot |
| Picker row height | 32px | Matches A7 palette density |
| Popover row height | 28px | Compact tab context controls |
| Border width | 1px | All structural borders |
| Radius | 0px | All A8-owned surfaces |

Exceptions: inherited A1 6px, 10px, and 22px terminal-grid constants remain valid. Do not snap them to 4px.

---

## Typography

A8 uses the same compact mono scale as earlier voss-app phases.

| Role | Size | Weight | Line Height | Font | A8 Usage |
|---|---:|---:|---:|---|---|
| Meta | 10px | 400 | 1.0 | `--font-mono` | Shortcuts, active markers, path metadata |
| Chrome | 11px | 400 | 1.0 | `--font-mono` | Workspace tab labels, popover rows, titlebar-adjacent controls |
| Body | 12px | 400 | 1.35 | `--font-mono` | Picker rows, theme/profile/font labels |
| Emphasis | 12px | 600 | 1.0 | `--font-mono` | Active tab label, selected picker row |
| Preview | user-selected | 400 | user-selected | selected terminal font | Font preview sample only |

Rules:

- No display type.
- No negative letter spacing.
- Workspace tab labels truncate with ellipsis, never wrap.
- Popover and picker labels must remain single-line.
- Theme names use canonical capitalization: `One Dark Pro`, `Catppuccin Mocha`, `GitHub Light`, etc.
- Terminal font preview may use the selected font; chrome remains `--font-mono`.

---

## Color

A8 rethemes the existing token system. The default visible state is still Variant B.

| Role | Value | Usage |
|---|---|---|
| Dominant (60%) | `--bg-0`, `--bg-1` | App background, tabbar base, inactive workspace bodies |
| Secondary (30%) | `--bg-2`, `--bg-3`, `--border`, `--border-bright`, `--fg-0..3` | Tabs, popovers, picker rows, pane chrome, text tiers |
| Accent (10%) | `--focus`, existing accents, workspace accent tokens | Active tab rail, focus ring, color dots, validation/feedback states only |
| Destructive | `--accent-red` | Close workspace, failed theme/profile/font operations |

Accent reserved for:

- `--focus`: focused pane, focused picker row, keyboard focus ring.
- Workspace accent tokens: 8px dots and 1px active-tab top rail only.
- `--accent-green`: success feedback.
- `--accent-amber`: warnings, high-contrast preview warnings.
- `--accent-red`: destructive close and errors.
- `--accent-cyan`: neutral info feedback.

Hover uses `--bg-2`/`--bg-3`, not accent fills.

### Workspace Color Dots

The workspace dot palette is fixed:

| Name | Token |
|---|---|
| Neutral | `--workspace-neutral` |
| Red | `--workspace-red` |
| Orange | `--workspace-orange` |
| Green | `--workspace-green` |
| Yellow | `--workspace-yellow` |
| Cyan | `--workspace-cyan` |
| Blue | `--workspace-blue` |
| Purple | `--workspace-purple` |

Theme JSON files must define these tokens. The default theme can alias them to existing accent values where appropriate, but component code reads only `--workspace-*`.

### High Contrast Overlay

High contrast is an overlay on top of the active theme.

Required overlay values:

- `--bg-0: #000`
- `--bg-1: #050505`
- `--bg-2: #101010`
- `--bg-3: #181818`
- `--fg-0: #fff`
- `--fg-1: #f5f5f5`
- `--fg-2: #d8d8d8`
- `--fg-3: #b8b8b8`
- `--focus: #ffff00`
- `--border-bright: #fff`

These raw values are allowed only in the high-contrast overlay module and tests. All component code still uses tokens.

---

## Copywriting Contract

| Element | Copy |
|---|---|
| Add workspace button label | `New workspace` |
| New workspace picker title | `New workspace` |
| Directory picker CTA | `Open folder` |
| Project-less CTA | `Start empty` |
| Workspace name placeholder | `workspace name` |
| Shell selector label | `Shell` |
| Layout selector label | `Layout` |
| Empty workspace name | `Untitled workspace` |
| Rename action | `Rename workspace` |
| Color action | `Color` |
| Close action | `Close workspace` |
| Close running confirmation | `Processes are running. Close workspace?` |
| Last workspace blocked | `Last workspace stays open` |
| Theme switch command | `Switch Theme` |
| Theme preview action | `Preview theme` |
| Theme apply success | `Theme changed` |
| Custom theme invalid | `Theme ignored` |
| Font switch command | `Switch Font` |
| Font apply success | `Font changed` |
| Profile switch command | `Switch Profile` |
| Profile apply success | `Profile changed` |
| High contrast command | `Toggle High Contrast` |
| Reduced motion label | `Reduced motion` |
| Bell command | `Set Bell Behavior` |

Error copy must name the failing object and recovery path:

- `Theme ignored: missing --bg-0`
- `Profile ignored: unsupported version`
- `Workspace not restored: session file is invalid`
- `Font unavailable: using JetBrains Mono`

Do not add visible explanatory text such as "Workspaces help you organize projects." Controls must be self-describing by label and placement.

---

## Workspace Tab Bar Contract

### Placement

The tab bar renders between the A1 titlebar and the grid pane area.

```text
Titlebar      22px
WorkspaceBar 28px
GridRoot     remaining height
```

The tab bar is part of app chrome, not a floating card. It spans full width.

### Layout

| Element | Contract |
|---|---|
| Background | `--bg-1` |
| Bottom border | `1px solid var(--border)` |
| Left inset | 12px, aligned with titlebar rhythm |
| Tab row | Horizontal, scrollable only after tabs exceed width |
| Add button | Fixed 28px square at row end; glyph `+`; tooltip/accessibility label `New workspace` |
| Active tab | `--bg-2`, `--fg-0`, 1px top rail in workspace accent token |
| Inactive tab | transparent/`--bg-1`, `--fg-2` |
| Hover tab | `--bg-2`, `--fg-1` |
| Dirty/running state | single `*` glyph or dim process dot; no badges with counts |

### Tab Anatomy

```text
[dot] workspace-name          [x]
```

- Dot is 8px and uses the workspace accent token.
- Name truncates with ellipsis.
- Close `x` is hover-revealed on pointer devices but remains reachable by keyboard.
- Active tab may show close button persistently if space allows.
- Tab height and width must not change on hover, active, close reveal, running state, or drag.

### Interaction

| Action | Behavior |
|---|---|
| Click tab | Switch active workspace; hidden workspaces stay mounted |
| Ctrl+1..Ctrl+9 | Switch to indexed workspace |
| Ctrl+Tab | Next workspace |
| Ctrl+Shift+Tab | Previous workspace |
| Double-click tab | Enter rename inline |
| Right-click/tab menu button | Open context menu |
| Drag tab | Reorder tabs; order persists |
| Click `+` | Open new workspace picker |
| Close tab | Confirm if any pane has a running foreground process; last workspace cannot close |

Focus after switching returns to the focused pane in the selected workspace.

### Context Menu

The context menu is a compact Variant B popover anchored to the tab.

| Row | Behavior |
|---|---|
| `Rename workspace` | Inline rename, selected text |
| `Color` | Opens fixed dot palette in the same popover |
| `Switch Profile` | Shows profile sublist if A7 command registry exists |
| `Close workspace` | Destructive row; asks confirmation if running processes exist |

Popover dimensions:

- Width: 220px max.
- Row height: 28px.
- Border: `1px solid var(--border-bright)`.
- Radius: 0px.
- Escape/outside-click dismisses.

Color dot row uses the fixed eight tokens. The active color shows a 1px `--focus` outline, not a filled badge.

---

## New Workspace Picker Contract

The picker is a centered overlay only for creating a workspace. It reuses A7 palette/toast infrastructure if available; otherwise it is a small A8-owned surface with the same visual rules.

| Property | Contract |
|---|---|
| Width | `min(560px, calc(100vw - 64px))` |
| Max height | `min(420px, calc(100vh - 96px))` |
| Background | `--bg-1` |
| Border | `1px solid var(--border-bright)` |
| Radius | 0px |
| Shadow | Existing hard terminal shadow only |
| Header height | 40px |
| Row height | 32px |

Fields:

- Workspace name input, defaulting to folder name or `Untitled workspace`.
- Folder row with `Open folder` action.
- Shell selector row.
- Layout selector row.
- Fixed color dot row.
- Primary action `Create workspace`.

The picker must support:

- Esc dismiss.
- Enter submits when valid.
- Tab/Shift+Tab trap inside overlay.
- No folder selected path: `Start empty` remains available.

No file tree, no onboarding explanation, and no agent selector in A8.

---

## Theme Contract

A8 ships 12 bundled curated themes:

1. Variant B
2. One Dark Pro
3. Dracula
4. Catppuccin Mocha
5. Gruvbox Dark
6. Tokyo Night
7. Nord
8. Monokai Pro
9. Solarized Dark
10. Catppuccin Latte
11. Solarized Light
12. GitHub Light

### Theme JSON Requirements

Each theme must define:

- `id`
- `name`
- `appearance: "dark" | "light"`
- `cssVars` for all required core and workspace tokens.
- `ansi` with 16 terminal colors.
- `selection`, `cursor`, and `cursorText` if not covered by `cssVars`.

### Theme Switch UI

Theme switching is via command palette sublist or compact picker, not a settings page.

Row contract:

```text
[T] Theme Name             dark/light
```

- Active theme shows right-aligned `active` in `--fg-3`.
- Hover may preview the theme immediately.
- Esc cancels preview and restores the committed theme.
- Enter/click commits the theme and shows `Theme changed`.
- Invalid custom theme rows are omitted; errors show toast/log copy.

Theme previews must update all chrome and panes within 100ms without remounting workspace grids.

---

## Appearance and Accessibility Contract

### Font Picker

Font switching is a compact command sublist.

Row contract:

```text
Font Name                  system/bundled
```

- The selected row may render its label in the candidate font for preview.
- Chrome labels outside the picker stay `--font-mono`.
- Font size floor is 10px.
- Size, line-height, letter-spacing, and ligature changes preview live in panes.
- Unavailable fonts fall back to JetBrains Mono with `Font unavailable: using JetBrains Mono`.

### Cursor

Allowed shapes:

- block
- bar
- underline

Blink options:

- off
- slow
- fast

Cursor color follows theme by default. Overrides are persisted but exposed only through compact command/profile surfaces in A8.

### Bell

Allowed behavior labels:

- `Visual flash`
- `Audible`
- `None`
- `Badge only`

Visual flash uses a short `--focus-glow` or `--accent-amber` pane-header flash and must respect reduced motion.

### Reduced Motion

A8 must add one global rule:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition: none !important;
    animation: none !important;
  }
}
```

If a user setting also disables motion, it applies the same class-level rule even when OS preference is not set.

### Transitions

Allowed transitions:

- Workspace tab hover/active color: 120ms ease.
- Split/close ratio movement: 150ms ease.
- Layout preset reflow: 200ms ease.
- Focus opacity/background shift: 120ms ease.

No spring physics, bouncing, parallax, or long fades.

### High Contrast

High contrast is a token overlay applied after the active theme. It must affect:

- titlebar
- workspace tabbar
- panes
- xterm foreground/background/ANSI mapping where feasible
- popovers/pickers
- toasts

Core foreground/background pairs must meet 7:1 contrast in automated tests.

---

## Platform-Native Chrome Contract

A8 keeps OS-native window shape, shadow, and resize behavior. It must not simulate rounded corners or shadows in web content.

### macOS

- Keep existing traffic-light positioning.
- Apply native vibrancy/window effect where Tauri supports it.
- System appearance follow may switch dark/light theme families only if a user theme is not pinned.
- Native menu integration wraps A7 registry if A7 is present.

### Windows

- Prefer supported Tauri/Windows effects for mica/acrylic/tabbed look.
- Preserve native snap layout behavior.
- Taskbar integration must not add web UI chrome.

### Linux

- No native blur assumption.
- Use CSS opacity fallback only.
- Desktop entry, tray icon, and WM_CLASS are platform metadata, not extra in-app UI.

All platform-effect errors fail soft and leave the app usable with opaque `--bg-0`.

---

## Profile Contract

Profiles are full settings snapshots. A8 provides minimal switching, not profile authoring UI beyond command/menu actions needed for acceptance.

Profile row contract:

```text
[P] Profile Name           pinned/active
```

Rules:

- Active profile shows right-aligned `active`.
- Workspace-pinned profile shows right-aligned `pinned`.
- Switching profile previews appearance immediately and commits terminal/layout defaults for future panes.
- Applying a profile shows `Profile changed`.
- Unsupported profile files fail safe with `Profile ignored: unsupported version`.

Default example names are allowed only in tests/fixtures:

- Work
- Personal
- Presentation

The app must not auto-create marketing/example profiles for real users.

---

## Pane Chrome Polish Contract

A8 may refine pane chrome but must not change A3/A4 semantics.

Allowed refinements:

- Resize handle hover state using `--border-bright`.
- Focus indicator consistency across all themes.
- Subtle drag affordance on handles.
- Bell visual flash.
- Theme-aware scrollbar colors.

Forbidden refinements:

- New pane badges.
- Per-pane theme overrides.
- Agent/cost/status content.
- Extra rows above/below pane headers.
- Decorative gradients or backgrounds behind terminal content.

Pane content area remains terminal-first and stable. Hover states must not resize panes.

---

## Copy and Empty States

A8 should avoid explanatory empty-state screens except inside the new workspace picker.

Allowed empty states:

- No folder selected in new workspace picker: `Start empty`.
- No custom themes: omit section entirely.
- No profiles: omit profile picker rows except built-in/default current profile if implemented.
- Last workspace close attempt: toast or inline message `Last workspace stays open`.

Do not show a full-page workspace education state. The app already has A5 setup window for first launch.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|---|---|---|
| shadcn official | none | not applicable |
| third-party UI registries | none | prohibited |
| icon packs | none | prohibited |
| animation libraries | none | prohibited |

Any new visual assets must be theme JSON or app metadata assets, not UI component registries.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-05-20

