---
phase: E1-eval-substrate
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/eval/suite.py
  - voss/eval/runner.py
  - tests/eval/test_task_spec.py
  - tests/eval/test_checks.py
autonomous: true
requirements: [EVSUB-01]
must_haves:
  truths:
    - "A task.toml with cmd / file_exists / file_contains checks loads via load_task"
    - "The 6 existing golden task.toml files still load unchanged (no checks yet)"
    - "A malformed check entry raises a pydantic validation error"
    - "_run_checks runs all three check types against a cwd and returns (gate_pass, results)"
    - "_run_checks never short-circuits: every check appears in the results list"
  artifacts:
    - path: "voss/eval/suite.py"
      provides: "AnyCheck discriminated union + TaskSpec.checks field"
      contains: "class CmdCheck"
    - path: "voss/eval/runner.py"
      provides: "_run_checks executor (pure function, not yet wired into rows)"
      contains: "def _run_checks"
    - path: "tests/eval/test_checks.py"
      provides: "Unit tests for _run_checks (all three types, pass/fail, timeout)"
  key_links:
    - from: "voss/eval/suite.py TaskSpec.checks"
      to: "AnyCheck union"
      via: "list[AnyCheck] field with Discriminator('type')"
      pattern: "checks:\\s*list\\[AnyCheck\\]"
    - from: "tests/eval/test_checks.py"
      to: "voss.eval.runner._run_checks"
      via: "direct import + call"
      pattern: "_run_checks"
---

<objective>
Add the deterministic-check schema (`checks` discriminated union on `TaskSpec`) and a standalone check executor (`_run_checks`) that runs the three check types (`cmd`, `file_exists`, `file_contains`) against a task's fixture cwd. This is the schema + pure-function layer ONLY — wiring `_run_checks` into JSONL rows and the suite loop happens in plan E1-03.

Purpose: EVSUB-01 — TaskSpec must accept an optional `checks` list, validated by pydantic, with full back-compat (tasks without `checks` behave exactly as today). Establishing the executor as a pure `(checks, cwd) -> (gate_pass, results)` function lets plan E1-03 wire it without redefining contracts.
Output: Extended `TaskSpec`, `_run_checks` function, unit tests for both.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/E1-eval-substrate/E1-SPEC.md
@.planning/phases/E1-eval-substrate/E1-CONTEXT.md
@.planning/phases/E1-eval-substrate/E1-PATTERNS.md

<interfaces>
<!-- Current TaskSpec contract the new `checks` field extends. From voss/eval/suite.py. -->
TaskSpec (pydantic, ConfigDict(extra="forbid")):
  prompt: str
  mode: Literal["plan","edit","auto"]
  rubric: str
  judge_inputs: list[Literal["final","file_diff"]] = ["final","file_diff"]
  provider: str | None = None
  model: str | None = None
  auto_approve_edits: bool = False
  tools: list[str] = []
  # NEW: checks: list[AnyCheck] = Field(default_factory=list)

Existing subprocess pattern to mirror for cmd checks (voss/eval/runner.py _file_diff):
  subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)

Verdict in voss/eval/judge.py is the Literal-discriminator analog to copy for the check union.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add AnyCheck discriminated union + TaskSpec.checks field</name>
  <files>voss/eval/suite.py, tests/eval/test_task_spec.py</files>
  <read_first>
    - voss/eval/suite.py (current TaskSpec; extra="forbid"; load_task/load_suite — do not change loader logic)
    - voss/eval/judge.py (Literal-discriminator pydantic pattern to copy)
    - .planning/phases/E1-eval-substrate/E1-PATTERNS.md (suite.py section, lines 27-105 — exact union shape per D-01)
    - tests/eval/test_task_spec.py (existing TaskSpec tests — back-compat assertions must stay green)
  </read_first>
  <behavior>
    - A task dict with no `checks` key validates and yields `spec.checks == []` (back-compat).
    - A dict with `checks=[{type:"cmd", run:"true"}]` yields one CmdCheck with `timeout == 60` default.
    - A dict with `checks=[{type:"cmd", run:"true", timeout:5}]` honors the override.
    - A dict with `checks=[{type:"file_exists", path:"x"}]` yields one FileExistsCheck.
    - A dict with `checks=[{type:"file_contains", path:"x", text:"y"}]` yields one FileContainsCheck.
    - A dict with `checks=[{type:"bogus"}]` raises pydantic ValidationError.
    - A dict with `checks=[{type:"cmd", run:"true", extra_key:1}]` raises ValidationError (extra="forbid" on sub-models).
  </behavior>
  <action>
    In voss/eval/suite.py add three pydantic check models — `CmdCheck` (fields: `type: Literal["cmd"]`, `run: str`, `timeout: int = 60`), `FileExistsCheck` (`type: Literal["file_exists"]`, `path: str`), `FileContainsCheck` (`type: Literal["file_contains"]`, `path: str`, `text: str`) — each with `model_config = ConfigDict(extra="forbid")`. Build `AnyCheck = Annotated[Union[Annotated[CmdCheck, Tag("cmd")], Annotated[FileExistsCheck, Tag("file_exists")], Annotated[FileContainsCheck, Tag("file_contains")]], Discriminator("type")]`. Import `Annotated`, `Union` from typing and `Discriminator`, `Tag` from pydantic. Add field `checks: list[AnyCheck] = Field(default_factory=list)` as the last field on `TaskSpec`. Keep `TaskSpec.model_config = ConfigDict(extra="forbid")` and leave `load_task`/`load_suite` untouched — tomllib parses `[[checks]]` array-of-tables natively. Export the new check classes and `AnyCheck` in any `__all__` if present.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_task_spec.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `from voss.eval.suite import CmdCheck, FileExistsCheck, FileContainsCheck, AnyCheck` succeeds.
    - `TaskSpec.model_validate({"prompt":"p","mode":"plan","rubric":"r"}).checks == []`.
    - `TaskSpec.model_validate({...,"checks":[{"type":"cmd","run":"true"}]}).checks[0].timeout == 60`.
    - `TaskSpec.model_validate({...,"checks":[{"type":"bogus"}]})` raises `pydantic.ValidationError`.
    - All 6 existing golden task.toml files still load: `.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_suite; print(len(load_suite(Path('tests/eval/golden'), suite='golden')))"` prints `6`.
    - `tests/eval/test_task_spec.py` passes with zero failures.
  </acceptance_criteria>
  <done>TaskSpec validates all three check types and rejects malformed entries; tasks without checks unchanged; existing task-spec tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add _run_checks executor (pure function) + unit tests</name>
  <files>voss/eval/runner.py, tests/eval/test_checks.py</files>
  <read_first>
    - voss/eval/runner.py (lines 1-115 — imports already include subprocess, Path; _file_diff is the subprocess analog; _prepare_fixture shows the temp-git cwd shape checks run inside)
    - .planning/phases/E1-eval-substrate/E1-PATTERNS.md (runner.py section, lines 128-159 — exact _run_checks shape per D-02/D-03)
    - voss/eval/suite.py (the CmdCheck/FileExistsCheck/FileContainsCheck models from Task 1 — _run_checks consumes these typed objects)
  </read_first>
  <behavior>
    - `_run_checks([], cwd)` returns `(True, [])` — vacuous gate_pass.
    - cmd check `run="true"` in a valid cwd returns pass=True; `run="false"` returns pass=False; both appear in results.
    - cmd check that exceeds its `timeout` records `pass=False`, `detail="timeout"` and does not raise.
    - file_exists check returns pass=True when `cwd/path` exists, False otherwise.
    - file_contains returns pass=True only when the file exists AND contains the text substring.
    - A list mixing one failing and one passing check returns `gate_pass=False` with BOTH results present (no short-circuit).
  </behavior>
  <action>
    In voss/eval/runner.py add `def _run_checks(checks: list, cwd: Path) -> tuple[bool, list[dict]]`. Iterate ALL checks (no short-circuit, per D-02). For `type == "cmd"`: `subprocess.run(check.run, shell=True, cwd=cwd, capture_output=True, text=True, timeout=getattr(check, "timeout", 60), check=False)`; `passed = returncode == 0`; on pass set `detail = stdout[:200]` else `detail = stderr[:200]`; catch `subprocess.TimeoutExpired` → `passed=False, detail="timeout"`. For `type == "file_exists"`: `passed = (cwd / check.path).exists()`, `detail=""`. For `type == "file_contains"`: `p = cwd / check.path; passed = p.exists() and check.text in p.read_text()`, `detail=""`. Append `{"type": check.type, "pass": passed, "detail": detail}` per check. Return `(all(r["pass"] for r in results), results)`. Place the function near `_file_diff`. Use stdlib only (subprocess/pathlib already imported) — no new imports, no new dependencies (SPEC constraint).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_checks.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `tests/eval/test_checks.py` exists and tests all behaviors above.
    - `_run_checks([], tmp)` returns `(True, [])`.
    - A cmd check `run="exit 1"` yields a result with `pass is False`; a `run="exit 0"` yields `pass is True`.
    - A cmd check `run="sleep 5", timeout=1` yields `pass=False, detail="timeout"` and the call returns within ~2s (no hang).
    - file_contains against a file lacking the text yields `pass=False`.
    - A mixed list `[passing, failing]` returns `gate_pass=False` and `len(results)==2`.
    - `grep -c "def _run_checks" voss/eval/runner.py` returns `1`.
  </acceptance_criteria>
  <done>_run_checks runs all three check types against a cwd, never short-circuits, handles timeouts without hanging, and is unit-tested green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml `cmd` check → shell | `cmd` checks run `shell=True` against repo-committed fixture task.toml files (trusted authors), but the shell string is operator-supplied at fixture-authoring time |
| check execution → fixture cwd | checks run inside the isolated temp git fixture copy (M5 D-06), not the operator's repo |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E1-01 | Elevation | `_run_checks` cmd `shell=True` | accept | Checks come only from repo-committed golden task.toml (trusted, code-reviewed); no untrusted/network-sourced task definitions in E1. Documented injection posture: do not load task.toml from untrusted sources. |
| T-E1-02 | Denial | runaway cmd check | mitigate | Per-check `timeout` (default 60s) caught via `subprocess.TimeoutExpired` → recorded fail, never hangs the run |
| T-E1-03 | Tampering | check escapes fixture | mitigate | `cwd` is the isolated temp git fixture copy (M5 D-06), not the operator repo; checks see only the seeded fixture state |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/test_task_spec.py tests/eval/test_checks.py -q` → all green
- `.venv/bin/python -m pytest tests/eval/ -q` → existing 30 eval tests still green (no regression from schema addition)
- All 6 golden task.toml files load via `load_suite` (count == 6)
</verification>

<success_criteria>
- TaskSpec validates `checks` with all three check types; malformed entries raise ValidationError
- Tasks without `checks` are unchanged (back-compat); existing eval suite green
- `_run_checks` is a pure `(checks, cwd) -> (gate_pass, results)` function, never short-circuits, timeout-safe
- No JSONL/row changes in this plan (that is E1-03)
</success_criteria>

<output>
Create `.planning/phases/E1-eval-substrate/E1-01-SUMMARY.md` when done
</output>
