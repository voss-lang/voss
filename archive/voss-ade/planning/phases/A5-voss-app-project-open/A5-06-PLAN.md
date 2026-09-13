---
phase: A5-voss-app-project-open
plan: 06
type: execute
wave: 5
depends_on: [A5-05]
files_modified:
  - apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx
  - apps/voss-app/e2e/project-open.spec.ts
  - .planning/phases/A5-voss-app-project-open/A5-VALIDATION.md
autonomous: false
requirements: [WS-01, WS-02, WS-03, WS-04, WS-05, WS-06, WS-07]
must_haves:
  truths:
    - "Every WS-01..WS-07 requirement and every SPEC AC #1..#11 checkbox has an automated assertion or an explicit deferred-with-reason note"
    - "An e2e spec exists for project-open and either runs or is explicitly skip-deferred with the documented macOS-Tauri-WebDriver reason"
    - "Full test suites (cargo test --workspace + pnpm --filter voss-app test + tsc --noEmit + cargo build -p voss-app) pass before phase verify"
    - "Manual visual checkpoint confirms the SetupWindow surface, Titlebar project-name swap, no L2 vocab, and the no-PTY-destruction guarantee"
  artifacts:
    - path: "apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx"
      provides: "Requirement-level acceptance suite grouped by WS-01..WS-07"
      contains: "WS-01"
    - path: "apps/voss-app/e2e/project-open.spec.ts"
      provides: "End-to-end smoke for folder picker + setup-vs-grid branch + project metadata; skip-deferred on macOS"
      contains: "SKIP_REASON"
    - path: ".planning/phases/A5-voss-app-project-open/A5-VALIDATION.md"
      provides: "Requirement-to-test traceability + final command list"
      contains: "WS-01"
---

<objective>
Close A5 with: a requirement-level acceptance suite (one section per WS-NN), an e2e spec following the documented macOS-skip-deferred pattern from A4, a validation document recording the test-to-requirement map, and a blocking human-verify checkpoint that runs the full command suite + a visual sign-off.

Purpose: Make every WS-01..WS-07 requirement and every SPEC acceptance checkbox traceable to an automated assertion or an explicitly deferred-with-reason note. Confirm L1 vocab discipline at the rendered-DOM level. Sign off the visual surface before `/gsd:verify-work A5`.
Output: `A5_FULL_GREEN` printed, A5-VALIDATION.md committed, and a human-approved visual record.
</objective>

<context>
@.planning/phases/A5-voss-app-project-open/A5-SPEC.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A5-voss-app-project-open/A5-RESEARCH.md
@.planning/phases/A5-voss-app-project-open/A5-PATTERNS.md
@.planning/ROADMAP.md
@.planning/phases/A4-voss-app-layout-presets/A4-05-PLAN.md
@.planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md
@apps/voss-app/e2e/layout-presets.spec.ts
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test coverage vs. requirement set | Acceptance suite must close the requirement-to-test map; gaps are reportable |
| Macro suite vs. local truth | `cargo test --workspace` may include unrelated phases; A5 cares about voss-app-core + voss-app + tsc all green |
| Visual vs. automated | DOM token-discipline tests catch most regressions; visual checkpoint catches the things tests cannot (font, spacing, perceived brightness) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A5-COV | Repudiation | requirement coverage gap | mitigate | a5-acceptance.test.tsx organizes assertions by WS-NN and SPEC AC #; A5-VALIDATION.md records the map; CI grep proves every WS-NN string appears in the test file |
| T-A5-L1-LEAK (carry) | Information disclosure | L2 vocab on L1 surface | mitigate | Final grep at acceptance-test level: assert no agent / worktree / reviewer / model / cost / token in the rendered DOM trees of SetupWindow and Titlebar (with project name) |
| T-A5-E2E-MAC | Repudiation | end-to-end gap on macOS dev box | accept | E2E spec captures intent in code form, gates on the documented SKIP_REASON, references the unit-acceptance suite as the macOS-authoritative gate (project memory `voss-app-tauri-e2e-macos-blocked`) |
| T-A5-PTY (carry) | DoS | PTY destruction on project change | mitigate | Acceptance test re-asserts pane identity is preserved across setProject calls — this is the only end-to-end proof of SPEC Req-8 in the unit layer |
</threat_model>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Write A5 requirement-level acceptance suite</name>
  <files>apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx, .planning/phases/A5-voss-app-project-open/A5-VALIDATION.md</files>
  <read_first>
    - apps/voss-app/src/grid/__tests__/a4-acceptance.test.tsx — A4 acceptance pattern (LAY-01..LAY-08 sections, grep gates, L2-vocab assertions)
    - .planning/phases/A4-voss-app-layout-presets/A4-VALIDATION.md — A4 validation document format (requirement-to-test map, status column, final command list)
    - .planning/ROADMAP.md Phase A5 — WS-01..WS-07 strings
    - .planning/phases/A5-voss-app-project-open/A5-SPEC.md — 11 acceptance checkboxes
    - apps/voss-app/src/__tests__/App.test.tsx (from A5-05) — integration coverage already in place
    - apps/voss-app/src/components/setup/__tests__/SetupWindow.test.tsx (from A5-04)
    - apps/voss-app/src/project/__tests__/projectStorage.test.ts (from A5-03)
  </read_first>
  <behavior>
    - The acceptance test file contains seven describe blocks: `WS-01`, `WS-02`, `WS-03`, `WS-04`, `WS-05`, `WS-06`, `WS-07`. Each block contains 1+ assertions referencing the SPEC AC checkboxes covered.
    - WS-01 (`⌘O` / folder picker — SPEC narrowed to picker contract; ⌘O accelerator is planner discretion per CONTEXT line 56): assert pickFolder is the picker contract; if a ⌘O binding was added, assert dispatch triggers handleOpenFolder.
    - WS-02 (recents at ~/.config/voss-app/recents.json, cap 5): assert recents cap behavior via A5-01 Rust test integration name (`open_project_caps_recents_at_5`) is referenced in A5-VALIDATION.md AND a JS-side assertion that listRecents() round-trips an empty/non-empty list.
    - WS-03 (lazy .voss/ on open): assert the Rust-side test name (`open_project_does_not_create_voss_directory`) is referenced.
    - WS-04 (git branch read via git2): assert ProjectInfo has gitBranch field, and that the A5-01 Rust test for git-init / branch-name covers the live path.
    - WS-05 (project-less mode): assert App.tsx test for `onStartProjectLess` → showGrid() flips → project remains null.
    - WS-06 (panes inherit project cwd; project-less = $HOME): assert default_cwd Tauri command exists (grep src-tauri/src/lib.rs) AND App.tsx test for the cwd thread-through (or document in A5-VALIDATION that the cwd into operations.ts is deferred to a follow-up).
    - WS-07 (switch project via palette): SPEC explicitly says A7 owns palette; A5-06 acceptance asserts the project-change PATH exists (calling handleOpenRecent updates project state and preserves panes). The palette UI itself is correctly absent.
    - SPEC AC #1..#11 cross-mapped — each checkbox has an explicit `// SPEC AC #N: ...` comment next to the relevant assertion.
    - L2-vocab final gate: render SetupWindow + Titlebar (with project name `agent-checker` — a deliberately tempting string that uses the word `agent` in user data, NOT in surface chrome), then assert that the App-chrome DOM (titlebar text content excluding the project-name substring + setup-window outerHTML) contains none of the forbidden tokens. (User-provided project names CAN contain those words; the rule is about voss-app's own chrome.)
  </behavior>
  <action>
    Create `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx`. Clone the A4 a4-acceptance.test.tsx scaffolding:

    - Import the same vi.hoisted invoke / openDialog mocks (cross-import or duplicate).
    - Group assertions by WS-NN describe blocks.
    - Where the actual behavior is covered by an existing test (App.test.tsx, SetupWindow.test.tsx, projectStorage.test.ts, or a Rust test in voss-app-core::project), include an `it.todo`-equivalent OR a thin re-assertion that calls the same handler. Prefer a thin re-assertion because the value of the acceptance suite is one-shot coverage proof, not duplicate exhaustive tests.
    - Add explicit `// SPEC AC #1` through `// SPEC AC #11` comments next to assertions.
    - Add the L2-vocab final gate test described in behavior.
    - The file should be ~150-250 lines (A4 a4-acceptance is ~200 lines for reference).

    Create `.planning/phases/A5-voss-app-project-open/A5-VALIDATION.md`. Clone the A4-VALIDATION format:

    Sections:
      1. Requirement-to-test map table: columns = `WS-NN`, `SPEC AC #`, `Test File`, `Test Name`, `Status (green/deferred)`.
      2. Final command list: the exact `cargo test --workspace`, `pnpm --filter voss-app test`, `pnpm --filter voss-app exec tsc --noEmit -p .`, `cargo build -p voss-app` invocations that constitute the A5 phase gate.
      3. Deferred items section: anything that is genuinely deferred (e.g. cwd thread-through into operations.ts, ⌘O accelerator) with the deferral phase named (A6 / A7 / A8 / A11 per SPEC boundaries).
      4. Visual checkpoint plan: the script the human will follow in Task 3 (launch app, expect setup window, click Open project, pick a temp dir, expect titlebar swap, expect grid mount, change project via recent, expect no pane remount).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && pnpm vitest run src/project/__tests__/a5-acceptance.test.tsx --reporter=dot 2>&1 | tail -30 && grep -q 'WS-01' src/project/__tests__/a5-acceptance.test.tsx && grep -q 'WS-07' src/project/__tests__/a5-acceptance.test.tsx && grep -q 'SPEC AC #1' src/project/__tests__/a5-acceptance.test.tsx && grep -q 'SPEC AC #11' src/project/__tests__/a5-acceptance.test.tsx && test -f /Users/benjaminmarks/Projects/Voss/.planning/phases/A5-voss-app-project-open/A5-VALIDATION.md && grep -q 'WS-01' /Users/benjaminmarks/Projects/Voss/.planning/phases/A5-voss-app-project-open/A5-VALIDATION.md && grep -q 'WS-07' /Users/benjaminmarks/Projects/Voss/.planning/phases/A5-voss-app-project-open/A5-VALIDATION.md && echo A5_ACCEPTANCE_OK</automated>
  </verify>
  <acceptance_criteria>
    - a5-acceptance.test.tsx has explicit WS-01..WS-07 describe blocks.
    - SPEC AC #1..#11 comments are mapped to specific assertions.
    - L2-vocab final gate asserts setup-window + titlebar chrome does NOT contain agent/worktree/reviewer/model/cost/token (modulo user-supplied data).
    - A5-VALIDATION.md exists, contains the requirement-to-test map, the final command list, and the deferred-items section.
    - `pnpm vitest run src/project/__tests__/a5-acceptance.test.tsx` exits 0.
    - A5_ACCEPTANCE_OK prints.
  </acceptance_criteria>
  <done>A5 has requirement-level coverage and a validation document mapping every requirement to a test or a documented deferral.</done>
</task>

<task type="auto">
  <name>Task 2: Write e2e project-open spec with macOS skip-deferred pattern</name>
  <files>apps/voss-app/e2e/project-open.spec.ts</files>
  <read_first>
    - apps/voss-app/e2e/layout-presets.spec.ts (entire file) — the documented SKIP_REASON pattern from A4 (project memory `voss-app-tauri-e2e-macos-blocked`); clone the header doc-comment verbatim with A5 substitutions
    - apps/voss-app/e2e/grid-integration.spec.ts — current voss-app Playwright launch + selector conventions
    - .planning/phases/A5-voss-app-project-open/A5-SPEC.md — the user-visible scenarios A5 e2e would cover if it could run
    - .planning/phases/A5-voss-app-project-open/A5-CONTEXT.md D-05 — folder picker is the contract; e2e cannot drive native folder dialogs anyway, so the e2e is partially blocked by dialog-mocking even on Linux. Document the limitation.
  </read_first>
  <action>
    Create `apps/voss-app/e2e/project-open.spec.ts`. Mirror the layout-presets.spec.ts header structure:

    1. Import `{ test }` from `@playwright/test`.
    2. Add the same SKIP_REASON doc-comment as layout-presets.spec.ts but with A5-specific substitutions:
       - List the A5 unit-test files that constitute the macOS-authoritative gate:
         * src/__tests__/App.test.tsx — setup-vs-grid branching + open-project orchestration + pane preservation
         * src/components/setup/__tests__/SetupWindow.test.tsx — controlled component + token discipline + L1 vocab
         * src/project/__tests__/projectStorage.test.ts — invoke wrappers + camelCase + dialog cancel
         * src/project/__tests__/a5-acceptance.test.tsx — WS-01..WS-07 requirement coverage
         * cargo test -p voss-app-core project:: — Rust core including lazy .voss/, recents cap, canonicalize, git-branch
       - Note the additional blocker: native folder dialog cannot be driven by Playwright without mocking; even on Linux, the test would need a JS-level mock of @tauri-apps/plugin-dialog injected via the test build, which is non-trivial.
       - Reference the same A2-04 user decision the A4 spec references (project memory `voss-app-tauri-e2e-macos-blocked`).
    3. Define `const SKIP_REASON = '...' ` and use it in test.skip() calls.
    4. Encode the scenarios A5 would cover if it could run — as `.skip` tests so the assertion intent is captured for the future Linux CI un-skip:
       - "setup window visible on launch with no project"
       - "click Open project → mocked picker returns /tmp/x → titlebar updates to 'x'"
       - "Start without project → grid mounts → titlebar stays 'Voss ADE'"
       - "Open recent → existing project changes → pane id from prior project survives" (D-13)
       - "Open same dir twice → recents list does not duplicate" (SPEC AC #3)
       - "Open 6 dirs → recents capped at 5" (SPEC Req-5)
       - "Open dir with .voss/layouts/default.json present → default layout applies" (SPEC Req-7)

    Each test body is `test.skip(SKIP_REASON, async ({ page }) => { /* TODO when un-skipped */ });`.

    Run the file once to confirm Playwright loads it without error (even if all tests skip).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && test -f e2e/project-open.spec.ts && grep -q 'SKIP_REASON' e2e/project-open.spec.ts && grep -q 'tauri-driver' e2e/project-open.spec.ts && grep -q 'Open project' e2e/project-open.spec.ts && grep -q 'Start without project' e2e/project-open.spec.ts && grep -q 'a5-acceptance' e2e/project-open.spec.ts && SKIPS=$(grep -c 'test.skip(' e2e/project-open.spec.ts) && [ "$SKIPS" -ge 7 ] && (pnpm playwright test project-open 2>&1 | tail -10) && echo A5_E2E_SPEC_OK</automated>
  </verify>
  <acceptance_criteria>
    - apps/voss-app/e2e/project-open.spec.ts exists with the SKIP_REASON header pattern.
    - Seven scenarios are encoded as skip()'d tests.
    - The unit-acceptance suite (a5-acceptance.test.tsx) is referenced as the macOS-authoritative gate.
    - Playwright load (`pnpm playwright test project-open`) does not error; tests skip gracefully.
    - A5_E2E_SPEC_OK prints.
  </acceptance_criteria>
  <done>E2E intent is captured for the future Linux CI un-skip; macOS gate stays on the unit + Rust + tsc suite.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Full verification and visual sign-off</name>
  <files>none</files>
  <read_first>
    - .planning/phases/A5-voss-app-project-open/A5-SPEC.md — 11 acceptance checkboxes
    - .planning/phases/A5-voss-app-project-open/A5-VALIDATION.md — final command list + visual checkpoint plan (written in Task 1)
    - .planning/phases/A5-voss-app-project-open/A5-CONTEXT.md D-13 — no PTY destruction on project change
  </read_first>
  <action>
    Run the full A5 command set in order:

      1. cargo test -p voss-app-core project:: -- --nocapture
      2. cargo test --workspace --quiet
      3. cargo build -p voss-app --quiet
      4. pnpm --filter voss-app test
      5. pnpm --filter voss-app exec tsc --noEmit -p .
      6. pnpm --filter voss-app build

    Then run the app on the dev machine (pnpm --filter voss-app dev OR pnpm --filter voss-app tauri dev — whichever is the documented launch path) and walk the SPEC visual checkpoints:

      a. Launch with no project → SetupWindow visible, Titlebar shows 'Voss ADE'.
      b. Click "Open project" → native folder picker opens. Pick a temp directory (e.g. mktemp -d).
      c. After pick → SetupWindow disappears, GridRoot mounts, Titlebar shows the temp dir basename.
      d. Verify `<temp>/.voss/` does NOT exist on disk (lazy creation rule — open shell, `ls -la <temp>/.voss` must say No such file).
      e. Open a second temp directory. Confirm: titlebar swaps to the new basename; the existing pane (if you spawned one) is still there with its scrollback intact (D-13).
      f. Click "Start without project" path → GridRoot mounts, Titlebar shows 'Voss ADE', new panes spawn with $HOME as cwd.
      g. Quit and relaunch in project-less mode (no project in any recents) → SetupWindow shows again (D-04: projectLessAccepted is session-only).
      h. Open a directory that is a git repo (e.g. the Voss repo itself) → Titlebar shows the project name; verify the gitBranch comes through (check via DevTools / a log line — A5 does not render branch in UI; A10 will).
      i. Verify the SetupWindow surface uses tokens-only — no raw white anywhere. Variant B aesthetic must match A1-A4 surface.
      j. Confirm no L2 vocab anywhere on the chrome (agent / worktree / reviewer / model / cost / token).

    Record pass/fail per checkpoint in the A5 execution summary. If any fails, do NOT advance — file a bug and route back to the relevant A5-NN plan.

    Resume signal: "approved — full suite green, all visual checkpoints (a)-(j) pass" or describe the failing checkpoint with the offending screenshot.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core project:: --quiet 2>&1 | tail -5 && cargo test --workspace --quiet 2>&1 | tail -5 && cargo build -p voss-app --quiet 2>&1 | tail -5 && pnpm --filter voss-app test 2>&1 | tail -10 && pnpm --filter voss-app exec tsc --noEmit -p . 2>&1 | tail -5 && pnpm --filter voss-app build 2>&1 | tail -10 && echo A5_FULL_GREEN</automated>
  </verify>
  <acceptance_criteria>
    - `cargo test -p voss-app-core project::` exits 0.
    - `cargo test --workspace` exits 0 (no regressions in prior phases).
    - `cargo build -p voss-app` exits 0.
    - `pnpm --filter voss-app test` exits 0 (all unit + integration green).
    - `pnpm --filter voss-app exec tsc --noEmit` exits 0.
    - `pnpm --filter voss-app build` exits 0.
    - Visual checkpoints (a)-(j) all pass on the dev machine.
    - `A5_FULL_GREEN` prints before phase verification.
  </acceptance_criteria>
  <done>A5 is fully verified, visually signed off, and ready for `/gsd:verify-work A5`.</done>
</task>

</tasks>

<verification>
Run the full command set in Task 3. All must exit 0. Then perform the visual sign-off.
</verification>

<success_criteria>
- WS-01 through WS-07 have acceptance coverage in a5-acceptance.test.tsx.
- SPEC AC #1..#11 each have at least one automated assertion or a documented deferral.
- E2E spec exists with the skip-deferred pattern; scenarios captured for future Linux CI.
- Full Rust + JS + tsc + build suite green.
- Manual visual verification confirms the SetupWindow, Titlebar swap, lazy .voss/, and D-13 pane preservation.
- L1 vocab discipline holds at the DOM level (no L2 tokens in chrome).
</success_criteria>

<output>
Create `.planning/phases/A5-voss-app-project-open/A5-06-SUMMARY.md` with: final test counts (cargo + vitest), the A5-VALIDATION.md status table snapshot, the visual checkpoint pass/fail record, screenshot links if captured, and any items proposed for follow-up (cwd thread-through into operations.ts, ⌘O accelerator, drag-drop onto app icon).
</output>
