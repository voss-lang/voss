---
phase: A7-voss-app-command-palette-keymap
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - .planning/phases/A7-voss-app-command-palette-keymap/A7-00-SUMMARY.md
autonomous: false
requirements: [CMD-01, CMD-02, CMD-03, CMD-04, CMD-05, CMD-06, CMD-07]
must_haves:
  truths:
    - "A7 execution is blocked until A7-CONTEXT, A7-RESEARCH, A7-VALIDATION, A7-UI-SPEC, and A7-PATTERNS exist"
    - "A7 builds on A3 keymap/GridRoot, A4 layout storage, A5 project recents/open, and Variant B tokens"
    - "D-01..D-16 are present in source artifacts before implementation starts"
  artifacts:
    - path: ".planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md"
      provides: "Approved visual and interaction contract"
      contains: "status: approved"
---

<objective>
Verify A7 planning substrate exists before command-palette/keymap implementation starts.
</objective>

<context>
@.planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-RESEARCH.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-VALIDATION.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md
@.planning/phases/A7-voss-app-command-palette-keymap/A7-PATTERNS.md
</context>

<threat_model>
T-A7-00 False-positive execution over missing design or substrate. Mitigation: require all A7 artifacts plus A3/A4/A5 source seams before Wave 1.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Verify A7 planning and source substrate</name>
  <files>.planning/phases/A7-voss-app-command-palette-keymap/A7-00-SUMMARY.md</files>
  <read_first>
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-CONTEXT.md - D-01..D-16 locked decisions
    - .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md - visual contract
    - apps/voss-app/src/App.tsx - A4/A5 AppContext source
    - apps/voss-app/src/grid/keymap.ts - existing chords to migrate
    - apps/voss-app/src/grid/GridRoot.tsx - keydown host
    - apps/voss-app/src/grid/layoutStorage.ts - saved layout wrappers
    - apps/voss-app/src/project/projectStorage.ts - recents/open wrappers
    - apps/voss-app/src/styles/variant-b.css - token source
  </read_first>
  <action>
    Inspect required artifacts and source seams. Confirm `A7-UI-SPEC.md` has `status: approved`, `A7-RESEARCH.md` contains `## Validation Architecture`, `A7-PATTERNS.md` contains `## PATTERN MAPPING COMPLETE`, `App.tsx` owns `project`, `recents`, `activeLayout`, `saveCurrentLayout`, and `loadLayoutByName`, `grid/keymap.ts` still defines current A3/A4 chords, and layout/project storage wrappers exist. Write `A7-00-SUMMARY.md` with `Self-Check: PASSED` if all assertions hold; otherwise write `Self-Check: FAILED` and stop later plans.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q 'status: approved' .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md && grep -q '## Validation Architecture' .planning/phases/A7-voss-app-command-palette-keymap/A7-RESEARCH.md && grep -q '## PATTERN MAPPING COMPLETE' .planning/phases/A7-voss-app-command-palette-keymap/A7-PATTERNS.md && grep -q 'saveCurrentLayout' apps/voss-app/src/App.tsx && grep -q 'loadLayoutByName' apps/voss-app/src/App.tsx && grep -q 'dispatchKey' apps/voss-app/src/grid/keymap.ts && grep -q 'listLayouts' apps/voss-app/src/grid/layoutStorage.ts && grep -q 'listRecents' apps/voss-app/src/project/projectStorage.ts && echo A7_PREFLIGHT_OK</automated>
  </verify>
  <acceptance_criteria>
    - `A7-00-SUMMARY.md` explicitly says PASSED or FAILED.
    - Failure names exact missing source/artifact assertions.
    - Passing preflight proves A7 can plan against real A3/A4/A5 substrate.
  </acceptance_criteria>
  <done>A7 substrate readiness is known before implementation starts.</done>
</task>
</tasks>

<verification>
Run the automated preflight command and inspect `A7-00-SUMMARY.md` before Wave 1.
</verification>

<success_criteria>
- A7 does not execute without approved UI-SPEC, research, validation, and source seams.
</success_criteria>

