---
phase: O4-reviewer-ab-split
plan: 04
type: execute
wave: 3
depends_on:
  - O4-02
  - O4-03
files_modified:
  - tests/harness/board/test_reviewer_integration.py
  - voss/harness/board/reviewer_a.py
  - voss/harness/board/reviewer_b.py
autonomous: true
requirements:
  - ORVW-10
  - ORVW-09
must_haves:
  truths:
    - "A full board lifecycle (Backlog to Done) works with ReviewerA + ReviewerB driving at least one Board column transition triggered by a reviewer.review() call"
    - "Both ReviewerA and ReviewerB implement the Reviewer Protocol and are interchangeable with DeterministicReviewerStub"
    - "All 11 ORVW tests pass (O4-01 scaffolds fully green)"
    - "verdict.py is unmodified from O3"
  artifacts:
    - path: "tests/harness/board/test_reviewer_integration.py"
      provides: "Integration test for ORVW-10: full board lifecycle with real reviewer implementations"
      contains: "test_board_lifecycle_with_real_reviewers"
  key_links:
    - from: "tests/harness/board/test_reviewer_integration.py"
      to: "voss/harness/board/reviewer_a.py"
      via: "import ReviewerA"
      pattern: "from voss\\.harness\\.board\\.reviewer_a import"
    - from: "tests/harness/board/test_reviewer_integration.py"
      to: "voss/harness/board/reviewer_b.py"
      via: "import ReviewerB"
      pattern: "from voss\\.harness\\.board\\.reviewer_b import"
    - from: "tests/harness/board/test_reviewer_integration.py"
      to: "voss/harness/board/machine.py"
      via: "import Board, Card"
      pattern: "from voss\\.harness\\.board\\.machine import"
---

<objective>
Integration test proving the full board lifecycle works with real ReviewerA + ReviewerB implementations, plus final acceptance gate for all 11 ORVW tests and the verdict.py invariant.

Purpose: O4's structural claim is that two independent sources (A authors verification, B renders independent judgment) plug into O3's board via the frozen Reviewer Protocol. This plan verifies that claim end-to-end: a card enters at Backlog, receives A-verification and B-judgment at the appropriate gates, and transitions through at least one Board column transition triggered by a reviewer.review() call before reaching Done. It also confirms the global O4 invariants: verdict.py unmodified, all 11 tests green, no existing test regressions.

Output: 1 green integration test (previously RED xfail scaffold from O4-01); full ORVW-01..10 acceptance.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/O4-reviewer-ab-split/O4-CONTEXT.md
@.planning/phases/O4-reviewer-ab-split/O4-RESEARCH.md
@.planning/phases/O4-reviewer-ab-split/O4-02-SUMMARY.md
@.planning/phases/O4-reviewer-ab-split/O4-03-SUMMARY.md

<interfaces>
<!-- O4's full interface surface — both reviewers + board + verdict -->

From voss/harness/board/reviewer_a.py (O4-03):
  class ReviewerA: __init__(*, provider, model, cwd, renderer, base_gate), async review(card) -> ReviewerVerdict

From voss/harness/board/reviewer_b.py (O4-02):
  class ReviewerB: __init__(*, provider, fast_model, strong_model), async review(card, *, tier="fast") -> ReviewerVerdict

From voss/harness/board/verdict.py (O3-frozen):
  ReviewerVerdict(conf, source, tier, verdict, notes, evidence_refs)
  Reviewer(Protocol): async def review(self, card: Card) -> ReviewerVerdict

From voss/harness/board/machine.py (O3):
  Board.from_team_config(team_config, recorder, reviewer=...) -> Board
  Board.move(card, to=column)
  Board.dry_run_gate(card, transition) -> (passed, failing_clauses)
  Card(node_id, column, risk_tier, retry_count, deadline, ...)

From voss/harness/board/stub.py (O3):
  DeterministicReviewerStub(conf=..., verdict=...) — implements Reviewer Protocol
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Integration test — board lifecycle with real ReviewerA + ReviewerB</name>
  <files>tests/harness/board/test_reviewer_integration.py</files>
  <read_first>
    - tests/harness/board/test_reviewer_integration.py (current xfail scaffold from O4-01)
    - voss/harness/board/reviewer_a.py (ReviewerA constructor + review signature)
    - voss/harness/board/reviewer_b.py (ReviewerB constructor + review signature)
    - voss/harness/board/machine.py (Board API — Board.from_team_config, Board.move, Board.dry_run_gate, Card shape, column enum/values, gate predicates — understand the full lifecycle API)
    - voss/harness/board/verdict.py (ReviewerVerdict, Reviewer Protocol)
    - voss/harness/board/stub.py (DeterministicReviewerStub — reference for how O3 tests drive the board)
    - voss/harness/board/gates.py (gate predicates — understand what the board checks at each transition)
    - tests/harness/board/ (any O3 integration tests for the board lifecycle pattern to follow — these are the primary reference for how to construct a Board, create Cards, and drive transitions in tests)
    - voss/harness/permissions.py (PermissionGate constructor for ReviewerA setup)
    - voss/harness/render.py (NullRenderer for silent runs)
  </read_first>
  <action>
    Rewrite `tests/harness/board/test_reviewer_integration.py` — replace the xfail scaffold with a real integration test. Remove `@pytest.mark.xfail(strict=True)`.

    The integration test verifies ORVW-10: "Full board lifecycle with real ReviewerA+B drives card to Done."

    This test does NOT call a real LLM. It uses fake providers for both ReviewerA and ReviewerB. The test is structural: it proves the Protocol contract works end-to-end with the Board, including at least one Board column transition triggered by a reviewer.review() call.

    CRITICAL REQUIREMENT: The test MUST exercise the Board lifecycle — specifically, at least one `Board.move()` (or equivalent Board transition API) must be triggered. Simply calling `review()` on both reviewers outside the Board context is NOT sufficient for ORVW-10. The test must prove that reviewer verdicts drive Board state transitions.

    Create `FakeProviderForA` that scripts run_turn responses such that ReviewerA produces a "pass" verdict (code-card: shell_run returning "[exit 0]"; AI-card: judge_run returning Verdict pass). Reuse the FakeProvider pattern from O4-03 test_reviewer_a.py.

    Create `FakeProviderForB` that returns a canned ReviewerVerdict with conf=0.95, verdict="pass" (sufficient to pass the high-risk-tier threshold). Reuse the FakeReviewerBProvider pattern from O4-02 test_reviewer_b.py.

    The test flow must follow one of these approaches (read O3 board tests to determine which matches the Board API):

    Approach A — Board-driven reviewer invocation:
    1. Set up a Board via Board.from_team_config(...) with ReviewerA and ReviewerB injected as the reviewers.
    2. Create a Card and place it on the Board.
    3. Drive the card through the lifecycle: use Board.move() or the Board's tick/advance API to transition the card through columns (Backlog -> Planned -> InProgress -> InReview -> Done).
    4. Assert the Board internally calls reviewer.review() at the gate transitions.
    5. Assert the card reaches Done.

    Approach B — Manual gate + Board.move() composition:
    1. Set up a Board via Board.from_team_config(...) or direct construction.
    2. Create a Card.
    3. At each gate transition, manually call the appropriate reviewer's review() method to get a ReviewerVerdict.
    4. Use Board.move(card, to=next_column) to advance the card, with the ReviewerVerdict satisfying the gate predicate.
    5. Assert at least one Board.move() call is conditioned on a reviewer.review() result (i.e., the reviewer's verdict determines whether the move succeeds).
    6. Assert the card reaches Done (card.column == Done or equivalent).
    7. Assert both ReviewerA and ReviewerB were invoked.

    Read the O3 board test files and Board API carefully to determine which approach matches the actual Board architecture. The Board may internally invoke reviewers at gate transitions (Approach A), or the caller may need to orchestrate the reviewer calls and Board.move() separately (Approach B). Either way, the test MUST include Board.move() driving the card through at least one column transition gated by a reviewer verdict.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_reviewer_integration.py -x -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - test_board_lifecycle_with_real_reviewers passes (0 xfail, 0 failures)
    - ReviewerA and ReviewerB are both constructed and their review() methods are called
    - The test exercises at least one Board.move() (or equivalent) column transition triggered by a reviewer.review() call
    - The card transitions through at least one column boundary gated by a reviewer verdict before reaching Done
    - Both produce ReviewerVerdict instances with correct field types (conf: float, source: Literal, tier: Literal, verdict: Literal, notes: str, evidence_refs: tuple)
    - The test proves ReviewerA and ReviewerB are drop-in replacements for DeterministicReviewerStub (Protocol compatibility)
    - No direct modification to verdict.py, machine.py, gates.py, or any O3 file
  </acceptance_criteria>
  <done>Integration test proves ReviewerA + ReviewerB plug into the O3 board lifecycle via the Reviewer Protocol, with Board column transitions driven by reviewer verdicts.</done>
</task>

<task type="auto">
  <name>Task 2: Final acceptance gate — all ORVW tests + invariants</name>
  <files>voss/harness/board/reviewer_a.py, voss/harness/board/reviewer_b.py, tests/harness/board/test_reviewer_a.py, tests/harness/board/test_reviewer_b.py, tests/harness/board/test_reviewer_integration.py</files>
  <read_first>
    - tests/harness/board/test_reviewer_a.py (should be all green)
    - tests/harness/board/test_reviewer_b.py (should be all green)
    - tests/harness/board/test_reviewer_integration.py (should be all green)
    - voss/harness/board/verdict.py (must be unmodified from O3)
    - voss/harness/board/reviewer_a.py (no verdict.py imports cycle)
    - voss/harness/board/reviewer_b.py (no agent/subagent imports)
  </read_first>
  <action>
    Run the full O4 test suite and verify all invariants:

    1. Run `.venv/bin/python -m pytest tests/harness/board/ -v -q` — all 11 tests must pass (0 xfail, 0 failures, 0 errors).
    2. Run `.venv/bin/python -m pytest tests/harness/ tests/eval/ -x -q` — full harness + eval suite, zero regressions.
    3. Verify verdict.py invariant: `git diff HEAD -- voss/harness/board/verdict.py` must be empty (O4 never modifies verdict.py).
    4. Verify no circular imports: `.venv/bin/python -c "from voss.harness.board.reviewer_a import ReviewerA; from voss.harness.board.reviewer_b import ReviewerB; print('no circular imports')"` exits 0.
    5. Verify reviewer_b.py isolation: `grep -v '^#' voss/harness/board/reviewer_b.py | grep -c 'voss\.harness\.agent\|voss\.harness\.subagents\|EpisodicMemory'` must be 0 (B does not use agent loop or episodic memory).
    6. Verify reviewer_a.py memory pattern: confirm EpisodicMemory appears inside the `review` method body, not at class level or __init__.

    If any check fails, fix the issue in the relevant source file (reviewer_a.py, reviewer_b.py, or the failing test file). The `files` field above lists all candidate files that may need fixes. Do NOT modify verdict.py.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/ -v -q 2>&1 | tail -15</automated>
    <automated>.venv/bin/python -m pytest tests/harness/ tests/eval/ -x -q --tb=short 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - 11/11 tests in tests/harness/board/ pass with 0 xfail, 0 failures
    - Full harness + eval suite shows 0 new failures (existing known failures are acceptable)
    - git diff on verdict.py is empty
    - No circular imports between reviewer_a.py, reviewer_b.py, and verdict.py
    - reviewer_b.py has zero imports from voss.harness.agent, voss.harness.subagents, or voss_runtime.memory
    - EpisodicMemory in reviewer_a.py is constructed inside review() method body
  </acceptance_criteria>
  <done>All 11 ORVW tests pass. verdict.py unmodified. No circular imports. Isolation invariants verified. Phase O4 acceptance gate satisfied.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| O3 board API | Integration test drives the board lifecycle; must not break O3 tests |
| ReviewerA/B interchangeability | Both must produce identical ReviewerVerdict shape as DeterministicReviewerStub |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O4-08 | Tampering | verdict.py | mitigate | git diff gate verifies verdict.py is unmodified; Task 2 acceptance criterion |
| T-O4-09 | Information Disclosure | reviewer_b.py imports | mitigate | grep gate verifies B has no agent/subagent/memory imports |
| T-O4-SC | Tampering | npm/pip installs | accept | O4 installs zero new packages |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/ -v -q` — 11 passed
- `.venv/bin/python -m pytest tests/harness/ tests/eval/ -x -q` — no new failures
- `git diff HEAD -- voss/harness/board/verdict.py` — empty
- `.venv/bin/python -c "from voss.harness.board.reviewer_a import ReviewerA; from voss.harness.board.reviewer_b import ReviewerB"` — exit 0
- `grep -v '^#' voss/harness/board/reviewer_b.py | grep -c 'voss\.harness\.agent\|EpisodicMemory'` — 0
</verification>

<success_criteria>
- ORVW-10 integration test proves A+B plug into the board lifecycle with Board column transitions driven by reviewer verdicts
- All 11 ORVW tests green (01-10 covered, 09 covered twice for both reviewers)
- verdict.py invariant: zero diff from O3
- Circular import invariant: clean
- Isolation invariants: B has no agent imports; A creates fresh memory per call
- Phase O4 ready for /gsd:verify-work
</success_criteria>

<output>
Create `.planning/phases/O4-reviewer-ab-split/O4-04-SUMMARY.md` when done
</output>
