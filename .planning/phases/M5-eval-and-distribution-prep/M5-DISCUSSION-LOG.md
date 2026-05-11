# Phase M5: Eval and Distribution Prep - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** M5-eval-and-distribution-prep
**Areas discussed:** Eval harness shape + artifact, Golden task design + scoring, LLM-as-judge mechanics, Fixture isolation, Cost + confidence correlation, Packaging smoke + distribution scope, Ship gate posture

---

## Eval Harness Shape + Artifact

| Option | Description | Selected |
|--------|-------------|----------|
| `voss eval` CLI + JSONL + Markdown | New top-level Click subcommand; emits `.voss/eval/<ts>/runs.jsonl` + `summary.md`. Dogfood-friendly first-class verb. | ✓ |
| `scripts/eval/run.py` standalone | Plain Python script; no new CLI surface. Lower discoverability; doesn't feel dogfooded. | |
| Pytest suite under `tests/eval/` with `-m eval` marker | Eval IS pytest; reuses fixtures/parametrize. Tradeoff: pytest 'test failure' semantics conflate with 'task didn't succeed'. | |
| Other / I'll describe it | — | |

**User's choice:** `voss eval` CLI + JSONL + Markdown.
**Notes:** Reports live under `.voss/eval/` (durable, M2 D-09 tracked) — not `.voss-cache/`. JSONL is canonical; Markdown is the human read.

---

## Golden Task Design + Scoring

| Option | Description | Selected |
|--------|-------------|----------|
| Temp-git fixture per task, declarative scorecard | `task.toml` declares `expect.*`; scorer asserts post-run state. Deterministic, regex-bounded. | |
| Single shared fixture repo, narrative sequential tasks | One fixture; tasks chain. Closer to real session arc; coupled. | |
| LLM-as-judge scorecard | Each task scored by judge LLM against per-task rubric. Semantic; adds cost + non-determinism. | ✓ |
| Other / I'll describe it | — | |

**User's choice:** LLM-as-judge scorecard.
**Notes:** Picks semantic scoring over regex assertions. Aligns with the "Voss is AI-native" framing — eval is itself an LLM workflow.

---

## LLM-as-Judge Mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Single-model judge, rubric per task, pass/fail + rationale | One configured judge model; `task.toml` rubric (plain text); judge returns `{verdict, confidence, rationale}` via JSON mode. | ✓ |
| Hybrid: deterministic gates first, judge only when gates pass | `expect.*` + `rubric`; gates filter first, judge tiebreaks. Cheaper, more reproducible. | |
| Judge-only, no deterministic gates | Pure LLM scoring on every task. Most semantic; most expensive. | |
| Other / I'll describe it | — | |

**User's choice:** Single-model judge, rubric per task.
**Notes:** Uniform scoring path. Rubrics evolve without changing test assertions. `Verdict` pydantic model reuses M1's JSON-mode response pattern.

---

## Fixture Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Per-task temp git repo, resume chains with predecessor | Tasks 01–04 isolated; task 05 reuses task 04's tmp dir for genuine continuity. | ✓ |
| Single shared fixture repo, sequential pipeline | All tasks chain in one fixture. Most realistic; most coupled. | |
| Other / I'll describe it | — | |

**User's choice:** Per-task temp git repo, resume chains with predecessor.
**Notes:** Refined in CONTEXT.md — task 05 spawns + kills + resumes within its OWN fresh fixture (not actually chained to task 04's tmp). Independence matters more for a measurement suite than shared continuity; resume semantics tested within its own fixture.

---

## Cost + Confidence Correlation

| Option | Description | Selected |
|--------|-------------|----------|
| Live by default, `--stub` for smoke, k=3 | Real provider via `auth.resolve`; no creds = loud fail. `--stub` for hermetic CI. 5 tasks × 3 runs = 15 datapoints for correlation. | ✓ |
| Stub-default, `--live` opt-in, k=1 baseline | Stub free; cost = token-count estimate. `--live` for real. Cheap but stub-cost is fake. | |
| Two suites: `smoke` (stub, k=1, CI) and `golden` (live, k=3, manual) | Explicit split between hermetic and live suites. Cleanest separation; two artifacts. | |
| Other / I'll describe it | — | |

**User's choice:** Live by default, `--stub` for smoke, k=3.
**Notes:** Cost + correlation only meaningful live. `--stub` cost = null (no fake numbers). Sequential runs; ~$0.50–$2 per full eval.

---

## Packaging Smoke + Distribution

| Option | Description | Selected |
|--------|-------------|----------|
| Wheel-in-tempvenv smoke; no publish | `python -m build` → tmpvenv → `pip install` → assert `voss --help`/`compile`/`check`/`doctor` + `voss_runtime` import. README polish. PyPI deferred. | ✓ |
| Wheel smoke + TestPyPI dry-run publish | Add `twine upload --repository testpypi` rehearsal. Real PyPI deferred. | |
| Wheel smoke + real PyPI publish under v0.1.0 tag | Largest scope. Risk: shipping a broken install. | |
| Other / I'll describe it | — | |

**User's choice:** Wheel-in-tempvenv smoke; no publish.
**Notes:** PyPI publish deferred to release-prep post-M5. v0.1 framing line required in README ("Python harness; Rust/Homebrew later").

---

## Ship Gate Posture

| Option | Description | Selected |
|--------|-------------|----------|
| Measurement only — record + report; ship is human call | Eval emits report; no CI threshold. Human reads, decides. | ✓ |
| Soft gate — baseline JSON tracked; CI warns on regression | First eval = baseline; PRs warn (not fail) on success-rate drop >10%. | |
| Hard gate — minimum success rate blocks ship | Numeric threshold (e.g., success_rate ≥ 0.6) enforced in CI. | |
| Other / I'll describe it | — | |

**User's choice:** Measurement only.
**Notes:** Design CI gates AFTER baselines exist. M5 produces the data; future-phase or release-prep designs the gates.

---

## Claude's Discretion

- Judge model selection — smallest defensible default; suggested `auth.resolve(role="judge")` shape.
- `Verdict` pydantic model location — `voss/harness/eval.py` (new module) natural home.
- Resume task (05) implementation detail — subprocess kill vs in-process cancellation; pick most reliable across CI.
- Auto-approve simulation for task 03 — `EVAL_AUTO_APPROVE=1` env honored by `PermissionGate` is the suggested hook.
- Whether `voss eval --task <id>` allows single-task invocation (yes, for dev iteration).
- "Diff vs last run" comparison in Markdown summary — out of M5 if it adds friction.
- README install section copy — framing line required; rest is style.
- Whether `docs/release.md` runbook lands in M5 or defers to release-prep.
- `.voss/eval/` git tracking — researcher confirms M2's `.voss/.gitignore` policy (default: tracked).

## Deferred Ideas

- PyPI publish (real or TestPyPI) — release-prep, post-M5.
- GitHub Actions release workflow — deferred with publish.
- CI ship gate (success/cost thresholds) — design after baselines exist.
- Baseline-tracking + regression warning — follow-on phase.
- Per-token cost estimation under `--stub` — rejected; no fake numbers.
- Judge-of-judge — rejected.
- Deterministic rule-based scorer — rejected.
- Eval against M4 `VOSS_HARNESS=compiled` path — future hardening.
- Multiple golden suites — single `golden` suite in M5.
- Structured-rubric DSL — rejected; plain text per task.
- Human-grader export — deferred.
- Cross-provider eval matrix — deferred.
- Cost dashboards / time-series viz — deferred.
- DIST-01 (Rust shell), DIST-02 (Homebrew), DIST-03 (MCP bridge) — explicitly post-v0.1.
- EDIT-01 (tree-sitter), EDIT-02 (VSCode), LING-01 (Linguist PR) — explicitly post-v0.1.
- TEAM-* / WEB-* (cloud, team, web UI) — explicitly post-v0.1.
