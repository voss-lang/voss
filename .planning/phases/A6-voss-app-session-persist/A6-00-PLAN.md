---
phase: A6-voss-app-session-persist
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - .planning/phases/A6-voss-app-session-persist/A6-00-SUMMARY.md
autonomous: false
requirements: [PER-01, PER-02, PER-03, PER-04, PER-05, PER-06]
must_haves:
  truths:
    - "A6 execution is blocked until A5 project-open lifecycle is present in the app runtime"
    - "A6 builds on A3 GridRoot and A4 layout persistence; it must not reimplement those features"
    - "If substrate is missing, stop and execute A5/A4 first rather than faking project/session state"
  artifacts:
    - path: "apps/voss-app/src/App.tsx"
      provides: "Project state, project-less state, activeLayout state, GridRoot controller wiring"
      contains: "GridRoot"
---

<objective>
Verify the A6 substrate exists before any session-persistence work starts. This is a blocking preflight plan because the inspected tree has A6 context ready but does not show A5 project-open fully summarized yet.
</objective>

<context>
@.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md
@.planning/phases/A6-voss-app-session-persist/A6-RESEARCH.md
@.planning/phases/A6-voss-app-session-persist/A6-PATTERNS.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md
@.planning/phases/A3-voss-app-grid-engine/A3-CONTEXT.md
</context>

<threat_model>
T-A6-00 False-positive planning over missing substrate. Mitigation: require source and summary evidence for A3/A4/A5 before implementation plans run. Continuing without this gate would produce cwd/session-target heuristics that violate A5 and A6 decisions.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Verify A3/A4/A5 substrate before A6 implementation</name>
  <files>.planning/phases/A6-voss-app-session-persist/A6-00-SUMMARY.md</files>
  <read_first>
    - .planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md - D-10/D-12 dependency decisions
    - apps/voss-app/src/App.tsx - app composition root
    - apps/voss-app/src/grid/GridRoot.tsx - grid controller shape
    - apps/voss-app/src/grid/layoutStorage.ts - A4 persistence wrappers
    - crates/voss-app-core/src/project.rs - A5 project/default cwd helpers
    - apps/voss-app/src-tauri/src/lib.rs - registered project/layout/grid commands
  </read_first>
  <action>
    Inspect the source and phase summaries. Confirm all of the following before any A6 plan executes: `App.tsx` owns project or project-less state from A5; `default_cwd`, `open_project`, and recents/list project commands are registered if A5 plans require them; `GridRoot` exposes `snapshot()` and `applyLoadedLayout()`; `App.tsx` owns `activeLayout`; `sync_grid`, `save_layout`, `load_default_layout`, and `get_grid` are registered in `apps/voss-app/src-tauri/src/lib.rs`. If any item is missing, write `A6-00-SUMMARY.md` with `Self-Check: FAILED`, name the missing source assertions, and stop execution of later A6 plans. If all pass, write `A6-00-SUMMARY.md` with `Self-Check: PASSED`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q 'GridRoot' apps/voss-app/src/App.tsx && grep -q 'snapshot' apps/voss-app/src/grid/GridRoot.tsx && grep -q 'applyLoadedLayout' apps/voss-app/src/grid/GridRoot.tsx && grep -q 'loadDefaultLayout' apps/voss-app/src/grid/layoutStorage.ts && grep -q 'pub fn default_cwd' crates/voss-app-core/src/project.rs && grep -q 'sync_grid' apps/voss-app/src-tauri/src/lib.rs && grep -q 'load_default_layout' apps/voss-app/src-tauri/src/lib.rs && echo A6_PREFLIGHT_PARTIAL_OK</automated>
  </verify>
  <acceptance_criteria>
    - `A6-00-SUMMARY.md` explicitly says PASSED or FAILED.
    - Failure names exact missing files/functions and stops downstream execution.
    - Passing preflight proves A3/A4/A5 substrate exists by source assertion, not assumption.
  </acceptance_criteria>
  <done>A6 substrate readiness is known before implementation starts.</done>
</task>
</tasks>

<verification>
Run the automated preflight command and inspect `A6-00-SUMMARY.md` before starting Wave 1.
</verification>

<success_criteria>
- A6 does not execute against missing project-open/session-target infrastructure.
- Any substrate gap is surfaced as an explicit blocker.
</success_criteria>

