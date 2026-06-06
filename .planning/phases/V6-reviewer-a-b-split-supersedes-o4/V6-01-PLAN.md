---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/harness/board/test_session_tree_additive.py
  - tests/harness/board/test_verdict.py
  - tests/harness/board/test_two_source_gate.py
  - tests/harness/board/test_domain_inferred.py
  - tests/harness/board/test_review_sidecar.py
  - tests/harness/board/test_review_cli.py
autonomous: true
requirements: [VREV-03, VREV-04, VREV-06, VREV-07, VREV-09, VREV-10, VREV-05]
must_haves:
  truths:
    - "The board test baseline is green (no pre-existing red) before V6 implementation begins"
    - "Five RED test files exist and fail (or xfail) for unimplemented V6 behavior, pinning the target contracts"
    - "The 6-field verdict invariant test is updated to expect 7 fields (domain_inferred)"
  artifacts:
    - path: "tests/harness/board/test_two_source_gate.py"
      provides: "RED scaffolds for VREV-03/04/07 (two-source gate, B-block, board slot back-compat)"
      contains: "class TestBoardSlotBackCompat"
    - path: "tests/harness/board/test_domain_inferred.py"
      provides: "RED scaffolds for VREV-06 (domain_inferred field + B populates)"
      contains: "domain_inferred"
    - path: "tests/harness/board/test_review_sidecar.py"
      provides: "RED scaffolds for VREV-09 (.review.json persistence)"
      contains: "review.json"
    - path: "tests/harness/board/test_review_cli.py"
      provides: "RED scaffolds for VREV-10 (voss review CLI)"
      contains: "review_cmd"
  key_links:
    - from: "tests/harness/board/test_verdict.py"
      to: "voss/harness/board/verdict.py"
      via: "fields(ReviewerVerdict) field-name set assertion"
      pattern: "domain_inferred"
---

<objective>
Establish a green baseline and lay down the RED test scaffolds that pin every V6 target contract before any implementation lands. This is the Wave 0 prerequisite: fix the single pre-existing failing board test, update the 6-field verdict invariant to 7 fields, and create the five new test files (two-source gate, domain_inferred, review sidecar, review CLI) as failing-but-importable scaffolds.

Purpose: Nyquist compliance — every V6 requirement gets an automated verification target that exists and fails before the feature is built. Without this, downstream waves have no RED→GREEN signal.
Output: 1 fixed test, 1 updated test, 4 new RED test files.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-SPEC.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-CONTEXT.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-PATTERNS.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-VALIDATION.md

<interfaces>
<!-- Target contracts the RED scaffolds assert against. Sourced from V6-RESEARCH.md + V6-PATTERNS.md. -->
<!-- These do NOT exist yet — the scaffolds are RED until later waves implement them. -->

Current ReviewerVerdict (voss/harness/board/verdict.py) — 6 fields, target adds 7th:
  conf, source, tier, verdict, notes, evidence_refs  (+ domain_inferred: Literal["code","ai","docs","unknown"] = "unknown")

Target Board construction (later wave):
  Board.from_team_config(team, recorder=..., reviewer_a=stub_a, reviewer_b=stub_b, cwd=...)
  Board.from_team_config(team, recorder=..., reviewer=stub, cwd=...)  # legacy alias → both slots

Target sidecar: .voss/sessions/<root_id>/<node_id>.review.json (0o600), keys: a_verification, b_verdict, final_outcome

Target CLI: review_cmd in voss.harness.cli — `voss review [run_id]`; unknown run → exit != 0 + stderr "unknown run_id"

DeterministicReviewerStub(conf=..., verdict="pass"|"fail"|"block", source=..., tier=...) — voss/harness/board/stub.py
Test fixtures: build_test_team() + tmp_recorder from tests/harness/board/conftest.py
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix pre-existing red baseline (EXIT_REASONS superset)</name>
  <read_first>
    - tests/harness/board/test_session_tree_additive.py (the failing TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3)
    - V6-PATTERNS.md "Pre-existing Test Fix (Wave 0 prerequisite)" section (exact before/after)
    - V6-RESEARCH.md "Pre-existing Failure to Fix in Wave 0"
  </read_first>
  <action>
    In `tests/harness/board/test_session_tree_additive.py`, update `TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3`: the expected set currently omits `"killed"` (added post-O3 by O5 for the EM kill-flow). Add `"killed"` to the asserted expected set so it matches the live `EXIT_REASONS`. One-line change to the expected-set literal only — do NOT touch any production module. This is a pre-existing regression unrelated to V6, fixed here to unblock the green baseline.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3 -x</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3 -x` exits 0
    - The expected set in that test contains the literal `"killed"`
    - No file under `voss/` is modified by this task
  </acceptance_criteria>
  <done>The previously-failing exit-reasons superset test passes; the board baseline has 0 red from pre-existing causes.</done>
</task>

<task type="auto">
  <name>Task 2: Update verdict invariant 6→7 fields + create domain_inferred RED scaffold</name>
  <read_first>
    - tests/harness/board/test_verdict.py (the `test_exactly_6_fields` invariant at L44-46)
    - voss/harness/board/verdict.py (current 6-field ReviewerVerdict, frozen+slots)
    - V6-PATTERNS.md "test_domain_inferred.py" section (exact scaffold pattern + 7-field set)
    - tests/harness/board/test_reviewer_b.py (FakeReviewerBProvider pattern for B-populates test)
  </read_first>
  <action>
    Two edits:
    (a) In `tests/harness/board/test_verdict.py`, update `test_exactly_6_fields` (per V6-CONTEXT D-08 — the one intended scoped edit to the frozen-field contract): change the asserted field-name set from `{"conf","source","tier","verdict","notes","evidence_refs"}` to include `"domain_inferred"` (7 names). Rename the test to `test_exactly_7_fields` if the surrounding suite style favors descriptive names; otherwise keep the name and update only the set. This test will go RED now and GREEN once V6-02 adds the field.
    (b) Create `tests/harness/board/test_domain_inferred.py` (VREV-06) with a `TestDomainInferred` class asserting: (1) `ReviewerVerdict(...)` keyword-constructed without `domain_inferred` defaults to `"unknown"`; (2) `fields(ReviewerVerdict)` name-set equals the 7-name set; (3) a B-populated path (via the `FakeReviewerBProvider` analog from `test_reviewer_b.py`) yields a verdict whose `domain_inferred` is clamped to the allowed set `{code,ai,docs,unknown}`. Use keyword `ReviewerVerdict` construction throughout (matches every existing call site).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_domain_inferred.py tests/harness/board/test_verdict.py -x 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/board/test_domain_inferred.py` exists and imports cleanly (collection succeeds, no ImportError)
    - `test_verdict.py` asserts a 7-name field set including `"domain_inferred"`
    - Both files are RED against current code (field does not yet exist) — RED is the expected Wave 0 state; the pytest run reports failures, NOT collection errors
    - `grep -c "domain_inferred" tests/harness/board/test_domain_inferred.py` ≥ 3
  </acceptance_criteria>
  <done>The 7-field invariant is pinned in test_verdict.py and test_domain_inferred.py; both fail against current 6-field code (RED), with no import/collection errors.</done>
</task>

<task type="auto">
  <name>Task 3: Create RED scaffolds for two-source gate, sidecar, and CLI</name>
  <read_first>
    - V6-PATTERNS.md sections "test_two_source_gate.py", "test_review_sidecar.py", "test_review_cli.py" (exact fixture + assertion patterns)
    - tests/harness/board/conftest.py (build_test_team, tmp_recorder fixtures)
    - tests/harness/board/test_stub_full_lifecycle.py (Backlog→Done drive pattern, artifact attach via dataclasses.replace)
    - tests/harness/board/test_critic_loop.py (block verdict + Blocked-column assertion pattern)
    - voss/harness/board/stub.py (DeterministicReviewerStub constructor signature)
  </read_first>
  <action>
    Create three RED test files mirroring the V6-PATTERNS.md scaffolds:
    (a) `tests/harness/board/test_two_source_gate.py` (VREV-03/04/07) with classes: `TestBoardSlotBackCompat` (legacy `reviewer=stub` sets both `board._reviewer_a` and `board._reviewer_b` to the stub), `TestTwoSourceGate` (A-fail refuses Done; B-fail refuses Done; both-pass → Done), and `TestBBlockAtGate` (a B `block` verdict at the Done gate moves the card to `column == "Blocked"` with terminal `exit_reason == "max-iter"`). Use two-stub construction `reviewer_a=stub_a, reviewer_b=stub_b` and the legacy-alias construction. Use `build_test_team()` + `tmp_recorder`, `dataclasses.replace(card, artifact=...)` + `board._cards = [...]` to attach a clean artifact before InReview.
    (b) `tests/harness/board/test_review_sidecar.py` (VREV-09): drive a card Backlog→Done with passing A+B stubs, then assert `.voss/sessions/<root_id>/<node_id>.review.json` exists, has mode `0o600`, and its JSON has keys `a_verification`, `b_verdict`, `final_outcome`. Resolve `root_id` via `manager.get_node(card.node_id).root_id`.
    (c) `tests/harness/board/test_review_cli.py` (VREV-10) using `click.testing.CliRunner` against `review_cmd` imported from `voss.harness.cli`: `test_unknown_run_id_exits_nonzero` (exit != 0, stderr contains `unknown run_id`), `test_no_sessions_exits_nonzero`, and `test_existing_run_exits_zero` (write a fake `<node>.review.json` sidecar under a temp `.voss/sessions/<root>/`, invoke, assert exit 0). Import `review_cmd` lazily/at module top — if it does not yet exist the file is RED via ImportError-guarded xfail OR a direct import that fails the collection only for this file (prefer: import at test-function level wrapped so the file still collects; the tests themselves are RED).
    All three files are scaffolds asserting the target contract; they fail against current code. Do NOT implement any production behavior here.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py tests/harness/board/test_review_sidecar.py tests/harness/board/test_review_cli.py 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - All three files exist under `tests/harness/board/`
    - `grep -c "class Test" tests/harness/board/test_two_source_gate.py` ≥ 3 (back-compat, two-source, B-block)
    - `test_review_cli.py` contains an assertion that an unknown run_id produces a non-zero exit AND stderr text `unknown run_id`
    - `test_review_sidecar.py` asserts the `.review.json` path, `0o600` mode, and the three payload keys
    - The pytest run reports test FAILURES (RED), not whole-file collection errors that abort the other board tests — i.e., `.venv/bin/python -m pytest tests/harness/board/ -q` still collects the full suite
  </acceptance_criteria>
  <done>Three RED scaffold files pin the two-source gate, sidecar persistence, and review CLI contracts; the full board suite still collects cleanly.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test harness → filesystem | Test scaffolds create temp `.voss/sessions/` dirs; no untrusted input, isolated tmp dirs |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V6-01-01 | Tampering | test fixtures writing `.review.json` | accept | Tests use `CliRunner.isolated_filesystem` / `tmp_path`; no real session data touched |
| T-V6-01-02 | Denial | RED scaffold causing whole-suite collection abort | mitigate | Acceptance criteria require the full board suite to still collect; import-failure-guarded test bodies, not module-top hard imports of unbuilt symbols |
| T-V6-01-SC | Tampering | npm/pip/cargo installs | mitigate | Zero new dependencies in this plan (test files only); no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3 -x` exits 0 (baseline green).
- `.venv/bin/python -m pytest tests/harness/board/ -q` collects the full suite (no collection errors); the new V6 scaffolds report as FAILED (RED), the pre-existing 92 remain green, and the previously-failing exit-reasons test is now green.
</verification>

<success_criteria>
- Pre-existing red test fixed (one-line, test-only).
- `test_verdict.py` updated to a 7-field invariant.
- 4 new RED test files exist (`test_two_source_gate.py`, `test_domain_inferred.py`, `test_review_sidecar.py`, `test_review_cli.py`) and fail against current code without breaking suite collection.
- No production (`voss/`) module modified.
</success_criteria>

<output>
Create `.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-01-SUMMARY.md` when done.
</output>
