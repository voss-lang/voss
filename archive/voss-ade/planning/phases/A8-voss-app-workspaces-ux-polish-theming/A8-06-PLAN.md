---
phase: A8-voss-app-workspaces-ux-polish-theming
plan: 06
type: execute
wave: 6
depends_on: [A8-01, A8-02, A8-03, A8-04, A8-05]
files_modified:
  - apps/voss-app/e2e/workspaces.spec.ts
  - apps/voss-app/e2e/themes.spec.ts
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PHASE-SUMMARY.md
  - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-06-SUMMARY.md
autonomous: false
requirements: [UXP-01, UXP-02, UXP-03, UXP-04, UXP-05, UXP-06, UXP-07, UXP-08, UXP-09, UXP-10, UXP-11, UXP-12, UXP-13, UXP-14, UXP-15, UXP-16, UXP-17, UXP-18, UXP-19, UXP-20, UXP-21, UXP-22, UXP-23, UXP-24, UXP-25, UXP-26, UXP-27, UXP-28, UXP-29, UXP-30]
must_haves:
  truths:
    - "A8 is not complete until automated and manual acceptance are recorded"
    - "Manual platform checks must name OS and date"
    - "Known platform gaps must be explicit, not silently accepted"
---

<objective>
Run full A8 acceptance, record manual platform/runtime results, and summarize phase completion.
</objective>

<context>
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-VALIDATION.md
@.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md
</context>

<threat_model>
T-A8-09 Automated tests pass but runtime UX is broken. Mitigation: final plan is non-autonomous and records manual workspace/theme/vibrancy checks before phase summary.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Add final workspace/theme acceptance tests</name>
  <files>apps/voss-app/e2e/workspaces.spec.ts, apps/voss-app/e2e/themes.spec.ts</files>
  <read_first>
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-VALIDATION.md - manual/automated matrix
    - apps/voss-app/package.json - e2e scripts
    - existing e2e files if present
  </read_first>
  <action>
    Add Playwright or documented runtime acceptance coverage for workspace creation/switching/restore and theme preview/apply. If Tauri e2e cannot run in CI, make the tests or script self-skipping with clear manual fallback instructions in the summary.
  </action>
  <verify>
    <automated>pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core && cargo build -p voss-app</automated>
  </verify>
  <acceptance_criteria>
    - Automated suite covers the A8 pure/component behaviors.
    - Runtime/e2e coverage exists or is explicitly marked manual with reason.
    - No watch-mode commands are used.
  </acceptance_criteria>
  <done>Automated A8 acceptance is represented.</done>
</task>

<task type="execute">
  <name>Task 2: Perform manual runtime acceptance and write phase summary</name>
  <files>.planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-PHASE-SUMMARY.md, .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-06-SUMMARY.md</files>
  <read_first>
    - .planning/ROADMAP.md - A8 success criteria and UXP-01..30
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-VALIDATION.md - manual checks
    - .planning/phases/A8-voss-app-workspaces-ux-polish-theming/A8-UI-SPEC.md - visual contract
    - A8-01-SUMMARY.md through A8-05-SUMMARY.md - implementation evidence
  </read_first>
  <action>
    Run the app locally and record manual checks: three workspace tabs with independent pane trees, Ctrl workspace switching, hidden PTY liveness, quit/reopen restore, theme preview/apply, high-contrast overlay, Presentation-style profile switch, opacity/vibrancy on available OS, and platform metadata status. Write `A8-PHASE-SUMMARY.md` mapping UXP-01..30 to evidence and `A8-06-SUMMARY.md` with `Self-Check: PASSED` or exact remaining gaps.
  </action>
  <verify>
    <manual>Run `pnpm --dir apps/voss-app tauri dev`, complete the A8-VALIDATION manual-only table, and paste exact pass/fail results with OS/date into A8-PHASE-SUMMARY.md.</manual>
  </verify>
  <acceptance_criteria>
    - A8-PHASE-SUMMARY.md maps every UXP-01..30 item to automated or manual evidence.
    - Manual checks name OS, date, and result.
    - Any not-run platform check is explicit with reason and follow-up owner.
    - A8-06-SUMMARY.md has `Self-Check: PASSED` only if blockers are closed.
  </acceptance_criteria>
  <done>A8 is ready for `/gsd:verify-work` with evidence, not assumptions.</done>
</task>
</tasks>

<verification>
Run full frontend/Rust suites, build both frontend and Tauri app, then complete manual runtime checks.
</verification>

<success_criteria>
- All A8 UXP-01..30 requirements have evidence.
- Manual-only platform and runtime checks are recorded clearly.
- Phase summary is ready for verification/audit.
</success_criteria>

