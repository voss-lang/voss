# Methodology

This page explains how a run becomes a result. If a report says something the definitions here don't support, the report is wrong.

## One run

1. **Workspace.** The scenario's `fixture/` is copied into a fresh temp directory and committed as the git baseline `init`. Runtime and build state is excluded from git, so it never appears in a diff or a scope check. The excluded paths are `.voss/`, `.voss-cache/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `node_modules/` and `target/`.
2. **Environment.** No run inherits the session variables of an agent that is driving `proofs` (`CLAUDECODE`, `CLAUDE_CODE_*`, `CODEX_COMPANION_*`). Offline configs get a throwaway `HOME`, `XDG_*` and `CODEX_HOME`, and every `*_API_KEY`, `*_TOKEN`, `*_SECRET` and `TYPESAFE_*` variable is removed. Live configs keep the real `HOME`, because subscription auth lives there. Each record shows which isolation level applied through its `live` flag.
3. **System under test.** The config's adapter runs:
   - `oracle` applies `reference.patch`.
   - `null` changes nothing.
   - `voss-serve` starts `voss serve`, creates a session in the workspace, sends the prompt, answers permission prompts with the configured choice and reads events until `session.idle`. The wall-clock budget comes from `[budget] wall_s`.
   - `cli-agent` (Baseline A) runs one external coding agent non-interactively in the workspace, with stdin closed and the same wall-clock budget. When the budget runs out, the agent's whole process group is killed.
     - `claude` runs as `claude -p --output-format json`. File edits are accepted. Shell commands run in the Claude Code sandbox, so they can write only inside the workspace. User settings, hooks and MCP servers are off.
     - `codex` runs as `codex exec --json` in the `workspace-write` sandbox, with the user's `config.toml` ignored.
   - `voss-swarm` (Configuration C) starts `voss serve` and creates a swarm with the default roster: a coordinator, `builders` native builders (default 2) and a reviewer. It then calls `/swarm/{id}/run`. The coordinator splits the prompt into tasks, and each builder runs one turn in the workspace. The adapter watches every member session's events, answers permission prompts and stops on `swarm.complete` or on a `decompose_failed`, `run_failed` or `run_incomplete` gate. The wall-clock budget covers the whole swarm.
4. **Evidence.** The staged diff (`git add -A`, so new files count), the final text, the event stream and the Voss session record are stored by sha256.
5. **Visible checks** run, followed by the **scope check**: changed paths must match `acceptance.allowed_paths` when that list is set.
6. **Hidden checks.** `hidden/` is copied into the workspace and the hidden checks run.
7. **Verdict.** `verified = all(checks passed)`. If the adapter errored, `verified` is false. If the scenario has no checks, `verified` is null (unknown).

A run is skipped when a toolchain listed in `requires` is missing. Skipped runs are listed in the report and never counted as failures.

## Claims vs verification

`claimed_complete` comes from the system itself:
- For `voss-serve`, it is true when the session's last run has `exit_reason == "done"`.
- For `oracle`, it is always true.
- For `voss-swarm`, it is true when the swarm emits `swarm.complete`, and false when it emits a failure gate. A member's task counts as done when its turn ends, whether or not the member did the work (upstream gap 18). So `swarm.complete` is a claim, and the hidden checks decide.
- For `cli-agent`, it is true when the agent finished without an error: `claude` reports `subtype: success`, and `codex` completes a turn with no failure event.
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
- **Paired comparisons.** For each pair of configs with the same `live` flag, the report gives the difference in verified rate, paired by scenario. Each scenario's rate is its verified share over k runs. The 95% interval is a paired bootstrap over scenarios: 10,000 resamples with seed 20261024, the same method as the J3 retrieval eval. A pair with fewer than 10 scenarios is marked underpowered.
- There is no composite score. Each dimension stays visible.

## Versioned scenario sets

`proofs freeze --bench <set>` writes `<set>/freeze.json`, which holds each scenario's version and the sha256 of its directory. `proofs run` and `proofs validate` check the whole set against it, even when `--task` narrows the run. They refuse to start if a scenario changed, appeared or disappeared, and the run's manifest records the freeze hash.

To change a frozen scenario, bump its `meta.version` and freeze again. `regression`, `orchestration` and `memory` are frozen as dev sets.

A set frozen with `--locked` is a held-out set. A live run on it needs `--locked-final`, and each config may run it once. The claim goes into `<set>/locked-runs.jsonl` before any run starts, so a crashed run still counts. Nothing may be tuned against a locked set.

A locked set's answers are sealed, because a live agent can read any file your user can read, and committed plaintext answers can also end up in model training data. `proofs seal --bench <set>` works like this:
1. It runs `validate`.
2. It asks for a key twice.
3. It encrypts each scenario's `hidden/` and `reference.patch` into `answers.enc` with `openssl` (AES-256, PBKDF2).
4. It checks that the archive opens, then deletes the plaintext.

After sealing, freeze the set with `--locked`. At run time, the answers are decrypted into a temp directory only after the system under test exits, or for `oracle`, which calls no model. The key is typed in when `proofs` asks. It is never put in an environment variable or a file, because other processes of the same user can read both, including through `ps eww` on macOS. A lost key cannot be recovered.

## Multi-step scenarios and memory (H4)

A scenario may list follow-up prompts in `steps`. The runner sends the prompt and then each step to the same workspace, and the checks run once at the end. Step results are merged:
- tokens and cost are summed, and cost stays unknown if any step's cost is unknown
- the exit reason is the first step that did not finish
- artifacts are kept per step
- a step that does not finish ends the sequence

`oracle` and `null` act once.

`memory` in a config decides what a later step can see:
- `fresh` (default): a new session per step. It sees the workspace and whatever the system itself persisted.
- `resume`: the step continues the previous step's session. `voss-serve` passes `resume=<session id>` to `POST /session`. `cli-claude-resume` runs `claude -p --resume`.

Claude Code keeps its own auto-memory per workspace path, so plain `cli-claude` also carries facts between steps. `cli-claude-nomemory` turns that off with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, which makes it the no-memory control.

The memory set separates two cases:
- `mem-001` needs a fact that exists only in the conversation.
- `mem-002` needs a convention that the step-1 code also shows.

## Cost and usage

- Unknown cost is recorded as `null` and shown as "unknown", never as zero.
- `oracle` and `null` record a known zero with `cost_source = "no model"`.
- For `voss-serve`, cost comes from `/session/{id}/cost` when the server recorded at least one run. Token counts come from the saved session record.
- The fake serve turn records no run, so its cost stays unknown.
- When Voss reports $0 for a run that consumed tokens, the cost is recorded as unknown. Subscription providers do this.
- `voss-swarm` sums `/cost` and the session-record tokens over its member sessions. The coordinator's task split runs outside any session, so it is missing from both totals (upstream gap 19).
- `claude -p` reports `total_cost_usd` even on a subscription. It is stored with a `cost_source` that says it is a list-price estimate. `codex exec` reports no cost, so codex cost is unknown.
- Token counts are stored as recorded: prompt, completion, cache creation and cache read. None of them is summed into a single "input tokens" figure.

## Turns that never ran

`voss serve` can send a message to ambient chat instead of the agent loop (upstream gap 14). If no `status` event with phase `run` appears, the adapter records the turn as follows:
- `exit_reason = "no-run"`, with an error explaining why.
- `claimed_complete = null`.

The checks still run, so a no-run counts as a failed attempt in the verified rate.

## Contamination controls

- Hidden tests live outside the workspace until the system under test exits. A test asserts they are absent during the run.
- Workspaces are temp directories outside this repository. The agent's cwd contains only the fixture.
- `codex exec` always loads `~/.codex/AGENTS.md`, the user's personal instructions. The only way to skip that file is a separate `CODEX_HOME`, which would split the Codex login, so `cli-codex` runs carry the user's instructions. `cli-claude` loads no user settings or memory. Prefer `cli-claude` as Baseline A.
- **Known limit:** a live agent with shell access could still read this repository by absolute path, because there is no OS sandbox on macOS. Until runs use an OS sandbox (Voss-OS) or a container, a live result from scenarios stored in this repo is a dev-set result, not a locked holdout result.
- Locked sets use `freeze.json` hashes and a run-once marker (see "Versioned scenario sets").
- After every run, its own output is scanned for the benchmark's source path and answer file names. That output is the events, final text, session records, swarm state and diff. A match is recorded in `contamination`, and the report lists those runs as possibly contaminated. `claude -p` runs with `--output-format stream-json`, so its tool calls are in the scanned events. Reads that leave no trace in a system's output can still go undetected.
- Live runs share the real HOME, and Claude Code keeps sessions and auto-memory under `~/.claude/projects/<workspace path>`. An earlier run of the same scenario could leave answers there. A live agent was seen browsing those folders. So workspace cleanup deletes the Claude project folder for its own workspace path, and no other one. That covers both `claude -p` and the claude-agent provider inside `voss serve`.
