# Phase E1: Eval Substrate — Specification

**Created:** 2026-06-10
**Ambiguity score:** 0.20 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

The existing M5 eval substrate (`voss/eval/`) gains hybrid scoring (deterministic `checks` gates + LLM judge), per-run turn/task caps, and a dev-gated internal-only posture — proven by one full golden-suite run live on subscription auth with ≥5/6 deterministic-gate passes within caps.

## Background

Codebase scout (2026-06-10) found M5 substrate **fully built** despite stale ROADMAP checkboxes: `voss/eval/suite.py` (pydantic `TaskSpec` + `load_suite`), `runner.py` (381 lines — fixture isolation, stub/live providers, `auth.resolve(role="runner"/"judge")`), `judge.py` (`Verdict` + `judge_run`), `summary.py` (summary.md + Pearson), `voss eval` CLI (`--stub --auth --suite -k --out`), 6 golden tasks in `tests/eval/golden/`, codex subscription auth in `voss/harness/auth.py`, 30 eval tests green plus creds-gated live tests.

**E1 is gap-closure, not a build.** Gaps vs E-track decisions (`.planning/notes/e-track-eval-decisions.md`):
1. Scoring is LLM-rubric-only — no deterministic gates → false-green risk the E-track exists to kill.
2. No per-run turn/task caps — a runaway task can burn weekly subscription limits.
3. `voss eval` is an undocumented but publicly registered CLI verb — E-track posture is internal-only.
4. The live subscription path has never been proven end-to-end as a full-suite run.

## Requirements

1. **Deterministic checks in TaskSpec**: `task.toml` supports an optional `checks` list; each check is one of: command-exits-0 (run in the task's isolated fixture copy), file-exists, file-contains.
   - Current: `TaskSpec` has `rubric` (judge text) + `judge_inputs` only; `extra="forbid"` rejects unknown fields
   - Target: `checks` field validates via pydantic; tasks without `checks` behave exactly as today (back-compat)
   - Acceptance: a task.toml with all three check types loads via `load_task`; existing 6 golden task.toml files still load unchanged before retrofit; malformed check entries raise validation errors

2. **Hybrid gate semantics**: deterministic checks decide pass/fail; judge scores quality only.
   - Current: `judge_run` verdict is the sole pass/fail signal
   - Target: per-task result records `gate_pass` (all checks pass; vacuously true if no checks) and `judge_verdict` separately; a task with failing checks is FAIL regardless of judge opinion; JSONL row + summary.md surface both signals
   - Acceptance: a task whose check fails but whose judge says pass is recorded FAIL; a task with no `checks` falls back to judge-only verdict (current behavior); summary.md shows gate-pass rate and judge rate as distinct columns

3. **Golden-task checks retrofit**: the existing 6 golden tasks get deterministic `checks`.
   - Current: all 6 tasks are rubric-only
   - Target: each task.toml has ≥1 deterministic check matching its contract (e.g. 01-analyze: `.voss/architecture.md` exists; 03-approved-edit: `sum_two` present and `add(` absent in both sites; 04-validation: `voss check sample.voss` exits 0)
   - Acceptance: `load_suite` returns 6 tasks each with non-empty `checks`; full stub-mode suite run executes all checks without error

4. **Per-run caps**: turn cap per task + task count visible upfront.
   - Current: no cap — runner drives the agent loop unbounded (only EpisodicMemory capacity=40)
   - Target: `max_turns` per task (CLI flag + config default; conservative default ~15) hard-stops the agent loop and records the task as FAIL/`capped`; run header prints task count + max-turns before any model call
   - Acceptance: a task forced past the cap (stub provider scripted to never finish) records `capped: true` and FAIL without hanging; run output shows `N tasks · max M turns/task` before first model call

5. **Internal-only dev gate**: `voss eval` refuses to run without an explicit dev opt-in.
   - Current: `voss eval` is registered and callable by anyone
   - Target: invocation without `VOSS_DEV=1` (env) exits non-zero with a one-line "internal tool" message; with the env var set, behavior is unchanged; eval tests set the var in conftest
   - Acceptance: `voss eval --stub ...` without the env var → exit ≠ 0 + stderr message, no model calls, no output dir; with `VOSS_DEV=1` → current behavior; full eval test suite still green

6. **Judge model split**: judge rides the same subscription auth but pins a different model than the actor by default.
   - Current: `_judge_provider_for_eval` resolves `role="judge"` but default model behavior undocumented/unpinned
   - Target: default judge model ≠ default actor model (config-pinned, overridable via existing `--judge-model`); JSONL rows record both actor and judge model
   - Acceptance: a live run's JSONL shows actor model and judge model fields with different values by default; `--judge-model` override is honored

7. **Live proof run**: full golden suite runs live on codex subscription auth.
   - Current: live path exists but only creds-gated unit signals; no recorded full-suite live run
   - Target: one documented run — all 6 golden tasks, `--auth codex`, ≥5/6 `gate_pass`, every task within the turn cap, JSONL + summary.md produced and committed (or path recorded in SUMMARY)
   - Acceptance: run artifacts exist showing 6 task rows, ≥5 with `gate_pass: true`, zero `capped` rows, actor+judge models recorded; total run completes without manual intervention

## Team Rollout Consideration

If Voss is rolled out to an engineering team, shared eval observability will probably matter. The intended later shape is an optional LangSmith export/trace adapter, not a replacement for local E1 artifacts:

- Canonical results remain `.voss/eval/<run>/runs.jsonl` and `summary.md`.
- LangSmith may receive traces/results for dashboards, run comparison, annotation, and evaluator calibration.
- Export must be opt-in, internal-only, dependency-gated, and able to record returned LangSmith trace/run URLs back into local JSONL rows.
- LangSmith must not own deterministic pass/fail gates, auth resolution, response caching, or reproducibility.

This is **not an E1 requirement**. E1 should preserve an exporter seam if naturally available, but should not add a LangSmith dependency.

## Boundaries

**In scope:**
- `checks` schema in `TaskSpec` + check executor (3 check types) in runner
- Hybrid gate/judge result plumbing through JSONL rows + summary.md
- Retrofit of all 6 existing golden tasks with deterministic checks
- `max_turns` per-task cap + upfront run-size print
- `VOSS_DEV=1` gate on the `voss eval` verb
- Judge-model default split + recording of both models
- One live full-suite proof run on codex subscription auth

**Out of scope:**
- New golden tasks or repo-shape matrix (py/rust/ts fixtures) — that is E2
- Surface e2e (CLI verbs/server plane driven live) — that is E3; SDK proof — E4; TUI/voss-app driving — E5
- CI integration, scheduled/nightly runs — internal on-demand only (E-track decision)
- Token-budget envelope integration (V4-style) — turn caps chosen instead; revisit only if turn caps prove insufficient
- Success-rate-over-N repeat harness — `-k` exists; multi-repeat statistics deferred until a consumer needs them
- Rebuilding/redesigning `voss/eval/` — gap-closure on the existing module only
- LLM-judge prompt/rubric quality improvements beyond the model split — judge content quality is an eval-of-evals problem, later
- LangSmith/shared dashboard integration — likely useful for team rollout, but later and adapter-only; no dependency or external source of truth in E1

## Constraints

- Subscription rate limits: live proof run must fit within turn caps; no repeat-N runs in E1 acceptance
- Backward compatibility: existing 30 eval tests must stay green (modulo conftest `VOSS_DEV=1` addition); tasks without `checks` keep current judge-only behavior
- Codex backend quirks (no temperature/max_tokens, gpt-5.x only) already handled in `voss/harness/auth.py` — do not regress
- `extra="forbid"` on `TaskSpec` stays — `checks` is added to the schema, not smuggled through
- No new dependencies for check execution (stdlib subprocess/pathlib)

## Acceptance Criteria

- [ ] `TaskSpec` validates `checks` with all three check types; tasks without `checks` unchanged
- [ ] Failing check ⇒ task FAIL regardless of judge verdict; no-checks task ⇒ judge-only verdict
- [ ] summary.md reports gate-pass rate and judge rate as separate columns
- [ ] All 6 golden tasks have ≥1 deterministic check; stub-mode full suite executes checks green
- [ ] Turn cap hard-stops a never-finishing task, recorded `capped: true` + FAIL, no hang
- [ ] Run prints task count + turn cap before first model call
- [ ] `voss eval` without `VOSS_DEV=1` exits non-zero with message, makes zero model calls
- [ ] Default judge model differs from actor model; both recorded per JSONL row; `--judge-model` honored
- [ ] Live codex-auth full-suite run artifacts: 6 rows, ≥5 `gate_pass: true`, 0 capped
- [ ] Existing eval test suite green (with conftest dev-gate var)

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                        |
|--------------------|-------|------|--------|----------------------------------------------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | Gap-closure reframe locked after scout       |
| Boundary Clarity   | 0.75  | 0.70 | ✓      | E2–E5 split + reuse-not-rebuild explicit     |
| Constraint Clarity | 0.78  | 0.65 | ✓      | Caps/judge routing locked; defaults to discuss |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | Live proof run concretely defined            |
| **Ambiguity**      | 0.20  | ≤0.20| ✓      |                                              |

## Interview Log

| Round | Perspective            | Question summary                          | Decision locked                                              |
|-------|------------------------|-------------------------------------------|--------------------------------------------------------------|
| 1     | Researcher             | M5 substrate already built — reframe?     | E1 = gap-closure on existing `voss/eval/`, no rebuild         |
| 1     | Researcher             | Internal-only meaning for `voss eval`?    | Hide behind dev flag/env (`VOSS_DEV=1` gate)                  |
| 1     | Researcher             | Deterministic gate shape?                 | Optional `checks` list per task (cmd-exit-0, file-exists, file-contains); gates decide pass/fail, judge scores quality |
| 2     | Researcher + Simplifier| What gets capped for sub limits?          | Turns per task + task count upfront; no token accounting      |
| 2     | Researcher + Simplifier| Which model judges?                       | Same subscription auth, different model than actor by default |
| 2     | Researcher + Simplifier| What proves "live works"?                 | Full golden suite via codex auth, ≥5/6 gate-pass, within caps |

---

*Phase: E1-eval-substrate*
*Spec created: 2026-06-10*
*Next step: /gsd-discuss-phase E1 — implementation decisions (check executor shape, cap defaults, dev-gate wiring, judge model pin)*
