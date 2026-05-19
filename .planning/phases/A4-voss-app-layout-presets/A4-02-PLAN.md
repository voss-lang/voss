---
phase: A4-voss-app-layout-presets
plan: 02
type: execute
wave: 2
depends_on: [A4-01]
files_modified:
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/grid/keymap.ts
  - apps/voss-app/src/components/titlebar/Titlebar.tsx
  - apps/voss-app/src/components/titlebar/PresetSwitcher.tsx
  - apps/voss-app/src/grid/__tests__/keymap.test.ts
  - apps/voss-app/src/components/titlebar/__tests__/PresetSwitcher.test.tsx
autonomous: true
requirements: [LAY-02, LAY-03, LAY-04, LAY-08]
must_haves:
  truths:
    - "Titlebar switcher is controlled by grid layout state, not local visual-only state"
    - "Cmd+G cycles presets in fixed order and updates geometry plus switcher state"
    - "Manual grid edits surface custom state without adding semantic labels"
  artifacts:
    - path: "apps/voss-app/src/components/titlebar/PresetSwitcher.tsx"
      provides: "Controlled Variant B preset switcher"
      contains: "activeLayout"
    - path: "apps/voss-app/src/grid/keymap.ts"
      provides: "Cmd+G injected preset-cycle hook"
      contains: "KeyG"
---

<objective>
Wire the pure preset model into the running Solid UI: titlebar switcher, `Cmd+G`, active/custom state, and grid transform application.
</objective>

<context>
@.planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md
@.planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md
@apps/voss-app/src/App.tsx
@apps/voss-app/src/grid/GridRoot.tsx
@apps/voss-app/src/components/titlebar/PresetSwitcher.tsx
@apps/voss-app/src/components/titlebar/Titlebar.tsx
</context>

<threat_model>
T-A4-02 UI-state drift: switcher says one preset while grid has another. Mitigation: single owner for active layout state and controlled switcher props. T-A4-01 pane loss through UI actions. Mitigation: UI applies A4-01 pure transforms only.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Convert PresetSwitcher/Titlebar to controlled Variant B components</name>
  <files>apps/voss-app/src/components/titlebar/PresetSwitcher.tsx, apps/voss-app/src/components/titlebar/Titlebar.tsx, apps/voss-app/src/components/titlebar/__tests__/PresetSwitcher.test.tsx</files>
  <read_first>
    - apps/voss-app/src/components/titlebar/PresetSwitcher.tsx — current A1 visual-only local state to replace
    - apps/voss-app/src/components/titlebar/Titlebar.tsx — prop threading surface
    - .planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md — exact titlebar switcher states, copy, overflow, aria labels
  </read_first>
  <action>
    Refactor `PresetSwitcher` to accept `activeLayout`, `disabled`, and `onSelect` props using the A4-UI-SPEC contract. Remove its local `createSignal` active state. Render the optional non-clickable `custom` label only when `activeLayout === 'custom'`. Use exact lowercase labels `fanout`, `pipeline`, `swarm`, `watchers`, `custom`; active text uses `var(--fg-0)`, not raw `white`; no border radius. Update `Titlebar` to accept/pass `activeLayout`, `layoutDisabled`, and `onLayoutSelect` while preserving A1 window controls, drag regions, title text, and 22px height. Add component tests proving clicking each preset calls `onSelect`, `custom` is display-only/not focusable, `aria-pressed` appears only on active preset, disabled buttons do not fire, and raw copy matches UI-SPEC.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run PresetSwitcher --reporter=dot && pnpm exec tsc --noEmit -p . && grep -q 'activeLayout' src/components/titlebar/PresetSwitcher.tsx && ! grep -q \"color: active() === preset ? 'white'\" src/components/titlebar/PresetSwitcher.tsx && echo SWITCHER_OK</automated>
  </verify>
  <acceptance_criteria>
    - `PresetSwitcher` has no local active `createSignal`.
    - Tests prove controlled active, custom, disabled, and click states.
    - `Titlebar` still renders `WindowControls`, drag spacers, and `Voss ADE`.
    - `SWITCHER_OK` prints.
  </acceptance_criteria>
  <done>The titlebar switcher is controlled and matches A4-UI-SPEC.</done>
</task>

<task type="tdd">
  <name>Task 2: Add Cmd+G and grid preset application without keymap state drift</name>
  <files>apps/voss-app/src/App.tsx, apps/voss-app/src/grid/GridRoot.tsx, apps/voss-app/src/grid/keymap.ts, apps/voss-app/src/grid/__tests__/keymap.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/keymap.ts — existing injected `onCloseRequest` pattern
    - apps/voss-app/src/grid/GridRoot.tsx — grid owner and keyboard host
    - apps/voss-app/src/App.tsx — app/titlebar composition point
    - apps/voss-app/src/grid/layoutPresets.ts — A4-01 transform API
    - .planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md — recommended app-level ownership pattern
  </read_first>
  <action>
    Extend `dispatchKey()` with an injected `onCycleLayout(store)` callback for `Cmd+G` (`code === 'KeyG'`, unshifted, no alt) and consume the event like other matched chords. Do not import `layoutPresets.ts` into `keymap.ts`. Update `GridRoot` to accept `activeLayout`, `onActiveLayoutChange`, and `onApplyPreset` or equivalent props, applying `nextPreset()`/`applyPreset()` inside `setStore(produce(...))` so `Cmd+G` and titlebar clicks transform the same store. Move active layout ownership to `App.tsx`: initialize to `custom` or the default chosen by existing app state, render `Titlebar activeLayout=... onLayoutSelect=...`, and render `GridRoot` with the matching callbacks. Mark active layout as `custom` after A3 manual structural edits (`splitFocused`, `forkFocused`, close, resize, equalize) by calling the app-provided change hook from `GridRoot` when `dispatchKey()` handles non-layout structural commands. Add tests proving `Cmd+G` cycle order, titlebar click application, and manual edit -> `custom`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/keymap.test.ts PresetSwitcher --reporter=dot && pnpm exec tsc --noEmit -p . && grep -q 'KeyG' src/grid/keymap.ts && grep -q 'nextPreset' src/grid/GridRoot.tsx && grep -q 'activeLayout' src/App.tsx && echo LAYOUT_ROUTING_OK</automated>
  </verify>
  <acceptance_criteria>
    - `Cmd+G` from custom applies fanout, then pipeline, swarm, watchers, and fanout in order.
    - Titlebar click and `Cmd+G` share the same preset-application path.
    - Manual split/fork/close/resize/equalize marks `activeLayout` as `custom`.
    - Existing unmatched key behavior still returns false without `preventDefault`.
    - `LAYOUT_ROUTING_OK` prints.
  </acceptance_criteria>
  <done>Preset state and geometry are wired through the titlebar and keyboard without drift.</done>
</task>
</tasks>

<verification>
Run focused switcher/keymap tests, then `pnpm --dir apps/voss-app test -- --run src` and `pnpm --dir apps/voss-app build` after this wave.
</verification>

<success_criteria>
- Titlebar switcher is controlled and token-compliant.
- `Cmd+G` cycles the fixed order and transforms panes.
- Manual grid edits expose `custom` state.
</success_criteria>

