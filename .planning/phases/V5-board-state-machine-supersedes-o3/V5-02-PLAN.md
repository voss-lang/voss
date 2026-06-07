---
phase: V5-board-state-machine-supersedes-o3
plan: 02
type: execute
wave: 2
depends_on: [V5-01]
files_modified:
  - voss/harness/board/machine.py
autonomous: true
requirements: [VBOARD-03, VBOARD-07]
must_haves:
  truths:
    - "A Card carries idea/role/acceptance_criteria/verification_requirement with '' defaults; existing O3 construction still works"
    - "card_status(card) returns the card's column; card_budget(envelope) returns (spent, limit)"
    - "move(card,'Done') on a Board with reviewer=None raises BoardGateError carrying 'no-reviewer' in failing_clauses; a valid reviewer permits Done"
    - "The InReview→Done transition still appends exactly one transitions[] entry per move (no double-append)"
  artifacts:
    - path: "voss/harness/board/machine.py"
      provides: "Card with four additive string fields + card_status/card_budget module helpers + self-Done independence guard in Board.move"
      contains: "def card_status"
  key_links:
    - from: "voss.harness.board.machine.card_status / card_budget"
      to: "tests/harness/board/test_card_fields_v5.py"
      via: "module-level helper functions imported by the RED scaffold"
      pattern: "card_status|card_budget"
    - from: "voss.harness.board.machine.Board.move"
      to: "BoardGateError(failing_clauses=['no-reviewer'])"
      via: "pre-gate guard when to=='Done' and self._reviewer is None"
      pattern: "no-reviewer"
---

<objective>
Implement the VBOARD-03 Card field completeness and the VBOARD-07 self-Done independence guard in `voss/harness/board/machine.py`. This greens the two machine-facing RED scaffolds written in V5-01 (`test_card_fields_v5.py`, `test_self_done_guard.py`).

Purpose: Close two of the three O3→PRD gaps in the shipped board state machine — the full Card field set (status/budget derived, not stored) and the guarantee that a card cannot reach Done without an independent reviewer verdict.

Output: `machine.py` with four additive `Card` fields, the `card_status` / `card_budget` module-level helpers, and the pre-gate `no-reviewer` guard in `Board.move`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-SPEC.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-RESEARCH.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-PATTERNS.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-01-PLAN.md

<interfaces>
<!-- The EXACT symbols the V5-01 RED scaffold imports. Implement these names/signatures verbatim so the scaffold goes GREEN. -->

Card (voss/harness/board/machine.py) — current fields PLUS four additive defaults appended after eval_threshold:
  node_id: str ; column: Column ; risk_tier: RiskTier ; retry_count: int ; deadline: float
  scope: Optional[TeamRoleScope] = None ; artifact: Optional[object] = None ; eval_threshold: float = 1.0
  idea: str = "" ; role: str = "" ; acceptance_criteria: str = "" ; verification_requirement: str = ""

Module-level helpers (NOT @property — slots=True interaction risk):
  def card_status(card: "Card") -> str          # returns card.column
  def card_budget(node_envelope: dict) -> tuple[int, int]   # (envelope.get("spent",0), envelope.get("limit",0))

Self-Done guard contract: Board.move(card, to="Done") when self._reviewer is None must raise
  BoardGateError("Done requires an independent reviewer", failing_clauses=["no-reviewer"])
  after emitting exactly one _append_delta(..., outcome="refused", failing_clauses=["no-reviewer"]).

BoardGateError (voss/harness/board/errors.py): __init__(self, reason, failing_clauses=None); exposes .failing_clauses list.
_append_delta signature (machine.py): (card, *, from_col, to_col, outcome, failing_clauses=None, reason=None, verdict_snapshot=None) -> None
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Card field completeness + card_status / card_budget helpers (VBOARD-03)</name>
  <files>voss/harness/board/machine.py</files>
  <read_first>
    - voss/harness/board/machine.py lines 84-97 (current Card def; `eval_threshold: float = 1.0` at line 97 is the last defaulted field — new fields append AFTER it)
    - V5-PATTERNS.md §"voss/harness/board/machine.py — Card dataclass extension (VBOARD-03)" (exact field block + helper signatures + the "no @property" constraint)
    - V5-RESEARCH.md §"Research Focus 2: Card Field Additions" (all four construction sites enumerated as safe: machine.py spawn_card + three dataclasses.replace sites; `""` default rationale)
    - tests/harness/board/test_card_fields_v5.py (the RED scaffold this task greens — read TestCardFieldsV5 / TestCardStatus / TestCardBudget to confirm the exact asserted defaults and helper return shapes)
  </read_first>
  <behavior>
    - Card(node_id="n1", column="Backlog", risk_tier="med", retry_count=0, deadline=999.0) → idea=="" and role=="" and acceptance_criteria=="" and verification_requirement=="".
    - Assigning card.idea = "x" raises dataclasses.FrozenInstanceError (frozen invariant preserved).
    - Card(..., idea="test idea") then dataclasses.replace(card, column="Planned") → idea carries through as "test idea".
    - card_status(Card(...column="InProgress"...)) == "InProgress".
    - card_budget({"spent": 100, "limit": 1000}) == (100, 1000); card_budget({}) == (0, 0).
  </behavior>
  <action>
    Append four additive string fields to the `Card` frozen dataclass (keep `@dataclass(frozen=True, slots=True)`), placed AFTER `eval_threshold: float = 1.0`: `idea: str = ""`, `role: str = ""`, `acceptance_criteria: str = ""`, `verification_requirement: str = ""`. Do NOT add `status` or `budget` as stored fields (sync hazard — they are derived). Then add two module-level functions immediately after the `Card` class body (NOT `@property`, to avoid the `slots=True` interaction documented in V5-RESEARCH Pitfall 1): `card_status(card)` returning `card.column`, and `card_budget(node_envelope)` returning `(node_envelope.get("spent", 0), node_envelope.get("limit", 0))`. Match the existing `""`-default string convention (not `Optional[...] = None`). Leave all four existing construction sites (spawn_card + the three `dataclasses.replace` calls) untouched — additive fields default correctly.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py -x -q --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `test_card_fields_v5.py` (TestCardFieldsV5, TestCardStatus, TestCardBudget) is GREEN: exit 0.
    - `grep -n "idea: str\|role: str\|acceptance_criteria: str\|verification_requirement: str" voss/harness/board/machine.py` shows all four new fields with `= ""` defaults.
    - `grep -n "def card_status\|def card_budget" voss/harness/board/machine.py` shows both module-level helpers (NOT decorated with `@property`).
    - `grep -n "status: \|budget: " voss/harness/board/machine.py` shows NO new stored `status`/`budget` field on Card.
    - Back-compat regression: `.venv/bin/python -m pytest tests/harness/board/test_card_node_wiring.py tests/harness/board/test_stub_full_lifecycle.py -q` stays GREEN.
  </acceptance_criteria>
  <done>The four additive Card fields and the card_status/card_budget helpers exist with the exact V5-01 signatures; test_card_fields_v5.py is GREEN; existing construction-path tests still pass; Card stays frozen with no stored status/budget field.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Self-Done independence guard in Board.move (VBOARD-07)</name>
  <files>voss/harness/board/machine.py</files>
  <read_first>
    - voss/harness/board/machine.py lines 350-376 (Board.move: unknown-column check ~358, WIP check, then `transition = (card.column, to)` at line 376 — the guard inserts BEFORE line 376)
    - voss/harness/board/machine.py lines 510-540 (`_append_delta` signature — keyword-only from_col/to_col/outcome/failing_clauses)
    - voss/harness/board/machine.py line 260 (`self._reviewer = reviewer if reviewer is not None else reviewer_b` — NOTE: a Board built with reviewer=None still has a non-None _reviewer because it defaults to reviewer_b; see action for how the guard distinguishes the no-injected-reviewer case)
    - voss/harness/board/errors.py lines 26-36 (BoardGateError(reason, failing_clauses=None); .failing_clauses list)
    - V5-PATTERNS.md §"voss/harness/board/machine.py — Self-Done independence guard (VBOARD-07)" (exact insertion site, the refused-delta-then-raise mirror of the WIP pattern, the single-_append_delta rule)
    - V5-RESEARCH.md §"Research Focus 1: Self-Done Independence Guard" and §"Common Pitfalls" Pitfall 2 (one _append_delta per refused move — do NOT double-append)
    - tests/harness/board/test_self_done_guard.py (the RED scaffold this task greens — confirm test_reviewer_none_raises_board_gate_error expects "no-reviewer" in exc.value.failing_clauses, and test_valid_reviewer_allows_done must stay GREEN)
  </read_first>
  <behavior>
    - A Board constructed so that no independent reviewer was injected, driven to InReview, then move(card, to="Done") → raises BoardGateError with "no-reviewer" in failing_clauses.
    - The refused Done move appends exactly ONE transitions[] entry (outcome="refused", failing_clauses=["no-reviewer"]) — not zero, not two.
    - A Board with DeterministicReviewerStub(conf=0.99, verdict="pass"), driven to InReview with a passing artifact, move(card, to="Done") → returns a Card with column=="Done" (positive path unbroken).
    - inspect.signature(board.move) has NO `verdict` parameter (structural no-injection tripwire stays true).
  </behavior>
  <action>
    Insert the VBOARD-07 independence guard in `Board.move` between the WIP enforcement block and the `transition = (card.column, to)` line (~line 376), mirroring the existing WIP refused-delta-then-raise pattern. The guard fires when `to == "Done"` and there is no independent reviewer injected. CRITICAL DISTINCTION: `self._reviewer` is defaulted to `reviewer_b` at __init__ (line 260) when the caller passes `reviewer=None`, so a bare `self._reviewer is None` check will not fire. Determine the actual "no independent reviewer was injected" condition by reading the __init__ wiring (lines 255-262): the guard must detect the case the V5-01 test drives (a Board built via `Board.from_team_config(..., reviewer=None, ...)`). Track the injected reviewer explicitly — store whether an external reviewer was supplied at __init__ (e.g. a `self._reviewer_injected` boolean set from the constructor's `reviewer is not None`) and gate on that, OR gate on the same None-ness the test exercises after confirming what from_team_config forwards. Use whichever the test's `reviewer=None` path actually produces; the contract is that the test's no-reviewer Board fails closed. On the guard firing: call `self._append_delta(card, from_col=card.column, to_col=to, outcome="refused", failing_clauses=["no-reviewer"])` exactly once, then `raise BoardGateError("Done requires an independent reviewer", failing_clauses=["no-reviewer"])`. Do NOT insert after `GateContext` construction (would double-append). Do NOT add a `verdict` kwarg to `move`. Do NOT modify verdict.py or gates.py.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_self_done_guard.py -x -q --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `test_self_done_guard.py` is GREEN: test_reviewer_none_raises_board_gate_error, test_valid_reviewer_allows_done, and test_no_verdict_injection_path all pass (exit 0).
    - `grep -n "no-reviewer" voss/harness/board/machine.py` shows the guard emits `failing_clauses=["no-reviewer"]` in both the `_append_delta` call and the `BoardGateError`.
    - The guard appears textually BEFORE the `transition = (card.column, to)` line in `Board.move` (insertion-order check via `grep -n`).
    - Transition-count invariant intact: `.venv/bin/python -m pytest tests/harness/board/test_transition_count_invariant.py -q` stays GREEN (no double-append).
    - `inspect.signature` of `Board.move` has no `verdict` parameter (asserted by test_no_verdict_injection_path).
    - `git diff --name-only` shows NO change to voss/harness/board/verdict.py or gates.py.
  </acceptance_criteria>
  <done>Board.move raises BoardGateError("no-reviewer") for the no-injected-reviewer Done path with exactly one refused delta; the valid-reviewer Done path and the no-injection structural tripwire stay GREEN; verdict.py/gates.py untouched; transition-count invariant holds.</done>
</task>

</tasks>

<verification>
- Both machine-facing scaffolds green: `.venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py tests/harness/board/test_self_done_guard.py -q --tb=short` → exit 0.
- No regression on the shipped board surface beyond the known pre-existing failure: `.venv/bin/python -m pytest tests/harness/board/ -q --tb=line` shows the SAME single pre-existing failure baseline (`test_exit_reasons_is_sorted_superset_of_pre_o3`, fixed later in V5-04) plus `test_board_cli.py` still RED (greened by V5-03) — and NO previously-green test flips to red.
- Frozen-schema guard: `git diff --name-only` shows changes ONLY to voss/harness/board/machine.py (no session.py, session_tree.py, voss_runtime, verdict.py, gates.py).
</verification>

<success_criteria>
- VBOARD-03: Card carries idea/role/acceptance_criteria/verification_requirement (`""` defaults); card_status/card_budget helpers exist with the exact V5-01 signatures; status/budget are derived (not stored).
- VBOARD-07: move(card,"Done") without an injected independent reviewer raises BoardGateError("no-reviewer"); a valid reviewer permits Done; exactly one refused delta per blocked move.
- test_card_fields_v5.py and test_self_done_guard.py are GREEN; back-compat and transition-count invariants intact; only machine.py changed.
</success_criteria>

<output>
Create `.planning/phases/V5-board-state-machine-supersedes-o3/V5-02-SUMMARY.md` when done.
</output>
