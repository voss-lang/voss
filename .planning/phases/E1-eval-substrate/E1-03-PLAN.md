---
phase: E1-eval-substrate
plan: 03
type: execute
wave: 2
depends_on: [E1-01, E1-02]
files_modified:
  - voss/eval/runner.py
  - voss/eval/summary.py
  - voss/templates/eval/summary.md.jinja
  - tests/eval/test_voss_eval_stub.py
  - tests/eval/test_summary_md.py
  - tests/eval/test_hybrid_gate.py
autonomous: true
requirements: [EVSUB-02, EVSUB-04, EVSUB-06]
must_haves:
  truths:
    - "A task whose check fails but whose judge says pass is recorded FAIL (gate decides pass/fail)"
    - "A task with no checks falls back to judge-only verdict (current behavior)"
    - "JSONL rows carry gate_pass, capped, and per-check results array (additive — existing columns unbroken)"
    - "A task forced past the turn cap records capped:true + FAIL, judge skipped, no hang"
    - "Run output prints 'N tasks · max M turns/task' before the first model call"
    - "Default judge model differs from actor model; both recorded; --judge-model honored; same-model warns not errors"
    - "summary.md shows gate-pass rate and judge rate as separate columns"
  artifacts:
    - path: "voss/eval/runner.py"
      provides: "checks wired into rows, turn cap, capped-skip-judge, judge-model default split, same-model warning, run header"
      contains: "gate_pass"
    - path: "voss/eval/summary.py"
      provides: "gate-pass-rate + judge-rate aggregation"
      contains: "gate_rate"
    - path: "voss/templates/eval/summary.md.jinja"
      provides: "gate pass + judge pass header lines + gate-pass per-task column"
    - path: "tests/eval/test_hybrid_gate.py"
      provides: "gate-overrides-judge, no-checks-fallback, cap-records-fail tests under stub"
  key_links:
    - from: "voss/eval/runner.py run_suite loop"
      to: "voss.eval.runner._run_checks (from E1-01)"
      via: "call after _drive_task, before judge; gate_pass into row"
      pattern: "_run_checks"
    - from: "voss/eval/runner.py judge guard"
      to: "capped skip"
      via: "crash_reason is None and not capped condition"
      pattern: "not capped"
    - from: "voss/eval/runner.py run_suite"
      to: "voss.harness.config.get_eval_max_turns / get_eval_judge_model (from E1-02)"
      via: "resolve cap + judge default with flag > config > default precedence"
      pattern: "get_eval_(max_turns|judge_model)"
---

<objective>
Wire the E1-01 check executor and E1-02 config defaults into the runner: hybrid gate/judge result plumbing (EVSUB-02 — checks decide pass/fail, judge scores quality), the per-task `max_turns` cap with upfront run-size print and capped-skip-judge (EVSUB-04), and the judge-model default split with same-model warning + dual-model recording (EVSUB-06). Extend `summary.py` + the jinja template with gate-pass vs judge-rate columns. Update the two sentinel tests (`test_voss_eval_stub.py` REQUIRED_FIELDS, `test_summary_md.py` golden bytes) IN THIS PLAN since their pins change here.

Purpose: This is the integration plan that turns the schema (E1-01) + config (E1-02) into observable hybrid behavior. New JSONL fields (`gate_pass`, `capped`, `checks`) are additive — existing columns never break (M5 D-04).
Output: hybrid-scoring runner, capped-task path, judge split, extended summary + template, updated sentinel tests, hybrid-behavior tests.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/E1-eval-substrate/E1-SPEC.md
@.planning/phases/E1-eval-substrate/E1-CONTEXT.md
@.planning/phases/E1-eval-substrate/E1-PATTERNS.md
@.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md

<interfaces>
<!-- From E1-01 (must be merged first): -->
voss.eval.runner._run_checks(checks: list, cwd: Path) -> tuple[bool, list[dict]]
voss.eval.suite.TaskSpec.checks: list[AnyCheck]   # [] when task has no checks

<!-- From E1-02 (must be merged first): -->
voss.harness.config.get_eval_max_turns() -> int          # default 15
voss.harness.config.get_eval_judge_model() -> str         # default "gpt-5.5-mini"
voss/harness/cli.py eval_cmd already forwards max_turns=<flag> into run_suite(...)

<!-- Current runner row (voss/eval/runner.py:358-377) — append new fields, never reorder/remove existing: -->
row keys today: task_id, run_idx, success, cost_usd, confidence, duration_s,
  judge_verdict, judge_confidence, judge_rationale, provider, model, judge_model,
  live, seed, voss_version, started_at
NEW additive keys: gate_pass (bool), capped (bool), checks (list[dict])

<!-- Current judge guard (runner.py:339-345): -->
verdict=None; judge_verdict="skipped"
if crash_reason is None and judge_provider is not None: <call judge_run>
  => NEW guard adds "and not capped"

<!-- Current model resolution (runner.py:322-323): -->
model_eff = "__stub__" if stub else (spec.model or model)
judge_model_eff = judge_model or model_eff or get_config().default_model
  => NEW: judge default = get_eval_judge_model() when no --judge-model and not stub;
     precedence --judge-model flag > [eval].judge_model config > pinned default.
     If judge_model_eff == model_eff (and not stub): click.echo warning to stderr, proceed (D-11).

<!-- Capped row (D-05): capped => success=False, judge_verdict="skipped", judge skipped. -->
<!-- judge_verdict:"skipped" already a known sentinel (stub-no-creds path). -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wire checks into rows + turn cap + capped-skip-judge + run header</name>
  <read_first>
    - voss/eval/runner.py (FULL — run_suite loop lines 272-381, _drive_task lines 198-239, _drive_resume lines 149-195, judge guard 339-356, row dict 358-377)
    - voss/eval/suite.py (TaskSpec.checks field from E1-01; the AnyCheck typed objects _run_checks consumes)
    - voss/harness/config.py (get_eval_max_turns / get_eval_judge_model from E1-02)
    - .planning/phases/E1-eval-substrate/E1-PATTERNS.md (runner.py section lines 109-191 — hook points for header, cap, capped row, judge skip per D-02/D-04/D-05; same-model warning lines 572-581 per D-11)
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md (D-04 JSONL schema — new fields are additive only)
  </read_first>
  <behavior>
    - Stub run of a task WITH a passing check => row has gate_pass=True, checks non-empty, success reflects judge (or null under stub-no-judge).
    - Stub run of a task WITH a failing check => row gate_pass=False AND success=False regardless of judge_verdict (gate overrides judge).
    - A task with NO checks => gate_pass=True (vacuous), checks=[], success falls back to judge verdict (current behavior preserved).
    - A task scripted to never finish under a small max_turns => row capped=True, success=False, judge_verdict="skipped", and the run returns without hanging.
    - run_suite prints "N tasks · max M turns/task" to stdout before the first model call.
    - Default judge model (no --judge-model, live) resolves to get_eval_judge_model(); recorded in row judge_model field distinct from model field.
    - --judge-model override equal to actor model => stderr warning, run proceeds, both recorded.
  </behavior>
  <action>
    In voss/eval/runner.py:

    (1) RUN HEADER: after `tasks` is built/filtered and the cap is resolved, before the `for task_id, spec in tasks:` loop, `click.echo(f"{len(tasks)} tasks · max {max_turns} turns/task")` to stdout (D-04 acceptance: shown before first model call).

    (2) CAP RESOLUTION: add `max_turns: int | None = None` to `run_suite(...)` signature; resolve `max_turns = max_turns if max_turns is not None else get_eval_max_turns()` (flag > config-default precedence, D-06). Import `get_eval_max_turns`, `get_eval_judge_model` from voss.harness.config.

    (3) TURN CAP ENFORCEMENT: thread `max_turns` into `_drive_task` (and `_drive_resume`). Per D-04/D-05, a task that does not finish within `max_turns` agent turns must hard-stop, returning a `capped=True` signal. Least-invasive hook (Claude's discretion per CONTEXT): count `run_turn` invocations in the drive loop; when the count would exceed `max_turns`, stop and signal capped. Extend `_drive_task`'s return to carry a `capped: bool` (e.g. return tuple gains a capped flag, or set crash_reason-style sentinel) so the run_suite loop can record it. Do NOT remove the existing crash_reason path.

    (4) CHECK EXECUTION: in the run_suite loop, after `_drive_task` returns and after `diff = _file_diff(cwd)`, call `gate_pass, check_results = _run_checks(spec.checks, cwd)` (cwd is the fixture temp dir). If `spec.checks` is empty, `_run_checks` returns `(True, [])` (vacuous) — preserving judge-only fallback.

    (5) JUDGE GUARD: change the judge guard to `if crash_reason is None and not capped and judge_provider is not None:` (D-05 — skip judge on capped). Capped => judge_verdict stays "skipped".

    (6) JUDGE-MODEL SPLIT (D-10/D-11): when not stub and no explicit `--judge-model`, default judge model = `get_eval_judge_model()` instead of `model_eff`. Keep precedence `judge_model` (flag) > config default > pinned. After resolving `judge_model_eff`, if `not stub and judge_model_eff == model_eff:` `click.echo(f"voss eval: judge model == actor model ({judge_model_eff!r}); proceeding", err=True)` (warn, never error).

    (7) ROW: append to the existing row dict (do NOT reorder existing keys): `"gate_pass": gate_pass`, `"capped": capped`, `"checks": check_results`. Set `success = False if (crash_reason or capped) else (False if not gate_pass else (verdict.verdict == "pass" if verdict else None))` — gate failure forces FAIL; no-checks + no-verdict stays None (stub). Keep `judge_model` recording the resolved judge_model_eff.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_hybrid_gate.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - New tests/eval/test_hybrid_gate.py covers: gate-overrides-judge (failing check => success False even if judge would pass), no-checks fallback (success follows judge / stays None under stub), capped path (capped=True, success=False, judge_verdict="skipped", no hang).
    - `grep -c "_run_checks" voss/eval/runner.py` ≥ 1; `grep -c "not capped" voss/eval/runner.py` ≥ 1; `grep -c "gate_pass" voss/eval/runner.py` ≥ 1.
    - Run header: a stub suite run's stdout contains a line matching `tasks · max` and `turns/task` before any provider output (assert in a test capturing stdout, or assert substring present in CLI stdout).
    - Capped test completes in bounded time (pytest does not hang; use a stub/scripted provider that never emits a terminal turn with a small `max_turns`).
    - Judge-model: a stub or unit-level assertion that with no --judge-model the resolved judge default == get_eval_judge_model() and differs from a gpt-5.5 actor default; --judge-model override honored.
    - Existing eval suite (minus the two sentinel tests updated in Task 2/3) still green: `.venv/bin/python -m pytest tests/eval -q --deselect tests/eval/test_summary_md.py::test_summary_renders_exact_markdown_bytes`.
  </acceptance_criteria>
  <done>Hybrid gate decides pass/fail; capped tasks recorded FAIL with judge skipped and no hang; run header prints task count + cap before first model call; judge-model split + same-model warning in place; new fields additive in the row.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend summary.py + jinja template with gate-pass and judge-rate columns; update golden-bytes sentinel</name>
  <read_first>
    - voss/eval/summary.py (FULL — aggregation lines 49-101, _mean_cost, _pearson, render context dict)
    - voss/templates/eval/summary.md.jinja (FULL 16 lines — current header + per-task table)
    - tests/eval/test_summary_md.py (FULL — test_summary_has_required_sections AND test_summary_renders_exact_markdown_bytes pin the EXACT rendered string; both must be updated to the new layout)
    - .planning/phases/E1-eval-substrate/E1-PATTERNS.md (summary.py + jinja sections lines 218-309 — exact new aggregation + template lines)
  </read_first>
  <behavior>
    - summary.md header gains a "gate pass rate" line and a "judge pass rate" line.
    - Per-task table gains a "gate pass" column between runs and pass rate.
    - Rows lacking the new fields (old JSONL) render gate/judge rates as "n/a" (back-compat via .get()).
    - The exact-bytes test asserts the new full rendered string.
  </behavior>
  <action>
    In voss/eval/summary.py add aggregation (mirror existing `scored`/`passes`/`overall_rate` with `.get()` guards for back-compat): `gate_rows = [r for r in rows if r.get("gate_pass") is not None]`, `gate_passes = sum(1 for r in gate_rows if r["gate_pass"])`, `gate_rate = gate_passes/len(gate_rows) if gate_rows else None`; `judge_rows = [r for r in rows if r.get("judge_verdict") not in (None,"skipped","error")]`, `judge_passes = sum(1 for r in judge_rows if r.get("judge_verdict")=="pass")`, `judge_rate = judge_passes/len(judge_rows) if judge_rows else None`. Per-task: add `gate_pass_rate` (gate-only rate for that task's rows, "n/a" if none). Pass new keys into the render context: `gate_rate`/`gate_passes`/`gate_total`, `judge_rate`/`judge_passes`/`judge_total` (format rates as `f"{x:.0%}"` or `"n/a"`).

    In voss/templates/eval/summary.md.jinja add after the `overall success rate` line: `- gate pass rate: {{ gate_rate }} ({{ gate_passes }}/{{ gate_total }})` and `- judge pass rate: {{ judge_rate }} ({{ judge_passes }}/{{ judge_total }})`. Change the per-task table header to `| task | runs | gate pass | pass rate | mean cost |` with matching alignment row, and the row body to include `{{ task.gate_pass_rate }}` before `{{ task.pass_rate }}`.

    In tests/eval/test_summary_md.py update BOTH tests: `test_summary_has_required_sections` — change the table-header assertion to the new 5-column header and add an assertion for "gate pass rate"; `test_summary_renders_exact_markdown_bytes` — regenerate the expected exact string to match the new header lines + 5-column table (run the function once during execution to capture the exact bytes, then pin them). The two fixture rows in the exact-bytes test lack the new fields, so gate/judge rates render "n/a" and per-task gate pass renders "n/a" — pin that.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_summary_md.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "gate_rate" voss/eval/summary.py` ≥ 1; `grep -c "judge_rate" voss/eval/summary.py` ≥ 1.
    - Template contains `gate pass rate` and `judge pass rate` lines and a per-task header `| task | runs | gate pass | pass rate | mean cost |`.
    - `test_summary_has_required_sections` asserts the new 5-column header and "gate pass rate".
    - `test_summary_renders_exact_markdown_bytes` passes against the regenerated exact string (no stale-byte failure).
    - Old-style rows (no gate_pass field) render gate/judge rate as "n/a" without KeyError.
    - `.venv/bin/python -m pytest tests/eval/test_summary_md.py -q` fully green.
  </acceptance_criteria>
  <done>summary.md surfaces gate-pass rate and judge rate as distinct columns; both summary tests (including the exact-bytes sentinel) updated and green; old rows degrade to "n/a".</done>
</task>

<task type="auto">
  <name>Task 3: Update REQUIRED_FIELDS sentinel in test_voss_eval_stub.py</name>
  <read_first>
    - tests/eval/test_voss_eval_stub.py (REQUIRED_FIELDS set lines 11-28; assertions `set(row) == REQUIRED_FIELDS` at lines 87 and 223)
    - voss/eval/runner.py (the row dict after Task 1 — confirm the exact new keys gate_pass/capped/checks)
  </read_first>
  <action>
    In tests/eval/test_voss_eval_stub.py add the three new additive keys to the `REQUIRED_FIELDS` set: `"gate_pass"`, `"capped"`, `"checks"`. This keeps the two `set(row) == REQUIRED_FIELDS` assertions accurate after Task 1 extends the row. Do not remove any existing field from the set (M5 D-04 — additive only). Do not change the subprocess env handling (the autouse conftest from E1-02 already supplies VOSS_DEV=1 via os.environ.copy()).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_voss_eval_stub.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `REQUIRED_FIELDS` contains `gate_pass`, `capped`, `checks` plus all 16 original fields (19 total).
    - `grep -c "gate_pass" tests/eval/test_voss_eval_stub.py` ≥ 1.
    - Both `set(row) == REQUIRED_FIELDS` assertions pass against the live stub row.
    - `.venv/bin/python -m pytest tests/eval/test_voss_eval_stub.py -q` fully green.
  </acceptance_criteria>
  <done>REQUIRED_FIELDS sentinel updated additively to match the extended row; stub-row schema assertions green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| _drive_task agent loop → turn cap | unbounded agent loop could burn weekly subscription limits; the cap is the budget boundary |
| judge model resolution → recorded row | judge model id flows into JSONL; must record actual resolved model, not assumed |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E1-07 | Denial | runaway agent loop on subscription auth | mitigate | `max_turns` hard-stop in `_drive_task`; capped task recorded FAIL + judge skipped (D-05) so no extra sub-credit on a partial transcript |
| T-E1-08 | Tampering | gate bypass via judge override | mitigate | gate_pass conjunction forces success=False on any failing check regardless of judge verdict (EVSUB-02) |
| T-E1-09 | Information | wrong judge model silently recorded | mitigate | judge_model_eff recorded verbatim in the row; same-model collision warns on stderr (D-11) |
| T-E1-10 | Tampering | sentinel tests masking row drift | mitigate | REQUIRED_FIELDS + exact-bytes summary updated in THIS plan (same plan that changes fields) — prevents stale-sentinel false-green (known project hazard) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/ -q` → FULL eval suite green (all sentinels updated in-plan)
- Hybrid: failing check => FAIL even if judge passes; no-checks => judge-only fallback
- Cap: never-finishing stub task => capped:true + FAIL + judge skipped, no hang
- Run header prints `N tasks · max M turns/task` before first model call
- Judge default differs from actor default; --judge-model honored; same-model warns
- summary.md gate-pass and judge-rate as separate columns
</verification>

<success_criteria>
- Failing check ⇒ task FAIL regardless of judge verdict; no-checks task ⇒ judge-only verdict (EVSUB-02)
- Turn cap hard-stops a never-finishing task: capped:true + FAIL, judge skipped, no hang; run prints task count + cap upfront (EVSUB-04)
- Default judge model differs from actor model; both recorded; --judge-model honored; same-model warns not errors (EVSUB-06)
- New JSONL fields additive; existing columns unbroken; both sentinel tests updated in-plan and green
- summary.md reports gate-pass rate and judge rate as separate columns
</success_criteria>

<output>
Create `.planning/phases/E1-eval-substrate/E1-03-SUMMARY.md` when done
</output>
