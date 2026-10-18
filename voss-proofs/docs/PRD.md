# VossProofs PRD and roadmap

## Goal

VossProofs produces reproducible evidence about how well the Voss ecosystem works. It asks when Voss's architecture beats simpler agent setups, where it fails, and what each component adds or costs. It is not a pass/fail test suite, and it does not produce a headline score.

**Primary research question.** Under comparable conditions, when does Voss's structured, confidence-aware, multi-agent architecture produce better software engineering outcomes than simpler agent setups?

**Hypotheses.** Each one gets tested. None is assumed.

- **H1.** Independent review reduces unsupported completion claims compared with a single agent judging its own work.
- **H2.** Multi-agent orchestration improves verified completion on complex enough tasks, and may lose efficiency on small ones.
- **H3.** Explicit decision judgments improve specific decision quality or calibration over heuristic confidence.
- **H4.** Persistent project memory improves performance on related multi-step tasks.
- **H5.** Budget and scope enforcement reduce runaway spend and unauthorized actions without hurting legitimate completion much.

## Principles

- **Consume, don't copy.** Voss is driven through `voss serve`, the CLI and frozen dataset files. Harness internals are not imported. A reimplementation must first show why the public contract falls short.
- **Separate claims from verification.** What a system says about its run is recorded apart from what the checks show.
- **Deterministic checks decide.** Model-assisted judgments add information and never override a failing check.
- **Label everything.**
  - Deterministic results are kept apart from live ones.
  - Synthetic scenarios are kept apart from real ones.
  - Unknown values are recorded as null, never as zero.
- **Live runs are opt-in and capped.** They need `--live` plus `--max-runs`, and can also take `--max-usd`.
- **Jev runs only when asked.** It is invoked only by configs that name it.

## What already exists (Phase 0 inventory)

| Asset | Location | Status | How VossProofs uses it |
|---|---|---|---|
| Suite runner: 9 surfaces, stub mode, k runs, A/B | `voss/eval/runner.py`, `voss eval` (needs `VOSS_DEV=1`) | Implemented | `proofs import-voss-eval` ingests its `runs.jsonl`. Task specs load unchanged. |
| Task spec (`task.toml`) | `voss/eval/suite.py` | Implemented | The run.v1 task spec is a strict superset. |
| J4 requirement-assessment eval | `voss/eval/review.py`, `evals/review/` | Frozen. The locked run is being redone on a branch. | Phase 2 baseline. Run through `python -m voss.eval.review`. |
| J3 retrieval eval | `voss/eval/retrieval.py`, `evals/retrieval/` | Frozen. Locked run done. | Memory & Retrieval suite reference. |
| Requirement review on any diff | `voss judge review --json` | Implemented (needs a Jev key) | Phase 2 semantic evaluator |
| Headless driving | `voss serve`: `/session`, `/message`, `/events`, `/permission`, `/cost` | Implemented | `voss-serve` adapter |
| Offline serve turn | `VOSS_SERVE_FAKE_TURN=1` | Test seam | `voss-serve-fake` config |
| Swarm over the API, worktree per CLI member | `POST /swarm`, `/swarm/{id}/run` | Implemented | Phase 3 multi-agent config |
| Board and EM | `voss/harness/board/`, `em/`, `voss team run` | Partial: stubbed reviewers, interactive sign-off | Blocked (upstream gap 5) |
| Workflow replay | voss-lang `voss-exec replay` and `tests/exec-fixtures` | Implemented | Phase 4 runtime suite |
| Sandbox probe | Voss-OS `smoke-test-sandbox.sh` | Implemented, Linux only | Optional Phase 4+ adapter |

[upstream-gaps.md](upstream-gaps.md) lists what's missing.

## Architecture

```
voss_proofs/
  spec.py       task.v1 / config.v1 / run.v1 pydantic contracts (schemas/ is generated)
  workspace.py  fresh git workspace per run, env isolation, staged diff, hidden-test install
  adapters.py   systems under test: oracle, null, voss-serve
  evaluate.py   cmd/file checks, scope check, verdict
  runner.py     scenarios x configs x k, seeded order, run caps, manifest
  store.py      sha256 object store + append-only runs.jsonl
  report.py     Wilson intervals, per-config and per-scenario tables, compare
  ingest.py     voss eval runs.jsonl -> run.v1
  cli.py        proofs run | validate | report | compare | import-voss-eval | schema
```

New adapters are added to `ADAPTERS` and to the `Config.adapter` literal. Split a module only once it grows past one screen of responsibility.

## Roadmap

### Phase 1: VossEvals foundation (this branch)

Delivered:
- The `proofs` CLI and the run.v1 record.
- Isolated workspaces with hidden acceptance tests.
- The content-addressed evidence store.
- Markdown reports.
- `voss eval` import.
- Oracle and null baseline validation.
- Eight regression scenarios across Python, Rust, TypeScript and Go.

**Gate.** Several scenarios run in isolated workspaces and produce inspectable evidence, and repeated runs give identical deterministic results without a live model. Met by:
- `proofs validate`
- two `proofs run` experiments with `proofs compare`, which show 0 differences
- the test suite

**Next in this phase:**
- Grow the regression set to 20–30 scenarios. Add an ambiguity/clarification scenario and a defective-PR review scenario.
- Add a `cli-agent` adapter for Baseline A, a single external coding agent run non-interactively.

### Phase 2: Decision and review research (H1, H3)

Delivered:
- `proofs import-review` reads a frozen J4 review set. It checks the `freeze.json` hashes, requires a complete report on the same commit, and writes review.v1 records with labels copied as-is. With `--run-dev --live` it first runs `voss.eval.review` on the dev split in a temp copy, so Voss's files stay untouched. Locked splits are imported and never rerun.
- Four review configs:
  - *author-claim*, which accepts every change
  - *reject-all*, which rejects every change
  - *jev*, the Jev requirement review
  - *reviewer-b*, the existing Reviewer B baseline
- Change-level false accept and true accept, always shown together. Criterion-level false supported, supported recall, contradicted recall, abstention and Brier on P(supported). Self-reported confidence is shown on its own and never scored as a probability. Any rate over fewer than 10 items is marked underpowered.
- An opt-in Jev judge for VossBench runs (`judge = "jev"`, live configs only). It runs `voss judge review` on the diff after the visible checks and before hidden tests exist, and it sees only the visible checks. The report scores the judge and the system's own completion claim against `verified`.
- First study: [studies/2026-10-18-review-baselines.md](studies/2026-10-18-review-baselines.md).

**Gate.** A report that compares at least two valid configs on these metrics. Met by the locked-set study, which compares four.

**Next in this phase:**
- Run `oracle-jev`, `null-jev` and `voss-serve-auto-jev` once a Jev key is available.
- Add accept-worthy changes, so change-level true accept stops being underpowered (upstream gap 17). VossBench `oracle-jev` adds 8 now. A decoy patch per scenario (passes the visible tests, fails the hidden ones) would add matched negatives.
- Add a heuristic-confidence baseline on the same pairs, so H3 can be tested.

### Phase 3: Swarm and orchestration (H2, H5)

Delivered:
- **Baseline A, `cli-agent`.** It runs `claude -p` or `codex exec` non-interactively in the workspace. Each runs in its tool's sandbox, with stdin closed and the scenario's wall budget. `cli-claude` loads no user settings. `cli-codex` always loads `~/.codex/AGENTS.md`.
- **Baseline B, `voss-serve`.** One session, from Phase 1.
- **Configuration C, `voss-swarm`.** `POST /swarm` with the default roster, then `/swarm/{id}/run`. The adapter watches every member session and sums usage over them.
- **Shared model.** All three Phase 3 configs name `claude-opus-5-5`. The report warns when the live configs in one experiment ran different models.
- **Five scenarios** in `benchmarks/orchestration`:
  - parallel independent modules
  - a shared file
  - dependent changes across files
  - contradictory tests under a token budget
  - a partial spec

  Worker failure and retry needs fault injection in the harness, so dependent changes replaced it.
- **A resources and limits table.** Tokens against the scenario budget, timeouts and scope violations.
- First gate run: [studies/2026-10-18-orchestration-gate.md](studies/2026-10-18-orchestration-gate.md).

Board/EM stays "not evaluable" until upstream gap 5 is closed.

**Gate.** The same scenario runs under A, B and C with comparable evidence and resource records. Met by the gate run: 5 scenarios × 3 configs, all on one model.

**Next in this phase:**
- k ≥ 3 per cell, and larger multi-file scenarios where splitting the work could pay off.
- Pass the token budget to each system where it accepts one, so H5 measures enforcement as well as overshoot.
- A fault-injection scenario for worker failure and retry.

### Phase 4: Expanded VossBench (H4)

- Dev set of 80–120 scenarios plus a locked subset, frozen with `freeze.json` hashes and a run-once marker.
- Memory suite: wrap J3, and add related-task sequences.
- Safety suite: denial scenarios from `.voss/safety.yml`.
- Runtime suite: `voss-exec replay` parity and `voss check` diagnostics.
- Optional env-specific adapters for ADE core and the Voss-OS sandbox. These are labeled as not covered by headless CI.
- Repeated-run comparisons with k ≥ 3 on a fixed subset. Paired bootstrap between configs.

**Gate.** A versioned corpus, automated grading, documented contamination controls and repeated-run comparisons.

### Phase 5: First formal study

1. Pre-register the hypotheses and analysis plan in `docs/studies/` before any locked run. Record its hash in the experiment manifest.
2. Freeze the benchmark versions.
3. Run the locked comparisons.
4. Publish *"Evaluating Confidence-Aware Multi-Agent Software Engineering: An Empirical Study of Voss"*. It includes negative results and threats to validity: a single model, synthetic tasks, judge non-objectivity, and no OS sandbox on macOS.

## Non-goals for now

- A dashboard. The CLI, JSON records and Markdown reports come first.
- A composite quality score.
- Disabling safety protections to improve benchmark numbers.
