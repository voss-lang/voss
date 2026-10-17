# Methodology

This page explains how a run becomes a result. If a report says something the definitions here don't support, the report is wrong.

## One run

1. **Workspace.** The scenario's `fixture/` is copied into a fresh temp directory and committed as the git baseline `init`. Runtime state under `.voss/` is excluded from git, so it never appears in a diff.
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

## Determinism

Configs with `live = false` call no model. Their results test the benchmark and the pipeline, not model capability, and reports print them in a separate section. `proofs compare A B` compares each scenario × config × run_idx on:
- skipped and verified
- claimed_complete
- exit_reason
- each check's pass/fail
- the diff hash

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

## Contamination controls

- Hidden tests live outside the workspace until the system under test exits. A test asserts they are absent during the run.
- Workspaces are temp directories outside this repository. The agent's cwd contains only the fixture.
- **Known limit:** a live agent with shell access could still read this repository by absolute path, because there is no OS sandbox on macOS. Until runs use an OS sandbox (Voss-OS) or a container, a live result from scenarios stored in this repo is a dev-set result, not a locked holdout result.
- Locked datasets, from Phase 4 on, follow the J3/J4 pattern: `freeze.json` hashes, a run-once marker, and no tuning against the locked split.
