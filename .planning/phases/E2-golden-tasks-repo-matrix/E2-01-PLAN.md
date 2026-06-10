---
phase: E2-golden-tasks-repo-matrix
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/eval/test_matrix_suite.py
  - tests/eval/test_matrix_runner.py
  - tests/eval/test_matrix_stub.py
  - tests/eval/test_matrix_summary.py
autonomous: true
requirements: [EVGLD-01, EVGLD-02, EVGLD-03, EVGLD-04, EVGLD-05, EVGLD-06, EVGLD-07]
must_haves:
  truths:
    - "Four matrix test files exist in tests/eval/ and are collected by pytest"
    - "Every EVGLD-* requirement has at least one named test (RED or skip-marked) referencing it"
    - "The existing 66 eval tests stay green — new RED tests are isolated (xfail or skip-until-implemented), never breaking collection"
  artifacts:
    - path: "tests/eval/test_matrix_suite.py"
      provides: "EVGLD-01 suite-loads-with-checks scaffold"
      contains: "load_suite"
    - path: "tests/eval/test_matrix_runner.py"
      provides: "EVGLD-02/03/04 preflight + skip + require-all scaffolds"
      contains: "toolchain"
    - path: "tests/eval/test_matrix_stub.py"
      provides: "EVGLD-05/06/07 per-cell + full-stub-run scaffolds"
      contains: "matrix"
    - path: "tests/eval/test_matrix_summary.py"
      provides: "EVGLD-06 summary skipped-column scaffold"
      contains: "skipped"
  key_links:
    - from: "tests/eval/test_matrix_*.py"
      to: "tests/eval/conftest.py"
      via: "autouse VOSS_DEV=1 fixture (inherited, no per-file setenv)"
      pattern: "VOSS_DEV"
---

<objective>
Create the four RED test-scaffold files for the E2 matrix — one Nyquist-aligned automated test per EVGLD requirement — so every downstream plan's `<acceptance_criteria>` resolves to a real, named pytest selector instead of `MISSING`. This is the Wave-0 foundation that closes the Validation map's Wave-0 gaps (E2-VALIDATION.md lines 64-68).

**Minted requirement IDs (documented here for the future E2-SPEC.md to adopt):** No SPEC exists; these IDs are minted from CONTEXT decisions D-01..D-04 + the 12-cell matrix scope.

| Req ID | Meaning | CONTEXT source |
|--------|---------|----------------|
| EVGLD-01 | Synthetic-minimal fixtures + matrix suite loads (12 cells, each ≥1 check) | D-01, D-02 |
| EVGLD-02 | Curated 12-cell matrix task.tomls with per-language behavioral checks | D-02, D-04 |
| EVGLD-03 | Per-language behavioral gates (toolchain test exits 0 + edit-landed file-contains) | D-04 |
| EVGLD-04 | Cognition gate (analyze → architecture.md contains lang-correct manifest token) | D-04 |
| EVGLD-05 | Toolchain require-present + recorded-skip + preflight print + `--require-all-toolchains` | D-03 |
| EVGLD-06 | summary.md skipped column (never silent-green) | D-03 |
| EVGLD-07 | Full matrix stub-run green + manual live-proof note | D-01..D-04 |

Purpose: Establish the test contract first so executors of plans 02-09 inherit deterministic acceptance selectors.
Output: Four test files, RED (failing or skip-pending) until their feature plan lands, GREEN by phase end.
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
@.planning/phases/E2-golden-tasks-repo-matrix/E2-VALIDATION.md

<interfaces>
<!-- Contracts the test scaffolds assert against. Use directly — no codebase exploration needed. -->

From voss/eval/suite.py (E1 — SHIPPED, no change in E2):
```python
def load_suite(suite_root: Path, *, suite: str) -> list[tuple[str, TaskSpec]]
class TaskSpec(BaseModel):  # model_config = ConfigDict(extra="forbid")
    prompt: str; mode: Literal["plan","edit","auto"]; rubric: str
    judge_inputs: list[...]; provider: str | None; model: str | None
    auto_approve_edits: bool; tools: list[str]; checks: list[AnyCheck]
class CmdCheck(BaseModel): type: Literal["cmd"]; run: str; timeout: int = 60
class FileExistsCheck(BaseModel): type: Literal["file_exists"]; path: str
class FileContainsCheck(BaseModel): type: Literal["file_contains"]; path: str; text: str
```

From voss/eval/runner.py (E1 — SHIPPED; W3 plan 08 EXTENDS these):
```python
def run_suite(*, suite="golden", stub=False, live=False, k=1, out=None,
              out_dir=None, judge_model=None, task=None, task_id=None,
              auth_pref="auto", model=None, max_turns=None) -> Path
# Plan 08 will ADD: require_all_toolchains: bool = False
```

From voss/eval/summary.py (E1 — SHIPPED; W3 plan 08 EXTENDS):
```python
def write_summary(jsonl_path: Path, summary_path: Path) -> Path
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Scaffold matrix suite-loads + summary tests (EVGLD-01, EVGLD-06)</name>
  <files>tests/eval/test_matrix_suite.py, tests/eval/test_matrix_summary.py</files>
  <read_first>
    - tests/eval/test_golden_checks.py (analog for test_matrix_suite.py — `_repo_root` lines 12-13, `test_all_golden_tasks_have_checks` lines 33-52: `load_suite(Path("tests/eval/golden"), suite="golden")` then `assert all(len(spec.checks) >= 1 ...)`)
    - tests/eval/test_summary_md.py (analog for test_matrix_summary.py — `_write_rows` lines 9-11, section-assertion pattern lines 33-44, exact-bytes pattern lines 47-90)
    - tests/eval/conftest.py (autouse VOSS_DEV=1 fixture lines 1-9 — inherited automatically, do NOT re-add)
    - voss/eval/summary.py lines 60-94 (gate/judge aggregation + per-task loop the skipped column extends)
  </read_first>
  <action>
    Create tests/eval/test_matrix_suite.py: copy `_repo_root()` from test_golden_checks.py verbatim. Add `test_matrix_suite_loads` asserting `load_suite(Path("tests/eval/matrix"), suite="matrix")` returns exactly 12 cells (EVGLD-01). Add `test_matrix_all_cells_have_checks` asserting `all(len(spec.checks) >= 1 for _, spec in tasks)` with message "every matrix task must have at least one deterministic check" (defeats Pitfall 6 vacuous-pass). Add `test_matrix_cell_ids` asserting the 12 expected ids are present: py-01-analyze, py-02-plan-only, py-03-approved-edit, py-04-validation, py-05-resume, py-06-fetch-summarize, rust-01-analyze, rust-03-approved-edit, rust-04-validation, ts-01-analyze, ts-03-approved-edit, ts-04-validation. Add `test_matrix_cognition_token` asserting each analyze cell has a FileContainsCheck on `.voss/architecture.md` with the lang-correct token (py→`pyproject`, rust→`Cargo.toml`, ts→`package.json`) — covers EVGLD-04. These tests will FAIL until plans 05/06/07 create the matrix dir; that is the intended RED state. Mark the suite-dependent tests with `pytest.mark.skipif(not (Path(_repo_root()) / "tests/eval/matrix").is_dir(), reason="matrix suite not built yet")` so collection stays green and the existing 66 tests are unaffected — they auto-activate once the matrix dir exists.

    Create tests/eval/test_matrix_summary.py: copy `_write_rows` from test_summary_md.py verbatim. Add `test_summary_renders_skipped_header` and `test_summary_renders_skipped_column` building rows with one normal row (`skipped: False`) and one toolchain-absent row (`success: None, skipped: True, skip_reason: "toolchain-absent", gate_pass: None`), calling `write_summary`, and asserting the rendered text contains `skipped` and the per-task table header `| task | runs | gate pass | skipped | pass rate | mean cost |` (EVGLD-06). These will FAIL until plan 08 extends summary.py + jinja — intended RED. Do NOT skip-guard these (summary.py already exists, so the test runs immediately as a true RED that turns green when plan 08 lands).
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/eval/test_matrix_suite.py --collect-only -q` exits 0 (collection succeeds, no import errors)
    - `.venv/bin/python -m pytest tests/eval/test_matrix_summary.py --collect-only -q` exits 0
    - `.venv/bin/python -m pytest tests/eval/ -q` still passes the existing 66 tests (new suite tests are skipif-guarded; summary tests are RED but isolated to the 2 new functions): the prior-66 count does not regress
    - `grep -c "EVGLD-01\|matrix_suite_loads\|skipped" tests/eval/test_matrix_suite.py tests/eval/test_matrix_summary.py` shows the selectors exist
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_matrix_suite.py tests/eval/test_matrix_summary.py --collect-only -q</automated>
  </verify>
  <done>Both files collect cleanly; suite tests skipif-guard on missing matrix dir; summary tests are true RED awaiting plan 08; existing 66 eval tests unaffected.</done>
</task>

<task type="auto">
  <name>Task 2: Scaffold matrix runner + stub tests (EVGLD-02, EVGLD-03, EVGLD-05, EVGLD-07)</name>
  <files>tests/eval/test_matrix_runner.py, tests/eval/test_matrix_stub.py</files>
  <read_first>
    - tests/eval/test_hybrid_gate.py (analog for test_matrix_runner.py — `_write_task` lines 23-28 writes to `golden/`; for matrix change to `tests/eval/matrix/`; `_read_rows` lines 31-33; monkeypatch+run_suite pattern lines 56-72; run-header capture `test_run_header_prints` lines 137-157 asserting `"tasks · max"` and `"turns/task"`)
    - tests/eval/test_voss_eval_stub.py (analog for test_matrix_stub.py — `REQUIRED_FIELDS` sentinel lines 11-31, `_repo_root` + `_read_rows` lines, `_run_eval` subprocess helper lines 38-49, parametrized golden-stub pattern lines 207-227)
    - tests/eval/test_runner_options.py lines 44-47 (monkeypatch `_provider_for_eval`/`_judge_provider_for_eval` to StubProvider — avoids creds in toolchain tests)
    - voss/eval/runner.py lines 380-395 (run header line 381 + task loop top 390-394 — where plan 08 inserts preflight + skip guard)
  </read_first>
  <action>
    Create tests/eval/test_matrix_runner.py: copy `_read_rows` verbatim; copy `_write_task` but target `root / "tests" / "eval" / "matrix" / task_id` (matrix, not golden). Add `test_preflight_prints_toolchain_availability` (EVGLD-02): write a matrix task `py-99-stub` (any prefix), monkeypatch `runner.shutil.which` so cargo returns None, run `runner.run_suite(stub=True, auth_pref="none", suite="matrix", task=..., out=..., max_turns=3)` with capsys, assert `"toolchains:"` in stdout and tokens `py`, `rust`, `ts` appear. Add `test_toolchain_absent_records_skip_row` (EVGLD-03): write a matrix task `rust-99-stub`, monkeypatch `runner.shutil.which` to return None for cargo, run, read the JSONL row, assert `row["skipped"] is True and row["skip_reason"] == "toolchain-absent" and row["gate_pass"] is None and row["success"] is None` — and explicitly assert `row.get("gate_pass") is not False` (a skip must NOT read as a gate FAIL). Add `test_require_all_toolchains_fails_when_absent` (EVGLD-05 strict): monkeypatch a toolchain to None, call `runner.run_suite(..., suite="matrix", require_all_toolchains=True, ...)` inside `pytest.raises(click.UsageError)` and assert the message names the missing toolchain. All three FAIL until plan 08 — guard each with `pytest.mark.xfail(reason="plan E2-08: runner toolchain extension not yet implemented", strict=True)` so they flip to XPASS→remove-xfail when plan 08 lands. Use strict=True so a premature pass is itself a failure (anti-false-green).

    Create tests/eval/test_matrix_stub.py: copy `REQUIRED_FIELDS`, `_repo_root`, `_read_rows`, `_run_eval` verbatim (add `"--suite", "matrix"` to the `_run_eval` arg list — it shells `python -m voss.cli eval`). Add `MATRIX_CELLS` = the 12 ids. Add parametrized `test_matrix_cell_stub` over MATRIX_CELLS: skip if `tests/eval/matrix/<id>/task.toml` absent (so it is RED-by-skip until plans 05/06/07), else `_run_eval(["--stub","--auth","none","--suite","matrix","--task",cell,"-k","1","--out",str(out)], cwd=repo)`, assert returncode 0, one row, `set(rows[0]) >= REQUIRED_FIELDS`. Add `test_full_matrix_stub_run` (EVGLD-07): skip if matrix dir absent, else run the whole suite under `--stub --suite matrix` and assert returncode 0 and 12 rows. The cell-specific behavioral assertions (EVGLD-03 edit-landed / EVGLD-04 cognition) are validated structurally via test_matrix_suite.py Task-1 (spec-level) and live via the manual proof note in plan 09; stub mode cannot drive real edits, so test_matrix_stub asserts the harness completes + row shape, not edit content.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/eval/test_matrix_runner.py tests/eval/test_matrix_stub.py --collect-only -q` exits 0
    - `.venv/bin/python -m pytest tests/eval/test_matrix_runner.py -q` reports 3 xfail (not error, not unexpected pass) — confirms the RED contract is wired and strict
    - `.venv/bin/python -m pytest tests/eval/ -q` does not regress the existing 66 tests (stub cells skip on absent matrix dir; runner tests are xfail)
    - `grep -c "EVGLD-02\|EVGLD-03\|EVGLD-05\|EVGLD-07\|toolchain-absent\|require_all_toolchains" tests/eval/test_matrix_runner.py tests/eval/test_matrix_stub.py` is non-zero
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_matrix_runner.py tests/eval/test_matrix_stub.py --collect-only -q && .venv/bin/python -m pytest tests/eval/test_matrix_runner.py -q -rx</automated>
  </verify>
  <done>Runner tests are strict-xfail (RED, flip to fail-if-pass), stub tests skip-until-fixtures; collection clean; existing 66 tests unaffected. Every EVGLD-0N maps to a named selector.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test → pytest collection | New test files must not break collection of the existing 66 eval tests |
| test → conftest VOSS_DEV gate | Tests inherit the autouse `VOSS_DEV=1` fixture; no test bypasses the gate |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-01 | Spoofing | RED scaffolds masking as green | mitigate | Runner tests use `xfail(strict=True)`; a premature pass FAILS the suite (no false-green). Suite/stub tests skip-guard on missing matrix dir, never assert-vacuous-pass. |
| T-E2-02 | Tampering | New tests altering golden suite behavior | accept | New files are additive in `tests/eval/`; they only read `tests/eval/matrix/` and synthetic rows — golden/ untouched. |
| T-E2-SC | Tampering | npm/pip/cargo installs | n/a | No package installs in this plan (test scaffolds only). No legitimacy gate needed. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/ -q` — existing 66 green, new suite/stub tests skip-pending, new runner tests strict-xfail, new summary tests RED (2 functions). No collection errors, no regression of the prior-66 count.
- Every EVGLD-01..07 has at least one named test function (verified by grep selectors above).
</verification>

<success_criteria>
- Four files exist: test_matrix_suite.py, test_matrix_runner.py, test_matrix_stub.py, test_matrix_summary.py
- All collect without import error under `.venv/bin/python`
- Existing 66 eval tests do not regress
- RED contract is anti-false-green: runner tests strict-xfail; suite/stub tests skip-guard; summary tests are true RED awaiting plan 08
- Minted EVGLD-01..07 documented at the top of this plan's objective
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-01-SUMMARY.md` when done
</output>
