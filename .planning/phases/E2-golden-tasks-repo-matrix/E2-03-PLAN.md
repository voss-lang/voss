---
phase: E2-golden-tasks-repo-matrix
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/eval/matrix/rust-01-analyze/fixture/Cargo.toml
  - tests/eval/matrix/rust-01-analyze/fixture/src/lib.rs
  - tests/eval/matrix/rust-01-analyze/fixture/tests/test_add.rs
  - tests/eval/matrix/rust-03-approved-edit/fixture/Cargo.toml
  - tests/eval/matrix/rust-03-approved-edit/fixture/src/lib.rs
  - tests/eval/matrix/rust-03-approved-edit/fixture/tests/test_add.rs
  - tests/eval/matrix/rust-04-validation/fixture/Cargo.toml
  - tests/eval/matrix/rust-04-validation/fixture/src/lib.rs
  - tests/eval/matrix/rust-04-validation/fixture/tests/test_add.rs
autonomous: true
requirements: [EVGLD-01]
must_haves:
  truths:
    - "Each Rust shape fixture (rust-01/03/04) is a self-contained 3-file crate (Cargo.toml + src/lib.rs + tests/test_add.rs) with an editable pub fn add()"
    - "cargo test --quiet exits 0 inside any of the three fixtures (cold compile within 120s)"
    - "No Cargo.toml has a [workspace] section (avoids inheriting the Voss repo workspace)"
  artifacts:
    - path: "tests/eval/matrix/rust-01-analyze/fixture/Cargo.toml"
      provides: "Self-contained crate manifest with no [workspace]"
      contains: "name = \"calc\""
    - path: "tests/eval/matrix/rust-03-approved-edit/fixture/src/lib.rs"
      provides: "Editable pub fn add() rename target"
      contains: "pub fn add"
    - path: "tests/eval/matrix/rust-04-validation/fixture/tests/test_add.rs"
      provides: "Integration test importing calc::add"
      contains: "use calc::add"
  key_links:
    - from: "tests/eval/matrix/rust-*/fixture/tests/test_add.rs"
      to: "tests/eval/matrix/rust-*/fixture/src/lib.rs"
      via: "use calc::add (integration test of the lib crate)"
      pattern: "use calc::add"
---

<objective>
Build the three Rust matrix fixture directories under `tests/eval/matrix/rust-*/fixture/`. Each shape-sensitive cell (rust-01-analyze, rust-03-approved-edit, rust-04-validation) gets an identical self-contained `calc` crate: `Cargo.toml` (no `[workspace]`) + `src/lib.rs` with an editable `pub fn add()` + `tests/test_add.rs` integration test importing `calc::add`. Rust has no language-agnostic cells (D-02: only analyze/approved-edit/validation run on rust).

Purpose: Provides the Rust project shape the runner copies + `cargo test`-checks in an isolated temp dir (EVGLD-01, D-01). The integration-test layout keeps `src/lib.rs` as the sole edit target so approved-edit (plan 06) has a clean rename surface.
Output: Three `rust-*/fixture/` crates, each self-contained and ≤ 5 files (D-01 limit, 3 files each).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-RESEARCH.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-PATTERNS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build the three Rust shape fixtures (rust-01, rust-03, rust-04)</name>
  <files>tests/eval/matrix/rust-01-analyze/fixture/{Cargo.toml,src/lib.rs,tests/test_add.rs}, tests/eval/matrix/rust-03-approved-edit/fixture/{Cargo.toml,src/lib.rs,tests/test_add.rs}, tests/eval/matrix/rust-04-validation/fixture/{Cargo.toml,src/lib.rs,tests/test_add.rs}</files>
  <read_first>
    - E2-RESEARCH.md §Rust Fixture lines 387-420 (VERIFIED locally: `cargo test --quiet` passes in isolated temp dir; integration test in tests/ keeps src/lib.rs clean; cold compile ~3-20s → timeout=120 needed on the cmd check)
    - E2-PATTERNS.md §`tests/eval/matrix/rust-*/fixture/` lines 287-316 (exact file bodies; Cargo.toml has NO [workspace])
    - E2-RESEARCH.md Pitfall 4 lines 623-627 (cargo workspace inheritance — isolated temp dir means no parent Cargo.toml, but the fixture itself must still omit [workspace])
    - E2-RESEARCH.md Open Q1 lines 751-754 (approved-edit must update BOTH src/lib.rs and tests/test_add.rs since the test imports calc::add — this informs the test-file call-site placement here)
  </read_first>
  <action>
    Create three IDENTICAL self-contained crate trees (one per shape cell). For each of rust-01-analyze, rust-03-approved-edit, rust-04-validation: write `fixture/Cargo.toml` with a `[package]` table — `name = "calc"`, `version = "0.1.0"`, `edition = "2021"` — and explicitly NO `[workspace]` section and no `[dependencies]` (std-only, zero registry fetch). Write `fixture/src/lib.rs` defining `pub fn add(a: i32, b: i32) -> i32 { a + b }` (this is the approved-edit rename target → `sum_two`). Write `fixture/tests/test_add.rs` as an integration test: `use calc::add;` then `#[test] fn test_add() { assert_eq!(add(1, 2), 3); }`. The integration-test placement (tests/, not a `#[cfg(test)]` mod inside lib.rs) keeps `src/lib.rs` as the ONLY definition site — and makes the test file the call site that approved-edit must also update (Open Q1). The three crates are byte-identical; per-cell behavior lives in the task.toml (plan 06).
  </action>
  <acceptance_criteria>
    - For each of the three dirs: `cargo test --quiet` exits 0 within 120s (run via the verify command below)
    - `grep -L "\[workspace\]" tests/eval/matrix/rust-0{1,3,4}-*/fixture/Cargo.toml` lists all three (none contain [workspace])
    - `grep -l "pub fn add" tests/eval/matrix/rust-0{1,3,4}-*/fixture/src/lib.rs` lists all three
    - Each fixture dir contains exactly 3 files: `find tests/eval/matrix/rust-01-analyze/fixture -type f | wc -l` equals 3
    - `grep -c "use calc::add" tests/eval/matrix/rust-03-approved-edit/fixture/tests/test_add.rs` equals 1 (call site present for the edit)
  </acceptance_criteria>
  <verify>
    <automated>for d in rust-01-analyze rust-03-approved-edit rust-04-validation; do (cd tests/eval/matrix/$d/fixture && timeout 120 cargo test --quiet) || exit 1; done</automated>
  </verify>
  <done>All three Rust shape fixtures exist as self-contained 3-file crates; cargo test passes in each within 120s; no [workspace]; editable pub fn add() present; integration-test call site in tests/test_add.rs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| fixture crate → runner's isolated copy | Crate is static, committed; copied to a temp dir before any cargo invocation (E1 `_prepare_fixture`) |
| cargo test → fixture copy cwd | `cargo test` executes ONLY in the isolated temp copy, never the Voss repo root; no parent Cargo.toml/workspace reachable from /tmp |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-05 | Tampering | cargo executing arbitrary build code | mitigate | Crate is std-only with NO `[dependencies]` — zero registry fetch, no build.rs, no proc-macros; cargo test runs in the isolated temp copy only. |
| T-E2-06 | Tampering | cargo workspace inheritance into repo | mitigate | Fixture Cargo.toml omits `[workspace]`; `_prepare_fixture` copies to /tmp where no parent Cargo.toml exists (Pitfall 4). |
| T-E2-07 | Denial | cargo cold-compile timeout | mitigate | Documented requirement: the rust cmd checks (plan 06) set `timeout = 120`; this plan only proves the fixture compiles within that bound. |
</threat_model>

<verification>
- All three crates pass `cargo test --quiet` in their isolated dirs within 120s.
- No Cargo.toml contains `[workspace]`; no `[dependencies]` (std-only).
- Each fixture ≤ 5 files; integration test imports calc::add (call site for approved-edit).
</verification>

<success_criteria>
- Three `tests/eval/matrix/rust-*/fixture/` crates exist
- Each is a self-contained 3-file calc crate with editable `pub fn add()`
- cargo test green in each (cold compile < 120s); EVGLD-01 Rust shape satisfied
- tests/test_add.rs provides the approved-edit call site (Open Q1 resolved)
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-03-SUMMARY.md` when done
</output>
