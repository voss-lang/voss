---
phase: O5-engineering-manager-loop
plan: 05
type: tdd
wave: 5
depends_on:
  - O5-04
files_modified:
  - tests/integration/harness/__init__.py
  - tests/integration/harness/conftest.py
  - tests/integration/harness/test_em_full_run.py
  - tests/integration/harness/test_em_misroute_audit.py
  - tests/integration/harness/test_em_kill_rescope_lineage.py
  - .planning/phases/O5-engineering-manager-loop/O5-VALIDATION.md
  - .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md
autonomous: true
requirements:
  - OEM-08
  - OEM-09
  - OEM-10
must_haves:
  truths:
    - "Integration test runs the full idea → all-terminal arc with DeterministicEMStub + StubBoard (until O3 ships) + StubReviewer (until O4 ships)"
    - "Misroute audit data is observable: handle audit side-table exposes RoutingRationale.chosen_role; a future ReviewerVerdict.domain_inferred mismatch is detectable via the cross-phase ask C-02"
    - "Kill / rescope lineage test: predecessor session-tree-node JSON still readable on disk; bidirectional pointers consistent"
    - "RunFinal persisted to .voss/sessions/<root_id>/_run_final.json with leading underscore (per RESEARCH Q8)"
    - "EXIT_REASONS now contains both 'killed' (O5) and the future 'timeout' (O3) — additive coordination confirmed"
    - "Cross-phase coordination doc (O5-CROSS-PHASE-COORDINATION.md) re-surfaces C-01 / C-02 / C-03 for O3 / O4 planner consumption"
    - "VALIDATION.md ships with the OEM-01..OEM-10 → plan-ID → verify-command coverage matrix"
  artifacts:
    - path: "tests/integration/harness/test_em_full_run.py"
      provides: "end-to-end happy path: idea → ticket → dispatch → Done"
      contains: "em_loop"
    - path: "tests/integration/harness/test_em_misroute_audit.py"
      provides: "OEM-09 — misroute audit data emission; cross-phase ask for ReviewerVerdict.domain_inferred"
    - path: "tests/integration/harness/test_em_kill_rescope_lineage.py"
      provides: "OEM-07 lineage: predecessor JSON on disk + bidirectional pointers"
    - path: ".planning/phases/O5-engineering-manager-loop/O5-VALIDATION.md"
      provides: "OEM-01..10 coverage matrix"
    - path: ".planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md"
      provides: "C-01 / C-02 / C-03 re-surfaced as actionable asks"
  key_links:
    - from: "tests/integration/harness/test_em_full_run.py"
      to: "voss/harness/em/loop.py"
      via: "em_loop full run with stubs"
      pattern: "from voss\\.harness\\.em import em_loop"
    - from: ".planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md"
      to: ".planning/phases/O3-board-state-machine/O3-SPEC.md"
      via: "Reviewer signature ask + EXIT_REASONS coordination"
      pattern: "Reviewer\\.review"
---

<objective>
Close the phase with end-to-end integration coverage and cross-phase
coordination artifacts.

Three integration tests live under `tests/integration/harness/`:
1. Full happy-path run — idea → ticket → dispatch → tick → all-terminal.
2. Misroute audit emission — handle audit side-table exposes
   RoutingRationale.chosen_role; the test ALSO asserts what O5 needs from
   O4 (`ReviewerVerdict.domain_inferred`) and marks the assertion as
   `xfail(strict=True)` with a reason pointing at the cross-phase
   coordination doc (so when O4 lands the field, the xfail flips to XPASS
   and the test infrastructure flags the cross-phase ask as resolved).
3. Kill/rescope lineage — predecessor's JSON on disk survives;
   bidirectional KillRecord↔RescopeRecord pointers consistent.

Two planning artifacts ship alongside:
- `O5-VALIDATION.md` — the OEM-01..OEM-10 → plan-ID → verify-command
  coverage matrix.
- `O5-CROSS-PHASE-COORDINATION.md` — re-surfaces the three coordination
  asks from W0 (C-01 Reviewer signature, C-02 ReviewerVerdict.domain_inferred,
  C-03 EXIT_REASONS additive ordering) as actionable items O3 / O4 planners
  pick up.

Purpose: O5 is the autonomous lead loop; W5 is the proof that the loop
runs end-to-end and emits the audit data O6 will surface. The
cross-phase asks are first-class artifacts because O3 / O4 are not yet
shipped; the asks live as text now and resolve when those phases land.

Output: 3 integration tests + 1 conftest + 2 planning docs.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/O5-engineering-manager-loop/O5-CONTEXT.md
@.planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md
@.planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md
@.planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md
@.planning/phases/O5-engineering-manager-loop/O5-01-SUMMARY.md
@.planning/phases/O5-engineering-manager-loop/O5-02-SUMMARY.md
@.planning/phases/O5-engineering-manager-loop/O5-03-SUMMARY.md
@.planning/phases/O5-engineering-manager-loop/O5-04-SUMMARY.md
@voss/harness/em/__init__.py
@voss/harness/em/loop.py
@voss/harness/em/handle.py
@voss/harness/em/stub.py
@tests/harness/em/conftest.py
@tests/harness/test_happy_path_integration.py

<interfaces>
<!-- Full em/ public surface (W1+W2+W3+W4) -->

From voss.harness.em:
  Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal
  EMCageViolation
  EMBoardHandle, BoardSnapshot, BoardProtocol, CardProtocol, Column
  EMPlanResponse, EMOp, CreateTicketOp, DispatchCardOp, KillCardOp,
    RescopeCardOp, SetACOp, SetDoDOp, NoopOp
  em_plan, DeterministicEMStub
  em_loop

<!-- Live -->

From voss.harness.session import EXIT_REASONS (must contain 'killed' post-W1)
From voss.harness.session_tree import SessionTreeNode, SessionTreeManager
From voss.harness.team import compile_team
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: RED — integration test scaffolds + conftest</name>
  <files>tests/integration/harness/__init__.py, tests/integration/harness/conftest.py, tests/integration/harness/test_em_full_run.py, tests/integration/harness/test_em_misroute_audit.py, tests/integration/harness/test_em_kill_rescope_lineage.py</files>
  <read_first>
    - tests/harness/test_happy_path_integration.py lines 1-78 (mock_provider + isolated_env patterns)
    - tests/harness/em/conftest.py (W2 — fixtures and StubBoard)
    - voss/harness/em/loop.py (W4 — em_loop signature)
    - voss/harness/em/handle.py (W2 — handle audit side-table read surface)
    - tests/parser/examples/team_strawman.voss (TeamConfig source)
    - .planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md §"Layer 2 — Integration tests"
    - .planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md §"tests/integration/harness/test_em_full_run.py"
  </read_first>
  <behavior>
    conftest.py (in tests/integration/harness/):
      - Mirror tests/harness/conftest.py's `isolated_state` autouse fixture
        (sets XDG_STATE_HOME). Tests/integration/ is a separate test root,
        so the fixture must be local.
      - Re-export key W2 fixtures (stub_board, stub_recorder,
        tiny_team_config, base_gate, make_handle) by importing them from
        tests/harness/em/conftest.py via a fixture-forwarding pattern (or
        duplicate the minimum needed — duplication is acceptable since
        integration tests should be self-contained per RESEARCH §Layer 2).

    test_em_full_run.py — happy-path end-to-end:
      - Build the handle via the conftest fixtures.
      - Script a DeterministicEMStub with 3 EMPlanResponses:
        iter 1: CreateTicketOp(worker_role="backend", original_idea="ship the homepage")
        iter 2: DispatchCardOp(card_id=…, role_id="backend", task="…",
                rationale_text="backend handles api routes",
                candidates_considered=["backend","frontend"])
        iter 3: NoopOp
      - Inject a fake subagent_runner that synchronously marks the card
        Done (no real run_turn).
      - `await em_loop(idea="ship the homepage", em_handle=handle,
        em_agent=stub, roster_descriptions={...}, max_iterations=20)`.
      - Assert RunFinal: total_cards=1, done_count=1, killed_count=0,
        rescope_count=0, em_iterations<=20.
      - Assert the routing-rationale side-table has exactly 1
        RoutingRationale; chosen_role=="backend";
        candidates_considered==("backend","frontend").
      - Assert the audit copy on the rationale contains the literal
        original_idea string verbatim somewhere in either
        ticket.original_idea OR the rationale_text (L-03 reminder: the
        idea text might mention "model" or "token" legitimately — the
        L-03 check is on FIELD names + EM-emitted copy, not on the human's
        idea).

    test_em_misroute_audit.py — OEM-09 audit emission + C-02 cross-phase ask:
      - Build the handle; stub emits CreateTicketOp(worker_role="backend")
        + DispatchCardOp(role_id="backend").
      - Run one em_loop iteration.
      - Assert handle audit side-table has the RoutingRationale with
        chosen_role="backend".
      - Use `@pytest.mark.xfail(strict=True, reason="C-02: O4 must add
        ReviewerVerdict.domain_inferred — see O5-CROSS-PHASE-COORDINATION.md")`
        on the inner assertion that reads
        `verdict.domain_inferred == "ai"`. The xfail-strict flip to XPASS
        when O4 lands the field signals coordination is done.
      - Assert the full audit chain reads without exceptions:
        handle.snapshot() → audit-side-table for the card → RoutingRationale.

    test_em_kill_rescope_lineage.py — OEM-07 lineage:
      - Build the handle. Stub iter 1: CreateTicketOp("api endpoint").
        Iter 2: KillCardOp(card_id=…, rationale_text="wrong scope").
      - Run em_loop.
      - Assert the original card's SessionTreeNode JSON STILL EXISTS at
        `.voss/sessions/<root_id>/<card_node_id>.json` (read it with
        `Path.read_text()` and parse JSON).
      - Assert the node's terminal_state.exit_reason == "killed".
      - Stub iter 1: CreateTicketOp("api endpoint"). Iter 2:
        RescopeCardOp(card_id=…, new_worker_role="frontend",
        new_acceptance=["…"], rationale_text="scope shift").
      - After rescope, assert (a) predecessor JSON still on disk;
        (b) successor card exists with column ∈ {Backlog, Planned};
        (c) successor's ticket.lineage_parent_id == predecessor_card_id;
        (d) predecessor's audit side-table KillRecord.successor_card_id
        == successor card's node_id.

    All RED until O5-01..O5-04 have shipped (which they have by W5 turn).
    Confirm collection succeeds and either all green (if the implementation
    is correct) or surfaces an integration-only gap.
  </behavior>
  <action>
    Write the conftest + three integration test files. Use the existing
    W2 fixtures via duplication or fixture-import.

    For the xfail-strict assertion in test_em_misroute_audit.py, the test
    body should try to look up `verdict.domain_inferred` on a verdict
    object that O4 will eventually emit; until O4 ships the field, the
    lookup raises AttributeError and xfail-strict marks it as expected.
    Do NOT inject a fake verdict object that simulates the future field —
    the goal is to use xfail as the cross-phase tripwire.

    Run pytest tests/integration/harness/ -x -q to collect.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/integration/harness/ -x -q --tb=short 2>&amp;1 | tee /tmp/o5-05-collect.log; grep -qE "(passed|failed|xfailed|error)" /tmp/o5-05-collect.log &amp;&amp; echo EM_INTEGRATION_COLLECT_OK</automated>
  </verify>
  <acceptance_criteria>
    - 4 new files under tests/integration/harness/.
    - pytest collects without errors (modules importable).
    - The misroute xfail tests are MARKED xfail-strict, not commented out.
  </acceptance_criteria>
  <done>Integration test scaffolds + conftest committed.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: GREEN — close gaps until integration tests pass; ship coordination + validation docs</name>
  <files>voss/harness/em/loop.py, voss/harness/em/handle.py, .planning/phases/O5-engineering-manager-loop/O5-VALIDATION.md, .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md</files>
  <read_first>
    - tests/integration/harness/test_em_full_run.py (Task 1)
    - tests/integration/harness/test_em_misroute_audit.py (Task 1)
    - tests/integration/harness/test_em_kill_rescope_lineage.py (Task 1)
    - voss/harness/em/loop.py (W4 implementation)
    - voss/harness/em/handle.py (W2 implementation; finalize_run + RunFinal persistence)
    - .planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md (C-01/C-02/C-03)
    - .planning/phases/O4-reviewer-ab-split/O4-VALIDATION.md (validation-matrix shape to mirror)
  </read_first>
  <behavior>
    Integration-test pass requires:

    1. handle.finalize_run() must persist `RunFinal` to
       `.voss/sessions/<root_id>/_run_final.json` (W2 may have skipped
       persistence). If not yet done, extend the handle to write the file
       on finalize_run; the file mode 0o600; leading underscore matches
       O1 convention but distinguishes from per-node JSON.
    2. handle.snapshot() must surface the audit side-table to integration
       tests via a public read accessor — if W2 only exposed
       `_node_audit` (private), add a public `audit_for_card(card_id)
       -> NodeAuditView` method that returns a frozen, read-only view.
       Add a corresponding test in tests/harness/em/test_em_handle.py if
       not already covered.
    3. The full-run test exercises the dispatch path via the fake
       subagent_runner. Loop must mark cards Done when the runner returns
       (the StubBoard helper does this; if the loop doesn't see column
       updates, the issue is in the StubBoard fixture — fix the fixture,
       not production code).

    Loop / handle code changes: ONLY if integration reveals an integration
    bug. Most behavior is W1–W4. Document any production-code change in
    O5-05-SUMMARY.md with the integration-only justification.

    Planning artifacts:

    `O5-VALIDATION.md` — mirror the shape of O4-VALIDATION.md:
      - Frontmatter: phase: O5, status: complete, wave_0_complete: true.
      - Test infrastructure block: pytest 7.x; framework command:
        `.venv/bin/python -m pytest tests/harness/em/ tests/integration/harness/ -x -q --tb=short`.
      - Sampling rate: per-task `tests/harness/em/`; per-wave
        `tests/harness/em/ tests/integration/harness/`; phase-gate full
        suite green.
      - Per-OEM coverage matrix (OEM-01..OEM-10 → plan-id → verify-command
        → unique tag → status pending).
      - Wave-0 requirements list: ticked complete.
      - Manual-only verifications: empty (O5 is fully automatable).
      - Validation sign-off checklist: each item checked.

    `O5-CROSS-PHASE-COORDINATION.md` — three sections:
      - C-01: Reviewer Protocol signature.
        Background: O3-SPEC §7 locks `Reviewer.review(card) -> ReviewerVerdict`.
        O4-01-PLAN Gate 3 will STOP if Card lacks original_idea / domain /
        artifact_path / artifact_text / file_diff / a_verification_summary.
        O5 introduced `Ticket` to wrap Card + EM-authored scaffolding.
        Ask: O4 should accept `Reviewer.review(ticket: Ticket) ->
        ReviewerVerdict` (or `Reviewer.review(card, ticket)` tuple).
        Resolution path: O3 planner amends SPEC line N before O4-02
        executes; O4 takes the amended signature.
      - C-02: ReviewerVerdict.domain_inferred field.
        Background: OEM-09 misroute audit needs Reviewer-B's claimed
        domain to diff against Ticket.worker_role. Fallback is regex on
        ReviewerVerdict.notes (worse fidelity).
        Ask: O4 adds `domain_inferred: Optional[Literal["code","ai"]] =
        None` to ReviewerVerdict.
        Resolution path: O4-02 implementer adds the field; O5
        test_em_misroute_audit.py xfail flips to XPASS, signaling done.
      - C-03: EXIT_REASONS additive ordering.
        Background: O3 wants "timeout" (O3-CONTEXT open question 5),
        O5 has already shipped "killed". Both additive; same playbook.
        Ask: O3 lands "timeout" additively in its own W1 (no conflict;
        the frozenset members are commutative).
        Resolution path: O3 W1 modifies session.py the same way O5-01
        did. If the W1 commit hashes interleave, the second commit
        rebases trivially.
  </behavior>
  <action>
    1. Run integration tests; identify failures.
    2. For each failure, decide: (a) test bug (fix conftest), (b) handle
       gap (extend handle with persistence or public accessor — minimal
       diff), (c) loop gap (very rare; W4 should be complete).
    3. Iterate to GREEN on the two non-xfail integration tests
       (test_em_full_run.py + test_em_kill_rescope_lineage.py). The
       misroute xfail must remain xfail-strict.
    4. Write O5-VALIDATION.md per the shape above.
    5. Write O5-CROSS-PHASE-COORDINATION.md per the shape above.

    Final full suite:
      .venv/bin/python -m pytest tests/harness/em/ tests/integration/harness/ -x -q
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/ tests/integration/harness/ -q --tb=short &amp;&amp; test -f .planning/phases/O5-engineering-manager-loop/O5-VALIDATION.md &amp;&amp; test -f .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md &amp;&amp; grep -q "OEM-01" .planning/phases/O5-engineering-manager-loop/O5-VALIDATION.md &amp;&amp; grep -q "C-01" .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md &amp;&amp; grep -q "C-02" .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md &amp;&amp; grep -q "C-03" .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md &amp;&amp; echo O5_FULL_GREEN</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/em/ + tests/integration/harness/ all green (xfailed allowed for the C-02 tripwire).
    - .voss/sessions/<root_id>/_run_final.json persisted on em_loop completion (with mode 0o600).
    - handle.audit_for_card(card_id) provides a public read of the side-table.
    - O5-VALIDATION.md exists with OEM-01..OEM-10 coverage matrix.
    - O5-CROSS-PHASE-COORDINATION.md exists with C-01, C-02, C-03 sections.
    - tests/harness/test_session_redaction.py still green (regression check).
  </acceptance_criteria>
  <done>All integration green (modulo intentional xfail); validation matrix + coordination doc shipped; commit references OEM-08, OEM-09, OEM-10.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| W5 integration ↔ W2 audit side-table | Public accessor exposes audit data O6 reads; private leak would force O6 to dig. |
| RunFinal on-disk JSON ↔ filesystem (audit replay) | Persistence guarantees audit replay across process boundaries. |
| xfail-strict ↔ cross-phase coordination | An xfail flipping to XPASS is the tripwire that the O4 ask has been resolved. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O5-05 | Repudiation | Misroute runs with no audit (residual #4 accepted but data must surface) | mitigate | RoutingRationale emitted on every dispatch; test_em_misroute_audit.py asserts the side-table read. C-02 cross-phase ask documents the future O4 field needed for the full diff. |
| T-O5-04 | Tampering | Killed-card JSON file removed from disk | mitigate | test_em_kill_rescope_lineage.py reads predecessor JSON post-kill; asserts file exists + terminal_state.exit_reason == "killed". |
| T-O5-06 | Tampering | RunFinal not persisted; audit cannot replay | mitigate | _run_final.json written via finalize_run; integration test asserts file exists + content matches counts. |
| T-O5-XPhase | Information disclosure | Cross-phase coordination ask buried in PLAN body | mitigate | Dedicated O5-CROSS-PHASE-COORDINATION.md surfaces C-01/C-02/C-03 as actionable items for O3/O4 planners. |
</threat_model>

<verification>
.venv/bin/python -m pytest tests/harness/em/ tests/integration/harness/ -q && test -f .planning/phases/O5-engineering-manager-loop/O5-VALIDATION.md && test -f .planning/phases/O5-engineering-manager-loop/O5-CROSS-PHASE-COORDINATION.md && .venv/bin/python -c "from voss.harness.session import EXIT_REASONS; assert 'killed' in EXIT_REASONS" && echo O5_FULL_GREEN
</verification>

<success_criteria>
- tests/integration/harness/ end-to-end tests green (with intentional xfail-strict on the C-02 tripwire).
- .voss/sessions/<root_id>/_run_final.json persisted.
- O5-VALIDATION.md ships with OEM-01..OEM-10 coverage matrix.
- O5-CROSS-PHASE-COORDINATION.md ships with C-01/C-02/C-03.
- Closes with the unique tag O5_FULL_GREEN.
</success_criteria>

<output>
Create `.planning/phases/O5-engineering-manager-loop/O5-05-SUMMARY.md` summarizing
the closed phase and pointing at O5-VALIDATION.md + O5-CROSS-PHASE-COORDINATION.md.
</output>
