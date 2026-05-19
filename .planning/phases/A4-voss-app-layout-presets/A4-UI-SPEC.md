---
phase: A4
slug: voss-app-layout-presets
status: approved
shadcn_initialized: false
preset: none
created: 2026-05-19
---

# Phase A4 - UI Design Contract: voss-app Layout Presets

> Visual and interaction contract for Phase A4. A4 EXTENDS the A1 Variant B and A3 grid contracts. It must not redefine token values, introduce a component library, or add semantic/agent meaning to layout presets.
> Sources: A1-UI-SPEC.md, A3-UI-SPEC.md, A4-CONTEXT.md, A4-RESEARCH.md, ROADMAP A4, sketch 001 Variant B.

---

## Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none (manual CSS + Tailwind v4) | A1/A3 UI contracts; Solid/Tauri, not React |
| Preset | not applicable | no component library |
| Component library | none - hand-rolled Solid components only | A1/A3 pattern |
| Icon library | none - glyph characters only (`fanout`, `pipeline`, `swarm`, `watchers`, `custom`, `...`) | Variant B density rule |
| Font (all UI) | `"JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace` | A1 `--font-mono` |

**shadcn gate:** not applicable. No `components.json` exists or is needed.

---

## Token Inheritance Contract

A4 MUST use the existing Variant B tokens from `apps/voss-app/src/styles/variant-b.css` and the Tailwind v4 mappings from `apps/voss-app/src/index.css`.

A4 MUST NOT:

- Add new color tokens.
- Use raw hex values in component code.
- Add rounded corners.
- Add animation or gradient treatment.
- Add cards, popovers, or landing-page-style explanatory text.
- Add L2 agent semantics to preset labels.

A4 may add component-level CSS classes, but their values must be composed from existing CSS variables:

- `--bg-0`, `--bg-1`, `--bg-2`, `--bg-3`
- `--border`, `--border-bright`
- `--focus`, `--focus-glow`
- `--fg-0`, `--fg-1`, `--fg-2`, `--fg-3`
- `--accent-green`, `--accent-amber`, `--accent-red`, `--accent-cyan`, `--accent-magenta`, `--accent-blue`
- `--titlebar-height`

---

## Spacing Scale

A4 inherits A1/A3 spacing exactly. No new spacing tokens are introduced.

| Token | Value | A4 Usage |
|-------|-------|----------|
| xs | 4px | Gap between preset label and compact status glyphs if needed |
| sm | 6px | Hit target inset and traffic-light gap inherited from A1 |
| md | 8px | Compact command-stub row padding and switcher internal grouping |
| base | 10px | Titlebar switcher horizontal button padding, inherited from A1 |
| lg | 12px | Titlebar edge/alignment spacing inherited from A1 |
| xl | 16px | Fixed menu/stub row side padding if a temporary command surface is needed |
| 2xl | 24px | Not used in A4 chrome |

### Structural Constants

| Constant | Value | A4 Usage |
|----------|-------|----------|
| Titlebar height | 22px | Preset switcher must fit inside the existing titlebar without increasing height |
| Switcher border | 1px | Outer switcher border and internal dividers |
| Switcher radius | 0px | Variant B no-rounding rule |
| Preset button height | 20px max inside 22px titlebar | Leaves room for the 1px switcher border top/bottom |
| Preset button padding | `0 10px` | Same horizontal rhythm as A1 titlebar controls |
| Save/load stub row height | 22px | If A4 exposes temporary command rows before A7, rows match header density |
| Inline error row height | 22px | Single-line layout file errors; no modal required in A4 |

**Exception policy:** A4 inherits A1's named exceptions (`6px`, `10px`, `22px`). Do not snap these to the 4px grid; they are already locked by the Variant B sketch and A1 contract.

---

## Typography

A4 inherits the A1/A3 typography scale. No new type roles are introduced.

| Role | Size | Weight | Line Height | Font | A4 Usage |
|------|------|--------|-------------|------|----------|
| Titlebar / switcher label | 11px | 400 | 1.0 | `--font-mono` | `fanout`, `pipeline`, `swarm`, `watchers`, `custom` |
| Body / stream | 11.5px | 400 | 1.5 | `--font-mono` | PTY output only; A4 does not alter body text |
| Metadata / shortcut | 10px | 400 | 1.0 | `--font-mono` | `Cmd+G` hint or dim shortcut text if shown in a temporary command stub |
| Active label | 12px | 600 | 1.0 | `--font-mono` | Not used by A4 preset labels; active state is color/background, not heavier text |

Preset labels are lowercase literal labels:

- `fanout`
- `pipeline`
- `swarm`
- `watchers`
- `custom`

Do not use title case (`Fanout`) or marketing copy (`Fanout Mode`). These are functional terminal controls, not feature explanations.

---

## Color

A4 uses A1/A3 tokens verbatim.

### Preset Switcher

| State | Background | Text | Border | Notes |
|-------|------------|------|--------|-------|
| Container | `transparent` or `--bg-0` | n/a | `1px solid var(--border)` | No radius, no shadow |
| Inactive preset | `transparent` | `--fg-2` | internal divider `--border` | Same quiet density as A1 visual switcher |
| Hover inactive | `--bg-2` | `--fg-1` | internal divider `--border-bright` only if already present | Neutral lift only |
| Active preset | `--focus` | `--fg-0` | `--focus` | Active state mirrors existing A1 switcher behavior but uses token text, not raw white |
| Custom state | `--bg-3` | `--accent-amber` | `--border-bright` | Indicates off-cycle manual geometry without implying error |
| Disabled/loading | `transparent` | `--fg-3` | `--border` | Used only while loading a layout file |

### Save / Load Feedback

| State | Color | Usage |
|-------|-------|-------|
| Saved / loaded | `--accent-green` | One-line success toast/row text only |
| Missing default layout | `--fg-3` | Silent/no-op or dim diagnostic in logs; not a user-facing warning |
| Corrupt layout ignored | `--accent-amber` | Non-fatal warning row/toast |
| Save/load failure | `--accent-red` | Error row/toast with recovery path |

Accent remains reserved for semantic state only. Do not use accent colors as generic hover colors.

---

## Titlebar Preset Switcher Contract

A4 converts `PresetSwitcher` from A1 local visual state into a controlled component. It receives:

- `activeLayout: 'fanout' | 'pipeline' | 'swarm' | 'watchers' | 'custom'`
- `disabled?: boolean`
- `onSelect(preset: LayoutPreset): void`

### Layout

The switcher remains in the existing A1 titlebar right cluster. It must not change titlebar height or project-title alignment.

Visual order is fixed:

```text
fanout | pipeline | swarm | watchers
```

The `custom` state is not a fifth clickable preset in the main row. It appears as a compact state label immediately before the preset row only when the current tree is off-cycle:

```text
custom  fanout | pipeline | swarm | watchers
```

`custom` uses `--accent-amber` text on `--bg-3`; it is display-only. Clicking `custom` does nothing.

### Interaction

| Action | Behavior |
|--------|----------|
| Click preset | Applies that preset to existing panes and updates active state to the clicked preset |
| `Cmd+G` from `custom` | Applies `fanout` |
| `Cmd+G` from `fanout` | Applies `pipeline` |
| `Cmd+G` from `pipeline` | Applies `swarm` |
| `Cmd+G` from `swarm` | Applies `watchers` |
| `Cmd+G` from `watchers` | Applies `fanout` |
| Manual split/fork/close/resize/equalize after a preset | Active state becomes `custom` unless the resulting tree is explicitly re-detected as the same preset |
| Layout load | Active state becomes the loaded layout's `activePreset`, or `custom` if the file stores custom geometry |

Switching presets is instant. No animation is allowed because panes may contain active PTY output and A2/A3 prioritize frame stability.

### Accessibility

Each clickable preset is a real `button` with:

- `aria-pressed="true"` only for the active preset.
- `aria-label="Switch layout to fanout"` etc.
- Disabled state while a layout file is loading.

The `custom` label uses `aria-label="Custom layout"` and is not focusable.

### Overflow

The titlebar switcher must remain usable down to the A1 minimum window width. If space is constrained:

1. Hide the `custom` display label first.
2. Reduce preset horizontal padding from 10px to 8px.
3. Keep all four preset labels visible.
4. Never collapse to icons, because these preset names are the control labels.

---

## Preset Geometry Visual Contract

A4 is visual geometry only. The preset names do not imply process role, agent role, prompt routing, worktree behavior, or any L2 semantic behavior.

| Preset | Visual Arrangement | Pane Mapping |
|--------|--------------------|--------------|
| `fanout` | Pane 1 primary on the left, remaining panes in a right-side vertical column | Stable A3 pane-index order; pane 1 fills primary slot |
| `pipeline` | Left-to-right equal row | Stable A3 pane-index order from left to right |
| `swarm` | Near-square grid, 2x2 default, growing toward 4x4 | Stable A3 pane-index order from top-left across rows |
| `watchers` | Pane 1 main on top, watcher panes in a thin bottom row | Stable A3 pane-index order; pane 1 fills main slot |

All preset switches preserve:

- Existing pane ids.
- Existing PTY sessions.
- Existing cwd and shell metadata.
- Existing focused pane id.
- Pane index recomputation after geometry changes.

Focus treatment remains exactly A3's inset shadow and header bg-lift. Do not add arrows, badges, flow lines, semantic labels, or per-preset decorative marks.

---

## Save / Load Layout UI Contract

A7 owns the full command palette. A4 only provides command handlers and a minimal callable/stub surface if needed for manual testing.

### Save Layout As

Copy:

| Element | Copy |
|---------|------|
| Command label | `Save layout as...` |
| Input placeholder | `layout name` |
| Success | `layout saved` |
| Name exists | `replace existing layout?` |
| Invalid name | `layout name cannot contain /, \\ or ..` |
| Failure | `could not save layout` |

Collision policy is planner discretion, but UI must use the exact confirmation copy above if overwrite confirmation is implemented.

### Load Layout

Copy:

| Element | Copy |
|---------|------|
| Command label | `Load layout...` |
| Empty list | `no saved layouts` |
| Success | `layout loaded` |
| Missing file | `layout not found` |
| Corrupt file | `layout ignored: invalid file` |
| Unsupported version | `layout ignored: unsupported version` |
| Failure | `could not load layout` |

Errors are single-line rows/toasts. No modal is required in A4.

### Default Layout

If `.voss/layouts/default.json` exists, loading it should produce no extra visible chrome beyond the resulting geometry and active switcher state.

If it is missing, the app should stay quiet.

If it is corrupt or unsupported, show/log only:

```text
layout ignored: invalid file
```

or:

```text
layout ignored: unsupported version
```

Do not block startup, do not clear panes, and do not show a destructive confirmation.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary preset controls | `fanout`, `pipeline`, `swarm`, `watchers` |
| Off-cycle state | `custom` |
| Keyboard cycle hint | `Cmd+G` |
| Save command | `Save layout as...` |
| Load command | `Load layout...` |
| Save success | `layout saved` |
| Load success | `layout loaded` |
| Empty saved-layout list | `no saved layouts` |
| Invalid name | `layout name cannot contain /, \\ or ..` |
| Corrupt layout | `layout ignored: invalid file` |
| Unsupported layout version | `layout ignored: unsupported version` |
| Generic save failure | `could not save layout` |
| Generic load failure | `could not load layout` |
| Destructive confirmation | None in A4; preset switching and layout loading must not destroy panes |

No visible explanatory text should describe what the presets mean. The UI labels are the controls; behavior is learned through use and covered by docs later.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party registries | none | forbidden for A4 |
| icon packages | none | forbidden for A4 |

A4 must not add a package for icons, menus, popovers, command palettes, or layout math.

---

## Verification Requirements

The A4 planner must include visual/UI verification tasks for:

- The titlebar stays 22px high after the controlled switcher change.
- The switcher remains in the titlebar right cluster and does not overlap the project title at A1 minimum width.
- Active, inactive, hover, disabled, and `custom` states use only the token assignments in this UI-SPEC.
- `Cmd+G` updates both geometry and switcher state in the fixed order.
- Clicking each preset updates both geometry and switcher state.
- Manual geometry edits surface `custom` without changing PTY content.
- Save/load success and error copy exactly match this UI-SPEC.
- No L2 semantic labels, arrows, model/cost tags, or agent-role copy appears in A4.

Suggested focused checks:

- `pnpm --dir apps/voss-app test -- --run src`
- `pnpm --dir apps/voss-app build`
- Manual screenshot at the A1 minimum width after A4 implementation.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS - exact control/error copy is locked and minimal.
- [x] Dimension 2 Visuals: PASS - A4 extends Variant B without new decorative surfaces.
- [x] Dimension 3 Color: PASS - existing tokens only; accent use is semantic and bounded.
- [x] Dimension 4 Typography: PASS - A1/A3 typography scale reused unchanged.
- [x] Dimension 5 Spacing: PASS - A1/A3 spacing and structural constants reused; no new exceptions.
- [x] Dimension 6 Registry Safety: PASS - no shadcn, third-party registry, icon package, or component package.

**Approval:** approved 2026-05-19

