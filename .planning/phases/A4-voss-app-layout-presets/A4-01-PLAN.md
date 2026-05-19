---
phase: A4-voss-app-layout-presets
plan: 01
type: execute
wave: 1
depends_on: [A4-00]
files_modified:
  - apps/voss-app/src/grid/layoutPresets.ts
  - apps/voss-app/src/grid/__tests__/layoutPresets.test.ts
autonomous: true
requirements: [LAY-01, LAY-03, LAY-04, LAY-05, LAY-08]
must_haves:
  truths:
    - "Preset transforms are pure visual tree rewrites over existing PaneLeaf objects"
    - "Preset switching preserves all existing pane ids, cwd, shell, and focused pane id"
    - "Binary split ratios are count-weighted so pipeline/swarm rows look equal"
  artifacts:
    - path: "apps/voss-app/src/grid/layoutPresets.ts"
      provides: "LayoutPreset/ActiveLayout types, nextPreset, applyPreset, no-destroy transforms"
      contains: "export type LayoutPreset"
    - path: "apps/voss-app/src/grid/__tests__/layoutPresets.test.ts"
      provides: "Preset model regression suite"
      contains: "preserves pane ids"
---

<objective>
Create the pure preset geometry layer for `fanout`, `pipeline`, `swarm`, and `watchers`, with deterministic index-order mapping and no pane destruction.
</objective>

<context>
@.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md
@.planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md
@.planning/phases/A4-voss-app-layout-presets/A4-PATTERNS.md
@apps/voss-app/src/grid/tree.ts
@apps/voss-app/src/grid/operations.ts
</context>

<threat_model>
T-A4-01 Pane destruction or process loss through layout transforms. Mitigation: reuse existing `PaneLeaf` objects, compare id sets before/after every preset, and preserve `focusedId`. T-A4-02 semantic leakage. Mitigation: no agent/worktree/role labels or behavior in the preset model.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add pure preset transform API with red tests</name>
  <files>apps/voss-app/src/grid/layoutPresets.ts, apps/voss-app/src/grid/__tests__/layoutPresets.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/tree.ts — source types and `collectLeaves()`/`recomputeIndices()` contracts
    - apps/voss-app/src/grid/operations.ts — existing no-destroy mutation pattern
    - .planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md — D-01..D-06 mapping/cycle decisions
    - .planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md — count-weighted binary tree construction guidance
  </read_first>
  <action>
    Create `apps/voss-app/src/grid/layoutPresets.ts` exporting `LayoutPreset = 'fanout' | 'pipeline' | 'swarm' | 'watchers'`, `ActiveLayout = LayoutPreset | 'custom'`, `LAYOUT_PRESETS`, `nextPreset(active: ActiveLayout): LayoutPreset`, and `applyPreset(root: TreeNode, preset: LayoutPreset): TreeNode`. Implement helper functions that collect panes in stable index order, build binary split rows/columns with count-weighted ratios, call `recomputeIndices()` on the returned tree, and never create filler panes. Create `layoutPresets.test.ts` with tests for 1, 2, 3, 4, 6, 9, 16, and 17 panes proving id-set preservation, focus-independent construction, correct `nextPreset()` order (`custom -> fanout -> pipeline -> swarm -> watchers -> fanout`), and no semantic strings beyond preset labels.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/layoutPresets.test.ts --reporter=dot && pnpm exec tsc --noEmit -p . && grep -q 'export type LayoutPreset' src/grid/layoutPresets.ts && grep -q 'nextPreset' src/grid/layoutPresets.ts && grep -q 'preserves pane ids' src/grid/__tests__/layoutPresets.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - `layoutPresets.ts` exports the exact `LayoutPreset` and `ActiveLayout` unions.
    - `nextPreset('custom') === 'fanout'` and the full fixed cycle is covered by tests.
    - Applying every preset to 1/2/3/4/6/9/16/17 pane fixtures preserves the exact set of pane ids.
    - Under-capacity presets do not spawn filler panes.
    - `pnpm vitest run src/grid/__tests__/layoutPresets.test.ts` and `pnpm exec tsc --noEmit -p .` exit 0.
  </acceptance_criteria>
  <done>Pure preset transform API exists and passes no-destroy/cycle tests.</done>
</task>

<task type="tdd">
  <name>Task 2: Lock preset-specific silhouettes and overflow spill behavior</name>
  <files>apps/voss-app/src/grid/layoutPresets.ts, apps/voss-app/src/grid/__tests__/layoutPresets.test.ts</files>
  <read_first>
    - apps/voss-app/src/grid/layoutPresets.ts — implementation from Task 1
    - apps/voss-app/src/grid/geometry.ts — compute rects to validate visual arrangement
    - .planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md — D-03/D-04 capacity rules
  </read_first>
  <action>
    Extend the test suite to validate preset silhouettes using `computePaneRects()` against a stable 1200x800 fixture: `fanout` keeps pane index 1 in the left primary slot and all remaining panes in a right column; `pipeline` produces a single left-to-right row; `swarm` produces near-square rows/columns up to 4x4 and for 17 panes spills the extra pane by splitting the last region; `watchers` keeps pane 1 in the top main region and places watcher panes along the bottom. Adjust `layoutPresets.ts` helpers so count-weighted ratios satisfy these tests. Do not import Solid, DOM, Tauri, or `invoke()` in `layoutPresets.ts`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/layoutPresets.test.ts --reporter=dot && ! grep -nE \"solid-js|@tauri|document|window|invoke\" src/grid/layoutPresets.ts && echo PRESET_MODEL_OK</automated>
  </verify>
  <acceptance_criteria>
    - Geometry tests prove `fanout`, `pipeline`, `swarm`, and `watchers` match A4-CONTEXT D-01..D-04.
    - 17-pane swarm preserves all 17 ids and spills through the last region rather than dropping a pane.
    - `layoutPresets.ts` has no Solid/DOM/Tauri imports.
    - `PRESET_MODEL_OK` prints.
  </acceptance_criteria>
  <done>Preset silhouettes and overflow rules are source-verified.</done>
</task>
</tasks>

<verification>
Run `pnpm --dir apps/voss-app test -- --run src/grid/__tests__/layoutPresets.test.ts` and `pnpm --dir apps/voss-app exec tsc --noEmit -p apps/voss-app` equivalent from the app directory.
</verification>

<success_criteria>
- All four presets exist as pure visual transforms.
- Pane ids and focus target are preserved by design.
- No L2 semantics or runtime I/O enters the preset model.
</success_criteria>

