# Phase M5: Eval and Distribution Prep - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

M5 measures v0.1 harness quality on a fixed golden task suite and verifies the Python package installs cleanly from a built wheel. It introduces a new `voss eval` CLI command, five golden task fixtures under `tests/eval/golden/`, an LLM-as-judge scorer with per-task rubrics, and a wheel-in-tempvenv packaging smoke. Eval defaults to live providers (resolved via existing `auth.resolve`) with `--stub` for hermetic CI smoke; runs k=3 per task to support EVAL-04 confidence correlation; emits per-run JSONL + a Markdown summary under `.voss/eval/<timestamp>.{jsonl,md}`. M5 is measurement-only — no CI threshold gate, no PyPI publish; the ship-v0.1 decision is human, informed by the report. Rust/Homebrew/MCP distribution stays explicitly deferred.

**In scope:**
- New CLI command `voss eval` (registered in `voss/cli.py`). Options: `--suite golden` (default), `--stub` (force `StubProvider`), `--live` (no-op when default is live; redundant convenience flag), `-k N` (runs per task, default 3), `--out <path>` (override default `.voss/eval/<timestamp>`), `--judge-model <name>` (override resolved judge), `--task <id>` (run a single golden task).
- Five golden task fixtures under `tests/eval/golden/`:
  - `01-analyze/` — analyze a tiny seed repo; expect `.voss/architecture.md` produced.
  - `02-plan-only/` — plan a small code change in `plan` mode; expect no writes, non-empty plan output.
  - `03-approved-edit/` — apply an edit in `edit` mode with auto-approve hook; expect target file modified.
  - `04-validation/` — invoke `voss check` on a `.voss` sample inside the fixture; expect exit 0.
  - `05-resume/` — spawn a session, kill mid-turn, resume; expect prior-context surfaces and turn completes.
- Per-task fixture shape: each task dir contains `task.toml` (prompt, mode, rubric, judge-input fields, optional `provider` / `model` overrides) + `fixture/` (seed files copied into a temp git repo at run time). The scorer initializes a fresh `git init`-ed temp dir from `fixture/` per run. Task 05 chains on its own seeded repo (spawn + kill + resume in one fixture); it does NOT reuse task 04's tmp dir.
- LLM-as-judge scorer. Single configured judge model (default: same as run-time provider via `auth.resolve(role="judge")` — falls back to `auth.resolve()` if no separate role). Per `task.toml` rubric (plain-text PASS/FAIL criteria). Judge receives: task prompt, agent `TurnResult.final`, file-state diff (unified diff of fixture-cwd before/after), rubric. Judge returns JSON-mode `{verdict: "pass"|"fail", confidence: 0.0–1.0, rationale: str}` via `Verdict` pydantic model.
- Live by default. `voss eval` resolves a provider via existing `auth.resolve(preference="auto")`; if no creds resolve, fails loudly with message like `voss eval: no provider creds — pass --stub for hermetic smoke or run /login`. `--stub` opts into `StubProvider` for CI smoke (success rate column meaningful; cost + conf-corr columns marked `n/a` because stub responses are deterministic and uninformative).
- k=3 runs per task default. Each run gets a fresh temp git dir. Outputs row per (task_id, run_idx).
- JSONL artifact schema (one row per run):
  - `task_id: str`, `run_idx: int`, `success: bool`, `cost_usd: float | null`, `confidence: float | null`, `duration_s: float`, `judge_verdict: str`, `judge_confidence: float`, `judge_rationale: str`, `provider: str`, `model: str`, `judge_model: str`, `seed: str | null`, `voss_version: str`, `started_at: str` (ISO).
- Markdown summary aggregates the JSONL: overall success rate, per-task success rate, mean cost (overall and per-task), Pearson r for `confidence` vs `success` (numeric encoding 1/0), provider/model used, run count, total elapsed. Linked from the JSONL via a `_summary.md` filename pair.
- Cost extraction: read `cost_usd` from agent's `RunRecord` (M2 D-13/D-14). For stub mode, cost = `null` (NOT a token-count estimate — explicit gap, no fake numbers).
- Confidence extraction: read `Plan.confidence` from `RunRecord`. Single value per run (the planner's self-rated confidence at planning time). Correlation computed across all (task, run_idx) pairs.
- Packaging smoke: extend `tests/packaging/test_entrypoint.py` (or add `tests/packaging/test_wheel_install.py`) with a test that builds wheel via `python -m build`, creates temp venv, `pip install <wheel>` from the venv, then asserts each of:
  - `voss --help` exits 0.
  - `voss compile samples/classify.voss` produces output and exits 0.
  - `voss check samples/classify.voss` exits 0.
  - `voss check samples/` (M4 dir-walking) exits 0 if M4 ships first; otherwise the file form.
  - `voss doctor` exits 0 (or expected non-zero for missing-creds rows — read its exit-code contract; matches M1 D-13).
  - `import voss_runtime` from the temp venv's python works.
  - The console script (`voss` on PATH inside the venv) exists and runs.
- README install section gets a polish pass: install command (`pip install voss`), `voss doctor` first-run check, link to samples, link to harness commands, "v0.1 is a Python harness" framing line. No Rust mention beyond a "later" note.
- Eval is **measurement only**. No CI threshold. No fail-on-regression. The first eval run establishes a baseline in the .voss/eval/ history; comparing subsequent runs is a human read.

**Out of scope (deferred to other phases):**
- PyPI publish (real or TestPyPI) — deferred. Wheel smoke is the M5 contract; publish is a release-runbook task that happens after v0.1 is greenlit by human review.
- GitHub Actions release workflow / tag-triggered publish — deferred with PyPI publish.
- Real-PyPI metadata polish beyond what's in `pyproject.toml` today (long description, classifiers, keywords, project URLs) — landing the polish is fine if researcher finds gaps, but a dedicated polish pass is deferred.
- CI ship gate (minimum success rate, max cost) — explicitly rejected. M5 records numbers; future phase or release-prep designs gates.
- Baseline-tracking + regression warning (`.voss/eval/baseline.json` committed) — rejected. Defer to a follow-on phase once enough eval history exists to set thresholds non-arbitrarily.
- Per-token cost estimation under `--stub` — rejected. Stub cost = `null`; no fake numbers.
- Real PyPI publish under v0.1.0 tag — rejected as M5 scope.
- LLM-as-judge with a SECOND model verifying the first (judge-of-judge) — rejected. Single judge is the M5 contract.
- Deterministic-stub judge (rule-based scorer that mimics LLM judge) — rejected. Under `--stub`, judge still calls the configured judge model (if creds exist for it); if neither agent nor judge has creds, `voss eval --stub` runs agent with stub and skips judge (rows marked `judge_verdict: "skipped"`, `success: null` — explicit gap).
- Eval against the M4 compiled harness path (`VOSS_HARNESS=compiled`) — deferred. M5 evaluates the Python harness only. A future hardening pass can parametrize eval over both backends once M4 stabilizes.
- Multiple golden suites beyond `golden` — single suite in M5. `--suite` flag exists for future extensibility but only `golden` is implemented.
- LLM-as-judge structured scoring rubric DSL — rejected. Rubric is plain text per task.
- Human-grader workflow (export-for-human-review) — deferred.
- Cross-provider eval matrix (run same task suite against Claude AND OpenAI AND ...) — deferred. Single provider per eval invocation in M5.
- Cost dashboards / time-series visualization — deferred. Markdown summary is sufficient for v0.1.
- DIST-01 (Rust harness shell) — explicitly post-v0.1.
- DIST-02 (Homebrew) — explicitly post-v0.1.
- DIST-03 (MCP bridge) — explicitly post-v0.1.
- EDIT-01/02 (tree-sitter, VSCode marketplace) — explicitly post-v0.1.
- LING-01 (GitHub Linguist PR) — explicitly post-v0.1.
- TEAM-*/WEB-* (cloud sync, team collab, web UI) — explicitly post-v0.1.

</domain>

<decisions>
## Implementation Decisions

### Eval harness shape + result artifact
- **D-01:** `voss eval` is a new top-level Click subcommand in `voss/cli.py`. First-class verb — dogfood-friendly. Mirrors `voss check` / `voss compile` registration pattern. Options listed in `<domain>` above.
- **D-02:** Artifact format = JSONL (per-run rows) + Markdown summary. Two files per eval invocation under `.voss/eval/<timestamp>/`: `runs.jsonl` and `summary.md`. Markdown is generated from the JSONL by the same command. JSONL is canonical; Markdown is the human read.
- **D-03:** Eval output directory is `.voss/eval/` — under the M2 durable `.voss/` tree, not `.voss-cache/`. Reports are durable project knowledge (M2 D-09 .voss/.gitignore must NOT add eval/; researcher confirms). Per-run subdirs avoid filename collisions.
- **D-04:** JSONL row schema (canonical): `task_id`, `run_idx`, `success` (bool, from judge verdict), `cost_usd` (float or null), `confidence` (float or null — from agent's `Plan.confidence`), `duration_s`, `judge_verdict` (`"pass"|"fail"|"skipped"`), `judge_confidence`, `judge_rationale`, `provider`, `model`, `judge_model`, `seed` (provider seed if applicable), `voss_version`, `started_at` ISO.

### Golden task design + scoring
- **D-05:** Five golden tasks under `tests/eval/golden/<NN>-<slug>/`. Each contains `task.toml` and `fixture/`. Task IDs and slugs are stable (used in JSONL rows): `01-analyze`, `02-plan-only`, `03-approved-edit`, `04-validation`, `05-resume`.
- **D-06:** Per-task fixture isolation. Each run copies `fixture/` to a fresh temp dir, `git init` + initial commit, runs the task with `--cwd=<tmp>`. Resume task (05) spawns + kills + resumes within its OWN temp fixture, NOT chained to task 04's tmp (independence is more important than shared continuity for a measurement suite).
- **D-07:** `task.toml` schema:
  ```toml
  prompt = "..."          # The task prompt passed to `voss do "<prompt>"`
  mode = "plan|edit|auto"  # Permission mode (M1 D-07)
  rubric = """             # Plain-text PASS/FAIL criteria for judge
    PASS if: ...
    FAIL if: ...
  """
  judge_inputs = ["final", "file_diff"]  # Subset to include (default: both)
  # Optional:
  provider = "anthropic"
  model = "claude-sonnet-4-6"
  auto_approve_edits = true  # For task 03; eval scorer simulates the [y] response.
  ```
- **D-08:** Scoring is LLM-as-judge only — no deterministic gate prefilter. The judge sees prompt + final + file-diff + rubric and returns the `Verdict` JSON. Hybrid (gate-then-judge) was rejected to keep the scoring path uniform; if a run crashes (non-zero agent exit), `success` is recorded `false` with `judge_verdict: "skipped"` (judge never invoked when the run itself errored).
- **D-09:** Judge returns `Verdict { verdict: pass|fail, confidence: 0.0-1.0, rationale: str }` via pydantic + provider JSON-mode (`response_format=Verdict`). Same machinery as the planner uses for `Plan` (M1 reuse).

### Cost + confidence correlation
- **D-10:** Live by default. `voss eval` (no flags) resolves a provider via existing `auth.resolve` and runs against it. No creds = loud failure: `voss eval: no provider creds — pass --stub for hermetic smoke or run /login` (M1 D-13 diagnose-don't-fix posture).
- **D-11:** `--stub` flag forces `StubProvider` for hermetic CI smoke. Under stub: agent runs are deterministic; cost = `null`; confidence is whatever stub returns (real value, just not informative). Judge call: if a judge provider has creds (could be different from agent provider), judge runs normally — useful for testing the scoring path. If NO creds at all, judge is skipped, `success: null`, `judge_verdict: "skipped"`. M3 D-01 auto-StubProvider banner fires once at eval start.
- **D-12:** k=3 runs per task default. Each run is independent: fresh temp dir, fresh session, no shared state. Runs are sequential (not parallel) — keeps cost predictable, avoids rate-limit issues, makes correlation cleaner. `-k N` overrides.
- **D-13:** Cost source = `RunRecord.cost_usd` (M2 D-13/D-14). The harness already records per-turn cost from the provider's response. Eval reads the session JSON at run end, extracts the last `RunRecord.cost_usd`, writes it to the JSONL row. For multi-turn tasks (resume), eval sums cost across all `RunRecord`s in the session.
- **D-14:** Confidence source = `Plan.confidence` (M1, agent.py:44) from the first turn's RunRecord. Single value per run. For resume task, eval records confidence from the FIRST turn (before kill), and the resumed turn's confidence in a separate column `resume_confidence` (or as run_idx fractional — researcher picks).
- **D-15:** Confidence correlation = Pearson r between `confidence` (float 0–1) and `success` (encoded 1.0/0.0) across all task-run rows where both are non-null. Reported in summary.md as `conf_corr_r: <r>` plus n. EVAL-04 satisfied by reporting this number, NOT by enforcing it.

### Packaging smoke + distribution
- **D-16:** Packaging smoke = wheel-in-tempvenv. New test `tests/packaging/test_wheel_install.py` (or extension to `test_entrypoint.py` — researcher picks): builds wheel via `python -m build`, creates temp venv, `pip install <wheel>` from the venv, asserts the post-install command surface (see `<domain>` for the exact assertion list).
- **D-17:** Marker: this test gets `@pytest.mark.slow` (existing marker per `pyproject.toml`) because it builds + installs. CI runs it on every PR; developers can `pytest -m "not slow"` locally.
- **D-18:** README install section polish. Required content: install command (`pip install voss`), `voss doctor` first-run, samples link, harness commands link, v0.1 framing line ("v0.1 is a Python harness; Rust/Homebrew later"). NO Rust install path in v0.1 docs.
- **D-19:** PyPI publish is OUT of M5 scope. Wheel smoke is the M5 contract. A release-prep checklist (post-M5) handles real PyPI publish; that checklist can live in `docs/release.md` or similar (researcher decides if it belongs in M5 at all — could be deferred to actual release time).

### Ship gate posture
- **D-20:** M5 is measurement only. No CI threshold gate. No fail-on-regression. The first `voss eval` run establishes a baseline in `.voss/eval/`. Ship-v0.1 decision is a human read of the report. Hard-gate and soft-gate options were both rejected as M5 scope.

### Claude's Discretion
- Judge model selection — pick the smallest defensible default (e.g., the same provider/model as the agent runs unless `--judge-model` overrides). `auth.resolve(role="judge")` is the suggested resolver shape; if existing `auth.resolve` doesn't support roles, extend minimally.
- Where the `Verdict` pydantic model lives — `voss/harness/eval.py` (new module) is the natural home.
- Exact shape of `task.toml` parsing (use `tomllib` from stdlib, validate with pydantic on read).
- Resume task (05) implementation detail — how to "kill mid-turn" deterministically. Subprocess kill after the planner emits a Plan but before tools dispatch is one option; in-process cancellation is another. Pick whichever is more reliable across CI environments.
- Auto-approve simulation for task 03 — the eval scorer must drive the permission gate's `[y/once/always/n]` prompt programmatically. Simplest path: an `EVAL_AUTO_APPROVE=1` env var that the gate honors (extends M1's gate). Researcher: confirm gate hook surface.
- Whether `voss eval --task 05-resume` is allowed (single-task invocation) — useful for dev iteration; suggested yes.
- Whether eval reports include a "diff vs last run" comparison in the Markdown summary — nice-to-have; out of M5 if it adds friction.
- Wheel-smoke test's exact pytest mark + directory placement — `tests/packaging/test_wheel_install.py` is the suggested home; mark it `@pytest.mark.slow`.
- README install section copy — pick what reads well; the framing line is required, the rest is style.
- Whether `voss eval --suite golden` is allowed even when golden is the only suite (yes, future-proofing the flag).
- `.voss/eval/` git tracking policy — eval reports are durable project knowledge per D-03. Default: NOT ignored by `.voss/.gitignore` (M2 D-09 ignores `sessions/` only). Researcher confirms by re-reading the M2 .gitignore decision.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v0.1 scope and product framing
- `.vscode/voss_v_0_1_scope_lock.md` §"M5: Eval and Distribution Prep" — Source of truth for EVAL-* requirements.
- `.planning/PROJECT.md` — Specifically the "Canonical repo-centric demo works" bullet (defines what the golden tasks measure) and "Python harness first, Rust later" principle (defines what's out of M5).
- `.planning/REQUIREMENTS.md` §lines 78–82 — EVAL-01..05.
- `.planning/REQUIREMENTS.md` §"Deferred Distribution / Editor / Product Surface" — DIST-01..03, EDIT-01..02, LING-01, TEAM-*, WEB-* all explicitly post-v0.1.
- `.planning/ROADMAP.md` §"Phase M5: Eval and Distribution Prep" — Phase goal, success criteria, cross-cutting constraints ("Full telemetry deferred; keep eval practical and local-first").

### Prior phase decisions (carry forward)
- `.planning/phases/M1-harness-happy-path/M1-CONTEXT.md` — Specifically D-05 (permission tiers; eval's auto-approve for task 03 hooks the gate, not bypasses it), D-13 (diagnose-don't-fix; loud-failure no-creds posture in D-10), D-07 (per-command mode defaults; task.toml `mode` field).
- `.planning/phases/M2-project-cognition/M2-CONTEXT.md` — Specifically D-09 (`.voss/.gitignore` content; eval/ default-tracked), D-13/D-14 (RunRecord schema with `cost_usd` and `Plan.confidence` source; eval reads these), D-10 (session storage path `.voss/sessions/<id>.json`; eval reads sessions from here for cost extraction).
- `.planning/phases/M3-language-validation/M3-CONTEXT.md` — Specifically D-01/D-02 (auto-StubProvider + banner; `voss eval --stub` reuses this), D-12 (raw-Python parity oracle pattern; eval-as-measurement parallels the "record what's actually true" posture).
- `.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md` — Specifically D-09 (Python `agent.py` stays as parity oracle; M5 evals the Python path, NOT the compiled `.voss` path), D-12 (M4 success bar = stub-provider real turn; M5's `--stub` mode benefits).

### Existing packaging + test surface (extend, do not rewrite)
- `pyproject.toml` — Already declares `voss = "voss.cli:main"` console script, `[project.optional-dependencies] dev` with pytest stack, `[tool.pytest.ini_options]` with `live` and `slow` markers. M5 extensions: maybe add `python -m build` as a doc/dev dep; the wheel smoke test imports it. NO new top-level deps unless judge-model client requires it (likely just reuses existing `litellm`).
- `tests/packaging/test_entrypoint.py` — Existing entry-point smoke: `pyproject.scripts` declaration check, `voss.cli.main` import check, `python -m voss.cli --help` smoke. M5 extends with the wheel-in-tempvenv test (D-16).
- `tests/harness/test_session_redaction.py` — Pattern for harness-level pytest. Eval scorer reads sessions; mirror this structure for any session-introspection helpers.
- `tests/examples/` (built in M3) — Pattern for stub-provider end-to-end tests. Eval `--stub` mode reuses StubProvider setup.
- `tests/harness/test_recorder.py` — RunRecord persistence path. Confirms where eval reads cost + confidence from.

### Harness surface eval depends on
- `voss/harness/agent.py:Plan.confidence` (line ~44) — confidence source for D-14.
- `voss/harness/session.py` (existing) — session JSON read for cost extraction (D-13).
- `voss/harness/auth.py` — `auth.resolve(preference="auto")` for provider selection (D-10). Researcher: confirm whether adding a `role="judge"` resolution path requires a small extension.
- `voss/harness/permissions.py:PermissionGate` — the gate the eval scorer must drive programmatically for task 03 (D-17, auto-approve hook). Researcher: identify the cleanest extension point.
- `voss_runtime/providers/litellm_provider.py` + `StubProvider` — both used by eval (live + stub modes).

### Demo workflow surface
- `voss doctor`, `voss do`, `voss edit`, `voss chat`, `voss resume`, `voss sessions`, `voss check`, `voss compile`, `voss tools`, `voss config` — the v0.1 surface that packaging smoke verifies installs cleanly (D-16).
- `samples/classify.voss`, `samples/support.voss`, `samples/research.voss` — used by the wheel-smoke test's `voss check samples/` assertion (M4 dir-walking if shipped; per-file otherwise).

### Existing scripts
- `scripts/dump_python_plan_schema.py`, `scripts/dump_python_tool_schemas.py` — pattern for `scripts/`-rooted helpers if eval grows a CLI-less helper.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`voss/harness/agent.py:Plan` + `TurnResult`** — Eval already has what it needs to extract confidence (D-14). No new model.
- **`voss/harness/session.py`** — Session JSON with `runs: list[RunRecord]` (M2 D-13). Eval reads these; no new persistence path.
- **`voss/harness/auth.py:resolve`** — Provider resolution. Eval reuses; may extend with `role="judge"` if researcher confirms minimal surface (D-10, Claude's discretion).
- **`voss_runtime.StubProvider`** + auto-fallback (M3 D-01) — `--stub` mode reuses.
- **`voss/cli.py`** — Existing Click `main` group; `voss eval` registers alongside existing commands (D-01).
- **`tests/packaging/test_entrypoint.py`** — Existing entry-point smoke (entry-point declaration, import, `python -m voss.cli --help`). D-16's wheel-in-venv test extends this set.
- **`pyproject.toml` `slow` marker** — Existing pytest marker; wheel smoke gets `@pytest.mark.slow` (D-17).
- **`pyproject.toml` `live` marker** — Existing marker for live-provider tests. `voss eval` itself is not a pytest test, but if any eval helper is exercised in pytest with a real provider, it gets `-m live`.
- **`tests/examples/`** (built in M3) — StubProvider + temp-project test pattern. Eval scorer reuses helpers if any are extracted to `tests/_common/`.
- **`voss/harness/permissions.py:PermissionGate`** — Programmatic gate driving for auto-approve in task 03 (D-17, Claude's discretion).
- **`voss/harness/diagnostics.py`** — Natural home for eval-specific exceptions (e.g., `NoProviderCredsError` if D-10 needs a structured exception class).

### Established Patterns
- **Loud failure on missing prerequisites** (M1 D-05, M2 D-07, M3 D-02, M4 D-10) — M5 mirrors: live eval fails loudly without creds (D-10), `--stub` is the explicit opt-out.
- **Diagnose-don't-fix** (M1 D-13) — Eval reports what it found; doesn't enforce thresholds (D-20).
- **Per-test temp git fixture** (legacy phase-06 test_helpers pattern, M3 D-09) — Eval scorer mirrors: each run gets a fresh temp git dir from `fixture/`.
- **Hermetic-by-default tests + opt-in live** (M3 D-11, `pyproject.toml` `live` marker) — Eval inverts the default (eval is live-by-default, stub for smoke) because cost + correlation are meaningful only live. The wheel-smoke test stays hermetic.
- **JSONL/Markdown report pair** (no prior art in this repo; new pattern) — JSONL is canonical, Markdown is the human read. Future eval consumers parse JSONL.
- **Pydantic JSON-mode responses** (M1 `Plan` via `response_format=Plan`) — `Verdict` follows the same pattern (D-09).
- **`.voss/` durable, `.voss-cache/` rebuildable** (M2 D-09) — Eval reports are durable (`.voss/eval/`), NOT under `.voss-cache/`.

### Integration Points
- **`voss/cli.py`** — `voss eval` registered as a new `@main.command("eval")` (D-01).
- **`voss/harness/eval.py`** (new module) — Scorer, judge call, JSONL writer, Markdown summarizer. Imports from `voss/harness/agent.py`, `voss/harness/session.py`, `voss/harness/auth.py`.
- **`tests/eval/golden/<NN>-<slug>/`** (new directories) — Five task fixtures (D-05).
- **`tests/packaging/test_wheel_install.py`** (new test) — Wheel-in-tempvenv smoke (D-16).
- **`README.md`** — Install section polish (D-18).
- **`voss/harness/permissions.py`** — Auto-approve hook for task 03 (Claude's discretion; suggested via `EVAL_AUTO_APPROVE=1` env honored by gate).

</code_context>

<specifics>
## Specific Ideas

- **The five task classes map 1:1 to ROADMAP M5 success criterion 1** — analyze, plan-only, approved edit, validation, resume. The phase doesn't invent new task classes; it makes the named ones runnable and judged.
- **JSONL is the canonical artifact** — Markdown is human-only. Future cross-version comparison reads JSONL, not Markdown.
- **`.voss/eval/` (durable) not `.voss-cache/eval/` (rebuildable)** — Eval reports ARE the v0.1 quality signal. Throwing them away loses the baseline.
- **Live default + loud no-creds failure** mirrors the rest of v0.1: never silently degrade. Cost and confidence correlation are MEANINGLESS without a real provider; defaulting to stub would silently produce zero-value numbers.
- **k=3 is a starting baseline** — small enough to be cheap (~$0.50–$2 full eval), big enough that confidence correlation has nontrivial signal across 15 datapoints (5 tasks × 3 runs).
- **LLM-as-judge with rubric per task** is the explicit M5 scoring path. No deterministic-gate prefilter (D-08) — keeps the scoring path uniform and lets rubrics evolve without changing test assertions.
- **Measurement-only ship posture** is the M5 contract — design CI gates AFTER eval baselines exist, not before. M5 produces the data; future-phase or release-prep designs the gates.
- **Wheel-in-tempvenv smoke covers the EVAL-05 ask without committing to PyPI** — proves install works; deferring publish to release-prep is the v0.1 product-discipline posture.

</specifics>

<deferred>
## Deferred Ideas

- **PyPI publish (real or TestPyPI)** — deferred to release-prep, post-M5.
- **GitHub Actions release workflow** — deferred with publish.
- **CI ship gate (success rate / cost thresholds)** — rejected as M5 scope; design after baselines exist.
- **Baseline-tracking + regression warning in CI** — deferred to a follow-on phase.
- **Per-token cost estimation under `--stub`** — rejected. No fake numbers.
- **Judge-of-judge (second model verifies first)** — rejected.
- **Deterministic rule-based scorer** — rejected. Judge stays LLM.
- **Eval against M4 compiled harness path (`VOSS_HARNESS=compiled`)** — deferred to a future hardening pass.
- **Multiple golden suites** — single suite (`golden`) in M5; `--suite` flag future-proofed.
- **Structured-rubric DSL** — rejected. Plain text per task.
- **Human-grader export workflow** — deferred.
- **Cross-provider eval matrix** — deferred.
- **Cost dashboards / time-series viz** — deferred.
- **Diff-vs-last-run comparison in Markdown summary** — Claude's discretion; out if it adds friction.
- **`docs/release.md` runbook** — Claude's discretion; can land in M5 if researcher finds it lightweight, else deferred.
- **Rust harness shell (DIST-01)** — explicitly post-v0.1.
- **Homebrew distribution (DIST-02)** — explicitly post-v0.1.
- **MCP bridge (DIST-03)** — explicitly post-v0.1.
- **Tree-sitter grammar (EDIT-01) / VSCode marketplace (EDIT-02) / Linguist PR (LING-01)** — explicitly post-v0.1.
- **Cloud sync / team collab / web UI (TEAM-*/WEB-*)** — explicitly post-v0.1.

</deferred>

---

*Phase: M5-eval-and-distribution-prep*
*Context gathered: 2026-05-11*
