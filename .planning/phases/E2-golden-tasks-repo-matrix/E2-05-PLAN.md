---
phase: E2-golden-tasks-repo-matrix
plan: 05
type: execute
wave: 2
depends_on: ["E2-02"]
files_modified:
  - tests/eval/matrix/py-01-analyze/task.toml
  - tests/eval/matrix/py-03-approved-edit/task.toml
  - tests/eval/matrix/py-04-validation/task.toml
  - tests/eval/matrix/py-02-plan-only/task.toml
  - tests/eval/matrix/py-05-resume/task.toml
  - tests/eval/matrix/py-06-fetch-summarize/task.toml
autonomous: true
requirements: [EVGLD-02, EVGLD-03, EVGLD-04]
must_haves:
  truths:
    - "All 6 py-* cells have a valid TaskSpec task.toml (extra=forbid: only the 9 valid fields, no lang field)"
    - "py-01-analyze has a cognition gate: file_contains .voss/architecture.md text=pyproject"
    - "py-03-approved-edit has behavioral gates: file_contains calc.py sum_two + cmd grep-old-absent + cmd pytest"
    - "py-04-validation runs python3 -m pytest test_calc.py -q (the native toolchain, NOT voss check)"
    - "py-02/05/06 reuse the golden task contracts (plan/resume/fetch) with their existing checks"
    - "Every py-* cell has at least one deterministic check (no vacuous judge-only pass)"
  artifacts:
    - path: "tests/eval/matrix/py-01-analyze/task.toml"
      provides: "Analyze cell with file_exists + cognition file_contains pyproject"
      contains: "pyproject"
    - path: "tests/eval/matrix/py-03-approved-edit/task.toml"
      provides: "Approved-edit cell: rename add to sum_two, gates green"
      contains: "sum_two"
    - path: "tests/eval/matrix/py-04-validation/task.toml"
      provides: "Validation cell running native pytest"
      contains: "pytest test_calc.py"
  key_links:
    - from: "tests/eval/matrix/py-*/task.toml [[checks]]"
      to: "voss/eval/runner.py _run_checks"
      via: "cmd/file_exists/file_contains executed in the isolated fixture copy"
      pattern: "type = .(cmd|file_exists|file_contains)."
---

<objective>
Write the 6 Python matrix `task.toml` files. Three shape cells (py-01-analyze, py-03-approved-edit, py-04-validation) get per-language behavioral + cognition gates over the flat calc fixture (plan 02). Three language-agnostic cells (py-02-plan-only, py-05-resume, py-06-fetch-summarize) reuse the golden task contracts so the session/planning machinery is proven once on Python (D-02).

Purpose: Encodes EVGLD-02 (curated cells), EVGLD-03 (behavioral gates), EVGLD-04 (cognition gate) for the Python axis. Each task.toml is a standard E1 TaskSpec — ZERO schema change; language is encoded in the task_id prefix (`py-`), NOT a new field.
Output: 6 `py-*/task.toml` files, each a valid TaskSpec with at least one deterministic check.
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
<!-- The ONLY valid TaskSpec fields (extra="forbid"). No `lang` field — language is in the task_id prefix. -->
From voss/eval/suite.py:
  prompt (str, required) · mode ("plan"|"edit"|"auto", required) · rubric (str, required)
  judge_inputs (list, default ["final","file_diff"]) · provider (str|None) · model (str|None)
  auto_approve_edits (bool, default false) · tools (list[str], default []) · checks (list, default [])
Check shapes: {type="cmd", run, timeout=60} · {type="file_exists", path} · {type="file_contains", path, text}
Loader signatures (VERIFIED voss/eval/suite.py:57-70):
  load_task(task_dir: Path) -> TaskSpec   # task_dir is the CELL DIRECTORY; it reads task_dir/"task.toml" internally
  load_suite(suite_root: Path, suite="matrix") -> list[(id, spec)]   # call with suite_root=Path("tests/eval/matrix") whose basename IS "matrix"
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the 3 Python shape-cell task.tomls (py-01, py-03, py-04)</name>
  <files>tests/eval/matrix/py-01-analyze/task.toml, tests/eval/matrix/py-03-approved-edit/task.toml, tests/eval/matrix/py-04-validation/task.toml</files>
  <read_first>
    - tests/eval/golden/01-analyze/task.toml (analog — full analyze field set: prompt, mode=edit, rubric, judge_inputs, auto_approve_edits, [[checks]] file_exists .voss/architecture.md)
    - tests/eval/golden/03-approved-edit/task.toml (analog — approved-edit field set + the old-name-absent cmd-check idiom that greps for the old def)
    - tests/eval/golden/04-validation/task.toml (analog — validation cmd-check shape; golden uses `voss check`, matrix uses NATIVE pytest per D-02)
    - E2-PATTERNS.md lines 121-218 (per-language task.toml substitutions — exact [[checks]] blocks for py-01/py-03/py-04)
    - E2-RESEARCH.md §Per-Cell Check Specifications lines 475-520 (Analyze/Approved-Edit/Validation check tables; cognition token Python=pyproject)
    - E2-RESEARCH.md Pitfall 5 lines 629-632 + Pitfall 6 lines 634-637 (analyze writes .voss/architecture.md directly; every cell MUST have a deterministic check or it is a vacuous pass)
  </read_first>
  <action>
    Write tests/eval/matrix/py-01-analyze/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final","file_diff"]). Prompt: "Analyze this repository and write architecture.md describing what it does." (same simple prompt as golden-01 — reliably names the manifest, Pitfall 5). Checks: a file_exists check on path ".voss/architecture.md" (behavioral: file created); a file_contains check on path ".voss/architecture.md" with text "pyproject" (cognition gate EVGLD-04: names Python tooling).

    Write tests/eval/matrix/py-03-approved-edit/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final","file_diff"]). Prompt: "Rename the function add() to sum_two() in calc.py and update its single call site in test_calc.py." Checks: a file_contains check on path "calc.py" with text "sum_two" (new name landed); a cmd check whose run negates a grep for the old def in calc.py — the literal command is `! grep -q 'def add(' calc.py` (old name removed); a cmd check with run `python3 -m pytest test_calc.py -q` and timeout=60 (suite green after edit — EVGLD-03 behavioral).

    Write tests/eval/matrix/py-04-validation/task.toml (mode=edit, auto_approve_edits=true, judge_inputs=["final"]). Prompt: "Run the project's test suite and report the exit code." Checks: a cmd check with run `python3 -m pytest test_calc.py -q` and timeout=60 (NATIVE toolchain gate per D-02 — explicitly NOT `voss check`).

    Every file must include a `rubric` string (required field; copy the PASS/FAIL shape from the golden analog and adapt the identifiers). Use ONLY the 9 valid TaskSpec fields — do NOT add a `lang` key (extra="forbid" rejects it; language is in the `py-` prefix).
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_task; [load_task(Path('tests/eval/matrix')/d) for d in ['py-01-analyze','py-03-approved-edit','py-04-validation']]"` exits 0 (all three validate under extra=forbid; load_task takes the cell DIRECTORY and reads task.toml internally)
    - `grep -c pyproject tests/eval/matrix/py-01-analyze/task.toml` is at least 1 (cognition token present)
    - `grep -c sum_two tests/eval/matrix/py-03-approved-edit/task.toml` is at least 1 and the file contains the literal `! grep -q 'def add('` old-name-absent cmd
    - `grep -c "pytest test_calc.py" tests/eval/matrix/py-04-validation/task.toml` is at least 1 and `grep -c "voss check" tests/eval/matrix/py-04-validation/task.toml` equals 0 (native toolchain, not voss check)
    - `grep -c "^lang " tests/eval/matrix/py-01-analyze/task.toml tests/eval/matrix/py-03-approved-edit/task.toml tests/eval/matrix/py-04-validation/task.toml` equals 0 (no forbidden field)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_task; [print(d, len(load_task(Path('tests/eval/matrix')/d).checks)) for d in ['py-01-analyze','py-03-approved-edit','py-04-validation']]"</automated>
  </verify>
  <done>Three Python shape task.tomls validate as TaskSpecs; py-01 has the pyproject cognition gate; py-03 has the three behavioral gates; py-04 runs native pytest (not voss check); no lang field.</done>
</task>

<task type="auto">
  <name>Task 2: Write the 3 Python-only-cell task.tomls (py-02, py-05, py-06)</name>
  <files>tests/eval/matrix/py-02-plan-only/task.toml, tests/eval/matrix/py-05-resume/task.toml, tests/eval/matrix/py-06-fetch-summarize/task.toml</files>
  <read_first>
    - tests/eval/golden/02-plan-only/task.toml (source contract to mirror — mode=plan, [[checks]] cmd `git diff --quiet HEAD` proves no writes in plan mode)
    - tests/eval/golden/05-resume/task.toml (source — mode=plan, [[checks]] cmd `test -f notes.txt`)
    - tests/eval/golden/06-fetch-summarize/task.toml (source — mode=edit, tools=["web_fetch","fs_write"], [[checks]] file_exists summary.txt + file_contains summary.txt "Example")
    - E2-PATTERNS.md lines 220-248 (py-02/05/06 reuse blocks — exact field carry-over)
    - E2-RESEARCH.md §Python-Only Cells lines 522-528 (these prove session/planning machinery once; checks are fixture-intrinsic)
  </read_first>
  <action>
    Mirror the three golden language-agnostic contracts into the matrix (the fixtures are already in place from plan 02). Write tests/eval/matrix/py-02-plan-only/task.toml from the golden-02 contract: mode=plan (no auto_approve_edits), the existing prompt + rubric, a cmd check with run `git diff --quiet HEAD` (plan mode writes nothing). Write tests/eval/matrix/py-05-resume/task.toml from golden-05: mode=plan, the existing prompt + rubric, a cmd check with run `test -f notes.txt`. Write tests/eval/matrix/py-06-fetch-summarize/task.toml from golden-06: mode=edit, auto_approve_edits=true, tools=["web_fetch","fs_write"], the existing prompt + rubric, a file_exists check on path "summary.txt" plus a file_contains check on path "summary.txt" with text "Example". These can be byte-faithful copies of the golden task.tomls (the contracts are identical; only the suite directory differs). Use ONLY the 9 valid TaskSpec fields; no `lang` key.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_task; [load_task(Path('tests/eval/matrix')/d) for d in ['py-02-plan-only','py-05-resume','py-06-fetch-summarize']]"` exits 0
    - `grep -c "git diff --quiet" tests/eval/matrix/py-02-plan-only/task.toml` equals 1 and `grep -c 'mode = .plan.' tests/eval/matrix/py-02-plan-only/task.toml` equals 1
    - `grep -c "test -f notes.txt" tests/eval/matrix/py-05-resume/task.toml` equals 1
    - `grep -c web_fetch tests/eval/matrix/py-06-fetch-summarize/task.toml` is at least 1 and `grep -c summary.txt tests/eval/matrix/py-06-fetch-summarize/task.toml` is at least 2
    - All 6 py cells load with checks via the verify command below (asserts count==6 and each spec has at least one check)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_suite; t=load_suite(Path('tests/eval/matrix'), suite='matrix'); py=[(i,len(s.checks)) for i,s in t if i.startswith('py-')]; print(py); assert len(py)==6 and all(c >= 1 for _,c in py)"</automated>
  </verify>
  <done>Three Python-only task.tomls mirror their golden contracts; all 6 py-* cells load via load_suite with at least one check each; no lang field.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml [[checks]] → runner's isolated copy | Checks are developer-authored, committed; `_run_checks` executes them with cwd=the isolated fixture copy, never the repo root |
| cmd check shell=True → fixture cwd | `python3 -m pytest` / `git diff` / `! grep` run only inside the temp copy (E1 `_run_checks` semantics) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-10 | Tampering | cmd check shell injection | accept | task.toml checks are developer-authored + committed; shell=True is the intentional E1 contract for fixture commands (RESEARCH Security Domain). |
| T-E2-11 | Spoofing | vacuous judge-only pass (no checks) | mitigate | Every py-* cell has at least one deterministic check; plan-01 `test_matrix_all_cells_have_checks` enforces it suite-wide (Pitfall 6). |
| T-E2-12 | Tampering | check running in repo root not fixture copy | mitigate | `_run_checks` sets cwd to the `_prepare_fixture` temp copy; no check path escapes it; all paths are fixture-relative. |
| T-E2-SC | Tampering | npm/pip/cargo installs | n/a | No package installs in this plan (task.toml content only). |
</threat_model>

<verification>
- All 6 py-* task.tomls validate as TaskSpecs under extra="forbid" (no lang field).
- py-01 cognition gate (pyproject), py-03 three behavioral gates, py-04 native pytest.
- py-02/05/06 mirror golden contracts; every cell has at least one deterministic check.
</verification>

<success_criteria>
- 6 `tests/eval/matrix/py-*/task.toml` files exist and load via load_suite(suite="matrix")
- Shape cells encode EVGLD-03 (behavioral) + EVGLD-04 (cognition); reuse cells encode session machinery
- Zero TaskSpec schema change; language carried only by the `py-` prefix
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-05-SUMMARY.md` when done
</output>
