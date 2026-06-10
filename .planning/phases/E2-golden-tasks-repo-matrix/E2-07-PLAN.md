---
phase: E2-golden-tasks-repo-matrix
plan: 07
type: execute
wave: 2
depends_on: ["E2-04"]
files_modified:
  - tests/eval/matrix/ts-01-analyze/task.toml
  - tests/eval/matrix/ts-03-approved-edit/task.toml
  - tests/eval/matrix/ts-04-validation/task.toml
autonomous: true
requirements: [EVGLD-02, EVGLD-03, EVGLD-04]
must_haves:
  truths:
    - "All 3 ts-* cells have a valid TaskSpec task.toml (extra=forbid: only the 9 valid fields, no lang field)"
    - "ts-01-analyze has a cognition gate: file_contains .voss/architecture.md text=package.json"
    - "ts-03-approved-edit renames add to sumTwo (camelCase) in src/calc.ts AND updates the src/calc.test.ts call site, with npm test green"
    - "ts-04-validation runs npm test as the native toolchain gate (node --experimental-strip-types --test)"
    - "No ts cell requires npm install or a global tsc"
  artifacts:
    - path: "tests/eval/matrix/ts-01-analyze/task.toml"
      provides: "Analyze cell with cognition file_contains package.json"
      contains: "package.json"
    - path: "tests/eval/matrix/ts-03-approved-edit/task.toml"
      provides: "Approved-edit cell: rename add to sumTwo in src + test"
      contains: "sumTwo"
    - path: "tests/eval/matrix/ts-04-validation/task.toml"
      provides: "Validation cell running npm test"
      contains: "npm test"
  key_links:
    - from: "tests/eval/matrix/ts-*/task.toml npm test check"
      to: "voss/eval/runner.py _run_checks (node:test built-in)"
      via: "cmd check runs npm test in the isolated copy; node:test needs no install"
      pattern: "npm test"
---

<objective>
Write the 3 TypeScript matrix `task.toml` files for the shape-sensitive cells (ts-01-analyze, ts-03-approved-edit, ts-04-validation) over the ESM `calc` project (plan 04). Behavioral gates run `npm test` (which invokes `node --experimental-strip-types --test`); the cognition gate asserts architecture.md names `package.json`. The rename target is camelCase `sumTwo` per RESEARCH Open Q2 (TypeScript idiom).

Purpose: Encodes EVGLD-02/03/04 for the TypeScript axis. Standard E1 TaskSpec — ZERO schema change; language is in the `ts-` prefix. approved-edit updates BOTH src/calc.ts and the src/calc.test.ts call site (the test imports `add` from ./calc.ts). The ExperimentalWarning on stderr does NOT fail the check (Pitfall 2: `_run_checks` keys on returncode).
Output: 3 `ts-*/task.toml` files, each a valid TaskSpec with at least one deterministic check.
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
<!-- Valid TaskSpec fields (extra="forbid"). No `lang` field — language is in the ts- prefix. -->
From voss/eval/suite.py:
  prompt (str, required) · mode ("plan"|"edit"|"auto", required) · rubric (str, required)
  judge_inputs · provider · model · auto_approve_edits · tools · checks
Check shapes: {type="cmd", run, timeout=60} · {type="file_exists", path} · {type="file_contains", path, text}
Loader (VERIFIED suite.py:57-70): load_task(task_dir) reads task_dir/"task.toml"; load_suite(Path("tests/eval/matrix"), suite="matrix").
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the 3 TypeScript shape-cell task.tomls (ts-01, ts-03, ts-04)</name>
  <files>tests/eval/matrix/ts-01-analyze/task.toml, tests/eval/matrix/ts-03-approved-edit/task.toml, tests/eval/matrix/ts-04-validation/task.toml</files>
  <read_first>
    - tests/eval/golden/01-analyze/task.toml (role-match analog — analyze field set + file_exists .voss/architecture.md)
    - tests/eval/golden/03-approved-edit/task.toml (role-match analog — approved-edit field set + old-name-absent grep idiom)
    - tests/eval/golden/04-validation/task.toml (role-match analog — validation cmd shape)
    - E2-PATTERNS.md lines 140-146 (ts-01-analyze block: file_contains package.json), lines 182-197 (ts-03 block: file_contains src/calc.ts sumTwo + old-name grep on src/calc.ts + npm test timeout=60), lines 212-218 (ts-04: npm test timeout=60)
    - E2-RESEARCH.md §Per-Cell Check Specifications lines 496-520 (cognition token TS=package.json; old-name grep idiom for function add) + Open Q2 lines 756-759 (camelCase sumTwo)
    - E2-RESEARCH.md Pitfall 2 lines 613-616 (Node ExperimentalWarning on stderr does NOT fail returncode-based check — no special handling)
  </read_first>
  <action>
    Write tests/eval/matrix/ts-01-analyze/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final","file_diff"]). Prompt: "Analyze this repository and write architecture.md describing what it does." Checks: a file_exists check on path ".voss/architecture.md"; a file_contains check on path ".voss/architecture.md" with text "package.json" (cognition gate EVGLD-04: names TypeScript tooling).

    Write tests/eval/matrix/ts-03-approved-edit/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final","file_diff"]). Prompt: "Rename the function add to sumTwo in src/calc.ts and update its call site in src/calc.test.ts." (BOTH files — the test imports add from ./calc.ts; camelCase sumTwo per Open Q2). Checks: a file_contains check on path "src/calc.ts" with text "sumTwo" (new name landed); a cmd check whose run is the literal old-name-absent command `! grep -q 'function add(' src/calc.ts`; a cmd check with run `npm test` and timeout=60 (suite green after edit — EVGLD-03 behavioral).

    Write tests/eval/matrix/ts-04-validation/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final"]). Prompt: "Run the project's test suite and report the exit code." Checks: a cmd check with run `npm test` and timeout=60 (native toolchain gate per D-02; node:test built-in, no install).

    Every file must include a `rubric` string. Use ONLY the 9 valid TaskSpec fields; no `lang` key (language is in the `ts-` prefix). Do NOT add any tsc check (tsc is not globally available) and do NOT add a pretest/install step.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_task; [load_task(Path('tests/eval/matrix')/d) for d in ['ts-01-analyze','ts-03-approved-edit','ts-04-validation']]"` exits 0
    - `grep -c package.json tests/eval/matrix/ts-01-analyze/task.toml` is at least 1 (cognition token)
    - `grep -c sumTwo tests/eval/matrix/ts-03-approved-edit/task.toml` is at least 1 and the file contains the literal old-name grep on src/calc.ts
    - `grep -c "npm test" tests/eval/matrix/ts-04-validation/task.toml` is at least 1
    - `grep -c "tsc\|npm install\|pretest" tests/eval/matrix/ts-01-analyze/task.toml tests/eval/matrix/ts-03-approved-edit/task.toml tests/eval/matrix/ts-04-validation/task.toml` equals 0 (no tsc gate, no install step)
    - `grep -c "^lang " tests/eval/matrix/ts-01-analyze/task.toml tests/eval/matrix/ts-03-approved-edit/task.toml tests/eval/matrix/ts-04-validation/task.toml` equals 0
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_task; [print(d, len(load_task(Path('tests/eval/matrix')/d).checks)) for d in ['ts-01-analyze','ts-03-approved-edit','ts-04-validation']]"</automated>
  </verify>
  <done>Three TypeScript shape task.tomls validate as TaskSpecs; ts-01 has the package.json cognition gate; ts-03 renames add to sumTwo in src AND test with npm test green; ts-04 runs npm test; no tsc/install; no lang field.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml npm test check → runner's isolated copy | `npm test` is developer-authored, committed; `_run_checks` runs it with cwd=the isolated fixture copy, never the repo root |
| node:test → fixture cwd | node runs only inside the temp copy; no third-party packages fetched (node:test is built-in) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-16 | Tampering | node executing arbitrary package code | mitigate | The ts fixture (plan 04) has no dependencies and no install hook; `npm test` runs only the built-in node:test in the isolated temp copy. |
| T-E2-17 | Spoofing | vacuous judge-only pass (no checks) | mitigate | Every ts-* cell has at least one deterministic check; plan-01 `test_matrix_all_cells_have_checks` enforces it (Pitfall 6). |
| T-E2-18 | Tampering | check running in repo root not fixture copy | mitigate | `_run_checks` sets cwd to the `_prepare_fixture` temp copy; all check paths are fixture-relative. |
| T-E2-SC | Tampering | npm/pip/cargo installs | mitigate | No tsc check, no `npm install`, no `pretest` hook — verified by grep (acceptance criterion). |
</threat_model>

<verification>
- All 3 ts-* task.tomls validate as TaskSpecs under extra="forbid" (no lang field).
- ts-01 cognition gate (package.json); ts-03 behavioral gates with both-file rename (camelCase sumTwo); ts-04 native npm test.
- No tsc gate, no install step.
</verification>

<success_criteria>
- 3 `tests/eval/matrix/ts-*/task.toml` files exist and load via load_suite(suite="matrix")
- EVGLD-03 (behavioral) + EVGLD-04 (cognition) encoded for TypeScript; Open Q2 resolved (camelCase sumTwo)
- Zero TaskSpec schema change; no global tsc dependency
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-07-SUMMARY.md` when done
</output>
