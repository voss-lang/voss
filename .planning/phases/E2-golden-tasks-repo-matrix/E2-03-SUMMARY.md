---
phase: E2-golden-tasks-repo-matrix
plan: 03
subsystem: testing
tags: [rust, cargo, eval, fixtures, matrix]

# Dependency graph
requires:
  - phase: E1-eval-runner
    provides: "_prepare_fixture isolated temp-dir copy that the rust cmd checks rely on"
provides:
  - "Three self-contained Rust calc crate fixtures (rust-01-analyze, rust-03-approved-edit, rust-04-validation)"
  - "Editable pub fn add() rename target in src/lib.rs for approved-edit (plan 06)"
  - "Integration-test call site (use calc::add) in tests/test_add.rs that approved-edit must also update (Open Q1)"
affects: [E2-06 task.toml authoring, eval matrix runner]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Rust fixture = std-only 3-file crate, no [workspace], no [dependencies]; cargo only ever runs in isolated temp copy"]

key-files:
  created:
    - tests/eval/matrix/rust-01-analyze/fixture/Cargo.toml
    - tests/eval/matrix/rust-01-analyze/fixture/src/lib.rs
    - tests/eval/matrix/rust-01-analyze/fixture/tests/test_add.rs
    - tests/eval/matrix/rust-03-approved-edit/fixture/Cargo.toml
    - tests/eval/matrix/rust-03-approved-edit/fixture/src/lib.rs
    - tests/eval/matrix/rust-03-approved-edit/fixture/tests/test_add.rs
    - tests/eval/matrix/rust-04-validation/fixture/Cargo.toml
    - tests/eval/matrix/rust-04-validation/fixture/src/lib.rs
    - tests/eval/matrix/rust-04-validation/fixture/tests/test_add.rs
  modified: []

key-decisions:
  - "Verified cargo test via temp-dir copy, not in-repo: fixtures sit under the Voss cargo workspace, so in-place cargo errors with 'believes it's in a workspace' — exactly Pitfall 4; runner isolation (_prepare_fixture) is what makes the no-[workspace] manifest correct"

patterns-established:
  - "Matrix shape fixtures are byte-identical across cells; per-cell behavior lives in task.toml (plan 06)"

requirements-completed: [EVGLD-01]

# Metrics
duration: 5min
completed: 2026-06-11
---

# Phase E2 Plan 03: Rust Matrix Fixtures Summary

**Three byte-identical self-contained Rust calc crates (Cargo.toml + src/lib.rs + tests/test_add.rs) with editable pub fn add() and calc::add integration-test call site; cargo test green in isolated temp copies**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-06-11
- **Tasks:** 1
- **Files modified:** 9 created

## Accomplishments
- rust-01-analyze, rust-03-approved-edit, rust-04-validation fixtures built as identical 3-file `calc` crates
- `cargo test --quiet` exits 0 in each (verified in isolated temp copies, mirroring runner `_prepare_fixture`)
- No `[workspace]`, no `[dependencies]` — std-only, zero registry fetch, no build.rs (T-E2-05/06 mitigations hold)
- `tests/test_add.rs` provides the `use calc::add` call site approved-edit must update alongside `src/lib.rs` (Open Q1 resolved)

## Task Commits

1. **Task 1: Build the three Rust shape fixtures** - `1832b50` (test)

## Files Created/Modified
- `tests/eval/matrix/rust-*/fixture/Cargo.toml` - `[package] name = "calc"`, edition 2021, no `[workspace]`
- `tests/eval/matrix/rust-*/fixture/src/lib.rs` - `pub fn add(a: i32, b: i32) -> i32` (approved-edit rename target)
- `tests/eval/matrix/rust-*/fixture/tests/test_add.rs` - integration test importing `calc::add`

## Decisions Made
- Verification ran in temp-dir copies instead of the plan's in-place `cd fixture && cargo test`: in-repo invocation fails because the Voss root `Cargo.toml` workspace claims the package ("current package believes it's in a workspace"). This is Pitfall 4 working as documented — the fixture intentionally omits `[workspace]` because the runner only ever invokes cargo inside an isolated temp copy.

## Deviations from Plan

**1. [Verify command adjustment] Temp-copy verification instead of in-place cargo test**
- **Found during:** Task 1 verification
- **Issue:** Plan's verify command (`cd tests/eval/matrix/$d/fixture && cargo test`) fails in-repo due to Voss workspace inheritance; also macOS has no `timeout` binary
- **Fix:** Copied each fixture to `mktemp -d` and ran `cargo test --quiet` there — identical to how the runner executes (E1 `_prepare_fixture`); all three green
- **Files modified:** none
- **Verification:** ALL_GREEN, 1 test passing per crate

---

**Total deviations:** 1 (verification environment only — fixture content exactly as planned)
**Impact on plan:** None on artifacts; confirms the isolation requirement is real, not theoretical.

## Issues Encountered
None beyond the expected in-repo workspace error documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Rust shape fixtures ready for plan 06 (task.toml cmd checks with `timeout = 120`)
- Approved-edit cell has both definition site (src/lib.rs) and call site (tests/test_add.rs)

---
*Phase: E2-golden-tasks-repo-matrix*
*Completed: 2026-06-11*
