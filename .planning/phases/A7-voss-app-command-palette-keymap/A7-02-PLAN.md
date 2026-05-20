---
phase: A7-voss-app-command-palette-keymap
plan: 02
type: execute
wave: 2
depends_on: [A7-01]
files_modified:
  - apps/voss-app/src/command-palette/CommandPalette.tsx
  - apps/voss-app/src/command-palette/quickOpen.ts
  - apps/voss-app/src/command-palette/__tests__/CommandPalette.test.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/__tests__/App.test.tsx
  - apps/voss-app/src/grid/GridRoot.tsx
autonomous: true
requirements: [CMD-01, CMD-02, CMD-03, CMD-04, CMD-07]
must_haves:
  truths:
    - "D-03: App.tsx builds one AppContext and threads it into registry handlers"
    - "D-05: Cmd+P quick-open lists saved layouts and recent projects only"
    - "D-06: one CommandPalette component handles quick and full modes"
    - "D-08: palette captures focus and keystrokes while open, then restores pane focus on dismiss"
    - "D-09: rows display right-aligned chord hints sourced from registry metadata"
  artifacts:
    - path: "apps/voss-app/src/command-palette/CommandPalette.tsx"
      provides: "Centered Variant B quick/full command palette"
      contains: "Open layout or recent project"
---

<objective>
Wire the registry into the app and render the Variant B command palette for Cmd+P quick-open and Cmd+Shift+P all-commands.
</objective>

<context>
@.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-PATTERNS.md
@apps/voss-app/src/App.tsx
@apps/voss-app/src/grid/GridRoot.tsx
@apps/voss-app/src/grid/layoutStorage.ts
@apps/voss-app/src/project/projectStorage.ts
</context>

<threat_model>
T-A7-03 Palette steals or leaks terminal input. Mitigation: palette-open state gates keyboard dispatch and tests assert pane dispatch is not called while the palette owns focus.
T-A7-04 Quick-open scope creep. Mitigation: quick rows are saved layouts and recent projects only; file-open rows are forbidden in tests.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add CommandPalette quick/full component</name>
  <files>apps/voss-app/src/command-palette/CommandPalette.tsx, apps/voss-app/src/command-palette/quickOpen.ts, apps/voss-app/src/command-palette/__tests__/CommandPalette.test.tsx</files>
  <read_first>
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - overlay, rows, copy, accessibility
    - apps/voss-app/src/grid/DotMenu.tsx - overlay/menu listener pattern
    - apps/voss-app/src/components/setup/SetupWindow.tsx - project-open copy precedent
    - apps/voss-app/src/grid/layoutStorage.ts - layout list/load wrappers
  </read_first>
  <behavior>
    - Test 1: quick mode input placeholder is `Open layout or recent project`.
    - Test 2: full mode input placeholder is `Run command`.
    - Test 3: empty quick mode renders `No layouts or recent projects` and the specified body copy.
    - Test 4: rows expose chord hints from registry metadata.
    - Test 5: Esc and outside click call dismiss.
  </behavior>
  <action>
    Implement one Solid `CommandPalette` component with `mode`, `open`, `commands`, `quickItems`, `onExecute`, and `onDismiss` props. Implement `quickOpen.ts` helpers that turn saved layout names and recent project paths into palette rows with `Layouts` and `Recent Projects` sections. Use A7-UI-SPEC dimensions: centered fixed overlay, 48px input, 32px rows, no radius, token-only colors, and no file-search placeholder. Add ARIA roles and deterministic labels per UI-SPEC.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/CommandPalette.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - One component renders both modes.
    - Quick mode contains layouts and recents only.
    - Full mode displays registry command labels and chord hints.
    - Empty and error copy matches A7-UI-SPEC.
    - Component tests pass.
  </acceptance_criteria>
  <done>Command palette UI exists and matches A7-UI-SPEC.</done>
</task>

<task type="execute" tdd="true">
  <name>Task 2: Build AppContext and route global keyboard through registry</name>
  <files>apps/voss-app/src/App.tsx, apps/voss-app/src/grid/GridRoot.tsx, apps/voss-app/src/__tests__/App.test.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx - current A4/A5 state and callable seams
    - apps/voss-app/src/grid/GridRoot.tsx - current keydown owner
    - apps/voss-app/src/command-palette/registry.ts - command registry from A7-01
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md - D-02/D-03/D-08
  </read_first>
  <behavior>
    - Test 1: Cmd+P opens quick palette.
    - Test 2: Cmd+Shift+P opens full palette.
    - Test 3: while palette is open, Cmd+D does not split a pane.
    - Test 4: dismissing the palette restores the grid/pane focus path.
    - Test 5: selecting a recent project row calls existing `openProject` flow.
  </behavior>
  <action>
    In `App.tsx`, construct a single `AppContext` containing project state accessors, recents refresh, active layout accessors, grid controller methods, `saveCurrentLayout`, `loadLayoutByName`, `applyDefaultLayout`, palette open/close methods, and toast methods introduced later as no-op placeholders if necessary. Move global Cmd+P/Cmd+Shift+P handling to the registry path. Adjust `GridRoot` so grid-specific commands can be invoked through registry/AppContext instead of importing the old `dispatchKey` switch directly. Preserve current `produce` boundaries for layout cycling and structural edits.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/__tests__/App.test.tsx src/command-palette src/grid && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - `App.tsx` owns one AppContext object.
    - Cmd+P and Cmd+Shift+P open correct palette modes.
    - Palette-open keys do not reach grid/PTX dispatch.
    - Existing A3/A4 keyboard behavior remains covered by tests.
    - TypeScript build passes.
  </acceptance_criteria>
  <done>Palette and registry dispatch are wired into the app shell.</done>
</task>
</tasks>

<verification>
Run focused App/palette/grid Vitest plus `pnpm --dir apps/voss-app build`.
</verification>

<success_criteria>
- Cmd+P and Cmd+Shift+P are usable command surfaces.
- Quick-open applies layout/recent-project actions through existing A4/A5 seams.
- Palette input owns keyboard focus while open.
</success_criteria>

