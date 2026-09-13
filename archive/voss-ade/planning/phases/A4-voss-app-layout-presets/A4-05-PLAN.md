---
phase: A4-voss-app-layout-presets
plan: 05
type: execute
wave: 4
depends_on: [A4-04]
files_modified:
  - apps/voss-app/src/grid/__tests__/a4-acceptance.test.tsx
  - apps/voss-app/e2e/layout-presets.spec.ts
  - .planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md
autonomous: false
requirements: [LAY-01, LAY-02, LAY-03, LAY-04, LAY-05, LAY-06, LAY-07, LAY-08]
must_haves:
  truths:
    - "All A4 LAY requirements have automated coverage or an explicit manual verification step"
    - "Full app build and voss-app-core layout tests pass"
    - "Manual visual verification confirms Variant B titlebar density and no L2 semantics"
  artifacts:
    - path: "apps/voss-app/src/grid/__tests__/a4-acceptance.test.tsx"
      provides: "A4 requirement-level acceptance suite"
      contains: "LAY-01"
    - path: "apps/voss-app/e2e/layout-presets.spec.ts"
      provides: "Runtime smoke for preset cycle and save/load"
      contains: "Cmd+G"
---

<objective>
Close A4 with requirement-level acceptance tests, e2e smoke, full verification commands, and a human visual check for the titlebar switcher and save/load workflow.
</objective>

<context>
@.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md
@.planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md
@.planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md
</context>

<threat_model>
T-A4-05 Incomplete acceptance: unit tests pass but user-facing workflow is broken. Mitigation: focused acceptance suite, e2e smoke, build, Rust tests, and manual visual verification. T-A4-02 semantic leakage: final grep/screenshot check for forbidden L2 labels.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add A4 requirement-level acceptance tests</name>
  <files>apps/voss-app/src/grid/__tests__/a4-acceptance.test.tsx, .planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md</files>
  <read_first>
    - .planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md — task-to-requirement map
    - .planning/ROADMAP.md Phase A4 — LAY-01..LAY-08
    - apps/voss-app/src/grid/__tests__/layoutPresets.test.ts — model coverage
    - apps/voss-app/src/grid/__tests__/layoutCommands.test.ts — persistence coverage
  </read_first>
  <action>
    Add `a4-acceptance.test.tsx` that groups assertions by LAY-01 through LAY-08: four presets exist and render/apply; switcher controlled state and `custom` copy; `Cmd+G` fixed cycle; no existing ids destroyed on preset switch; capacity mismatch behavior; save/load callable stubs and exact copy; versioned `.voss/layouts/<name>.json` schema; no L2 semantic strings. Update `A4-VALIDATION.md` statuses from pending to green for rows whose automated tests now exist.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/a4-acceptance.test.tsx --reporter=dot && grep -q 'LAY-01' src/grid/__tests__/a4-acceptance.test.tsx && grep -q 'LAY-08' src/grid/__tests__/a4-acceptance.test.tsx && echo A4_ACCEPTANCE_OK</automated>
  </verify>
  <acceptance_criteria>
    - The acceptance test file contains explicit LAY-01..LAY-08 sections.
    - No L2 semantic strings (`agent`, `worktree`, `reviewer`, `model`, `cost`) are introduced by A4 preset UI.
    - `A4_ACCEPTANCE_OK` prints.
  </acceptance_criteria>
  <done>A4 has requirement-level automated acceptance coverage.</done>
</task>

<task type="auto">
  <name>Task 2: Add e2e preset cycle and save/load smoke</name>
  <files>apps/voss-app/e2e/layout-presets.spec.ts</files>
  <read_first>
    - apps/voss-app/e2e/grid-integration.spec.ts — A3 launch/selectors convention
    - apps/voss-app/src/grid/layoutCommands.ts — save/load callable seam
    - .planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md — visible copy and visual-state requirements
  </read_first>
  <action>
    Add `layout-presets.spec.ts` using the existing voss-app Playwright convention. Cover: create four panes, press `Cmd+G` four times and assert the active switcher label/geometry changes through fanout, pipeline, swarm, watchers; manually resize/split and assert `custom` appears; save a named layout, modify geometry, load it, and assert geometry/focus restored with panes preserved; create `.voss/layouts/default.json` fixture and assert startup/default-load applies it when the project path is supplied by the test harness. If the local Playwright/Tauri harness cannot run on macOS, mark the test with the same explicit skip/deferred pattern used by existing app e2e files and keep unit acceptance as the automated gate.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && test -f e2e/layout-presets.spec.ts && grep -q 'Cmd+G' e2e/layout-presets.spec.ts && grep -q 'default.json' e2e/layout-presets.spec.ts && (pnpm playwright test layout-presets 2>&1 | tail -20 || echo 'A4_E2E_DEFERRED_SEE_OUTPUT') && echo A4_E2E_SPEC_OK</automated>
  </verify>
  <acceptance_criteria>
    - `layout-presets.spec.ts` contains preset-cycle, custom-state, save/load, and default-layout scenarios.
    - If e2e cannot run locally, the skip reason references the existing Tauri/macOS harness limitation and unit acceptance remains green.
    - `A4_E2E_SPEC_OK` prints.
  </acceptance_criteria>
  <done>A4 e2e smoke exists and either runs or is explicitly deferred with reason.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Full verification and visual sign-off</name>
  <files>none</files>
  <read_first>
    - .planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md — visual/copy contract
    - .planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md — final command list
  </read_first>
  <action>
    Run the full command set: `pnpm --dir apps/voss-app test`, `pnpm --dir apps/voss-app build`, and `cargo test -p voss-app-core`. Then run the app on the dev machine and visually verify the titlebar remains 22px high, all four preset labels are visible, active/custom states match A4-UI-SPEC, `Cmd+G` and clicks update both geometry and switcher state, save/load copy matches the spec, and no L2 agent/model/cost/worktree semantics appear. Record pass/fail in the A4 execution summary.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core && echo A4_FULL_GREEN</automated>
  </verify>
  <acceptance_criteria>
    - Full Vitest suite exits 0.
    - `pnpm --dir apps/voss-app build` exits 0.
    - `cargo test -p voss-app-core` exits 0.
    - Human visual verification confirms the A4-UI-SPEC switcher, custom state, and save/load copy.
    - `A4_FULL_GREEN` prints before phase verification.
  </acceptance_criteria>
  <done>A4 is fully verified and ready for `/gsd:verify-work A4`.</done>
</task>
</tasks>

<verification>
Run `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core`.
</verification>

<success_criteria>
- LAY-01 through LAY-08 have acceptance coverage.
- Full app build/test and Rust tests are green.
- Manual visual verification confirms the switcher and save/load UX.
</success_criteria>

