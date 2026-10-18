# Methodology

This page explains how a run becomes a result. If a report says something the definitions here don't support, the report is wrong.

## One run

1. **Workspace.** The scenario's `fixture/` is copied into a fresh temp directory and committed as the git baseline `init`. Runtime and build state is excluded from git, so it never appears in a diff or a scope check. The excluded paths are `.voss/`, `.voss-cache/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `node_modules/` and `target/`.
2. **Environment.** Offline configs get a throwaway `HOME`, `XDG_*` and `CODEX_HOME`, and every `*_API_KEY`, `*_TOKEN`, `*_SECRET` and `TYPESAFE_*` variable is removed. Live configs keep the real `HOME`, because subscription auth lives there. Each record shows which isolation level applied through its `live` flag.
3. **System under test.** The config's adapter runs:
   - `oracle` applies `reference.patch`.
   - `null` changes nothing.
   - `voss-serve` starts `voss serve`, creates a session in the workspace, sends the prompt, answers permission prompts with the configured choice and reads events until `session.idle`. The wall-clock budget comes from `[budget] wall_s`.
4. **Evidence.** The staged diff (`git add -A`, so new files count), the final text, the event stream and the Voss session record are stored by sha256.
5. **Visible checks** run, followed by the **scope check**: changed paths must match `acceptance.allowed_paths` when that list is set.
6. **Hidden checks.** `hidden/` is copied into the workspace and the hidden checks run.
7. **Verdict.** `verified = all(checks passed)`. If the adapter errored, `verified` is false. If the scenario has no checks, `verified` is null (unknown).

A run is skipped when a toolchain listed in `requires` is missing. Skipped runs are listed in the report and never counted as failures.

## Claims vs verification

`claimed_complete` comes from the system itself:
- For `voss-serve`, it is true when the session's last run has `exit_reason == "done"`.
- For `oracle`, it is always true.
- For `null`, and for runs with no session record, it is null.

The report's "claimed but not verified" column counts runs where the system claimed completion and the checks disagreed. Hypothesis H1 (independent review reduces unsupported completion claims) is measured on this column.

Model judgments (the Phase 2 semantic evaluators) are stored in `judge` and never override a failing deterministic check. A passing test also does not prove a requirement is met. That gap is why hidden acceptance tests and, later, criterion-level review exist.

## Requirement review

**Review sets.** `proofs import-review` reads a frozen J4 set (`evals/review`, `evals/review-locked-2`):
1. The fixture hashes must match `freeze.json`.
2. The split's report must be complete and on the frozen commit.
3. Labels are copied, not re-scored.
4. Each record carries the rubric of the run that produced it. That can differ from the rubric at freeze time: the first set's dev split was rerun under rubric v2 for tuning.

A change should be accepted only when every criterion's gold label is *supported*. Changes with an ambiguous criterion are left out of change-level rates and counted in the report.

**Two rates, always together.** False accept is the share of should-reject changes that a config accepted. True accept is the share of should-accept changes that it accepted. Either one alone can be gamed: *author-claim* gets a perfect true accept and *reject-all* a perfect false accept. Both rules appear in every review report as bounds.

**Criterion level.** Configs that label each criterion also get false supported, supported recall, contradicted recall, abstention and a Brier score on P(supported). Reviewer B gives one verdict per change, so it has no criterion-level row. Its confidence is self-reported, so it is shown as a mean and never scored as a probability.

**Judging VossBench runs.** A config with `judge = "jev"` runs `voss judge review --criteria-file --checks --json` in the workspace. The call happens after the visible checks and before `hidden/` is installed. It passes the scenario's `acceptance.criteria` and only the visible check results. The verdict is *accept* when every criterion is supported. It goes into `judge` and never changes `verified`. The report scores both the judge and the system's own completion claim against `verified`.

**Power.** A rate over fewer than 10 items is marked underpowered. Read its interval, not its point estimate.

## Determinism

Configs with `live = false` call no model. Their results test the benchmark and the pipeline, not model capability, and reports print them in a separate section. `proofs compare A B` compares each scenario × config × run_idx on:
- skipped and verified
- claimed_complete
- exit_reason
- each check's pass/fail
- the diff hash
- the judge verdict, when a judge ran

Timings, ids and check log text are excluded, because log text includes timing. Two offline experiments should show zero differences.

Job order is shuffled with `--seed` (default 0), so a slow or stateful scenario can't systematically bias a single config.

## Statistics

- Rates are reported as `verified / graded` with a Wilson 95% interval. That interval reflects sampling error only.
- Small n is the norm in this suite, so intervals are wide on purpose. Don't read 8/8 vs 6/8 as a finding.
- Paired comparisons between configs on the same scenarios are a Phase 2+ deliverable. They will reuse the paired-bootstrap approach of the J3 retrieval eval: resampling by group, fixed seed.
- There is no composite score. Each dimension stays visible.

## Cost and usage

- Unknown cost is recorded as `null` and shown as "unknown", never as zero.
- `oracle` and `null` record a known zero with `cost_source = "no model"`.
- For `voss-serve`, cost comes from `/session/{id}/cost` when the server recorded at least one run. Token counts come from the saved session record.
- The fake serve turn records no run, so its cost stays unknown.
- When Voss reports $0 for a run that consumed tokens, the cost is recorded as unknown. Subscription providers do this.
- Token counts are stored as recorded: prompt, completion, cache creation and cache read. None of them is summed into a single "input tokens" figure.

## Turns that never ran

`voss serve` can send a message to ambient chat instead of the agent loop (upstream gap 14). If no `status` event with phase `run` appears, the adapter records the turn as follows:
- `exit_reason = "no-run"`, with an error explaining why.
- `claimed_complete = null`.

The checks still run, so a no-run counts as a failed attempt in the verified rate.

## Contamination controls

- Hidden tests live outside the workspace until the system under test exits. A test asserts they are absent during the run.
- Workspaces are temp directories outside this repository. The agent's cwd contains only the fixture.
- **Known limit:** a live agent with shell access could still read this repository by absolute path, because there is no OS sandbox on macOS. Until runs use an OS sandbox (Voss-OS) or a container, a live result from scenarios stored in this repo is a dev-set result, not a locked holdout result.
- Locked datasets, from Phase 4 on, follow the J3/J4 pattern: `freeze.json` hashes, a run-once marker, and no tuning against the locked split.
