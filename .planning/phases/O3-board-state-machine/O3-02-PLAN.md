---
phase: O3-board-state-machine
plan: 02
type: execute
wave: 2
depends_on:
  - O3-01
files_modified:
  - voss/harness/board/__init__.py
  - voss/harness/board/machine.py
  - tests/harness/board/conftest.py
  - tests/harness/board/test_card_node_wiring.py
  - tests/harness/board/test_board_factory.py
  - tests/harness/board/test_columns_and_unknown.py
  - tests/harness/board/test_wip_cap.py
  - tests/harness/board/test_transition_count_invariant.py
autonomous: true
requirements:
  - OBRD-01
  - OBRD-02
  - OBRD-03
  - OBRD-06
user_setup: []
must_haves:
  truths:
    - "`Board.from_team_config(team_config, recorder=manager, reviewer=stub, cwd=tmp)` returns a Board with an observable `board.root_node_id`."
    - "`board.spawn_card(risk_tier='med')` creates a card whose `manager.get_node(card.node_id)` returns a live `SessionTreeNode`."
    - "`Board.move(card, to='InProgress')` succeeds 3 times then raises `BoardWIPError` on the 4th (default `InProgress` cap = 3)."
    - "`Board.move(card, to='Foo')` raises `BoardGateError('unknown column: Foo')`."
    - "Every transition attempt (passed or refused) appends exactly one entry to `node.transitions`."
    - "`_DEFAULT_RISK_THRESHOLDS == {'low': 0.60, 'med': 0.80, 'high': 0.95}` and is referenced from a single import site."
  artifacts:
    - path: "voss/harness/board/machine.py"
      provides: "Board state machine, Card value-object, _BoardConfig adapter, BoardSpec reader, WIP enforcement, transition-delta emission"
      contains: "class Board"
      min_lines: 250
    - path: "tests/harness/board/conftest.py"
      provides: "Shared fixtures: tmp_recorder, _build_test_team, _artifact_passing/failing, FakeClock placeholder"
      contains: "def tmp_recorder"
  key_links:
    - from: "voss/harness/board/machine.py"
      to: "voss/harness/session_tree.SessionTreeManager.get_node"
      via: "Card.column read"
      pattern: "manager\\.get_node\\(.*\\.node_id"
    - from: "voss/harness/board/machine.py"
      to: "SessionTreeNode.transitions"
      via: "delta append on move"
      pattern: "\\.transitions\\.append"
    - from: "voss/harness/board/machine.py"
      to: "voss/harness/team.TeamConfig"
      via: "Board.from_team_config reads ceiling, board (BoardSpec)"
      pattern: "team_config\\.(ceiling|board)"
---

<objective>
Land the board state machine: `Card` frozen value-object, `Board` class with the 6-column model, WIP enforcement, `Board.from_team_config()` factory, `Board.spawn_card()`, `Board.move()`, the `_read_board_spec` adapter that consumes O2's opaque `BoardSpec.raw_items`, and the per-transition delta append onto `SessionTreeNode.transitions`. **No gate-predicate evaluation yet** (gates are O3-03) — `move` enforces only WIP + unknown-column rejection and appends the delta. Gate plumbing slot is reserved.

Purpose: This is the bones of the cage. Cards live on session-tree nodes (no parallel store). Multiple boards from the same `TeamConfig` are independent. The default WIP table is enforced. Every state transition emits exactly one delta — refused transitions included. The risk-threshold constant lives in one place, sourced from a `_DEFAULT_RISK_THRESHOLDS` module-level constant.

Output: `machine.py` (~250-300 lines) + 5 test files covering OBRD-01 / OBRD-02 / OBRD-03 / OBRD-06 acceptance checkboxes (SPEC L110-L113, L116, L123).
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
@voss/harness/session_tree.py
@voss/harness/team.py
@voss/ast_nodes.py
@voss/parser.py

<interfaces>
<!-- O3-01 surfaces (assumed present by precondition) -->

From voss/harness/board/__init__.py:
```python
from .verdict import ReviewerVerdict, Reviewer
from .errors import BoardError, BoardWIPError, BoardGateError, BoardTimeoutError
```

From voss/harness/board/errors.py:
```python
class BoardWIPError(BoardError):
    def __init__(self, column: str, cap: int) -> None: ...  # .column, .cap
class BoardGateError(BoardError):
    def __init__(self, reason: str, failing_clauses: list[str] | None = None) -> None: ...  # .reason, .failing_clauses
class BoardTimeoutError(BoardError):
    def __init__(self, reason: str) -> None: ...  # .reason
```

From voss/harness/session_tree.py (post-O3-01):
```python
@dataclass
class SessionTreeNode:
    id: str; root_id: str; parent_run_id: Optional[str]
    envelope: dict   # {"limit": int, "spent": int}
    terminal_state: Optional[dict]; created_at: str; ended_at: Optional[str]
    rejected_raises: list = field(default_factory=list)
    transitions: list = field(default_factory=list)    # NEW
    retry_notes: list = field(default_factory=list)    # NEW

class SessionTreeManager:
    def __init__(self, root_node, *, reserve, cwd) -> None: ...
    def get_node(self, node_id: str) -> SessionTreeNode | None: ...   # NEW
    async def allocate_child(self, limit: int) -> SessionTreeNode: ...

def _write_node_file(node, cwd: Path) -> Path: ...
```

<!-- O2 surfaces (precondition: O2 plans landed) -->

From voss/harness/team.py:
```python
@dataclass(frozen=True, slots=True)
class TeamRoleScope:
    globs: tuple[str, ...]
    def is_contained_in(self, other: TeamRoleScope | None) -> bool: ...

@dataclass(frozen=True, slots=True)
class TeamCeiling:
    budget_tokens: int | None
    scope: TeamRoleScope | None
    latency_seconds: int | None

@dataclass(frozen=True, slots=True)
class TeamPolicy:
    p: object | None

@dataclass(frozen=True, slots=True)
class BoardSpec:
    raw_items: tuple[object, ...]   # mixed: (key, ast-value) pairs and BoardGate instances

@dataclass(frozen=True, slots=True)
class TeamConfig:
    name: str
    ceiling: TeamCeiling
    policy: TeamPolicy
    em_agent_id: str | None
    roster_ids: frozenset[str]
    board: BoardSpec | None
    rituals: tuple[RitualSpec, ...]
```

From voss/ast_nodes.py:
```python
@dataclass(frozen=True, slots=True)
class BoardGate(Node):
    column: str
    target: tuple[str, str | None]    # (target column, optional ("code")|("ai"))
    predicates: tuple[Expr, ...]      # opaque expressions O3 does NOT evaluate
```

From voss/parser.py (lines 1083-1110) — `board_kv` keys: "columns" | "wip" | "p" | "retry" | "liveness".
</interfaces>

<o2_dependency_note>
This plan depends on O2 symbols: `TeamConfig`, `TeamCeiling`, `TeamPolicy`, `BoardSpec`, `BoardGate`. Per CONTEXT.md, **O2 plans exist but execution may not yet be complete.** Pre-conditions section below blocks O3-02 execution until those symbols are live in `voss/harness/team.py` and `voss/ast_nodes.py`.

The adapter `_read_board_spec` is the **single localized point of contact** with `BoardSpec.raw_items`. Per O3-RESEARCH.md §9, if O2 ever ships a typed `BoardSpec` (post-O3), the adapter can be swapped with no callsite changes outside `machine.py`.
</o2_dependency_note>

<pre_conditions>
- O3-01 shipped: `SessionTreeNode.transitions` field exists; `SessionTreeManager.get_node` exists; `voss/harness/board/{__init__,verdict,errors}.py` exist.
- O2-02 shipped (compile_team produces `TeamConfig`): grep `voss/harness/team.py` for `class TeamConfig` and `BoardSpec`. If either is missing, STOP and surface the dependency to the orchestrator. Do not stub them in O3.
- `voss/ast_nodes.py` defines `BoardGate` (O2 grammar work): grep confirms. If missing, STOP.
</pre_conditions>

<open-question id="card-mutability">
Per O3-CONTEXT.md `<open_questions>` #2 and O3-RESEARCH.md §8: `Card` frozen-rebuild vs mutable-with-controlled-setters.

**Locked recommendation:** `@dataclass(frozen=True, slots=True) class Card` — replaced wholesale via `dataclasses.replace(card, column=to_col, retry_count=new_count, ...)` on each transition. Matches the O2/O1 frozen-VO pattern (`team.py:144,188,210`, `session_tree.py:48`). EM cannot widen `card.scope` by mutation (cage invariant). Performance cost is irrelevant at the 100-card stress scale.

**Fallback:** mutable dataclass with controlled `_set_column` method. Only if frozen+replace produces unacceptable test-fixture churn.

**Escalate to checkpoint:decision** only if executor finds a SPEC line that requires mutation observability (e.g. weakrefs to `Card` from O5).
</open-question>

<open-question id="boardspec-adapter-shape">
Per O3-RESEARCH.md §9 and O3-CONTEXT.md `<open_questions>` #1: how does O3 read `BoardSpec.raw_items`?

**Locked recommendation:** a private `_read_board_spec(spec: BoardSpec | None) -> _BoardConfig` function in `machine.py`, with `isinstance` dispatch and explicit defaults applied. Do NOT touch `BoardSpec` itself — SPEC §89-90 lists "team{} grammar/parser changes" as out-of-scope. The adapter is the single localized site that the planner may swap to a typed `BoardSpec` later.

**Fallback:** pass `BoardSpec` through and read inline in `Board.__init__`. Worse — couples each callsite to the opaque tuple shape.

**Escalate to checkpoint:decision** only if O2 ships a typed `BoardSpec` between O3-01 landing and O3-02 starting (unlikely; SPEC §89-90 forbids it).
</open-question>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: machine.py — Card, _BoardConfig, _read_board_spec adapter, Board scaffold</name>
  <files>
    voss/harness/board/machine.py,
    voss/harness/board/__init__.py,
    tests/harness/board/conftest.py,
    tests/harness/board/test_board_factory.py,
    tests/harness/board/test_card_node_wiring.py
  </files>
  <behavior>
    - Test 1 (test_board_factory.py): `Board.from_team_config(team_config, recorder=manager, reviewer=stub_obj, cwd=tmp)` returns a Board; `board.root_node_id == manager._root.id` (or a child id under `parent_node_id` when provided).
    - Test 2 (test_board_factory.py): two `Board.from_team_config(...)` calls with the SAME `team_config` produce distinct boards with distinct `root_node_id`; mutating one's `cards()` list does not affect the other (independent boards — OBRD-02 acceptance L111).
    - Test 3 (test_card_node_wiring.py): `card = board.spawn_card(risk_tier="med")`; `manager.get_node(card.node_id)` is a live `SessionTreeNode`; `card.column == "Backlog"`; `card.retry_count == 0`; `card.risk_tier == "med"`; `card.deadline > clock()`.
    - Test 4 (test_card_node_wiring.py): `Card` is `frozen=True, slots=True`; attempting `card.column = "Done"` raises `FrozenInstanceError`.
    - Test 5 (test_board_factory.py): `_read_board_spec(None)` returns a `_BoardConfig` with all defaults; `_read_board_spec(BoardSpec(raw_items=()))` returns the same defaults; the function is private (leading underscore) and not re-exported from `__init__`.
    - Test 6 (test_board_factory.py): `_DEFAULT_RISK_THRESHOLDS == {"low": 0.60, "med": 0.80, "high": 0.95}` AND a repo-wide grep `grep -rn "_DEFAULT_RISK_THRESHOLDS\\|risk.*threshold.*0\\.60\\|risk.*threshold.*0\\.80" voss/` returns exactly ONE location (machine.py). Magic-number copies fail OBRD-06 acceptance L116.
  </behavior>
  <action>
    Land `voss/harness/board/machine.py`. Anchor on O3-RESEARCH.md §3.3 (symbol table), §8 (Card shape), §9 (BoardSpec adapter), §7 (defaults).

    1. Top of file: module docstring citing O3-SPEC.md OBRD-01..OBRD-03 + OBRD-06. Imports:
       ```python
       from __future__ import annotations
       import dataclasses
       import time
       from dataclasses import dataclass, field
       from datetime import datetime, timezone
       from pathlib import Path
       from typing import Callable, Literal, Optional

       from voss.harness.session_tree import SessionTreeManager, SessionTreeNode, _write_node_file
       from voss.harness.team import BoardSpec, TeamCeiling, TeamConfig, TeamRoleScope
       from voss.ast_nodes import BoardGate
       from .errors import BoardGateError, BoardWIPError
       from .verdict import Reviewer, ReviewerVerdict
       ```
       Note: do NOT import from `voss.harness.board.gates` or `voss.harness.board.tick` — those land in O3-03 / O3-04. `machine.py` must be importable independent of those modules at this wave.

    2. Type aliases + constants (private, module-level):
       ```python
       Column = Literal["Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done"]
       RiskTier = Literal["low", "med", "high"]
       _COLUMNS: tuple[Column, ...] = ("Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done")
       _TERMINAL_COLUMNS: frozenset[str] = frozenset({"Done", "Blocked"})

       # SPEC L116 SINGLE SOURCE OF TRUTH — do not duplicate elsewhere.
       _DEFAULT_RISK_THRESHOLDS: dict[str, float] = {"low": 0.60, "med": 0.80, "high": 0.95}

       _DEFAULT_WIP: dict[str, Optional[int]] = {
           "Backlog": None, "Planned": None, "InProgress": 3,
           "InReview": 2, "Blocked": None, "Done": None,
       }
       _DEFAULT_RETRY_CEILING = 3
       _DEFAULT_CARD_DEADLINE_S = 1800.0  # 30 min
       _DEFAULT_TICK_INTERVAL_S = 1.0
       ```

    3. `Card` frozen dataclass (per O3-RESEARCH.md §8):
       ```python
       @dataclass(frozen=True, slots=True)
       class Card:
           node_id: str
           column: Column
           risk_tier: RiskTier
           retry_count: int
           deadline: float
           scope: Optional[TeamRoleScope] = None
           artifact: Optional[object] = None
           eval_threshold: float = 1.0
       ```

    4. `_BoardConfig` (private, frozen) — the adapter output shape:
       ```python
       @dataclass(frozen=True, slots=True)
       class _BoardConfig:
           wip: dict          # dict[Column, int | None]
           p_overrides: dict  # dict[RiskTier, float]
           retry_ceiling: int
           card_deadline_s: float
           tick_interval_s: float
           gates: tuple      # tuple[BoardGate, ...]  — opaque; O3 default registry overrides
       ```

    5. `_read_board_spec(spec: BoardSpec | None) -> _BoardConfig` — adapter per O3-RESEARCH.md §9.
       Walk `spec.raw_items` once; classify each item:
       - `isinstance(item, BoardGate)` → append to `gates` list.
       - `isinstance(item, tuple) and len(item) == 2` → key/value pair:
         - `key == "wip"` → call helper `_parse_wip(val)` returning a dict (best-effort; if `val` is not parseable, log + leave defaults — O3-02 does not own grammar enforcement).
         - `key == "p"` → `_parse_p_overrides(val)` returning `dict[RiskTier, float]`.
         - `key == "retry"` → `_parse_retry(val)` returning int.
         - `key == "liveness"` → `_parse_liveness(val)` returning float seconds.
         - `key == "columns"` → IGNORE (SPEC locks the 6 columns).
       Return a single `_BoardConfig`.

       For the helpers: `BoardSpec.raw_items` contains AST nodes (`IntLit`, `FloatLit`, `StringLit`, `ListLit`, `DurationLit`) per `voss/parser.py:1083`. Use `getattr(val, "value", None)` to extract the literal value; if `None` or wrong type, return the default. **Defensive only** — no `VossTeamConfigError` raises in this wave; O5 owns user-error surfacing.

    6. `Board` class — public API per O3-RESEARCH.md §3.3:
       ```python
       class Board:
           def __init__(
               self,
               *,
               manager: SessionTreeManager,
               reviewer: Reviewer,
               cwd: Path,
               cfg: _BoardConfig,
               team_ceiling: TeamCeiling,
               root_node_id: str,
               clock: Callable[[], float] = time.monotonic,
               per_card_budget: int = 100_000,
               reserve: int = 0,
           ) -> None:
               self._manager = manager
               self._reviewer = reviewer
               self._cwd = cwd
               self._cfg = cfg
               self._team_ceiling = team_ceiling
               self._root_node_id = root_node_id
               self._clock = clock
               self._per_card_budget = per_card_budget
               self._reserve = reserve
               self._cards: list[Card] = []
               # tick task slot — populated by O3-04
               self._tick_task = None

           @classmethod
           def from_team_config(
               cls, team_config, *, recorder, reviewer, cwd, clock=time.monotonic,
               parent_node_id=None, per_card_budget=100_000,
           ) -> "Board":
               cfg = _read_board_spec(team_config.board)
               # wall-clock deadline source: team_config.ceiling.latency_seconds — per O3-RESEARCH.md §9 OQ-4
               if team_config.ceiling.latency_seconds:
                   cfg = dataclasses.replace(cfg, card_deadline_s=float(team_config.ceiling.latency_seconds))
               # determine root: use existing root or parent (caller owns recorder lifecycle)
               root_id = parent_node_id if parent_node_id else recorder._root.id
               return cls(
                   manager=recorder, reviewer=reviewer, cwd=cwd, cfg=cfg,
                   team_ceiling=team_config.ceiling, root_node_id=root_id,
                   clock=clock, per_card_budget=per_card_budget,
               )

           @property
           def root_node_id(self) -> str:
               return self._root_node_id

           def cards(self) -> list[Card]:
               return list(self._cards)
       ```

       `spawn_card` — async (because `allocate_child` is async):
       ```python
       async def spawn_card(
               self, *, risk_tier: RiskTier = "med",
               artifact: Optional[object] = None,
               deadline_override: Optional[float] = None,
               per_card_budget: Optional[int] = None,
       ) -> Card:
           limit = per_card_budget if per_card_budget is not None else self._per_card_budget
           node = await self._manager.allocate_child(limit=limit)
           deadline = deadline_override if deadline_override is not None else (
               self._clock() + self._cfg.card_deadline_s
           )
           card = Card(
               node_id=node.id, column="Backlog", risk_tier=risk_tier,
               retry_count=0, deadline=deadline,
               scope=self._team_ceiling.scope, artifact=artifact,
           )
           self._cards.append(card)
           return card
       ```

       `move` — synchronous; THIS wave only enforces unknown-column + WIP + delta emission. Gate predicates are O3-03; insert a `# TODO(O3-03): wire gate registry` marker where the predicate-evaluation block will go. Do not call into a gates module in this wave.
       ```python
       def move(self, card: Card, to: Column) -> Card:
           # 1. unknown column check
           if to not in _COLUMNS:
               # emit refused delta even for unknown column (audit-invariant L123)
               self._append_delta(card, from_col=card.column, to_col=to,
                                  outcome="refused", failing_clauses=["unknown-column"])
               raise BoardGateError(f"unknown column: {to}")

           # 2. WIP enforcement
           cap = self._cfg.wip.get(to)
           if cap is not None:
               in_dest = sum(1 for c in self._cards if c.column == to)
               if in_dest >= cap:
                   self._append_delta(card, from_col=card.column, to_col=to,
                                      outcome="refused", failing_clauses=["wip"])
                   raise BoardWIPError(to, cap)

           # 3. TODO(O3-03): gate predicate evaluation goes here.
           # For O3-02 we accept the transition unconditionally after WIP passes.

           # 4. emit passed delta + rebuild card with new column
           new_card = dataclasses.replace(card, column=to)
           self._cards = [new_card if c.node_id == card.node_id else c for c in self._cards]
           self._append_delta(card, from_col=card.column, to_col=to,
                              outcome="passed", failing_clauses=None)
           return new_card

       def _append_delta(self, card: Card, *, from_col, to_col, outcome,
                          failing_clauses=None, reason=None, verdict_snapshot=None) -> None:
           node = self._manager.get_node(card.node_id)
           if node is None:
               return  # defensive — card.node_id should always resolve
           delta = {
               "kind": "board.transition",
               "from": from_col,
               "to": to_col,
               "outcome": outcome,
               "failing_clauses": list(failing_clauses) if failing_clauses else None,
               "reason": reason,
               "verdict_snapshot": verdict_snapshot,
               "retry_count": card.retry_count,
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           }
           node.transitions.append(delta)
           _write_node_file(node, self._cwd)
       ```
       Per O3-RESEARCH.md §5 "from" is the persisted key (not `from_`); use the string-keyed dict literal exactly as above.

    7. Add `Board`, `Card`, `Column` (and `RiskTier`) to `voss/harness/board/__init__.py` `__all__` and import block. Do NOT export `_BoardConfig`, `_read_board_spec`, `_COLUMNS`, `_DEFAULT_*` — those are private.

    8. `tests/harness/board/conftest.py` — shared fixtures:
       - `tmp_recorder(tmp_path)` → returns `(manager, cwd)` where manager wraps a fresh root.
       - `stub_reviewer()` → returns a callable-shaped object satisfying `Reviewer` Protocol; for OBRD-02/03 tests it's never invoked, so a minimal `class _NeverReviewer: def review(self, card): raise AssertionError("should not be called in this test")` suffices.
       - `build_test_team(*, budget=1_000_000, latency_s=600.0)` → returns a minimal `TeamConfig` instance. Construct directly from imported O2 dataclasses; do NOT go through the parser. The TeamConfig.board can be `BoardSpec(raw_items=())` for the default-WIP test path; later tests will pass a tuple with WIP overrides.
       - `_artifact_passing()` / `_artifact_failing()` → simple `SimpleNamespace` with `tests_passed=True/False`, `eval_score=1.0/0.0`, `scope_violations=()`.

    9. Tests as listed in `<behavior>`. For Test 6 (single-import-site grep): use a subprocess `grep` invocation or `pathlib` walk + regex to assert exactly one match. Pattern:
       `^.*_DEFAULT_RISK_THRESHOLDS\\s*=\\s*\\{.*0\\.60.*0\\.80.*0\\.95.*\\}` — count == 1 across `voss/`.

    depends_on_o2_symbol: `TeamConfig`, `TeamCeiling`, `TeamPolicy`, `BoardSpec`, `BoardGate`, `TeamRoleScope`.
    locked_decisions_touched: Card frozen+replace pattern, _DEFAULT_RISK_THRESHOLDS single-source, transition delta JSON key "from" (not from_), `team_config.ceiling.latency_seconds` is the deadline source.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_board_factory.py tests/harness/board/test_card_node_wiring.py -x -q</automated>
    <automated>.venv/bin/python -c "from voss.harness.board import Board, Card, Column; import dataclasses; assert dataclasses.is_dataclass(Card); flds={f.name for f in dataclasses.fields(Card)}; expected={'node_id','column','risk_tier','retry_count','deadline','scope','artifact','eval_threshold'}; assert flds == expected, flds"</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.machine import _DEFAULT_RISK_THRESHOLDS; assert _DEFAULT_RISK_THRESHOLDS == {'low': 0.60, 'med': 0.80, 'high': 0.95}"</automated>
    <automated>test "$(grep -rn '_DEFAULT_RISK_THRESHOLDS = ' voss/ | grep -v '^#' | wc -l | tr -d ' ')" = "1"</automated>
    <automated>.venv/bin/python -c "import dataclasses; from voss.harness.board.machine import Card; c=Card(node_id='x', column='Backlog', risk_tier='med', retry_count=0, deadline=0.0); import pytest; ok=False;\\nimport dataclasses\\ntry: object.__setattr__(c, 'column', 'Done')\\nexcept Exception: ok=True\\n# frozen test via assignment\\nimport sys\\ntry: c.column='Done'\\nexcept dataclasses.FrozenInstanceError: ok=True\\nassert ok"</automated>
  </verify>
  <done>
    `voss/harness/board/machine.py` ships; Card is frozen 8-field dataclass; Board factory creates independent boards from the same TeamConfig; `_DEFAULT_RISK_THRESHOLDS` is the single source of truth (grep-confirmed); `_read_board_spec` adapter is localized in machine.py (no other site reads `BoardSpec.raw_items`); both new test files green.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Column rejection + WIP enforcement + transition-delta count invariant</name>
  <files>
    tests/harness/board/test_columns_and_unknown.py,
    tests/harness/board/test_wip_cap.py,
    tests/harness/board/test_transition_count_invariant.py
  </files>
  <behavior>
    - Test 1 (test_columns_and_unknown.py): all 6 column names ("Backlog","Planned","InProgress","InReview","Blocked","Done") are accepted by `board.move(card, to=col)` (with default WIP, after spawning a card per move target). Unknown column "Foo" raises `BoardGateError` containing the literal substring "unknown column: Foo".
    - Test 2 (test_columns_and_unknown.py): the refused move emits exactly one transition delta with `outcome="refused"` and `failing_clauses == ["unknown-column"]` on the card's node.
    - Test 3 (test_wip_cap.py): spawn 4 cards, move each to "InProgress" sequentially (default cap = 3). First 3 succeed. 4th raises `BoardWIPError` with `.column == "InProgress"` and `.cap == 3`.
    - Test 4 (test_wip_cap.py): the refused 4th move appends exactly one delta with `outcome="refused"` and `failing_clauses == ["wip"]` to that card's node.
    - Test 5 (test_wip_cap.py): a board with `wip={"InReview": 0}` (cap of 0) refuses every move into `InReview` — spawn 1 card, attempt `move(card, "InReview")`, expect `BoardWIPError` with `.cap == 0`. (Use a custom `BoardSpec` with `raw_items=(("wip", _make_wip_lit({"InReview": 0})),)` OR construct `_BoardConfig` directly via a test helper that mutates `board._cfg`.)
    - Test 6 (test_transition_count_invariant.py): drive a mixed lifecycle of N=20 transitions (mix of passed + refused via column/WIP) across 5 cards; for each card, assert `len(manager.get_node(card.node_id).transitions) == count_of_move_attempts_for_that_card`. Sum matches total attempts. **SPEC L123 acceptance.**
  </behavior>
  <action>
    Pure-test wave — no source edits beyond what Task 1 landed.

    1. `tests/harness/board/test_columns_and_unknown.py`:
       - Use `conftest.tmp_recorder` + `build_test_team` fixtures.
       - For each of the 6 columns: spawn a card, call `board.move(card, to=col)`, assert returned card has `.column == col` and `manager.get_node(card.node_id).transitions[-1]["to"] == col` with `outcome="passed"`.
       - Then spawn one card and call `board.move(card, to="Foo")`. Use `pytest.raises(BoardGateError) as exc; assert "unknown column: Foo" in str(exc.value)`.
       - After the raise: assert the node's transitions list has exactly one entry with `outcome="refused"` and `failing_clauses == ["unknown-column"]`.

    2. `tests/harness/board/test_wip_cap.py`:
       - Build a test team with default WIP (InProgress=3).
       - Spawn 4 cards; for the first 3, call `board.move(c, to="InProgress")` and assert success.
       - On the 4th: `with pytest.raises(BoardWIPError) as exc: board.move(c4, to="InProgress"); assert exc.value.column == "InProgress" and exc.value.cap == 3`.
       - Assert the 4th card's node has a single transition with `outcome="refused"` and `failing_clauses == ["wip"]`.
       - **Cap-of-0 sub-test:** construct a `_BoardConfig` with `wip={"InReview": 0}` and pass it via direct `Board(...)` construction (bypassing `from_team_config` — this is a unit-test escape hatch acceptable in the conftest helper). Spawn one card; assert `board.move(card, "InReview")` raises `BoardWIPError(cap=0)`.

    3. `tests/harness/board/test_transition_count_invariant.py`:
       - Spawn 5 cards. For each card, perform a deterministic mix of moves:
         - card1: 4 successful moves (Backlog→Planned→InProgress→InReview, then refuse via unknown-column → 5 attempts total = 5 deltas).
         - card2-5: mix of 3-5 attempts each, including some refused-by-WIP cases by oversubscribing InProgress.
       - For each card: `node = manager.get_node(card.node_id); assert len(node.transitions) == attempts_made_for_this_card` (track in a dict during the test).
       - Sum-of-counts assertion: `sum_attempts == sum(len(manager.get_node(c.node_id).transitions) for c in board.cards())`.

    depends_on_o2_symbol: none beyond what Task 1 already pulls in.
    locked_decisions_touched: SPEC L112 (6-column allowlist + BoardGateError for unknown), SPEC L113 (per-column WIP cap + BoardWIPError + cap-of-0 refuses all), SPEC L123 (transition-delta count == transition-attempt count).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_columns_and_unknown.py tests/harness/board/test_wip_cap.py tests/harness/board/test_transition_count_invariant.py -x -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/board/ -x -q</automated>
    <automated>grep -c 'failing_clauses.*"wip"\|failing_clauses.*\\["wip"\\]' tests/harness/board/test_wip_cap.py | head -1</automated>
  </verify>
  <done>
    All 6 column names accepted; unknown column raises `BoardGateError("unknown column: ...")`; WIP cap=3 refuses 4th transition into InProgress with `BoardWIPError`; cap-of-0 refuses every transition into the column; every refused or passed transition emits exactly one delta on the node — count invariant holds across a 20-transition mixed lifecycle.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `Card` (frozen) ↔ `Board._cards` mutable list | `Card` itself is immutable; `Board._cards` is a list of frozen Cards that gets list-replaced on every move. EM (in O5) cannot widen `card.scope` because frozen forbids attr assignment and `dataclasses.replace` produces a NEW Card. |
| `_read_board_spec` ↔ malformed `BoardSpec.raw_items` | O2's raw_items is opaque mixed-type tuple; this wave is the single localized consumer. Best-effort parse with defensive defaults — wrong types fall back to default config rather than raising. |
| `Board._append_delta` ↔ `SessionTreeNode.transitions` write | Every move attempt (passed or refused) appends exactly one delta and persists via `_write_node_file`. Silent refusal = audit-invariant violation. Test_transition_count_invariant is the gate. |
| Direct `Board(...)` constructor ↔ `from_team_config` factory | `__init__` is public to allow unit-test escape hatches (cap-of-0 test); `from_team_config` is the production path. Both go through the same `move` semantics. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O3-02-01 | Elevation of Privilege | `Card.scope` mutation widens beyond `team_ceiling.scope` | mitigate | `Card` is `frozen=True, slots=True`; `dataclasses.replace` rebuilds wholesale. Frozen check covered by test in Task 1. |
| T-O3-02-02 | Repudiation | Refused transition produces no audit record | mitigate | `_append_delta` is called BEFORE the raise in `move()`. Test_transition_count_invariant gates count equality. |
| T-O3-02-03 | Tampering | `_read_board_spec` consumed malformed `BoardSpec.raw_items` (e.g. wrong AST literal type) | accept | Defensive parse with default fallback in O3-02; harden in O5 when EM authors `team{}` blocks. O3 tests use directly-constructed BoardSpec instances, not parser output. |
| T-O3-02-04 | Denial-of-Service | WIP cap of 0 silently blocks every transition (no per-card budget burn) | accept | This is the desired behavior — cap=0 == "freeze the column"; cards remain non-terminal but timeout/budget enforcement (O3-04) drives them to Blocked eventually. |
| T-O3-02-05 | Information Disclosure | Transition delta contains reviewer-authored `notes` text | mitigate | `verdict_snapshot` is null in this wave (no reviewer calls). Field shape is reserved; redaction allowlist already covers `transitions` per O3-01. |
| T-O3-02-06 | Tampering | Two boards constructed from same `TeamConfig` mutate each other's state | mitigate | `_cards` is per-board instance attribute; `_root_node_id` differs (each board allocates its own root via the recorder). Test_board_factory.py Test 2 is the gate. |
</threat_model>

<verification>
**Plan-level automated:**
- `.venv/bin/python -m pytest tests/harness/board/ -x -q` (full board test suite)
- `.venv/bin/python -m pytest tests/harness/test_session_tree.py tests/harness/test_session_redaction.py -x -q` (O1 substrate regression — no new field changes here, but the additive `node.transitions.append` writes must round-trip)
- Single-import-site grep for `_DEFAULT_RISK_THRESHOLDS`: must return 1.
- AST import-set test on `verdict.py` still green (O3-01 invariant; this wave does not touch verdict.py).

**Manual review:**
- Inspect a persisted node JSON after a move; confirm `"transitions"` array contains the expected delta dict shape.
</verification>

<success_criteria>
- SPEC acceptance L110 (Card.column reachable via `manager.get_node(card.node_id)`): met.
- SPEC acceptance L111 (`board.root_node_id` observable; independent boards): met.
- SPEC acceptance L112 (6 columns; unknown column raises): met.
- SPEC acceptance L113 (per-column WIP refuses (N+1)th; cap-of-0 refuses every transition): met.
- SPEC acceptance L116 (risk thresholds from single source): met.
- SPEC acceptance L123 (transition-delta count == transition-attempt count): met.
- Gate predicate evaluation marked with `# TODO(O3-03)` — explicit handoff.
- No regressions in `tests/harness/test_session_tree.py`.
</success_criteria>

<output>
Create `.planning/phases/O3-board-state-machine/O3-02-SUMMARY.md` on completion. Include:
- Final `Card` field list (paste `dataclasses.fields(Card)` output).
- Test counts for all 5 new test files.
- Confirmation that `move()` has a `# TODO(O3-03):` marker where gate predicates land.
- Note any defensive parse fallbacks `_read_board_spec` exercised.
</output>
