---
phase: V10-voss-language-as-coordination-spec
plan: 05
type: execute
wave: 5
depends_on:
  - V10-04
files_modified:
  - samples/team-orchestration.voss
  - samples/reviewer-split.voss
  - samples/audit-gates.voss
autonomous: true
requirements:
  - VLANG-08
  - VLANG-VERIFY
  - VLANG-GUARD

must_haves:
  truths:
    - "Three org-loop example .voss files exist and pass voss check clean"
    - "An end-to-end team{} file passes voss team check AND voss team run completes on the stub"
    - "voss ast/check/compile/run still work; raw-Python parity tests stay green"
    - "git diff shows zero field changes on RunRecord, SessionRecord, BudgetScope"
    - "The V10 diff adds only coordination grammar (no general-purpose language features)"
  artifacts:
    - path: "samples/team-orchestration.voss"
      provides: "team orchestration org-loop example using V10 blocks"
      contains: "team"
    - path: "samples/reviewer-split.voss"
      provides: "reviewer-split example (gate ... require independent_review)"
      contains: "require independent_review"
    - path: "samples/audit-gates.voss"
      provides: "audit-gates example (gate done with evidence_refs)"
      contains: "require evidence_refs"
  key_links:
    - from: "samples/*.voss"
      to: "voss check"
      via: "CliRunner invoke check, exit 0"
      pattern: "team"
    - from: "tests/harness/test_e2e_team_run.py fixture .voss/team.voss"
      to: "voss.harness.cli.team_run_cmd"
      via: "team run on stub completes (run complete + sign-off)"
      pattern: "team_run_cmd"
---

<objective>
Ship the VLANG-08 deliverables and prove the verify/guard requirements: three runnable org-loop `samples/*.voss` examples (team orchestration, reviewer split, audit gates) that pass `voss check` clean, plus an end-to-end `team{}` file that passes `voss team check` and drives a complete `voss team run` on the stub provider. Then close the phase by confirming the verify requirement (ast/check/compile/run + raw-Python parity green) and the two guards: frozen `RunRecord`/`SessionRecord`/`BudgetScope` show zero field changes (git diff), and the V10 grammar diff added only coordination blocks.

Purpose: Close VLANG-08, VLANG-VERIFY, VLANG-GUARD. This is the integration + acceptance wave — it turns the remaining V10-01 scaffolds (Task 3: org-loop examples + e2e) GREEN and runs the SPEC's git-diff acceptance check.
Output: three sample files; V10-01 org-loop + e2e scaffolds GREEN; frozen-schema + coordination-focus guards verified.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md

<interfaces>
<!-- Example + e2e surfaces, verified against the live codebase. -->

Sample location: samples/ (existing: classify.voss, research.voss, support.voss). New files go here.

End-to-end team file: <cwd>/.voss/team.voss — voss team run reads it (harness/cli.py:4046).
  voss team check  → harness/cli.py:3888 (parse → compile_team → JSON; semantic validation path).
  voss team run "<goal>" --cwd <dir> → harness/cli.py:4021; ENDS with click.prompt sign-off (CliRunner needs input="approve\n").
  Stub stack auto-activates under VOSS_HERMETIC=1 (RESEARCH lines 439-446).

voss check (voss/cli.py:341): parse + analyze ONLY. LOCKED interpretation (RESEARCH Q1):
  voss check = parse-only validation (must NOT crash on the new blocks; exit 0 on a well-formed team file).
  voss team check = the team-semantic validation verb (runs compile_team).

Frozen records (git-diff acceptance — must show ZERO field changes):
  RunRecord, SessionRecord → voss/harness/session.py (lines 119, 158)
  BudgetScope → voss_runtime/budget.py

Canonical team{} skeleton with all V10 blocks: V10-RESEARCH.md lines 574-614.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author three org-loop sample .voss files (turn org-loop scaffold green)</name>
  <read_first>
    - samples/classify.voss (header-comment convention + file shape)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (canonical team Engineering {} skeleton lines 574-614)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (example file guidance lines 505-517)
    - tests/voss/test_org_loop_examples.py (the RED scaffold — confirm the exact three filenames it parametrizes)
    - voss/grammar.lark (the now-shipped principles_block/gate_block/memory_block/roster_block/ceiling_block rules — author the samples to parse against the real grammar)
  </read_first>
  <action>
    Create three example files under samples/, each a valid `team{}` using the V10 grammar (ceiling + the new principles/gate/memory blocks + roster), each with a one-line `#` header comment naming the scenario:
    - `samples/team-orchestration.voss` — a multi-role roster (e.g. backend + frontend + reviewer) demonstrating team orchestration, with a `gate done { require tests_passed; require independent_review; require evidence_refs }`, a `principles{}` block, and a `memory{}` block.
    - `samples/reviewer-split.voss` — emphasizes the reviewer-split pattern: a roster with distinct reviewer roles and a `gate done { ... require independent_review ... }` (NO separate review{} block — that is deferred; the reviewer requirement is expressed via the gate, per SPEC).
    - `samples/audit-gates.voss` — emphasizes audit gates: a `gate done { require tests_passed; require independent_review; require evidence_refs }` with a `memory{}` block declaring decisions/sessions/semantic paths.
    Each file must parse AND pass `voss check` (parse-only — LOCKED interpretation) cleanly. Author against the real shipped grammar (read grammar.lark first); do not invent grammar the parser does not accept. Keep them coordination-only — no fn/agent/prompt general-purpose constructs (VLANG-GUARD).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_org_loop_examples.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Three files exist: samples/team-orchestration.voss, samples/reviewer-split.voss, samples/audit-gates.voss
    - samples/reviewer-split.voss contains `require independent_review`; samples/audit-gates.voss contains `require evidence_refs`
    - `voss check samples/team-orchestration.voss` exits 0 (and likewise the other two): `.venv/bin/python -m voss check samples/team-orchestration.voss && .venv/bin/python -m voss check samples/reviewer-split.voss && .venv/bin/python -m voss check samples/audit-gates.voss`
    - None of the three contains a `fn`/`agent`/`prompt`/`class` general-purpose declaration: `grep -lE '^\s*(fn|agent|prompt|class)\b' samples/team-orchestration.voss samples/reviewer-split.voss samples/audit-gates.voss` returns nothing
    - The V10-01 org-loop scaffold PASSES: the pytest command above exits 0
  </acceptance_criteria>
  <done>Three coordination-only org-loop samples authored; all pass voss check; org-loop scaffold GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: End-to-end team run on the stub (turn e2e scaffold green)</name>
  <read_first>
    - tests/harness/test_e2e_team_run.py (the RED scaffold from V10-01 — it writes .voss/team.voss in tmp_path and invokes team_run_cmd with input="approve\n")
    - voss/harness/cli.py (team_run_cmd lines 4021-4138 — confirm the run-complete + sign-off output strings; team_check_cmd lines 3888-3941)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (stub provider activation lines 439-446; e2e binding to voss team run lines 400-404, A1 lines 717)
  </read_first>
  <action>
    Make the V10-01 e2e scaffold pass. The scaffold writes a `.voss/team.voss` fixture (team + ceiling + principles + gate done + memory + roster) into tmp_path, sets `VOSS_HERMETIC=1`, and invokes `team_run_cmd` via CliRunner with `input="approve\n"`, asserting exit 0 + "run complete" + "sign-off recorded: approve".
    Implementation work here is primarily: ensure the fixture `.voss/team.voss` content parses and compiles under the V10 grammar/compiler (built in V10-02/03/04) and is a valid input to `voss team run`. If the scaffold's embedded fixture content does not yet compile (e.g. a roster role missing a required field, or a block ordering the grammar rejects), adjust the FIXTURE content in the test to a minimal valid V10 team file (mirror the canonical skeleton from RESEARCH lines 574-614). Do NOT modify production `team_run_cmd` behavior — `voss team run` already composes the stub stack; this task only proves the V10-authored `.voss` file drives it.
    Also add a direct `voss team check` assertion in the same test (or a sibling test): invoke `team_check_cmd` on the same fixture via CliRunner and assert exit 0 — proving the end-to-end file passes the semantic-validation verb.
  </action>
  <verify>
    <automated>VOSS_HERMETIC=1 .venv/bin/python -m pytest tests/harness/test_e2e_team_run.py -q</automated>
  </verify>
  <acceptance_criteria>
    - The V10-01 e2e scaffold PASSES: the pytest command above exits 0
    - The test invokes team_run_cmd with input="approve\n" and asserts "run complete" + "sign-off recorded: approve" in output
    - A team check assertion exists proving the fixture passes the semantic verb (team_check_cmd exit 0 on the same .voss/team.voss)
    - No production change to voss/harness/cli.py team_run_cmd: `git diff --stat voss/harness/cli.py` shows no changes from this plan (only the test file + samples are this plan's files_modified; cli.py must not be edited here)
  </acceptance_criteria>
  <done>End-to-end .voss/team.voss drives a complete voss team run on the stub (approve sign-off) and passes voss team check; e2e scaffold GREEN; no cli.py edits.</done>
</task>

<task type="auto">
  <name>Task 3: Verify gate — parity green + frozen-schema git-diff guard + coordination-focus guard</name>
  <read_first>
    - voss/harness/session.py (RunRecord line 119, SessionRecord line 158 — the frozen field lists the git-diff guard protects)
    - voss_runtime/budget.py (BudgetScope — frozen field list)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md (acceptance criteria lines 90-98 — the 8 checks)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (parity test locations lines 408-422)
  </read_first>
  <action>
    Run and record the phase verify + guard checks (no production edits — this is a verification task; if a check fails, the fix belongs to the responsible earlier plan and execution must surface it, not paper over it):
    - Parity / verify (VLANG-VERIFY): run the raw-Python parity + CLI-verb suites and confirm green: `tests/harness/test_voss_loop_parity.py`, `tests/codegen/test_examples.py`, `tests/parser/test_team_grammar.py`, `tests/voss/test_team_compile.py`, `tests/voss/test_team_backcompat_regression.py`. Also smoke the four verbs on a new-block file: `voss ast`, `voss check`, `voss compile`, and confirm `voss run` is unaffected for an ordinary codegen `.voss` (the new blocks are coordination-only and not codegen targets).
    - Frozen-schema guard: run `git diff` (against the phase base commit) restricted to the frozen record files and assert ZERO field changes: `git diff -- voss/harness/session.py voss_runtime/budget.py` shows no change to the `RunRecord`/`SessionRecord`/`BudgetScope` field declarations. (Diff may legitimately be empty for these files entirely — V10 should not touch them.)
    - Coordination-focus guard (VLANG-GUARD): inspect the grammar diff and confirm the only new top-level/team-item rules are `principles_block`, `gate_block`, `memory_block` (plus their kv/require sub-rules) — no new general-purpose language rule (no new fn/expr/control-flow construct). `git diff -- voss/grammar.lark` adds only the three coordination blocks.
    Record the results (commands + pass/fail) in the SUMMARY. If any frozen-record field changed or a non-coordination grammar rule was added, FAIL the task and report which earlier plan must fix it.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_voss_loop_parity.py tests/codegen/test_examples.py tests/parser/test_team_grammar.py tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py -q && git diff -- voss/harness/session.py voss_runtime/budget.py | grep -E '^[+-]\s+(id|started_at|ended_at|goal|name|cwd|model|token_limit)' ; test $? -ne 0</automated>
  </verify>
  <acceptance_criteria>
    - Parity + CLI-verb suites green: the pytest portion of the verify command exits 0
    - `voss ast`/`voss check`/`voss compile` run on a new-block file without crashing; `voss run` behavior on ordinary codegen files is unchanged
    - Frozen-schema guard PASSES: `git diff -- voss/harness/session.py voss_runtime/budget.py` shows no field-line changes to RunRecord/SessionRecord/BudgetScope (the grep for changed field lines finds nothing → `test $? -ne 0` succeeds)
    - Coordination-focus guard PASSES: `git diff -- voss/grammar.lark` adds only principles_block/gate_block/memory_block (+ sub-rules) and the team_item/top_decl alternatives — no general-purpose rule added
    - All eight SPEC acceptance criteria (V10-SPEC.md lines 90-98) are confirmed met and recorded in the SUMMARY
  </acceptance_criteria>
  <done>Parity green; frozen RunRecord/SessionRecord/BudgetScope unchanged (git diff); grammar diff is coordination-only; all 8 SPEC acceptance criteria recorded as met.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test fixture `.voss/team.voss` → voss team run | A `.voss` team file authored under tmp_path drives the stub EM loop; the stub provider performs no real network/exec |
| `memory{}` declared paths in samples → compile | Sample files declare memory paths as config strings only; no file I/O on those paths |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V10-05-01 | Tampering | e2e test writing .voss/team.voss | accept | All e2e writes use pytest tmp_path; no repo-root `.voss/` write. VOSS_HERMETIC=1 forces the in-memory stub provider — no real provider call, no external side effect. |
| T-V10-05-02 | Elevation of Privilege | gate{}/memory{} declared in samples accidentally changing Done-gate enforcement | mitigate | The frozen-schema git-diff guard (Task 3) + the V10-03 informational-config design ensure the shipped board still uses its own default predicates; samples are config-only and cannot alter enforcement |
| T-V10-05-03 | DoS | team run unbounded loop on the stub | accept | `team_run_cmd` already bounds the EM loop via `--max-iterations` (default 50); the stub EM script terminates with a NoopOp — no unbounded run |
| T-V10-05-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs; samples are static `.voss` text and the e2e reuses the shipped stub stack. No new dependency. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/voss/test_org_loop_examples.py tests/harness/test_e2e_team_run.py -q` — green.
- Full phase gate: `.venv/bin/python -m pytest tests/parser/ tests/voss/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py tests/harness/test_voss_loop_parity.py tests/codegen/test_examples.py -q` — all green.
- `git diff -- voss/harness/session.py voss_runtime/budget.py` — no field changes (SPEC acceptance).
- `git diff -- voss/grammar.lark` — only the three coordination blocks added.
</verification>

<success_criteria>
- Three org-loop samples pass voss check; one end-to-end team file passes voss team check AND drives a complete voss team run on the stub.
- ast/check/compile/run work; raw-Python parity green.
- Frozen RunRecord/SessionRecord/BudgetScope unchanged; grammar diff coordination-only.
- All 8 SPEC acceptance criteria met.
</success_criteria>

<output>
Create `.planning/phases/V10-voss-language-as-coordination-spec/V10-05-SUMMARY.md` when done.
</output>
