# Phase E1: Eval Substrate - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

E1 is gap-closure on the already-built M5 eval substrate (`voss/eval/`): add hybrid scoring (deterministic `checks` gates + existing LLM judge), per-run turn caps, an internal-only dev gate on `voss eval`, a judge-model default split, and prove the whole thing with one live full-golden-suite run on codex subscription auth. No rebuild — `suite.py`/`runner.py`/`judge.py`/`summary.py` and the 6 golden tasks are the foundation.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**7 requirements are locked.** See `E1-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `E1-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** `checks` schema in TaskSpec + check executor (3 check types); hybrid gate/judge plumbing through JSONL + summary.md; retrofit checks onto all 6 golden tasks; `max_turns` per-task cap + upfront run-size print; `VOSS_DEV=1` gate on `voss eval`; judge-model default split + dual-model recording; one live full-suite proof run on codex auth.

**Out of scope (from SPEC.md):** new golden tasks / repo-shape matrix (E2); surface e2e (E3); SDK proof (E4); TUI/voss-app driving (E5); CI or scheduled runs; token-budget envelope integration (turn caps chosen); success-rate-over-N repeat harness; `voss/eval/` redesign; judge prompt/rubric quality work.

</spec_lock>

<decisions>
## Implementation Decisions

### Check executor
- **D-01:** `task.toml` checks = `[[checks]]` array of typed tables with `type` discriminator: `{type="cmd", run="..."}` / `{type="file_exists", path="..."}` / `{type="file_contains", path="...", text="..."}`. Pydantic discriminated union on `TaskSpec` (keep `extra="forbid"`).
- **D-02:** Run all checks, report all — no short-circuit. JSONL row carries a per-check results array (type, pass, detail); `gate_pass` = conjunction.
- **D-03:** `cmd` checks: 60s default timeout, optional per-check `timeout` field override. Run in the task's isolated fixture copy (M5 D-06 temp git dir), stdlib subprocess only.

### Caps
- **D-04:** `max_turns` default = 15 per task. Golden tasks finish in 3–8 turns today; 15 bounds runaways without capping legit work.
- **D-05:** Capped task ⇒ recorded FAIL with `capped: true`; **judge is skipped** (`judge_verdict: "skipped"`) — don't burn sub turns judging a partial transcript.
- **D-06:** Defaults live in an `[eval]` config section (`max_turns`, `judge_model`); `--max-turns` CLI flag overrides config. Matches existing config patterns.

### Dev gate
- **D-07:** `VOSS_DEV=1` checked in the CLI command callback — fails at verb entry before any auth/provider/fixture work. `run_suite` stays importable/programmatically usable without the var.
- **D-08:** Var name is `VOSS_DEV` (generic internal-tooling gate, reusable for future E3–E5 internal verbs), not eval-specific.
- **D-09:** `tests/eval/conftest.py` sets `VOSS_DEV=1` autouse for the existing suite; plus 2 explicit gate tests: (a) no var ⇒ exit ≠ 0 + stderr message + zero model calls, (b) var set ⇒ proceeds.

### Judge model
- **D-10:** Default judge = **smaller/cheaper gpt-5.x variant** than the actor's default, same codex subscription auth. Concrete model id picked by researcher/planner from what codex auth exposes. Precedence: `--judge-model` flag > `[eval].judge_model` config > pinned default.
- **D-11:** If resolved judge model == actor model (user override), **warn on stderr + proceed** — never hard-error an internal tool. Row still records both models (JSONL `model` + `judge_model` fields already exist per M5 D-04).

### Claude's Discretion
- Exact stderr wording for the dev-gate message and same-model warning.
- Conftest mechanics (autouse fixture vs env in pytest config).
- Concrete judge model id (within "smaller gpt-5.x variant" constraint).
- summary.md column layout for the new gate-pass vs judge-rate columns.
- Where the turn counter hooks the agent loop (runner-level vs harness iteration param) — pick what's least invasive to the harness.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract
- `.planning/phases/E1-eval-substrate/E1-SPEC.md` — Locked requirements — MUST read before planning.
- `.planning/notes/e-track-eval-decisions.md` — E-track decision log (backend, judging, cadence, M5 supersession, phase sketch).

### M5 substrate (the code being extended)
- `.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md` — Prior decisions still binding: JSONL row schema (D-04), fixture isolation (D-06), task.toml schema (D-07), `.voss/eval/<timestamp>/` output layout (D-02/D-03), judge Verdict contract.
- `.planning/phases/M5-eval-and-distribution-prep/M5-05-SUMMARY.md` — Golden task contracts (what each of the 6 tasks expects — source for retrofit checks).

### Live-auth path
- `voss/harness/auth.py` — Codex subscription auth + `resolve(role=...)`; backend quirks (no temperature/max_tokens, gpt-5.x only) must not regress.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `voss/eval/suite.py` — `TaskSpec` (pydantic, `extra="forbid"`) + `load_task`/`load_suite`; `checks` becomes a new validated field.
- `voss/eval/runner.py` (381 lines) — `run_suite`, `_drive_task`/`_drive_resume`, `_prepare_fixture` (temp git isolation), `_provider_for_eval`/`_judge_provider_for_eval` (role-split auth), `_append_row` JSONL writer. Check executor and turn cap slot in here.
- `voss/eval/judge.py` — `Verdict` + `judge_run`; untouched except skip-on-capped path.
- `voss/eval/summary.py` — summary.md + Pearson; gains gate-pass vs judge-rate columns.
- `tests/eval/` — 30 green tests incl. stub-mode suite runs + creds-gated live signals; `tests/eval/golden/` 6 tasks.

### Established Patterns
- Stub-mode (`--stub`) hermetic testing — new check/cap behavior must be testable under stub with zero creds.
- `judge_verdict: "skipped"` already exists as a value (M5: stub-without-creds path) — capped tasks reuse it.
- JSONL canonical + summary.md derived — new fields extend the row, never break existing columns.

### Integration Points
- `voss eval` CLI registration (Click subcommand) — dev-gate callback wraps here.
- Config system — new `[eval]` section for `max_turns` / `judge_model` defaults.
- Agent drive loop in `_drive_task` — turn cap enforcement point (least-invasive hook at Claude's discretion).

</code_context>

<specifics>
## Specific Ideas

- Live proof run = the phase's closing act: full 6-task golden suite, `--auth codex`, ≥5/6 gate_pass, 0 capped rows, artifacts (JSONL + summary.md) recorded in the phase SUMMARY.
- Run header must print `N tasks · max M turns/task` before the first model call — operator sees sub-burn exposure upfront.

</specifics>

<deferred>
## Deferred Ideas

- Live-proof artifact commit policy (commit run outputs vs path-reference only) — decide at execution; SPEC allows either.
- Repeat-N success-rate statistics (`-k` exists but no aggregation contract) — E2+ when a consumer needs it.
- Gate reuse for E3–E5 internal verbs (`VOSS_DEV` is designed generic for this).

</deferred>

---

*Phase: E1-eval-substrate*
*Context gathered: 2026-06-10*
