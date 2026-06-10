---
phase: E1-eval-substrate
plan: 04
type: execute
wave: 3
depends_on: [E1-01, E1-03]
files_modified:
  - tests/eval/golden/01-analyze/task.toml
  - tests/eval/golden/02-plan-only/task.toml
  - tests/eval/golden/03-approved-edit/task.toml
  - tests/eval/golden/04-validation/task.toml
  - tests/eval/golden/05-resume/task.toml
  - tests/eval/golden/06-fetch-summarize/task.toml
  - tests/eval/test_golden_checks.py
autonomous: true
requirements: [EVSUB-03]
must_haves:
  truths:
    - "Each of the 6 golden tasks has at least one deterministic check matching its contract"
    - "load_suite returns 6 tasks each with non-empty checks"
    - "A full stub-mode suite run executes all checks without error (no crash; pass/fail recorded)"
  artifacts:
    - path: "tests/eval/golden/01-analyze/task.toml"
      provides: "file_exists .voss/architecture.md check"
      contains: "[[checks]]"
    - path: "tests/eval/golden/03-approved-edit/task.toml"
      provides: "file_contains sum_two present (calc.py + main.py) + cmd gate for old name removed"
      contains: "sum_two"
    - path: "tests/eval/golden/04-validation/task.toml"
      provides: "cmd voss check sample.voss exits 0"
      contains: "[[checks]]"
    - path: "tests/eval/test_golden_checks.py"
      provides: "asserts all 6 tasks have non-empty checks + stub suite runs checks cleanly"
  key_links:
    - from: "tests/eval/golden/*/task.toml [[checks]]"
      to: "voss.eval.suite.load_suite"
      via: "tomllib array-of-tables → AnyCheck validation"
      pattern: "\\[\\[checks\\]\\]"
    - from: "tests/eval/test_golden_checks.py"
      to: "voss.eval.suite.load_suite"
      via: "assert every spec.checks non-empty"
      pattern: "spec.checks"
---

<objective>
Retrofit deterministic `[[checks]]` onto all 6 existing golden task.toml files (EVSUB-03), each matching the task's contract. Depends on E1-01 (schema accepts `checks`) and E1-03 (executor wired into the suite loop so retrofit checks run and record). Add a coverage test asserting all 6 tasks carry non-empty checks and that a full stub-mode suite run executes the checks without error.

Purpose: EVSUB-03 — convert the 6 rubric-only golden tasks into hybrid-scored tasks with concrete deterministic gates. These gates are what the EVSUB-07 live proof run measures (≥5/6 gate_pass).
Output: 6 task.toml files with grounded checks + a coverage test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/E1-eval-substrate/E1-SPEC.md
@.planning/phases/E1-eval-substrate/E1-PATTERNS.md
@.planning/phases/M5-eval-and-distribution-prep/M5-05-SUMMARY.md

<interfaces>
<!-- TOML array-of-tables form (one [[checks]] block per check). Each validates via AnyCheck (E1-01). -->
<!-- Per-task grounded check contracts (verified against the actual fixtures): -->
01-analyze:  prompt writes .voss/architecture.md (mode=edit, auto_approve)
  => file_exists path=".voss/architecture.md"
02-plan-only: plan mode, MUST NOT modify files
  => cmd run="git diff --quiet HEAD"  (exit 0 == no modifications)
03-approved-edit: rename add()->sum_two() in calc.py + update call site in main.py
  => file_contains calc.py "sum_two" ; file_contains main.py "sum_two" ;
     cmd run="! grep -q 'def add(' calc.py"  (gates the old name is gone)
04-validation: agent runs `voss check sample.voss`; the deterministic gate runs it directly
  => cmd run="python -m voss.cli check sample.voss"  (VERIFIED exits 0 on the fixture sample.voss)
05-resume: resume task; robust two-turns deterministic check needs session introspection that is
     fragile across stub/live. SPEC §3 permits a judge-only fallback for 05 (PATTERNS line 523).
  => cmd run="test -f notes.txt"  (cheap fixture-intrinsic gate so the task is non-empty per EVSUB-03;
     judge carries resume correctness)
06-fetch-summarize: writes summary.txt mentioning Example/Domain
  => file_exists path="summary.txt" ; file_contains path="summary.txt" text="Example"
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Retrofit [[checks]] onto all 6 golden task.toml files</name>
  <read_first>
    - tests/eval/golden/01-analyze/task.toml AND its fixture/ (README.md, main.py)
    - tests/eval/golden/02-plan-only/task.toml AND fixture/calc.py
    - tests/eval/golden/03-approved-edit/task.toml AND fixture/calc.py + fixture/main.py (current: def add(a,b); from calc import add; print(add(1,2)))
    - tests/eval/golden/04-validation/task.toml AND fixture/sample.voss (voss check exits 0 — verified)
    - tests/eval/golden/05-resume/task.toml AND fixture/notes.txt
    - tests/eval/golden/06-fetch-summarize/task.toml AND fixture/README.md
    - voss/eval/suite.py (the AnyCheck union from E1-01 — confirm field names: cmd.run, file_exists.path, file_contains.path/text)
    - .planning/phases/E1-eval-substrate/E1-PATTERNS.md (golden task.toml section lines 494-525 — TOML [[checks]] syntax + per-task contracts)
  </read_first>
  <action>
    Append `[[checks]]` blocks to each task.toml (do NOT modify prompt/mode/rubric/judge_inputs/auto_approve_edits — checks are additive). Use exactly these grounded checks:

    01-analyze: one check `type="file_exists"` `path=".voss/architecture.md"`.

    02-plan-only: one check `type="cmd"` `run="git diff --quiet HEAD"` (exit 0 means no file modifications — the plan-mode no-writes contract).

    03-approved-edit: three checks — `type="file_contains"` `path="calc.py"` `text="sum_two"`; `type="file_contains"` `path="main.py"` `text="sum_two"`; `type="cmd"` `run="! grep -q 'def add(' calc.py"` (gates that the old name is gone — rename completeness).

    04-validation: one check `type="cmd"` `run="python -m voss.cli check sample.voss"` (verified exits 0 on the fixture).

    05-resume: one check `type="cmd"` `run="test -f notes.txt"` (cheap fixture-intrinsic gate satisfying the EVSUB-03 non-empty requirement; resume correctness stays with the judge per SPEC §3 fallback allowance — PATTERNS line 523).

    06-fetch-summarize: two checks — `type="file_exists"` `path="summary.txt"`; `type="file_contains"` `path="summary.txt"` `text="Example"`.

    Keep TOML valid (tomllib must parse). The `[[checks]]` arrays append cleanly after the existing scalar/string fields.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_suite; tasks=load_suite(Path('tests/eval/golden'), suite='golden'); assert len(tasks)==6; assert all(len(s.checks)>=1 for _,s in tasks), [(t,len(s.checks)) for t,s in tasks]; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `load_suite(Path('tests/eval/golden'), suite='golden')` returns 6 tasks, each with `len(spec.checks) >= 1`.
    - 01-analyze has a `file_exists` check with `path == ".voss/architecture.md"`.
    - 03-approved-edit has `file_contains` checks for `sum_two` in both calc.py and main.py plus a cmd gate for the removed `def add(`.
    - 04-validation has a cmd check whose `run` invokes `voss check sample.voss`.
    - All 6 task.toml files are valid TOML (tomllib parses without error).
    - `grep -lc "\[\[checks\]\]" tests/eval/golden/*/task.toml | wc -l` shows all 6 files contain `[[checks]]`.
  </acceptance_criteria>
  <done>All 6 golden tasks carry ≥1 grounded deterministic check matching their contract; suite loads with non-empty checks; TOML valid.</done>
</task>

<task type="auto">
  <name>Task 2: Coverage test — all tasks have checks + stub suite runs checks cleanly</name>
  <read_first>
    - tests/eval/test_voss_eval_stub.py (subprocess _run_eval harness + golden-suite stub-run pattern to mirror; conftest from E1-02 supplies VOSS_DEV=1)
    - voss/eval/suite.py (load_suite signature)
    - voss/eval/runner.py (run_suite — full stub suite writes runs.jsonl with checks/gate_pass per row after E1-03)
  </read_first>
  <action>
    Create tests/eval/test_golden_checks.py with two tests. Test 1: load the golden suite via `load_suite(Path('tests/eval/golden'), suite='golden')` and assert exactly 6 tasks, each with `len(spec.checks) >= 1`, and assert per-task the expected check shape (01 file_exists on architecture.md; 04 a cmd check). Test 2: run the FULL stub suite via the subprocess `_run_eval`-style harness (`--stub --auth none -k 1 --out <dir>`) from the repo root with VOSS_DEV=1 in env; assert returncode 0, assert runs.jsonl has 6 rows, and assert every row has a `checks` list (the checks executed without crashing the run — pass/fail values are not asserted, since stub agents don't perform edits so some gates legitimately fail). This proves "stub-mode full suite executes checks without error" (SPEC §3 acceptance) — NOT that all gates pass (gate-pass is a live concern, EVSUB-07).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_golden_checks.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Test 1 asserts 6 tasks, each `len(spec.checks) >= 1`, with the 01 and 04 check shapes verified.
    - Test 2 runs the full stub suite (all 6 tasks), asserts returncode 0, 6 rows in runs.jsonl, and every row carries a `checks` list.
    - Test 2 does NOT assert all gates pass (stub agents do not edit; gate-pass is the live EVSUB-07 concern).
    - `.venv/bin/python -m pytest tests/eval/test_golden_checks.py -q` fully green.
    - Full eval suite still green: `.venv/bin/python -m pytest tests/eval -q`.
  </acceptance_criteria>
  <done>Coverage test proves all 6 golden tasks have checks and a full stub suite executes every task's checks without error; eval suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| golden task.toml cmd checks → shell | the new cmd gates (`git diff --quiet`, `voss check`, `! grep`) are repo-committed, code-reviewed fixture definitions |
| cmd check → fixture cwd | gates run inside the isolated temp git fixture copy, not the operator repo |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E1-11 | Tampering | retrofit cmd checks run shell | accept | All 6 cmd gates are committed in the repo's golden fixtures (trusted, reviewed); inherits E1-01 T-E1-01 posture — no untrusted task.toml sourcing |
| T-E1-12 | Denial | a cmd gate (e.g. voss check) hangs | mitigate | inherits E1-01 per-check 60s timeout; the four cmd gates are sub-second fixture-local commands |
</threat_model>

<verification>
- `load_suite` returns 6 tasks each with ≥1 check
- Full stub suite (6 tasks) runs returncode 0, every row carries a `checks` list (checks executed without error)
- `.venv/bin/python -m pytest tests/eval -q` → full eval suite green
- All 6 task.toml files parse as valid TOML
</verification>

<success_criteria>
- All 6 golden tasks have ≥1 deterministic check matching their contract (EVSUB-03)
- `load_suite` returns 6 tasks each with non-empty `checks`
- Full stub-mode suite executes all checks without error (no crash); gate-pass is the live EVSUB-07 concern
</success_criteria>

<output>
Create `.planning/phases/E1-eval-substrate/E1-04-SUMMARY.md` when done
</output>
