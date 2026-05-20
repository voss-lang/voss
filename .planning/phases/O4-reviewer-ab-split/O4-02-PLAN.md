---
phase: O4-reviewer-ab-split
plan: 02
type: execute
wave: 2
depends_on:
  - O4-01
files_modified:
  - voss/harness/board/reviewer_b.py
  - tests/harness/board/test_reviewer_b.py
autonomous: true
requirements:
  - ORVW-04
  - ORVW-05
  - ORVW-06
  - ORVW-07
  - ORVW-09
must_haves:
  truths:
    - "Reviewer-B receives ONLY [artifact, acceptance, repo, original_idea, a_verification_summary] — zero EM narrative in messages[]"
    - "Reviewer-B uses fast model at intermediate gate and strong model at Done gate"
    - "Reviewer-B returns verdict='block' when A-verification diverges from the original idea (Residual-2)"
    - "ReviewerB is a valid instance of the Reviewer Protocol"
  artifacts:
    - path: "voss/harness/board/reviewer_b.py"
      provides: "ReviewerB class implementing Reviewer Protocol via single provider.complete() call"
      contains: "class ReviewerB"
    - path: "tests/harness/board/test_reviewer_b.py"
      provides: "5 green tests covering ORVW-04..07 and ORVW-09"
      contains: "test_b_message_isolation"
  key_links:
    - from: "voss/harness/board/reviewer_b.py"
      to: "voss/harness/board/verdict.py"
      via: "import ReviewerVerdict, Reviewer"
      pattern: "from voss\\.harness\\.board\\.verdict import"
    - from: "voss/harness/board/reviewer_b.py"
      to: "voss_runtime/providers/base.py"
      via: "provider.complete() call"
      pattern: "provider\\.complete"
---

<objective>
Implement Reviewer-B: the independent tiered judgment reviewer that produces ReviewerVerdict via a single `provider.complete()` call with strict message-list isolation.

Purpose: Reviewer-B is the cage's independent confidence source. It sees ONLY the original idea, acceptance criteria, artifact, repo context, and A's verification summary. It never sees EM narrative/plans. The A/B split is structurally enforced by what enters `messages[]`. Residual-2 (verdict="block" when A diverges from the idea) is a first-class verdict value, not heuristic string matching.

Output: `reviewer_b.py` implementing the `Reviewer` Protocol; 5 green tests (previously RED xfail scaffolds from O4-01).
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
@.planning/phases/O4-reviewer-ab-split/O4-PATTERNS.md
@.planning/phases/O4-reviewer-ab-split/O4-01-SUMMARY.md

<interfaces>
<!-- Exact analog: voss/eval/judge.py — same provider.complete() + response_format pattern -->

From voss/eval/judge.py:
  async def judge_run(*, provider: ModelProvider, model: str, task_prompt: str, final: str, file_diff: str, rubric: str) -> tuple[Verdict | None, str]
  JUDGE_SYSTEM = "You are an evaluator..."
  Pattern: try provider.complete(messages=[system, user], model=model, response_format=Verdict, temperature=0.0) except ParseError

From voss/harness/board/verdict.py (O3-frozen):
  @dataclass(frozen=True) ReviewerVerdict: conf, source, tier, verdict, notes, evidence_refs
  class Reviewer(Protocol): async def review(self, card: Card) -> ReviewerVerdict

From voss_runtime/providers/base.py:
  ModelProvider(Protocol): async complete(*, messages, model, response_format=None, tools=None, temperature=1.0, max_tokens=None, timeout=None) -> ProviderResponse
  ProviderResponse: text, model, prompt_tokens, completion_tokens, cost_usd, raw, parsed

From voss_runtime/providers/litellm_provider.py:
  ParseError — raised when structured output JSON parsing fails

From tests/eval/test_judge_verdict.py (test pattern):
  FakeJudgeProvider — canned ProviderResponse with .parsed field set
  RaisingProvider — raises ParseError on complete()
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement ReviewerB class</name>
  <files>voss/harness/board/reviewer_b.py</files>
  <read_first>
    - voss/harness/board/verdict.py (ReviewerVerdict exact fields + Reviewer Protocol method signature — sync vs async confirmed in O4-01 summary)
    - voss/harness/board/machine.py (Card fields: node_id, column, risk_tier, retry_count, deadline — identify what fields carry original_idea, acceptance, artifact)
    - voss/eval/judge.py (judge_run: the exact provider.complete() + response_format + ParseError pattern to replicate)
    - voss_runtime/providers/base.py (ModelProvider protocol + ProviderResponse shape)
    - voss_runtime/providers/litellm_provider.py (ParseError import path)
    - voss_runtime/_config.py (default_model string for reference)
  </read_first>
  <action>
    Create `voss/harness/board/reviewer_b.py`. Start with `from __future__ import annotations`.

    Import: `ModelProvider` from `voss_runtime.providers.base`, `ParseError` from `voss_runtime.providers.litellm_provider`, `ReviewerVerdict` and `Reviewer` from `voss.harness.board.verdict`, `Card` from `voss.harness.board.machine`. Use `from typing import Literal`.

    Define module-level constant `REVIEWER_B_SYSTEM` (string). Content must:
    - Declare "You are Reviewer-B, an independent judge"
    - State B sees ONLY: original idea, acceptance criteria, artifact, repository context, and Reviewer-A's verification summary
    - State B does NOT see EM plans, EM narrative, or Reviewer-A's reasoning process
    - Grant explicit authority for Residual-2: set verdict="block" when A's verification diverges from what the original idea requires
    - Instruct return of JSON matching ReviewerVerdict schema (conf, source, tier, verdict, notes, evidence_refs)

    Define `class ReviewerB` implementing the `Reviewer` Protocol.
    Constructor `__init__(self, *, provider: ModelProvider, fast_model: str, strong_model: str)` — stores all three as instance attributes. Both model strings are injectable (tests use fake model names, production uses real ones).

    Implement `async def review(self, card: Card, *, tier: Literal["fast", "strong"] = "fast") -> ReviewerVerdict`. The method:
    1. Selects model: `self.fast_model` if tier=="fast", `self.strong_model` if tier=="strong".
    2. Constructs `user_msg` with exactly 5 labeled sections using only data from `card`: original_idea, acceptance (from card fields — confirm exact field names from machine.py read), artifact, repo_summary, a_verification_summary. CRITICAL: no EM plan text, no EM narrative, no A's episodic history enters this string.
    3. Calls `await self.provider.complete(messages=[{"role": "system", "content": REVIEWER_B_SYSTEM}, {"role": "user", "content": user_msg}], model=model, response_format=ReviewerVerdict, temperature=0.0)`.
    4. On `ParseError`: return a blocking `ReviewerVerdict(conf=0.0, source="B", tier=tier, verdict="block", notes="ParseError: structured output failed", evidence_refs=())`. Do NOT swallow silently like judge_run does — a parse failure at the gate is safer as a block.
    5. On `resp.parsed is None`: same blocking verdict as ParseError.
    6. On success: if the ReviewerVerdict is a frozen dataclass (not pydantic), the structured output from provider.complete() will be pydantic-parsed as the `response_format` shape, then needs translation to the dataclass. Check how O3's verdict.py defines ReviewerVerdict — if it is a dataclass (not pydantic BaseModel), create a pydantic mirror class `_ReviewerBOutput(BaseModel)` with the same fields for `response_format`, then translate to `ReviewerVerdict(...)` from the parsed result. If ReviewerVerdict IS a pydantic BaseModel, use it directly as `response_format`. Handle both cases based on what O3 actually shipped.
    7. Return the ReviewerVerdict with `source="B"` and the appropriate `tier`.

    The information isolation guarantee is structural: `messages[]` contains exactly 2 entries (system + user), and the user message is built from card data only. No method on ReviewerB accepts EM context.

    Ensure `reviewer_b.py` does NOT import from `voss.harness.agent`, `voss.harness.subagents`, or any module that carries session/episodic state. B is a single call, not an agent loop.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.board.reviewer_b import ReviewerB, REVIEWER_B_SYSTEM; print('import ok')"</automated>
  </verify>
  <acceptance_criteria>
    - voss/harness/board/reviewer_b.py exists and imports cleanly
    - ReviewerB.__init__ accepts provider, fast_model, strong_model as keyword-only arguments
    - ReviewerB.review is async def and returns ReviewerVerdict
    - REVIEWER_B_SYSTEM constant contains "independent judge", "original idea", "block", and "Residual-2" or "diverges"
    - reviewer_b.py does NOT import from voss.harness.agent or voss.harness.subagents
    - reviewer_b.py does NOT import from voss_runtime.memory or EpisodicMemory
    - ParseError path returns ReviewerVerdict with verdict="block" (not None or raise)
    - messages list in provider.complete() call contains exactly 2 entries (system + user)
  </acceptance_criteria>
  <done>ReviewerB class importable, implements Reviewer Protocol shape, single provider.complete() call with isolation guarantee.</done>
</task>

<task type="auto">
  <name>Task 2: Turn RED test_reviewer_b.py scaffolds GREEN</name>
  <files>tests/harness/board/test_reviewer_b.py</files>
  <read_first>
    - tests/harness/board/test_reviewer_b.py (current xfail scaffolds from O4-01)
    - voss/harness/board/reviewer_b.py (just-created implementation from Task 1)
    - voss/harness/board/verdict.py (ReviewerVerdict exact constructor kwargs)
    - voss/harness/board/machine.py (Card constructor kwargs — needed to construct test cards)
    - tests/eval/test_judge_verdict.py (FakeJudgeProvider pattern: canned ProviderResponse, RaisingProvider for ParseError)
    - voss_runtime/providers/base.py (ProviderResponse required fields: text, model, prompt_tokens, completion_tokens, cost_usd, raw, parsed)
  </read_first>
  <action>
    Rewrite `tests/harness/board/test_reviewer_b.py` — replace xfail scaffolds with real test implementations. Remove `@pytest.mark.xfail(strict=True)` decorators. Keep all 5 function names unchanged.

    Create a `FakeReviewerBProvider` class (modeled on FakeJudgeProvider from tests/eval/test_judge_verdict.py) that:
    - Accepts a canned `ReviewerVerdict` (or pydantic equivalent) in __init__
    - Records `self.calls: list[dict]` capturing `{"messages": messages, "model": model}` on every complete() call
    - Returns ProviderResponse with text=json-serialized-verdict, model=model, prompt_tokens=1, completion_tokens=1, cost_usd=0.0, raw={}, parsed=canned_verdict
    - Has count_tokens returning 1

    Create a helper `_make_card(...)` that constructs a Card with test data (original_idea, acceptance, artifact, etc. — adapt to Card's actual fields from machine.py read).

    **test_b_message_isolation (ORVW-04):**
    Construct a ReviewerB with FakeReviewerBProvider. Call review(card). Assert:
    - provider.calls has exactly 1 entry
    - messages list has exactly 2 entries (system + user)
    - The user message content contains "original_idea_text" (the card's idea) but does NOT contain "em_plan", "EM", "engineering manager", or any EM-narrative marker
    - The system message is REVIEWER_B_SYSTEM

    **test_b_tier_selection (ORVW-05):**
    Construct ReviewerB with fast_model="test-fast" and strong_model="test-strong". Call review(card, tier="fast"). Assert provider.calls[0]["model"] == "test-fast".

    **test_b_tier_strong (ORVW-06):**
    Same setup. Call review(card, tier="strong"). Assert provider.calls[0]["model"] == "test-strong".

    **test_b_residual_2_block (ORVW-07):**
    Construct FakeReviewerBProvider that returns a ReviewerVerdict with verdict="block". Call review(card). Assert returned verdict.verdict == "block". Assert verdict.source == "B". This tests that the Residual-2 path is a first-class structured value, not string parsing.

    **test_b_implements_protocol (ORVW-09):**
    Import ReviewerB and Reviewer. Construct a ReviewerB instance. Assert isinstance(b, Reviewer) (Reviewer is runtime_checkable Protocol). If Reviewer is NOT runtime_checkable, use inspect.signature or structural duck-typing check instead (verify review method exists with correct signature).

    All tests are `async def` (pyproject.toml asyncio_mode=auto).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_reviewer_b.py -x -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - All 5 tests in test_reviewer_b.py pass (0 xfail, 0 failures)
    - test_b_message_isolation asserts messages list length == 2 AND absence of EM-narrative strings
    - test_b_tier_selection asserts model == "test-fast"
    - test_b_tier_strong asserts model == "test-strong"
    - test_b_residual_2_block asserts verdict.verdict == "block" (not string matching on notes)
    - test_b_implements_protocol verifies ReviewerB is a Reviewer (Protocol conformance)
    - No imports from voss.harness.agent or voss.harness.subagents in the test file
    - Existing tests outside tests/harness/board/ show zero regressions
  </acceptance_criteria>
  <done>5 tests GREEN covering ORVW-04..07 and ORVW-09 for Reviewer-B. Information isolation, tiered model selection, Residual-2, and Protocol conformance all verified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| B's messages[] construction | Untrusted card data enters the system prompt; isolation = message-list discipline |
| provider.complete() output | LLM-generated structured output parsed as ReviewerVerdict; pydantic validates |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O4-02 | Information Disclosure | reviewer_b.py messages[] | mitigate | messages[] constructed from exactly 5 card fields; no EM narrative input parameter exists on ReviewerB |
| T-O4-03 | Tampering | provider.complete() output | mitigate | pydantic response_format validates ReviewerVerdict shape; ParseError produces verdict="block" (fail-safe) |
| T-O4-04 | Spoofing | verdict.source field | mitigate | ReviewerB hardcodes source="B" in the returned ReviewerVerdict; LLM output does not control source field |
| T-O4-SC | Tampering | npm/pip installs | accept | O4 installs zero new packages |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/test_reviewer_b.py -x -q` — 5 passed
- `.venv/bin/python -c "from voss.harness.board.reviewer_b import ReviewerB"` — exit 0
- `grep -c "voss.harness.agent\|voss.harness.subagents" voss/harness/board/reviewer_b.py` — 0 (no agent/subagent imports)
- `git diff --name-only voss/harness/board/verdict.py` — empty (verdict.py unmodified)
</verification>

<success_criteria>
- ReviewerB implements the Reviewer Protocol with a single provider.complete() call
- Information isolation structurally enforced: no EM narrative input path exists
- Tiered model selection injectable via constructor (fast_model, strong_model)
- Residual-2 is verdict="block" (first-class value, not heuristic)
- ParseError produces verdict="block" (fail-safe, not silent skip)
- 5/5 tests pass, 0 xfail
</success_criteria>

<output>
Create `.planning/phases/O4-reviewer-ab-split/O4-02-SUMMARY.md` when done
</output>
