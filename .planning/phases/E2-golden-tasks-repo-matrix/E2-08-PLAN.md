---
phase: E2-golden-tasks-repo-matrix
plan: 08
type: execute
wave: 2
depends_on: ["E2-01"]
files_modified:
  - voss/eval/runner.py
  - voss/harness/cli.py
  - voss/eval/summary.py
  - voss/templates/eval/summary.md.jinja
autonomous: true
requirements: [EVGLD-05, EVGLD-06]
must_haves:
  truths:
    - "run_suite prints toolchain availability (py/rust/ts OK or MISSING) before the first model call"
    - "A task whose lang prefix maps to an absent toolchain records skipped=True + skip_reason=toolchain-absent + gate_pass=None + success=None, then continues — never gate_pass=False"
    - "run_suite accepts require_all_toolchains; when True and any of py/rust/ts is absent it raises click.UsageError naming the missing toolchains, before any model call"
    - "voss eval registers --require-all-toolchains and threads it to run_suite"
    - "summary.md shows a skipped count in the header and a skipped column in the per-task table"
    - "The existing 66 eval tests stay green; the golden suite is unaffected"
  artifacts:
    - path: "voss/eval/runner.py"
      provides: "toolchain preflight + skip-row guard + require_all_toolchains enforcement"
      contains: "toolchain-absent"
    - path: "voss/harness/cli.py"
      provides: "--require-all-toolchains flag on eval_cmd"
      contains: "require_all_toolchains"
    - path: "voss/eval/summary.py"
      provides: "skipped-count aggregation"
      contains: "skipped"
    - path: "voss/templates/eval/summary.md.jinja"
      provides: "skipped header line + skipped table column"
      contains: "skipped"
  key_links:
    - from: "voss/harness/cli.py eval_cmd --require-all-toolchains"
      to: "voss/eval/runner.py run_suite(require_all_toolchains=...)"
      via: "click flag threaded into the run_suite call"
      pattern: "require_all_toolchains"
    - from: "voss/eval/runner.py skip row"
      to: "voss/eval/summary.py skipped aggregation"
      via: "skipped=True JSONL field consumed by write_summary"
      pattern: "skipped"
---

<objective>
Extend the E1 runner + CLI + summary with toolchain awareness (D-03, EVGLD-05/06). This is the only NEW engine code in E2 — additive to E1's shipped `run_suite`/`write_summary`. Four edits: (1) toolchain preflight print, (2) per-task skip-row guard before fixture prep, (3) `--require-all-toolchains` strict flag, (4) summary.md skipped count + column. Uses `shutil.which` (already imported, mirrors `diagnostics.py:471`). This plan turns plan-01's strict-xfail runner tests and RED summary tests GREEN.

Purpose: A missing toolchain must read as SKIPPED, never as green and never as a gate FAIL (the E-track anti-false-green mission). ZERO TaskSpec schema change — language is read from the task_id prefix via `task_id.split("-")[0]`.
Output: runner.py + cli.py + summary.py + summary.md.jinja extended; matrix-runner + matrix-summary tests pass.
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
<!-- Exact anchors VERIFIED in the codebase this session. Edit additively at these points. -->
voss/eval/runner.py:
  line 7   import shutil            (already present — no new import)
  line 20  from voss import __version__ as VOSS_VERSION
  line 50  def _prepare_fixture(task_dir, tmp) -> Path
  line 133 def _append_row(path, row) -> None     (mkdir + append-open + json.dumps)
  line 347-361 def run_suite(*, suite="golden", stub=False, live=False, k=1, out=None,
               out_dir=None, judge_model=None, task=None, task_id=None,
               auth_pref="auto", model=None, max_turns=None) -> Path
  line 381 click.echo(f"{len(tasks)} tasks · max {max_turns} turns/task")   ← extend with toolchains
  line 390 for task_id, spec in tasks:
  line 391   for run_idx in range(k):
  line 392     started_at = _now_iso()        ← skip guard goes AFTER this, BEFORE line 393
  line 393     start = time.monotonic()
  line 394     with tempfile.TemporaryDirectory(prefix=f"voss-eval-{task_id}-") as tmp:
voss/harness/cli.py:
  line 3492 @click.command("eval")
  line 3514 @click.option("--max-turns", ...)   ← add --require-all-toolchains AFTER this
  line 3515-3525 def eval_cmd(suite, stub, live, k, out_path, judge_model, task, auth_pref, max_turns)
  line 3527 VOSS_DEV gate
  line 3533-3543 run_suite(...) call   ← add require_all_toolchains=require_all_toolchains
voss/eval/summary.py:
  line 49  def write_summary(jsonl_path, summary_path) -> Path
  line 60-68 gate_rows/gate_passes/gate_rate + judge_rows/judge_passes/judge_rate
  line 81-94 per-task loop building tasks.append({id, runs, gate_pass_rate, pass_rate, mean_cost})
  line 98-123 render_package_template(...) context dict + write_text
voss/templates/eval/summary.md.jinja:
  header lines (runs/provider/gate pass rate/judge pass rate/mean cost)
  per-task table header: | task | runs | gate pass | pass rate | mean cost |
diagnostics.py:471 analog: tools = {name: shutil.which(name) for name in ("node","pnpm","cargo")}
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Toolchain preflight + skip-row guard + require_all_toolchains (runner.py + cli.py)</name>
  <files>voss/eval/runner.py, voss/harness/cli.py</files>
  <read_first>
    - voss/eval/runner.py lines 347-395 (run_suite signature + header line 381 + task loop top 390-394 — the exact insertion points)
    - voss/eval/runner.py lines 133-136 (_append_row — skip row uses this verbatim) + lines 455-478 (the normal row dict shape, to mirror field names in the skip row)
    - voss/harness/cli.py lines 3492-3543 (eval_cmd registration, --max-turns flag at 3514, run_suite call at 3533)
    - voss/harness/diagnostics.py lines 471-477 (shutil.which toolchain-dict pattern — the established analog)
    - E2-PATTERNS.md lines 370-448 (runner extension: header rewrite, skip-guard block, require_all enforcement) + lines 505-563 (cli flag + signature threading)
    - E2-RESEARCH.md §Toolchain Skip Implementation lines 564-601 (Approach A prefix convention + full skip-row schema with all fields) + §Pattern 1 lines 272-295 + §Pattern 3 lines 320-331
    - tests/eval/test_matrix_runner.py (the strict-xfail tests this task must turn green: test_preflight_prints_toolchain_availability, test_toolchain_absent_records_skip_row, test_require_all_toolchains_fails_when_absent)
  </read_first>
  <behavior>
    - test_preflight_prints_toolchain_availability: run_suite(suite="matrix", stub=True) echoes a line containing "toolchains:" and the tokens py, rust, ts before the task loop
    - test_toolchain_absent_records_skip_row: with cargo absent (monkeypatched which→None), a rust-* task records one JSONL row with skipped=True, skip_reason="toolchain-absent", gate_pass=None, success=None — and that row's gate_pass is NOT False
    - test_require_all_toolchains_fails_when_absent: run_suite(suite="matrix", require_all_toolchains=True) with a toolchain absent raises click.UsageError naming the missing toolchain(s), before any model call
  </behavior>
  <action>
    In voss/eval/runner.py: add `require_all_toolchains: bool = False` to the run_suite keyword-only signature (after max_turns, line ~360). Immediately after the existing header echo (line 381), build a toolchains dict `{"py": shutil.which("python3"), "rust": shutil.which("cargo"), "ts": shutil.which("node")}` (mirrors diagnostics.py:471). If require_all_toolchains and any value is None, collect the missing keys and `raise click.UsageError` naming them — this MUST happen before `_provider_for_eval` (line 383) so no model call occurs. Rewrite the header echo to append `· toolchains: ` plus a per-lang `py{OK|MISSING}` summary (use plain OK/MISSING ASCII tokens, not unicode checkmarks, to stay terminal-safe). Inside the task loop, after `started_at = _now_iso()` (line 392) and before `start = time.monotonic()` (line 393), compute `lang = task_id.split("-")[0] if "-" in task_id else None`; if `lang in toolchains and toolchains.get(lang) is None`, call `_append_row(runs_path, {...})` with the full skip-row schema (RESEARCH lines 576-601: task_id, run_idx, success=None, skipped=True, skip_reason="toolchain-absent", gate_pass=None, capped=False, checks=[], cost_usd=None, confidence=None, duration_s=0.0, judge_verdict="skipped", judge_confidence=0.0, judge_rationale=f"skipped: toolchain-absent ({lang})", provider="n/a", model="n/a", judge_model="n/a", live=live, seed=run_idx, voss_version=VOSS_VERSION, started_at=started_at) then `continue` (skip _prepare_fixture entirely — no fixture copy, no model call). The skip row MUST set gate_pass=None (NOT False) so it never reads as a gate failure.

    In voss/harness/cli.py: after the --max-turns option (line 3514) add `@click.option("--require-all-toolchains", "require_all_toolchains", is_flag=True, default=False, help="Fail run if python3/cargo/node is absent (strict mode).")`. Add `require_all_toolchains: bool` to the eval_cmd signature (after max_turns, line 3524). Add `require_all_toolchains=require_all_toolchains` to the run_suite(...) call (line 3542 area). Do not change the VOSS_DEV gate.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/eval/test_matrix_runner.py -q` passes (the 3 formerly-xfail tests now PASS — the executor must remove the `xfail` markers from plan-01's runner tests as part of GREEN, since they were strict)
    - A skip row never reads as a FAIL: the test asserts `row["gate_pass"] is None` (not False) and `row["skipped"] is True`
    - require-all is enforced pre-model: `.venv/bin/python -m pytest tests/eval/test_matrix_runner.py -k require_all -q` passes (raises click.UsageError)
    - CLI wiring present: `grep -c require_all_toolchains voss/harness/cli.py` is at least 3 (option + signature + call)
    - No new import added to runner.py: `grep -c "^import shutil" voss/eval/runner.py` equals 1 (shutil already imported at line 7)
    - Golden untouched: `.venv/bin/python -m pytest tests/eval/test_voss_eval_stub.py tests/eval/test_hybrid_gate.py -q` still green
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_matrix_runner.py -q && grep -c require_all_toolchains voss/harness/cli.py</automated>
  </verify>
  <done>run_suite prints toolchain availability before the first model call; absent-toolchain tasks record a skip row (gate_pass=None, not False) and continue; --require-all-toolchains raises pre-model; CLI threads the flag; runner xfail tests flipped to pass; golden suite green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: summary.md skipped count + per-task column (summary.py + jinja)</name>
  <files>voss/eval/summary.py, voss/templates/eval/summary.md.jinja</files>
  <read_first>
    - voss/eval/summary.py lines 49-123 (write_summary: aggregation 60-68, per-task loop 81-94, render context 98-123)
    - voss/templates/eval/summary.md.jinja (full file — header lines + per-task table header and row loop)
    - E2-PATTERNS.md lines 452-501 (summary extension: skipped_rows aggregation, template header line, per-task table column, tasks.append skipped field)
    - tests/eval/test_matrix_summary.py (the RED tests this task turns green: test_summary_renders_skipped_header, test_summary_renders_skipped_column)
    - tests/eval/test_summary_md.py (analog — exact-bytes + section-assertion patterns, so the new column does not break existing golden summary assertions)
  </read_first>
  <behavior>
    - test_summary_renders_skipped_header: write_summary over rows including one skipped row renders a header line mentioning skipped with the skipped count
    - test_summary_renders_skipped_column: the per-task table header is `| task | runs | gate pass | skipped | pass rate | mean cost |` and a skipped row's task line shows its skipped count
    - existing test_summary_md.py assertions still pass (the new column is additive; gate/judge/cost columns unchanged in order except the inserted skipped column)
  </behavior>
  <action>
    In voss/eval/summary.py: after the gate/judge aggregation (line ~68) add `skipped_rows = [r for r in rows if r.get("skipped") is True]` and `skipped_count = len(skipped_rows)`. In the per-task loop (lines 81-94) add `task_skipped = sum(1 for row in task_rows if row.get("skipped") is True)` and include `"skipped": str(task_skipped)` in the tasks.append dict. In the render_package_template context dict (lines 98-123) add `"skipped_count": skipped_count`. Use `.get("skipped")` everywhere (existing golden rows have no skipped field → None → not counted; back-compat preserved).

    In voss/templates/eval/summary.md.jinja: add a header line after the judge-pass-rate line: `- skipped (toolchain-absent): {{ skipped_count }}`. In the per-task table, insert a `skipped` column between `gate pass` and `pass rate` — update both the header row to `| task | runs | gate pass | skipped | pass rate | mean cost |` (and its separator row alignment) and the `{% for task in tasks %}` row to emit `{{ task.skipped }}` in the new column position.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/eval/test_matrix_summary.py -q` passes (both RED summary tests now green)
    - The rendered summary contains the new column header: `.venv/bin/python -m pytest tests/eval/test_matrix_summary.py -k column -q` passes
    - Back-compat: `.venv/bin/python -m pytest tests/eval/test_summary_md.py tests/eval/test_pearson.py -q` still green (golden rows without skipped field render skipped=0)
    - `grep -c skipped voss/templates/eval/summary.md.jinja` is at least 2 (header line + table column)
    - `grep -c "\.get(.skipped" voss/eval/summary.py` is at least 1 (uses .get for back-compat)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_matrix_summary.py tests/eval/test_summary_md.py -q</automated>
  </verify>
  <done>summary.md gains a skipped header count + a per-task skipped column; matrix-summary RED tests pass; existing golden summary tests stay green via .get back-compat.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| skip-row write → JSONL/summary | A toolchain-absent cell is recorded as skipped, not as a pass and not as a gate FAIL — it must be visually distinct in summary.md |
| require-all flag → pre-model enforcement | The strict flag must fail BEFORE any provider/model call so a misconfigured proof run does not burn subscription |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-19 | Spoofing | absent toolchain reading as green | mitigate | Skip row sets gate_pass=None (not True, not False) + skipped=True + a distinct summary column; plan-01 test asserts gate_pass is None and never False. |
| T-E2-20 | Denial | uncapped/misconfigured proof run burning subscription | mitigate | require_all_toolchains raises click.UsageError before `_provider_for_eval`; the existing max_turns cap (E1) is unchanged. |
| T-E2-21 | Tampering | summary back-compat break on golden rows | mitigate | All new aggregation uses `.get("skipped")`; golden rows lacking the field render skipped=0; test_summary_md.py regression gate enforces it. |
| T-E2-SC | Tampering | npm/pip/cargo installs | n/a | No package installs; `shutil.which` only probes PATH (no execution). |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/ -q` — the existing 66 tests stay green; matrix-runner (3) and matrix-summary (2) tests flip from xfail/RED to pass.
- Skip row gate_pass=None (never False); require-all raises pre-model; summary has skipped header + column.
- No new imports in runner.py; CLI threads --require-all-toolchains.
</verification>

<success_criteria>
- runner.py: preflight print + skip guard (gate_pass=None) + require_all_toolchains enforcement, all additive
- cli.py: --require-all-toolchains flag wired to run_suite
- summary.py + jinja: skipped count header + per-task skipped column, back-compat via .get
- EVGLD-05 + EVGLD-06 satisfied; golden suite unaffected
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-08-SUMMARY.md` when done
</output>
