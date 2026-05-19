---
phase: A4-voss-app-layout-presets
plan: 00
type: execute
wave: 0
depends_on: [A3-06]
files_modified: []
autonomous: false
requirements: [LAY-04, LAY-05, LAY-08]
must_haves:
  truths:
    - "A4 execution does not start until A3-06 has mounted GridRoot in App.tsx and registered sync_grid/get_grid in the Tauri app"
    - "A4 does not repair A3 duplicate-header, foreground-close, or mirror-registration gaps"
    - "The executor has a clean substrate checklist before touching preset/layout files"
  artifacts:
    - path: ".planning/phases/A3-voss-app-grid-engine/A3-06-SUMMARY.md"
      provides: "A3-06 completion proof"
      contains: "GridRoot"
    - path: "apps/voss-app/src/App.tsx"
      provides: "GridRoot is mounted below the titlebar"
      contains: "GridRoot"
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "sync_grid/get_grid command registration"
      contains: "sync_grid"
---

<objective>
Block A4 execution until the A3 runtime substrate is actually assembled. A4 is a layout-preset phase, not the A3 integration phase.
</objective>

<context>
@.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md
@.planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md
@.planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md
@.planning/phases/A3-voss-app-grid-engine/A3-06-PLAN.md
</context>

<threat_model>
Primary risk: false-positive A4 implementation over an unmounted grid or unregistered Rust mirror. Mitigation: hard preflight assertions before any A4 code task proceeds. Block on failure.
</threat_model>

<tasks>
<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Verify A3-06 substrate before A4 begins</name>
  <files>none</files>
  <read_first>
    - .planning/phases/A3-voss-app-grid-engine/A3-06-SUMMARY.md — completion proof for the app integration wave
    - apps/voss-app/src/App.tsx — must render `GridRoot` below `Titlebar`, not direct `PaneComponent`
    - apps/voss-app/src-tauri/src/lib.rs — must register and manage `sync_grid` and `get_grid`
    - .planning/phases/A3-voss-app-grid-engine/A3-05-SUMMARY.md — carry-forward notes that A3-06 must resolve or explicitly defer
  </read_first>
  <action>
    Check that `.planning/phases/A3-voss-app-grid-engine/A3-06-SUMMARY.md` exists and states A3-06 completed. Check that `apps/voss-app/src/App.tsx` imports/renders `GridRoot` in the body slot below `Titlebar`. Check that `apps/voss-app/src-tauri/src/lib.rs` registers `sync_grid` and `get_grid` in `tauri::generate_handler!` and manages `Mutex<GridState>`. Check whether A3-05's duplicate-header and foreground-close carry-forward items are resolved or explicitly deferred in A3-06-SUMMARY. If any check fails, stop A4 execution and run `/gsd:execute-phase A3` for A3-06 first.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && test -f .planning/phases/A3-voss-app-grid-engine/A3-06-SUMMARY.md && grep -q 'GridRoot' apps/voss-app/src/App.tsx && grep -q 'sync_grid' apps/voss-app/src-tauri/src/lib.rs && grep -q 'get_grid' apps/voss-app/src-tauri/src/lib.rs && grep -q 'Mutex<GridState>' apps/voss-app/src-tauri/src/lib.rs && echo A4_SUBSTRATE_READY</automated>
  </verify>
  <acceptance_criteria>
    - `A4_SUBSTRATE_READY` prints from the automated command.
    - If the command fails, no A4 implementation files are edited.
    - The executor records the A3-06 summary status in A4 execution notes before continuing.
  </acceptance_criteria>
  <done>A3 substrate is verified; A4 can safely implement preset/layout behavior.</done>
</task>
</tasks>

<verification>
Run the task verify command. Continue to A4-01 only if it prints `A4_SUBSTRATE_READY`.
</verification>

<success_criteria>
- A4 does not proceed on an unmounted grid.
- A4 does not silently absorb unfinished A3 integration work.
- The A4 executor has an explicit pass/fail substrate gate.
</success_criteria>

