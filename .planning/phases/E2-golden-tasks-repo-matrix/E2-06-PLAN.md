---
phase: E2-golden-tasks-repo-matrix
plan: 06
type: execute
wave: 2
depends_on: ["E2-03"]
files_modified:
  - tests/eval/matrix/rust-01-analyze/task.toml
  - tests/eval/matrix/rust-03-approved-edit/task.toml
  - tests/eval/matrix/rust-04-validation/task.toml
autonomous: true
requirements: [EVGLD-02, EVGLD-03, EVGLD-04]
must_haves:
  truths:
    - "All 3 rust-* cells have a valid TaskSpec task.toml (extra=forbid: only the 9 valid fields, no lang field)"
    - "rust-01-analyze has a cognition gate: file_contains .voss/architecture.md text=Cargo.toml"
    - "rust-03-approved-edit renames add to sum_two in src/lib.rs AND updates the tests/test_add.rs call site, with cargo test green"
    - "rust-04-validation runs cargo test --quiet as the native toolchain gate"
    - "Every rust cargo cmd check sets timeout=120 (cargo cold compile, RESEARCH Pitfall 1)"
  artifacts:
    - path: "tests/eval/matrix/rust-01-analyze/task.toml"
      provides: "Analyze cell with cognition file_contains Cargo.toml"
      contains: "Cargo.toml"
    - path: "tests/eval/matrix/rust-03-approved-edit/task.toml"
      provides: "Approved-edit cell: rename add to sum_two in lib + test"
      contains: "sum_two"
    - path: "tests/eval/matrix/rust-04-validation/task.toml"
      provides: "Validation cell running cargo test with timeout 120"
      contains: "cargo test"
  key_links:
    - from: "tests/eval/matrix/rust-*/task.toml cargo test check"
      to: "voss/eval/runner.py _run_checks (timeout honored)"
      via: "cmd check timeout=120 to survive cargo cold compile in the isolated copy"
      pattern: "timeout = 120"
---

<objective>
Write the 3 Rust matrix `task.toml` files for the shape-sensitive cells (rust-01-analyze, rust-03-approved-edit, rust-04-validation) over the self-contained `calc` crate (plan 03). Behavioral gates run `cargo test --quiet`; the cognition gate asserts architecture.md names `Cargo.toml`. Every cargo cmd check sets `timeout = 120` because a fresh fixture compiles cold (RESEARCH Pitfall 1: 8-20s, default 60s false-fails).

Purpose: Encodes EVGLD-02/03/04 for the Rust axis. Standard E1 TaskSpec — ZERO schema change; language is in the `rust-` prefix. Resolves RESEARCH Open Q1: approved-edit updates BOTH src/lib.rs and the tests/test_add.rs call site (the integration test imports `calc::add`, so renaming only lib.rs would break compilation).
Output: 3 `rust-*/task.toml` files, each a valid TaskSpec with at least one deterministic check and cargo checks at timeout=120.
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

<interfaces>
<!-- Valid TaskSpec fields (extra="forbid"). No `lang` field — language is in the rust- prefix. -->
From voss/eval/suite.py:
  prompt (str, required) · mode ("plan"|"edit"|"auto", required) · rubric (str, required)
  judge_inputs · provider · model · auto_approve_edits · tools · checks
Check shapes: {type="cmd", run, timeout=60} · {type="file_exists", path} · {type="file_contains", path, text}
Loader (VERIFIED suite.py:57-70): load_task(task_dir) reads task_dir/"task.toml"; load_suite(Path("tests/eval/matrix"), suite="matrix").
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the 3 Rust shape-cell task.tomls (rust-01, rust-03, rust-04)</name>
  <files>tests/eval/matrix/rust-01-analyze/task.toml, tests/eval/matrix/rust-03-approved-edit/task.toml, tests/eval/matrix/rust-04-validation/task.toml</files>
  <read_first>
    - tests/eval/golden/01-analyze/task.toml (role-match analog — analyze field set + file_exists .voss/architecture.md)
    - tests/eval/golden/03-approved-edit/task.toml (role-match analog — approved-edit field set + old-name-absent grep idiom)
    - tests/eval/golden/04-validation/task.toml (role-match analog — validation cmd shape)
    - E2-PATTERNS.md lines 123-138 (rust-01-analyze block: file_contains Cargo.toml), lines 165-180 (rust-03 block: file_contains src/lib.rs sum_two + old-name grep on src/lib.rs + cargo test timeout=120), lines 206-210 (rust-04: cargo test timeout=120)
    - E2-RESEARCH.md §Per-Cell Check Specifications lines 496-520 (cognition token Rust=Cargo.toml; the old-name grep idiom for fn add)
    - E2-RESEARCH.md Pitfall 1 lines 607-611 (cargo cold compile → timeout=120 mandatory) + Open Q1 lines 751-754 (prompt must update both src/lib.rs and tests/test_add.rs)
  </read_first>
  <action>
    Write tests/eval/matrix/rust-01-analyze/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final","file_diff"]). Prompt: "Analyze this repository and write architecture.md describing what it does." Checks: a file_exists check on path ".voss/architecture.md"; a file_contains check on path ".voss/architecture.md" with text "Cargo.toml" (cognition gate EVGLD-04: names Rust tooling).

    Write tests/eval/matrix/rust-03-approved-edit/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final","file_diff"]). Prompt: "Rename the function add to sum_two in src/lib.rs and update its call site in tests/test_add.rs." (BOTH files — the integration test imports calc::add; renaming only lib.rs breaks the build, Open Q1). Checks: a file_contains check on path "src/lib.rs" with text "sum_two" (new name landed); a cmd check whose run is the literal old-name-absent command `! grep -q 'fn add(' src/lib.rs`; a cmd check with run `cargo test --quiet` and timeout=120 (suite green after edit — EVGLD-03 behavioral; the timeout MUST be 120 for cold compile).

    Write tests/eval/matrix/rust-04-validation/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final"]). Prompt: "Run the project's test suite and report the exit code." Checks: a cmd check with run `cargo test --quiet` and timeout=120 (native toolchain gate per D-02).

    Every file must include a `rubric` string. Use ONLY the 9 valid TaskSpec fields; no `lang` key (language is in the `rust-` prefix). Every cargo cmd check MUST set `timeout = 120`.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_task; [load_task(Path('tests/eval/matrix')/d) for d in ['rust-01-analyze','rust-03-approved-edit','rust-04-validation']]"` exits 0
    - `grep -c Cargo.toml tests/eval/matrix/rust-01-analyze/task.toml` is at least 1 (cognition token)
    - `grep -c sum_two tests/eval/matrix/rust-03-approved-edit/task.toml` is at least 1 and the file contains the literal old-name grep on src/lib.rs
    - `grep -c "cargo test" tests/eval/matrix/rust-04-validation/task.toml` is at least 1
    - `grep -rc "timeout = 120" tests/eval/matrix/rust-03-approved-edit/task.toml tests/eval/matrix/rust-04-validation/task.toml` shows timeout=120 on the cargo checks (rust-03 has at least 1, rust-04 has exactly 1); the verify command below confirms no cargo check uses the default 60
    - `grep -c "^lang " tests/eval/matrix/rust-01-analyze/task.toml tests/eval/matrix/rust-03-approved-edit/task.toml tests/eval/matrix/rust-04-validation/task.toml` equals 0
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_matrix_suite.py -k "cell_ids or all_cells_have_checks or cognition_token" -q</automated>
  </verify>
  <done>Three Rust shape task.tomls validate as TaskSpecs; rust-01 has the Cargo.toml cognition gate; rust-03 renames add to sum_two in lib AND test with cargo test green; rust-04 runs cargo test; all cargo checks at timeout=120; no lang field.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml cargo check → runner's isolated copy | `cargo test` is developer-authored, committed; `_run_checks` runs it with cwd=the isolated fixture copy, never the repo root or the frozen `crates/` workspace |
| cargo cmd check timeout → fixture cwd | The 120s timeout bounds the cold compile; no parent Cargo.toml/workspace reachable from the temp copy |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-13 | Tampering | cargo test executing arbitrary build code | mitigate | The rust fixture (plan 03) is std-only with no dependencies/build.rs; cargo test runs only in the isolated temp copy, never the Voss `crates/` workspace. |
| T-E2-14 | Denial | cargo cold-compile timeout false-fail | mitigate | Every cargo cmd check sets `timeout = 120` (Pitfall 1); verified by grep + the suite-test gate. |
| T-E2-15 | Spoofing | vacuous judge-only pass (no checks) | mitigate | Every rust-* cell has at least one deterministic check; plan-01 `test_matrix_all_cells_have_checks` enforces it (Pitfall 6). |
| T-E2-SC | Tampering | npm/pip/cargo installs | n/a | No package installs added; the fixture crate has no `[dependencies]` (no registry fetch). |
</threat_model>

<verification>
- All 3 rust-* task.tomls validate as TaskSpecs under extra="forbid" (no lang field).
- rust-01 cognition gate (Cargo.toml); rust-03 behavioral gates with both-file rename; rust-04 native cargo test.
- Every cargo cmd check sets timeout=120 (Pitfall 1).
</verification>

<success_criteria>
- 3 `tests/eval/matrix/rust-*/task.toml` files exist and load via load_suite(suite="matrix")
- EVGLD-03 (behavioral) + EVGLD-04 (cognition) encoded for Rust; Open Q1 resolved (both-file rename)
- Zero TaskSpec schema change; cargo timeout=120 throughout
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-06-SUMMARY.md` when done
</output>
