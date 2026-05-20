---
phase: O4-reviewer-ab-split
plan: 03
type: execute
wave: 2
depends_on:
  - O4-01
files_modified:
  - voss/harness/board/reviewer_a.py
  - tests/harness/board/test_reviewer_a.py
autonomous: true
requirements:
  - ORVW-01
  - ORVW-02
  - ORVW-03
  - ORVW-08
  - ORVW-09
must_haves:
  truths:
    - "Reviewer-A derives the judging bar from the original idea, not EM's AC/DoD"
    - "Reviewer-A authors and runs deterministic tests for code cards; test exit code is the verdict"
    - "Reviewer-A uses judge_run for AI cards with an A-authored rubric; Verdict translates to ReviewerVerdict"
    - "EpisodicMemory is fresh per review() call — no cross-card bleed"
    - "ReviewerA is a valid instance of the Reviewer Protocol"
  artifacts:
    - path: "voss/harness/board/reviewer_a.py"
      provides: "ReviewerA class implementing Reviewer Protocol via run_turn agent loop"
      contains: "class ReviewerA"
    - path: "tests/harness/board/test_reviewer_a.py"
      provides: "5 green tests covering ORVW-01..03, ORVW-08, ORVW-09"
      contains: "test_a_uses_original_idea"
  key_links:
    - from: "voss/harness/board/reviewer_a.py"
      to: "voss/harness/board/verdict.py"
      via: "import ReviewerVerdict, Reviewer"
      pattern: "from voss\\.harness\\.board\\.verdict import"
    - from: "voss/harness/board/reviewer_a.py"
      to: "voss/harness/agent.py"
      via: "run_turn call for A's authoring loop"
      pattern: "from voss\\.harness\\.agent import run_turn"
    - from: "voss/harness/board/reviewer_a.py"
      to: "voss/eval/judge.py"
      via: "judge_run call for AI-card eval gate"
      pattern: "from voss\\.eval\\.judge import judge_run"
---

<objective>
Implement Reviewer-A: the verification-authoring reviewer that derives the judging bar from the original human idea and produces deterministic verification (tests for code cards, eval harness for AI cards).

Purpose: Reviewer-A is the cage's bar-author. The OPLAN invariant "engineers cannot author the verification that gates them" is structurally enforced: A is a separate agent (not the EM, not the engineer) that uses `run_turn` with fresh `EpisodicMemory` per card to derive what "done" means from the original idea. For code cards, A authors a test file and runs it via `shell_run` — exit code IS the verdict. For AI cards, A authors a rubric and delegates to `judge_run` — Verdict.confidence becomes ReviewerVerdict.conf.

Output: `reviewer_a.py` implementing the `Reviewer` Protocol; 5 green tests (previously RED xfail scaffolds from O4-01).
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
<!-- Reviewer-A's two analogs: run_subagent (agent loop) + judge_run (AI-card path) -->

From voss/harness/agent.py:
  async def run_turn(task: str, *, tools: dict[str, ToolEntry], cwd: Path, renderer: Renderer,
    confidence_threshold: float = 0.60, token_budget: int = 60_000, model: str | None = None,
    provider: ModelProvider | None = None, history: EpisodicMemory | None = None,
    permissions: PermissionGate | None = None, session_id: str | None = None,
    cognition=None, prior_context: dict | None = None, voss_md_text: str | None = None) -> ...

From voss/harness/subagents.py (run_subagent pattern):
  result = await run_turn(agent_task(spec, task), tools=child_tools, cwd=cwd, renderer=renderer,
    model=model, provider=provider, history=EpisodicMemory(capacity=20), permissions=gate, ...)

From voss/eval/judge.py:
  async def judge_run(*, provider, model, task_prompt, final, file_diff, rubric) -> tuple[Verdict | None, str]
  class Verdict(BaseModel): verdict: Literal["pass","fail"], confidence: float, rationale: str

From voss/harness/board/verdict.py (O3-frozen):
  @dataclass(frozen=True) ReviewerVerdict: conf, source, tier, verdict, notes, evidence_refs
  class Reviewer(Protocol): async def review(self, card: Card) -> ReviewerVerdict

From voss/harness/team.py:
  def gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate
  def filter_toolset_for_role(spec: SubagentSpec, base_toolset: Mapping[str, ToolEntry]) -> dict[str, ToolEntry]

From voss/harness/subagents.py:
  SubagentSpec(id, description, role_prompt, model=None, mode=None, scope=None, budget=None, tools=None, net=False)

From voss_runtime:
  EpisodicMemory(capacity=20)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement ReviewerA class</name>
  <files>voss/harness/board/reviewer_a.py</files>
  <read_first>
    - voss/harness/board/verdict.py (ReviewerVerdict exact fields + Reviewer Protocol method signature)
    - voss/harness/board/machine.py (Card fields — identify what carries original_idea, domain, artifact_path, acceptance)
    - voss/harness/agent.py (run_turn signature at line 412 — exact kwargs, return type)
    - voss/harness/subagents.py (run_subagent at lines 90-164 — the EpisodicMemory(capacity=20) fresh-per-call pattern)
    - voss/harness/team.py (gate_for_role, filter_toolset_for_role — signatures and required args)
    - voss/harness/tools.py (make_toolset signature — what args it accepts)
    - voss/harness/render.py (Renderer, NullRenderer, PlainRenderer — for silent A runs)
    - voss/eval/judge.py (judge_run signature, Verdict fields, JUDGE_SYSTEM — AI-card path)
    - voss/harness/permissions.py (PermissionGate constructor kwargs, Mode enum values)
    - voss_runtime/memory/episodic.py (EpisodicMemory constructor — confirm capacity kwarg)
  </read_first>
  <action>
    Create `voss/harness/board/reviewer_a.py`. Start with `from __future__ import annotations`.

    Import: `uuid` (stdlib), `Path` (stdlib), `Literal` from typing, `EpisodicMemory` from `voss_runtime`, `ModelProvider` from `voss_runtime.providers.base`, `run_turn` from `voss.harness.agent`, `Renderer` from `voss.harness.render`, `make_toolset` from `voss.harness.tools`, `gate_for_role` and `filter_toolset_for_role` from `voss.harness.team`, `SubagentSpec` from `voss.harness.subagents`, `PermissionGate` from `voss.harness.permissions`, `judge_run` and `Verdict` from `voss.eval.judge`, `ReviewerVerdict` and `Reviewer` from `voss.harness.board.verdict`, `Card` from `voss.harness.board.machine`.

    Define module-level constant `REVIEWER_A_ROLE_PROMPT` — a task template string that anchors to the original idea. Content must instruct A to:
    - Derive the verification bar from the provided original idea (NOT from EM's AC/DoD)
    - For code-domain cards: write a test file and run it via shell_run; exit 0 = pass, non-zero = fail
    - For AI-domain cards: write a rubric (plain-text PASS/FAIL criteria) then signal completion
    - Never consult EM plans or prior A reviews

    Define a private helper `_reviewer_a_task(original_idea: str, artifact_path: str, domain: str) -> str` that formats `REVIEWER_A_ROLE_PROMPT` with the card's specifics.

    Define a private helper `_verdict_from_judge(v: Verdict, rubric_id: str) -> ReviewerVerdict` that translates M5's `Verdict` (pydantic) to O3's `ReviewerVerdict` (frozen dataclass). Mapping: conf=v.confidence, source="A", tier="strong" (A's determination is always "strong" — deterministic), verdict=v.verdict (pass/fail — A never produces "block"), notes=v.rationale, evidence_refs=(rubric_id,).

    Define a private helper `_verdict_from_test_exit(exit_code: int, test_file: str, output: str) -> ReviewerVerdict` for code-card path. Mapping: conf=1.0 if exit_code==0 else 0.0, source="A", tier="strong", verdict="pass" if exit_code==0 else "fail", notes=output (truncated to 2000 chars), evidence_refs=(test_file,).

    Define `class ReviewerA` implementing the `Reviewer` Protocol.
    Constructor `__init__(self, *, provider: ModelProvider, model: str, cwd: Path, renderer: Renderer, base_gate: PermissionGate)` — stores all as instance attributes. Also construct a `SubagentSpec` for reviewer_a internally: id="reviewer_a", description="Derives verification bar from original idea", role_prompt=REVIEWER_A_ROLE_PROMPT, mode=check O3/O2's expected mode for A (likely "edit" — needs fs_write for test authoring + shell_run for execution), tools=frozenset({"fs", "shell"}) (A needs fs_write for test files + shell_run for execution).

    Implement `async def review(self, card: Card) -> ReviewerVerdict`. The method:
    1. Creates `EpisodicMemory(capacity=20)` INSIDE this method body (CRITICAL: never in __init__ — Pitfall 2).
    2. Creates a fresh `session_id = str(uuid.uuid4())` (no shared session).
    3. Derives the task prompt from `_reviewer_a_task(card.original_idea, card.artifact_path, card.domain)` — adapt field names to actual Card fields from machine.py.
    4. Calls `run_turn(task_prompt, tools=filter_toolset_for_role(self._reviewer_a_spec, make_toolset(self.cwd, renderer=self.renderer)), cwd=self.cwd, renderer=self.renderer, model=self.model, provider=self.provider, history=memory, permissions=gate_for_role(self._reviewer_a_spec, self.base_gate), session_id=session_id)`.
    5. After `run_turn` completes, inspect the result to determine A's outcome:
       - For **code cards** (card.domain == "code"): parse the run result for `shell_run` tool calls. Find the test execution call, parse the `[exit N]` suffix from the shell output. Return `_verdict_from_test_exit(exit_code, test_file, output)`.
       - For **AI cards** (card.domain == "ai"): extract A's authored rubric from the run result (A writes it as part of its agent loop). Call `await judge_run(provider=self.provider, model=self.model, task_prompt=card.original_idea, final=card.artifact_text, file_diff=card.file_diff, rubric=a_rubric)`. Return `_verdict_from_judge(verdict, rubric_id)` if verdict is not None; return a fail ReviewerVerdict if verdict is None (judge_run returned "skipped").
    6. Handle edge cases: run_turn budget exceeded (BudgetExceededError from voss_runtime.exceptions) — return fail verdict with notes="A ran out of budget".

    The information isolation guarantee for A is: fresh EpisodicMemory per call, fresh session_id, task prompt derived from original_idea only (not EM AC). A does NOT see EM narrative — the REVIEWER_A_ROLE_PROMPT anchors to original_idea.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.board.reviewer_a import ReviewerA, REVIEWER_A_ROLE_PROMPT; print('import ok')"</automated>
  </verify>
  <acceptance_criteria>
    - voss/harness/board/reviewer_a.py exists and imports cleanly
    - ReviewerA.__init__ accepts provider, model, cwd, renderer, base_gate as keyword-only arguments
    - ReviewerA.review is async def and returns ReviewerVerdict
    - EpisodicMemory(capacity=20) is constructed INSIDE review(), not in __init__
    - uuid.uuid4() generates a fresh session_id per review() call
    - _reviewer_a_task references original_idea (the card's human idea), not EM AC/DoD
    - _verdict_from_judge translates Verdict to ReviewerVerdict with source="A", tier="strong"
    - _verdict_from_test_exit produces conf=1.0/verdict="pass" for exit 0, conf=0.0/verdict="fail" for non-zero
    - reviewer_a.py imports from voss.eval.judge (judge_run), voss.harness.agent (run_turn), voss.harness.team (gate_for_role)
    - reviewer_a.py does NOT modify verdict.py
  </acceptance_criteria>
  <done>ReviewerA class importable, implements Reviewer Protocol via run_turn with fresh memory, handles code-card (test exit) and AI-card (judge_run) paths.</done>
</task>

<task type="auto">
  <name>Task 2: Turn RED test_reviewer_a.py scaffolds GREEN</name>
  <files>tests/harness/board/test_reviewer_a.py</files>
  <read_first>
    - tests/harness/board/test_reviewer_a.py (current xfail scaffolds from O4-01)
    - voss/harness/board/reviewer_a.py (just-created implementation from Task 1)
    - voss/harness/board/verdict.py (ReviewerVerdict constructor)
    - voss/harness/board/machine.py (Card constructor — needed for test cards)
    - tests/harness/test_agent_integration.py (FakeProvider pattern for run_turn-based tests)
    - tests/eval/test_judge_verdict.py (FakeJudgeProvider pattern)
    - voss_runtime/providers/base.py (ProviderResponse fields)
    - voss/harness/agent.py (run_turn return type + Plan schema — needed to script fake provider responses)
    - voss/harness/permissions.py (PermissionGate constructor for test setup)
    - voss/harness/render.py (NullRenderer or PlainRenderer for test setup)
  </read_first>
  <action>
    Rewrite `tests/harness/board/test_reviewer_a.py` — replace xfail scaffolds with real test implementations. Remove `@pytest.mark.xfail(strict=True)` decorators. Keep all 5 function names unchanged.

    Create a `FakeReviewerAProvider` class that:
    - Scripts responses for run_turn's multi-turn agent loop. run_turn calls provider.complete() multiple times (planning call, tool calls). The fake must return a Plan-shaped response on the first call (the planning phase) and then handle subsequent tool-call responses.
    - Read how FakeProvider in tests/harness/test_agent_integration.py handles this — it returns a Plan with tool_calls on the first complete() and then handles the follow-up calls.
    - Records `self.calls: list[dict]` for inspection.
    - For AI-card tests: the fake must also handle the judge_run call (separate from run_turn). Use FakeJudgeProvider pattern for this.

    Create helper fixtures: `_make_code_card(...)` and `_make_ai_card(...)` that construct Card instances with appropriate domain fields.

    **test_a_uses_original_idea (ORVW-01):**
    Construct a ReviewerA. Call review(code_card). Inspect provider.calls to verify the task prompt sent to run_turn contains the card's original_idea text and does NOT contain "EM", "AC", "DoD", "engineering manager", or any EM-narrative marker. The task prompt is the first message's content in the first provider.complete() call.

    **test_a_authors_test_file (ORVW-02):**
    Construct a ReviewerA with a FakeProvider that scripts: Plan with a shell_run tool call returning "[exit 0]" output. Call review(code_card). Assert returned verdict.verdict == "pass" and verdict.conf == 1.0 and verdict.source == "A". Also test the fail path: "[exit 1]" produces verdict="fail" and conf=0.0.

    **test_a_ai_card_eval (ORVW-03):**
    Construct a ReviewerA with a FakeProvider that scripts run_turn completing with a rubric, plus a FakeJudgeProvider for the judge_run call. Call review(ai_card). Assert returned verdict translates from Verdict(verdict="pass", confidence=0.85, rationale="good") to ReviewerVerdict with conf=0.85, source="A", tier="strong", verdict="pass".

    **test_a_memory_fresh_per_card (ORVW-08):**
    Construct a ReviewerA. Call review(card_1) then review(card_2) with a recording FakeProvider. For the second call's first provider.complete() invocation, assert the messages list does NOT contain any text from card_1's original_idea or artifact. This proves EpisodicMemory is fresh per call.

    **test_a_implements_protocol (ORVW-09):**
    Import ReviewerA and Reviewer. Construct a ReviewerA instance. Assert isinstance(a, Reviewer) or structural Protocol conformance check.

    All tests are `async def`. Use `tmp_path` (pytest fixture) for cwd. Use NullRenderer for renderer. Construct a minimal PermissionGate for base_gate.

    NOTE: run_turn is a complex async function. These tests may need to mock run_turn itself (via monkeypatch or dependency injection) rather than trying to script the full agent loop via a fake provider. Read how test_agent_integration.py handles this. If run_turn is too complex to fake through the provider alone, mock `reviewer_a._run_turn_wrapper` or inject a callable. The key is: test the ReviewerA CONTRACT (idea in, verdict out, fresh memory), not the internals of run_turn.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_reviewer_a.py -x -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - All 5 tests in test_reviewer_a.py pass (0 xfail, 0 failures)
    - test_a_uses_original_idea asserts original_idea is in the task prompt AND EM-narrative strings are absent
    - test_a_authors_test_file exercises the shell_run exit-code-to-verdict path for both pass (exit 0) and fail (exit 1)
    - test_a_ai_card_eval exercises the judge_run Verdict-to-ReviewerVerdict translation path
    - test_a_memory_fresh_per_card proves sequential review() calls have isolated memory (card_2 messages do not contain card_1 text)
    - test_a_implements_protocol verifies ReviewerA is a Reviewer Protocol instance
    - Existing tests outside tests/harness/board/ show zero regressions
  </acceptance_criteria>
  <done>5 tests GREEN covering ORVW-01..03, ORVW-08, ORVW-09 for Reviewer-A. Bar-from-idea, test authoring, AI eval gate, memory isolation, and Protocol conformance all verified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| run_turn tool execution | A uses fs_write + shell_run — scoped by gate_for_role permission cap |
| judge_run LLM call | A delegates AI-card judgment to judge_run — same trust as M5 eval |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O4-05 | Elevation of Privilege | reviewer_a.py run_turn | mitigate | gate_for_role caps A's permissions via SubagentSpec (mode, tools); A cannot exceed base_gate |
| T-O4-06 | Information Disclosure | reviewer_a.py EpisodicMemory | mitigate | EpisodicMemory(capacity=20) created inside review(), not __init__; fresh session_id per call prevents cross-card bleed |
| T-O4-07 | Spoofing | reviewer_a.py verdict.source | mitigate | _verdict_from_judge and _verdict_from_test_exit hardcode source="A"; run_turn output does not control source |
| T-O4-SC | Tampering | npm/pip installs | accept | O4 installs zero new packages |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/test_reviewer_a.py -x -q` — 5 passed
- `.venv/bin/python -c "from voss.harness.board.reviewer_a import ReviewerA"` — exit 0
- `grep -c "EpisodicMemory" voss/harness/board/reviewer_a.py` — at least 1 (inside review() body)
- `grep -c "uuid.uuid4" voss/harness/board/reviewer_a.py` — at least 1 (fresh session_id)
- `git diff --name-only voss/harness/board/verdict.py` — empty (verdict.py unmodified)
</verification>

<success_criteria>
- ReviewerA implements the Reviewer Protocol via run_turn + fresh EpisodicMemory
- Code-card path: test file authored + shell_run exit code = verdict
- AI-card path: rubric authored + judge_run Verdict translated to ReviewerVerdict
- EpisodicMemory created per review() call (no cross-card bleed)
- Original idea is the anchor (not EM AC/DoD)
- 5/5 tests pass, 0 xfail
</success_criteria>

<output>
Create `.planning/phases/O4-reviewer-ab-split/O4-03-SUMMARY.md` when done
</output>
