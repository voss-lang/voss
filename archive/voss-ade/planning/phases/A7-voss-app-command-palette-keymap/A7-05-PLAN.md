---
phase: A7-voss-app-command-palette-keymap
plan: 05
type: execute
wave: 4
depends_on: [A7-02, A7-03, A7-04]
files_modified:
  - apps/voss-app/src/command-palette/nativeMenu.ts
  - apps/voss-app/src/command-palette/__tests__/nativeMenu.test.ts
  - apps/voss-app/e2e/command-palette.spec.ts
  - .planning/phases/A7-voss-app-command-palette-keymap/A7-PHASE-SUMMARY.md
autonomous: true
requirements: [CMD-01, CMD-02, CMD-03, CMD-04, CMD-05, CMD-06, CMD-07]
must_haves:
  truths:
    - "D-04: native OS menus wrap the same command registry"
    - "CMD-01/CMD-02: quick-open and full palette are both exercised"
    - "CMD-03: all Window, Pane, Layout, Project, Settings, Help categories are discoverable"
    - "CMD-04: recent commands affect fuzzy ranking"
    - "CMD-05/CMD-06: custom keymap override and validation feedback are covered"
    - "CMD-07: palette/toast/prefix UI follows approved Variant B UI-SPEC"
  artifacts:
    - path: "apps/voss-app/src/command-palette/nativeMenu.ts"
      provides: "native menu generation from registry metadata"
      contains: "setAsAppMenu"
---

<objective>
Generate native menus from the command registry and close the A7 acceptance surface with automated/source/manual verification.
</objective>

<context>
@.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-RESEARCH.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-VALIDATION.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md
@apps/voss-app/src/command-palette/registry.ts
@apps/voss-app/src/App.tsx
</context>

<threat_model>
T-A7-08 Native menu command drift. Mitigation: native menu builder consumes registry metadata and tests fail if labels/categories diverge.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add native menu generation from registry metadata</name>
  <files>apps/voss-app/src/command-palette/nativeMenu.ts, apps/voss-app/src/command-palette/__tests__/nativeMenu.test.ts, apps/voss-app/src/App.tsx</files>
  <read_first>
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-RESEARCH.md - Tauri menu docs findings
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - Native Menu Contract
    - apps/voss-app/src/command-palette/registry.ts - command metadata source
  </read_first>
  <behavior>
    - Test 1: menu groups are Window, Pane, Layout, Project, Settings, Help.
    - Test 2: menu item id equals command id.
    - Test 3: menu labels equal registry labels.
    - Test 4: invoking a mocked menu action calls registry execution for that id.
  </behavior>
  <action>
    Add `nativeMenu.ts` that builds and installs the native menu from registry metadata using `@tauri-apps/api/menu` if available in the current dependency set. If the dependency surface is unavailable in tests, isolate it behind an adapter so unit tests can verify the menu model. Wire installation from `App.tsx` after registry creation and rerun/rebuild accelerators when effective bindings change. Do not add a second hard-coded command list.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/command-palette/__tests__/nativeMenu.test.ts && pnpm --dir apps/voss-app build</automated>
  </verify>
  <acceptance_criteria>
    - Native menu model is generated from registry metadata.
    - Labels, ids, categories, and accelerators stay synchronized.
    - App build passes.
  </acceptance_criteria>
  <done>Native menu generation has no source drift from the registry.</done>
</task>

<task type="execute">
  <name>Task 2: Add A7 acceptance smoke and phase summary</name>
  <files>apps/voss-app/e2e/command-palette.spec.ts, .planning/phases/A7-voss-app-command-palette-keymap/A7-PHASE-SUMMARY.md</files>
  <read_first>
    - apps/voss-app/playwright.config.ts - e2e setup
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-VALIDATION.md - per-task verification map
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - manual-only checks
  </read_first>
  <action>
    Add a Playwright smoke spec or source-backed e2e-style spec for A7. Cover these acceptance paths: Cmd+P opens quick mode, Cmd+Shift+P opens full mode, all six categories are findable, recent ranking affects command order in unit coverage, a custom keybinding update can be represented through the keymap storage bridge, invalid keymap entries produce a toast, and tmux Cmd+B then `%` dispatches vertical split. If real Tauri shell execution is not available in CI, mark only the true shell/native-menu checks as manual in `A7-PHASE-SUMMARY.md` and keep unit/source assertions automated.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core keymap && cargo build -p voss-app</automated>
  </verify>
  <acceptance_criteria>
    - A7-PHASE-SUMMARY.md maps CMD-01..CMD-07 to concrete automated or manual verification.
    - Any native menu/file-watch/manual checks are named explicitly, not hidden.
    - Full frontend tests, frontend build, keymap Rust tests, and app build pass.
  </acceptance_criteria>
  <done>A7 is ready for execution verification and later `/gsd:verify-work`.</done>
</task>
</tasks>

<verification>
Run `pnpm --dir apps/voss-app test`, `pnpm --dir apps/voss-app build`, `cargo test -p voss-app-core keymap`, and `cargo build -p voss-app`.
</verification>

<success_criteria>
- All A7 requirements are represented by automated/source/manual acceptance checks.
- Native menus, palette, keyboard dispatch, keymap override validation, toast feedback, and tmux prefix behavior are planned as one cohesive registry-driven feature.
</success_criteria>

