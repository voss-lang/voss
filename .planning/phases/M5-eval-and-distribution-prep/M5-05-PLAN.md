---
phase: M5
plan: 05
type: execute
wave: 4
depends_on:
  - M5-01
  - M5-03
files_modified:
  - tests/eval/golden/01-analyze/task.toml
  - tests/eval/golden/01-analyze/fixture/main.py
  - tests/eval/golden/01-analyze/fixture/README.md
  - tests/eval/golden/02-plan-only/task.toml
  - tests/eval/golden/02-plan-only/fixture/calc.py
  - tests/eval/golden/03-approved-edit/task.toml
  - tests/eval/golden/03-approved-edit/fixture/calc.py
  - tests/eval/golden/03-approved-edit/fixture/main.py
  - tests/eval/golden/04-validation/task.toml
  - tests/eval/golden/04-validation/fixture/sample.voss
  - tests/eval/golden/05-resume/task.toml
  - tests/eval/golden/05-resume/fixture/notes.txt
autonomous: true
requirements:
  - EVAL-01
must_haves:
  truths:
    - "Five directories exist under `tests/eval/golden/` with stable ids: 01-analyze, 02-plan-only, 03-approved-edit, 04-validation, 05-resume."
    - "Each task directory contains a parseable `task.toml` (validates against `TaskSpec` from Plan 01)."
    - "Each task directory contains a `fixture/` subdir with seed files."
    - "Task 03 (`03-approved-edit`) has `auto_approve_edits = true` in its task.toml."
    - "Task 04 (`04-validation`) contains a `.voss` sample copied from `samples/classify.voss`."
    - "Task 05 (`05-resume`) has its own fixture (not shared with task 04 — D-06 independence)."
    - "`voss eval --stub --task <id> -k 1` runs to completion (returncode 0) for each of the 5 fixtures."
  artifacts:
    - path: "tests/eval/golden/01-analyze/task.toml"
      provides: "analyze prompt + rubric for architecture.md production"
      contains: "auto_approve_edits = true"
    - path: "tests/eval/golden/01-analyze/fixture/"
      provides: "Tiny seed repo (main.py + README.md) for the analyze task"
    - path: "tests/eval/golden/02-plan-only/task.toml"
      provides: "plan-mode prompt + no-writes rubric"
      contains: "mode = \"plan\""
    - path: "tests/eval/golden/02-plan-only/fixture/calc.py"
      provides: "5-line add() function without type hints"
    - path: "tests/eval/golden/03-approved-edit/task.toml"
      provides: "edit prompt for rename + auto_approve_edits=true wiring"
      contains: "auto_approve_edits = true"
    - path: "tests/eval/golden/03-approved-edit/fixture/"
      provides: "calc.py with add() + main.py importing it"
    - path: "tests/eval/golden/04-validation/task.toml"
      provides: "Prompt invokes `voss check sample.voss`; rubric checks exit 0"
    - path: "tests/eval/golden/04-validation/fixture/sample.voss"
      provides: "Copy of samples/classify.voss"
    - path: "tests/eval/golden/05-resume/task.toml"
      provides: "Summarize-notes prompt + rubric for prior-context surfaces"
    - path: "tests/eval/golden/05-resume/fixture/notes.txt"
      provides: "Distinguishable paragraphs for resume summary"
  key_links:
    - from: "tests/eval/golden/03-approved-edit/task.toml"
      to: "voss/harness/permissions.py:PermissionGate (line 98-104)"
      via: "auto_approve_edits=true → PermissionGate(auto_yes=True) constructed by runner"
      pattern: "auto_approve_edits = true"
    - from: "tests/eval/golden/05-resume/task.toml"
      to: "voss/eval/runner.py:_drive_resume"
      via: "task_id startswith '05-resume' routes through asyncio.Task.cancel + SessionRecord round-trip"
      pattern: "05-resume"
    - from: "tests/eval/golden/04-validation/fixture/sample.voss"
      to: "samples/classify.voss"
      via: "Copy of an existing minimal valid .voss program"
      pattern: "classify"
---

<objective>
Ship the five golden task fixtures that the M5 eval suite measures. Each fixture is a minimal, hermetic, independent seed repo plus a `task.toml` validated by `TaskSpec` (Plan 01). The fixture ids and stable contract:

| id | mode | distinctive contract |
|---|---|---|
| 01-analyze | edit | Agent writes `.voss/architecture.md` in fixture cwd |
| 02-plan-only | plan | Plan exists; no files modified |
| 03-approved-edit | edit | `auto_approve_edits=true`; both calc.py and main.py renamed |
| 04-validation | edit | Agent runs `voss check sample.voss`; final reports exit 0 |
| 05-resume | plan | Spawn → cancel → resume → summary references notes.txt content |

Purpose: EVAL-01 requires these five tasks to exist and cover the canonical v0.1 demo workflow (ROADMAP M5 success criterion 1). Plan 03's parametrize-skip tests come live once these fixtures land.

Output: 12 files under `tests/eval/golden/` (5 task.toml + 7 fixture files). Total fixture LOC < 250.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md
@.planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md
@.planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md
@.planning/phases/M5-eval-and-distribution-prep/M5-01-PLAN.md
@.planning/phases/M5-eval-and-distribution-prep/M5-03-PLAN.md
@samples/classify.voss
@voss/harness/permissions.py
@voss/harness/cognition.py

<interfaces>
<!-- TaskSpec — see Plan 01 -->
# prompt: str
# mode: Literal["plan", "edit", "auto"]
# rubric: str
# judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
# provider: str | None = None
# model: str | None = None
# auto_approve_edits: bool = False

<!-- ConfigDict(extra="forbid") rejects unknown keys -->

<!-- Runner routing for task 05 — voss/eval/runner.py:_drive_task -->
# if task_id.startswith("05-resume"):
#     return await _drive_resume(...)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Tasks 01–03 fixtures (analyze, plan-only, approved-edit)</name>
  <files>tests/eval/golden/01-analyze/task.toml, tests/eval/golden/01-analyze/fixture/main.py, tests/eval/golden/01-analyze/fixture/README.md, tests/eval/golden/02-plan-only/task.toml, tests/eval/golden/02-plan-only/fixture/calc.py, tests/eval/golden/03-approved-edit/task.toml, tests/eval/golden/03-approved-edit/fixture/calc.py, tests/eval/golden/03-approved-edit/fixture/main.py</files>
  <read_first>
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/golden/01-analyze/" (lines 1257-1284) — task.toml shape + fixture sizing rule (<200 LOC)
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/golden/02-plan-only/" (lines 1288-1314) — plan-mode rubric + fixture
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/golden/03-approved-edit/" (lines 1317-1345) — auto_approve_edits wiring + rename rubric
    - voss/harness/permissions.py:98-104, 108-109 — auto_yes path + plan-mode deny non-read tools
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-05, D-07, D-08 — fixture id contract + rubric plain-text + LLM-as-judge scoring
    - .planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md §"Open Question 2" — task 01 measures LLM agent path (NOT the deterministic _handle_analyze skill)
  </read_first>
  <action>
    Create `tests/eval/golden/01-analyze/task.toml` per M5-PATTERNS.md lines 1262-1277:
    - `prompt = "Analyze this repository and write architecture.md describing what it does."`
    - `mode = "edit"`
    - `rubric` (multiline `"""..."""`): plain-text PASS/FAIL criteria. PASS if `.voss/architecture.md` exists after the run AND the file is non-empty AND contains at least one paragraph describing the codebase. FAIL if `.voss/architecture.md` does not exist OR the file is empty/placeholder.
    - `judge_inputs = ["final", "file_diff"]`
    - `auto_approve_edits = true`
    Note: task 01 uses `mode="edit"` (not "auto") to ensure the LLM agent path is exercised, not the deterministic `_handle_analyze` skill (RESEARCH Open Question 2).

    Create `tests/eval/golden/01-analyze/fixture/main.py` — a 10-line "Hello CLI" Python file. Suggested body (keep < 15 LOC):
    - `"""Tiny seed CLI for the analyze fixture."""`
    - `def greet(name: str) -> str: return f"Hello, {name}!"`
    - `def main() -> None: import sys; name = sys.argv[1] if len(sys.argv) > 1 else "world"; print(greet(name))`
    - `if __name__ == "__main__": main()`

    Create `tests/eval/golden/01-analyze/fixture/README.md` — single paragraph stating: "Tiny seed repo for the M5 analyze eval fixture. `main.py` exposes a `greet(name)` function and a CLI entry point." Keep under 5 lines.

    Create `tests/eval/golden/02-plan-only/task.toml` per M5-PATTERNS.md lines 1294-1306:
    - `prompt = "Add type hints to the add() function in calc.py. Plan only — do not write."`
    - `mode = "plan"`
    - `rubric` (multiline): PASS if the plan describes specific tool calls (e.g., `fs_read calc.py`, then a planned write of type hints) AND no file modifications occurred in the fixture during the run. FAIL if the plan is empty/boilerplate OR any file in the fixture was modified.
    - `judge_inputs = ["final", "file_diff"]`
    - Do NOT set `auto_approve_edits` (defaults to false). Plan mode denies non-read tools per permissions.py:108-109.

    Create `tests/eval/golden/02-plan-only/fixture/calc.py`:
    - `"""Adder used by the M5 plan-only eval fixture."""`
    - `def add(a, b): return a + b`
    No type hints — that's the intended change the agent should PLAN but not execute.

    Create `tests/eval/golden/03-approved-edit/task.toml` per M5-PATTERNS.md lines 1322-1337:
    - `prompt = "Rename the function add() to sum_two() in calc.py and update its single call site in main.py."`
    - `mode = "edit"`
    - `rubric` (multiline): PASS if calc.py defines `sum_two()` (not `add()`), AND main.py imports and calls `sum_two()` (not `add()`), AND both files were modified. FAIL if either file is unchanged OR the rename is incomplete (one file updated, the other not).
    - `judge_inputs = ["final", "file_diff"]`
    - `auto_approve_edits = true` — runner wires `PermissionGate(auto_yes=True)` so no human prompt fires (RESEARCH §Pattern 3 Option A).

    Create `tests/eval/golden/03-approved-edit/fixture/calc.py`:
    - `"""Original add() — to be renamed to sum_two() by the agent."""`
    - `def add(a, b): return a + b`

    Create `tests/eval/golden/03-approved-edit/fixture/main.py`:
    - `"""Call site for add() — agent must update to sum_two() after rename."""`
    - `from calc import add`
    - `print(add(1, 2))`

    All `task.toml` files must parse with stdlib `tomllib.loads(...)` and validate against `TaskSpec.model_validate(...)`. Quick local check while authoring: `python -c "import tomllib; from voss.eval.suite import TaskSpec; data=tomllib.loads(open('<path>').read()); TaskSpec.model_validate(data)"`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "
import tomllib
from voss.eval.suite import TaskSpec, load_suite
from pathlib import Path
for tid in ['01-analyze','02-plan-only','03-approved-edit']:
    data = tomllib.loads((Path('tests/eval/golden')/tid/'task.toml').read_text())
    spec = TaskSpec.model_validate(data)
    print(tid, spec.mode, 'auto_approve=', spec.auto_approve_edits)
assert TaskSpec.model_validate(tomllib.loads(Path('tests/eval/golden/03-approved-edit/task.toml').read_text())).auto_approve_edits is True
assert TaskSpec.model_validate(tomllib.loads(Path('tests/eval/golden/02-plan-only/task.toml').read_text())).mode == 'plan'
print('OK')
"</automated>
  </verify>
  <done>
    3 task.toml files exist and validate against TaskSpec. Task 03 has `auto_approve_edits=true`. Task 02 has `mode="plan"`. Fixture files exist with documented seed content.
  </done>
</task>

<task type="auto">
  <name>Task 2: Tasks 04–05 fixtures (validation, resume) + cross-fixture smoke</name>
  <files>tests/eval/golden/04-validation/task.toml, tests/eval/golden/04-validation/fixture/sample.voss, tests/eval/golden/05-resume/task.toml, tests/eval/golden/05-resume/fixture/notes.txt</files>
  <read_first>
    - samples/classify.voss — minimal valid .voss program; will be copied verbatim into task 04's fixture/sample.voss
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/golden/04-validation/" (lines 1348-1374) — exit-0 rubric + shell_run dependency
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/golden/05-resume/" (lines 1378-1407) — prior-context-surfaces rubric + D-06 independence + canonical `notes.txt` body shape (three short paragraphs about a fictional project status — use this as the shape reference; do NOT inline the body here, see M5-PATTERNS.md for the literal text)
    - .planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md §"Pattern 4" + Assumption A2 — asyncio.Task.cancel propagation
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-06 — Task 05 must use its OWN seeded repo (not chained to task 04's tmp dir)
    - voss/eval/runner.py:_drive_resume (introduced in Plan 03) — task_id.startswith("05-resume") routing
  </read_first>
  <action>
    Create `tests/eval/golden/04-validation/task.toml` per M5-PATTERNS.md lines 1353-1367:
    - `prompt = "Run \`voss check sample.voss\` in this directory and report the exit code."`
    - `mode = "edit"` (shell_run is allowed in edit mode with auto-approve)
    - `rubric` (multiline): PASS if the agent's final answer indicates `voss check` exited 0 AND no errors or warnings reported. FAIL if the final answer indicates a non-zero exit code OR the agent did not actually invoke `voss check`.
    - `judge_inputs = ["final"]` (no file_diff needed — the run does not modify files; the agent's shell_run output captures the exit code).
    - `auto_approve_edits = true` (so shell_run does not block on permission prompt).

    Create `tests/eval/golden/04-validation/fixture/sample.voss`:
    - Read `samples/classify.voss` from the repo and copy its full content verbatim into `tests/eval/golden/04-validation/fixture/sample.voss`. This is RESEARCH's stated approach ("copy of `samples/classify.voss`"; M5-PATTERNS.md line 1370). The intent is a minimal valid .voss program that `voss check` will exit 0 on.

    Create `tests/eval/golden/05-resume/task.toml` per M5-PATTERNS.md lines 1383-1399:
    - `prompt = "Summarize the contents of notes.txt."`
    - `mode = "plan"` — read-only is sufficient; the resume contract tests prior-context surfaces, not file mutation.
    - `rubric` (multiline): PASS if after resume the agent's final answer summarizes notes.txt (not a fresh question) AND the summary references content present in notes.txt AND the session record shows two turns (initial + resumed). FAIL if the agent restarts the task from scratch OR the session record shows only one turn OR the summary references content not present in notes.txt.
    - `judge_inputs = ["final"]`.
    - Do NOT set `auto_approve_edits` (mode is plan; no approval needed).

    Create `tests/eval/golden/05-resume/fixture/notes.txt`:
    - Three short paragraphs of distinguishable content. Use the canonical body shape referenced in M5-PATTERNS.md §"tests/eval/golden/05-resume/fixture/notes.txt" (a fictional project status report so the resume summary has concrete facts to surface). Keep < 250 words. Include at least one specific noun (e.g., a name, a date, or a project code) that the judge can verify appears in the agent's summary. The body text shape: paragraph 1 names the project and reporting period, paragraph 2 reports an engineering milestone with a no-regression line, paragraph 3 lists open items / deferrals. The literal text lives in M5-PATTERNS.md (not duplicated here to keep this action prose-only).

    Cross-fixture smoke (best-effort under stub — exact subprocess command, validates loader + runner pick up all 5 fixtures):
    Run `python -m voss.cli eval --stub --suite golden -k 1 --out /tmp/voss-eval-smoke` from the repo root. Expected behavior:
    - Each fixture's `task.toml` parses (no `TaskSpec` ValidationError).
    - Loader returns 5 (task_id, spec) tuples.
    - 5 JSONL rows are written.
    - Each row has `judge_verdict: "skipped"` (no judge creds under stub per Plan 03 D-11 branch) and `success: null`.
    - The smoke does NOT validate rubric satisfaction (that requires live providers + judge model). It only validates that fixture loading + per-task dispatch + JSONL write all work.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "
from pathlib import Path
import tomllib
from voss.eval.suite import TaskSpec, load_suite
# 1. All 5 fixtures parse
tasks = load_suite(Path('tests/eval/golden'), suite='')
ids = {tid for tid, _ in tasks}
assert ids == {'01-analyze','02-plan-only','03-approved-edit','04-validation','05-resume'}, ids
# 2. sample.voss exists and is non-empty
s = Path('tests/eval/golden/04-validation/fixture/sample.voss').read_text()
assert len(s) > 0
# 3. notes.txt exists and is distinguishable
n = Path('tests/eval/golden/05-resume/fixture/notes.txt').read_text()
assert len(n.split()) >= 20, f'notes.txt too short: {len(n.split())} words'
print('OK')
"</automated>
  </verify>
  <done>
    5 fixtures present and load via `load_suite`. Task 04's sample.voss is a verbatim copy of `samples/classify.voss`. Task 05's notes.txt has at least 20 words of distinguishable content. All five `task.toml` files validate against TaskSpec.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Fixture seed → tempdir | Fixture contents copied verbatim into per-run tempdir; agent reads them under the cwd jail |
| task.toml rubric → judge prompt | Rubric is authored in-repo (trusted); judge sees it alongside agent output |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M5-05-task-spec-drift | T (Tampering) | golden task.toml authoring | mitigate | All 5 task.toml files validated against TaskSpec.model_validate at authoring time (verify script). ConfigDict(extra="forbid") from Plan 01 rejects typos. |
| T-M5-05-fixture-leak | I (Info Disclosure) | golden/<id>/fixture/ | mitigate | Fixtures are static, in-repo, and small (no secrets, no env-dependent content). Per-run runner copy is to tempdir (Plan 03 _prepare_fixture). |
| T-M5-05-task-04-shell-run | E (Elevation) / V12 (Files) | shell_run path in task 04 | accept | Task 04 prompt invokes `voss check sample.voss` — agent uses shell_run with `auto_approve_edits=true`. Path-jail at run_turn enforces cwd=tempdir; shell_run allowlist (M1 CTRL-02) further constrains. Risk is bounded by the existing v0.1 controls; no new attack surface. |
| T-M5-05-resume-flake | T (Tampering) | task 05 cancel timing | mitigate | Cancel point in `_drive_resume` is `asyncio.sleep(RESUME_CANCEL_DELAY_S)` (default 0.05s, env-tunable per Plan 03 mitigation) — deterministic relative to event-loop scheduling. RESEARCH Assumption A2 confirms CancelledError propagates past `except Exception`. The fixture rubric is sleep-delay-agnostic (tests outcome: "resume succeeded; summary references notes.txt content"), so even a late cancel that lets the first turn finish still exercises the resume contract on the second turn. |
</threat_model>

<verification>
- All 5 task.toml files parse and validate.
- `load_suite(Path("tests/eval/golden"), suite="")` returns 5 entries with the expected ids.
- `python -m voss.cli eval --stub --suite golden -k 1 --out /tmp/voss-eval-smoke` writes 5 JSONL rows (best-effort manual smoke).
- `pytest -q -m "not slow and not live" tests/eval/` continues to pass — Plan 03's parametrize tests now exercise each fixture under stub (they will pass with `success: null` because no judge creds; collection succeeds).
</verification>

<success_criteria>
1. Five directories under `tests/eval/golden/` with the stable ids (01-analyze … 05-resume).
2. Each has a parseable `task.toml` validating against TaskSpec.
3. Task 03 has `auto_approve_edits=true`; task 02 has `mode="plan"`; task 05 uses its own fixture.
4. Task 04 fixture contains a working `.voss` sample (copy of `samples/classify.voss`).
5. Plan 03's parametrize tests for ids 01-05 either pass or are skipped via the existing skip guard.
</success_criteria>

<output>
After completion, create `.planning/phases/M5-eval-and-distribution-prep/M5-05-SUMMARY.md` summarizing: the 5 fixture ids and their distinctive contract (mode + auto_approve flag), the verbatim-copy provenance for task 04's sample.voss, the notes.txt distinctive content for task 05's judge verification, and the recorded cancel-timing assumption for task 05.
</output>
