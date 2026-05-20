# Phase O3: Board State Machine + Gated Transitions — Research

**Researched:** 2026-05-19
**Domain:** Async state machine + gated transitions over the O1 session-tree substrate
**Confidence:** HIGH on existing code surface (every claim cited file:line); MEDIUM on the open `RunRecord`-delta question (CONTEXT.md asserts a `RunRecord.payload` field that does NOT exist — see §1.3 and §5).

<user_constraints>
## User Constraints (from O3-SPEC.md + O3-CONTEXT.md)

### Locked Decisions (SPEC.md — WHAT)
- **Card == O1 session-tree node** (no parallel store). `Card.column` is reachable only via `recorder.get_node(card.node_id)`.
- **One board per compiled `team{}` block, one root tree node per board.**
- **6 columns** exactly: `Backlog → Planned → InProgress → InReview → Blocked → Done`.
- **Per-column WIP caps** (defaults: `Backlog:∞, Planned:∞, InProgress:3, InReview:2, Blocked:∞, Done:∞`).
- **Artifact-only confidence gating** (`InProgress→InReview` and `InReview→Done` only).
- **3-bucket risk tier `p`** `{low: 0.60, med: 0.80, high: 0.95}`; team-overridable; default tier `"med"`.
- **`ReviewerVerdict` frozen dataclass + `Reviewer` Protocol** as the O4 plug-in contract. `verdict.py` imports ONLY from `typing` and `dataclasses` — no transitive harness deps.
- **In-tree `DeterministicReviewerStub` for O3 tests**; production wiring is O4's job.
- **Critic loop** bounded by retry-ceiling AND budget — first-hit. `verdict.verdict == "fail"` on `InReview` transitions card back to `InProgress` and appends a `RetryNote(round, notes)` to the node's episodic memory.
- **Budget-fraction primary + wall-clock safety net** via injectable `Board.tick()`. Default deadline `team_config.ceiling.latency` (30 min default). Default tick interval 1.0 s.
- **Every state transition emits exactly one `RunRecord` delta** on the card's node; refusals included.

### Claude's Discretion (CONTEXT.md `<decisions>` "Claude's discretion")
- `Card` frozen-rebuild vs mutable-with-controlled-setters — **§8 recommends frozen+rebuild**.
- Exact key names inside `team_config.board` for tick interval / wall-clock latency — **§9 recommends keeping `BoardSpec.raw_items` opaque + thin adapter in O3**.
- Where the predicate-name string constants live — **§4 recommends a module-level frozen tuple in `gates.py`**.

### Deferred Ideas (OUT OF SCOPE)
- Reviewer-A / Reviewer-B implementations → **O4**.
- EM board mutation, ticket authoring, AC/DoD generation, specialist dispatch → **O5**.
- Audit product, killed-card surfacing, calibration telemetry → **O6**.
- `team{}` grammar/parser changes → **O2** (already shipped).
- Cross-board scheduling, global WIP, continuous-formula `p`, card priority/non-FIFO ordering, TUI surface → out-of-scope perimeter.
- Persistence across process restarts → **F1** (Durable Session Persistence).
- EM-injected custom gate predicates (`team_config.board.extra_gates`) — read opaquely if present; injection semantics are O5.
</user_constraints>

<phase_requirements>
## Phase Requirements

Stable IDs assigned in SPEC requirement order. Each cites the SPEC acceptance checkbox(es) (`O3-SPEC.md` lines 110-124) that prove it.

| ID | One-liner | SPEC acceptance checkbox(es) | Locked? |
|----|-----------|------------------------------|---------|
| OBRD-01 | Card == session-tree node (no parallel store); column is a node attribute; transitions emit a `RunRecord` delta to that node. | L110, L113, L123 | locked |
| OBRD-02 | `Board.from_team_config(team_config, recorder)` factory: per-team board with its own root node; multiple concurrent boards are independent. | L111 | locked |
| OBRD-03 | 6 columns + per-column WIP. `Board.move(card, to=...)` rejects unknown column with `BoardGateError`; over-cap raises `BoardWIPError`. | L112, L113 | locked |
| OBRD-04 | Gate-predicate registry: 7 transitions (`Backlog→Planned`, `Planned→InProgress`, `InProgress→InReview`, `InReview→Done(code)`, `InReview→Done(ai)`, `any→Blocked`, plus terminal `Done`/`Blocked` no-op). `dry_run_gate` returns failing clauses by stable name. | L114 | locked |
| OBRD-05 | Artifact-only confidence gating — `verdict.conf` never invoked for `Backlog→Planned` or `Planned→InProgress`. | L115 | locked |
| OBRD-06 | Risk-tiered `p` from a single named constant; `low: 0.60`, `med: 0.80`, `high: 0.95`. Team-overridable. Default tier `"med"`. | L116 | locked |
| OBRD-07 | `ReviewerVerdict` frozen 6-field dataclass + `Reviewer` Protocol; `verdict.py` imports only `typing` + `dataclasses`. `DeterministicReviewerStub` exists. | L117, L118, L124 | locked |
| OBRD-08 | Critic loop: failed review → back to `InProgress` + `RetryNote` appended; bounded by retry-ceiling AND budget; 4 fails on ceiling=3 lands `Blocked(reason="retry_ceiling")`. | L119 | locked |
| OBRD-09 | Timeout: wall-clock + O1 budget; `tick()` synchronous test entry; 100-card stress run — zero non-terminal cards. | L120, L121, L122, L123 | locked |
</phase_requirements>

---

## Summary

O3 is greenfield code in a well-understood codebase. The O1 substrate (`session_tree.py`) and O2 compile path (`team.py`) have shipped; the relevant call surfaces are short and concrete. The bulk of O3 work is mechanical: a 6-file `voss/harness/board/` package, a frozen `ReviewerVerdict` dataclass + `Reviewer` Protocol, a gate-predicate registry, and an `asyncio` tick loop. The state-machine semantics are fully nailed in SPEC; the planner does not need a research-driven exploration of alternatives.

Three load-bearing surfacings that the planner MUST resolve before Wave 0:

1. **`RunRecord` has no `payload` field today** (`voss/harness/session.py:115-139`). CONTEXT.md `<decisions>` §"`RunRecord` Transition-Delta Payload" says transition deltas live in "the existing `RunRecord.payload` field" — that field does not exist. The planner must pick one of: (a) add an additive Optional `payload: dict | None` field to `RunRecord` (touches the O1-SPEC-5 redaction invariant — must update `test_session_redaction.py`); (b) store transition deltas in a new attribute on `SessionTreeNode` (e.g. `transitions: list[dict]`); (c) store transition deltas in a dedicated list keyed by `node_id` on the `Board` (in-memory only — preserves zero schema change, but loses the "node owns its history" property). **§5 recommends (b)** with full rationale.

2. **No `recorder.get_node()` method exists today.** SPEC acceptance L110 ("`Card.column` is reachable only via `recorder.get_node(card.node_id)`") implies the recorder/manager needs a new lookup API. `RunRecorder` (`voss/harness/recorder.py:28`) and `SessionTreeManager` (`session_tree.py:139`) are different objects; neither indexes nodes by id. The planner must extend `SessionTreeManager` with `get_node(node_id) -> SessionTreeNode` (or land an equivalent on `Board`). **§1.1 has the recommendation.**

3. **No per-node episodic memory store exists today.** SPEC REQ-8 requires `RetryNote` entries to be "readable on the node's episodic memory in order". `EpisodicMemory` (`voss_runtime/memory/episodic.py:18`) is constructed fresh per subagent dispatch (`subagents.py:124, 137` — `EpisodicMemory(capacity=20)`); it is not associated with a `SessionTreeNode`. The planner must add an `episodic: list[dict]` or `notes: list[RetryNote]` attribute to `SessionTreeNode` (or `Board`-side `dict[node_id, list[RetryNote]]`). **§1.4 has the recommendation.**

**Primary recommendation:** Land a minimal additive shape on `SessionTreeNode` — two new list fields `transitions: list[dict] = []` and `notes: list[dict] = []` — and one new method on `SessionTreeManager`: `get_node(node_id)`. Both honor O1-SPEC-5 (no field changes to `SessionRecord` / `RunRecord` proper) and are persisted via the existing `_write_node_file` writer.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|-----------------|-----------|
| Board state machine (columns, WIP, transitions) | Harness — `voss/harness/board/machine.py` | — | Purely server-side orchestration; no UI tier |
| Gate predicates (`scope_ok`, `budget_ok`, `conf_meets_p`, ...) | Harness — `voss/harness/board/gates.py` | Reads from O1 budget, O2 scope | Pure functions over `(card, verdict, budget_state)` |
| Reviewer contract (O4 plug-in) | Standalone module — `voss/harness/board/verdict.py` | None (zero harness deps) | Constraint: O4 imports without circular deps |
| Tick driver (clock + async loop) | Harness — `voss/harness/board/tick.py` | Reuses `asyncio.create_task` pattern from `lifecycle.py:369` | Aligns with existing long-running task lifecycle |
| Card↔node wiring | Harness — `voss/harness/board/machine.py` | Calls into `voss/harness/session_tree.py` | Card IS a session-tree node; no parallel store |
| Critic loop / retry notes | Harness — `voss/harness/board/machine.py` | Persists onto `SessionTreeNode.notes` (new field) | Notes live with the node — see §1.4 |
| Transition deltas | Harness — `voss/harness/board/machine.py` | Persists onto `SessionTreeNode.transitions` (new field) | See §5 below |
| Permission scoping per card | Reuse — `voss/harness/skill/scope.py` (`_min_mode`, `scoped_gate`) | None — must NOT re-implement | CONTEXT.md constraint |

---

## 1. Existing code surface (CITED file:line)

### 1.1 Recorder and node lookup — **GAP**

- `RunRecorder` lives at `voss/harness/recorder.py:28`. It is a per-turn observation collaborator (`observe`, `absorb`, `begin_iteration`, `end_iteration`, `finalize`). It does NOT own a node index and has no `get_node(id)` method.
- `SessionTreeNode` lives at `voss/harness/session_tree.py:48`. Persisted to `<cwd>/.voss/sessions/<root_id>/<node_id>.json` (`session_tree.py:92-97`). No global registry — manager owns root + children list at `session_tree.py:148`.
- `SessionTreeManager` (`session_tree.py:139`) holds `self._root` + `self._children: list[SessionTreeNode]`. No `get_node(node_id)` lookup; `allocate_child` appends to `_children` only.

**SPEC says** (`O3-SPEC.md:22`): "For every card observed in the board, `recorder.get_node(card.node_id)` returns a live `SessionRecord`; transitions append a `RunRecord` to that node whose payload includes `from_column` / `to_column`."

**Recommendation:**
```python
# voss/harness/session_tree.py — new method on SessionTreeManager
def get_node(self, node_id: str) -> SessionTreeNode | None:
    if self._root.id == node_id:
        return self._root
    for child in self._children:
        if child.id == node_id:
            return child
    return None
```
Cite this as the "recorder.get_node" the SPEC references; "recorder" in SPEC text means the persistence collaborator surface, not literally `RunRecorder`. The Board carries a reference to the `SessionTreeManager` (held by the harness top-level per CONTEXT.md `<decisions>` "Card↔Recorder wiring").

### 1.2 `RunRecord` payload field — **DOES NOT EXIST**

`RunRecord` fields (`voss/harness/session.py:115-146`):
```
id, started_at, ended_at, goal, plan, inspected, changed, avoided, assumptions,
decisions, risks, validation, failures, diff_summary, follow_ups, cost_usd,
iterations, iteration_count, exit_reason,
iteration_total_prompt_tokens, iteration_total_completion_tokens
```

No `payload` field. CONTEXT.md `<decisions>` §"`RunRecord` Transition-Delta Payload" references "the existing `RunRecord.payload` field" — that field is **not** present. This is the load-bearing surfacing in §5 below.

`SessionRecord` (`session.py:149-162`) has `turns: list[dict]` and `runs: list[dict]` — both are arbitrary `list[dict]` and would not require schema changes to host transition deltas, but they belong to `SessionRecord`, not to a per-card node, so they violate the "per-node" requirement.

### 1.3 `SessionRecord` lifecycle

- `SessionRecord.new(cwd, model, name)` at `session.py:164-175`. Per-board root creation will call `SessionTreeNode.create_root(cwd, limit)` (`session_tree.py:60-74`), NOT `SessionRecord.new` — boards use the tree substrate, not the flat session.
- `save(record, history)` at `session.py:205-213`. NOT used by Board — Board persists via `_write_node_file(node, cwd)` (`session_tree.py:92-97`).

**Board ↔ recorder wiring shape:**
- `Board.from_team_config(team_config, recorder=..., parent_node_id=None)` accepts an existing `SessionTreeManager` (the "recorder" in CONTEXT.md's looser usage). When `parent_node_id is None`, Board creates its own root via `SessionTreeNode.create_root(cwd=..., limit=team_config.ceiling.budget_tokens)`. Otherwise it allocates a child under the parent via `manager.allocate_child(limit=...)` (`session_tree.py:151`).
- Board does NOT own the manager's lifecycle (CONTEXT.md `<decisions>`).

### 1.4 Episodic memory — **GAP for retry notes**

`EpisodicMemory` (`voss_runtime/memory/episodic.py:18-37`) is a value object with `.add(content, role)` and `.last(n)`. It is constructed **fresh per subagent dispatch** (`voss/harness/subagents.py:124, 137`): `history=EpisodicMemory(capacity=20)`. There is no shared/persisted episodic memory keyed by `SessionTreeNode`.

For SPEC REQ-8 ("`RetryNote` entries readable on the node's episodic memory in order"), the planner has three choices:

| Option | Cost | Pros | Cons |
|--------|------|------|------|
| (a) Add `notes: list[dict]` to `SessionTreeNode` | additive field on JSON schema | Card "owns" notes; survives restart (F1-ready); cheap | Touches O1 schema — needs `test_session_redaction.py` review |
| (b) Board-side `self._notes: dict[node_id, list[RetryNote]]` | zero schema change | Pure in-memory; safe | Notes die on process exit; SPEC says "node's episodic memory" implies node-owned |
| (c) Construct an `EpisodicMemory` per card; hold reference in `Card` | needs to add `episodic` field to Card | Reuses the existing class | `EpisodicMemory` is voss_runtime-coupled (`provider`, `model`, `_provider`); overkill for plain notes |

**Recommendation:** (a). The additive `notes: list[dict]` field on `SessionTreeNode` is the most aligned with the SPEC text and survives F1 persistence. Update `tests/harness/test_session_redaction.py` to include `notes` in the field allowlist (they carry reviewer-authored text — same threat surface as `turns`/`runs` which are already allowed for the user-typed-it reason).

### 1.5 Async task lifecycle — existing pattern

The harness has one canonical pattern for long-running asyncio tasks: `lifecycle.py:351-372`:
```python
rec = JobRecord(handle=..., ...)
...
if start_task:
    rec.task = asyncio.create_task(_supervise(rec, ...))
```
`JobRecord` (`lifecycle.py:77-79`) holds `task: asyncio.Task | None`. Stop semantics: `task.cancel()` then `await task` with an `asyncio.CancelledError` catcher (see `lifecycle.py:298-303`, `cli.py:301`).

**Recommendation for `Board.start()` / `Board.stop()`:** Mirror this pattern. `Board._tick_task: asyncio.Task | None`. `start()` sets `self._tick_task = asyncio.create_task(self._tick_loop())`. `stop()` calls `self._tick_task.cancel()` and awaits with `try/except asyncio.CancelledError: pass`. Store the task internally — do NOT return it from `start()`. Resolves CONTEXT.md `<open_questions>` #3.

### 1.6 Clock abstraction — **DOES NOT EXIST** (CONTEXT.md was wrong)

CONTEXT.md `<code_context>` claims "M14 watch — clock-as-Protocol with a `MonotonicClock` default impl and a `FakeClock` for tests. Reuse the same shape." This is not present in the codebase. Existing harness code uses one of:

| Pattern | Site | Form |
|---------|------|------|
| Direct `time.monotonic()` | `agent.py:649, 720, 1141, 1154, 1168`, `cli.py:2265, 2289`, `net.py:131, 135, 197, 202`, `lifecycle.py:78, 164, 283`, `watch/backend.py:114-115`, `rate_limit.py:32, 35` | bare call |
| `Callable[[], float] = time.monotonic` injected | `auth.py:423` | `now: Callable[[], float] = time.monotonic` |
| `field(default_factory=time.monotonic)` | `lifecycle.py:78` | dataclass default |

No `Clock` Protocol exists.

**Recommendation:** Introduce a minimal new `Clock` Protocol in `voss/harness/board/tick.py`:
```python
class Clock(Protocol):
    def now(self) -> float: ...

class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()

@dataclass
class FakeClock:
    _t: float = 0.0
    def now(self) -> float: return self._t
    def advance(self, dt: float) -> None: self._t += dt
```
This is also acceptable as `Callable[[], float]` injection (the `auth.py:423` pattern). The Protocol form gives test code `clock.advance(60.0)` ergonomics, which is what the 100-card stress test wants.

### 1.7 Permission scoping — REUSE

`_min_mode(m1, m2)` (`voss/harness/skill/scope.py:74-79`) is the cap-not-expand operator used by `scoped_gate` (`scope.py:82-95`). When O5 wires the EM, per-card permission caps will reuse this. O3 does NOT need to invoke this in the gate predicates (predicates check `scope.ok(card)` and `scope.clean(card)` — these read the `card.scope` value the EM declared at spawn, not a permission-gate cap). But the predicate `scope_ok` SHOULD delegate to `card.scope.is_contained_in(team_config.ceiling.scope)` (`team.py:165-184`), which is the existing glob containment heuristic.

### 1.8 BoardSpec shape (what O3 consumes from O2)

`BoardSpec` (`voss/harness/team.py:199-201`):
```python
@dataclass(frozen=True, slots=True)
class BoardSpec:
    raw_items: tuple[object, ...]
```

`raw_items` is a **mixed** tuple of:
- `tuple[str, object]` pairs from `board_kv` (`voss/parser.py:1081-1092`) — keys: `"columns"`, `"wip"`, `"p"`, `"retry"`, `"liveness"`; values are raw AST nodes (`ListLit`, `StringLit`, `IntLit`, `FloatLit`, etc.) — opaque.
- `BoardGate` instances from `gate_decl` (`voss/parser.py:1094-1112`, `ast_nodes.py:317-323`):
  ```python
  @dataclass(frozen=True, slots=True)
  class BoardGate(Node):
      column: str                                # source column
      target: tuple[str, str | None]             # (target column, optional "(code)" / "(ai)")
      predicates: tuple[Expr, ...]               # opaque expr AST per predicate
  ```

**O3 thin adapter recommendation (§9 below):** A function `read_board_spec(spec: BoardSpec | None) -> _BoardConfig` in `machine.py` that walks `spec.raw_items`, classifies each entry by `isinstance(item, BoardGate)` vs `tuple` lookup-by-key, and returns a typed read-shape (defaults applied where absent). Do NOT upgrade `BoardSpec` to a typed shape in O3 — that crosses the "no O2 parser changes" perimeter (SPEC out-of-scope §89-90).

---

## 2. OBRD-NN requirement table

See `<phase_requirements>` block above.

---

## 3. Module-file plan

Per CONTEXT.md `<decisions>` "Module Layout", `voss/harness/board/` is a package with 6 files. Symbol audit below.

### 3.1 `voss/harness/board/__init__.py`
Public API only — re-exports:
```python
from .machine import Board, Card, Column
from .verdict import ReviewerVerdict, Reviewer
from .errors import BoardWIPError, BoardGateError, BoardTimeoutError

__all__ = [
    "Board", "Card", "Column",
    "ReviewerVerdict", "Reviewer",
    "BoardWIPError", "BoardGateError", "BoardTimeoutError",
]
```
Do NOT re-export gate predicates, `Predicate`, `GateContext`, `Clock`, `MonotonicClock`, `FakeClock`, `DeterministicReviewerStub` — those are internal.

### 3.2 `voss/harness/board/verdict.py` — **import-set proof**

**SPEC constraint** (`O3-SPEC.md:102`, `O3-SPEC.md:124`): imports only `typing` and `dataclasses`. Zero transitive harness imports. Verified by a test that greps `verdict.py` imports.

Concrete file content (see §7 for the dataclass shape):
```python
"""O4 plug-in contract. NO transitive harness imports — verified by test_verdict_imports.

This file is the only public API that O4 (Reviewer A/B implementations) imports.
Adding any import beyond `typing` and `dataclasses` here breaks the plug-in contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ReviewerVerdict:
    conf: float
    source: Literal["A", "B"]
    tier: Literal["fast", "strong"]
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: tuple[str, ...]


class Reviewer(Protocol):
    def review(self, card: "object") -> ReviewerVerdict: ...
```

Note `card: "object"` — quoted, no `from ..machine import Card`. Type erasure here is the price of the zero-deps rule; this is acceptable because the Reviewer Protocol is structural. (Alternative: define a `CardProtocol` here with the read-only attributes a reviewer needs — `risk_tier`, `artifact`. Strictly typed but adds maintenance.) **Recommendation:** plain `object` annotation; downstream Reviewer impls in O4 can typed-import the concrete `Card` if they want stricter typing.

**Test:** `tests/harness/board/test_verdict_imports.py` — read `verdict.py` source, parse with `ast.parse`, walk `ast.Import` + `ast.ImportFrom` nodes, assert every module in `{"typing", "dataclasses", "__future__"}`. Fails if any harness import is added.

### 3.3 `voss/harness/board/machine.py`

Symbols (public + private):
| Symbol | Public? | Purpose |
|--------|---------|---------|
| `Column` | public | `Literal["Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done"]` |
| `COLUMNS` | private | `tuple[Column, ...]` = ("Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done") |
| `TERMINAL_COLUMNS` | private | frozenset `{"Done", "Blocked"}` |
| `Card` | public | frozen dataclass — see §8 |
| `RiskTier` | public | `Literal["low", "med", "high"]` |
| `Board` | public | the state machine |
| `BoardTransitionDelta` | private | `TypedDict` — see §5 |
| `_DEFAULT_WIP` | private | `{"Backlog": None, "Planned": None, "InProgress": 3, "InReview": 2, "Blocked": None, "Done": None}` |
| `_DEFAULT_RISK_THRESHOLDS` | private | `{"low": 0.60, "med": 0.80, "high": 0.95}` — **single source of truth** per SPEC L116 |
| `_DEFAULT_RETRY_CEILING` | private | `3` |
| `_DEFAULT_CARD_DEADLINE_S` | private | `1800.0` (30 min) |
| `_DEFAULT_TICK_INTERVAL_S` | private | `1.0` |

Public methods on `Board`:
- `from_team_config(team_config, *, recorder, reviewer, clock=None, parent_node_id=None, cwd) -> Board` (classmethod)
- `spawn_card(*, risk_tier="med", artifact=None) -> Card`
- `move(card: Card, to: Column) -> Card`
- `dry_run_gate(card: Card, transition: tuple[Column, Column]) -> tuple[bool, list[str]]`
- `start() -> None`
- `stop() -> None`
- `_tick_once(now: float) -> None`  (sync test entry — names with underscore but explicitly part of the test API)
- `root_node_id: str` (read-only property)
- `cards() -> list[Card]` (snapshot read; for tests)

### 3.4 `voss/harness/board/gates.py`

Symbols:
| Symbol | Purpose |
|--------|---------|
| `Predicate` | Protocol with `name: str` + `evaluate(ctx) -> bool` |
| `GateContext` | frozen dataclass `(card, verdict, budget_state, now)` |
| `_PREDICATE_NAMES` | module-level frozen tuple — `("conf", "tests", "eval", "scope", "budget", "retry", "timeout")` — single import site |
| `scope_ok` | predicate: `card.scope.is_contained_in(team_ceiling.scope)` |
| `scope_clean` | predicate: same scope check + verifies `card.scope_violations` is empty |
| `budget_ok` | predicate: `node.envelope["spent"] < node.envelope["limit"] - reserve` |
| `conf_meets_p` | predicate: `verdict.conf >= p_for_tier(card.risk_tier)` |
| `tests_pass` | predicate: stub — checks an attribute on the artifact; O5 wires real tests |
| `eval_meets_threshold` | predicate: stub — checks `eval.score >= card.eval_threshold`; O5/AI cards |
| `retry_under_ceiling` | predicate: `card.retry_count <= ceiling` |
| `not_timed_out` | predicate: `now < card.deadline` |
| `Gates` | dataclass with `transitions: dict[tuple[Column, Column], tuple[Predicate, ...]]` |
| `Gates.confidence_required(transition) -> bool` | returns True only for `("InProgress","InReview")` and `("InReview","Done")` |
| `Gates.build_default(team_config, reviewer) -> Gates` | factory using `_PREDICATE_NAMES` registry |

### 3.5 `voss/harness/board/tick.py`

Symbols:
| Symbol | Purpose |
|--------|---------|
| `Clock` | Protocol `now() -> float` |
| `MonotonicClock` | default impl |
| `FakeClock` | test impl with `advance(dt)` |
| `_tick_loop(board, clock, interval_s) -> Coroutine` | async loop — `await asyncio.sleep(interval_s)` between ticks |

### 3.6 `voss/harness/board/errors.py`

```python
class BoardError(Exception):
    """Base for all board-state-machine errors."""

class BoardWIPError(BoardError):
    """Raised when a transition would exceed a destination column's WIP cap."""
    def __init__(self, column: str, cap: int) -> None:
        self.column = column; self.cap = cap
        super().__init__(f"WIP cap exceeded for column {column!r}: cap={cap}")

class BoardGateError(BoardError):
    """Raised when a transition is refused by a gate predicate."""
    def __init__(self, reason: str, failing_clauses: list[str] | None = None) -> None:
        self.reason = reason; self.failing_clauses = failing_clauses or []
        super().__init__(reason)

class BoardTimeoutError(BoardError):
    """Raised when a card is forced terminal by deadline or budget exhaustion."""
    def __init__(self, reason: str) -> None:  # reason in {"timeout","budget","retry_ceiling"}
        self.reason = reason
        super().__init__(f"forced terminal: {reason}")
```

Note: per SPEC L114 + L122-L123, `dry_run_gate` returns `(bool, list[str])` and `Board.move` RAISES `BoardGateError` with `.reason` on refusal. So gate-refused transitions are not silent — they emit a transition delta with `outcome="refused"` AND raise. The dual surface lets callers test gates non-destructively.

### 3.7 `voss/harness/board/stub.py`

```python
"""DeterministicReviewerStub — O3 tests use this; production must NOT import."""
from dataclasses import dataclass
from .verdict import Reviewer, ReviewerVerdict

@dataclass
class DeterministicReviewerStub:
    conf: float = 0.99
    verdict: str = "pass"
    tier: str = "strong"
    source: str = "B"

    def review(self, card: object) -> ReviewerVerdict:
        return ReviewerVerdict(
            conf=self.conf,
            source=self.source,
            tier=self.tier,
            verdict=self.verdict,
            notes="(deterministic stub)",
            evidence_refs=(),
        )
```
This file is allowed to import from `verdict.py` because `verdict.py` is the zero-deps module. Production code path (`voss/harness/cli.py` etc.) must not import `stub.py` — enforce with a test that greps `voss/harness/` (excluding tests) for `from .board.stub` / `from voss.harness.board.stub`.

---

## 4. Gate-predicate concrete table

7 non-terminal transitions (per SPEC REQ-4). Pin order: budget/retry/timeout (cheap, no LLM call) → scope (cheap, glob math) → confidence/tests/eval (expensive, calls reviewer).

| # | Transition | Predicate tuple (in execution order) | Dependencies |
|---|-----------|---------------------------------------|--------------|
| 1 | `Backlog → Planned` | `(scope_ok,)` | card.scope, team_ceiling.scope |
| 2 | `Planned → InProgress` | `(budget_ok, scope_ok)` | node.envelope, card.scope, ceiling |
| 3 | `InProgress → InReview` | `(budget_ok, scope_ok, conf_meets_p)` | + verdict (B.fast) |
| 4a | `InReview → Done(code)` | `(scope_clean, conf_meets_p, tests_pass)` | + verdict (B.strong), artifact.tests |
| 4b | `InReview → Done(ai)` | `(scope_clean, conf_meets_p, eval_meets_threshold)` | + verdict (B.strong), artifact.eval_score, card.eval_threshold |
| 5 | `* → Blocked` | always-passes (forced transition; no predicates) — but emits `reason ∈ {"budget","retry_ceiling","timeout"}` | none (it's forced by tick or critic loop, not gate-evaluated) |
| 6 | `InReview → InProgress` (critic loop) | always-passes (driven by `verdict.verdict == "fail"`) | none; increments `retry_count` and appends RetryNote |

**Predicate pseudocode (each with stable `.name`):**

```python
class scope_ok:  # name: "scope"
    name = "scope"
    def evaluate(self, ctx: GateContext) -> bool:
        if ctx.card.scope is None or ctx.team_ceiling.scope is None:
            return True
        return ctx.card.scope.is_contained_in(ctx.team_ceiling.scope)

class budget_ok:  # name: "budget"
    name = "budget"
    def evaluate(self, ctx: GateContext) -> bool:
        env = ctx.node.envelope
        return env["spent"] < env["limit"] - ctx.reserve

class conf_meets_p:  # name: "conf"
    name = "conf"
    def evaluate(self, ctx: GateContext) -> bool:
        if ctx.verdict is None:
            ctx.verdict = ctx.reviewer.review(ctx.card)  # FIRST call site for verdict
        threshold = _DEFAULT_RISK_THRESHOLDS[ctx.card.risk_tier]
        # team override:
        threshold = ctx.team_p_overrides.get(ctx.card.risk_tier, threshold)
        return ctx.verdict.conf >= threshold

class tests_pass:  # name: "tests"
    name = "tests"
    def evaluate(self, ctx: GateContext) -> bool:
        # O3 stub: card.artifact may have a `tests_passed: bool` attribute (set by harness or test)
        return bool(getattr(ctx.card.artifact, "tests_passed", False))

class eval_meets_threshold:  # name: "eval"
    name = "eval"
    def evaluate(self, ctx: GateContext) -> bool:
        score = getattr(ctx.card.artifact, "eval_score", 0.0)
        return score >= getattr(ctx.card, "eval_threshold", 1.0)

class scope_clean:  # name: "scope"  (same name — SPEC L114 lists "scope" as one stable name)
    name = "scope"
    def evaluate(self, ctx: GateContext) -> bool:
        if not ctx.card.scope.is_contained_in(ctx.team_ceiling.scope):
            return False
        return not getattr(ctx.card.artifact, "scope_violations", ())

class retry_under_ceiling:  # name: "retry"
    name = "retry"
    def evaluate(self, ctx: GateContext) -> bool:
        return ctx.card.retry_count <= ctx.retry_ceiling

class not_timed_out:  # name: "timeout"
    name = "timeout"
    def evaluate(self, ctx: GateContext) -> bool:
        return ctx.now < ctx.card.deadline
```

**Stable predicate names** (the seven SPEC L114 lists): `("conf", "tests", "eval", "scope", "budget", "retry", "timeout")`. `scope_ok` and `scope_clean` share the `"scope"` name; this is intentional — SPEC enumerates exactly 7 names, and the dry-run consumer should not have to distinguish "scope" vs "scope.clean".

**Confidence-required predicate** (SPEC REQ-5 acceptance L115):

```python
@staticmethod
def confidence_required(transition: tuple[Column, Column]) -> bool:
    return transition in {("InProgress", "InReview"), ("InReview", "Done")}
```

For dry-run / move calls on `transition NOT in this set`, the gate registry MUST NOT contain `conf_meets_p` — so the reviewer is never invoked. This is structural, not a runtime check.

---

## 5. `RunRecord` delta concrete shape

> **This is the load-bearing surfacing.** CONTEXT.md says transition deltas go into "the existing `RunRecord.payload` field" — that field does not exist (see §1.2). Three options follow; recommendation is option (b).

### Option (a): Add `payload: dict | None = None` field to `RunRecord`
Pros: matches CONTEXT.md text; one site, one field. Cons: changes O1-locked `RunRecord` schema; needs redaction-test update; mixes "iteration metrics" with "board events" on the same record.

### Option (b) — **RECOMMENDED**: Add `transitions: list[dict] = field(default_factory=list)` to `SessionTreeNode`
Pros: card "owns" its history (matches SPEC L110 "Card.column reachable only via recorder.get_node"); no `RunRecord` schema change; existing `_write_node_file` persists it; F1-ready.
Cons: needs `test_session_redaction.py` allowlist update for the new field.

### Option (c): Board-side `self._transitions: dict[node_id, list[dict]]`
Pros: zero schema change. Cons: in-memory only; conflicts with the "the audit surface IS the UX" invariant from ORCHESTRATION-PLAN.md §4.7.

**Going forward, assume option (b)** unless the planner overrides with a `checkpoint:decision`.

### TypedDict shape

```python
from typing import Literal, NotRequired, TypedDict

class BoardTransitionDelta(TypedDict):
    kind: Literal["board.transition"]
    from_: str                      # source column (`from` is reserved — note trailing underscore)
    to: str                         # destination column
    outcome: Literal["passed", "refused", "forced"]
    failing_clauses: NotRequired[list[str] | None]    # only when outcome="refused"
    reason: NotRequired[str | None]                   # only when outcome="forced" — one of "timeout","budget","retry_ceiling"
    verdict_snapshot: NotRequired[dict | None]        # dataclasses.asdict(verdict) iff verdict was consulted
    retry_count: int
    at: str                                           # UTC ISO timestamp from datetime.now(timezone.utc).isoformat()
```

Note: Python forbids `from` as a TypedDict key; use `from_` and remap at serialization or use a string-keyed `dict` with `"from"`. The TypedDict is internal API — the **persisted JSON key MUST be `"from"`** to match CONTEXT.md `<decisions>` §"`RunRecord` Transition-Delta Payload" exactly. The simplest concrete pattern:
```python
delta = {"kind": "board.transition", "from": from_col, "to": to_col, ...}
node.transitions.append(delta)
```
Skip the TypedDict if it complicates the `from` issue; document the shape in a docstring instead.

### Worked example 1: passed `InProgress→InReview` with verdict_snapshot

```python
{
    "kind": "board.transition",
    "from": "InProgress",
    "to": "InReview",
    "outcome": "passed",
    "failing_clauses": None,
    "reason": None,
    "verdict_snapshot": {
        "conf": 0.92,
        "source": "B",
        "tier": "fast",
        "verdict": "pass",
        "notes": "Code review clean; no slop.",
        "evidence_refs": ["voss/harness/board/machine.py:120"],
    },
    "retry_count": 0,
    "at": "2026-05-19T17:42:03+00:00",
}
```
**Maps to SPEC acceptance:** L123 ("every state transition emits exactly one delta — count of records matches count of transition attempts").

### Worked example 2: refused `InReview→Done` with failing_clauses `["tests"]`

```python
{
    "kind": "board.transition",
    "from": "InReview",
    "to": "Done",
    "outcome": "refused",
    "failing_clauses": ["tests"],          # tests.pass(artifact) returned False
    "reason": None,
    "verdict_snapshot": {                   # verdict WAS consulted — conf passed but tests didn't
        "conf": 0.96,
        "source": "B",
        "tier": "strong",
        "verdict": "pass",
        "notes": "Confidence OK; tests failing.",
        "evidence_refs": [],
    },
    "retry_count": 0,
    "at": "2026-05-19T17:43:18+00:00",
}
```
**Maps to SPEC acceptance:** L114 (`dry_run_gate` returns stable clause names) and L123. Also caller raises `BoardGateError(reason="...", failing_clauses=["tests"])` immediately after the delta is appended.

### Worked example 3: forced `*→Blocked` with `reason="timeout"`

```python
{
    "kind": "board.transition",
    "from": "InProgress",     # last column the card was in
    "to": "Blocked",
    "outcome": "forced",
    "failing_clauses": None,
    "reason": "timeout",
    "verdict_snapshot": None,  # no verdict consulted
    "retry_count": 2,
    "at": "2026-05-19T18:12:01+00:00",
}
```
**Maps to SPEC acceptance:** L120 (deadline elapses → `Blocked(reason="timeout")` after one `tick()`), L122 (100-card stress: zero non-terminal), L123 (delta emitted per transition).

After this delta, `finalize_node(node, exit_reason="budget", final=...)` (from `session_tree.py:100`) is called to seal the node. `exit_reason` here is one of `EXIT_REASONS = {"done", "max-iter", "budget", "interrupt", "batch-invariant"}` — note `"timeout"` is NOT in `EXIT_REASONS`. **Planner choice:** map board `reason="timeout"` to `exit_reason="budget"` (latency budget exhausted) OR extend `EXIT_REASONS` with `"timeout"`. The former preserves O1 SPEC-5; the latter requires updating `EXIT_REASONS` (`session.py:74-76`). **Recommendation:** map `"timeout"` → `exit_reason="budget"` for the node finalize call; the `reason="timeout"` stays in the transition delta for audit.

---

## 6. `Board.tick()` design

### `Clock` Protocol (see §1.6 — new code)
```python
# voss/harness/board/tick.py
from typing import Protocol
import time

class Clock(Protocol):
    def now(self) -> float: ...

class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()

class FakeClock:
    def __init__(self, t0: float = 0.0) -> None: self._t = t0
    def now(self) -> float: return self._t
    def advance(self, dt: float) -> None: self._t += dt
```

### `Board.start()` / `Board.stop()` semantics

```python
class Board:
    _tick_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._tick_task is not None and not self._tick_task.done():
            return  # idempotent
        self._tick_task = asyncio.create_task(_tick_loop(self, self._clock, self._interval_s))

    async def stop(self) -> None:
        if self._tick_task is None: return
        self._tick_task.cancel()
        try:
            await self._tick_task
        except asyncio.CancelledError:
            pass
        self._tick_task = None
```

### `_tick_loop` (async; ONLY production path)
```python
async def _tick_loop(board: Board, clock: Clock, interval_s: float) -> None:
    while True:
        board._tick_once(clock.now())
        await asyncio.sleep(interval_s)
```
Note: `asyncio.sleep` raises `CancelledError` when the parent task is cancelled — propagates up, `stop()` swallows.

### `_tick_once(now: float)` — sync test entry

```python
def _tick_once(self, now: float) -> None:
    # snapshot of cards to avoid mutation-during-iteration
    for card in list(self._cards):
        if card.column in TERMINAL_COLUMNS:
            continue
        # 1. wall-clock
        if now >= card.deadline:
            self._force_terminal(card, "timeout")
            continue
        # 2. budget exhaustion
        node = self._manager.get_node(card.node_id)
        if node is None: continue
        env = node.envelope
        if env["spent"] >= env["limit"] - self._reserve:
            self._force_terminal(card, "budget")
```
**Idempotent:** running `_tick_once(now)` twice with the same `now` produces no additional transitions because terminal cards are skipped.

**Reuses existing pattern:** mirrors `lifecycle.py:269-303` (sync inner loop wrapped in async task; cancellation via `asyncio.CancelledError`). Cite this in the plan's `<interfaces>`.

---

## 7. `ReviewerVerdict` + `Reviewer` Protocol exact code

```python
# voss/harness/board/verdict.py
"""O4 plug-in contract. ZERO transitive harness imports — verified by test.

Adding any import beyond `typing`, `dataclasses`, `__future__` here breaks the
contract that O4's Reviewer A/B impls can import this module without circular
dependencies. See O3-SPEC.md L124.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ReviewerVerdict:
    """The frozen 6-field verdict shape O4 reviewers return.

    Fields locked by O3-SPEC.md REQ-7:
        conf:           [0.0, 1.0] confidence score from Reviewer B
        source:         which reviewer authored this verdict
        tier:           B.fast (cheap) at intermediate gate; B.strong at ->Done
        verdict:        pass | fail | block (block = abort lineage)
        notes:          reviewer-authored text; appended to card episodic memory on fail
        evidence_refs:  tuple of pointers (file:line, test names, eval refs)
    """
    conf: float
    source: Literal["A", "B"]
    tier: Literal["fast", "strong"]
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: tuple[str, ...]


class Reviewer(Protocol):
    """The injectable reviewer interface. O3 ships DeterministicReviewerStub in stub.py;
    O4 will ship the real Reviewer A and Reviewer B implementations."""

    def review(self, card: object) -> ReviewerVerdict: ...
```

`DeterministicReviewerStub` (in `stub.py`) — see §3.7.

---

## 8. Card ↔ SessionRecord wiring

### `Card.node_id` creation site
`Board.spawn_card(*, risk_tier="med", artifact=None)`:
```python
node = await self._manager.allocate_child(limit=self._per_card_budget)
card = Card(
    node_id=node.id,
    column="Backlog",
    risk_tier=risk_tier,
    retry_count=0,
    deadline=self._clock.now() + self._card_deadline_s,
    scope=self._team_ceiling.scope,   # default; EM may narrow later
    artifact=artifact,
)
self._cards.append(card)
return card
```
Note: `allocate_child` (`session_tree.py:151-178`) raises `BudgetAllocationError` if oversold. Board must handle this — typically returns nothing (signals backpressure to EM in O5) or surfaces as a `BoardWIPError`-shaped error on Backlog. Recommend re-raise as-is in O3; O5 decides handling.

### Frozen-rebuild vs mutable Card — **recommendation: frozen + rebuild**

| Choice | Pros | Cons |
|--------|------|------|
| `@dataclass(frozen=True, slots=True) class Card` | Matches O2/O1 frozen-VO pattern (`team.py:187-218`, `session_tree.py:48`). Tests easier (no aliasing surprises). EM cannot widen scope by mutation. Aligns with "cage is syntax". | Each transition allocates a new `Card`; `Board._cards` list must be updated. |
| Mutable Card | Cheaper (no realloc). | Risk: EM could mutate `card.scope` in-place to widen. Tests become brittle. |

**Recommendation: frozen.** Card is replaced wholesale on transition via `dataclasses.replace(card, column=to_col, retry_count=new_count, ...)`. Performance cost is irrelevant for the 100-card stress scale; the cage-immutability win is structural.

```python
@dataclass(frozen=True, slots=True)
class Card:
    node_id: str
    column: Column
    risk_tier: RiskTier
    retry_count: int
    deadline: float
    scope: TeamRoleScope | None     # delegated to voss.harness.team.TeamRoleScope (team.py:144)
    artifact: object | None = None  # opaque — set by EM/engineer in O5; O3 treats as duck-typed
    eval_threshold: float = 1.0     # only relevant for InReview->Done(ai)
```

Board internal: `self._cards: list[Card]`. On transition: `new_card = dataclasses.replace(card, column=to_col, ...)`; replace in-list by `node_id` match.

Resolves CONTEXT.md `<open_questions>` #2.

---

## 9. O2 BoardSpec read path

### Current shape (`voss/harness/team.py:199-201`):
```python
@dataclass(frozen=True, slots=True)
class BoardSpec:
    raw_items: tuple[object, ...]
```

`raw_items` is a mixed tuple of:
- `tuple[str, object]` from `board_kv` — keys ∈ `{"columns", "wip", "p", "retry", "liveness"}` (`voss/parser.py:1083`); values are raw AST `Expr` nodes.
- `BoardGate` (`voss/ast_nodes.py:316-323`) from `gate_decl` — has `column`, `target=(str, str | None)`, `predicates: tuple[Expr, ...]`.

### Recommendation: **thin adapter in O3, no O2 shape change**

Reason: SPEC §89-90 lists "team{} grammar/parser changes" as out-of-scope and "New schema for SessionRecord/RunRecord" likewise. Touching `BoardSpec` would cross the perimeter.

```python
# voss/harness/board/machine.py (private)
@dataclass(frozen=True, slots=True)
class _BoardConfig:
    wip: dict[Column, int | None]
    p_overrides: dict[RiskTier, float]
    retry_ceiling: int
    card_deadline_s: float
    tick_interval_s: float
    gates: tuple[BoardGate, ...]      # opaque; O3 default registry overrides

def _read_board_spec(spec: BoardSpec | None) -> _BoardConfig:
    cfg = _BoardConfig(
        wip=dict(_DEFAULT_WIP),
        p_overrides={},
        retry_ceiling=_DEFAULT_RETRY_CEILING,
        card_deadline_s=_DEFAULT_CARD_DEADLINE_S,
        tick_interval_s=_DEFAULT_TICK_INTERVAL_S,
        gates=(),
    )
    if spec is None:
        return cfg
    gates: list[BoardGate] = []
    for item in spec.raw_items:
        if isinstance(item, BoardGate):
            gates.append(item)
            continue
        if isinstance(item, tuple) and len(item) == 2:
            key, val = item
            # key ∈ {"columns","wip","p","retry","liveness"}
            if key == "wip":   cfg = _replace(cfg, wip=_parse_wip(val))
            elif key == "p":     cfg = _replace(cfg, p_overrides=_parse_p(val))
            elif key == "retry": cfg = _replace(cfg, retry_ceiling=_parse_retry(val))
            elif key == "liveness": cfg = _replace(cfg, card_deadline_s=_parse_liveness(val))
            elif key == "columns": pass  # SPEC locks columns — ignore for now
    return _replace(cfg, gates=tuple(gates))
```
Helper parsers operate on the AST literals (`IntLit`, `FloatLit`, `StringLit`, `ListLit`, plus a `DURATION_S` shape — see `grammar.lark:246`). If a key is malformed, raise `VossTeamConfigError` (defined `voss/harness/team.py:120-128`) so the cage stays compile-failing.

**Custom predicates from `BoardSpec.raw_items` gates:** O3 reads them as `BoardGate(column, target, predicates: tuple[Expr, ...])` but does NOT evaluate the `predicates` Expr AST. The O3 default registry (§4) supplies the 7 transitions; user-declared gates are surfaced to O5 (`team_config.board.extra_gates` deferred plumbing per CONTEXT.md `<decisions>` "Gate-Predicate Registry"). For O3 tests, the registry is the SPEC-defined default — the strawman's `gate InProgress->InReview { ... }` is informational, not authoritative.

Resolves CONTEXT.md `<open_questions>` #1.

### Wall-clock deadline source (CONTEXT.md open question #4)

SPEC says "`team_config.ceiling.latency` (default 30 min)". `TeamCeiling` (`voss/harness/team.py:188-191`) has `latency_seconds: int | None`. **Confirmed: lives on `ceiling`, NOT on `board`.** `Board.from_team_config` should read `team_config.ceiling.latency_seconds or _DEFAULT_CARD_DEADLINE_S`. Resolves CONTEXT.md `<open_questions>` #4.

---

## 10. Test surface

Unit + integration tests organized by SPEC acceptance checkbox. All in `tests/harness/board/` (new package).

| Test file | Acceptance covered (SPEC line refs) | Tests |
|-----------|--------------------------------------|-------|
| `test_verdict.py` | L117, L124 | `ReviewerVerdict` is frozen 6-field dataclass; assignment raises FrozenInstanceError; `Reviewer` is a Protocol with one method. |
| `test_verdict_imports.py` | L124 | AST-parse `verdict.py`; assert imports ⊆ `{"typing","dataclasses","__future__"}`. Fails on any harness import added. |
| `test_card_node_wiring.py` | L110, L111 | After `spawn_card`, `manager.get_node(card.node_id)` returns a live `SessionTreeNode`; `board.root_node_id` is observable. |
| `test_columns_and_unknown.py` | L112 | `board.move(card, to="Backlog")` accepts all 6 names; `board.move(card, to="Foo")` raises `BoardGateError("unknown column: Foo")`. |
| `test_wip_cap.py` | L113 | With InProgress cap=3, 3 successive `move(card_n, "InProgress")` succeed; 4th raises `BoardWIPError`. Cap-of-0 column refuses every transition into it. |
| `test_dry_run_gate.py` | L114 | `dry_run_gate(card, ("InProgress","InReview"))` returns `(False, ["conf"])` when verdict.conf below p; `(True, [])` when above. |
| `test_artifact_only_confidence.py` | L115 | Reviewer mock that raises on `review()` call. `move(card, "Planned")` from Backlog succeeds (no review called). `move(card, "InProgress")` from Planned succeeds (no review). `move(card, "InReview")` from InProgress raises the mock — proves review was invoked exactly there. |
| `test_risk_thresholds.py` | L116 | Import `_DEFAULT_RISK_THRESHOLDS` from `machine.py` — assert `{"low":0.60,"med":0.80,"high":0.95}`. Single import site (grep `_DEFAULT_RISK_THRESHOLDS` repo-wide returns one location). high-tier card with conf=0.94 refused; conf=0.95 passes. |
| `test_critic_loop.py` | L119 | Stub returns 4 sequential fails on a `retry.ceiling=3` card → final state `Blocked(reason="retry_ceiling")`. `node.notes` has 3 `RetryNote`-shape dicts in order with round=1,2,3. |
| `test_timeout_tick.py` | L120 | `FakeClock(0.0)`; `spawn_card` with deadline=30s; `clock.advance(31.0)`; `board._tick_once(clock.now())` → card.column=="Blocked", last transition's reason=="timeout". |
| `test_budget_tick.py` | L121 | spawn card; drain node envelope (`mutate_envelope(node, -limit, cwd)`); `_tick_once(now)` → card Blocked(reason="budget"). |
| `test_100_card_stress.py` | L122 | See below. |
| `test_transition_count_invariant.py` | L123 | Run a mixed lifecycle of N transitions (N=20); assert `len(node.transitions) == N` for every card (sum across cards). |
| `test_stub_full_lifecycle.py` | L118 | `DeterministicReviewerStub(conf=0.99, verdict="pass")` drives a card from Backlog → Planned → InProgress → InReview → Done. No LLM call (assert by Reviewer that fails on real network access). |

### 100-card stress (L122) — deterministic plan

```python
@pytest.mark.asyncio
async def test_100_card_stress_deterministic():
    clock = FakeClock(0.0)
    reviewer = DeterministicReviewerStub(conf=0.99, verdict="pass")
    team_config = _build_test_team(budget=10_000_000, latency_s=600.0, wip_inprogress=3)
    manager = SessionTreeManager(SessionTreeNode.create_root(cwd=tmp, limit=team_config.ceiling.budget_tokens), reserve=10_000, cwd=tmp)
    board = Board.from_team_config(team_config, recorder=manager, reviewer=reviewer, clock=clock, cwd=tmp)

    cards: list[Card] = []
    for i in range(100):
        # mix outcomes: 60% pass, 20% timeout, 10% budget-starved, 10% retry-ceiling
        if i % 10 < 6: card = board.spawn_card(risk_tier="med", artifact=_artifact_passing())
        elif i % 10 < 8: card = board.spawn_card(risk_tier="med", artifact=_artifact_passing(), deadline_override=clock.now() + 0.1)
        elif i % 10 < 9: card = board.spawn_card(risk_tier="med", artifact=_artifact_passing(), per_card_budget=1)  # starved
        else:           card = board.spawn_card(risk_tier="med", artifact=_artifact_failing())  # → retry_ceiling
        cards.append(card)

    # drive lifecycle deterministically (no asyncio.sleep needed; we use _tick_once)
    for _ in range(_MAX_TICKS):  # bounded
        clock.advance(1.0)
        board._tick_once(clock.now())
        # also drive the move loop synchronously: any card in non-terminal column
        # whose gates pass advances one step. (Pure sync — no Board.start() in this test.)
        for c in board.cards():
            if c.column not in TERMINAL_COLUMNS:
                next_col = _next_in_path(c.column, c.artifact)
                try: board.move(c, to=next_col)
                except BoardGateError: pass
        if all(c.column in TERMINAL_COLUMNS for c in board.cards()): break

    # SPEC L122 assertion:
    for c in board.cards():
        assert c.column in {"Done", "Blocked"}, f"card {c.node_id} stuck at {c.column}"
    assert sum(c.column == "Done" for c in board.cards()) > 0
    assert sum(c.column == "Blocked" for c in board.cards()) > 0
```

Key design choices:
- **Use `_tick_once(clock.now())`, not `Board.start()`.** Sync test entry — no real `asyncio.sleep`. Test runs in <100ms.
- **`FakeClock` advance is the only time progression.** Eliminates wall-clock flake.
- **`DeterministicReviewerStub`** — no network, no LLM.
- **No real subagent spawns** — `Card.artifact` is a duck-typed object with `.tests_passed`, `.eval_score`, `.scope_violations` attributes. O3 does NOT drive `run_subagent`; that's O5.

---

## 11. Risks + open questions

Ranked HIGH / MED / LOW.

### HIGH

**R-01. `RunRecord.payload` does not exist (§1.2, §5).** Without resolving this, plan-checker rejects the work. **Recommendation:** add `transitions: list[dict]` and `notes: list[dict]` fields to `SessionTreeNode` (option (b)). **Fallback:** Option (c) — Board-side in-memory dict; lose persistence but unblock execution. Surface as a checkpoint:decision at plan time.

**R-02. `recorder.get_node()` does not exist (§1.1).** SPEC acceptance L110 depends on this lookup. **Recommendation:** add `get_node(node_id)` method to `SessionTreeManager`. **Fallback:** Board maintains its own `dict[node_id, SessionTreeNode]` that mirrors the manager's `_children` — duplicative state but additive only. Surface as a checkpoint:decision at plan time.

**R-03. No per-node episodic memory exists (§1.4).** SPEC REQ-8 acceptance requires retry notes "readable on the node's episodic memory in order". **Recommendation:** add `notes: list[dict]` field to `SessionTreeNode`. **Fallback:** Board-side `dict[node_id, list[dict]]` — same fallback as R-01. Surface as a checkpoint:decision.

### MED

**R-04. `EXIT_REASONS` does not include `"timeout"` (§5 worked example 3).** `finalize_node` validates against `session.py:74-76`. Forcing a card to Blocked due to wall-clock timeout cannot call `finalize_node(exit_reason="timeout")`. **Recommendation:** map `"timeout"` → `exit_reason="budget"` for the finalize call; keep `reason="timeout"` in the transition delta. **Fallback:** extend `EXIT_REASONS` with `"timeout"` (touches O1 schema; needs O1 ack).

**R-05. `BoardSpec.raw_items` parsing is fragile (§9).** AST literal classes (`IntLit`, `FloatLit`, `StringLit`, `ListLit`, `DURATION_S`) are O2's responsibility; O3 must consume them defensively. A malformed `wip: "three"` would silently fall through if not validated. **Recommendation:** thin adapter `_read_board_spec` with explicit `isinstance` checks and `VossTeamConfigError` on mismatch.

**R-06. Custom gates from strawman `board { gate ... }` are read but not evaluated (§4, §9).** Risk: "looks accepted, silently dropped" (O2-RESEARCH.md R5). **Recommendation:** the `_read_board_spec` adapter logs a `decisions.md`-style warning or returns `gates=()` with an explicit note that user-declared gates are deferred to O5. Add a SPEC acceptance test that proves the default 7-transition registry is used regardless of `BoardSpec.raw_items` content.

### LOW

**R-07. `Board.tick()` interval default (1.0 s) vs the 100-card stress test (CONTEXT.md `<decisions>`).** The stress test uses `_tick_once` directly — no real sleep. Production: 1.0 s. **Recommendation:** keep default; document that tests bypass the interval via `_tick_once`.

**R-08. Predicate `.name` collisions (§4).** `scope_ok` and `scope_clean` both have `name="scope"`. SPEC L114 enumerates exactly 7 stable names — this is intentional. **Recommendation:** document the design choice in a `_PREDICATE_NAMES` docstring; assert the dry-run output has at most one `"scope"` entry per call.

**R-09. `Card.artifact` is duck-typed (§4, §8).** O3 reads `.tests_passed`, `.eval_score`, `.scope_violations` attributes opaquely. O5 will introduce a concrete `Artifact` shape. **Recommendation:** define a `class ArtifactProtocol(Protocol)` in `machine.py` with the read-only attributes O3 needs, even though it's not enforced — documentation aid for O5.

### Open questions from CONTEXT.md

| # | Question | Resolution (recommended this RESEARCH) |
|---|----------|----------------------------------------|
| OQ-1 | `BoardSpec.raw_items` upgrade vs adapter | **Adapter (§9).** Do not touch O2 — out-of-scope per SPEC L89-90. |
| OQ-2 | `Card` frozen-rebuild vs mutable | **Frozen + `dataclasses.replace` (§8).** Matches O2/O1 pattern. |
| OQ-3 | `Board.start()` returns task vs stores internally | **Stores internally (§1.5, §6).** Mirrors `lifecycle.py:351-372`. |
| OQ-4 | Wall-clock deadline lives on `ceiling` vs `board` | **`team_config.ceiling.latency_seconds` (§9).** Confirmed against `team.py:188-191`. |

---

## 12. Canonical refs

Bulleted full relative paths (cite-by-line throughout this doc):

- `.planning/phases/O3-board-state-machine/O3-SPEC.md` — locked WHAT
- `.planning/phases/O3-board-state-machine/O3-CONTEXT.md` — locked HOW + open questions
- `.planning/ORCHESTRATION-PLAN.md` — §3 board, §4 cage invariants, §5 strawman, §8 decision log
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md` — budget envelope invariant, SPEC-5 schema-additivity
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-CONTEXT.md` — recorder+budget integration points
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-01-SUMMARY.md` — substrate shipped
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-02-SUMMARY.md` — finalize boundary shipped
- `.planning/phases/O2-voss-team-spec-roster/O2-CONTEXT.md` — TeamConfig, SubagentRegistry, BoardSpec compile path
- `.planning/phases/O2-voss-team-spec-roster/O2-RESEARCH.md` — BoardSpec.raw_items opaque tuple shape (lines 291-295, 385-391)
- `.planning/phases/O2-voss-team-spec-roster/O2-01-PLAN.md` — board_block grammar + BoardDecl AST
- `.planning/phases/O2-voss-team-spec-roster/O2-02-PLAN.md` — compile_team + SubagentSpec extensions
- `.planning/phases/O2-voss-team-spec-roster/O2-03-PLAN.md` — gate compile (per-role PermissionGate; O2-03 status: assume parallel completion before O3 execution)
- `voss/harness/recorder.py` (line 28 `RunRecorder`)
- `voss/harness/session.py` (line 74 `EXIT_REASONS`, line 115 `RunRecord`, line 149 `SessionRecord`, line 205 `save`)
- `voss/harness/session_tree.py` (line 48 `SessionTreeNode`, line 60 `create_root`, line 100 `finalize_node`, line 121 `mutate_envelope`, line 139 `SessionTreeManager`, line 151 `allocate_child`)
- `voss/harness/subagents.py` (line 28 `SubagentSpec` post-O2, line 90 `run_subagent`, line 116 `run_turn` re-entry, line 142 finalize on budget exit)
- `voss/harness/skill/scope.py` (line 74 `_min_mode`, line 82 `scoped_gate`)
- `voss/harness/permissions.py` (line 42 `Mode`, line 146 `PermissionGate`)
- `voss/harness/team.py` (line 144 `TeamRoleScope`, line 165 `is_contained_in`, line 188 `TeamCeiling`, line 195 `TeamPolicy`, line 199 `BoardSpec`, line 211 `TeamConfig`, line 222 `TeamRunContext`)
- `voss/harness/lifecycle.py` (line 77-79 `JobRecord.task`, line 269-303 `_supervise` async pattern, line 369 `asyncio.create_task` site)
- `voss/grammar.lark` (line 215 `board_block`, line 218 `BOARD_KEY`, line 219 `gate_decl`, line 221 `gate_predicate`)
- `voss/ast_nodes.py` (line 316 `BoardGate`, line 326 `BoardDecl`, line 336 `TeamDecl`)
- `voss/parser.py` (line 1067 `board_block` transformer, line 1094 `gate_decl` transformer)
- `voss_runtime/budget.py` (line 12 `BudgetScope`, line 38 `add_usage`)
- `voss_runtime/memory/episodic.py` (line 18 `EpisodicMemory`, line 33 `add`)
- `tests/harness/test_session_redaction.py` — invariant gate; needs allowlist update if option (b) chosen
- `tests/harness/test_session_tree.py` — O1 substrate regression suite
- `tests/harness/test_subagent_recursion.py` — recursion pin

---

## Project Constraints (from CLAUDE.md)

Project-level CLAUDE.md not present at repo root. User-global CLAUDE.md applies:
- Use `.venv/bin/python` for tests (memory note `voss-python-interpreter`).
- Surgical changes — touch only what you must.
- Don't refactor unrelated code.
- Define success criteria before implementation.

Phase-specific guard: All code edits must remain inside the SPEC perimeter — no `voss/grammar.lark` or `voss/parser.py` changes (O2 owns those); no new `SessionRecord` / `RunRecord` field changes (O1 SPEC-5 invariant). Schema deltas must be on `SessionTreeNode` if needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.11) — existing project standard |
| Config file | repo root `pyproject.toml` / `pytest.ini` (existing) |
| Quick run command | `.venv/bin/python -m pytest tests/harness/board/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/board/ tests/harness/test_session_tree.py tests/harness/test_session_redaction.py tests/harness/test_subagent_recursion.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBRD-01 | Card == node; transitions emit deltas | unit | `pytest tests/harness/board/test_card_node_wiring.py -x` | ❌ Wave 0 |
| OBRD-02 | One board per team_config, independent roots | unit | `pytest tests/harness/board/test_board_factory.py -x` | ❌ Wave 0 |
| OBRD-03 | 6 columns + WIP cap | unit | `pytest tests/harness/board/test_columns_and_unknown.py tests/harness/board/test_wip_cap.py -x` | ❌ Wave 0 |
| OBRD-04 | Gate registry + dry_run | unit | `pytest tests/harness/board/test_dry_run_gate.py -x` | ❌ Wave 0 |
| OBRD-05 | Artifact-only confidence | unit | `pytest tests/harness/board/test_artifact_only_confidence.py -x` | ❌ Wave 0 |
| OBRD-06 | Risk-tiered p, single constant | unit | `pytest tests/harness/board/test_risk_thresholds.py -x` | ❌ Wave 0 |
| OBRD-07 | ReviewerVerdict frozen + Protocol + imports | unit | `pytest tests/harness/board/test_verdict.py tests/harness/board/test_verdict_imports.py -x` | ❌ Wave 0 |
| OBRD-08 | Critic loop bounded by retry + budget | integration | `pytest tests/harness/board/test_critic_loop.py -x` | ❌ Wave 0 |
| OBRD-09 | Timeout + 100-card stress | integration | `pytest tests/harness/board/test_timeout_tick.py tests/harness/board/test_budget_tick.py tests/harness/board/test_100_card_stress.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/harness/board/ -x -q`
- **Per wave merge:** Full suite command above (board + session_tree + redaction + recursion)
- **Phase gate:** Full suite green; `test_verdict_imports.py` asserts zero harness deps; transition count invariant holds.

### Wave 0 Gaps
- [ ] `tests/harness/board/__init__.py` — package marker
- [ ] `tests/harness/board/conftest.py` — shared fixtures: `FakeClock`, `_build_test_team`, `_artifact_passing`, `_artifact_failing`, `tmp_recorder` (SessionTreeManager around a `tmp_path`)
- [ ] All 14 test files listed in §10
- [ ] No new framework install — pytest + pytest-asyncio already in repo (`tests/harness/test_session_tree.py` uses both)

---

## Security Domain

ASVS categories applicable to this phase:

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | board runs inside an authenticated harness; no new auth surface |
| V3 Session Management | yes | reuses O1 session-tree; per-node `0o600` mode preserved (`session_tree.py:96`) |
| V4 Access Control | yes | per-card scope checked via existing `TeamRoleScope.is_contained_in` (`team.py:165`); EM cannot widen — `TeamConfig.frozen=True` (`team.py:210`) |
| V5 Input Validation | yes | `BoardSpec.raw_items` adapter validates types with `VossTeamConfigError`; column-name allowlist on `Board.move` |
| V6 Cryptography | no | no crypto in this phase |

### Threat patterns

| Pattern | STRIDE | Standard mitigation |
|---------|--------|---------------------|
| EM widens its own `card.scope` to escape `ceiling.scope` | Elevation of Privilege | `Card` is frozen (§8); `dataclasses.replace` creates a new instance; scope predicates check against the immutable `team_ceiling`. `scope_ok` runs on every non-terminal transition. |
| Adversarial reviewer returns `conf=1.0` for failing artifact | Spoofing | Mitigated by `tests_pass` / `eval_meets_threshold` predicate AT `→Done` — double-gate per SPEC REQ-4. O3 just enforces; reviewer integrity is O4. |
| Forged `ReviewerVerdict` from outside (un-injected reviewer) | Tampering | `ReviewerVerdict` is `frozen=True, slots=True`; constructor is the only path. Board accepts `Reviewer` via `from_team_config(reviewer=...)` injection — single binding site. |
| Card stuck non-terminal forever (liveness violation) | Denial-of-Service | Dual mechanism — wall-clock + budget; SPEC L122 100-card stress test is the assertion. |
| Transition delta dropped silently | Repudiation / Audit | SPEC L123 invariant: count of deltas == count of attempts. `test_transition_count_invariant` is the gate. |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | O2-03 (per-role PermissionGate compile) will ship before O3 execution begins (CONTEXT.md notes "O2 plans not yet executed"). | Dependencies | LOW — O3 does not call PermissionGate directly; only references scope via `TeamRoleScope`. If O2-03 slips, O3 unaffected. |
| A2 | Mapping `reason="timeout"` → `exit_reason="budget"` for `finalize_node` is acceptable (R-04). | §5 worked example 3 | MED — if O6 audit needs to distinguish "wall-clock" vs "token-exhausted" termination causes, the mapping conflates them. Mitigation: transition delta retains the precise reason. |
| A3 | `BoardSpec.raw_items` AST node values are typed `IntLit`/`FloatLit`/`StringLit`/`ListLit`/`DURATION_S` (not raw Python primitives). | §9 | LOW — verified by reading `voss/parser.py:1078-1092`. Could regress if O2-03 refactors. Adapter is defensive (`isinstance` checks). |
| A4 | The 100-card stress run does NOT need real `asyncio.sleep` — `_tick_once` + `FakeClock` are sufficient. | §10 | LOW — deterministic test pattern is well-established (cited `rate_limit.py:32-35` monkeypatch usage). |
| A5 | `Reviewer` Protocol accepts `card: object` (un-typed) without breaking O4's typed reviewer impls. | §3.2, §7 | LOW — Protocols are structural; O4 can subclass or write impls that take a stricter type. Alternative: `CardProtocol` in `verdict.py` — adds maintenance. |
| A6 | `DeterministicReviewerStub` can satisfy a Reviewer-Protocol typed at `card: object`. | §3.7 | LOW — Python's Protocol does structural matching; verified mentally. |

---

## Open Questions

1. **Add `transitions` + `notes` fields to `SessionTreeNode`, or use Board-side dicts?** (§5, §11 R-01/R-03)
   - What we know: SessionTreeNode already has `terminal_state: Optional[dict]` and `rejected_raises: list` — adding two more lists is precedented; persisted via `_write_node_file`.
   - What's unclear: whether O1 considers this an additive non-breaking change or a SPEC-5 boundary touch.
   - Recommendation: **add the fields**; update `test_session_redaction.py` allowlist; flag as a `checkpoint:decision` in the plan's Wave 0.

2. **Should `_tick_once` advance cards' columns, or ONLY force terminal states?** (§6)
   - What we know: SPEC L120-L121 only specify `tick()` for timeout/budget enforcement → Blocked.
   - What's unclear: the 100-card stress test (§10) drives forward moves via an explicit move-loop, not via tick. Is that the right separation?
   - Recommendation: **separation of concerns** — `_tick_once` ONLY forces terminal; forward progression is via `Board.move` (called by EM in O5 or test driver). Keeps tick deterministic and tickless tests possible.

3. **Reviewer call cardinality per transition.** When `InProgress → InReview` has predicates `(budget_ok, scope_ok, conf_meets_p)`, does `conf_meets_p` invoke `reviewer.review(card)` every evaluation, or is the verdict cached on the Card?
   - Recommendation: **call once per transition attempt**; result lives in `GateContext.verdict` for the duration of the call so subsequent predicates in the same tuple see the same verdict. Do NOT cache on Card across attempts (the verdict is artifact-dependent and the artifact can change between attempts).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | All code | ✓ | repo standard | — |
| `pytest` | Test suite | ✓ | already used | — |
| `pytest-asyncio` | async tick/loop tests | ✓ | `tests/harness/test_session_tree.py` uses it | — |
| `lark` | (transitive — only if O3 reads back into parser; it does NOT) | ✓ | already in deps | — |
| `voss_runtime` (`BudgetScope`, `BudgetExceededError`) | budget integration | ✓ | `voss_runtime/budget.py` | — |
| `.venv/bin/python` interpreter | run tests | ✓ | per `voss-python-interpreter` memory note | bare `python3` lacks deps |

**Missing dependencies with no fallback:** none — this is a pure-code phase with no external services.

**Missing dependencies with fallback:** none.

---

## Sources

### Primary (HIGH confidence)
- Codebase reads with file:line citations — all `voss/harness/*.py`, `voss/parser.py`, `voss/ast_nodes.py`, `voss_runtime/*.py` paths above.
- `.planning/phases/O3-board-state-machine/O3-SPEC.md` (locked) — every requirement and acceptance criterion.
- `.planning/phases/O3-board-state-machine/O3-CONTEXT.md` (locked) — module layout, gate registry shape, tick driver, delta payload schema.
- `.planning/phases/O1-*` summaries + spec — substrate facts.
- `.planning/phases/O2-*` plans + research — compile-path facts and BoardSpec opaque-tuple shape.

### Secondary (MEDIUM confidence)
- ORCHESTRATION-PLAN.md sections 3/4/5/8 — design rationale (the "why" behind locked decisions).

### Tertiary (LOW confidence)
- None — RESEARCH did not rely on external web sources. Phase is library-internal.

---

## Metadata

**Confidence breakdown:**
- Standard stack (Python 3.11 + asyncio + pytest + dataclasses): **HIGH** — entire codebase uses this stack.
- Architecture (board package, gate registry, frozen Card, async tick loop): **HIGH** — pattern recommendations align with existing harness conventions cited file:line.
- Pitfalls (`RunRecord.payload` gap, `EXIT_REASONS` mapping, `EpisodicMemory` per-call construction, `Clock` Protocol absence): **HIGH** — surfaced by direct codebase grep, not training data.
- Delta payload shape and storage location: **MEDIUM** — recommendation made, but final decision is a `checkpoint:decision` for the planner (Option (a)/(b)/(c) in §5).

**Research date:** 2026-05-19
**Valid until:** 2026-06-18 (30 days for stable code; O1 + O2 substrate is shipped, low churn expected)
