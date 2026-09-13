---
phase: A4-voss-app-layout-presets
plan: 04
type: execute
wave: 3
depends_on: [A4-01, A4-02, A4-03]
files_modified:
  - apps/voss-app/src/grid/layoutStorage.ts
  - apps/voss-app/src/grid/layoutCommands.ts
  - apps/voss-app/src/grid/__tests__/layoutStorage.test.ts
  - apps/voss-app/src/grid/__tests__/layoutCommands.test.ts
  - apps/voss-app/src/App.tsx
autonomous: true
requirements: [LAY-04, LAY-05, LAY-06, LAY-07, LAY-08]
must_haves:
  truths:
    - "Frontend save/load invokes Rust I/O and remaps existing panes without killing them"
    - "Bigger saved layouts spawn only net-new panes with saved cwd/shell"
    - "Smaller saved layouts preserve extras through overflow/spill"
  artifacts:
    - path: "apps/voss-app/src/grid/layoutStorage.ts"
      provides: "Thin invoke wrappers for layout persistence"
      contains: "save_layout"
    - path: "apps/voss-app/src/grid/layoutCommands.ts"
      provides: "Frontend save/load remap behavior and exact copy"
      contains: "layout saved"
---

<objective>
Wire layout save/load behavior into the frontend while preserving existing panes and respecting A7's command-palette boundary.
</objective>

<context>
@.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md
@.planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md
@.planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md
@apps/voss-app/src/grid/layoutPresets.ts
@apps/voss-app/src/grid/tree.ts
</context>

<threat_model>
T-A4-01 Pane loss on load. Mitigation: remap existing leaves by stable index order, spawn only missing slots, never remove extra existing leaves. T-A4-04 Bad layout file crash. Mitigation: treat Rust load errors as non-fatal UI messages.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add invoke wrappers and exact copy mapping</name>
  <files>apps/voss-app/src/grid/layoutStorage.ts, apps/voss-app/src/grid/__tests__/layoutStorage.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/sync.ts — existing thin invoke wrapper pattern
    - .planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md — exact save/load copy
    - apps/voss-app/src-tauri/src/lib.rs — command names registered in A4-03
  </read_first>
  <action>
    Create `layoutStorage.ts` with typed `saveLayout`, `loadLayout`, `listLayouts`, and `loadDefaultLayout` wrappers around `invoke()` using the A4-03 command names. Define exported copy constants matching A4-UI-SPEC exactly: `Save layout as...`, `Load layout...`, `layout saved`, `layout loaded`, `no saved layouts`, `layout not found`, `layout ignored: invalid file`, `layout ignored: unsupported version`, `could not save layout`, `could not load layout`, and `layout name cannot contain /, \\ or ..`. Add tests with mocked `invoke()` proving wrapper command names/payloads and exact copy.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/layoutStorage.test.ts --reporter=dot && pnpm exec tsc --noEmit -p . && grep -q 'layout ignored: invalid file' src/grid/layoutStorage.ts && echo LAYOUT_STORAGE_OK</automated>
  </verify>
  <acceptance_criteria>
    - Wrapper tests prove command names and payload shapes.
    - Copy constants exactly match A4-UI-SPEC.
    - `LAYOUT_STORAGE_OK` prints.
  </acceptance_criteria>
  <done>Frontend storage bridge and copy constants exist.</done>
</task>

<task type="tdd">
  <name>Task 2: Implement save/load remapping without pane destruction</name>
  <files>apps/voss-app/src/grid/layoutCommands.ts, apps/voss-app/src/grid/__tests__/layoutCommands.test.ts, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/layoutPresets.ts — preset/spill helpers from A4-01
    - apps/voss-app/src/grid/tree.ts — `collectLeaves`, `makePane`, `recomputeIndices`
    - apps/voss-app/src/grid/layoutStorage.ts — wrappers and copy constants from Task 1
    - .planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md — D-07/D-08 save/load semantics
  </read_first>
  <action>
    Create `layoutCommands.ts` with pure helpers for serializing the current grid layout and applying a loaded layout to the current store. Save serializes root, focusedId, activePreset, cwd, and shell only; it does not serialize scrollback, PTY session ids, process state, or env mutations. Load remaps existing leaves onto saved geometry by stable index order: if the saved layout has more slots than currently open, create net-new panes using saved cwd/shell for those slots; if the saved layout has fewer slots, preserve extra current panes by spilling them through the last saved region using A4-01 overflow logic. Existing pane ids must remain in the tree after load. Add tests for equal-count, bigger-saved, smaller-saved, corrupt-load error mapping, and default layout application. Wire `App.tsx` or the layout-state owner to expose callable save/load/default-load functions for A7 later, without adding a full palette UI.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/layoutCommands.test.ts --reporter=dot && pnpm exec tsc --noEmit -p . && grep -q 'serialize' src/grid/layoutCommands.ts && grep -q 'applyLoadedLayout' src/grid/layoutCommands.ts && echo LAYOUT_COMMANDS_OK</automated>
  </verify>
  <acceptance_criteria>
    - Equal-count load preserves all existing pane ids and restores geometry.
    - Bigger saved layout spawns only missing panes using saved cwd/shell.
    - Smaller saved layout preserves extras by spilling, never dropping existing ids.
    - Save output contains no scrollback/process/session-id fields.
    - A callable save/load/default-load seam exists for A7 without implementing the full command palette.
    - `LAYOUT_COMMANDS_OK` prints.
  </acceptance_criteria>
  <done>Frontend layout save/load behavior is wired and no-destroy tested.</done>
</task>
</tasks>

<verification>
Run focused layout storage/command tests, then `pnpm --dir apps/voss-app test -- --run src/grid`.
</verification>

<success_criteria>
- Save/load uses Rust I/O wrappers.
- Loaded layouts remap existing panes without killing them.
- Copy and command-stub behavior match A4-UI-SPEC.
</success_criteria>

