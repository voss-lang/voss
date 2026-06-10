---
phase: E4-sdk-proof
plan: 07
type: execute
wave: 5
depends_on: [E4-06]
files_modified:
  - tests/eval/sdk/05-ts-permission-deny/task.toml
  - tests/eval/sdk/05-ts-permission-deny/fixture/calc.py
  - tests/eval/sdk/consumers/ts/consumer.js
  - voss/eval/suite.py
  - voss/eval/runner.py
  - tests/eval/test_sdk.py
  - .planning/phases/E4-sdk-proof/E4-PROOF.md
autonomous: false
requirements: [EVSDK-07, EVSDK-08]
must_haves:
  truths:
    - "A Deny-variant scenario exists for the ts client: in live mode the agent hits a gated tool call, the consumer replies Deny, and the turn degrades to a final WITHOUT hanging"
    - "The permission-gate live scenarios are marked live-only and SKIP in automated runs (FAKE_TURN emits no permission.updated; the gate needs real creds)"
    - "One documented live codex run covers >=1 scenario per surface (sdk:python, sdk:ts, sdk:go, sdk:rust), achieves >=80% gate_pass, 0 capped rows, with the permission scenario among the passers"
    - "The Allow round-trip is proven live through each client SDK (consumer receives permission.updated, replies a, reaches final); the Deny variant degrades without hang"
    - "A human checkpoint gates the live proof run (operator supplies codex subscription creds; nothing in CI can run it)"
    - "The proof artifacts (run dir, summary, per-surface gate_pass, sub-burn) are recorded in E4-PROOF.md and referenced in the phase SUMMARY"
  artifacts:
    - path: "tests/eval/sdk/05-ts-permission-deny/task.toml"
      provides: "sdk:ts Deny variant (live: turn degrades without hang)"
      contains: "surface = \"sdk:ts\""
    - path: "voss/eval/runner.py"
      provides: "_drive_sdk_client forwards VOSS_PERMISSION_CHOICE so the deny scenario replies d"
      contains: "VOSS_PERMISSION_CHOICE"
    - path: ".planning/phases/E4-sdk-proof/E4-PROOF.md"
      provides: "the documented live proof run record (command, run dir, per-surface gate_pass, capped count, permission verdicts, total sub-burn)"
      contains: "gate_pass"
  key_links:
    - from: "tests/eval/sdk/05-ts-permission-deny/task.toml"
      to: "the ts consumer Deny path (choice=d)"
      via: "live permission Deny -> turn degrades to final without hang"
      pattern: "surface = .sdk:ts."
    - from: ".planning/phases/E4-sdk-proof/E4-PROOF.md"
      to: "voss eval --suite sdk --auth codex"
      via: "the operator-run live proof; >=1 scenario/surface, >=80% gate_pass, 0 capped, permission scenario passes"
      pattern: "--suite sdk --auth codex"
---

<objective>
Wave 4 — phase close (EVSDK-07, EVSDK-08): prove the permission-gate round-trip LIVE through each SDK client and run the one documented live proof on codex subscription auth, gated by a human checkpoint. This is the marquee proof of E4: an external developer can drive the full live plane — spawn -> session -> typed SSE events -> gated tool call -> Allow/Deny -> final -> read audit — via the published client, which nothing proves today (V13.x tests are drift/type + stub-server only).

The permission gate is LIVE-ONLY (RESEARCH Pitfall 3): `VOSS_SERVE_FAKE_TURN` emits no `permission.updated` (app.py:166-178). The Allow scenarios (plan 06's 02/03/04) and the new Deny variant only exercise the gate with real creds; in automated runs they SKIP. The operator runs the proof with `--auth codex` and records the artifacts.

Proof criteria (D-08, mirrors E3 D-11 / E1 EVSUB-07): one documented live run; every surface (sdk:python/ts/go/rust) has >=1 scenario; overall >=80% gate_pass; 0 capped rows; the permission-gate scenario is among the passers; total sub-burn surfaced upfront in the run header; artifacts recorded in E4-PROOF.md + the phase SUMMARY.

Budget note: plan 06 created 4 scenarios (one Allow per surface). This plan adds ONE Deny variant (ts) -> 5 scenarios total, within the <= ~8 sub-burn budget. The Deny path is proven on one client (ts) as representative; Allow is proven on all four. The live run is turn-capped (0 capped is a pass criterion) so there is no runaway spend.

Purpose: Prove the live permission round-trip per client + run the documented codex proof under an operator checkpoint.
Output: Deny-variant scenario + env-driven choice forwarding + live-only markers + E4-PROOF.md proof record + human checkpoint.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E4-sdk-proof/E4-CONTEXT.md
@.planning/phases/E4-sdk-proof/E4-RESEARCH.md
@.planning/phases/E4-sdk-proof/E4-PATTERNS.md
@.planning/phases/E4-sdk-proof/E4-VALIDATION.md

<interfaces>
<!-- The four Allow scenarios exist from plan 06: tests/eval/sdk/{01-python-basic, 02-ts-permission-allow, 03-go-permission-allow, 04-rust-permission-allow}/task.toml -->
<!-- The three consumers' permission branches reply choice="a" (Allow). For the Deny variant the consumer must reply "d".
     The ts consumer (plan 03) honors VOSS_PERMISSION_CHOICE (default "a"); this plan adds an optional permission_choice
     field to TaskSpec that _drive_sdk_client forwards as VOSS_PERMISSION_CHOICE so the deny scenario replies "d"
     without a second consumer file. -->

<!-- suite.py TaskSpec (extra="forbid") — adding ONE optional field: permission_choice: str | None = None.
     This is NOT a JSONL row key — REQUIRED_FIELDS (test_voss_eval_stub.py) is unaffected. -->

<!-- _drive_sdk_client (runner.py, plan 02) builds consumer_env. Add: if spec.permission_choice: env["VOSS_PERMISSION_CHOICE"]=spec.permission_choice -->

<!-- Live run command (run_suite flags): VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite sdk --auth codex [--task <id>] [-k 1] -->
<!-- auth: voss/harness/auth.py codex subscription path; quirks (no temperature/max_tokens, gpt-5.x only) must not regress -->
<!-- gate/judge/JSONL all inherited from E1; the row carries surface (E3-01). Proof reads .voss/eval/<ts>/{runs.jsonl, summary.md}. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Deny-variant scenario + permission_choice forwarding + live-only markers</name>
  <files>tests/eval/sdk/05-ts-permission-deny/task.toml, tests/eval/sdk/05-ts-permission-deny/fixture/calc.py, tests/eval/sdk/consumers/ts/consumer.js, voss/eval/suite.py, voss/eval/runner.py, tests/eval/test_sdk.py</files>
  <read_first>
    - tests/eval/sdk/02-ts-permission-allow/task.toml (the Allow analog from plan 06 — the Deny variant mirrors it with the opposite choice + a degrade-without-hang rubric)
    - tests/eval/sdk/consumers/ts/consumer.js (the hardened consumer from plan 03 — the permission.updated branch; confirm it already reads VOSS_PERMISSION_CHOICE, add it if plan 03 hardcoded "a")
    - sdk/typescript/src/client/permission.ts (replyPermission valid choices — "a"/"A"/"d"/"y"/"n"; confirm "d" is the deny choice)
    - voss/eval/suite.py (TaskSpec fields + extra="forbid" — add the optional permission_choice field next to target_file; it is the ONLY new TaskSpec field in E4)
    - voss/eval/runner.py (`_drive_sdk_client` consumer_env build from plan 02 — forward permission_choice as VOSS_PERMISSION_CHOICE when set)
    - voss/harness/server/app.py (lines 166-178 — FAKE_TURN emits no permission.updated; the Deny path is live-only)
    - tests/eval/test_sdk.py (the EVSDK-07 live-only skip stub from plan 02 — extend the marker docs to cover Allow+Deny per client)
    - .planning/phases/E4-sdk-proof/E4-VALIDATION.md (Manual-Only Verifications lines 69-72 — the live permission round-trip + Deny degrades-without-hang)
  </read_first>
  <action>
    (1) Add an optional `permission_choice: str | None = None` field to TaskSpec in voss/eval/suite.py (immediately after target_file; extra=forbid-safe because it is an explicit declared field). This is the ONLY new TaskSpec field E4 introduces and it is NOT a JSONL row key — REQUIRED_FIELDS stays unchanged.

    (2) In voss/eval/runner.py `_drive_sdk_client`, when building consumer_env, add: `if spec.permission_choice: consumer_env["VOSS_PERMISSION_CHOICE"] = spec.permission_choice`. This lets the Deny scenario set the consumer's reply to "d" via the task.toml.

    (3) Ensure the ts consumer (tests/eval/sdk/consumers/ts/consumer.js) reads `const choice = process.env.VOSS_PERMISSION_CHOICE || "a"` and passes `choice` to replyPermission (it should already from plan 03 if that plan made it env-driven; if it hardcoded "a", change it here — idempotent). saw_permission_gate stays true on any permission.updated regardless of choice. Re-verify `node --check` and the no-VossLauncher grep still hold.

    (4) Create tests/eval/sdk/05-ts-permission-deny/ with the shared shape-agnostic calc.py fixture (copy plan 06's fixture/calc.py) and a task.toml: surface = "sdk:ts"; mode = "plan"; permission_choice = "d"; prompt asks for an action requiring a gated tool call; rubric PASS if, when the permission is DENIED, the turn degrades to a final WITHOUT hanging (the agent reports it could not complete the gated action, no infinite wait); judge_inputs = ["final"]. extra=forbid: every key is a declared TaskSpec field (surface, mode, prompt, rubric, judge_inputs, permission_choice). Add the comment: "LIVE-ONLY (FAKE_TURN emits no permission.updated). permission_choice=d makes the consumer reply Deny; in automated/stub runs this scenario drains to idle with saw_permission_gate=false."

    (5) In tests/eval/test_sdk.py: keep `test_permission_gate_live` as `@pytest.mark.skip(reason="live-only ...")` and extend its docstring/reason to enumerate: Allow proven on sdk:python/ts/go/rust (plan 06 scenarios 01-04), Deny proven on sdk:ts (scenario 05); all require `--auth codex`. Add a small real test `test_permission_choice_field` (NOT skipped) asserting `TaskSpec(prompt="x", mode="plan", rubric="r", surface="sdk:ts", permission_choice="d").permission_choice == "d"` and that it defaults to None — this proves the field wiring hermetically without needing live creds.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_sdk.py::test_permission_choice_field -x -q 2>&1 | tail -6</automated>
  </verify>
  <acceptance_criteria>
    - The suite now loads 5 scenarios: `.venv/bin/python -c "from pathlib import Path; from voss.eval.suite import load_suite; t=load_suite(Path('tests/eval/sdk'), suite='sdk'); print(len(t))"` prints 5; the Deny scenario has surface=="sdk:ts" and permission_choice=="d".
    - `permission_choice` is an optional TaskSpec field defaulting None: `test_permission_choice_field` passes; `grep -c "permission_choice" voss/eval/suite.py` >= 1.
    - `_drive_sdk_client` forwards it: `grep -c "VOSS_PERMISSION_CHOICE" voss/eval/runner.py` >= 1.
    - The ts consumer choice is env-driven: `grep -c "VOSS_PERMISSION_CHOICE" tests/eval/sdk/consumers/ts/consumer.js` >= 1; `node --check tests/eval/sdk/consumers/ts/consumer.js` exits 0; `grep -c "VossLauncher" tests/eval/sdk/consumers/ts/consumer.js` == 0 (pitfall still held).
    - The Deny task.toml exists + validates: `test -f tests/eval/sdk/05-ts-permission-deny/task.toml`; `grep -c "deny\|Deny\|degrade\|without hang" tests/eval/sdk/05-ts-permission-deny/task.toml` >= 1 (degrade-without-hang rubric).
    - No new JSONL row key: `git diff tests/eval/test_voss_eval_stub.py` shows REQUIRED_FIELDS unchanged (permission_choice is a TaskSpec field, not a row key).
    - The permission live tests remain skipped: `.venv/bin/python -m pytest tests/eval/test_sdk.py -q -k "permission_gate_live" 2>&1 | grep -c "skipped"` >= 1 (live-only; not run in CI).
    - `.venv/bin/python -m pytest tests/eval/test_sdk.py -q 2>&1 | tail -3` shows no new failures.
  </acceptance_criteria>
  <done>A live-only ts Deny variant exists (degrade-without-hang) driven by permission_choice=d forwarded through _drive_sdk_client; the permission live scenarios are skip-marked in automated runs; suite loads 5 scenarios; permission_choice is the only new TaskSpec field and is not a JSONL key.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 2: Operator live proof run on codex auth + record E4-PROOF.md</name>
  <files>.planning/phases/E4-sdk-proof/E4-PROOF.md (the operator records the proof here; the live run also produces git-ignored .voss/eval/&lt;ts&gt;/ artifacts — no other tracked repo files modified)</files>
  <read_first>
    - .planning/phases/E4-sdk-proof/E4-CONTEXT.md (D-08 proof criteria — every surface >=1 scenario, >=80% gate_pass, 0 capped, permission scenario among passers, sub-burn surfaced upfront)
    - .planning/phases/E3-surface-e2e/E3-04-PLAN.md (the direct analog — E3's live-proof checkpoint Task 3; operator creds, artifact recording, the run-header sub-burn confirmation)
    - tests/eval/sdk/ (the 5 scenarios authored in plans 06-07 — what the live run exercises: 01 python, 02 ts-allow, 03 go-allow, 04 rust-allow, 05 ts-deny)
    - voss/harness/auth.py (the codex subscription path; quirks — no temperature/max_tokens, gpt-5.x only — must not regress)
  </read_first>
  <action>Pause for the operator to run the live SDK suite on codex subscription auth: `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite sdk --auth codex -k 1`. The operator confirms the run header prints "5 tasks · max N turns/task" (sub-burn exposure) BEFORE the first model call, then inspects the printed `.voss/eval/&lt;ts&gt;/runs.jsonl` + `summary.md` for the D-08 criteria: every surface (sdk:python/ts/go/rust) has >=1 row; overall gate_pass >= 80% across the 5 rows; 0 capped rows; the permission scenarios are among the passers (ts Allow reaches a final after replying Allow; ts Deny degrades to a final WITHOUT hanging — no timeout/cap); the Allow round-trip is observable per client (saw_permission_gate=true on the gated ts/go/rust Allow scenarios; sdk:python proves the in-process public-API turn). No tracked repo files are written by the run; artifacts land under git-ignored .voss/. The operator records the proof in `.planning/phases/E4-sdk-proof/E4-PROOF.md` (exact command, run dir path, per-surface gate_pass table, capped count, permission verdicts, total sub-burn) and references it from the phase SUMMARY. This is the E4 phase ship gate (EVSDK-08, D-08). See &lt;how-to-verify&gt; for the exact steps; if any criterion fails, do NOT approve — report the failing scenario so a gap-closure plan can address it.</action>
  <verify>Human types "approved" after confirming >=80% gate_pass, 0 capped, every surface present, the permission-Allow scenarios passed, and the Deny scenario degraded without a hang; the run dir path + per-surface gate_pass + permission verdicts recorded in E4-PROOF.md and referenced from the SUMMARY.</verify>
  <done>Documented live run on codex auth meets D-08 (>=1 scenario/surface, >=80% gate_pass, 0 capped, permission scenario among passers, Deny no-hang); E4-PROOF.md records the command + run dir + per-surface gate_pass + verdicts + sub-burn; explicit operator approval logged.</done>
  <what-built>
    The full E4 SDK suite (4 Allow scenarios across sdk:python/ts/go/rust + 1 ts Deny variant) driven through the single E1 hybrid substrate. Stub-mode plumbing for all four consumers is green in CI; the permission-gate Allow/Deny round-trip and the gate_pass/cost figures can only be produced LIVE on codex subscription auth (FAKE_TURN emits no permission.updated). This checkpoint is the documented live proof (D-08) — it requires operator-supplied codex creds and cannot run unattended.
  </what-built>
  <how-to-verify>
    1. Ensure codex subscription auth is available to the operator shell (the codex path in voss/harness/auth.py; `voss /login` or the env the operator uses for codex). The run is subscription-gated + turn-capped (no runaway spend).
    2. Run the full SDK suite live (surface the total sub-burn from the run header first):
         `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite sdk --auth codex -k 1`
       (the header prints "5 tasks · max N turns/task" — confirm the sub-burn is acceptable before letting it complete; ~5 scenarios x N turns).
    3. After completion, open the run dir `.voss/eval/<ts>/` and inspect `runs.jsonl` + `summary.md`. Confirm the D-08 criteria:
         - every surface present: rows include surface in {sdk:python, sdk:ts, sdk:go, sdk:rust} (>=1 scenario each).
         - overall gate_pass >= 80% across the 5 rows.
         - 0 capped rows (no row has capped=true).
         - the permission-gate scenario(s) are among the passers: the ts Allow scenario reaches a final after replying Allow; the ts Deny scenario degrades to a final WITHOUT hanging (no timeout/cap).
         - confirm the Allow round-trip is observable per client (the consumer JSON / summary shows saw_permission_gate=true for the Allow scenarios on ts/go/rust where a gated tool call fired; sdk:python proves the in-process public-API turn).
    4. If any criterion fails (gate_pass < 80%, a capped row, a hung Deny, a missing surface), DO NOT approve — report which scenario + verdict failed so a gap-closure plan can address it.
    5. Record the proof in `.planning/phases/E4-sdk-proof/E4-PROOF.md`: the exact command, the run dir path, a per-surface gate_pass table, the capped count (must be 0), the permission verdicts (Allow reached-final per client; Deny degraded-without-hang), and the total sub-burn (scenarios x turns + any cost figure from summary.md). Reference E4-PROOF.md from the phase SUMMARY.
  </how-to-verify>
  <resume-signal>Type "approved" (paste the run dir path + per-surface gate_pass + capped=0 + permission verdicts), or describe which scenario/verdict failed.</resume-signal>
  <acceptance_criteria>
    - The operator ran `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite sdk --auth codex` and confirmed the run-header sub-burn before completion.
    - D-08 met: >=1 scenario per surface (sdk:python/ts/go/rust), overall gate_pass >= 80%, 0 capped rows, the permission scenario(s) among the passers (ts Allow reached final; ts Deny degraded without hang).
    - E4-PROOF.md records the exact command, run dir path, per-surface gate_pass table, capped=0, permission verdicts, and total sub-burn; referenced from the phase SUMMARY.
    - Explicit "approved" recorded; if any criterion failed, the failing scenario is reported instead (no approval) so a gap-closure plan can address it.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator codex creds -> live model run | subscription-gated; turn-capped (0 capped is a pass criterion) so no runaway spend |
| consumer permission reply (Allow/Deny) -> live serve | the choice crosses via VOSS_PERMISSION_CHOICE env -> replyPermission over the loopback bearer-token plane |
| live run artifacts -> E4-PROOF.md | the proof record is operator-reviewed; the human checkpoint blocks phase close until D-08 criteria are met |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E4-21 | Denial | runaway live spend on the proof run | mitigate | run is turn-capped (get_eval_max_turns); 0 capped rows is a D-08 pass criterion; the operator confirms sub-burn from the run header before completing |
| T-E4-22 | Denial | Deny path hangs the turn (infinite wait on a denied gate) | mitigate | the Deny scenario rubric REQUIRES degrade-without-hang; a hung/capped Deny FAILS the checkpoint (no approval) |
| T-E4-23 | Repudiation | unverifiable proof claim | mitigate | E4-PROOF.md records the exact command + run dir + per-surface gate_pass + verdicts; the blocking-human checkpoint requires the operator to paste them |
| T-E4-24 | Information Disclosure | codex creds leaking into the proof record | accept | E4-PROOF.md records run metadata (gate_pass, paths, verdicts), never creds; auth lives in the operator shell / auth.py, not in the artifact |
| T-E4-25 | Tampering | permission_choice injecting an unexpected reply value | mitigate | replyPermission only accepts a/A/d/y/n; an out-of-range choice is rejected by the SDK; permission_choice is operator-authored in a committed task.toml |
| T-E4-SC | Tampering | npm/pip/cargo installs | accept | E4 introduces zero new packages; this plan adds a toml scenario + an optional TaskSpec field + a consumer env tweak + a proof doc; no install task |
</threat_model>

<verification>
- The SDK suite loads 5 scenarios (4 Allow + 1 ts Deny); the ts consumer drives Allow/Deny via VOSS_PERMISSION_CHOICE forwarded from permission_choice
- Permission live scenarios SKIP in automated runs (FAKE_TURN emits no permission.updated); CI stays green; permission_choice field-wiring proven hermetically
- OPERATOR (blocking-human): one live codex run, >=1 scenario/surface, >=80% gate_pass, 0 capped, permission scenario among passers, Deny degrades without hang
- E4-PROOF.md records the command, run dir, per-surface gate_pass, capped=0, permission verdicts, total sub-burn; referenced from the phase SUMMARY
</verification>

<success_criteria>
- EVSDK-07: permission-gate live scenario per client — Allow reaches final (sdk:python/ts/go/rust), ts Deny degrades without hang; live-only (skipped in CI)
- EVSDK-08: one documented live codex proof run meeting all D-08 criteria, gated by a blocking-human operator checkpoint, recorded in E4-PROOF.md
- turn-capped, subscription-gated, no runaway spend (0 capped is a pass criterion); permission_choice is the only new TaskSpec field (not a JSONL key)
</success_criteria>

<output>
Create `.planning/phases/E4-sdk-proof/E4-07-SUMMARY.md` when done
</output>
