---
phase: M5
slug: eval-and-distribution-prep
status: executing
nyquist_compliant: true
wave_0_complete: true
wave_1_complete: true
wave_2_complete: true
wave_3_complete: true
wave_4_complete: true
created: 2026-05-11
---

# Phase M5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `M5-RESEARCH.md §Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ + pytest-asyncio 0.23.x (auto mode) — pyproject.toml:25-26, 39-46 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest -q -m "not slow and not live" tests/eval tests/packaging` |
| **Wave-marker run** | `pytest -q -m "not live" tests/eval tests/packaging` (includes slow wheel smoke) |
| **Full suite command** | `pytest -q` (includes slow + live where creds available) |
| **Subprocess CLI** | `python -m voss.cli eval --stub --task <id> -k 1 --out <tmp>` |
| **Estimated runtime** | ~5s quick; ~60-120s wave (wheel build); live tests gated on creds |

---

## Sampling Rate

- **After every task commit:** `pytest -q -m "not slow and not live" tests/eval tests/packaging` (~seconds)
- **After every plan wave:** `pytest -q -m "not live"` (includes wheel-in-tempvenv smoke; ~1-2 min)
- **Before `/gsd-verify-work`:** full suite green + manual live-creds run of `voss eval --suite golden` exercising EVAL-04 (Pearson r against real data, k=3 default) + manual wheel-install smoke
- **Max feedback latency:** 30s quick / 180s wave

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| task-spec-model | 01 | 0 | EVAL-01 | — | `TaskSpec` pydantic model validates `task.toml` schema (prompt/mode/rubric/judge_inputs/optional provider/model/auto_approve_edits) | unit | `pytest tests/eval/test_task_spec.py -q` | ✓ | ✓ green |
| suite-loads | 01 | 0 | EVAL-01 | — | Suite loader walks task directories in stable order, skips non-directories and dirs without `task.toml`, and returns `(task_id, TaskSpec)` pairs | unit | `pytest tests/eval/test_suite_loads.py -q` | ✓ | ✓ green |
| fixture-isolation | 01 | 0 | EVAL-01 / D-06 | T-M5-fixture-leak | Per-run fixture isolation helper copies `fixture/` to a fresh git-initialized cwd and two invocations do not share state | unit | `pytest tests/eval/test_fixture_isolation.py -q` | ✓ | ✓ green |
| verdict-model | 02 | 1 | EVAL-02 / D-08 | — | `Verdict` pydantic model `{verdict: "pass"|"fail", confidence: float, rationale: str}`; `judge_run` calls providers with `response_format=Verdict` JSON-mode | unit | `pytest tests/eval/test_judge_verdict.py -q` | ✓ | ✓ green |
| judge-skipped-on-crash | 02 | 1 | EVAL-02 / D-08 | — | `judge_run` returns `(None, "skipped")` on `ParseError`; non-ParseError provider failures propagate for the runner crash path | unit | `pytest tests/eval/test_judge_skipped.py -q` | ✓ | ✓ green |
| auth-resolve-role | 02 | 1 | D-08 (judge) | — | `voss/harness/auth.py:resolve(role: str \| None = None)` added; defaults pass-through; judge uses same provider when no `role="judge"` creds | unit | `pytest tests/harness/test_auth.py -q -k role` | ✓ | ✓ green |
| cli-eval-command | 03 | 2 | EVAL-01..05 / D-01 | T-M5-cli-options-drift | `voss eval` Click subcommand registers via `AGENT_COMMANDS` tuple in `voss/harness/cli.py`; supports `--suite golden`, `--stub`, `--live`, `-k N`, `--out <path>`, `--judge-model <name>`, `--task <id>` | unit | `pytest tests/eval/test_cli_options.py -q` | ✓ | ✓ green |
| stub-eval-smoke | 03 | 2 | EVAL-02 / D-04 | — | `voss eval --stub --task 02-plan-only -k 1 --out <tmp>` produces `<tmp>/runs.jsonl` with 1 row whose schema matches D-04 (task_id, run_idx, success, cost_usd=null, confidence, duration_s, judge_verdict, judge_confidence, judge_rationale, provider, model, judge_model, seed, voss_version, started_at) | integration | `pytest tests/eval/test_voss_eval_stub.py -q` | ✓ | ✓ green |
| jsonl-cost-stub-null | 03 | 2 | EVAL-03 | T-M5-fake-cost | Under `--stub`, JSONL `cost_usd` is JSON `null` — NOT a token-count estimate, NOT 0.0 | unit | `pytest tests/eval/test_voss_eval_stub.py::test_cost_field_null_under_stub -q` | ✓ | ✓ green |
| cost-extraction-live | 03 | 2 | EVAL-03 | — | Live run: JSONL `cost_usd` populated from `RunRecord.cost_usd` (voss/harness/session.py:77) | live | `pytest -m live tests/eval/test_live_signals.py::test_cost -q` | ✓ | ✓ gated |
| confidence-extraction | 03 | 2 | EVAL-04 | — | JSONL `confidence` populated from `Plan.confidence` (voss/harness/agent.py:46); single value per run | live | `pytest -m live tests/eval/test_live_signals.py::test_confidence -q` | ✓ | ✓ gated |
| pearson-correlation | 04 | 3 | EVAL-04 | T-M5-pearson-wrong | `summary.md` includes `conf_corr_r` line computed via `statistics.correlation(confidences, successes_as_01)`; matches manual reference on fixture rows | unit | `pytest tests/eval/test_pearson.py -q` | ✓ | ✓ green |
| markdown-summary-shape | 04 | 3 | EVAL-02..04 / D-02 | — | `summary.md` aggregates JSONL: overall success rate + per-task success rate + mean cost (overall + per-task) + Pearson r + provider/model + run count + total elapsed; linked from `runs.jsonl` via `_summary.md` filename pair | unit | `pytest tests/eval/test_summary_md.py -q` | ✓ | ✓ green |
| voss-eval-gitignore | 04 | 3 | D-03 / M2 D-09 | T-M5-eval-gitignored | `.voss/.gitignore` (cognition.py:581) does NOT add `eval/`; `.voss/eval/<timestamp>/` artifacts stay git-tracked | unit | `pytest tests/eval/test_gitignore.py -q -k eval_tracked` | ✓ | ✓ green |
| task-01-analyze | 05 | 4 | EVAL-01 | — | `tests/eval/golden/01-analyze/` exists; fixture contains seed repo; task.toml prompt analyzes repo; rubric: PASS if `.voss/architecture.md` produced | fixture | `pytest tests/eval/test_voss_eval_stub.py -q -k task_01` | ✓ | ✓ green |
| task-02-plan-only | 05 | 4 | EVAL-01 | — | `tests/eval/golden/02-plan-only/` exists; mode=plan; rubric PASS if no writes + non-empty plan | fixture | `pytest tests/eval/test_voss_eval_stub.py -q -k task_02` | ✓ | ✓ green |
| task-03-approved-edit | 05 | 4 | EVAL-01 / D-07 auto_approve | — | `tests/eval/golden/03-approved-edit/` exists; mode=edit; `auto_approve_edits=true` wires into `PermissionGate(auto_yes=True)` (voss/harness/permissions.py:98-104); rubric PASS if target file modified | fixture | `pytest tests/eval/test_voss_eval_stub.py -q -k task_03` | ✓ | ✓ green |
| task-04-validation | 05 | 4 | EVAL-01 | — | `tests/eval/golden/04-validation/` exists; fixture contains a `.voss` sample; task invokes `voss check`; rubric PASS if exit 0 | fixture | `pytest tests/eval/test_voss_eval_stub.py -q -k task_04` | ✓ | ✓ green |
| task-05-resume | 05 | 4 | EVAL-01 | T-M5-resume-flake | `tests/eval/golden/05-resume/` exists; runner spawns turn, asyncio.Task.cancel() after first tool call, `voss resume` from SessionRecord; rubric PASS if prior-context surfaces AND turn completes | fixture | `pytest tests/eval/test_voss_eval_stub.py -q -k task_05` | ✓ | ✓ green |
| wheel-build | 06 | 5 | EVAL-05 | — | `python -m build --wheel` produces `dist/voss-*.whl` (build 1.5.0 already available; pyproject [project.scripts] declares `voss` console script) | slow | `pytest -m slow tests/packaging/test_wheel_install.py::test_wheel_builds -q` | ❌ W5 | ⬜ pending |
| wheel-tempvenv-install | 06 | 5 | EVAL-05 | T-M5-wheel-deps-leak | `venv.create(<tmp>)` + `<tmp>/bin/pip install <wheel>` (with deps, unlike existing editable-install test) succeeds | slow | `pytest -m slow tests/packaging/test_wheel_install.py::test_install -q` | ❌ W5 | ⬜ pending |
| wheel-smoke-asserts | 06 | 5 | EVAL-05 | — | In tempvenv: `voss --help` exit 0; `voss compile samples/classify.voss` exit 0; `voss check samples/classify.voss` exit 0; `voss doctor` honors M1 D-13 exit-code contract; `import voss_runtime` works | slow | `pytest -m slow tests/packaging/test_wheel_install.py::test_smoke_asserts -q` | ❌ W5 | ⬜ pending |
| readme-install-polish | 06 | 5 | EVAL-05 / D-18 | — | README install section contains `pip install voss`, `voss doctor` first-run check, samples link, harness commands link, "v0.1 is a Python harness" framing; NO Rust mention beyond "later" note | unit | `pytest tests/packaging/test_readme.py -q` | ❌ W5 | ⬜ pending |

*Status: ⬜ pending · ✓ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

**Wave 0 (suite loader + fixture isolation):**
- [x] `tests/eval/__init__.py` — package marker
- [x] `tests/eval/test_suite_loads.py` — inline suite loader fixtures
- [x] `tests/eval/test_task_spec.py` — pydantic validation
- [x] `tests/eval/test_fixture_isolation.py` — tempdir + git init pattern
- [x] `voss/eval/__init__.py` (NEW package) — package marker
- [x] `voss/eval/suite.py` (NEW) — suite loader + TaskSpec pydantic model

**Wave 1 (judge + auth role):**
- [x] `voss/harness/auth.py` — `role` kwarg extension (5-line)
- [x] `voss/eval/judge.py` — Verdict pydantic + LiteLLMProvider JSON-mode call (response_format=Verdict)
- [x] `tests/eval/test_judge_verdict.py`
- [x] `tests/eval/test_judge_skipped.py`
- [x] `tests/harness/test_auth.py` — role-kwarg cases

**Wave 2 (CLI + runner + JSONL):**
- [x] `voss/eval/runner.py` — orchestrates suite × k runs; collects RunRecord.cost_usd + Plan.confidence; writes JSONL row per run
- [x] `voss/harness/cli.py` AGENT_COMMANDS — register `eval_cmd` (mirror check/compile entry shape)
- [x] `tests/eval/test_cli_options.py`
- [x] `tests/eval/test_voss_eval_stub.py` (stub smoke + cost-null assertion)
- [x] `tests/eval/test_live_signals.py` (@pytest.mark.live)

**Wave 3 (summary + Pearson + gitignore guard):**
- [x] `voss/eval/summary.py` — Markdown generator; statistics.correlation Pearson (no scipy)
- [x] `tests/eval/test_pearson.py`
- [x] `tests/eval/test_summary_md.py`
- [x] `tests/eval/test_gitignore.py` — confirms `.voss/.gitignore` does NOT add `eval/`

**Wave 4 (5 golden task fixtures):**
- [x] `tests/eval/golden/01-analyze/{task.toml,fixture/}` — seed repo, expect `.voss/architecture.md`
- [x] `tests/eval/golden/02-plan-only/{task.toml,fixture/}` — mode=plan, no writes
- [x] `tests/eval/golden/03-approved-edit/{task.toml,fixture/}` — mode=edit, auto_approve_edits=true
- [x] `tests/eval/golden/04-validation/{task.toml,fixture/}` — sample.voss inside fixture
- [x] `tests/eval/golden/05-resume/{task.toml,fixture/}` — spawn-cancel-resume runner shape

**Wave 5 (packaging + README):**
- [ ] `tests/packaging/test_wheel_install.py` (@pytest.mark.slow) — wheel build + tempvenv install + smoke asserts
- [ ] `tests/packaging/test_readme.py` — install-section content asserts
- [ ] `README.md` (MODIFY) — install polish per D-18

*(No framework install needed — pytest, pytest-asyncio, build, tomllib all already available per RESEARCH.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live-provider eval Pearson r meaningful | EVAL-04 | Live API costs; reproducibility tied to provider model state | Manual: `ANTHROPIC_API_KEY=... voss eval --suite golden -k 3`; inspect `.voss/eval/<ts>/summary.md` for `conf_corr_r`; record date + provider + sanitized stdout |
| Wheel smoke against real venv on dev machine | EVAL-05 | CI may mask install-path quirks present locally | Manual: `python -m build --wheel`; `python -m venv /tmp/voss-smoke && /tmp/voss-smoke/bin/pip install dist/voss-*.whl && /tmp/voss-smoke/bin/voss --help` |
| LLM judge rubric quality (judge prompts produce defensible verdicts) | EVAL-02 | Subjective evaluation of rubric clarity | Reviewer reads 5 `task.toml` rubrics; spot-checks a recorded judge_rationale per task; confirms verdicts not arbitrary |
| Eval report human-readability | D-02 | Editorial judgment on summary.md aggregation | Reviewer reads a generated `summary.md`; confirms per-task table + correlation + cost columns are scannable |

---

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references (suite loader + TaskSpec + fixture isolation)
- [x] No watch-mode flags
- [x] Feedback latency < 30s quick / < 180s wave
- [x] Default tests hermetic (StubProvider per M3 D-01; `@pytest.mark.live` gates real-provider tests; `@pytest.mark.slow` gates wheel build)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-11
