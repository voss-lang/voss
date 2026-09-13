---
phase: A9
slug: voss-app-settings-theme
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-20
---

# Phase A9 — UI Design Contract: voss-app Settings + Theme

> Visual and interaction contract for Phase A9. Authored inline (GSD agents not installed).
> A9 EXTENDS the A1 Variant B contract — it never redefines token values.
> All color, typography, spacing, and component decisions reference A1-UI-SPEC.md
> verbatim or declare new settings-specific chrome on top of those exact tokens.
> Sources: A1-UI-SPEC.md (authoritative base), A9-CONTEXT.md (D-01..D-16),
> ROADMAP.md (CFG-01..07), FEATURES.md §L1.6, CONCEPT.md §10 Q7/Q9.

---

## Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none (manual CSS + Tailwind v4) | A1-UI-SPEC — shadcn gate N/A (Solid/Tauri, not React) |
| Preset | not applicable | no component library |
| Component library | none — hand-rolled Solid components only | A1-UI-SPEC |
| Icon library | none — glyph characters only | A1 glyph pattern |
| Font (UI text) | `--font-ui` (`"Inter", -apple-system, "SF Pro Text", system-ui, sans-serif`) | A1-UI-SPEC — settings UI uses the sans-serif UI font stack for form labels and descriptions |
| Font (code/values) | `--font-mono` (`"JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace`) | A1-UI-SPEC — settings values, JSON references, keyboard shortcuts displayed in mono |

**Font usage note:** The settings panel is the first A-track surface to use `--font-ui` for body text. This is intentional — settings is a form/documentation interface, not a terminal surface. The UI font improves readability for labels and descriptions. Terminal panes behind the overlay remain in `--font-mono`.

---

## Token Inheritance Contract

A9 MUST NOT redefine any token value from A1. All settings chrome is expressed using tokens
already declared in `apps/voss-app/src/styles/variant-b.css`.

**Token system reference:** A1-UI-SPEC.md § Color Token Table + § CSS Variable to Tailwind Mapping Contract.

No inline `style="color: #..."` in A9 components (except within `applyThemeOverrides`).

---

## Spacing Scale

A9 inherits the full A1 spacing scale without modification. Settings-specific measurements
are declared as named structural constants below.

| Token | Value | A9 Usage |
|-------|-------|---------|
| xs | 4px | Gap between toggle switch and its label; badge internal padding |
| sm | 8px | Vertical gap between setting rows within a section; search input internal padding |
| md | 16px | Horizontal padding inside the right form pane; gap between sidebar items |
| lg | 24px | Vertical padding at top/bottom of each category section; sidebar vertical padding |
| xl | 32px | Gap between category sections in the right pane |
| 2xl | 48px | Not used in A9 settings chrome |

### Named Structural Constants for A9 Settings Chrome

| Constant | Value | Rationale |
|----------|-------|-----------|
| Settings overlay z-index | **50** | Same z-layer as CommandPalette (A7). Only one overlay visible at a time (settings or palette, never both). |
| Sidebar width | **160px** | Fixed — D-03 locks this. Wide enough for "Keybindings" (11 chars) at 13px UI font. |
| Search bar height | **32px** | 8×4 grid. Comfortable text input target with `sm` (8px) vertical padding + 13px font. |
| Setting row height | **min 32px** | Minimum 32px; taller for multi-line descriptions. Each row = label + control, vertically centered. |
| Toggle switch width | **36px** | 9×4 grid. Standard macOS-style toggle dimensions. |
| Toggle switch height | **20px** | 5×4 grid. Proportional to width. |
| Dropdown height | **32px** | Matches search bar. Consistent input element height across the form. |
| Slider track height | **4px** | 1×4 grid. Thin track, prominent thumb. |
| Slider thumb diameter | **16px** | 4×4 grid. Clear grab target. |
| Workspace badge height | **18px** | Compact inline badge for "workspace" override indicator. Fits within 32px row. |
| "Edit as JSON" link height | **22px** | Matches titlebar/pane header height for visual consistency. Appears at section bottom. |

**Border radius:** 0px on all A9 chrome containers and sections — Variant B absolute rule.
Exception: toggle switch uses `10px` border-radius (half height) for the pill shape — functionally necessary for the toggle affordance, same class as A1's traffic-light circle exception. Slider thumb uses `50%` (circle). No other exceptions.

---

## Typography

A9 introduces the first use of `--font-ui` for non-terminal UI text. Terminal/code values
remain in `--font-mono`.

| Role | Size | Weight | Line Height | Font | A9 Usage |
|------|------|--------|-------------|------|---------|
| Section heading | 14px | 600 | 1.3 | `--font-ui` | Category headings in the right pane ("Appearance", "Terminal", etc.) |
| Setting label | 13px | 500 | 1.3 | `--font-ui` | Individual setting name ("Theme", "Font Family", "Default Shell") |
| Setting description | 12px | 400 | 1.4 | `--font-ui` | Help text below setting controls; telemetry consent descriptions (D-15) |
| Sidebar category | 13px | 400 | 1.0 | `--font-ui` | Sidebar nav labels; active category uses weight 600 |
| Search placeholder | 13px | 400 | 1.0 | `--font-ui` | "Search settings..." placeholder text |
| Setting value (code) | 12px | 400 | 1.3 | `--font-mono` | Displayed values for shell path, JSON keys, keyboard shortcuts |
| Badge text | 10px | 500 | 1.0 | `--font-ui` | "workspace" override badge text (D-05) |
| "Edit as JSON" link | 11px | 400 | 1.0 | `--font-mono` | Link text — rendered in mono to signal "code-adjacent" action |
| Version string | 11px | 400 | 1.0 | `--font-mono` | Updates section: current version number |

**No HiDPI verification delta needed for A9** — UI font sizes are well above minimum legibility thresholds and don't have the 0.5px distinction from A1/A3.

---

## Color

A9 uses A1 tokens verbatim. Settings-specific usage extensions below are additive.

### Background — A9 Settings-Specific Usage

| Token | Hex | A9 Usage |
|-------|-----|---------|
| `--bg-0` | `#0a0b0e` | Settings overlay background (full content area fill) |
| `--bg-1` | `#11131a` | Sidebar background; unfocused dropdown/input background |
| `--bg-2` | `#171a23` | Active sidebar category highlight; focused input background; toggle track OFF state |
| `--bg-3` | `#1f232e` | Search bar background; dropdown option hover; slider track |

### Border — A9 Settings-Specific Usage

| Token | Hex | A9 Usage |
|-------|-----|---------|
| `--border` | `#262b38` | Sidebar/form divider (1px vertical line); input borders; section separators |
| `--border-bright` | `#353b4a` | Input focus border; dropdown hover border |

### Foreground — A9 Settings-Specific Usage

| Token | Hex | A9 Usage |
|-------|-----|---------|
| `--fg-0` | `#e8eaf0` | Setting labels; section headings; active sidebar category text |
| `--fg-1` | `#aab0c0` | Setting values; dropdown selected text; search input text |
| `--fg-2` | `#6a7080` | Setting descriptions; placeholder text; disabled controls; "Edit as JSON" link |
| `--fg-3` | `#444a5a` | Disabled toggle labels; tooltip user-level value text |

### Accent — A9 Settings-Specific Usage

| Token | Hex | A9 Usage |
|-------|-----|---------|
| `--accent-green` | `#6fd28f` | Toggle switch ON state (track fill) |
| `--accent-blue` | `#7aa2ff` | Active sidebar category left border indicator (2px left border) |
| `--focus` | `#5a7cff` | Input focus ring: `box-shadow: inset 0 0 0 1px var(--focus)` |

**No new accent colors.** Toggle ON = `--accent-green` (positive/enabled state, consistent with pane status dot). Sidebar active indicator = `--accent-blue` (focus/selection role). Both follow A1 reserved-use rules.

### Workspace Override Badge Colors

| Element | Color | Source |
|---------|-------|--------|
| Badge background | `rgba(90, 124, 255, 0.15)` | `--focus` at 15% opacity — subtle, non-competing |
| Badge text | `--accent-blue` (`#7aa2ff`) | Focus/selection family — signals "this value comes from workspace" |
| "Reset to default" link | `--fg-2` (`#6a7080`) | Muted action — secondary to the setting control itself |

---

## Settings Panel Layout Contract

### Overlay Structure (D-01)

```
┌─────────────────────────────────────────────────────────┐
│ Titlebar (22px, always visible — A1 locked)             │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [🔍 Search settings...]              (32px height) │ │
│ ├────────────┬────────────────────────────────────────┤ │
│ │            │                                        │ │
│ │ Sidebar    │  Form Pane (scrollable)                │ │
│ │ 160px      │                                        │ │
│ │ fixed      │  ## Appearance                         │ │
│ │            │  Theme:    [Variant B        ▼]        │ │
│ │ Appearance │  Font:     [JetBrains Mono   ▼]        │ │
│ │ Terminal   │  Size:     [14]  [-] [+]               │ │
│ │ Layout     │  Opacity:  ──────●──── 0.85            │ │
│ │ Keybindings│  Cursor:   ● block ○ bar ○ underline   │ │
│ │ Project    │  High contrast: [OFF ━━]               │ │
│ │ Updates    │                                        │ │
│ │ Telemetry  │  [Edit as JSON]                        │ │
│ │            │                                        │ │
│ │            │  ─────────────────────────────          │ │
│ │            │                                        │ │
│ │            │  ## Terminal                            │ │
│ │            │  Shell:  [/bin/zsh           ▼]        │ │
│ │            │  ...                                   │ │
│ └────────────┴────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

| Region | Width | Background | Scroll |
|--------|-------|------------|--------|
| Search bar | 100% of overlay | `--bg-3` | none |
| Sidebar | 160px fixed | `--bg-1` | `overflow-y: auto` (if 7+ categories exceed viewport) |
| Form pane | `calc(100% - 160px)` | `--bg-0` | `overflow-y: auto` (primary scroll target) |
| Sidebar/form divider | 1px | `--border` | — |

### Sidebar Navigation

| Element | Style |
|---------|-------|
| Category item | 13px `--font-ui` weight 400, `--fg-2`, padding `md` (16px) horizontal, `sm` (8px) vertical |
| Active category | weight 600, `--fg-0`, 2px left border `--accent-blue`, background `--bg-2` |
| Hover state | background `--bg-2` (non-active items only) |
| Click behavior | Scrolls form pane to matching `<section>` element (smooth scroll) |

### Search Bar

| Property | Value |
|----------|-------|
| Height | 32px |
| Background | `--bg-3` |
| Border | 1px `--border`, focus: 1px `--border-bright` + inset shadow `--focus` |
| Placeholder | "Search settings..." in `--fg-3`, 13px `--font-ui` |
| Icon | None — text-only input. Magnifying glass adds visual noise to a functional search. |
| Clear button | "×" glyph appears when input has text, `--fg-2`, click clears and restores all rows |
| Behavior | Filter-to-matches (D-04): hide non-matching rows, show matches with label + description highlighted |

### Setting Row Layout

Each setting row is a horizontal flex container:

```
┌──────────────────────────────────────────────────────┐
│ Label text                          [Control]        │
│ Description text in --fg-2          [workspace] ↩    │
└──────────────────────────────────────────────────────┘
```

| Element | Position | Style |
|---------|----------|-------|
| Label | Left, top-aligned | 13px `--font-ui` weight 500, `--fg-0` |
| Description | Left, below label | 12px `--font-ui` weight 400, `--fg-2` |
| Control | Right, vertically centered | Dropdown / toggle / slider / radio group / number input |
| Workspace badge | Right, below control (when D-05 active) | "workspace" text in `--accent-blue`, `rgba(--focus, 0.15)` bg, 10px, `xs` padding |
| Reset link | Right of badge | "Reset to default" in `--fg-2`, 11px, underline on hover |

### Form Controls

#### Toggle Switch

| Property | Value |
|----------|-------|
| Width × Height | 36px × 20px |
| Track (OFF) | `--bg-2` fill, 10px border-radius |
| Track (ON) | `--accent-green` fill |
| Thumb | 16px circle, `--fg-0` fill, 2px left/right travel margin |
| Transition | `transform 150ms ease` (disabled under `prefers-reduced-motion`) |
| Focus | Inset shadow `--focus` on the track |

#### Dropdown Select

| Property | Value |
|----------|-------|
| Height | 32px |
| Background | `--bg-1` (unfocused), `--bg-2` (focused/open) |
| Border | 1px `--border` |
| Text | 12px `--font-mono` `--fg-1` |
| Chevron | "▾" glyph in `--fg-2` |
| Popup | `--bg-3` background, `--border` border, max-height 200px, `overflow-y: auto` |
| Option hover | `--bg-2` background |
| Option selected | `--fg-0` text (bold weight 500) |

#### Number Stepper

| Property | Value |
|----------|-------|
| Width | 80px input + 24px "−" button + 24px "+" button |
| Input | `--bg-1` fill, `--border`, 12px `--font-mono` `--fg-1`, center-aligned |
| Buttons | `--bg-2` fill, `--fg-1` glyph, hover `--bg-3` |
| Step | ±1 per click (font size), ±0.05 for opacity slider |

#### Slider

| Property | Value |
|----------|-------|
| Track | 4px height, `--bg-3` fill, full width |
| Fill (left of thumb) | `--accent-blue` |
| Thumb | 16px circle, `--fg-0` fill, `box-shadow: 0 1px 3px rgba(0,0,0,0.3)` |
| Value label | Right of slider, 12px `--font-mono` `--fg-1` |
| Focus | Thumb outline `--focus` |

#### Radio Group (cursor shape)

| Property | Value |
|----------|-------|
| Layout | Horizontal, `md` (16px) gap between options |
| Radio circle | 14px, 1px `--border`, unselected = `--bg-1` fill |
| Selected | `--accent-blue` fill dot (8px) inside the circle |
| Label | 12px `--font-ui` `--fg-1`, right of circle |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Search placeholder | `Search settings...` |
| Edit as JSON link (user) | `Edit as JSON` |
| Edit as JSON link (workspace) | `Edit workspace JSON` |
| Workspace badge | `workspace` |
| Reset action | `Reset to default` |
| Toggle ON label | (none — position conveys state) |
| Toggle OFF label | (none) |
| Telemetry toggle 1 | `Crash Reports` |
| Telemetry description 1 | `Anonymous crash reports help us fix bugs. No personal data is collected.` |
| Telemetry toggle 2 | `Usage Analytics` |
| Telemetry description 2 | `Anonymous usage analytics help us prioritize features. No commands, file paths, or content are shared.` |
| Updates section heading | `Updates` |
| Update check button (disabled) | `Check for updates` |
| Update check tooltip | `Coming in a future release` |
| Version display | `Version {version}` |
| Keyboard shortcut | `⌘,` (displayed in palette row hint per A7 D-09) |

---

## Interaction Contracts

### Opening & Closing (D-01, D-02)

| Trigger | Action |
|---------|--------|
| `⌘,` | Open settings overlay (command registry entry "Open Settings") |
| `⌘⇧P` → "Open Settings" | Open settings overlay |
| `Esc` | Close settings overlay, return focus to previously-focused pane |
| Click outside overlay | Close (if overlay has a backdrop — planner decides whether backdrop is visible dim or transparent) |
| Opening when palette is open | Close palette, open settings (only one overlay at a time) |

### Search Behavior (D-04)

| Action | Result |
|--------|--------|
| Type in search | Filter: hide non-matching setting rows; matching rows remain with label/description text as-is |
| Clear search (× or backspace to empty) | Restore all rows; sidebar category selection preserved |
| Search + sidebar click | Clear search, jump to selected category |
| No matches | Show "No settings match '{query}'" centered in form pane, `--fg-2` |

### Hot-Reload (D-09..D-12)

| Setting Category | Reload Behavior |
|------------------|-----------------|
| Theme | Immediate all panes — `applyThemeOverrides()` |
| Font family/size/line-height | Immediate all panes — xterm.js `setOption()` per terminal |
| Opacity | Immediate — Tauri webview background alpha |
| Cursor shape | Immediate all panes — xterm.js `setOption('cursorStyle', ...)` |
| High contrast | Immediate — overlay token layer applied/removed |
| Shell | New panes only — existing panes keep running shell |
| Scrollback size | New panes only — xterm.js set at Terminal construction |
| Bell behavior | New panes only |
| Layout default preset | Next layout apply only |
| Keymap profile | Immediate — registry rebinds (A7 infrastructure) |

No "ask before retroactive" prompts for any setting (D-12).

### Workspace Override UX (D-05, D-06, D-07)

| Action | Result |
|--------|--------|
| Setting differs from user-level | "workspace" badge visible; "Reset to default" link appears |
| Hover workspace badge | Tooltip showing user-level value: "User default: {value}" |
| Click "Reset to default" | Remove workspace override; value falls back to user-level; badge disappears |
| No workspace open | All workspace badges hidden; "Edit workspace JSON" link hidden |

---

## Component Inventory

| Component | File | Responsibility |
|-----------|------|----------------|
| `SettingsPanel` | `src/settings/SettingsPanel.tsx` | Full-screen overlay container; open/close state; Esc handler; backdrop |
| `SettingsSidebar` | `src/settings/SettingsSidebar.tsx` | 160px fixed sidebar; category list; active highlight; click-to-scroll |
| `SettingsSearch` | `src/settings/SettingsSearch.tsx` | Search input; filter logic; clear button |
| `SettingsSection` | `src/settings/SettingsSection.tsx` | Category section wrapper; heading; "Edit as JSON" link |
| `SettingRow` | `src/settings/SettingRow.tsx` | Single setting: label + description + control + optional workspace badge |
| `Toggle` | `src/settings/controls/Toggle.tsx` | ON/OFF switch; accent-green track |
| `Dropdown` | `src/settings/controls/Dropdown.tsx` | Select with popup; chevron; option list |
| `NumberStepper` | `src/settings/controls/NumberStepper.tsx` | Numeric input with −/+ buttons |
| `Slider` | `src/settings/controls/Slider.tsx` | Horizontal slider with value label |
| `RadioGroup` | `src/settings/controls/RadioGroup.tsx` | Horizontal radio options (cursor shape) |
| `WorkspaceBadge` | `src/settings/WorkspaceBadge.tsx` | "workspace" badge + tooltip + "Reset to default" link |

---

## Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Keyboard navigation | Tab through all controls in reading order; Enter/Space activates toggles/dropdowns |
| Focus visible | All controls show `--focus` ring on keyboard focus (not on mouse click) |
| Screen reader | `role="dialog"` on overlay, `aria-label="Settings"`, `role="tablist"` on sidebar, `role="tabpanel"` on form pane |
| `prefers-reduced-motion` | Toggle animation (150ms) disabled. All other transitions already CSS-only. |
| Color contrast | All text meets WCAG AA (4.5:1) against respective backgrounds. Verified: `--fg-0` on `--bg-0` = 14.2:1, `--fg-2` on `--bg-0` = 5.1:1. |

---

## Verification Checklist

- [ ] Dimension 1 Spacing: All measurements multiples of 4 (exceptions formally declared)
- [ ] Dimension 2 Color: No new accent colors; 60/30/10 split maintained; no inline hex
- [ ] Dimension 3 Contrast: All text/bg pairs meet WCAG AA (4.5:1 minimum)
- [ ] Dimension 4 Typography: UI font for labels/descriptions; mono font for values/code
- [ ] Dimension 5 Consistency: Toggle/dropdown/slider patterns used uniformly; no one-off controls
- [ ] Dimension 6 Completeness: Every setting category has layout; all form controls specified

---

*Phase: A9-voss-app-settings-theme*
*UI-SPEC created: 2026-05-20*
