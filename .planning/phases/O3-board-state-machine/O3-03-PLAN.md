---
phase: O3-board-state-machine
plan: 03
type: execute
wave: 3
depends_on:
  - O3-02
files_modified:
  - voss/harness/board/gates.py
  - voss/harness/board/stub.py
  - voss/harness/board/machine.py
  - tests/harness/board/test_gate_predicates_basic.py
  - tests/harness/board/test_dry_run_gate.py
  - tests/harness/board/test_artifact_only_confidence.py
  - tests/harness/board/test_risk_thresholds.py
  - tests/harness/board/test_stub.py
  - tests/harness/board/test_stub_full_lifecycle.py
autonomous: true
requirements:
  - OBRD-04
  - OBRD-05
  - OBRD-06
  - OBRD-07
user_setup: []
must_haves:
  truths:
    - "Gate registry is a frozen `dict[(Column,Column), tuple[Predicate, ...]]`."
    - "Each predicate has a stable `.name ∈ {\"conf\",\"tests\",\"eval\",\"scope\",\"budget\",\"retry\",\"timeout\"}`."
    - "`board.dry_run_gate(card, (from,to))` returns `(passed: bool, failing_clauses: list[str])` without mutating state."
    - "`Backlog→Planned` and `Planned→InProgress` NEVER invoke `reviewer.review`."
    - "`InProgress→InReview` invokes `reviewer.review` exactly once per move attempt."
    - "`DeterministicReviewerStub(conf=0.99, verdict=\"pass\")` runs Backlog→Planned→InProgress→InReview→Done."
    - "`Board.move` refused by a gate raises `BoardGateError` with `.reason` and `.failing_clauses`, AND emits an `outcome=\"refused\"` delta."
  artifacts:
    - path: "voss/harness/board/gates.py"
      provides: "Predicate Protocol, GateContext, 8 predicates with stable .name, Gates registry, confidence_required()"
      contains: "class Gates"
      min_lines: 200
    - path: "voss/harness/board/stub.py"
      provides: "DeterministicReviewerStub — O3 test reviewer"
      contains: "class DeterministicReviewerStub"
    - path: "voss/harness/board/machine.py"
      provides: "Board.move integrates gate evaluation; Board.dry_run_gate public; verdict_snapshot in passed deltas; predicate handoff site activated"
      contains: "def dry_run_gate"
  key_links:
    - from: "voss/harness/board/machine.py"
      to: "voss/harness/board/gates.py"
      via: "Gates.build_default + evaluate per transition"
      pattern: "from \\.gates import"
    - from: "voss/harness/board/gates.py"
      to: "ReviewerVerdict (verdict.py)"
      via: "conf_meets_p invokes reviewer.review and stores result on GateContext"
      pattern: "reviewer\\.review"
    - from: "voss/harness/board/stub.py"
      to: "verdict.Reviewer Protocol"
      via: "structural subtyping (.review method)"
      pattern: "def review"
---

<objective>
Activate the gate-predicate registry. Land `gates.py` (8 predicates with stable `.name` strings + `GateContext` + `Predicate` Protocol + `Gates` registry with the 7-transition default table + `confidence_required` static method). Wire `Board.move` to evaluate predicates in declared order. Add `Board.dry_run_gate` for non-destructive inspection. Land `stub.py` (`DeterministicReviewerStub`). Verify the artifact-only confidence invariant (reviewer never called for non-artifact transitions) and the risk-tier threshold lookup.

Purpose: This wave makes the cage actually gate. Before O3-03, the board accepts every transition that passes WIP. After O3-03, only transitions whose predicate tuple all evaluate `True` are accepted; refused transitions raise `BoardGateError` with stable clause names AND emit an `outcome="refused"` delta carrying `failing_clauses`. The reviewer is invoked structurally only where SPEC REQ-5 requires it.

Output: 2 new source files (`gates.py`, `stub.py`) + 1 source edit (`machine.py` activates the gate evaluation block) + 5 new test files covering OBRD-04, OBRD-05, OBRD-06 (acceptance), OBRD-07 (stub end-to-end).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/O3-board-state-machine/O3-SPEC.md
@.planning/phases/O3-board-state-machine/O3-CONTEXT.md
@.planning/phases/O3-board-state-machine/O3-RESEARCH.md
@.planning/phases/O3-board-state-machine/O3-01-PLAN.md
@.planning/phases/O3-board-state-machine/O3-02-PLAN.md
@voss/harness/board/machine.py
@voss/harness/board/verdict.py
@voss/harness/board/errors.py
@voss/harness/team.py

<interfaces>
<!-- Post-O3-02 surfaces -->

From voss/harness/board/machine.py:
```python
Column = Literal["Backlog","Planned","InProgress","InReview","Blocked","Done"]
RiskTier = Literal["low","med","high"]
_DEFAULT_RISK_THRESHOLDS = {"low": 0.60, "med": 0.80, "high": 0.95}
_TERMINAL_COLUMNS = frozenset({"Done","Blocked"})

@dataclass(frozen=True, slots=True)
class Card:
    node_id: str; column: Column; risk_tier: RiskTier; retry_count: int
    deadline: float; scope: Optional[TeamRoleScope] = None
    artifact: Optional[object] = None; eval_threshold: float = 1.0

class Board:
    def move(self, card: Card, to: Column) -> Card: ...
    # O3-02 contains a `# TODO(O3-03): wire gate registry` marker; this wave replaces it.
```

From voss/harness/board/verdict.py:
```python
@dataclass(frozen=True, slots=True)
class ReviewerVerdict:
    conf: float; source: Literal["A","B"]; tier: Literal["fast","strong"]
    verdict: Literal["pass","fail","block"]; notes: str; evidence_refs: tuple[str,...]

class Reviewer(Protocol):
    def review(self, card: object) -> ReviewerVerdict: ...
```

From voss/harness/team.py:
```python
@dataclass(frozen=True, slots=True)
class TeamRoleScope:
    globs: tuple[str, ...]
    def is_contained_in(self, other: TeamRoleScope | None) -> bool: ...
@dataclass(frozen=True, slots=True)
class TeamCeiling:
    budget_tokens: int | None; scope: TeamRoleScope | None; latency_seconds: int | None
```
</interfaces>

<pre_conditions>
- O3-02 shipped: `voss/harness/board/machine.py` has Board, Card, the `# TODO(O3-03)` marker, and tests pass.
- O3-01 shipped: verdict.py, errors.py exist; `SessionTreeNode.transitions` field exists.
- Reviewer Protocol from verdict.py is importable (test does this in CI already).
</pre_conditions>

<open-question id="scope-clean-naming">
Per O3-RESEARCH.md §4 R-08: `scope_ok` and `scope_clean` both expose `.name == "scope"` — SPEC L114 lists exactly 7 stable names, and the dry-run consumer should not distinguish "scope" vs "scope.clean".

**Locked recommendation:** keep both predicates with shared `name="scope"`. Document the design choice in a module-level docstring; the dry_run_gate output coalesces duplicate clause names via `list(dict.fromkeys(failing))` or similar order-preserving dedup. SPEC's 7-name enumeration is the contract.

**Fallback:** rename `scope_clean` to expose `name="scope_clean"` (8 names total). Only if a checker rejects the dedup behavior.

**Escalate to checkpoint:decision** only if a SPEC reviewer flags the dedup as scope creep.
</open-question>

<open-question id="reviewer-cardinality">
Per O3-RESEARCH.md §11 Open Question 3: when `InProgress → InReview` evaluates predicates `(budget_ok, scope_ok, conf_meets_p)`, does `conf_meets_p` invoke `reviewer.review(card)` once per evaluation, or is the verdict cached?

**Locked recommendation:** call `reviewer.review(card)` once per `move` attempt; cache the result on `GateContext.verdict` for the duration of this single evaluation pass; do NOT cache across multiple move attempts (artifact may change between attempts). This means: within a single `Board.move(card, to)` call, the reviewer is invoked at most once even if multiple predicates need it.

**Fallback:** call per-predicate (worst-case 2 calls for `(budget, scope, conf, conf)`-style stacks). Wasteful but harmless.

**Escalate to checkpoint:decision** only if an O4 reviewer impl proves to be non-idempotent (currently impossible — Reviewer is a structural Protocol and tests inject deterministic stubs).
</open-question>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: gates.py — Predicate Protocol, GateContext, 8 predicates, Gates registry</name>
  <files>
    voss/harness/board/gates.py,
    tests/harness/board/test_gate_predicates_basic.py,
    tests/harness/board/test_risk_thresholds.py
  </files>
  <behavior>
    - Test 1 (test_gate_predicates_basic.py): `_PREDICATE_NAMES == ("conf","tests","eval","scope","budget","retry","timeout")` — exactly 7 stable names from SPEC L114.
    - Test 2 (test_gate_predicates_basic.py): each of the 8 predicate classes (`scope_ok`, `scope_clean`, `budget_ok`, `conf_meets_p`, `tests_pass`, `eval_meets_threshold`, `retry_under_ceiling`, `not_timed_out`) has a `.name` attribute that is a string and is in `_PREDICATE_NAMES`. Two predicates share `.name == "scope"` (intentional per §4).
    - Test 3 (test_gate_predicates_basic.py): `Gates.build_default(team_ceiling, team_p_overrides, retry_ceiling, reserve)` returns a `Gates` instance whose `.transitions` dict has exactly 4 keys (the 4 forward-progression transitions; `→Blocked` is forced not gated; `InReview→InProgress` critic-loop is also unguarded). Each value is a tuple of predicate instances in declared order (budget/scope before conf/tests).
    - Test 4 (test_gate_predicates_basic.py): `Gates.confidence_required(("InProgress","InReview")) is True`; `Gates.confidence_required(("InReview","Done")) is True`; `Gates.confidence_required(("Backlog","Planned")) is False`; `Gates.confidence_required(("Planned","InProgress")) is False`.
    - Test 5 (test_risk_thresholds.py): `_DEFAULT_RISK_THRESHOLDS == {"low": 0.60, "med": 0.80, "high": 0.95}` (imported from machine.py only); a high-tier card with verdict `conf=0.94` → `conf_meets_p.evaluate(...)` returns `False`; same card with `conf=0.95` → `True`. Team override `p_overrides={"high": 0.90}` lowers the threshold; card with conf=0.91 now passes.
    - Test 6 (test_risk_thresholds.py): single-import-site invariant — `grep -rn "_DEFAULT_RISK_THRESHOLDS" voss/` returns exactly ONE definition (in `machine.py`). `gates.py` IMPORTS it (`from .machine import _DEFAULT_RISK_THRESHOLDS`) rather than redefining.
  </behavior>
  <action>
    Land `voss/harness/board/gates.py` per O3-RESEARCH.md §4. The file structure:

    1. Module docstring citing SPEC L114 + L116 + L115 (artifact-only confidence).

    2. Imports:
       ```python
       from __future__ import annotations
       from dataclasses import dataclass, field
       from typing import Callable, Optional, Protocol

       from voss.harness.team import TeamCeiling, TeamRoleScope
       from .machine import Card, Column, RiskTier, _DEFAULT_RISK_THRESHOLDS
       from .verdict import Reviewer, ReviewerVerdict
       ```
       The `_DEFAULT_RISK_THRESHOLDS` import (NOT redefinition) is the OBRD-06 single-source invariant.

    3. Module-level frozen tuple — SPEC L114 stable names:
       ```python
       _PREDICATE_NAMES: tuple[str, ...] = ("conf", "tests", "eval", "scope", "budget", "retry", "timeout")
       ```

    4. `Predicate` Protocol:
       ```python
       class Predicate(Protocol):
           name: str
           def evaluate(self, ctx: "GateContext") -> bool: ...
       ```

    5. `GateContext` frozen dataclass (mutable `verdict` slot for reviewer caching per OQ above):
       ```python
       @dataclass
       class GateContext:
           card: Card
           node_envelope: dict             # node.envelope; {"limit": int, "spent": int}
           team_ceiling: TeamCeiling
           team_p_overrides: dict          # dict[RiskTier, float]
           retry_ceiling: int
           reserve: int
           now: float
           reviewer: Optional[Reviewer] = None
           verdict: Optional[ReviewerVerdict] = None    # populated by conf_meets_p on first call
       ```
       Note: NOT frozen — the `verdict` slot is intentionally mutable so `conf_meets_p` can populate it once per move attempt and downstream predicates in the same tuple (currently none) can read it.

    6. The 8 predicate classes per O3-RESEARCH.md §4 pseudocode. Concrete shapes:
       ```python
       class scope_ok:
           name = "scope"
           def evaluate(self, ctx: GateContext) -> bool:
               if ctx.card.scope is None or ctx.team_ceiling.scope is None: return True
               return ctx.card.scope.is_contained_in(ctx.team_ceiling.scope)

       class budget_ok:
           name = "budget"
           def evaluate(self, ctx: GateContext) -> bool:
               env = ctx.node_envelope
               return env["spent"] < env["limit"] - ctx.reserve

       class conf_meets_p:
           name = "conf"
           def evaluate(self, ctx: GateContext) -> bool:
               if ctx.reviewer is None: return False
               if ctx.verdict is None:
                   ctx.verdict = ctx.reviewer.review(ctx.card)   # AT MOST ONCE per move attempt
               threshold = ctx.team_p_overrides.get(ctx.card.risk_tier,
                                                    _DEFAULT_RISK_THRESHOLDS[ctx.card.risk_tier])
               return ctx.verdict.conf >= threshold

       class tests_pass:
           name = "tests"
           def evaluate(self, ctx: GateContext) -> bool:
               return bool(getattr(ctx.card.artifact, "tests_passed", False))

       class eval_meets_threshold:
           name = "eval"
           def evaluate(self, ctx: GateContext) -> bool:
               score = getattr(ctx.card.artifact, "eval_score", 0.0)
               return float(score) >= ctx.card.eval_threshold

       class scope_clean:
           name = "scope"   # intentional dedup with scope_ok (see module docstring)
           def evaluate(self, ctx: GateContext) -> bool:
               if ctx.card.scope is not None and ctx.team_ceiling.scope is not None:
                   if not ctx.card.scope.is_contained_in(ctx.team_ceiling.scope): return False
               return not bool(getattr(ctx.card.artifact, "scope_violations", ()))

       class retry_under_ceiling:
           name = "retry"
           def evaluate(self, ctx: GateContext) -> bool:
               return ctx.card.retry_count <= ctx.retry_ceiling

       class not_timed_out:
           name = "timeout"
           def evaluate(self, ctx: GateContext) -> bool:
               return ctx.now < ctx.card.deadline
       ```

    7. `Gates` dataclass + `build_default` + `confidence_required`:
       ```python
       @dataclass(frozen=True, slots=True)
       class Gates:
           transitions: dict   # dict[tuple[Column, Column], tuple[Predicate, ...]]

           @staticmethod
           def confidence_required(transition: tuple[Column, Column]) -> bool:
               return transition in {("InProgress", "InReview"), ("InReview", "Done")}

           @classmethod
           def build_default(cls) -> "Gates":
               # Predicate ordering: cheap (budget/scope/retry/timeout) → expensive (conf/tests/eval).
               # Per OBRD-05 (SPEC L115): conf_meets_p ONLY in artifact transitions.
               return cls(transitions={
                   ("Backlog", "Planned"):   (scope_ok(),),
                   ("Planned", "InProgress"): (budget_ok(), scope_ok()),
                   ("InProgress", "InReview"): (budget_ok(), scope_ok(), conf_meets_p()),
                   ("InReview", "Done"):     (scope_clean(), conf_meets_p(), tests_pass()),   # code path
                   # AI path Done variant — see note below
               })
       ```
       **Done-variant decision:** SPEC REQ-4 distinguishes `InReview→Done(code)` from `InReview→Done(ai)`. For O3-03, the default registry maps `("InReview","Done")` to the **code** path (`tests_pass`). The AI path (`eval_meets_threshold`) is plumbed via `Gates.build_default(ai_card_predicate=eval_meets_threshold)` or by inspecting `card.artifact` at evaluation time. **Recommend:** dynamically swap `tests_pass` for `eval_meets_threshold` inside `Board.move` based on `card.artifact` having an `eval_score` attribute vs `tests_passed` attribute. Document this as a sub-decision in the docstring; if O5 adds an explicit `card.kind == "ai"` flag, the swap moves there.
       Actually simpler: ship both variants in the registry under tagged keys and have `Board.move` pick by inspecting card.artifact. Concrete plan:
       ```python
       _CODE_DONE_PREDICATES = (scope_clean(), conf_meets_p(), tests_pass())
       _AI_DONE_PREDICATES   = (scope_clean(), conf_meets_p(), eval_meets_threshold())
       ```
       And `Gates.transitions[("InReview","Done")]` is set to `_CODE_DONE_PREDICATES` by default; `Board.move` introspects `card.artifact` to choose: if `hasattr(artifact, "eval_score") and not hasattr(artifact, "tests_passed")`, use AI predicates; else code. Test both variants in Task 2.

    8. Tests as listed in `<behavior>`. For Test 6, use `subprocess.run(["grep","-rn","_DEFAULT_RISK_THRESHOLDS","voss/"])` and assert the output has exactly one `=` assignment line (other lines may be `from .machine import _DEFAULT_RISK_THRESHOLDS` — count those separately and assert one definition + ≥1 import).

    depends_on_o2_symbol: `TeamCeiling`, `TeamRoleScope` (only — gates.py doesn't read BoardSpec directly).
    locked_decisions_touched: 7 stable predicate names (scope dedupe), Predicate ordering (cheap→expensive), conf_meets_p reviewer-cardinality (at most once per move), `_DEFAULT_RISK_THRESHOLDS` imported not redefined, code-vs-AI Done variant lookup by artifact attribute.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_gate_predicates_basic.py tests/harness/board/test_risk_thresholds.py -x -q</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.gates import _PREDICATE_NAMES; assert _PREDICATE_NAMES == ('conf','tests','eval','scope','budget','retry','timeout'), _PREDICATE_NAMES"</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.gates import scope_ok, scope_clean, budget_ok, conf_meets_p, tests_pass, eval_meets_threshold, retry_under_ceiling, not_timed_out, _PREDICATE_NAMES; names={scope_ok.name, scope_clean.name, budget_ok.name, conf_meets_p.name, tests_pass.name, eval_meets_threshold.name, retry_under_ceiling.name, not_timed_out.name}; assert names == set(_PREDICATE_NAMES), names"</automated>
    <automated>test "$(grep -rn '_DEFAULT_RISK_THRESHOLDS *= *{' voss/ | grep -v '^#' | wc -l | tr -d ' ')" = "1"</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.gates import Gates; g=Gates.build_default(); assert Gates.confidence_required(('InProgress','InReview')); assert Gates.confidence_required(('InReview','Done')); assert not Gates.confidence_required(('Backlog','Planned')); assert not Gates.confidence_required(('Planned','InProgress'))"</automated>
  </verify>
  <done>
    `gates.py` ships with 8 predicates carrying 7 stable names; `Gates.build_default` registers the 4 forward transitions; `confidence_required` returns True only for the 2 artifact transitions; `_DEFAULT_RISK_THRESHOLDS` remains single-source; threshold tests green.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire Board.move → gate evaluation + dry_run_gate + DeterministicReviewerStub</name>
  <files>
    voss/harness/board/machine.py,
    voss/harness/board/stub.py,
    voss/harness/board/__init__.py,
    tests/harness/board/test_dry_run_gate.py,
    tests/harness/board/test_artifact_only_confidence.py,
    tests/harness/board/test_stub.py,
    tests/harness/board/test_stub_full_lifecycle.py
  </files>
  <behavior>
    - Test 1 (test_stub.py): `DeterministicReviewerStub(conf=0.99, verdict="pass")` is structurally a `Reviewer` (has `review(card)`); calling `stub.review(any_card)` returns a `ReviewerVerdict` with the configured `conf` and `verdict`, default `tier="strong"`, `source="B"`, `notes="(deterministic stub)"`, `evidence_refs=()`.
    - Test 2 (test_dry_run_gate.py): with a passing artifact and conf=0.99 stub, `board.dry_run_gate(card, ("InProgress","InReview"))` returns `(True, [])`. With conf=0.5 stub and high-risk card: returns `(False, ["conf"])`. With conf=0.99 stub but `card.artifact.scope_violations=("/etc",)` and dest `Done`: returns `(False, ["scope"])`. `dry_run_gate` MUST NOT mutate `board._cards`, MUST NOT append to `node.transitions`, MUST NOT change `card.column`.
    - Test 3 (test_artifact_only_confidence.py): instantiate a `class RaisingReviewer: def review(self, card): raise AssertionError("reviewer should not be invoked")`. Use it as `Board(reviewer=...)`. Spawn a card; `board.move(card, "Planned")` succeeds. `board.move(card_now_planned, "InProgress")` succeeds. `board.move(card_now_inprogress, "InReview")` raises the AssertionError from the reviewer (proves conf_meets_p IS invoked at the artifact transition).
    - Test 4 (test_stub_full_lifecycle.py): `DeterministicReviewerStub(conf=0.99, verdict="pass")` + passing artifact. Drive a card Backlog→Planned→InProgress→InReview→Done. Final `card.column == "Done"`. Inspect `manager.get_node(card.node_id).transitions`: 4 deltas, all `outcome="passed"`. The InReview→InReview and InReview→Done deltas should contain a non-null `verdict_snapshot` field (dict shape from `dataclasses.asdict(ReviewerVerdict)`); the Backlog→Planned and Planned→InProgress deltas should have `verdict_snapshot=None`.
    - Test 5 (test_dry_run_gate.py): refused move emits delta with `outcome="refused"` and `failing_clauses==["conf"]` (e.g.) — `Board.move` raises `BoardGateError(reason="gate refused", failing_clauses=["conf"])` AND the delta is on the node.
    - Test 6 (test_stub_full_lifecycle.py): a card with `artifact=SimpleNamespace(eval_score=0.95)` (no `tests_passed`) and `eval_threshold=0.9` drives Backlog→…→Done via the AI variant (eval_meets_threshold). A card with `artifact=SimpleNamespace(eval_score=0.5)` and `eval_threshold=0.9` REFUSES the Done transition with `failing_clauses=["eval"]`.
  </behavior>
  <action>
    Two source files + one source edit.

    1. `voss/harness/board/stub.py`:
       ```python
       """DeterministicReviewerStub — O3 test reviewer.

       Production code must NOT import this module. The O3-04 stress test enforces
       this via a repo-wide grep gate.
       """
       from __future__ import annotations
       from dataclasses import dataclass
       from .verdict import Reviewer, ReviewerVerdict


       @dataclass
       class DeterministicReviewerStub:
           conf: float = 0.99
           verdict: str = "pass"     # one of "pass" | "fail" | "block"
           tier: str = "strong"      # one of "fast" | "strong"
           source: str = "B"         # one of "A" | "B"

           def review(self, card: object) -> ReviewerVerdict:
               return ReviewerVerdict(
                   conf=self.conf,
                   source=self.source,         # type: ignore[arg-type]
                   tier=self.tier,             # type: ignore[arg-type]
                   verdict=self.verdict,       # type: ignore[arg-type]
                   notes="(deterministic stub)",
                   evidence_refs=(),
               )
       ```

    2. `voss/harness/board/__init__.py`: do NOT re-export `DeterministicReviewerStub`. Per O3-RESEARCH.md §3.7 it must remain test-only-import.

    3. `voss/harness/board/machine.py` edits:
       - Add import at top: `from .gates import Gates, GateContext, eval_meets_threshold, tests_pass, scope_clean, conf_meets_p, scope_ok, budget_ok, _PREDICATE_NAMES`.
       - Add `dataclasses.asdict` import.
       - In `Board.__init__`, store the gates registry:
         ```python
         self._gates = Gates.build_default()
         self._team_p_overrides: dict = {}  # populated from team_config.policy if present
         ```
       - In `Board.from_team_config`, before constructing the Board, derive `team_p_overrides` from `team_config.policy.p` if it's a mapping (`isinstance(p, dict)`); else `{}`. Pass into the Board constructor.
       - Replace the `# TODO(O3-03)` block in `move` with gate evaluation:
         ```python
         # 3. gate evaluation
         transition = (card.column, to)
         predicates = self._gates.transitions.get(transition)
         verdict_snapshot = None
         if predicates is not None:
             # AI-vs-code Done variant: swap tests_pass <-> eval_meets_threshold based on artifact
             if transition == ("InReview", "Done") and card.artifact is not None:
                 if hasattr(card.artifact, "eval_score") and not hasattr(card.artifact, "tests_passed"):
                     predicates = (scope_clean(), conf_meets_p(), eval_meets_threshold())
             node = self._manager.get_node(card.node_id)
             if node is None:
                 # defensive — should never happen post-spawn
                 raise BoardGateError("card node missing", failing_clauses=["scope"])
             ctx = GateContext(
                 card=card,
                 node_envelope=dict(node.envelope),
                 team_ceiling=self._team_ceiling,
                 team_p_overrides=dict(self._team_p_overrides),
                 retry_ceiling=self._cfg.retry_ceiling,
                 reserve=self._reserve,
                 now=self._clock(),
                 reviewer=self._reviewer,
             )
             failing: list[str] = []
             for p in predicates:
                 if not p.evaluate(ctx):
                     if p.name not in failing:   # dedup duplicate "scope" entries per OQ scope-clean-naming
                         failing.append(p.name)
             if ctx.verdict is not None:
                 verdict_snapshot = dataclasses.asdict(ctx.verdict)
             if failing:
                 self._append_delta(card, from_col=card.column, to_col=to,
                                    outcome="refused", failing_clauses=failing,
                                    verdict_snapshot=verdict_snapshot)
                 raise BoardGateError("gate refused", failing_clauses=failing)
         ```
       - Adjust the "passed" delta path to include the `verdict_snapshot` populated above.

       - Add `dry_run_gate`:
         ```python
         def dry_run_gate(self, card: Card, transition: tuple[Column, Column]) -> tuple[bool, list[str]]:
             """Non-destructive predicate evaluation. SPEC L114 acceptance.

             Returns (passed, failing_clauses). Never mutates board state, never
             appends to node.transitions, never invokes the reviewer if no
             confidence predicate is in the registry for `transition`.
             """
             predicates = self._gates.transitions.get(transition)
             if predicates is None:
                 return (True, [])
             # AI-vs-code Done variant — same logic as move
             if transition == ("InReview", "Done") and card.artifact is not None:
                 if hasattr(card.artifact, "eval_score") and not hasattr(card.artifact, "tests_passed"):
                     predicates = (scope_clean(), conf_meets_p(), eval_meets_threshold())
             node = self._manager.get_node(card.node_id)
             ctx = GateContext(
                 card=card,
                 node_envelope=dict(node.envelope) if node else {"limit": 0, "spent": 0},
                 team_ceiling=self._team_ceiling,
                 team_p_overrides=dict(self._team_p_overrides),
                 retry_ceiling=self._cfg.retry_ceiling,
                 reserve=self._reserve,
                 now=self._clock(),
                 reviewer=self._reviewer,
             )
             failing: list[str] = []
             for p in predicates:
                 if not p.evaluate(ctx):
                     if p.name not in failing:
                         failing.append(p.name)
             return (not failing, failing)
         ```

    4. Tests as listed in `<behavior>`. Use `conftest.tmp_recorder` + `build_test_team` + `DeterministicReviewerStub` everywhere. For Test 3 (artifact-only confidence), the `RaisingReviewer` must be defined inline in the test (it's not a generic fixture).

    5. **Production-import guard test** (small extra in `test_stub.py`): grep `voss/` excluding `voss/harness/board/stub.py` itself and tests, assert no production file imports `from .stub` or `from voss.harness.board.stub`. Use `subprocess.run(["grep","-rn","--include=*.py","voss.harness.board.stub","voss/"])` and assert output contains only stub.py itself (or is empty).

    depends_on_o2_symbol: same as Task 1 — no new O2 dependency.
    locked_decisions_touched: code-vs-AI Done variant by artifact-attribute introspection; reviewer cardinality at-most-once per move (verdict cached on GateContext); dedup duplicate "scope" entries in failing_clauses; verdict_snapshot is `dataclasses.asdict(ctx.verdict)` only when verdict was consulted; production must not import `stub`.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_dry_run_gate.py tests/harness/board/test_artifact_only_confidence.py tests/harness/board/test_stub.py tests/harness/board/test_stub_full_lifecycle.py -x -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/board/ -x -q</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.stub import DeterministicReviewerStub; from voss.harness.board.verdict import Reviewer; s=DeterministicReviewerStub(); v=s.review(None); assert v.notes == '(deterministic stub)' and v.conf == 0.99"</automated>
    <automated>test "$(grep -rn --include='*.py' 'voss.harness.board.stub\\|from .stub\\|from \\.\\.board\\.stub' voss/ | grep -v 'voss/harness/board/stub.py' | wc -l | tr -d ' ')" = "0"</automated>
    <automated>grep -c 'dataclasses.asdict' voss/harness/board/machine.py</automated>
    <automated>grep -c 'def dry_run_gate' voss/harness/board/machine.py</automated>
  </verify>
  <done>
    `Board.move` now evaluates the gate registry; refused transitions raise `BoardGateError(reason="gate refused", failing_clauses=[…])` and emit `outcome="refused"` deltas with `verdict_snapshot` populated if the reviewer was consulted; `dry_run_gate` is non-destructive; reviewer is NOT invoked for Backlog→Planned or Planned→InProgress (artifact-only confidence proven); DeterministicReviewerStub drives the full Backlog→Done lifecycle for both code and AI artifact variants; production code does not import the stub.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `GateContext.verdict` mutable slot ↔ Reviewer invocation cardinality | `verdict` is populated by `conf_meets_p.evaluate` at most once per `move` attempt. Cross-attempt caching is forbidden (artifact can change between attempts). |
| `Board.dry_run_gate` ↔ `Board.move` | Both share predicate-evaluation logic but `dry_run_gate` MUST NOT mutate. Test_dry_run_gate verifies state non-mutation. |
| Production code ↔ `voss/harness/board/stub.py` | Stub is test-only. Grep-gate in test_stub.py blocks any production import. |
| `card.artifact` duck-typing ↔ tests_pass / eval_meets_threshold / scope_clean predicates | Each predicate uses `getattr(artifact, attr, default)`; missing attribute → predicate evaluates False (safe-fail). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O3-03-01 | Spoofing | Adversarial reviewer returns `conf=1.0` for failing artifact | mitigate (partial) | At `→Done`: `tests_pass` (code) or `eval_meets_threshold` (AI) is an INDEPENDENT predicate; reviewer cannot override. Double-gate per SPEC REQ-4 acceptance. Full mitigation lands in O4 (Reviewer A vs B independence). |
| T-O3-03-02 | Tampering | `ReviewerVerdict` constructed outside the injected `Reviewer` | mitigate | Reviewer is constructor-injected at `from_team_config`; `_reviewer` is the only call site; `ReviewerVerdict` is `frozen=True, slots=True` (O3-01). |
| T-O3-03-03 | Information Disclosure | `verdict_snapshot` in transition delta contains reviewer-authored `notes` text on disk | mitigate | Field shape reserved in O3-01; redaction allowlist already covers `transitions`. Reviewer notes are reviewer-authored, not user-PII. |
| T-O3-03-04 | Repudiation | Refused gate produces no delta or wrong failing_clauses | mitigate | Test_dry_run_gate + test_transition_count_invariant (O3-02) gate. Dedup duplicate "scope" entries via `if p.name not in failing` — predictable output order. |
| T-O3-03-05 | Denial-of-Service | Reviewer.review is slow / blocks the move loop | accept | Wave 4 (`Board.tick`) does NOT block on reviewer; reviewer only invoked synchronously inside `move`. Slow reviewer → slow `move` call; caller's concern. O5 owns dispatch concurrency. |
| T-O3-03-06 | Elevation of Privilege | Test imports `DeterministicReviewerStub` and ships in production binary | mitigate | Production-import grep gate in test_stub.py. CI fails if any voss/ file outside tests imports `voss.harness.board.stub`. |
</threat_model>

<verification>
**Plan-level automated:**
- Full board suite: `.venv/bin/python -m pytest tests/harness/board/ -x -q`
- O1 substrate regression: `.venv/bin/python -m pytest tests/harness/test_session_tree.py tests/harness/test_session_redaction.py -x -q`
- Single-source-threshold grep: `grep -rn '_DEFAULT_RISK_THRESHOLDS *= *{' voss/ | wc -l == 1`
- Production-import guard grep: no production file imports stub.
- Verdict.py import-set still ⊆ {typing, dataclasses, __future__} (O3-01 invariant; this wave does not touch verdict.py).

**Manual review:**
- Spot-check `_append_delta` call sites in `Board.move` and `Board.dry_run_gate` — only ONE site should be inside `move` (`dry_run_gate` must not call it).
</verification>

<success_criteria>
- SPEC L114 acceptance: `dry_run_gate` returns failing clauses by stable name (`conf`, `tests`, `eval`, `scope`, `budget`, `retry`, `timeout`).
- SPEC L115 acceptance: reviewer never invoked for `Backlog→Planned` / `Planned→InProgress`.
- SPEC L116 acceptance: `_DEFAULT_RISK_THRESHOLDS` single source of truth.
- SPEC L118 acceptance: `DeterministicReviewerStub(conf=0.99, verdict="pass")` drives full lifecycle.
- Gate refused → BoardGateError raised + `outcome="refused"` delta emitted (audit invariant preserved).
- Code-vs-AI Done variant works (`tests_pass` vs `eval_meets_threshold` swapped by artifact introspection).
</success_criteria>

<output>
Create `.planning/phases/O3-board-state-machine/O3-03-SUMMARY.md` on completion. Include:
- Final predicate name set (paste `_PREDICATE_NAMES` literal).
- Reviewer-invocation cardinality test result (proves at-most-once per move).
- Note on the `dry_run_gate` non-mutation invariant.
- Any deviations from the AI-vs-code Done variant logic.
</output>
