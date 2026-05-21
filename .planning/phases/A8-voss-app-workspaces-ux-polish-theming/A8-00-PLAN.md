---
phase: A8-voss-app-workspaces-ux-polish-theming
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-00-SUMMARY.md
autonomous: false
requirements: [UXP-01, UXP-02, UXP-03, UXP-04, UXP-05, UXP-06, UXP-07, UXP-08, UXP-09, UXP-10, UXP-11, UXP-12, UXP-13, UXP-14, UXP-15, UXP-16, UXP-17, UXP-18, UXP-19, UXP-20, UXP-21, UXP-22, UXP-23, UXP-24, UXP-25, UXP-26, UXP-27, UXP-28, UXP-29, UXP-30]
must_haves:
  truths:
    - "A8 execution is blocked until context, research, validation, UI-SPEC, and pattern map exist"
    - "A8-CONTEXT supersedes ROADMAP wording where ROADMAP still mentions VSCode theme import"
    - "A7 source surface must exist before A8 wires registry/toast/profile/theme commands"
  artifacts:
    - path: ".planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md"
      provides: "Approved visual and interaction contract"
      contains: "status: approved"
---

<objective>
Verify A8 planning and source substrate before workspace/theme implementation starts.
</objective>

<context>
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-VALIDATION.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PATTERNS.md
</context>

<threat_model>
T-A8-00 False-positive execution over missing design, A7, or A6 substrate. Mitigation: non-autonomous preflight records exact pass/fail for UI-SPEC, A7 registry/toast/menu, App/GridRoot, theme seam, and A6 persistence seam.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Verify A8 planning and source substrate</name>
  <files>.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-00-SUMMARY.md</files>
  <read_first>
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-CONTEXT.md - D-01..D-14 locked decisions
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md - A7/A6 hazards
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - visual contract
    - apps/voss-app/src/App.tsx - current single-workspace composition root
    - apps/voss-app/src/grid/GridRoot.tsx - global keydown host
    - apps/voss-app/src/grid/sessionPersist.ts - single-workspace save lifecycle
    - apps/voss-app/src/theme/applyTheme.ts - runtime theme seam
    - apps/voss-app/src/command-palette/registry.ts - A7 command registry
    - apps/voss-app/src/command-palette/toast.tsx - A7 toast stack
  </read_first>
  <action>
    Inspect required artifacts and source seams. Confirm `A8-UI-SPEC.md` has `status: approved`, `A8-RESEARCH.md` contains `## Validation Architecture`, `A8-PATTERNS.md` contains `## PATTERN MAPPING COMPLETE`, A7 registry/toast/native menu files exist, `App.tsx` still has one `GridRoot` and A7 palette wiring, `GridRoot.tsx` still installs global keydown listeners that need active gating, `sessionPersist.ts` still installs one close handler, and `applyThemeOverrides()` exists. Write `A8-00-SUMMARY.md` with `Self-Check: PASSED` if all assertions hold; otherwise write `Self-Check: FAILED` and stop later plans.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -q 'status: approved' .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md && grep -q '## Validation Architecture' .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-RESEARCH.md && grep -q '## PATTERN MAPPING COMPLETE' .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PATTERNS.md && test -f apps/voss-app/src/command-palette/registry.ts && test -f apps/voss-app/src/command-palette/toast.tsx && grep -q 'createCommandRegistry' apps/voss-app/src/App.tsx && grep -q 'window.addEventListener.*keydown' apps/voss-app/src/grid/GridRoot.tsx && grep -q 'installCloseSessionSave' apps/voss-app/src/grid/sessionPersist.ts && grep -q 'applyThemeOverrides' apps/voss-app/src/theme/applyTheme.ts && echo A8_PREFLIGHT_OK</automated>
  </verify>
  <acceptance_criteria>
    - `A8-00-SUMMARY.md` explicitly says PASSED or FAILED.
    - Failure names exact missing source/artifact assertions.
    - Summary explicitly records whether A7 registry/toast/native-menu source exists.
  </acceptance_criteria>
  <done>A8 readiness is known before implementation starts.</done>
</task>
</tasks>

<verification>
Run the automated preflight command and inspect `A8-00-SUMMARY.md` before Wave 1.
</verification>

<success_criteria>
- A8 does not execute without approved UI-SPEC, research, validation, pattern map, and source seams.
</success_criteria>

