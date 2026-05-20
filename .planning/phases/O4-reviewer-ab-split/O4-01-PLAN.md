---
phase: O4-reviewer-ab-split
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/board/test_reviewer_a.py
  - tests/harness/board/test_reviewer_b.py
  - tests/harness/board/test_reviewer_integration.py
autonomous: true
requirements:
  - ORVW-01
  - ORVW-02
  - ORVW-03
  - ORVW-04
  - ORVW-05
  - ORVW-06
  - ORVW-07
  - ORVW-08
  - ORVW-09
  - ORVW-10
must_haves:
  truths:
    - "O3 board package exists and verdict.py imports cleanly before any O4 code runs"
    - "RED test scaffolds collect and fail for all 10 ORVW requirements"
    - "Existing test suite is unmodified and passes"
  artifacts:
    - path: "tests/harness/board/test_reviewer_a.py"
      provides: "RED scaffolds for ORVW-01, ORVW-02, ORVW-03, ORVW-08, ORVW-09"
      contains: "pytest.fail"
    - path: "tests/harness/board/test_reviewer_b.py"
      provides: "RED scaffolds for ORVW-04, ORVW-05, ORVW-06, ORVW-07, ORVW-09"
      contains: "pytest.fail"
    - path: "tests/harness/board/test_reviewer_integration.py"
      provides: "RED scaffold for ORVW-10"
      contains: "pytest.fail"
  key_links:
    - from: "tests/harness/board/test_reviewer_a.py"
      to: "voss/harness/board/verdict.py"
      via: "import ReviewerVerdict, Reviewer"
      pattern: "from voss\\.harness\\.board\\.verdict import"
    - from: "tests/harness/board/test_reviewer_b.py"
      to: "voss/harness/board/verdict.py"
      via: "import ReviewerVerdict, Reviewer"
      pattern: "from voss\\.harness\\.board\\.verdict import"
---

<objective>
O3 preflight gate + RED test scaffolds for all 10 ORVW requirements.

Purpose: Verify the O3 substrate (board package, verdict.py, ReviewerVerdict, Reviewer Protocol, Card, DeterministicReviewerStub) is importable before writing any O4 code. Stand up the RED test framework so O4-02 and O4-03 can drive their implementations against failing tests.

Output: 3 test files with xfail scaffolds covering ORVW-01 through ORVW-10. All collect, all fail, zero existing test regressions.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/O4-reviewer-ab-split/O4-CONTEXT.md
@.planning/phases/O4-reviewer-ab-split/O4-RESEARCH.md
@.planning/phases/O4-reviewer-ab-split/O4-PATTERNS.md

<interfaces>
<!-- O3-shipped interfaces O4 consumes. Confirm these exist at preflight. -->

From voss/harness/board/verdict.py (O3-shipped):
  ReviewerVerdict — frozen dataclass with fields: conf (float), source (Literal["A","B"]), tier (Literal["fast","strong"]), verdict (Literal["pass","fail","block"]), notes (str), evidence_refs (tuple[str, ...])
  Reviewer — Protocol with method: async def review(self, card: Card) -> ReviewerVerdict  (confirm sync vs async at preflight)

From voss/harness/board/machine.py (O3-shipped):
  Board, Card

From voss/harness/board/stub.py (O3-shipped):
  DeterministicReviewerStub

From voss/eval/judge.py (M5-shipped):
  Verdict — pydantic BaseModel: verdict (Literal["pass","fail"]), confidence (float 0.0-1.0), rationale (str)
  judge_run — async def judge_run(*, provider, model, task_prompt, final, file_diff, rubric) -> tuple[Verdict | None, str]

From voss_runtime/providers/base.py:
  ProviderResponse — dataclass: text, model, prompt_tokens, completion_tokens, cost_usd, raw, parsed
  ModelProvider — Protocol: async complete(...) -> ProviderResponse, count_tokens(...)

From tests/eval/test_judge_verdict.py (test pattern):
  FakeJudgeProvider — returns canned Verdict/ProviderResponse for hermetic tests
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: O3 preflight gate + RED test scaffolds</name>
  <files>tests/harness/board/test_reviewer_a.py, tests/harness/board/test_reviewer_b.py, tests/harness/board/test_reviewer_integration.py</files>
  <read_first>
    - voss/harness/board/__init__.py (confirm O3 board package exists)
    - voss/harness/board/verdict.py (confirm ReviewerVerdict fields + Reviewer Protocol signature — sync vs async)
    - voss/harness/board/machine.py (confirm Card shape — fields: node_id, column, risk_tier, retry_count, deadline; confirm Board exists)
    - voss/harness/board/stub.py (confirm DeterministicReviewerStub exists and its constructor kwargs)
    - tests/eval/test_judge_verdict.py (FakeJudgeProvider pattern for ProviderResponse construction)
    - tests/harness/test_agent_integration.py (FakeProvider pattern for run_turn-based tests)
    - voss/eval/judge.py (Verdict + judge_run signatures)
    - voss_runtime/providers/base.py (ProviderResponse + ModelProvider protocol shape)
  </read_first>
  <action>
    PREFLIGHT (blocking): Verify that `from voss.harness.board.verdict import ReviewerVerdict, Reviewer` succeeds. Verify that `from voss.harness.board.machine import Board, Card` succeeds. Verify that `from voss.harness.board.stub import DeterministicReviewerStub` succeeds. If ANY import fails, STOP and report "O3 not yet executed — O4 is blocked." Check whether `Reviewer.review` is `async def` or `def` (RESEARCH Open Question #1) and record the finding for O4-02/O4-03.

    After preflight passes, create the `tests/harness/board/` directory (may already exist from O3). Confirm `__init__.py` exists in `tests/harness/board/` or create an empty one.

    Create `tests/harness/board/test_reviewer_a.py` with xfail scaffolds for 5 tests:
    - `test_a_uses_original_idea` (ORVW-01): A derives bar from original idea, not EM AC. xfail(strict=True, reason="ORVW-01: ReviewerA not implemented").
    - `test_a_authors_test_file` (ORVW-02): A authors tests for code cards; exit code is verdict. xfail(strict=True, reason="ORVW-02").
    - `test_a_ai_card_eval` (ORVW-03): A uses judge_run for AI cards (rubric to Verdict). xfail(strict=True, reason="ORVW-03").
    - `test_a_memory_fresh_per_card` (ORVW-08): EpisodicMemory is fresh per review() call, no cross-card bleed. xfail(strict=True, reason="ORVW-08").
    - `test_a_implements_protocol` (ORVW-09): ReviewerA is an instance of the Reviewer Protocol. xfail(strict=True, reason="ORVW-09").

    Each test body contains `pytest.fail("RED — implement in O4-03")`.

    Create `tests/harness/board/test_reviewer_b.py` with xfail scaffolds for 5 tests:
    - `test_b_message_isolation` (ORVW-04): B receives only [artifact, acceptance, repo, original_idea, a_verification_summary] — no EM narrative. xfail(strict=True, reason="ORVW-04").
    - `test_b_tier_selection` (ORVW-05): B uses fast model at intermediate gate. xfail(strict=True, reason="ORVW-05").
    - `test_b_tier_strong` (ORVW-06): B uses strong model at Done gate. xfail(strict=True, reason="ORVW-06").
    - `test_b_residual_2_block` (ORVW-07): B returns verdict="block" when A-verification diverges from idea (Residual-2 invariant). xfail(strict=True, reason="ORVW-07").
    - `test_b_implements_protocol` (ORVW-09): ReviewerB is an instance of the Reviewer Protocol. xfail(strict=True, reason="ORVW-09").

    Each test body contains `pytest.fail("RED — implement in O4-02")`.

    Create `tests/harness/board/test_reviewer_integration.py` with 1 xfail scaffold:
    - `test_board_lifecycle_with_real_reviewers` (ORVW-10): Full board lifecycle with ReviewerA+B stubs drives card to Done. xfail(strict=True, reason="ORVW-10").

    Test body contains `pytest.fail("RED — implement in O4-04")`.

    All test files use `from __future__ import annotations`, `import pytest`, and top-level imports from `voss.harness.board.verdict` (ReviewerVerdict, Reviewer). Use `async def` for async tests natively (pyproject.toml asyncio_mode=auto). Do NOT import ReviewerA or ReviewerB yet (they do not exist) — those imports go inside the test bodies or are guarded by the xfail decorator.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/ --collect-only -q 2>&1 | tail -5</automated>
    <automated>.venv/bin/python -m pytest tests/harness/board/ -x -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/board/test_reviewer_a.py contains exactly 5 test functions: test_a_uses_original_idea, test_a_authors_test_file, test_a_ai_card_eval, test_a_memory_fresh_per_card, test_a_implements_protocol
    - tests/harness/board/test_reviewer_b.py contains exactly 5 test functions: test_b_message_isolation, test_b_tier_selection, test_b_tier_strong, test_b_residual_2_block, test_b_implements_protocol
    - tests/harness/board/test_reviewer_integration.py contains exactly 1 test function: test_board_lifecycle_with_real_reviewers
    - All 11 tests collect successfully via --collect-only
    - All 11 tests are xfail (strict=True) and show as xfailed (not XPASS) on run
    - `from voss.harness.board.verdict import ReviewerVerdict, Reviewer` succeeds at import time
    - Existing test suite (tests/harness/ minus board/) shows zero regressions
    - Reviewer.review signature (sync vs async) is documented in the summary
  </acceptance_criteria>
  <done>11 RED scaffolds collect and xfail; O3 preflight gate passes; existing tests unbroken; Reviewer.review sync/async finding recorded.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| O3→O4 interface | O4 imports frozen types from O3's verdict.py; must not modify verdict.py |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O4-01 | Tampering | verdict.py | mitigate | O4 never modifies verdict.py; grep gate verifies zero diff on verdict.py in every plan |
| T-O4-SC | Tampering | npm/pip installs | accept | O4 installs zero new packages; no supply-chain risk |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/ --collect-only -q` shows 11 tests
- `.venv/bin/python -m pytest tests/harness/board/ -x -q` shows 11 xfailed, 0 passed, 0 failed
- `.venv/bin/python -c "from voss.harness.board.verdict import ReviewerVerdict, Reviewer"` exits 0
- `git diff --name-only` shows only files in tests/harness/board/
</verification>

<success_criteria>
- 11 xfail scaffolds covering all 10 ORVW requirements
- O3 preflight verified (board package importable)
- Reviewer.review sync/async determination documented
- Zero existing test regressions
</success_criteria>

<output>
Create `.planning/phases/O4-reviewer-ab-split/O4-01-SUMMARY.md` when done
</output>
