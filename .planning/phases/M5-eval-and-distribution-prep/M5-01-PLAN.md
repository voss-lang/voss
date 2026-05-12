---
phase: M5
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - voss/eval/__init__.py
  - voss/eval/suite.py
  - tests/eval/__init__.py
  - tests/eval/test_suite_loads.py
  - tests/eval/test_task_spec.py
  - tests/eval/test_fixture_isolation.py
autonomous: true
requirements:
  - EVAL-01
must_haves:
  truths:
    - "`voss/eval/` is a real Python package and `from voss.eval.suite import TaskSpec, load_suite` works."
    - "TaskSpec validates a minimal task.toml shape (prompt/mode/rubric) and rejects unknown keys."
    - "load_suite walks a directory of NN-slug subdirs and returns [(task_id, TaskSpec)] sorted by id."
    - "Per-run fixture isolation helper produces a fresh git-initialized cwd containing the fixture contents."
  artifacts:
    - path: "voss/eval/__init__.py"
      provides: "Package marker + run_suite re-export stub (function imported lazily from runner.py — Wave 2)."
      contains: "from .runner import run_suite"
    - path: "voss/eval/suite.py"
      provides: "TaskSpec pydantic model + load_task + load_suite"
      exports: ["TaskSpec", "load_task", "load_suite"]
      contains: "class TaskSpec(BaseModel):"
    - path: "tests/eval/__init__.py"
      provides: "test package marker (empty)"
    - path: "tests/eval/test_suite_loads.py"
      provides: "Test: suite loader finds exactly the 5 expected fixture ids"
    - path: "tests/eval/test_task_spec.py"
      provides: "Test: TaskSpec accepts valid data, rejects unknown keys, rejects invalid mode"
    - path: "tests/eval/test_fixture_isolation.py"
      provides: "Test: _prepare_fixture creates git-init cwd, two runs do not share state"
  key_links:
    - from: "voss/eval/suite.py"
      to: "pydantic.BaseModel"
      via: "TaskSpec inherits from BaseModel with ConfigDict(extra='forbid')"
      pattern: "model_config\\s*=\\s*ConfigDict\\(extra=\"forbid\"\\)"
    - from: "voss/eval/suite.py"
      to: "stdlib tomllib"
      via: "load_task reads task.toml via tomllib.loads"
      pattern: "import tomllib"
---

<objective>
Stand up the `voss/eval/` package skeleton plus the `TaskSpec` pydantic schema, `load_suite` directory walker, and the per-run fixture-isolation helper. This is the Wave 0 contract: every downstream wave (judge, runner, summary, fixtures, packaging) imports from `voss.eval.suite` or relies on `_prepare_fixture` for hermetic per-run cwds. No CLI surface here; no judge; no runner. Just the loader, the validated TOML schema, and the helper that gives every later run a clean tempdir.

Purpose: All five EVAL-01 fixtures (Wave 4) must validate against `TaskSpec`. The Wave 2 runner constructs `PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)` from `TaskSpec` instances. The fixture-isolation helper is the per-run hermetic boundary referenced by D-06.

Output: `voss/eval/__init__.py`, `voss/eval/suite.py`, three pytest files under `tests/eval/`, and the empty package marker.
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
@voss/harness/agent.py
@voss/harness/cognition.py

<interfaces>
<!-- Pydantic Plan model (analog for TaskSpec) — voss/harness/agent.py:43-58 -->
class Plan(BaseModel):
    rationale: str = Field(description="...")
    steps: list[ToolCall] = Field(default_factory=list, description="...")
    confidence: float = Field(ge=0.0, le=1.0, description="...")
    open_question: str | None = Field(default=None, ...)
    final_when_done: str = Field(default="", ...)

<!-- M1 D-07 modes — Literal["plan", "edit", "auto"] -->
<!-- M5 D-07 task.toml shape (target for TaskSpec) -->
# prompt = "..."
# mode = "plan|edit|auto"
# rubric = "..."         # PASS/FAIL plaintext
# judge_inputs = ["final", "file_diff"]   # default both
# provider = "..."        # optional
# model = "..."           # optional
# auto_approve_edits = true   # only for task 03

<!-- Per-run git-init fixture pattern — M5-RESEARCH §Code Examples -->
# shutil.copytree(task_dir / "fixture", tmp / "fixture")
# git init -q -b main
# git -c user.email=eval@voss -c user.name=eval add -A
# git -c user.email=eval@voss -c user.name=eval commit -q -m init
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create voss/eval/ package + TaskSpec model + load_suite</name>
  <files>voss/eval/__init__.py, voss/eval/suite.py</files>
  <read_first>
    - voss/harness/agent.py:43-58 — Plan BaseModel + Field constraints pattern (analog for TaskSpec)
    - voss_runtime/memory/__init__.py:1-3 — empty package marker shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"voss/eval/suite.py (NEW) — Wave 0 Pattern 1" (lines 113-156) — exact target shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-05, D-07 — task_id = directory basename; task.toml schema (prompt, mode, rubric, judge_inputs, provider, model, auto_approve_edits)
    - .planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md §"Code Examples" (lines 263-275) — verified TaskSpec target
  </read_first>
  <behavior>
    - TaskSpec(prompt="x", mode="plan", rubric="PASS if ok") constructs successfully; judge_inputs defaults to ["final", "file_diff"]; auto_approve_edits defaults to False.
    - TaskSpec(prompt="x", mode="rust", rubric="...") raises pydantic ValidationError (mode is Literal["plan","edit","auto"]).
    - TaskSpec(prompt="x", mode="plan", rubric="...", typo_field=1) raises pydantic ValidationError (ConfigDict(extra="forbid")).
    - TaskSpec(prompt="x", mode="edit", rubric="...", auto_approve_edits=True) round-trips auto_approve_edits=True.
    - load_task(task_dir) reads task_dir/"task.toml" via stdlib tomllib and returns a validated TaskSpec.
    - load_suite(suite_root, suite="") on a directory containing N subdirs each with task.toml returns N (task_id, TaskSpec) tuples sorted by task_id (alphabetical).
    - load_suite ignores entries in suite_root that are NOT directories or that lack a task.toml.
  </behavior>
  <action>
    Create `voss/eval/__init__.py` with module docstring "voss.eval — golden-suite evaluation harness (M5)." and a lazy re-export comment line: `# from .runner import run_suite  # Wave 2 will land runner.py`. Do NOT import .runner yet (runner.py does not exist until Plan 03); the marker file is empty body otherwise per the analog `voss_runtime/memory/__init__.py:1-3`.

    Create `voss/eval/suite.py` with:
    - `from __future__ import annotations`
    - `import tomllib` (stdlib at python>=3.11 per pyproject.toml:9)
    - `from pathlib import Path`
    - `from typing import Literal`
    - `from pydantic import BaseModel, ConfigDict, Field`
    - Class `TaskSpec(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and fields per D-07: `prompt: str` (with Field description), `mode: Literal["plan", "edit", "auto"]`, `rubric: str` (with Field description), `judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]`, `provider: str | None = None`, `model: str | None = None`, `auto_approve_edits: bool = False`.
    - Function `load_task(task_dir: Path) -> TaskSpec` that reads `task_dir / "task.toml"` via `tomllib.loads(...)` and returns `TaskSpec.model_validate(data)`.
    - Function `load_suite(suite_root: Path, suite: str = "golden") -> list[tuple[str, TaskSpec]]` per M5-PATTERNS.md line 141-149: if `suite_root.name == suite` or `suite == ""`, treat `suite_root` as the suite directory directly; otherwise resolve to `suite_root / suite`. Walk sorted children, skip non-directories and dirs without task.toml. Return list of (basename, TaskSpec) tuples.
    - task_id is `task_dir.name` (directory basename) per D-05 — stable identifier written to JSONL row `task_id` field (D-04).
    - Use `tomllib`, NOT third-party `tomli` (RESEARCH §"Don't Hand-Roll"). Use `ConfigDict(extra="forbid")` per RESEARCH §"Common Pitfalls: schema drift".
    - Add module docstring `"""Task suite loader + TaskSpec schema (M5 D-05, D-07)."""`.
    - Pydantic `BaseModel` + `ConfigDict` + `Field` import path mirrors `voss/harness/agent.py:43`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "from voss.eval.suite import TaskSpec, load_task, load_suite; s = TaskSpec(prompt='x', mode='plan', rubric='PASS if ok'); assert s.judge_inputs == ['final','file_diff']; assert s.auto_approve_edits is False; print('OK')"</automated>
  </verify>
  <done>
    `voss/eval/__init__.py` and `voss/eval/suite.py` exist. `TaskSpec` imports and constructs with minimal fields. `load_suite` is importable. No runtime imports of `runner` or `judge` (these modules do not yet exist).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Pytest coverage for TaskSpec + suite loader + fixture isolation helper</name>
  <files>tests/eval/__init__.py, tests/eval/test_task_spec.py, tests/eval/test_suite_loads.py, tests/eval/test_fixture_isolation.py</files>
  <read_first>
    - tests/parser/test_examples.py:1-30 — directory walk + count assertion analog (for test_suite_loads.py)
    - tests/harness/test_agent_integration.py — pydantic round-trip + ValidationError pattern (for test_task_spec.py)
    - tests/examples/helpers.py:60-69 — `run_voss` subprocess (referenced by isolation test design)
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/test_suite_loads.py", §"test_task_spec.py", §"test_fixture_isolation.py" (lines 749-859) — target shapes
    - .planning/phases/M5-eval-and-distribution-prep/M5-VALIDATION.md rows `task-spec-model`, `suite-loads`, `fixture-isolation` (Wave 0)
  </read_first>
  <behavior>
    - `pytest tests/eval/test_task_spec.py -q` passes 4 tests: minimal spec defaults, invalid mode raises, unknown key raises, auto_approve_edits round-trip.
    - `pytest tests/eval/test_suite_loads.py -q` passes 2 tests: against an inline fixture dir built in `tmp_path`, load_suite finds exactly the expected ids; each task parses with non-empty prompt/rubric and a valid mode.
    - `pytest tests/eval/test_fixture_isolation.py -q` passes 2 tests: _prepare_fixture creates a .git directory inside the destination and copies seed files; two independent invocations produce independent trees (mutating one does not affect the other).
    - All three test files run under `pytest -q -m "not slow and not live"` (no markers needed — pure unit tests).
  </behavior>
  <action>
    Create `tests/eval/__init__.py` as empty file (package marker; mirror `tests/harness/__init__.py`).

    Create `tests/eval/test_task_spec.py` with 4 functions per M5-PATTERNS.md lines 789-816:
    - `test_minimal_spec`: TaskSpec(prompt="x", mode="plan", rubric="PASS if ok") — asserts judge_inputs == ["final","file_diff"] and auto_approve_edits is False.
    - `test_invalid_mode`: pytest.raises(pydantic.ValidationError) on `TaskSpec(prompt="x", mode="rust", rubric="...")`.
    - `test_unknown_key_rejected`: pytest.raises(pydantic.ValidationError) on `TaskSpec(prompt="x", mode="plan", rubric="...", typo_field=1)` — pins ConfigDict(extra="forbid").
    - `test_auto_approve_edits_round_trip`: TaskSpec(..., mode="edit", auto_approve_edits=True).auto_approve_edits is True.
    Import pydantic.ValidationError from pydantic.

    Create `tests/eval/test_suite_loads.py` per M5-PATTERNS.md lines 753-776, but build the fixture inline (avoid coupling Wave 0 tests to Wave 4 golden fixtures which do not yet exist):
    - Build a fixture tree under `tmp_path`: create 3 subdirs (e.g., `01-foo`, `02-bar`, `03-baz`) each containing a minimal `task.toml` with `prompt`, `mode = "plan"`, `rubric` strings.
    - Also create one non-directory file (e.g., `README.md`) and one dir without a task.toml (e.g., `empty/`) — confirm both are skipped.
    - `test_suite_finds_expected_fixtures`: load_suite(tmp_path, suite="") returns exactly 3 entries with ids `{"01-foo","02-bar","03-baz"}` and they are sorted alphabetically.
    - `test_each_task_parses`: every returned spec has non-empty prompt, non-empty rubric, mode in {"plan","edit","auto"}.
    Call signature: `load_suite(tmp_path, suite="")` — when suite is empty string OR matches `suite_root.name`, suite_root IS the directory walked (mirror the implementation choice from Task 1).

    Create `tests/eval/test_fixture_isolation.py` with the helper imported via a forward-compatible alias. Because `voss/eval/runner.py` does not exist yet in Wave 0, define the helper inline in this test module (verbatim copy of the target `_prepare_fixture` shape from M5-PATTERNS.md lines 390-399) and add a TODO comment: `# TODO Wave 2: replace inline helper with `from voss.eval.runner import _prepare_fixture`.` This keeps Wave 0 self-contained while pinning the contract.
    - `test_prepare_fixture_creates_git_repo`: build `src/fixture/hello.txt` containing `"hi\n"`, call _prepare_fixture(src, tmp_path / "run0"), assert (cwd / ".git").is_dir() and (cwd / "hello.txt").read_text() == "hi\n".
    - `test_two_runs_dont_share_state`: build src once; call _prepare_fixture twice with different dest dirs; mutate the first; assert second is unchanged.
    Use subprocess.run for `git init -q -b main`, `git add -A`, `git -c user.email=eval@voss -c user.name=eval commit -q -m init` per M5-PATTERNS.md lines 390-399.

    All three test files: only stdlib + pydantic + pytest imports.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest -q -m "not slow and not live" tests/eval/test_task_spec.py tests/eval/test_suite_loads.py tests/eval/test_fixture_isolation.py</automated>
  </verify>
  <done>
    All three test files pass on a clean checkout. `tests/eval/__init__.py` exists. Inline `_prepare_fixture` in test_fixture_isolation.py carries a TODO marker pointing to its Wave 2 home (voss/eval/runner.py).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml → TaskSpec | Untrusted TOML input (golden fixture authors, possibly future user-authored suites) crosses into the Python type system |
| fixture/ tree → tempdir | Files copied into a per-run cwd that subsequent agent runs will read and possibly write |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M5-01-schema-drift | T (Tampering) | voss/eval/suite.py:TaskSpec | mitigate | ConfigDict(extra="forbid") rejects unknown keys; `test_unknown_key_rejected` pins this. Mode field is `Literal[...]` so typos fail validation. |
| T-M5-01-fixture-leak | I (Info Disclosure) / T (Tampering) | _prepare_fixture | mitigate | Wave 0 helper uses `tmp_path` only; never writes outside the destination dir. `test_two_runs_dont_share_state` pins independence. Runner (Wave 2) wraps invocations in `tempfile.TemporaryDirectory()` which auto-cleans on context exit. |
| T-M5-01-toml-injection | T (Tampering) | load_task | accept | tomllib (stdlib) parses TOML safely; pydantic validates types. No code execution from TOML content. |
</threat_model>

<verification>
- `pytest -q -m "not slow and not live" tests/eval/` passes (all Wave 0 tests).
- `python -c "from voss.eval.suite import TaskSpec, load_task, load_suite"` exits 0.
- No imports of `voss.eval.runner`, `voss.eval.judge`, or `voss.eval.summary` (these are introduced in later plans).
</verification>

<success_criteria>
1. `voss/eval/` is an importable package.
2. `TaskSpec` validates minimal task.toml shape; rejects unknown keys and invalid modes.
3. `load_suite` returns sorted (task_id, TaskSpec) tuples; skips non-directories and dirs without task.toml.
4. Per-run fixture isolation helper produces a fresh git-init cwd; two invocations are independent.
5. All Wave 0 tests pass under `pytest -q -m "not slow and not live"`.
</success_criteria>

<output>
After completion, create `.planning/phases/M5-eval-and-distribution-prep/M5-01-SUMMARY.md` summarizing: TaskSpec field allowlist, load_suite call signature (especially the `suite=""` convention), the inline test_fixture_isolation helper TODO marker pointing to Wave 2's runner home.
</output>
