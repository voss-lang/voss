---
phase: A5
slug: voss-app-project-open
status: automated-green-visual-pending
created: 2026-05-20
---

# Phase A5 - Validation Strategy

## Requirement-to-test map

| WS-NN | SPEC AC # | Test File | Test Name | Status |
|---|---:|---|---|---|
| WS-01 | #2 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-01 — folder picker opens a local project > sets the active project and mounts the grid after a picked folder` | green |
| WS-01 | #2 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-01 — folder picker opens a local project > uses the Tauri directory picker contract` | green |
| WS-01 | deferred | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-01 — folder picker opens a local project > documents that Cmd+O is outside the locked A5 picker contract` | deferred to A7 |
| WS-02 | #3 | `crates/voss-app-core/src/project.rs` | `update_recents_moves_existing_path_to_front_without_duplicate` | green |
| WS-02 | #8 | `crates/voss-app-core/src/project.rs` | `update_recents_caps_at_five_newest_first` / `open_project_caps_recents_at_5` | green |
| WS-02 | #8 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-02 — recents round-trip through global app storage > listRecents reads the Rust recents command` | green |
| WS-03 | #9 | `crates/voss-app-core/src/project.rs` | `open_project_does_not_create_voss_directory` | green |
| WS-03 | #9 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-03 — project open stays lazy with respect to .voss > maps the lazy .voss invariant to the Rust filesystem test` | green |
| WS-04 | #5 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-04 — project metadata exposes name and git branch > ProjectInfo carries path, folder basename, and nullable gitBranch` | green |
| WS-04 | #6 | `crates/voss-app-core/src/project.rs` | `open_project_returns_current_branch_for_git_dir` / `open_project_returns_none_branch_for_non_git_dir` | green |
| WS-05 | #1 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-05 — project-less mode is an explicit setup choice > shows setup first, then starts grid without a project path` | green |
| WS-05 | #7 | `apps/voss-app/src/__tests__/App.test.tsx` | `App — setup branch > start without project mounts GridRoot and keeps the titlebar fallback` | green |
| WS-06 | #7 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-06 — pane cwd defaults come from Rust-resolved project cwd > defaultCwd delegates both project and project-less cwd resolution to Tauri` | green |
| WS-06 | #7 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-06 — pane cwd defaults come from Rust-resolved project cwd > threads the open project path into GridRoot as the future-pane cwd` | green |
| WS-06 | #7 | `apps/voss-app/src/grid/operations.ts` | `splitFocused` / `forkFocused` consuming `projectCwd` for new panes | deferred to A6 follow-up |
| WS-07 | #4 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-07 — project switching path exists before palette UI lands > open recent updates project metadata without remounting the grid` | green |
| WS-07 | #10 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-07 — project switching path exists before palette UI lands > attempts default layout load and ignores failure while keeping the project open` | green |
| WS-07 | #11 | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `WS-07 — project switching path exists before palette UI lands > open recent updates project metadata without remounting the grid` | green |
| WS-07 | deferred | A7 command palette | `Open recent` / `Close project` palette UI | deferred to A7 |
| L2 vocab | n/a | `apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx` | `A5 final L2-vocab gate — setup and titlebar chrome stay L1` | green |

## Final command list

Run these before `/gsd:verify-work A5`:

```bash
cargo test -p voss-app-core project:: -- --nocapture
cargo test --workspace
pnpm --filter voss-app test
pnpm --filter voss-app exec tsc --noEmit -p .
cargo build -p voss-app
pnpm --filter voss-app build
```

Task 1 focused verification:

```bash
cd apps/voss-app && pnpm vitest run src/project/__tests__/a5-acceptance.test.tsx --reporter=dot
grep -q 'WS-01' apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx
grep -q 'WS-07' apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx
grep -q 'SPEC AC #1' apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx
grep -q 'SPEC AC #11' apps/voss-app/src/project/__tests__/a5-acceptance.test.tsx
grep -q 'WS-01' .planning/phases/A5-voss-app-project-open/A5-VALIDATION.md
grep -q 'WS-07' .planning/phases/A5-voss-app-project-open/A5-VALIDATION.md
echo A5_ACCEPTANCE_OK
```

## Deferred items

| Item | Reason | Owning phase |
|---|---|---|
| `Cmd+O` accelerator | A5-CONTEXT D-05 locks folder picker as the contract; accelerator was planner discretion, not SPEC-required. | A7 |
| Command palette `Open recent` / `Close project` UI | SPEC explicitly assigns palette entries to the command palette phase. A5 proves the project-change path exists via setup recents. | A7 |
| Drag-drop folder onto app icon | ROADMAP mentioned it, but A5-SPEC moved it out of scope. | A11 or later polish |
| Operation-level cwd injection into `splitFocused` / `forkFocused` | A5 currently threads `projectCwd` to `GridRoot`; `operations.ts` still creates default panes without consuming that cwd. | A6 follow-up |
| E2E project-open live execution | `apps/voss-app/e2e/project-open.spec.ts` exists and loads, but its seven scenarios are intentionally skipped because macOS cannot drive live Tauri WebDriver and Playwright cannot drive the native folder dialog without a future JS dialog-mock seam. | A10 / Linux CI |

## Visual checkpoint plan

1. Launch app with no active project. Expect `SetupWindow` visible and titlebar fallback `Voss ADE`.
2. Click `Open project`. Pick a temporary directory.
3. Expect setup surface to disappear, grid to mount, and titlebar to show the temp directory basename.
4. Verify `<temp>/.voss/` does not exist after open.
5. Open a second temp directory from recents or picker. Expect titlebar to swap and existing pane identity/scrollback to remain intact.
6. Start without project in a fresh launch. Expect grid mount, `Voss ADE` titlebar fallback, and future panes to use `$HOME`.
7. Relaunch after project-less mode. Expect setup window again because `projectLessAccepted` is session-only.
8. Open a git repository. Verify `gitBranch` is present in project metadata; A5 does not render branch in the UI.
9. Inspect setup window and titlebar styling against Variant B tokens. No raw user-facing `.voss` copy should appear.
10. Confirm app chrome contains no L2 vocabulary: `agent`, `worktree`, `reviewer`, `model`, `cost`, or `token`. User-supplied project names are excluded from this check.

## Automated closeout

2026-05-20:

- `cargo test -p voss-app-core project:: --quiet` passed: 24 project tests.
- `cargo test --workspace --quiet` passed; the run includes one intentionally ignored macOS Keychain test.
- `cargo build -p voss-app --quiet` passed.
- `pnpm --filter voss-app test` passed: 20 files / 224 tests.
- `pnpm --filter voss-app exec tsc --noEmit -p .` passed.
- `pnpm --filter voss-app build` passed.
- `pnpm playwright test project-open` loaded the A5 e2e spec and reported 7 skipped scenarios.
- `A5_FULL_GREEN` printed for the automated gate.

Manual visual checkpoint remains pending until a human runs the checklist above in the Tauri app.
