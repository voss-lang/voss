---
phase: A9
plan: "02"
title: "Frontend form controls — pure Solid components"
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src/settings/controls/Toggle.tsx
  - apps/voss-app/src/settings/controls/Dropdown.tsx
  - apps/voss-app/src/settings/controls/NumberStepper.tsx
  - apps/voss-app/src/settings/controls/Slider.tsx
  - apps/voss-app/src/settings/controls/RadioGroup.tsx
  - apps/voss-app/src/settings/WorkspaceBadge.tsx
  - apps/voss-app/src/settings/SettingRow.tsx
  - apps/voss-app/src/settings/settings.css
autonomous: true
requirements: []
must_haves:
  truths:
    - "Toggle: 36×20 pill, accent-green ON, bg-2 OFF, 150ms transition, prefers-reduced-motion disabled"
    - "Dropdown: 32px height, bg-1 unfocused, bg-2 focused, chevron ▾, popup bg-3 max-height 200px"
    - "NumberStepper: 80px input + 24px ± buttons, center-aligned mono value"
    - "Slider: 4px track bg-3, accent-blue fill, 16px thumb, value label right"
    - "RadioGroup: horizontal layout, 14px circles, accent-blue selected dot"
    - "WorkspaceBadge: inline badge + tooltip + reset-to-default link (D-05)"
    - "SettingRow: label+description left, control right, optional WorkspaceBadge"
    - "All controls use Variant B tokens only — no inline hex"
---

# A9-02: Frontend Form Controls

## Objective

Build the reusable form control components for the settings UI. These are pure Solid components with no Tauri dependency — they receive values and onChange callbacks as props. The settings panel (A9-03) composes them.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Inaccessible controls | All controls have keyboard support (Tab/Space/Enter), focus ring via --focus, aria attributes |
| Animation for reduced-motion users | All transitions respect `prefers-reduced-motion: reduce` via CSS media query |

## Tasks

### Task 1: Toggle + Dropdown + NumberStepper components

<read_first>
- apps/voss-app/src/styles/variant-b.css (token values for all styling)
- apps/voss-app/src/pane/pane.css (pattern for component-scoped CSS in the project)
- .planning/phases/A9-voss-app-settings-theme/A9-UI-SPEC.md § Form Controls (exact dimensions and colors)
</read_first>

<action>
1. Create `apps/voss-app/src/settings/settings.css` with:
   - `.settings-toggle` — 36×20 pill, `border-radius: 10px`, OFF=`var(--bg-2)`, transition `transform 150ms ease`
   - `.settings-toggle.on` — `background: var(--accent-green)`
   - `.settings-toggle .thumb` — 16px circle, `var(--fg-0)`, translate on state
   - `.settings-dropdown` — 32px height, `var(--bg-1)`, `1px solid var(--border)`
   - `.settings-dropdown.open` — `var(--bg-2)`, `var(--border-bright)`
   - `.settings-dropdown-popup` — `var(--bg-3)`, `var(--border)`, `max-height: 200px`, `overflow-y: auto`
   - `.settings-dropdown-option:hover` — `var(--bg-2)`
   - `.settings-stepper` — input 80px + buttons 24px each
   - `@media (prefers-reduced-motion: reduce)` — `transition: none !important` on all `.settings-*`

2. Create `apps/voss-app/src/settings/controls/Toggle.tsx`:
   - Props: `value: boolean`, `onChange: (v: boolean) => void`, `disabled?: boolean`
   - Renders pill track + circle thumb
   - Click toggles, Space/Enter toggles, Tab focuses
   - `role="switch"`, `aria-checked={value}`

3. Create `apps/voss-app/src/settings/controls/Dropdown.tsx`:
   - Props: `value: string`, `options: {label: string, value: string}[]`, `onChange: (v: string) => void`
   - Click opens popup, Esc/click-outside closes
   - Selected option shown in closed state with ▾ chevron
   - Keyboard: ArrowUp/Down navigates, Enter selects
   - `role="listbox"` on popup, `role="option"` on items

4. Create `apps/voss-app/src/settings/controls/NumberStepper.tsx`:
   - Props: `value: number`, `min: number`, `max: number`, `step: number`, `onChange: (v: number) => void`
   - Input: center-aligned, `--font-mono`, editable
   - − and + buttons: `var(--bg-2)`, hover `var(--bg-3)`
   - Clamp to min/max on blur and button click
</action>

<acceptance_criteria>
- `npx tsc --noEmit` exits 0
- `grep -r 'var(--' apps/voss-app/src/settings/` finds only CSS var references (no raw hex)
- `grep 'prefers-reduced-motion' apps/voss-app/src/settings/settings.css` finds at least 1 media query
- Toggle.tsx exports a component with `role="switch"` and `aria-checked`
- Dropdown.tsx exports a component with `role="listbox"`
- NumberStepper.tsx clamps value between min and max
</acceptance_criteria>

### Task 2: Slider + RadioGroup + WorkspaceBadge + SettingRow

<read_first>
- apps/voss-app/src/settings/controls/Toggle.tsx (just created — pattern reference)
- apps/voss-app/src/settings/settings.css (just created — extend with new control styles)
- .planning/phases/A9-voss-app-settings-theme/A9-UI-SPEC.md § Form Controls + § Workspace Override Badge Colors
- .planning/phases/A9-voss-app-settings-theme/A9-CONTEXT.md D-05 (workspace badge UX)
</read_first>

<action>
1. Create `apps/voss-app/src/settings/controls/Slider.tsx`:
   - Props: `value: number`, `min: number`, `max: number`, `step: number`, `onChange: (v: number) => void`, `label?: string`
   - Track: 4px height, `var(--bg-3)`, full width
   - Fill (left of thumb): `var(--accent-blue)`
   - Thumb: 16px circle, `var(--fg-0)`, subtle shadow
   - Value label: right of slider, `--font-mono` 12px `--fg-1`
   - `<input type="range">` for accessibility; styled via CSS

2. Create `apps/voss-app/src/settings/controls/RadioGroup.tsx`:
   - Props: `value: string`, `options: {label: string, value: string}[]`, `onChange: (v: string) => void`
   - Horizontal layout, `md` (16px) gap
   - Circle: 14px, 1px `--border`, unselected `--bg-1`
   - Selected: 8px `--accent-blue` dot inside
   - Label: 12px `--font-ui` `--fg-1`
   - `role="radiogroup"`, `role="radio"` per option

3. Create `apps/voss-app/src/settings/WorkspaceBadge.tsx`:
   - Props: `userValue: string`, `onReset: () => void`
   - Badge: "workspace" text, `--accent-blue` color, `rgba(90,124,255,0.15)` bg, 10px font, xs padding
   - Tooltip on hover: "User default: {userValue}"
   - "Reset to default" link: `--fg-2`, 11px, underline on hover
   - Click reset calls `onReset`

4. Create `apps/voss-app/src/settings/SettingRow.tsx`:
   - Props: `label: string`, `description?: string`, `workspaceOverride?: {userValue: string, onReset: () => void}`, `children: JSX.Element` (the control)
   - Horizontal flex: label+description left, control right
   - Label: 13px `--font-ui` weight 500 `--fg-0`
   - Description: 12px `--font-ui` weight 400 `--fg-2`
   - If `workspaceOverride` set: renders `<WorkspaceBadge>` below control

5. Add CSS for all new components to `settings.css`.
</action>

<acceptance_criteria>
- `npx tsc --noEmit` exits 0
- Slider.tsx renders an `<input type="range">` for accessibility
- RadioGroup.tsx has `role="radiogroup"` and each option has `role="radio"`
- WorkspaceBadge.tsx renders "workspace" text + "Reset to default" link
- SettingRow.tsx accepts `children` prop (the control element)
- `grep -r '#[0-9a-fA-F]' apps/voss-app/src/settings/controls/` returns 0 matches (no raw hex in TSX — only in CSS rgba for badge bg)
</acceptance_criteria>

### Task 3: Vitest tests for form controls

<read_first>
- apps/voss-app/src/settings/controls/Toggle.tsx (test target)
- apps/voss-app/src/settings/controls/Dropdown.tsx (test target)
- apps/voss-app/src/settings/SettingRow.tsx (test target)
- apps/voss-app/src/grid/__tests__/keymap.test.ts (existing test pattern in voss-app)
</read_first>

<action>
Create `apps/voss-app/src/settings/__tests__/controls.test.ts`:

1. Toggle: renders, click toggles value, Space toggles, has role="switch", has aria-checked
2. Dropdown: renders closed with value, click opens popup, select option calls onChange, Esc closes
3. NumberStepper: renders with value, + increments, − decrements, clamps to min/max
4. SettingRow: renders label + description + child control, renders WorkspaceBadge when override present
5. WorkspaceBadge: renders "workspace" text, click reset calls onReset
</action>

<acceptance_criteria>
- `npx vitest run src/settings` exits 0 with all tests passing
- Test count >= 10 (covering Toggle, Dropdown, NumberStepper, SettingRow, WorkspaceBadge)
- No test imports from Tauri (controls are pure Solid components)
</acceptance_criteria>
