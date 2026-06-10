---
phase: E3-surface-e2e
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/eval/suite.py
  - voss/eval/runner.py
  - tests/eval/test_voss_eval_stub.py
  - tests/eval/test_task_spec.py
autonomous: true
requirements: [EVSRF-01]
must_haves:
  truths:
    - "TaskSpec accepts surface=cli:do|cli:chat|cli:edit|serve|internal and defaults to internal"
    - "Golden tasks with no surface key still load and run unchanged (back-compat)"
    - "TaskSpec accepts an optional target_file (None default) for cli:edit scenarios"
    - "The JSONL row carries an additive surface field equal to the task's surface"
    - "The runner dispatches per-surface in _drive_task; internal keeps the existing path byte-for-byte"
    - "REQUIRED_FIELDS sentinel includes surface (set equality stays exact)"
  artifacts:
    - path: "voss/eval/suite.py"
      provides: "surface + target_file fields on TaskSpec (additive, extra=forbid safe)"
      contains: "surface"
    - path: "voss/eval/runner.py"
      provides: "surface dispatch skeleton in _drive_task + additive surface JSONL field"
      contains: "spec.surface"
    - path: "tests/eval/test_voss_eval_stub.py"
      provides: "REQUIRED_FIELDS sentinel updated with surface (same plan as the field)"
      contains: "surface"
  key_links:
    - from: "voss/eval/runner.py _drive_task"
      to: "spec.surface"
      via: "match/if dispatch; internal -> existing run_turn path unchanged"
      pattern: "spec\\.surface|surface =="
    - from: "voss/eval/runner.py run_suite row dict"
      to: "spec.surface"
      via: "additive row key after checks"
      pattern: "\"surface\""
---

<objective>
Extend the E1 substrate schema and runner with the `surface` routing field — the foundation every E3 driver consumes (D-04, EVSRF-01). Add `surface` and `target_file` fields to `TaskSpec`, an additive `surface` field to the JSONL row, the `REQUIRED_FIELDS` sentinel update (co-located per the known stale-sentinel hazard), and a `_drive_task` dispatch skeleton that routes `internal` to the existing path unchanged and stubs the four new surfaces with a clear "not yet implemented" crash_reason (filled in by E3-02 and E3-03).

This is contract-first: it defines the schema and dispatch seam so E3-02 (CLI drivers) and E3-03 (serve driver) implement against a fixed interface with no codebase scavenger hunt.

HARD PRECONDITION: E1-03 and E1-04 must be merged before E3 executes (E3 consumes `run_suite(max_turns=...)`, `_run_checks`, row fields `gate_pass`/`capped`/`checks`, judge guard `not capped`, `get_eval_max_turns`/`get_eval_judge_model`). Task 1 includes a gate check that STOPS execution with an "execute E1 first" message if `gate_pass` is absent from `voss/eval/runner.py`.

Purpose: One additive schema + dispatch seam; no behavior change for existing golden/internal tasks.
Output: extended TaskSpec, additive JSONL surface field, updated sentinel, dispatch skeleton, surface-field unit tests.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E3-surface-e2e/E3-CONTEXT.md
@.planning/phases/E3-surface-e2e/E3-RESEARCH.md
@.planning/phases/E3-surface-e2e/E3-PATTERNS.md

<interfaces>
<!-- TaskSpec today (voss/eval/suite.py:41-54) — extra="forbid"; new fields MUST be explicit model fields: -->
class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str
    mode: Literal["plan", "edit", "auto"]
    rubric: str
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False
    tools: list[str] = Field(default_factory=list)
    checks: list[AnyCheck] = Field(default_factory=list)   # E1-01

<!-- _drive_task dispatch point today (voss/eval/runner.py:241-292): -->
async def _drive_task(task_id, spec, *, cwd, provider, model, stub=False, max_turns=15)
    -> tuple[SessionRecord, str, str | None, bool]:   # (record, final, crash_reason_or_None, capped)
    ...
    if task_id.startswith("05-"):
        record, final, capped = await _drive_resume(...)   # existing resume path
    else:
        configure(max_iterations=max_turns); result = await run_turn(...)   # existing in-process path

<!-- run_suite row dict today (voss/eval/runner.py:456-478) — additive only, never reorder: -->
row = { task_id, run_idx, success, cost_usd, confidence, duration_s,
        judge_verdict, judge_confidence, judge_rationale, provider, model,
        judge_model, live, seed, voss_version, started_at,
        gate_pass, capped, checks }   # E1-03 added the last three
<!-- E3-01 appends: "surface": getattr(spec, "surface", "internal") -->

<!-- REQUIRED_FIELDS sentinel today (tests/eval/test_voss_eval_stub.py:11-31) holds all 19 keys above. -->
<!-- Two assertions `set(row) == REQUIRED_FIELDS` at lines 90 and 226 will break unless surface is added here. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: E1-merge gate check + surface/target_file fields on TaskSpec</name>
  <files>voss/eval/suite.py, tests/eval/test_task_spec.py</files>
  <read_first>
    - voss/eval/suite.py (FULL — TaskSpec lines 41-54, AnyCheck union lines 31-38, load_task/load_suite 57-70)
    - tests/eval/test_task_spec.py (FULL — test_checks_* pattern lines 39-125 is the analog for the new field tests)
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (suite.py section lines 23-51 — exact fields to add)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (Pattern 1 lines 194-215, target_file rationale lines 230-233 + Open Question 1 lines 730-733)
  </read_first>
  <action>
    GATE FIRST: run `grep -q "gate_pass" voss/eval/runner.py`. If it returns non-zero (gate_pass absent), STOP immediately and emit to the operator: "E1-03 not merged — execute E1 (waves 1-3) before E3. E3 consumes run_suite(max_turns=...), _run_checks, gate_pass/capped/checks row fields. Aborting." Do not modify any files. (On this checkout the marker IS present — E1-03/E1-04 SUMMARYs exist on disk — so the gate passes and execution proceeds.)

    Then in voss/eval/suite.py, add two fields to TaskSpec immediately after the `checks` field (copy the `checks` optional-with-default pattern; extra="forbid" is satisfied because these are explicit fields, not unknown keys):
      surface: Literal["internal", "cli:do", "cli:chat", "cli:edit", "serve"] = "internal"
      target_file: str | None = None   # required by the cli:edit driver; None for every other surface

    `Literal` is already imported (used by `mode`). Do NOT touch AnyCheck, load_task, or load_suite. Golden tasks have no `surface` key → default `"internal"` → unchanged validation.

    Add five unit tests to tests/eval/test_task_spec.py following the existing `test_checks_*` style (use TaskSpec(...) for happy paths and TaskSpec.model_validate({...}) + pytest.raises(ValidationError) for the rejection case):
      test_surface_defaults_internal — TaskSpec(prompt, mode="plan", rubric) → spec.surface == "internal"
      test_surface_cli_do — model_validate with surface="cli:do" → spec.surface == "cli:do"
      test_surface_invalid_rejected — model_validate with surface="bogus" raises ValidationError
      test_target_file_defaults_none — default spec → spec.target_file is None
      test_target_file_cli_edit — model_validate with surface="cli:edit", target_file="calc.py" → spec.target_file == "calc.py"
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_task_spec.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "gate_pass" voss/eval/runner.py` succeeds (E1 merged) — the plan would have aborted otherwise.
    - `grep -c "surface" voss/eval/suite.py` >= 1 and `grep -c "target_file" voss/eval/suite.py` >= 1.
    - The new `surface` field is a `Literal["internal", "cli:do", "cli:chat", "cli:edit", "serve"]` with default `"internal"`; `target_file` is `str | None = None`.
    - All five new tests pass; `TaskSpec(prompt="x", mode="plan", rubric="...").surface == "internal"`.
    - `TaskSpec.model_validate({"prompt":"x","mode":"plan","rubric":"...","surface":"bogus"})` raises `pydantic.ValidationError`.
    - Existing golden tasks still load: `.venv/bin/python -c "from voss.eval.suite import load_suite; from pathlib import Path; print(len(load_suite(Path('tests/eval/golden'), suite='golden')))"` prints 6 with no error.
  </acceptance_criteria>
  <done>TaskSpec carries surface + target_file additively; golden tasks load unchanged; E1-merge precondition verified; surface-field tests green.</done>
</task>

<task type="auto">
  <name>Task 2: Additive surface JSONL field + REQUIRED_FIELDS sentinel + dispatch skeleton</name>
  <files>voss/eval/runner.py, tests/eval/test_voss_eval_stub.py</files>
  <read_first>
    - voss/eval/runner.py (FULL — _drive_task lines 241-292 dispatch point, the existing `if task_id.startswith("05-")` branch; run_suite row dict lines 456-478)
    - tests/eval/test_voss_eval_stub.py (REQUIRED_FIELDS set lines 11-30; the two `set(row) == REQUIRED_FIELDS` assertions at lines 90 and 226)
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (runner.py dispatch section lines 237-267; sentinel section lines 483-495)
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md (D-04 — JSONL fields additive only, never reorder/remove)
  </read_first>
  <action>
    In voss/eval/runner.py:

    (1) DISPATCH SKELETON in _drive_task: before the existing `if task_id.startswith("05-")` branch, read `surface = spec.surface` (the field now always exists; no getattr needed at the spec level). Add a dispatch:
        - surface in {"cli:do", "cli:chat", "cli:edit", "serve"}: for THIS plan return a not-yet-implemented crash_reason so the row records cleanly — `return record, "", f"surface {surface!r} driver not implemented (E3-02/E3-03)", False`. E3-02 and E3-03 replace these branches with real driver calls (await _drive_cli_* / await _drive_serve). Keep the return-tuple shape `(record, final, crash_reason_or_None, capped)`.
        - else (surface == "internal"): fall through to the EXISTING `if task_id.startswith("05-") ... else ... run_turn` logic completely unchanged. Do NOT alter the internal path's behavior.
      Use a registry dict or if/elif (Claude's discretion per D-04 discretion note) — keep it readable; the four CLI/serve branches dispatch by surface string, the internal branch is the existing code.

    (2) ROW: append `"surface": spec.surface` as the LAST key in the run_suite row dict (after `"checks": check_results`). Do not reorder or remove any existing key (M5 D-04, additive only).

    In tests/eval/test_voss_eval_stub.py: add `"surface"` to the REQUIRED_FIELDS set (do not remove any existing field). This keeps both `set(row) == REQUIRED_FIELDS` assertions exact after the row gains the field — co-located in the SAME plan that adds the field (known stale-sentinel hazard; MEMORY "voss stale sentinel tests").
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_voss_eval_stub.py tests/eval/test_task_spec.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '"surface"' voss/eval/runner.py` >= 1 (the row key).
    - `grep -c "surface" tests/eval/test_voss_eval_stub.py` >= 1; REQUIRED_FIELDS contains `"surface"` (20 fields total: 19 prior + surface).
    - Both `set(row) == REQUIRED_FIELDS` assertions pass against the live stub row (the stub suite run still emits exactly the REQUIRED_FIELDS set).
    - The `internal` dispatch path is unchanged: a stub golden run still produces non-crash rows — `grep -v '^#' voss/eval/runner.py | grep -c "task_id.startswith(\"05-\")"` >= 1 (the existing resume branch is preserved).
    - The four new surfaces dispatch to a not-implemented crash_reason in THIS plan (no NameError, no call to undefined `_drive_cli_*`): `.venv/bin/python -c "import voss.eval.runner"` imports cleanly.
    - `.venv/bin/python -m pytest tests/eval -q -m 'not live'` stays green (no regression in the internal/golden path).
  </acceptance_criteria>
  <done>surface is an additive JSONL field with the sentinel updated in-plan; _drive_task dispatches by surface with internal unchanged and the four new surfaces stubbed for E3-02/E3-03; full eval suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml (operator-authored) → TaskSpec validation | surface/target_file are operator input; extra="forbid" + Literal constrain the value space |
| eval row schema → sentinel test | additive field drift can silently invalidate REQUIRED_FIELDS (known project hazard) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E3-01 | Tampering | invalid surface value in task.toml | mitigate | Literal["internal","cli:do","cli:chat","cli:edit","serve"] rejects unknown values at validation (test_surface_invalid_rejected) |
| T-E3-02 | Tampering | sentinel masking row drift | mitigate | REQUIRED_FIELDS updated in the SAME plan that adds surface; both set-equality assertions enforce exactness |
| T-E3-03 | Denial | premature E3 execution before E1 merged | mitigate | Task 1 grep gate on gate_pass aborts with an "execute E1 first" message before any file change |
| T-E3-SC | Tampering | npm/pip/cargo installs | accept | E3 introduces zero new packages (RESEARCH Package Legitimacy Audit: not applicable); no install tasks in this plan |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval -q -m 'not live'` → full eval suite green (sentinel updated in-plan)
- TaskSpec rejects unknown surface; defaults to internal; target_file defaults None
- Golden suite loads 6 tasks unchanged; internal dispatch path byte-unchanged
- Row carries additive surface field; REQUIRED_FIELDS exact
</verification>

<success_criteria>
- surface + target_file additive on TaskSpec; golden/internal behavior unchanged (EVSRF-01, D-04)
- additive surface JSONL field; REQUIRED_FIELDS sentinel updated in-plan
- _drive_task dispatch seam in place; four surfaces stubbed for E3-02/E3-03; internal unchanged
- E1-merge precondition verified by grep gate
</success_criteria>

<output>
Create `.planning/phases/E3-surface-e2e/E3-01-SUMMARY.md` when done
</output>
