# Phase A8: voss-app Workspaces, UX Polish, & Theming - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** A8-voss-app-workspaces-ux-polish-theming
**Areas discussed:** Workspace isolation, Theme engine depth, Vibrancy & platform, Animation & a11y

---

## Workspace isolation

### Q1: Inactive workspace behavior on switch

| Option | Description | Selected |
|--------|-------------|----------|
| Keep mounted (hidden) | All workspace GridRoots stay in DOM, visibility toggled via CSS display:none. PTYs keep running. Instant switch. Higher memory. Warp/iTerm2 model. | ✓ |
| Unmount/remount | Only active workspace mounted. Switch = unmount old + mount new. PTYs killed on unmount. Slower switch. Lower memory. | |
| Hybrid (cap) | Keep up to 3 workspaces mounted (MRU). 4th+ unmounts LRU. Balance memory vs speed. | |

**User's choice:** Keep mounted (hidden)
**Notes:** None.

### Q2: Workspace state structure

| Option | Description | Selected |
|--------|-------------|----------|
| Workspace = mini-App | Each workspace is self-contained: own GridStore, project signal, activeLayout, session context. App.tsx becomes thin orchestrator. | |
| Single store, keyed | One top-level store keyed by workspace ID. Active workspace ID selects sub-tree. | |
| You decide | Planner picks based on minimizing GridRoot changes. | ✓ |

**User's choice:** You decide
**Notes:** Planner has discretion, bounded by D-01 (all mounted) and existing architecture.

### Q3: Workspace accent colors

| Option | Description | Selected |
|--------|-------------|----------|
| Auto from name hash | Deterministic color from project name hash. Override from 6 accent palette colors. No custom hex. | |
| Manual pick only | No auto-color. User picks from accent palette explicitly. | |
| Auto + custom hex | Auto hash default + custom hex via mini color picker. | Initially selected |

**User's choice:** Changed to fixed dot palette (Warp-style) after user provided Warp screenshot showing ~8 color dots. No custom hex picker — fixed palette only.
**Notes:** User provided Warp screenshot reference. Revised D-03 from "auto + custom hex" to Warp-style fixed dot palette (~8 preset colors).

### Q4: Workspace persistence

| Option | Description | Selected |
|--------|-------------|----------|
| workspaces.json index | Top-level index + per-workspace session files. Project workspaces use .voss/session.json. Project-less use ~/.config/voss-app/sessions/<id>.json. | ✓ |
| Single merged file | One big session-state.json with everything inlined. | |
| You decide | Planner picks, bounded by A6 pattern. | |

**User's choice:** workspaces.json index
**Notes:** None.

---

## Theme engine depth

### Q1: Theme mapping depth

**User intervention before answering:** User clarified that they want curated bundled themes only, not a VSCode import engine. "Pick several popular themes and only offer those." Question was reformulated.

### Q2: Which bundled themes

| Option | Description | Selected |
|--------|-------------|----------|
| ROADMAP 11 + Variant B | All 11 from ROADMAP (8 dark + 3 light) plus Variant B default. 12 total. | ✓ |
| Trim to 6-8 | Most popular subset only. | |
| You pick | Planner curates 8-12 based on popularity + color diversity. | |

**User's choice:** ROADMAP 11 + Variant B
**Notes:** None.

### Q3: Theme storage format

| Option | Description | Selected |
|--------|-------------|----------|
| Static JSON in repo | Each theme = JSON file with CSS var mappings + ANSI colors. Hand-curated. Build-time bundled. Reuses applyThemeOverrides(). | ✓ |
| CSS files per theme | Each theme = CSS file with :root overrides. Dynamic <link> swap. | |
| You decide | Planner picks, bounded by ≤100ms hot-swap and existing applyThemeOverrides(). | |

**User's choice:** Static JSON in repo
**Notes:** None.

### Q4: Custom theme support

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, same JSON schema | .voss/themes/<name>.json using bundled schema. Shows in picker. Power-user escape hatch. | ✓ |
| Defer to later | 12 bundled only. Custom authoring deferred. | |
| Yes + live preview | Custom themes + hover preview in picker. | |

**User's choice:** Yes, same JSON schema
**Notes:** None.

---

## Vibrancy & platform

### Q1: Vibrancy depth

| Option | Description | Selected |
|--------|-------------|----------|
| Native vibrancy (macOS) | macOS: NSVisualEffectView. Windows: acrylic/mica. Linux: CSS opacity fallback. Opacity slider 0.5–1.0. | ✓ |
| CSS-only opacity | No native vibrancy. Opacity slider adjusts bg alpha. Simulated transparency. | |
| macOS only, defer rest | Native vibrancy macOS only. Others get CSS opacity. | |

**User's choice:** Native vibrancy (macOS) — which includes all platforms
**Notes:** None.

### Q2: Platform-native polish depth

| Option | Description | Selected |
|--------|-------------|----------|
| macOS polished, rest stub | macOS full polish. Windows/Linux basic. | |
| All three polished | Equal investment across macOS, Windows, Linux. | ✓ |
| macOS only | Skip Windows/Linux platform work. | |

**User's choice:** All three polished
**Notes:** None.

### Q3: Window corner radius + shadow

| Option | Description | Selected |
|--------|-------------|----------|
| OS-native defaults | Let each OS handle corners and shadows natively. | ✓ |
| Custom radius per OS | Override Tauri decorations for exact control. | |
| You decide | Planner picks based on Tauri 2 capabilities. | |

**User's choice:** OS-native defaults
**Notes:** None.

---

## Animation & accessibility

### Q1: Animation infrastructure

| Option | Description | Selected |
|--------|-------------|----------|
| CSS transitions only | Pure CSS transitions. 150ms ease split/close, 200ms layout reflow. prefers-reduced-motion kills all. No JS lib. | ✓ |
| Solid.js Transition | Solid <Transition> for mount/unmount + CSS for reflow. Hybrid. | |
| No animation | Skip all animation. Instant snaps. Add later. | |

**User's choice:** CSS transitions only
**Notes:** None.

### Q2: High-contrast mode

| Option | Description | Selected |
|--------|-------------|----------|
| Token override layer | CSS var overrides on top of active theme. WCAG AAA 7:1 min. Keeps theme hue, bumps luminance. Toggle in settings.json. | ✓ |
| Dedicated HC theme | Separate standalone high-contrast theme. | |
| OS high-contrast only | Detect OS settings, auto-apply. No manual toggle. | |

**User's choice:** Token override layer
**Notes:** None.

### Q3: Font picker

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown + live preview | System font enumeration. Live preview in all panes. Size/line-height/spacing sliders. Ligature toggle. JetBrains Mono fallback. | ✓ |
| Text input + preview | User types font name. Autocomplete from curated list. | |
| You decide | Planner picks UX. | |

**User's choice:** Dropdown + live preview
**Notes:** None.

### Q4: Setting profiles scope

| Option | Description | Selected |
|--------|-------------|----------|
| Profile = appearance snapshot | Captures theme, font, opacity, cursor, high-contrast only. | |
| Profile = full settings | Captures ALL settings: appearance + terminal + layout defaults. | ✓ |
| Defer profiles | Skip profiles in A8. Add in A9. | |

**User's choice:** Profile = full settings
**Notes:** None.

---

## Claude's Discretion

- D-02: Workspace state structure (mini-App vs keyed store)
- Theme JSON schema exact shape
- Workspace tab bar visual design
- Font enumeration implementation
- Bell behavior configuration
- Cursor customization options
- Pane chrome refinement details
- Profile schema shape
- Workspace accent color dot picker placement (inline vs popover)

## Deferred Ideas

None — discussion stayed within A8 scope. VSCode theme import engine dropped from scope entirely (not deferred — removed).
