---
phase: A6-voss-app-session-persist
plan: 05
type: execute
wave: 5
depends_on: [A6-04]
files_modified:
  - apps/voss-app/src/grid/RestoreBanner.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/grid/__tests__/RestoreBanner.test.tsx
  - apps/voss-app/src/grid/__tests__/a6-acceptance.test.tsx
  - apps/voss-app/e2e/session-persist.spec.ts
  - .planning/phases/A6-voss-app-session-persist/A6-05-SUMMARY.md
autonomous: false
requirements: [PER-01, PER-02, PER-03, PER-04, PER-05, PER-06]
must_haves:
  truths:
    - "Restored panes show a 22px RestoreBanner with exact copy `Session restored - N lines`"
    - "D-07/D-08/D-09: RestoreBanner is a separate component, uses the exact line-count copy, and dismisses on first keystroke in that pane"
    - "No L1 path relaunches old processes after restore"
    - "A6 final verification includes corrupt-session fallback and project-less global restore"
  artifacts:
    - path: "apps/voss-app/src/grid/RestoreBanner.tsx"
      provides: "Restored scrollback banner"
      contains: "Session restored"
    - path: "apps/voss-app/e2e/session-persist.spec.ts"
      provides: "Restart/session persistence acceptance coverage"
      contains: "session.json"
---

<objective>
Add the restore banner UX and final A6 acceptance coverage for project sessions, project-less sessions, corrupt fallback, scrollback cap, and no process relaunch.
</objective>

<context>
@.planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md
@.planning/phases/A6-voss-app-session-persist/A6-VALIDATION.md
@apps/voss-app/src/grid/CloseConfirmBanner.tsx
@apps/voss-app/src/pane/ExitBanner.tsx
@apps/voss-app/src/grid/SplitNode.tsx
</context>

<threat_model>
T-A6-07 Misleading restore UI. Mitigation: banner copy reports actual restored line count and disappears on first user input; no UI suggests the old process is still running.
</threat_model>

<tasks>
<task type="execute">
  <name>Task 1: Add RestoreBanner component and mount it in pane chrome</name>
  <files>apps/voss-app/src/grid/RestoreBanner.tsx, apps/voss-app/src/grid/SplitNode.tsx, apps/voss-app/src/grid/__tests__/RestoreBanner.test.tsx</files>
  <read_first>
    - apps/voss-app/src/grid/CloseConfirmBanner.tsx - 22px banner layout
    - apps/voss-app/src/pane/ExitBanner.tsx - concise terminal status copy style
    - apps/voss-app/src/grid/SplitNode.tsx - pane chrome mount point
    - .planning/phases/A6-voss-app-session-persist/A6-CONTEXT.md - D-07/D-08/D-09
  </read_first>
  <action>
    Create `RestoreBanner.tsx` rendering a 22px row under `PaneHeader` with Variant B tokens and exact ASCII copy `Session restored - N lines`, where N is passed as `lineCount`. No explicit dismiss button. Mount it in `SplitNode.tsx` when that pane id has restored lines and until `onPaneFirstInput` clears it. Add DOM tests that assert height 22px, exact copy for 0/1/2000 line counts, no button, and dismissal callback path through first input.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/grid/__tests__/RestoreBanner.test.tsx --reporter=dot && grep -q 'Session restored -' src/grid/RestoreBanner.tsx && grep -q \"height: '22px'\" src/grid/RestoreBanner.tsx && echo RESTORE_BANNER_OK</automated>
  </verify>
  <acceptance_criteria>
    - Copy is `Session restored - N lines`.
    - Banner height is 22px.
    - No dismiss button exists.
    - Banner is removed after first input for that pane.
    - `RESTORE_BANNER_OK` prints.
  </acceptance_criteria>
  <done>Restored panes show the required banner.</done>
</task>

<task type="execute">
  <name>Task 2: Add A6 acceptance tests and session restart smoke</name>
  <files>apps/voss-app/src/grid/__tests__/a6-acceptance.test.tsx, apps/voss-app/e2e/session-persist.spec.ts</files>
  <read_first>
    - apps/voss-app/src/grid/__tests__/a4-acceptance.test.tsx - mocked app/grid acceptance style
    - apps/voss-app/e2e/layout-presets.spec.ts - current Playwright skip/platform style
    - .planning/phases/A6-voss-app-session-persist/A6-VALIDATION.md - acceptance map
  </read_first>
  <action>
    Add mocked Vitest acceptance tests proving: project session restore applies before default layout; corrupt/unsupported session falls through to default layout; project-less global session with `projectLessAccepted` bypasses setup; tree-only autosave writes `scrollback: null`; quit save writes last 2,000 lines; no serialized field contains PTY session id or process name. Add a Playwright `session-persist.spec.ts` smoke that documents the real restart flow. If local CI cannot run Tauri restart e2e on Linux, use the existing skip pattern but keep source assertions for `session.json`, `global-session.json`, and `Session restored` tokens.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pnpm --dir apps/voss-app test -- --run src/grid src/pane && pnpm --dir apps/voss-app build && cargo test -p voss-app-core && grep -q 'session.json' apps/voss-app/e2e/session-persist.spec.ts && grep -q 'global-session.json' apps/voss-app/e2e/session-persist.spec.ts && echo A6_ACCEPTANCE_OK</automated>
  </verify>
  <acceptance_criteria>
    - Vitest covers session/default/fresh restore priority.
    - Vitest covers global project-less restore.
    - Vitest covers corrupt/future-version fallback.
    - Tests assert no process relaunch metadata is serialized.
    - Full app test/build and cargo core tests pass.
    - `A6_ACCEPTANCE_OK` prints.
  </acceptance_criteria>
  <done>A6 automated acceptance coverage exists.</done>
</task>

<task type="checkpoint">
  <name>Task 3: Manual restart sign-off</name>
  <files>.planning/phases/A6-voss-app-session-persist/A6-05-SUMMARY.md</files>
  <read_first>
    - .planning/phases/A6-voss-app-session-persist/A6-VALIDATION.md - manual verification instructions
    - apps/voss-app/e2e/session-persist.spec.ts - restart smoke expectations
  </read_first>
  <action>
    Run the app locally. Verify: quit with four panes across two splits and reopen the same project restores exact geometry, focus, active preset, and visible restored scrollback banners; project-less mode relaunches without setup when `global-session.json` has `projectLessAccepted: true`; corrupt `.voss/session.json` falls through to default layout or a fresh pane without crash/dialog. Record results in `A6-05-SUMMARY.md` with `Self-Check: PASSED` only after manual approval.
  </action>
  <verify>
    <manual>Type `approved` only after the restart checks pass on the local machine.</manual>
  </verify>
  <acceptance_criteria>
    - Four-pane project restart restores geometry/focus/preset and banners.
    - Project-less restart bypasses setup window.
    - Corrupt session does not crash and falls through.
    - `A6-05-SUMMARY.md` records manual sign-off.
  </acceptance_criteria>
  <done>Human restart behavior is verified.</done>
</task>
</tasks>

<verification>
Run full app and core test suites, then complete the manual restart sign-off.
</verification>

<success_criteria>
- Project and project-less sessions restore across app restart.
- Corrupt sessions fail closed.
- Restore UI is accurate and unobtrusive.
- No live process restart is attempted in L1.
</success_criteria>
