# Phase O5: Engineering Manager Loop — Pattern Map

**Mapped:** 2026-05-20
**Files analyzed:** 7 new (1 package + 5 modules + integration test), N unit-test files (planner-decomposed)
**Analogs found:** 7 / 7 (every new file maps to ≥1 in-tree analog)

> Substrate gate note: O3 (board) and O4 (reviewers) are **planned but not executed**.
> No `voss/harness/board/` directory or `ReviewerVerdict` class exists in live code today.
> Every analog in §Pattern Assignments that references board/* is a **spec-frozen interface**,
> not a live module. O5 plans must compile against the O3-SPEC §"Acceptance Criteria" surface
> (frozen dataclass + Protocol shape) and use mocks/stubs until O3 ships.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/em/__init__.py` (NEW) | package-init | — | `voss/harness/skill/__init__.py` | role-match (small re-export shim, matches existing harness sub-package convention) |
| `voss/harness/em/tickets.py` (NEW) | model | CRUD (frozen records) | `voss/harness/team.py` (`TeamCeiling`, `BoardSpec` frozen dataclasses) + `voss/eval/judge.py` (`Verdict` pydantic model) + `voss/harness/session.py` (`RunRecord` `__post_init__` validation) | exact (frozen-dataclass + literal enum + asdict-clean pattern is identical) |
| `voss/harness/em/handle.py` (NEW) | service / facade | request-response (cage-bounded verbs) | `voss/harness/edit_scope.py` (`EditScope` "scope facade refuses illegal writes") + `voss/harness/team.py` `gate_for_role` (cap-not-expand) + `voss/harness/skill/scope.py:_min_mode` | exact (cap-not-expand + refuse-with-typed-error is the live pattern; `EditScope.allows_write` ↔ `EMBoardHandle.allows_verb`) |
| `voss/harness/em/llm.py` (NEW) | service | request-response (structured LLM) | `voss/eval/judge.py` `judge_run` + `voss/harness/agent.py:1377` `_record_run_call` + `voss/harness/agent.py:172-210` `Plan`/`RunSemantics` pydantic schemas | exact (pydantic `BaseModel` + `provider.complete(response_format=Schema)` + sentinel `None` on `ParseError` is the project's structured-LLM idiom) |
| `voss/harness/em/loop.py` (NEW) | service / driver | event-driven loop | `voss/harness/session_tree.py` `SessionTreeManager` (allocator loop owning a lifecycle) + `voss/harness/subagents.py` `run_subagent` (single-boundary always-finalize) + `voss/harness/multiagent.py` `M13Allocator` (asyncio loop ownership) | role-match (no exact precedent — closest is `SessionTreeManager` per O1-PATTERNS Pattern 2; structurally one-class-owns-lifecycle-state with `async with self._lock`) |
| `voss/harness/em/stub.py` (NEW) | test fixture (in-tree) | deterministic responder | **`voss/harness/board/stub.py` `DeterministicReviewerStub` (O3-CONTEXT §Module Layout — SPEC-FROZEN, NOT YET LIVE)** + `voss/harness/subagents.py` `default_subagent_registry` (in-tree stub for tests) | spec-match (O5 stub mirrors O3's deterministic-stub-for-tests convention; until O3 lands, copy the surface frozen in O3-CONTEXT lines 38-43) |
| `tests/integration/harness/test_em_full_run.py` (NEW) | test | end-to-end | `tests/harness/test_happy_path_integration.py` (CliRunner-free mock-provider end-to-end) + `tests/harness/test_session_tree.py` (`tmp_path`, async, asyncio_mode=auto) | exact (`mock_provider` fixture pattern + `isolated_env` `tmp_path` + `MagicMock`+`AsyncMock` returning `ProviderResponse(parsed=Schema(...))` is the live precedent) |

---

## Pattern Assignments

### `voss/harness/em/tickets.py` (NEW — frozen data model)

**Primary analog:** `voss/harness/team.py` lines 187-218 (TeamCeiling/TeamPolicy/BoardSpec/TeamConfig — frozen-slots dataclass cluster)
**Secondary analog:** `voss/eval/judge.py` lines 12-19 (`Verdict` pydantic model with `Literal` enum)
**Tertiary analog:** `voss/harness/session.py` lines 141-146 (`RunRecord.__post_init__` literal-set validation)

#### Imports pattern — copy from `voss/harness/team.py` lines 1-30

```python
"""O5 EM ticket / kill / re-scope / routing-rationale frozen records.

Pure data module. No harness imports beyond `voss.harness.session.EXIT_REASONS`
(if the planner ties kill `reason` to that vocabulary; otherwise zero
transitive imports — mirrors O3 `verdict.py`'s "typing+dataclasses only" rule).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional
```

**Rationale:** `team.py` shows the canonical "value-object cluster in one file" idiom. Pure-data + `Literal`-typed `verdict`/`kind` fields = the project's standard cage-vocab pattern. No `BaseModel` here unless the records cross the LLM boundary (in which case follow `judge.py`'s `pydantic` route — but **prefer frozen dataclasses** for harness-internal records to match `team.py` / `verdict.py`).

#### Frozen dataclass + literal-enum pattern — copy from `voss/harness/team.py` lines 187-218

```python
# team.py lines 187-218 (canonical project shape — copy verbatim, change names)
@dataclass(frozen=True, slots=True)
class TeamCeiling:
    budget_tokens: int | None
    scope: TeamRoleScope | None
    latency_seconds: int | None


@dataclass(frozen=True, slots=True)
class BoardSpec:
    raw_items: tuple[object, ...]


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

**O5 mapping:**
- `Ticket` — `frozen=True, slots=True`. Fields: `id: str`, `card_node_id: str`, `title: str`, `acceptance: tuple[str, ...]`, `dod: tuple[str, ...]`, `assigned_role: str`, `risk_tier: Literal["low", "med", "high"]`, `routing_rationale: RoutingRationale`, `created_at: str`.
- `KillRecord` — `frozen=True, slots=True`. Fields: `killed_node_id: str`, `lineage_parent_id: str | None`, `reason: str`, `evidence_refs: tuple[str, ...]`, `killed_at: str`, `kind: Literal["em.kill"] = "em.kill"`.
- `RescopeRecord` — `frozen=True, slots=True`. Fields: `original_node_id: str`, `lineage_parent_id: str`, `new_acceptance: tuple[str, ...]`, `new_dod: tuple[str, ...]`, `reason: str`, `rescoped_at: str`, `kind: Literal["em.rescope"] = "em.rescope"`.
- `RoutingRationale` — `frozen=True, slots=True`. Fields: `chosen_role: str`, `candidate_roles: tuple[str, ...]`, `criteria: tuple[str, ...]`, `rationale: str` (one-paragraph free text — O5 decision #20). EM-emitted, audited at sign-off.

#### `Literal` enum validation — copy from `voss/eval/judge.py` lines 12-19

```python
# judge.py lines 12-19
class Verdict(BaseModel):
    """Judge response, pydantic-validated via response_format=Verdict."""
    model_config = ConfigDict(extra="ignore")
    verdict: Literal["pass", "fail"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
```

`risk_tier: Literal["low", "med", "high"]` on `Ticket` mirrors this exactly. The 3-bucket vocabulary is locked by O3-SPEC REQ-6; the **single named constant** that holds the thresholds lives in `voss/harness/board/verdict.py` (O3-CONTEXT §Module Layout). O5 must import that constant, not re-declare it.

#### Validation-via-`__post_init__` for non-Literal invariants — copy from `voss/harness/session.py` lines 141-146

```python
# session.py lines 141-146 (RunRecord)
def __post_init__(self) -> None:
    if self.exit_reason is not None and self.exit_reason not in EXIT_REASONS:
        raise ValueError(
            f"invalid exit_reason {self.exit_reason!r}; "
            f"must be one of {sorted(EXIT_REASONS)}"
        )
```

**O5 mapping:** `KillRecord.__post_init__` may validate `lineage_parent_id != killed_node_id` (no self-parented kills). `RescopeRecord.__post_init__` may validate `original_node_id != lineage_parent_id`. Do NOT add a giant validator — match the one-invariant-per-`__post_init__` style of `RunRecord`.

#### Audit-record `kind` discriminator — copy from O3-CONTEXT §Transition-Delta Storage

```
# O3-CONTEXT (SPEC-FROZEN, lines 71-83)
BoardTransition = {
  "kind": "board.transition",
  ...
}
```

O5 records must follow the **same `kind` namespace convention**: `"em.kill"`, `"em.rescope"`, `"em.routing"`. This is the audit-vocabulary contract O6 will consume — every EM-emitted record carries a `kind` string starting with `em.`, every O3-emitted carries `board.`. O5 plans must NOT reuse `board.*` namespace.

---

### `voss/harness/em/handle.py` (NEW — cage facade)

**Primary analog:** `voss/harness/edit_scope.py` (`EditScope` lines 51-134 — the live "scope facade refuses illegal writes" pattern)
**Secondary analog:** `voss/harness/team.py:gate_for_role` lines 98-125 (cap-not-expand pattern)
**Tertiary analog:** `voss/harness/skill/scope.py:_min_mode` (referenced in O3-CONTEXT canonical_refs — the cap primitive)

#### Refuse-illegal-writes pattern — copy from `voss/harness/edit_scope.py` lines 89-107

```python
# edit_scope.py lines 89-107 (canonical "facade allows-or-refuses" pattern)
def allows_write(self, target: str | Path) -> bool:
    p = (
        (self.cwd / target).resolve()
        if not Path(target).is_absolute()
        else Path(target).resolve()
    )
    try:
        p.relative_to(self.cwd)
    except ValueError:
        return False
    if p in self.files:
        return True
    for d in self.dirs:
        try:
            p.relative_to(d)
            return True
        except ValueError:
            continue
    return False
```

**O5 mapping for `EMBoardHandle`:** Expose ONLY the verbs the EM is allowed to drive: `create_card(...)`, `move(card_id, to_column)`, `kill_card(card_id, reason, evidence_refs)`, `rescope_card(card_id, new_acceptance, new_dod, reason)`, `dispatch(card_id, role, task)`, `read_board() -> BoardView`, `read_ticket(card_id) -> Ticket`. The facade **does not** expose `set_ceiling`, `set_p`, `set_wip`, `raise_budget`, `register_agent`, or `mutate_team_config` — those attempts must raise `EMCageViolation` at the facade layer (before any board call), with the rejected attempt appended to a kill-lineage-style audit list.

The cage invariants the facade enforces (from O5-CONTEXT + ORCHESTRATION-PLAN.md §4):
1. `ceiling` writes → `EMCageViolation("ceiling is EM-immutable")`
2. `p` writes → `EMCageViolation("threshold p is EM-immutable")`
3. Budget extension → `EMCageViolation("budget is non-extendable")` (already raised by O1 `BudgetCapRaiseError`; facade catches + re-raises with EM-vocabulary)
4. Unknown role dispatch → `EMCageViolation("role {x} not in roster {team_config.roster_ids}")` (read from O2's `SubagentRegistry`; never construct a new `SubagentSpec`)
5. Out-of-scope card scope → reuse O2's `TeamRoleScope.is_contained_in` (team.py:156)

#### Cap-not-expand pattern — copy from `voss/harness/team.py` lines 98-125

```python
# team.py lines 98-125 (canonical cap-not-expand)
def gate_for_role(spec: SubagentSpec, base_gate: PermissionGate) -> PermissionGate:
    if spec.mode is None:
        effective_mode = base_gate.mode
    else:
        effective_mode = _min_mode(base_gate.mode, spec.mode)
    return PermissionGate(
        mode=effective_mode,
        ...
        allow_net=True if spec.net else False,
    )
```

**O5 mapping:** When the EM dispatches a card to a role, the per-card scope is **the intersection** of (a) ceiling.scope, (b) role.scope, (c) EM-declared card.scope. Use `TeamRoleScope.is_contained_in` (team.py:156-184) to assert (c) ⊆ (a) ∩ (b); refuse with `EMCageViolation` otherwise. Never widen — match the existing `_min_mode` discipline.

#### Lineage preservation — kill / re-scope never delete

**Rule (O5-CONTEXT landmine):** `kill_card` / `rescope_card` must NEVER call any board verb that removes a session-tree node. They:
1. Append a `KillRecord` or `RescopeRecord` (the dataclasses from `tickets.py`) to the existing node's audit list (analog: `voss/harness/session_tree.py:121-136` `mutate_envelope` "rejected_raises append" pattern — write the record, leave the node in place).
2. For `rescope_card`, **additionally** allocate a NEW session-tree child node via the O1 path (`SessionTreeManager.allocate_child` — session_tree.py:151-178), linked back to the killed/re-scoped node via `lineage_parent_id`.
3. NEVER delete the original node from disk. The per-node JSON at `.voss/sessions/<root_id>/<node_id>.json` is immutable once the kill record is appended — O6 audit reads this directly.

Mirror the O1 `mutate_envelope` audit-append shape:

```python
# session_tree.py lines 121-136 — the "append-not-delete" precedent
def mutate_envelope(node: SessionTreeNode, delta: int, cwd: Path) -> None:
    if delta > 0:
        node.rejected_raises.append(
            {
                "attempted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "requested_delta": delta,
                "reason": "cap_raise_rejected",
            }
        )
        _write_node_file(node, cwd)
        raise BudgetCapRaiseError(node.id, delta, "non-extendable cap")
    ...
```

#### Typed errors — copy from `voss/harness/session_tree.py` lines 30-44

```python
# session_tree.py lines 30-44
class BudgetAllocationError(Exception):
    """Raised when a child allocation would oversell the parent envelope."""


class BudgetCapRaiseError(Exception):
    """Raised when an upward envelope delta (cap raise) is rejected."""

    def __init__(self, node_id: str, attempted_delta: int, reason: str) -> None:
        self.node_id = node_id
        self.attempted_delta = attempted_delta
        self.reason = reason
        super().__init__(
            f"cap raise rejected for node {node_id}: "
            f"delta={attempted_delta} ({reason})"
        )
```

**O5 mapping:** `EMCageViolation(Exception)` with `attempted_verb: str`, `reason: str`. Identical structured-attribute pattern so O6 can introspect.

---

### `voss/harness/em/llm.py` (NEW — structured LLM wrapper)

**Primary analog:** `voss/eval/judge.py` (the entire 59-line module — the project's reference structured-LLM call)
**Secondary analog:** `voss/harness/agent.py:1377-1426` (`_record_run_call` — "never-raise + sentinel-None" closing-call discipline)
**Tertiary analog:** `voss/harness/agent.py:172-210` (`Plan` / `RunSemantics` pydantic schemas — schema-design idiom)

#### Module-level system prompt + `judge_run`-shaped async function — copy from `voss/eval/judge.py`

```python
# judge.py lines 22-59 (canonical structured-LLM wrapper)
JUDGE_SYSTEM = """You are an evaluator. Given a task prompt, ...
Return ONLY a JSON object: ..."""


async def judge_run(
    *,
    provider: ModelProvider,
    model: str,
    task_prompt: str,
    final: str,
    file_diff: str,
    rubric: str,
) -> tuple[Verdict | None, str]:
    """Return (Verdict, judge_verdict_str). On ParseError, returns (None, "skipped")."""
    user_msg = (
        f"## Task prompt\n{task_prompt}\n\n"
        f"## Agent final\n{final}\n\n"
        ...
    )
    try:
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            response_format=Verdict,
            temperature=0.0,
        )
    except ParseError:
        return None, "skipped"
    if resp.parsed is None:
        return None, "skipped"
    return resp.parsed, resp.parsed.verdict
```

**O5 mapping:** O5 needs at least three structured-LLM call points:
1. **`em_plan_from_idea(idea: str) -> EMPlanResponse | None`** — idea → tickets/AC/DoD. Schema = `EMPlanResponse(BaseModel)` containing `tickets: list[TicketDraft]` where `TicketDraft` has `title`, `acceptance`, `dod`, `assigned_role`, `risk_tier`, `routing_rationale`.
2. **`em_dispatch_decision(board_view, ready_cards) -> DispatchDecision | None`** — choose which ready card to move + which role to dispatch to + the routing rationale.
3. **`em_terminate_decision(card_view) -> TerminateDecision | None`** — when a card is repeatedly failing or off-course, decide `kill` vs `rescope` vs `retry`.

All three follow `judge_run`'s exact shape:
- Pydantic `BaseModel` with `model_config = ConfigDict(extra="ignore")` (the **lenient** flavor — agent.py:203 — because EM hallucinations should drop unknown fields, not crash the loop).
- `temperature=0.0` for reproducibility.
- `response_format=Schema` (provider-translated; see providers.py:264/333/596/676 for how this works across providers).
- `except ParseError: return None, "skipped"` sentinel-tuple OR `_record_run_call`-style bare `except Exception: return None` (agent.py:1399). **Recommend `judge_run` style** (typed ParseError) for normal paths; `_record_run_call` style only if the call is in the never-fail finalize boundary.

#### Schema design — copy from `voss/harness/agent.py` lines 172-210

```python
# agent.py lines 172-210 (Plan + RunSemantics — the two reference EM-style schemas)
class ToolCall(BaseModel):
    name: str = Field(description="Tool name from the available tool list.")
    args: dict[str, Any] = Field(default_factory=dict, description="Keyword arguments.")
    why: str = Field(default="", description="One-line rationale for this call.")


class Plan(BaseModel):
    rationale: str = Field(description="One-paragraph reasoning for the chosen approach.")
    steps: list[ToolCall] = Field(default_factory=list, description="Sequential tool calls.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-rated confidence ...",
    )
    open_question: str | None = Field(default=None, description="...")
    final_when_done: str = Field(default="", description="...")


class RunSemantics(BaseModel):
    """... `extra="ignore"` is LENIENT ... we silently drop them ..."""
    model_config = {"extra": "ignore"}

    goal: str = ""
    avoided: list[dict] = Field(default_factory=list)
    ...
```

**O5 mapping:**
- Each EM response model **must** carry `extra="ignore"` (lenient — match `RunSemantics`, NOT the STRICT `cognition_schemas.py:12` posture).
- Every field gets a `Field(description=...)` so the JSON-schema fed to the LLM is self-documenting (the LLM consumes pydantic descriptions verbatim).
- `confidence: float = Field(ge=0.0, le=1.0)` — copy verbatim wherever EM emits a self-rated number. **Note (O5-CONTEXT landmine):** EM's self-rated confidence is **theater** at the audit layer (cage invariant #3 — confidence comes from Reviewer-B). The EM may report it for its own reasoning, but the **board gate predicate must never read it** — that's Reviewer-B's `ReviewerVerdict.conf` (O3-SPEC REQ-7).

#### Provider call surface — see `voss/harness/agent.py:1389` for the `provider.complete(..., response_format=Schema)` contract

```python
# agent.py:1389-1398 — the call surface O5 uses unchanged
resp = await provider.complete(
    messages=[
        {"role": "system", "content": RECORD_RUN_SYSTEM},
        {"role": "user", "content": transcript},
    ],
    model=model,
    response_format=RunSemantics,
    temperature=0.0,
    max_tokens=800,
)
```

**Constraint:** O5 plans must NOT introduce a new provider abstraction. Use `voss_runtime.providers.base.ModelProvider` directly (the type used by `judge_run` — judge.py:8). The harness already wires this up; O5's EM is just another structured-LLM caller.

#### Never-raise discipline — copy from `voss/harness/agent.py:1377-1426` `_record_run_call`

```python
# agent.py:1377-1410 — privileged closing-call shape
async def _record_run_call(provider, model: str, transcript: str):
    """Privileged closing call. Returns RunSemantics or None on any failure.

    Never raises — Pitfall 1 mitigation. Turn must continue if this fails.
    """
    ...
    try:
        resp = await provider.complete(...)
    except Exception:  # noqa: BLE001 — sentinel-return is the contract
        ...
        return None
    ...
    if resp.parsed is None:
        return None
    return resp.parsed
```

**O5 mapping:** The EM loop's "decide what to do next" call (`em_dispatch_decision`) follows `judge_run`'s typed-`ParseError`-only catch. The EM loop's `em_terminate_decision` (which is the EM's last-chance call before forcing a card to Blocked) follows `_record_run_call`'s bare-`except` discipline — never raise out of the finalize boundary. A non-parsed terminate decision MUST default to "force to Blocked" (liveness invariant — ORCHESTRATION-PLAN.md §4 invariant 6).

---

### `voss/harness/em/loop.py` (NEW — EM loop driver)

**Primary analog:** `voss/harness/session_tree.py` `SessionTreeManager` lines 139-178 (one-class-owns-lifecycle + `asyncio.Lock` guard + per-iteration write-to-disk)
**Secondary analog:** `voss/harness/subagents.py:run_subagent` lines 90-164 (single-boundary always-finalize + per-call `try/except BudgetExceededError` shape)
**Tertiary analog:** `voss/harness/multiagent.py` `M13Allocator` lines 69-155 (concurrent allocator with `asyncio.Lock` — lifted directly from O1 PATTERNS Pattern 2, the same playbook applies here)

**NOTE:** There is **no orchestrator-loop precedent in the harness today.** `voss/harness/lifecycle.py` is process-lifecycle (subprocess reap), not orchestration. The closest structural pattern is `SessionTreeManager` (owns one tree's state machine) + `run_subagent` (single-boundary finalize). O5's loop is structurally novel — researcher/planner own the exact shape, but it must follow these three patterns:

#### Driver class shape — copy from `voss/harness/session_tree.py` lines 139-178

```python
# session_tree.py lines 139-178 (one-class-owns-lifecycle)
class SessionTreeManager:
    """Owns one tree's allocation state; one instance per running root."""

    def __init__(
        self, root_node: SessionTreeNode, *, reserve: int, cwd: Path
    ) -> None:
        self._root = root_node
        self._reserve = reserve
        self._cwd = cwd
        self._children: list[SessionTreeNode] = []
        self._lock = asyncio.Lock()

    async def allocate_child(self, limit: int) -> SessionTreeNode:
        async with self._lock:
            ...
```

**O5 mapping for `EMLoop`:**
- One instance per running board / per `team{}` block (mirrors "one `SessionTreeManager` per running root").
- Constructor: `EMLoop(handle: EMBoardHandle, llm: EMLLMCaller, registry: SubagentRegistry, recorder: RunRecorder, *, clock: Callable[[], float] = time.monotonic)`. The injectable `clock` follows O3-CONTEXT §code_context "test clock injection pattern" — `Callable[[], float] = time.monotonic`, NOT a `Clock` Protocol (research finding O3-CONTEXT line 130).
- `asyncio.Lock` guards state-machine transitions ("decide next action" must be atomic w.r.t. concurrent ticks).
- Public entrypoints: `async def run(idea: str) -> EMRunResult` (idea → board → Done). `async def stop()` (cooperative cancel).

#### Single-boundary always-finalize — copy from `voss/harness/subagents.py:run_subagent` lines 90-164

```python
# subagents.py lines 90-164 (the canonical "single boundary, always finalize" shape)
async def run_subagent(...) -> str:
    ...
    try:
        async with scope:
            result = await run_turn(...)
        if node and result.run and result.run.exit_reason == "budget":
            finalize_node(node, exit_reason="budget", ...)
        elif node:
            finalize_node(node, exit_reason="done", ...)
        return result.final
    except BudgetExceededError:
        if node:
            finalize_node(node, exit_reason="budget", final="<halted: budget>", cwd=cwd)
        return "<halted: budget>"
```

**O5 mapping for `EMLoop.run`:**
- Single `try/except` boundary around the **entire** idea → Done arc.
- On `BudgetExceededError` (from any child via O1's substrate): force every still-open card to `Blocked(reason="budget")` and return. Mirror the always-finalize discipline — every spawned card reaches Done or Blocked **before the loop returns** (cage invariant #6, ORCHESTRATION-PLAN.md §4).
- On `EMCageViolation` (from the facade): force the offending card to `Blocked(reason="cage")` and append a `KillRecord` with `reason="cage_violation"`. **Continue the loop** — one cage-violating card does not abort the run; that's the audit-not-abort principle.
- Loop body: `read_board() → llm.em_dispatch_decision() → handle.move(...) / handle.dispatch(...) / handle.kill_card(...)` then await board tick. NEVER block on `asyncio.sleep` inside the lock — release the lock around dispatch awaits (same discipline as `SessionTreeManager._lock` releasing around `run_turn` per O1-PATTERNS line 488).

#### Dispatch reads from O2's registry — do NOT construct new SubagentSpec

```python
# subagents.py lines 60-83 — the registry-lookup pattern
def default_subagent_registry() -> SubagentRegistry:
    registry = SubagentRegistry()
    registry.register(SubagentSpec(id="explorer", ...))
    ...
    return registry
```

**O5 mapping (landmine reinforcement):** When EM dispatches a card to a role, it calls `registry.get(role_name) -> SubagentSpec | None`. If `None`, `EMCageViolation("role not in roster")`. **It does NOT** call `SubagentSpec(...)` or `registry.register(...)` itself — those are O2-compile-time-only. The EM is downstream of O2; it consumes, never authors specs. (This is the cage invariant "EM cannot invent agents" — ORCHESTRATION-PLAN.md §2 EM row, decision #3.)

#### Loop termination — Done iff board has cards and all are terminal

The loop terminates when `board.read_board()` shows zero non-terminal cards (all in `Done` or `Blocked`). Mirror O3 SPEC's liveness invariant: "100-card stress: ... every card terminates as Done or Blocked; zero non-terminal cards after the run" (O3-SPEC acceptance criterion lines 121-122).

---

### `voss/harness/em/stub.py` (NEW — deterministic test stub)

**Primary analog (SPEC-FROZEN, not yet live):** `voss/harness/board/stub.py` `DeterministicReviewerStub` — O3-CONTEXT lines 38-43

```
# O3-CONTEXT §Module Layout (SPEC-FROZEN, NOT YET LIVE)
- `stub.py` — `DeterministicReviewerStub` for O3 tests; production callers must not import.
```

And from O3-SPEC acceptance criterion (lines 118):
```
- [ ] `DeterministicReviewerStub(conf=0.99, verdict="pass")` runs the full lifecycle Backlog→…→Done without invoking any real LLM.
```

**Secondary analog:** `voss/harness/subagents.py:default_subagent_registry` lines 60-83 (in-tree default fixture that returns canned data, no provider call).

**O5 mapping for `DeterministicEMStub`:**
- Class that implements the same surface as the production `EMLLMCaller` (so `EMLoop` accepts either).
- Constructor: `DeterministicEMStub(plan: EMPlanResponse, dispatch_sequence: tuple[DispatchDecision, ...], terminate_decisions: dict[str, TerminateDecision])` — fully pre-canned.
- `async def em_plan_from_idea(...) -> EMPlanResponse`: return the constructor's `plan`.
- `async def em_dispatch_decision(...) -> DispatchDecision`: pop sequentially from `dispatch_sequence`.
- `async def em_terminate_decision(card_view) -> TerminateDecision`: lookup by `card_view.node_id` in `terminate_decisions`, default to `TerminateDecision(action="retry")`.
- Zero LLM calls. Zero `provider.complete` invocations. (Mirrors O3 stub: "without invoking any real LLM" — O3-SPEC line 118.)

**Constraint:** Production callers must not import. Same posture as `DeterministicReviewerStub`. Plans should add a `__getattr__`-level import guard or simply a docstring warning matching O3-CONTEXT line 43.

---

### `voss/harness/em/__init__.py` (NEW — package init)

**Primary analog:** `voss/harness/skill/__init__.py` (existing harness sub-package — verify exact shape during planning).

Re-export only the EM **public surface**:
```python
from .tickets import Ticket, KillRecord, RescopeRecord, RoutingRationale
from .handle import EMBoardHandle, EMCageViolation
from .llm import EMLLMCaller, EMPlanResponse, DispatchDecision, TerminateDecision
from .loop import EMLoop, EMRunResult
from .stub import DeterministicEMStub

__all__ = [
    "Ticket", "KillRecord", "RescopeRecord", "RoutingRationale",
    "EMBoardHandle", "EMCageViolation",
    "EMLLMCaller", "EMPlanResponse", "DispatchDecision", "TerminateDecision",
    "EMLoop", "EMRunResult",
    "DeterministicEMStub",
]
```

Do not re-export internal predicates / helpers. Match `voss/harness/session_tree.py:20-27` `__all__` shape.

---

### `tests/integration/harness/test_em_full_run.py` (NEW — integration)

**Primary analog:** `tests/harness/test_happy_path_integration.py` lines 1-78 (CliRunner-free `mock_provider` end-to-end with `AsyncMock` + `ProviderResponse`).
**Secondary analog:** `tests/harness/test_session_tree.py` (`tmp_path`, `asyncio_mode=auto`, class-based, no provider — O1-PATTERNS lines 222-355).

#### Mock provider fixture — copy verbatim from `test_happy_path_integration.py` lines 30-64

```python
# test_happy_path_integration.py lines 30-64
@pytest.fixture
def mock_provider(monkeypatch):
    """Stub out the provider so no network call happens."""
    from voss.harness.agent import Plan, ToolCall
    from voss_runtime.providers.base import ProviderResponse

    plan = Plan(
        rationale="trivial summary",
        steps=[ToolCall(name="fs_glob", args={"pattern": "*.md"}, why="find docs")],
        confidence=0.9,
        final_when_done="repo summary: {{step_0}}",
    )
    resp = ProviderResponse(
        text="",
        model="claude-sonnet-4-20250514",
        prompt_tokens=10,
        completion_tokens=10,
        cost_usd=0.001,
        parsed=plan,
    )

    async def fake_complete(*args, **kwargs):
        return resp

    fake = MagicMock()
    fake.complete = AsyncMock(side_effect=fake_complete)
    ...
    return fake
```

**O5 mapping:** Same fixture shape, but the `parsed=...` payload is an `EMPlanResponse` (or chains of `DispatchDecision` / `TerminateDecision` via `side_effect=[...]` for multi-call sequences). **For the integration test, prefer `DeterministicEMStub` over a mocked provider** — fewer moving parts, and the stub is the very thing O5 is shipping. Use `mock_provider` only for the leaf engineer-roster turns (so worker subagents still go through `run_turn` with deterministic plans).

#### Isolated env fixture — copy from `test_happy_path_integration.py` lines 22-27

```python
@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake-key-for-tests")
    return tmp_path
```

**Note:** `tests/harness/conftest.py:28-31` already provides `isolated_state` as autouse — but `tests/integration/` is a separate root, so the planner should either (a) duplicate the autouse fixture in `tests/integration/harness/conftest.py` (new file — verify with planner) or (b) explicitly request the fixture per-test. **Recommend (a)** to match `tests/harness/` ergonomics.

#### End-to-end shape — full board run with stubs

The integration test must execute: idea (string) → `EMLoop.run(idea)` → assert (1) board reaches all-terminal state, (2) every dispatched card has a `RoutingRationale` record on its node, (3) any kill produced a `KillRecord` with intact `lineage_parent_id`, (4) zero non-terminal cards remain. The 100-card stress test is **O3's** responsibility (O3-SPEC line 121); O5's integration test is one happy path + one kill path + one rescope path.

---

## Shared Patterns

### Frozen dataclass + `slots=True` for all value objects
**Source:** `voss/harness/team.py` lines 187-218
**Apply to:** Every record in `em/tickets.py` (Ticket, KillRecord, RescopeRecord, RoutingRationale). Also `EMPlanResponse.tickets` items if planner decides those are dataclasses vs pydantic.

### `kind: Literal["em.kill" | "em.rescope" | "em.routing"]` discriminator
**Source:** O3-CONTEXT lines 71-83 (SPEC-FROZEN BoardTransition `kind` field)
**Apply to:** Every EM-emitted audit record. O6 reads these by `kind` namespace; `em.*` is reserved for O5, `board.*` for O3, never mixed.

### Pydantic `model_config = ConfigDict(extra="ignore")` — LENIENT
**Source:** `voss/eval/judge.py:14` and `voss/harness/agent.py:203`
**Apply to:** Every LLM-response schema in `em/llm.py`. **Reject** the STRICT (`extra="forbid"`) posture of `cognition_schemas.py:12` for LLM-output schemas — LLM hallucinated fields must drop silently, not crash the loop.

### `response_format=Schema` + `temperature=0.0` + sentinel-`None`
**Source:** `voss/eval/judge.py:46-59` (canonical) + `voss/harness/agent.py:1389-1426` (never-raise variant)
**Apply to:** All three `em/llm.py` call sites. Choose typed-`ParseError` catch for normal paths, bare-`except Exception` only for the terminate path (mirrors `_record_run_call`).

### `asyncio.Lock` for state machine guard; release before any await of LLM/run_turn
**Source:** `voss/harness/session_tree.py:149,152` (`self._lock = asyncio.Lock()`, `async with self._lock:`)
**Apply to:** `em/loop.py` — guard board-state transitions; do not hold the lock during LLM calls or child subagent runs.

### Injectable clock via `Callable[[], float] = time.monotonic`
**Source:** `voss/harness/auth.py:423` (canonical, confirmed in O3-CONTEXT line 130)
**Apply to:** `em/loop.py` if O5 needs time. Do NOT introduce a `Clock` Protocol — the project convention is the bare `Callable`.

### `from __future__ import annotations` at every module top
**Source:** All harness files (`session.py:1`, `recorder.py:1`, `subagents.py:1`, `team.py:8`, `session_tree.py:6`)
**Apply to:** Every new `em/*.py`.

### UTC ISO timestamps
**Source:** `voss/harness/session.py:168`, `voss/harness/recorder.py:53`, `voss/harness/session_tree.py:69`
**Apply to:** Every `created_at` / `killed_at` / `rescoped_at` field:
```python
datetime.now(timezone.utc).isoformat(timespec="seconds")
```

### UUID id generation (12-hex)
**Source:** `voss/harness/recorder.py:52`, `voss/harness/session.py:167`, `voss/harness/session_tree.py:62`
**Apply to:** Every new `Ticket.id`, `KillRecord` id-like fields:
```python
uuid.uuid4().hex[:12]
```

### `EXIT_REASONS` membership for terminal `exit_reason`
**Source:** `voss/harness/session.py:74-76`
**Apply to:** `em/loop.py` when finalizing a forced-Blocked card. Recall O3-CONTEXT open question #5: `"timeout"` is NOT yet in `EXIT_REASONS`. Until O3 lands, O5 plans must use `"budget"` or `"interrupt"` from the live frozen set and rely on the `BoardTransition.reason="timeout"` audit field (O3-CONTEXT line 79).

### Read-from-O2-registry, never construct SubagentSpec
**Source:** `voss/harness/subagents.py:50` (`registry.get`)
**Apply to:** Every dispatch path in `em/handle.py` / `em/loop.py`. Cage invariant: EM cannot invent agents.

### Append-not-delete audit
**Source:** `voss/harness/session_tree.py:121-136` (`mutate_envelope` appends `rejected_raises`, never removes the node)
**Apply to:** Every `kill_card` / `rescope_card` in `em/handle.py`. Killed nodes stay on disk; `KillRecord` is appended.

### `EMCageViolation` exception with structured attributes (not just message)
**Source:** `voss/harness/session_tree.py:34-44` (`BudgetCapRaiseError(node_id, attempted_delta, reason)`)
**Apply to:** `em/handle.py` typed errors. O6 introspects via `.attempted_verb` / `.reason`, not by parsing the message.

---

## No Analog Found

| File | Note |
|---|---|
| `voss/harness/em/loop.py` | No live orchestrator-loop precedent. Closest are `SessionTreeManager` (one-class-owns-lifecycle) + `run_subagent` (single-boundary finalize) + `M13Allocator` (asyncio-concurrent allocator). Planner composes these three rather than inheriting from one. |

---

## Plan Implications — wave ordering (planner's call to confirm/adjust)

The recommended waves in the dispatch request are coherent against this pattern map:

- **W0 — substrate gate.** Verify O1 ✓ shipped (session_tree.py is live), O2 ✓ shipped (team.py is live), and **O3-SPEC / O4-CONTEXT contracts are frozen on paper** (not live). All O5 imports of `voss/harness/board/*` must use mocks/stubs until O3 lands. This wave produces no code — it's an acceptance gate.

- **W1 — `em/tickets.py` (data model).** No live dependencies beyond `voss/harness/session.EXIT_REASONS` (optional). Lands cleanly without O3/O4. Tests cover frozen-dataclass invariants + `__post_init__` validation. **First write target.**

- **W2 — `em/handle.py` (facade).** Depends on W1 records + frozen `voss/harness/board/Board` interface from O3-SPEC. **Until O3 lands**, the facade can construct against a mock `Board` Protocol matching O3-CONTEXT §Module Layout. Tests cover cage-refusal paths (EMCageViolation for ceiling/p/budget/unknown-role/out-of-scope writes).

- **W3 — `em/llm.py` + `em/stub.py`.** Independent of O3/O4 (no board imports needed for the schemas themselves; the stub returns the schemas). Lands second-to-last by code volume but is unblocked by O3/O4. Tests cover schema parse + sentinel-None behavior + stub determinism.

- **W4 — `em/loop.py` (driver).** Composes W1+W2+W3. **Hard-depends on O3 being live OR a board mock matching O3-SPEC exactly.** If O3 lands first (recommended), W4 plans against live `Board`; if O5 plans concurrent with O3, W4 plans against a `BoardProtocol` typed against O3-CONTEXT line 38-43 module shape.

- **W5 — `tests/integration/harness/test_em_full_run.py`.** Full board run with `DeterministicReviewerStub` (O3) + `DeterministicEMStub` (O5) + real `EMLoop` + real `EMBoardHandle` + live O1/O2 substrate. **This wave is the cross-phase acceptance:** if O3/O4 stubs are honest, this test passes; if O3/O4 stubs drift from their SPECs, this test catches it.

**Cross-phase planning notes for the planner:**

1. **O3-CONTEXT open question #5** (`EXIT_REASONS` extension for `"timeout"`) is upstream of O5. If O3 plans choose the "extend EXIT_REASONS" option (recommended in O3-CONTEXT), O5's `em/loop.py` forced-blocked path becomes simpler (`exit_reason="timeout"` is legal). If O3 plans choose "map to budget", O5 must work around — surface in W4 plan.

2. **O3-CONTEXT open question #7** (per-node episodic memory for retry notes) decides where `EMLoop` reads critic-loop history from. Until decided, plan W4 against `node.retry_notes: list[RetryNote]` (O3-CONTEXT recommended option).

3. **O2's per-role net cage (O2-03)** is live as `SubagentSpec.net: bool` (subagents.py:41) + `gate_for_role` (team.py:124). O5's dispatch path uses these as-is. **Landmine:** do NOT widen `allow_net` in the EM dispatch — `gate_for_role` already caps it correctly.

4. **The audit-vocabulary boundary** (`em.*` vs `board.*` `kind` namespace) is the contract between O5 and O6. Lock it in W1 (the `tickets.py` records). O6 will assert disjoint namespaces.

5. **No L2 vocab in EM-emitted records** (O5-CONTEXT landmine): `Ticket.title` / `RoutingRationale.rationale` text is human-facing audit copy. The planner's plan-text checks must reject `"model"`, `"cost"`, `"token"`, `"provider"` strings in user-visible field values during W1 tests.

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss/eval/`, `tests/harness/`, `tests/integration/`, `.planning/phases/O1-..*`, `.planning/phases/O2-..*`, `.planning/phases/O3-..*`, `.planning/phases/O4-..*`.

**Files read:** `voss/harness/team.py` (full), `voss/harness/session_tree.py` (full), `voss/harness/edit_scope.py` (full), `voss/eval/judge.py` (full), `voss/harness/cognition_schemas.py` (full), `voss/harness/subagents.py` (full), `voss/harness/recorder.py` (full), `voss/harness/session.py` lines 60-220, `voss/harness/agent.py` lines 150-260, 640-722, 1375-1426, `voss/harness/cognition.py` lines 1-120, `voss/harness/lifecycle.py` lines 1-100, `voss/harness/multiagent.py` lines 1-200, `tests/harness/test_happy_path_integration.py` lines 1-80, `tests/harness/test_team_gate_compile.py` lines 1-60, `.planning/phases/O1-..*/O1-CONTEXT.md`, `.planning/phases/O1-..*/O1-PATTERNS.md` (full — the format reference), `.planning/phases/O2-..*/O2-CONTEXT.md`, `.planning/phases/O3-..*/O3-SPEC.md` (full), `.planning/phases/O3-..*/O3-CONTEXT.md` (full), `.planning/phases/O4-..*/O4-CONTEXT.md`, `.planning/phases/O5-..*/O5-CONTEXT.md`, `.planning/ORCHESTRATION-PLAN.md` (full).

**Live vs SPEC-frozen distinction:** Every analog cited in §Pattern Assignments is **live code** unless explicitly labeled "SPEC-FROZEN, NOT YET LIVE" (only `voss/harness/board/*` references — those are O3-SPEC contracts to plan against, not import).

**Pattern extraction date:** 2026-05-20.
