---
phase: T6-slash-debt
plan: 03
type: execute
wave: 3
depends_on: [T6-02-grouped-help-and-cli-signpost]
files_modified:
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [SLASH-01, SLASH-03, SLASH-05, SLASH-06]
must_haves:
  truths:
    - "Each of /diff and /resume has at least one integration test exercising its happy path (ROADMAP T6 SC#1)"
    - "/discard is confirmed already covered by an existing happy-path test (D-02 git-tree, test-only, no code change)"
    - "The /why test proves rationale + the existing single confidence float render with NO provider call (ROADMAP T6 SC#2)"
    - "/resume tests confirm both arms of session_store.load resolution (id-prefix AND exact-name) resolve, and the cross-cwd path warns and stays in the current cwd, with the real session.py resolution order unchanged (D-03)"
    - "Every SLASH-01..07 has at least one passing happy-path integration test (SC#1 roll-up; this plan is the T6 validation contract / Nyquist substitute)"
  artifacts:
    - path: "tests/harness/test_repl_slash.py"
      provides: "SC#1 happy-path tests for /diff and /resume (id + name + cross-cwd), a D-07 /why SC#2 audit test, and a SLASH-01..07 coverage roll-up"
      contains: "def test_diff"
  key_links:
    - from: "tests/harness/test_repl_slash.py /resume test"
      to: "voss.harness.cli.session_store.load"
      via: "monkeypatch the loader; assert both resolution arms route through one load(target) call + cross-cwd warning; real session.py:222 OR predicate untouched"
      pattern: "session_store"
---

<objective>
Close the SC#1 per-slash integration-test gap and resolve D-07 + D-03. Add ≥1
happy-path test for the slashes not yet covered in `TestT6Behaviors`
(`/diff`, `/resume`), confirm `/discard` is already covered (D-02 git-tree —
test-only, no code change), and add an explicit D-07 audit test asserting the
current `_why` output already satisfies PRD §2.4 / Ticket 7 (rationale + single
`confidence:.2f` float + step why, NO provider call) — so the only `/why` work
in T6 is the test, with NO code delta. `/budget`, `/apply`,
`/cost --by-model`, `/discard` dry-run, and `/why` rationale/steps are already
covered (test_repl_slash.py:171-258) — audit-only per D-05.

Purpose: ROADMAP T6 SC#1 requires ≥1 integration test per PRD §2.4 slash
exercising the happy path; SC#2 requires `/why` to render confidence + rationale
with no provider call. This plan IS the T6 validation contract (the Nyquist
substitute, since research was intentionally skipped). Wave 3 because it edits
`tests/harness/test_repl_slash.py`, which T6-01 and T6-02 also edit
(file-ownership serialization).
Output: New test methods in `TestT6Behaviors`; D-07 + D-03 resolutions recorded
in the SUMMARY.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T6-slash-debt/T6-CONTEXT.md
@.planning/phases/T6-slash-debt/T6-01-SUMMARY.md
@.planning/phases/T6-slash-debt/T6-02-SUMMARY.md

<interfaces>
<!-- Extracted from codebase. No exploration required. -->

D-07 RESOLUTION (planner-determined — this task ASSERTS it, NO code change):
  PRD Ticket 7 (.vscode/voss_v_0_1_scope_lock.md:1213-1221) acceptance criteria:
    "last major decision can be explained"            → plan.rationale  ✓
    "explanation includes confidence if available"    → plan.confidence:.2f  ✓
    "explanation references tool outputs or plan constraints where possible"
                                                       → per-step step.why + open_question + final_when_done  ✓
  `ProbableValue` (.vscode/voss_v_0_1_scope_lock.md:712) is a RUNTIME-LAYER
  responsibility (the confidence-bearing type), NOT a PRD-mandated /why output
  format. PRD says confidence "if available"; the single float satisfies it.
  CONCLUSION: current _why output (cli.py:655-673) SUFFICES. T6 /why work =
  test-only, NO code delta.

_why renderer (voss/harness/cli.py:655-673), NO provider call — reads
  ctx.last_plan only:
    rationale: {plan.rationale}
    confidence: {plan.confidence:.2f}
    steps: enumerated {step.name} — {step.why}
    open question / final-when-done if present

/resume (voss/harness/cli.py:754-782) calls
  session_store.load(target, cwd=ctx.cwd) (cli.py:763); module alias is
  `from . import session as session_store` (cli.py:26) → monkeypatch target is
  `voss.harness.cli.session_store.load`. On resolved record.cwd != ctx.cwd it
  prints a warning to err (cli.py:767-772) and STAYS in ctx.cwd (D-03 — no
  rebind). Real resolution predicate (voss/harness/session.py:222, _scan_dir) is
  a SINGLE OR: `data.get("id","").startswith(target) OR data.get("name")==target`
  — NO id-first/name-second sequencing. load() raises FileNotFoundError on no
  match, ValueError on >1 ambiguous. THIS PLAN MUST NOT CHANGE THAT ORDER.

/diff (voss/harness/cli.py:675-702): `git diff` via subprocess.run with
  cwd=str(ctx.cwd), timeout=15; no-changes path echoes "  (no changes)".

/discard ALREADY covered: tests/harness/test_repl_slash.py:233-249
  (test_discard_dry_run_lists_files + test_discard_no_runs_is_no_op) — D-02
  git-tree semantics, test-only, NO code change in T6.

Handler-direct test pattern (tests/harness/test_repl_slash.py:128-258):
  reg = _build_slash_registry(); reg.lookup("/x").handler(fake_ctx, args, line)
  → assert on capsys.readouterr(). Reuse the `fake_ctx` SimpleNamespace fixture
  (post-T6-01 it carries an `iterations` key on the second run dict).

Registration-parity test to extend (tests/harness/test_repl_slash.py:118-125):
  test_t6_prd_slash_commands_registered asserts
  /diff /apply /discard /budget /resume /why register — add /cost.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: /diff happy-path test (SLASH-01) + D-07 /why SC#2 audit test (SLASH-06)</name>
  <files>tests/harness/test_repl_slash.py</files>
  <read_first>
    - tests/harness/test_repl_slash.py:128-258 (the `TestT6Behaviors` class, the `fake_ctx` fixture, the existing `test_why_renders_rationale_and_steps` at 171-179 and `test_discard_dry_run_lists_files` at 233-240 as the closest analogs)
    - voss/harness/cli.py:675-702 (`_diff` — `git diff` subprocess with timeout + stderr surfacing; no-changes path echoes "  (no changes)")
    - voss/harness/cli.py:655-673 (`_why` — rationale + `confidence:.2f` + step why, NO provider call; the D-07 subject)
  </read_first>
  <action>
    In `tests/harness/test_repl_slash.py` `TestT6Behaviors`, add a `/diff`
    happy-path test (SLASH-01). Use the lighter approach: monkeypatch
    `voss.harness.cli.subprocess.run` to return a fake `CompletedProcess`
    (returncode 0, stdout containing a diff body line, empty stderr), dispatch
    `reg.lookup("/diff").handler(fake_ctx, [], "/diff")`, and assert the fake
    diff body is echoed in `capsys.readouterr().out`; OR if a real `tmp_path`
    git repo is preferred, init it with one tracked file + an uncommitted
    modification and assert a hunk marker appears (mirror the existing
    handler-direct + capsys shape from the same class). Also add a D-07 AUDIT
    test for `/why` (SLASH-06, SC#2): dispatch `/why` against the existing
    `fake_ctx` plan and assert the output contains the rationale text AND the
    formatted single confidence float (`0.82`) AND a step `why` token, AND that
    NO provider/network call occurred — assert by construction (the test
    monkeypatches NOTHING provider-side and `_why` reads `ctx.last_plan` only).
    Add an in-test comment citing D-07: PRD Ticket 7
    (`.vscode/voss_v_0_1_scope_lock.md:1213-1221`) is satisfied by the existing
    single confidence float; `ProbableValue` (`:712`) is a runtime-layer type,
    NOT a `/why` output-format mandate → NO `/why` code delta. No fenced code in
    this action — copy the existing class's method shape.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_repl_slash.py -q -k "diff or why" 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tests/harness/test_repl_slash.py -q -k "diff or why"` exits 0.
    - `grep -nE "def test_diff" tests/harness/test_repl_slash.py` returns a match (the new /diff SLASH-01 happy-path test exists).
    - The new /why audit test asserts BOTH the confidence string `0.82` AND the rationale text appear in the output (SC#2: rendered with no provider call).
    - `grep -n "D-07" tests/harness/test_repl_slash.py` shows the audit comment citing PRD Ticket 7 + the `ProbableValue` runtime-type / no-code-delta conclusion.
    - No production file is modified by this plan: `git status --porcelain voss/ | grep -q . && exit 1 || true`.
  </acceptance_criteria>
  <done>`/diff` has a passing SLASH-01 SC#1 happy-path test; `/why` has a passing SLASH-06 SC#2 audit test with the D-07 no-code-delta conclusion documented in-test; no production code changed.</done>
</task>

<task type="auto">
  <name>Task 2: /resume SC#1 tests (SLASH-05, D-03) — id-prefix arm, exact-name arm, cross-cwd warning</name>
  <files>tests/harness/test_repl_slash.py</files>
  <read_first>
    - voss/harness/cli.py:754-782 (`_resume` — calls `session_store.load(target, cwd=ctx.cwd)`, swaps ctx.record/history/total_cost/last_plan/prior_context, cross-cwd warning at 767-772, stays in ctx.cwd)
    - voss/harness/cli.py:26 (`from . import session as session_store` — the monkeypatch target is `voss.harness.cli.session_store.load`)
    - voss/harness/session.py:213-261 (`_scan_dir` SINGLE OR predicate at :222 + `load` raise-on-missing/ambiguous — the resolution order this test MUST NOT change)
    - tests/harness/test_repl_slash.py:128-258 (`TestT6Behaviors` + `fake_ctx`; the handler-direct + capsys + monkeypatch shape)
  </read_first>
  <action>
    In `TestT6Behaviors`, add three `/resume` happy-path tests (SLASH-05) that
    monkeypatch `voss.harness.cli.session_store.load` (NOT real session.py —
    D-03 changes NO resolution order). (1) id-prefix arm: patch `load` to assert
    it received an id-shaped `target` and return a fake `(record, history)`
    whose `cwd` equals `fake_ctx.cwd`; dispatch `/resume <id>`; assert
    `capsys.readouterr().out` contains the resumed-session confirmation and that
    `fake_ctx.record` was swapped to the returned record. (2) exact-name arm:
    same with a name-shaped `target`, documenting (in-test comment) that
    `/resume <name>` and `/resume <id>` both route through the SAME single
    `load(target)` call, matching the real-code session.py:222 OR predicate with
    NO id-first/name-second ordering — the patched loader accepts either. (3)
    cross-cwd: patch `load` to return a record whose `cwd` differs from
    `fake_ctx.cwd`; dispatch `/resume`; assert `capsys.readouterr().err`
    contains the cross-cwd warning AND that the handler did NOT change
    `fake_ctx.cwd` (D-03 — stays in current cwd, points to `voss resume`). No
    fenced code in this action — reuse the class's handler-direct + capsys +
    monkeypatch shape.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_repl_slash.py -q -k "resume" 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tests/harness/test_repl_slash.py -q -k "resume"` exits 0 and collects at least 3 resume tests.
    - One test patches `session_store.load` with an id-shaped target and asserts `fake_ctx.record` is swapped to the returned record.
    - One test exercises a name-shaped target through the same `load(target)` call with an in-test comment documenting the session.py:222 OR has no id-first/name-second ordering.
    - One test asserts the cross-cwd path writes the warning to `capsys.readouterr().err` AND `fake_ctx.cwd` is unchanged after dispatch.
    - `grep -n "session_store" tests/harness/test_repl_slash.py` confirms the monkeypatch targets `voss.harness.cli.session_store.load` (real session.py resolution untouched).
    - No production file modified: `git status --porcelain voss/ | grep -q . && exit 1 || true`.
  </acceptance_criteria>
  <done>`/resume` has three passing SLASH-05 SC#1 tests (id arm, name arm, cross-cwd warning) all routing through a monkeypatched `session_store.load`; real session.py:222 resolution order unchanged (D-03); no production code touched.</done>
</task>

<task type="auto">
  <name>Task 3: SLASH-01..07 coverage roll-up + registration-parity extension + full-suite green gate</name>
  <files>tests/harness/test_repl_slash.py</files>
  <read_first>
    - tests/harness/test_repl_slash.py (full file — confirm every SLASH-01..07 happy path now has ≥1 test: /diff /apply /discard /budget /resume /why /cost --by-model + --by-tool)
    - tests/harness/test_repl_slash.py:118-125 (`test_t6_prd_slash_commands_registered` — the registration-parity test to extend with `/cost`)
    - .planning/phases/T6-slash-debt/T6-01-SUMMARY.md (confirms the rewritten `--by-tool` approximation test exists from Plan 01) and T6-02-SUMMARY.md (confirms grouped-help test from Plan 02)
  </read_first>
  <action>
    Audit `tests/harness/test_repl_slash.py` and confirm SLASH-01..07 each have
    ≥1 happy-path test: SLASH-01 `/diff` (Task 1), SLASH-02 `/apply`
    (`test_apply_explains_v01_semantics`, existing), SLASH-03 `/discard`
    (`test_discard_dry_run_lists_files` + `test_discard_no_runs_is_no_op`,
    existing — D-02 git-tree, test-only, NO code change confirmed), SLASH-04
    `/budget` (`test_budget_set_and_show`, existing), SLASH-05 `/resume`
    (Task 2), SLASH-06 `/why` (`test_why_renders_rationale_and_steps` + Task 1
    D-07 audit), SLASH-07 `/cost` (`test_cost_by_model_groups_by_session_model`
    + the rewritten `--by-tool` approximation test from Plan 01). If any
    SLASH-NN lacks a happy-path test, add the minimal one mirroring existing
    class methods. Extend `test_t6_prd_slash_commands_registered` (lines
    118-125) so its asserted tuple ALSO includes `/cost` alongside the existing
    `/diff /apply /discard /budget /resume /why`. Run the full slash test file
    and confirm green; if cheap, also run a broader `pytest -q` smoke over
    `tests/harness/`. No fenced code in this action.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_repl_slash.py -q 2>&1 | tail -3 && python -m pytest tests/harness/ -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tests/harness/test_repl_slash.py -q` exits 0 (entire file green).
    - `grep -nE "/diff|/apply|/discard|/budget|/resume|/why|/cost" tests/harness/test_repl_slash.py` shows a happy-path test referencing each of the seven SLASH targets.
    - `test_t6_prd_slash_commands_registered` asserts `/cost` is registered (`grep -n '"/cost"' tests/harness/test_repl_slash.py` shows it inside that test's asserted tuple).
    - `python -m pytest tests/harness/ -q` exits 0 (no regression in the broader harness test package).
    - No production file modified by this plan: `git status --porcelain voss/ | grep -q . && exit 1 || true`.
  </acceptance_criteria>
  <done>Every SLASH-01..07 has ≥1 passing happy-path integration test; the registration-parity test covers `/cost`; the full harness test package is green; no production code touched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test harness → handlers | Tests dispatch handlers directly with a synthetic `fake_ctx`; no untrusted external input |
| Monkeypatched `session_store.load` | The `/resume` tests substitute the loader; real path/identifier resolution in session.py is NOT exercised or modified |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T6-05 | Tampering | `/resume <id\|name>` user-supplied target → `session_store.load` | accept | Production resolution (`_scan_dir`, session.py:213-224) is a read-only JSON glob over `.voss/sessions` with `id.startswith` / `name ==` matching — no path-traversal sink, no shell. This plan only TESTS it via monkeypatch; resolution order is unchanged (D-03). |
| T-T6-06 | Denial of Service | `/diff` test git subprocess | accept | `_diff` already wraps `subprocess.run` with a 15s timeout + a fixed arg list (no `shell=True`); the test either monkeypatches `subprocess.run` or exercises that bounded path in a throwaway `tmp_path` repo. No injection surface (args are a fixed list). |
| T-T6-SC | Tampering | npm/pip/cargo installs | mitigate | No package installs in this plan (test-only, zero new deps per D-08). N/A — no slopcheck checkpoint required; no `[ASSUMED]`/`[SUS]` packages introduced. |

No `high`-severity threat. ASVS L1: this plan modifies only the test file —
no production surface, input validation, auth, or injection sink is added or
changed.
</threat_model>

<verification>
- `python -m pytest tests/harness/test_repl_slash.py -q` exits 0.
- `python -m pytest tests/harness/ -q` exits 0 (no broader regression).
- Every SLASH-01..07 has ≥1 happy-path test (SC#1 satisfied — this plan is the T6 validation contract / Nyquist substitute).
- D-07 resolution (current `_why` suffices, no code delta) + D-03 resolution (no `/resume` resolution-order change) recorded in the SUMMARY.
- `git status --porcelain voss/` is empty (no production file touched by this plan).
</verification>

<success_criteria>
- ROADMAP T6 SC#1: each PRD §2.4 slash registered in `_build_slash_registry` has ≥1 integration test exercising the happy path (`/diff` + `/resume` added here; `/discard` confirmed already covered; the rest covered by Plans 01-02 + pre-existing tests).
- ROADMAP T6 SC#2: `/why` renders confidence + rationale from the most recent Plan without a provider call (asserted by the D-07 audit test).
- D-03 honored: `/resume` resolution order unchanged; cross-cwd warns and stays in the current cwd.
</success_criteria>

<output>
Create `.planning/phases/T6-slash-debt/T6-03-SUMMARY.md` when done. The SUMMARY
MUST record verbatim: (1) the D-07 resolution — PRD Ticket 7 is satisfied by the
existing `_why` single-confidence-float output; `ProbableValue` is a
runtime-layer type, not a `/why` output-format mandate; T6 made NO `/why` code
change; (2) the D-03 resolution — `/resume` resolution order (session.py:222
single OR predicate) was NOT changed; only tests were added; (3) the
SLASH-01..07 coverage roll-up table showing the test backing each requirement.
</output>
