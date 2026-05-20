# Phase O5: Engineering Manager Loop — Research

**Researched:** 2026-05-20
**Domain:** Python harness multi-agent orchestration — autonomous Engineering Manager LLM planner that wires O1 substrate + O2 roster + O3 board + O4 reviewers into a closed loop from `idea -> Done`. The phase ships the EM control structure, ticket/AC/DoD data model, routing-rationale + kill/rescope lineage records, a cage-enforcing facade over the O3 board, and a structured-LLM-output schema for EM plans.
**Confidence:** HIGH on O1/O2 surfaces (read from shipped code: `voss/harness/session_tree.py`, `voss/harness/team.py`, `voss/harness/subagents.py`, `voss_runtime/agent.py`). MEDIUM on O3/O4 surfaces (read from O3-SPEC.md / O3-CONTEXT.md / O3-02-PLAN.md / O4-CONTEXT.md / O4-RESEARCH.md / O4-01-PLAN.md — O3 and O4 have planned interfaces but **not yet executed code**). LOW on EM-prompt content and routing-rationale wording (no precedent in repo).

---

<user_constraints>
## User Constraints (from O5-CONTEXT.md)

### Locked Decisions
- **EM = LLM planner with full lead-engineer authority** (ORCHESTRATION-PLAN decisions #2, #3): create / kill / re-scope / reassign cards.
- **Human is final sign-off only** (decision #5) — autonomous to Done, no in-flight approvals.
- **Role metaphor** (decision #19): planner = Engineering Manager; workers = specialist Engineer roster.
- **Misroute handling = EM declares routing rationale, audited** (decision #20). Misroute is *not* caught in-flight — it surfaces at sign-off (residual #4).
- **AC/DoD are worker scaffolding, audit bar is the original idea** (decision #13) — the EM cannot grade its own homework.

### Claude's Discretion
- EM loop control structure (reuse `voss_runtime` `spawn`/`gather` vs harness-driven scheduler).
- Card / ticket data model relative to the O1 session tree + O3 board state.
- Routing-rationale schema (free text vs structured classification record).

### Deferred Ideas (OUT OF SCOPE)
- Board mechanics (O3 owns).
- Reviewer internals (O4 owns).
- Audit *surface* + calibration + forcing function (O6 owns; O5 only **emits** routing rationale + kill lineage as first-class records).
- Leak-6 `semantic.memory` mitigation (O6).
- `ritual standup` runtime (only stub if it cleanly drops in).
</user_constraints>

---

## Executive Findings (current-codebase integration drift)

1. **O3 and O4 are not yet executed — only planned.** O1 shipped (commits `a274d2e`, `97d70c5`, `cd0db25`, `4b59a81`). O2 shipped (commits `7c95828` … `e812318`). O3 has 4 wave plans, none executed. O4 has 4 wave plans, none executed. **O5 cannot land until O3 and O4 are green.** Plan O5 against the *frozen interfaces O3/O4 will ship*, not against working code.
2. **`voss_runtime.spawn`/`gather`/`AgentHandle` are real and shipped** in `voss_runtime/agent.py` (lines 74–120). `VossAgent.spawn(*args) -> AgentHandle` wraps `asyncio.create_task(self.run(...))`; `gather([handles], timeout=…)` returns a results list with failures coerced to `None`. **They are too primitive for O5's needs**: they do not carry per-card budget envelopes, cannot enforce per-role gates, do not honor the O1 reserved-drain finalize boundary, and silently swallow exceptions. **O5 should NOT route specialist dispatch through `voss_runtime.spawn` directly** — it should call `voss/harness/subagents.py:run_subagent(node=child, reserve=N, …)` which is already wired to the O1 finalize boundary.
3. **`Card` field gap between O3-locked shape and O4-assumed shape.** O3-SPEC.md REQ-1 locks `Card = (node_id, column, risk_tier, retry_count, deadline)` and O3-02-PLAN adds `(scope, artifact, eval_threshold)`. **O4-01-PLAN Gate 3 (line 120) asserts presence of `original_idea`, `domain`, `artifact_path`, `artifact_text`, `file_diff`, `a_verification_summary` on `Card` and will STOP if missing.** This is a real coordination gap. O5 owns the resolution: either (a) extend `Card` with EM-authored idea/domain/AC/DoD fields, or (b) introduce a **`Ticket`** value-object that wraps `Card` + EM scaffolding and passes it to reviewers as the dispatch payload. Recommend (b) — keeps O3's `Card` minimal and frozen, makes EM-owned data discoverable by audit (O6).
4. **No EM loop precedent exists in the repo.** No multi-card planner agent, no `Ticket` type, no routing-rationale record, no kill/rescope record. Closest patterns to reuse: `voss/eval/judge.py:Verdict` (pydantic `BaseModel`, `response_format=Verdict` via `provider.complete`) and `voss/harness/agent.py:run_turn` line 412 (the full agent loop with cognition + budget + permissions). The EM's LLM call should reuse the `provider.complete(..., response_format=EMPlanResponse)` pattern from `judge_run` — not the full `run_turn` cycle.
5. **Card persistence is on the SessionTreeNode, not on `RunRecord`.** O3-CONTEXT line 66 made this correction explicitly. O5's `KillRecord` / `RescopeRecord` / `RoutingRationale` must also live on `SessionTreeNode` (additive attributes, same shape as `node.transitions` and `node.retry_notes`) — never on `RunRecord` (whose fixed-field redaction invariant `tests/harness/test_session_redaction.py` actively enforces). This preserves O1 SPEC-5.
6. **`gate_for_role` + `filter_toolset_for_role` are shipped but not yet wired into `run_subagent`.** O2-03 SUMMARY line 56 says: *"EM tool surface must not expose arbitrary `PermissionGate(...)` construction. Dispatch should use `subagent_run(agent_id, task)` with harness-owned `gate_for_role` — document for O5 SPEC."* This is O5's responsibility: extend `run_subagent` (or wrap it) so per-card dispatch derives the gate via `gate_for_role(spec, base_gate)` and the toolset via `filter_toolset_for_role(spec, base_toolset)` — never letting the EM construct a gate directly.
7. **`recorder.get_node` does not yet exist.** O3-01-PLAN ships `SessionTreeManager.get_node(node_id) -> SessionTreeNode | None` (additive). O5 depends on this. If O3 lands first (which it must), O5 just consumes it.

---

## Phase Requirements

> **Numbering note (2026-05-20):** The OEM IDs below were the planner's initial suggestion. The locked OEM-01..OEM-10 numbering used by the plans + `O5-VALIDATION.md` regrouped these items (e.g. RESEARCH's OEM-04 = `EMBoardHandle` is locked as OEM-02; RESEARCH's OEM-08 = `DeterministicEMStub` is locked as OEM-04). When in doubt, the **plans + `O5-VALIDATION.md` numbering is authoritative**; the descriptions below remain valid as semantic specifications.

| ID (suggested) | Description | Research Support | Locked As |
|----|-------------|------------------|-----------|
| OEM-01 | `Ticket` value-object — `Card` + EM-authored scaffolding (`original_idea`, `acceptance_criteria`, `dod`, `worker_role`, `routing_rationale_id`, `lineage_parent_id`, `domain`). Frozen, replaced wholesale on EM mutation. | Q2, Q3 | OEM-01 |
| OEM-02 | `RoutingRationale` frozen record on `SessionTreeNode` — `(card_id, chosen_role, candidates_considered, rationale_text, confidence_hint, ts)`. Emitted on every dispatch. | Q3 |
| OEM-03 | `KillRecord` + `RescopeRecord` on `SessionTreeNode` — kill/rescope NEVER deletes the node; lineage_parent_id links new card to killed one. | Q4 |
| OEM-04 | `EMBoardHandle` facade — cage-enforced verb surface; refuses `ceiling`/`p`/budget mutation; refuses unknown role IDs; the EM's *only* board API. | Q5 |
| OEM-05 | `EMPlanResponse` pydantic schema — structured EM LLM output; list of typed plan ops the harness deterministically executes. | Q6 |
| OEM-06 | EM loop driver — read idea, snapshot board + roster, call EM LLM, execute plan ops via `EMBoardHandle`, tick board, terminate when all cards `Done`/`Blocked`. | Q1, Q6 |
| OEM-07 | Specialist dispatch — `EMBoardHandle.dispatch_card(card_id, role_id, task)` derives per-role gate + toolset, allocates budget child via O1, calls `run_subagent(node=child, reserve=…)`, emits `RoutingRationale`. | Q7 |
| OEM-08 | `DeterministicEMStub` — pure-Python implementation of the EM-LLM-call interface for unit tests; no live model. | Validation |
| OEM-09 | Misroute-audit emission — every dispatched card carries its `RoutingRationale` + reviewer-derived `domain_match_score` (from O4's Reviewer-B output) on its node; O6 reads these to build the misroute diff. | Q8 |
| OEM-10 | Idempotent termination — EM loop terminates iff every card is `Done` or `Blocked`; emits a `RunFinal` record on the root node with counts. | Q1 |

---

## Implementation Research

### Q1 — EM Loop Control Structure

**Two options surveyed:**

1. **Reuse `voss_runtime.spawn` + `gather`** (from `voss_runtime/agent.py:74–120`):
   ```python
   class VossAgent:
       def spawn(self, *args, **kwargs) -> AgentHandle:
           task = asyncio.create_task(self.run(*args, **kwargs))
           return AgentHandle(task=task, agent=self)

   @dataclass(frozen=True)
   class AgentHandle:
       task: asyncio.Task[Any]
       agent: VossAgent
       async def result(self) -> Any: ...
       async def cancel(self) -> None: ...

   async def gather(handles, *, timeout=None) -> list[Any]: ...
   ```
   - **Pro:** Already exported in `voss_runtime.__all__`. Familiar concurrency primitive.
   - **Con:** Silently swallows exceptions (`results.append(None)` on failure — line 119). No per-card budget envelope. No O1 finalize-boundary integration. Cancels pending tasks on timeout without finalizing nodes (would strand them, violating Leak-4 closure).

2. **Harness-driven scheduler over `subagents.run_subagent` + `Board.tick`** (the existing O1-O3 substrate):
   - `Board.tick()` already drives card terminal state (O3-SPEC REQ-9: `Board.tick()` checks deadline/budget on every non-terminal card and forces `→Blocked`).
   - `run_subagent(node=child, reserve=N, …)` already routes through the O1 finalize boundary (`voss/harness/subagents.py:141–164`).
   - The EM loop becomes a **plan-and-tick cycle**: pull a plan from the LLM, execute the plan ops (which may dispatch via `run_subagent`), let `Board.tick()` drain terminal cards, repeat until all cards terminal.

**Recommendation: option 2 (harness-driven scheduler).** Three reasons:

1. **Testability.** `Board.tick()` is already injectable-clock (O3-CONTEXT decision: `Board.__init__(..., clock: Callable[[], float] = time.monotonic)`). Tests step the clock + call `tick()` synchronously; no asyncio gymnastics. `gather` requires `asyncio.wait` and real tasks even in tests.
2. **Cage compliance.** `run_subagent` is the *single chokepoint* for the O1 reserved-drain finalize (D-03). Bypassing it via raw `spawn` means re-implementing the finalize boundary or risking stranded nodes. The cage invariant "every card reaches a verdict" requires the chokepoint.
3. **No double-scheduler.** O3's `Board.tick` is *already* the scheduler. Adding `gather` on top creates two schedulers competing for control of the same cards. One scheduler = simpler reasoning.

**Exact loop shape:**

```python
async def em_loop(
    *,
    idea: str,
    em_handle: EMBoardHandle,
    em_agent: EMLLMAgent,           # OEM-05 — structured-output planner
    max_iterations: int = 50,
) -> RunFinal:
    iteration = 0
    while not em_handle.all_cards_terminal():
        if iteration >= max_iterations:
            em_handle.force_block_all(reason="em_iteration_ceiling")
            break
        snapshot = em_handle.snapshot()                   # board + roster + prior rationales
        plan: EMPlanResponse = await em_agent.plan(idea=idea, snapshot=snapshot)
        em_handle.execute_plan(plan)                       # may dispatch via run_subagent
        await em_handle.tick()                             # one Board.tick() pass
        iteration += 1
    return em_handle.finalize_run()
```

`em_agent.plan(...)` is the single LLM call per iteration (cheap-to-test against a stub). `em_handle.execute_plan(...)` is pure Python over the cage-enforced facade. `em_handle.tick()` delegates to `Board.tick()` (already O3-shipped).

### Q2 — Card / Ticket Data Model

**O3-locked Card shape (`O3-02-PLAN.md:255–262`):**

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

O3-CONTEXT decision: `Card` is frozen, replaced wholesale via `dataclasses.replace(card, …)` on every transition (matches O2/O1 frozen-VO pattern).

**O4-01-PLAN gate-3 requires** `Card.original_idea`, `Card.domain`, `Card.artifact_path`, `Card.artifact_text`, `Card.file_diff`, `Card.a_verification_summary`. None of those are on O3's `Card`.

**Recommendation: introduce a `Ticket` value-object that wraps a `Card` plus EM-authored scaffolding.** Reviewers consume `Ticket` (not bare `Card`) so the cross-phase field gap is resolved by composition rather than schema extension.

```python
# voss/harness/board/ticket.py  (new module — O5 owned)
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional

from voss.harness.board.machine import Card     # O3-shipped


Domain = Literal["code", "ai"]                  # O4 splits Done gate by domain
WorkerRole = str                                # validated against TeamConfig.roster_ids


@dataclass(frozen=True, slots=True)
class Ticket:
    """EM-authored scaffolding wrapping an O3 Card.

    `Card` remains the O3-frozen state-machine value object (node_id, column,
    risk_tier, retry_count, deadline, scope, artifact, eval_threshold).
    `Ticket` adds the EM's worker-scaffolding fields the AC/DoD/idea bar
    reviewers need. Tickets are looked up by `card.node_id`; one ticket per
    card.
    """
    card: Card                                  # by reference; replace whole ticket on mutation
    original_idea: str                          # IMMUTABLE — copied from EM input; audit bar (residual-2)
    acceptance_criteria: tuple[str, ...]        # EM-authored worker scaffolding
    dod: tuple[str, ...]                        # EM-authored definition-of-done
    worker_role: WorkerRole                     # selected from TeamConfig.roster_ids
    routing_rationale_id: str                   # FK into node.routing_rationales[]
    lineage_parent_id: Optional[str] = None     # node_id of the killed/rescoped predecessor
    domain: Domain = "code"                     # O4 dispatches code vs ai eval-harness paths
    artifact_path: Optional[str] = None         # set by worker when an artifact is produced
    artifact_text: Optional[str] = None         # in-memory mirror for Reviewer-B
    file_diff: str = ""                         # populated when the worker commits
    a_verification_summary: Optional[str] = None # Reviewer-A fills; Reviewer-B reads
```

**Why a wrapper, not a Card extension:**
- O3-SPEC line 19 explicitly locks Card fields. Extending Card requires an O3 SPEC amendment.
- The audit invariant in O3-CONTEXT line 88 (`len(node.transitions) == count of transition attempts`) is about state-machine motion. Ticket scaffolding is *not* state-machine motion — it's EM authoring product.
- Keeps O4 Wave-0 Gate-3 happy by passing `Ticket` (not `Card`) to `Reviewer.review(...)`. O4 contract becomes `Reviewer.review(ticket: Ticket) -> ReviewerVerdict` instead of `Reviewer.review(card: Card)`. **This requires a one-line tweak to the O3 Reviewer Protocol** — flag as a coordination point in OPEN QUESTIONS below.

**Ticket registry on the Board** (not a parallel persistence file — node IS the registry):
```python
# Stored on SessionTreeNode as a single attribute, mirroring node.transitions
# from O3-CONTEXT line 67. Frozen list, append-only via guarded mutator.
node.tickets: list[Ticket]   # always len(node.tickets) == 1 once EM creates the ticket;
                              # rescope appends to lineage_parent_id's node a new Ticket
                              # on the NEW child node — never mutates the closed one.
```

### Q3 — Routing-Rationale Schema

ORCHESTRATION-PLAN §8 decision #20: *"EM declares routing rationale, audited (first-class surface)."* Residual #4: *misroute caught at sign-off only.* O5 must emit the data O6 surfaces.

**Existing audit-record patterns to mirror:**

- `voss/eval/judge.py:Verdict` (pydantic BaseModel) — `(verdict, confidence, rationale)` shape, validated via `response_format=Verdict` on the provider call.
- O1 `SessionTreeNode.rejected_raises` (line 56 of `session_tree.py`) — a `list[dict]` of audit entries appended on every cap-raise attempt; mode 0o600 on disk; serialized via `to_dict`. **This is the established cage-audit pattern in the repo.**
- O3 `node.transitions` (O3-CONTEXT line 67) — frozen TypedDict appended on every state transition.

**Recommendation: frozen dataclass + node attribute, mirroring `node.transitions`:**

```python
# voss/harness/board/routing.py  (new module — O5 owned)
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class RoutingRationale:
    """First-class audit record for EM specialist dispatch (decision #20).

    Emitted exactly once per dispatch_card op. Stored on the card's
    SessionTreeNode under `node.routing_rationales` (list, append-only).
    Lives on disk as part of the node's JSON file (audit replayable).
    """
    id: str                                    # uuid hex[:12]; FK target from Ticket.routing_rationale_id
    card_id: str                               # == node_id of the card being dispatched
    chosen_role: str                           # the role EM picked from the roster
    candidates_considered: tuple[str, ...]    # other roster role IDs EM evaluated
    rationale_text: str                        # EM's free-form explanation (audit reads, doesn't parse)
    confidence_hint: Optional[float]           # EM-self-reported routing confidence in [0,1]; NOT used for gating
    ts: str                                    # ISO-8601 UTC


# Stored on SessionTreeNode (additive attribute, like node.transitions)
node.routing_rationales: list[RoutingRationale]   # append-only
```

**Why structured (not free text):** O6's forcing function needs to programmatically diff misroutes (Reviewer-B claims `actual_domain="ai"` but EM dispatched `worker_role="backend"`). Free text needs an NLP layer to parse; structured `chosen_role` makes the diff a string compare.

**Why `confidence_hint` is `Optional[float]` and explicitly NOT used for gating:** Cage invariant #3 ("self-reported confidence = theater"). The EM may *hint* at its own confidence; the harness logs it for audit; **no gate consumes it**. O6 can use it as a calibration signal (does EM low-confidence correlate with misroutes?).

### Q4 — Kill / Re-scope Lineage

ORCHESTRATION-PLAN §4 invariant #7 + decision #17: *"Killed/re-scoped cards = first-class audit surface."*

**Existing patterns to mirror:**

- O1 `mutate_envelope(node, delta, cwd)` (`session_tree.py:121`): single guarded funnel. Upward delta → record `rejected_raises` entry + raise. **Single mutator + record-on-attempt is the established cage pattern.**
- O1 `finalize_node(node, exit_reason=…)` (`session_tree.py:100`): idempotent close-write, never deletes. **Closing a node ≠ deleting a node.** The node persists at `.voss/sessions/<root_id>/<node_id>.json` forever.

**Recommendation: kill = finalize-with-reason; rescope = finalize + spawn new child with `lineage_parent_id` pointer.**

```python
# voss/harness/board/lineage.py  (new module — O5 owned)
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class KillRecord:
    """Why a card was killed by the EM.

    Stored on the killed card's SessionTreeNode under `node.kill_record`
    (Optional[KillRecord] — present iff the node was EM-killed; absent for
    naturally-terminating Done/Blocked cards).
    """
    card_id: str
    killed_at: str                              # ISO-8601 UTC
    rationale_text: str                         # EM's free-form reason
    successor_card_id: Optional[str] = None     # set when kill is part of a rescope


@dataclass(frozen=True, slots=True)
class RescopeRecord:
    """When the EM kills a card and spawns a replacement with new scope/role/AC.

    Stored on the SUCCESSOR card's SessionTreeNode as a single attribute
    `node.rescope_record`. Reading the predecessor's `node.kill_record.successor_card_id`
    gives the forward lineage link; reading the successor's
    `node.rescope_record.predecessor_card_id` gives the back link. Bidirectional;
    O6 walks either direction.
    """
    predecessor_card_id: str
    successor_card_id: str
    diff_summary: str                           # e.g. "scope: src/api/** -> src/web/**; role: backend -> frontend"
    rationale_text: str
    rescoped_at: str
```

**Kill flow:**
1. `EMBoardHandle.kill_card(card_id, rationale_text)` → set `node.kill_record = KillRecord(…)` → call O1 `finalize_node(node, exit_reason="killed", final="<em-killed>")`. **`EXIT_REASONS` needs `"killed"` added** — additive, same playbook as O3's open question 5 (`"timeout"`).
2. `node.transitions` gets a `forced→Blocked(reason="em_killed")` entry. Audit invariant preserved.

**Rescope flow:**
1. `EMBoardHandle.rescope_card(card_id, new_role=…, new_scope=…, …, rationale)`:
   - Calls `kill_card(card_id, rationale)` internally.
   - Allocates a new child node via O1 `SessionTreeManager.allocate_child(limit=…)`.
   - Creates a new `Ticket` with `lineage_parent_id = old_card_id`.
   - Sets `node[new].rescope_record = RescopeRecord(predecessor=old, successor=new, diff=…)`.
   - Backfills `node[old].kill_record.successor_card_id = new_card_id`.

**Lineage never breaks the tree.** The killed node's JSON file at `.voss/sessions/<root_id>/<old_id>.json` is sealed and read-only after finalize (O1 guarantee). The new node sits as a sibling under the same root. Bidirectional pointers let O6 walk lineage in O(1).

**Why no deletion ever:** preserves Leak-3 mitigation (planner avoidance) — the EM cannot make a card "disappear" to hide a bad route. Every card that ever existed is on disk, sealed, replayable.

### Q5 — Cage-Bound EM Enforcement (`EMBoardHandle` facade)

ORCHESTRATION-PLAN §4 invariants 1–3: EM cannot rewrite `ceiling`/`p`, cannot invent agents, cannot extend budget. O2 already enforces this at compile (`TeamConfig` is `@dataclass(frozen=True, slots=True)` — `voss/harness/team.py:211`; `mutate_envelope` rejects upward deltas — `session_tree.py:121`).

**Problem:** if O5 hands the EM a raw `Board` instance, the EM can in principle call `board._cards` directly, or construct a new `Card` with arbitrary scope, or `board._team_config` and read but then mutate via Python (frozen dataclass is *suggestion*, not security — `object.__setattr__` works around `frozen=True`).

**Recommendation: `EMBoardHandle` facade that exposes ONLY the legal EM verbs.** Cage by API surface area, not by trust.

```python
# voss/harness/board/em_handle.py  (new module — O5 owned)
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence

from voss.harness.board.machine import Board, Card
from voss.harness.board.ticket import Ticket
from voss.harness.board.routing import RoutingRationale
from voss.harness.board.lineage import KillRecord, RescopeRecord
from voss.harness.team import TeamConfig
from voss.harness.subagents import SubagentRegistry


class EMCageViolation(Exception):
    """Raised when the EM attempts an op outside its legal verb set.

    Includes: unknown role IDs, budget extension, ceiling/p mutation, dispatch
    to an empty/closed card, kill of a Done card, rescope of a Blocked card.
    """
    def __init__(self, op: str, reason: str) -> None:
        self.op = op
        self.reason = reason
        super().__init__(f"EM cage violation in {op}: {reason}")


@dataclass(frozen=True, slots=True)
class BoardSnapshot:
    """Read-only board+roster view the EM sees per iteration.

    Snapshot = pure-Python value object. EM cannot mutate via the snapshot;
    mutations only land via EMBoardHandle methods (the audited surface).
    """
    cards: tuple[Card, ...]
    tickets: tuple[Ticket, ...]
    roster_role_ids: tuple[str, ...]
    ceiling_budget_tokens: Optional[int]        # read-only — EM cannot widen
    ceiling_scope_globs: tuple[str, ...]         # read-only — EM cannot widen
    p_thresholds: dict[str, float]               # read-only — EM cannot override
    prior_rationales: tuple[RoutingRationale, ...]  # all rationales emitted so far this run
    iteration: int


class EMBoardHandle:
    """The ONLY surface the EM's plan ops are allowed to touch.

    Constructor is harness-private; the EM never instantiates this. The harness
    constructs one EMBoardHandle per run and passes it to the EM loop.
    """

    def __init__(
        self,
        *,
        board: Board,                             # O3-owned; not exposed to EM
        registry: SubagentRegistry,               # O2-owned; not exposed to EM
        team_config: TeamConfig,                  # O2-owned; not exposed to EM
        manager,                                  # SessionTreeManager (O1) — not exposed to EM
    ) -> None:
        self._board = board
        self._registry = registry
        self._team_config = team_config
        self._manager = manager

    # ----- READ surface (snapshot is the only window the EM sees) -----

    def snapshot(self) -> BoardSnapshot: ...

    def all_cards_terminal(self) -> bool: ...

    # ----- WRITE surface (legal EM verbs only) -----

    def create_ticket(
        self, *, original_idea: str, acceptance_criteria: Sequence[str],
        dod: Sequence[str], worker_role: str, domain: str = "code",
        risk_tier: str = "med",
    ) -> Ticket:
        """Idea -> ticket. Validates worker_role against registry; calls
        Board.spawn_card; allocates child budget node via O1; binds ticket to card."""

    def set_ac(self, card_id: str, acceptance_criteria: Sequence[str]) -> Ticket: ...
    def set_dod(self, card_id: str, dod: Sequence[str]) -> Ticket: ...

    def dispatch_card(
        self, *, card_id: str, role_id: str, task: str,
        rationale_text: str, candidates_considered: Sequence[str],
        confidence_hint: Optional[float] = None,
    ) -> RoutingRationale:
        """Run the picked specialist on the card.

        - Validates role_id against team_config.roster_ids; raises EMCageViolation
          if unknown.
        - Looks up the card; raises if column not in {Planned, InProgress}.
        - Derives per-role gate via gate_for_role(spec, base_gate) (O2-03 shipped).
        - Derives toolset via filter_toolset_for_role(spec, base_toolset).
        - Calls subagents.run_subagent(node=child_node, reserve=…) — uses O1 finalize.
        - Emits RoutingRationale onto the child node + returns it for the EM's record.
        """

    def kill_card(self, card_id: str, rationale_text: str) -> KillRecord: ...

    def rescope_card(
        self, *, card_id: str, new_worker_role: str, new_scope: Optional[str],
        new_acceptance: Sequence[str], rationale_text: str,
    ) -> RescopeRecord: ...

    async def tick(self) -> None:
        """Single Board.tick() pass (O3-shipped). EM has no other scheduler hook."""
        self._board._tick_once(now=self._board._clock())

    def force_block_all(self, reason: str) -> None:
        """Emergency drain: force every non-terminal card to Blocked(reason). Used
        when the EM iteration ceiling is hit. Not callable by the EM directly —
        only by the harness driver."""

    def finalize_run(self) -> "RunFinal": ...

    # ----- DELIBERATELY ABSENT methods (cage by omission) -----
    # - No set_ceiling, set_p, set_budget, extend_budget — invariants 1, 3.
    # - No register_role, set_role_scope — invariant 2 ("cannot invent agents").
    # - No direct access to self._board, self._team_config, self._manager.
    # - No method that returns the raw Board, SubagentRegistry, or TeamConfig.
```

**Cage proof:** any EM-side op must go through `EMBoardHandle.<verb>`. The EM agent's tool surface only registers these verbs as callable tools (`@tool` decorators wrapping the handle methods). Mutation of `ceiling`/`p`/budget is unreachable.

### Q6 — EM LLM Call Shape

**Existing structured-output pattern in repo:**

- `voss/eval/judge.py:judge_run` (lines 30–62): `provider.complete(messages=[...], model=…, response_format=Verdict, temperature=0.0)`. `Verdict` is a pydantic `BaseModel` with `model_config = ConfigDict(extra="ignore")`.
- `voss/harness/cognition_schemas.py`: pydantic v2 strict (`extra="forbid"`) for config files.
- `voss/harness/agent.py:658`: `response_format=Plan` for the agent's plan output (full `run_turn` loop).

**Recommendation: pydantic strict model + single `provider.complete` call per iteration.** Do NOT use the full `run_turn` agent loop — the EM is a planner, not a tool-using worker.

```python
# voss/harness/board/em_schema.py  (new module — O5 owned)
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


STRICT = ConfigDict(extra="forbid")


class CreateTicketOp(BaseModel):
    model_config = STRICT
    op: Literal["create_ticket"]
    original_idea: str
    acceptance_criteria: list[str]
    dod: list[str]
    worker_role: str                            # validated against registry; cage refuses unknown
    domain: Literal["code", "ai"] = "code"
    risk_tier: Literal["low", "med", "high"] = "med"


class DispatchCardOp(BaseModel):
    model_config = STRICT
    op: Literal["dispatch_card"]
    card_id: str
    role_id: str
    task: str
    rationale_text: str
    candidates_considered: list[str]
    confidence_hint: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class KillCardOp(BaseModel):
    model_config = STRICT
    op: Literal["kill_card"]
    card_id: str
    rationale_text: str


class RescopeCardOp(BaseModel):
    model_config = STRICT
    op: Literal["rescope_card"]
    card_id: str
    new_worker_role: str
    new_scope: Optional[str] = None
    new_acceptance: list[str]
    rationale_text: str


class SetACOp(BaseModel):
    model_config = STRICT
    op: Literal["set_ac"]
    card_id: str
    acceptance_criteria: list[str]


class SetDoDOp(BaseModel):
    model_config = STRICT
    op: Literal["set_dod"]
    card_id: str
    dod: list[str]


class NoopOp(BaseModel):
    """Returned when the EM has nothing to add this iteration; just wait for tick."""
    model_config = STRICT
    op: Literal["noop"]
    reason: str = ""


EMOp = (
    CreateTicketOp | DispatchCardOp | KillCardOp | RescopeCardOp
    | SetACOp | SetDoDOp | NoopOp
)


class EMPlanResponse(BaseModel):
    """One iteration's worth of EM-planned operations.

    The harness executes ops in declared order via EMBoardHandle. Invalid ops
    (unknown role_id, kill of Done card, etc.) raise EMCageViolation and are
    logged as `node.transitions[*].outcome == 'refused'` so the EM sees the
    refusal on its next snapshot and can replan.
    """
    model_config = STRICT
    ops: list[EMOp] = Field(default_factory=list, max_length=20)   # cap blast radius per iter
    reasoning: str = ""                                              # free-form EM scratchpad


# EM LLM call shape (mirrors judge_run):
async def em_plan(
    *,
    provider,
    model: str,
    idea: str,
    snapshot: BoardSnapshot,
    roster_descriptions: dict[str, str],
) -> EMPlanResponse:
    user_msg = (
        f"## Original Idea (audit bar — IMMUTABLE)\n{idea}\n\n"
        f"## Roster\n{format_roster(roster_descriptions)}\n\n"
        f"## Ceiling (cannot widen)\n"
        f"- budget_tokens: {snapshot.ceiling_budget_tokens}\n"
        f"- scope: {snapshot.ceiling_scope_globs}\n"
        f"- p_thresholds: {snapshot.p_thresholds}\n\n"
        f"## Board snapshot\n{format_snapshot(snapshot)}\n\n"
        f"## Prior routing rationales\n{format_rationales(snapshot.prior_rationales)}\n"
    )
    resp = await provider.complete(
        messages=[
            {"role": "system", "content": EM_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        model=model,
        response_format=EMPlanResponse,
        temperature=0.2,
    )
    if resp.parsed is None:
        # ParseError -> safe default: do nothing this iteration
        return EMPlanResponse(ops=[NoopOp(op="noop", reason="parse_failure")])
    return resp.parsed
```

**Why per-iteration `provider.complete`, not `run_turn`:**
- `run_turn` (`voss/harness/agent.py:412`) is for tool-using agents; the EM does not use tools itself, it emits plan ops the harness executes. Bypassing `run_turn` saves the cognition cycle + token-budget overhead.
- `provider.complete(response_format=...)` matches the `judge_run` pattern, which is the closest precedent (LLM-as-planner with structured output, no tool loop).
- Each iteration is one provider call. Easy to mock, easy to budget (one call per `em_loop` iteration; iteration count is the budget knob).

**Why STRICT (`extra="forbid"`):** Cage hygiene. If the EM tries to invent a field (`extend_budget: 50000`), pydantic rejects at parse time and the op is logged as a refused parse — never reaches `EMBoardHandle`.

### Q7 — Specialist Dispatch Path

**End-to-end shape** for `EMBoardHandle.dispatch_card`:

```python
def dispatch_card(
    self, *, card_id: str, role_id: str, task: str,
    rationale_text: str, candidates_considered: Sequence[str],
    confidence_hint: Optional[float] = None,
) -> RoutingRationale:
    # 1. Cage check: role must be in compiled roster (cannot invent agents).
    if role_id not in self._team_config.roster_ids:
        raise EMCageViolation(
            "dispatch_card",
            f"unknown role {role_id!r}; legal: {sorted(self._team_config.roster_ids)}",
        )

    # 2. Card check: card exists and is dispatchable.
    card = self._board.get_card(card_id)
    if card is None:
        raise EMCageViolation("dispatch_card", f"unknown card {card_id!r}")
    if card.column not in ("Planned", "InProgress"):
        raise EMCageViolation(
            "dispatch_card",
            f"card {card_id} in column {card.column!r}; only Planned/InProgress dispatchable",
        )

    # 3. Look up the per-role compiled spec (O2-shipped registry).
    spec = self._registry.get(role_id)
    assert spec is not None                          # invariant: roster_ids ⊆ registry.ids()

    # 4. Derive per-role gate + toolset (O2-03 shipped helpers).
    from voss.harness.team import gate_for_role, filter_toolset_for_role
    role_gate = gate_for_role(spec, self._base_gate)
    role_tools = filter_toolset_for_role(spec, self._base_toolset)

    # 5. Allocate per-card child budget envelope via O1 SessionTreeManager
    #    (already done at spawn_card time; reuse the existing child node).
    child_node = self._manager.get_node(card.node_id)
    assert child_node is not None

    # 6. Emit routing rationale BEFORE dispatch (so even a crashed dispatch
    #    leaves the audit trail).
    rationale = RoutingRationale(
        id=uuid.uuid4().hex[:12],
        card_id=card_id,
        chosen_role=role_id,
        candidates_considered=tuple(candidates_considered),
        rationale_text=rationale_text,
        confidence_hint=confidence_hint,
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    child_node.routing_rationales.append(rationale)
    _write_node_file(child_node, self._cwd)          # persist (O1 pattern)

    # 7. Patch the ticket's worker_role + routing_rationale_id (frozen replace).
    old_ticket = self._board.get_ticket(card_id)
    new_ticket = dataclasses.replace(
        old_ticket, worker_role=role_id, routing_rationale_id=rationale.id,
    )
    self._board.set_ticket(card_id, new_ticket)

    # 8. Move card Planned -> InProgress (O3 gate, may refuse).
    self._board.move(card, to="InProgress")

    # 9. Spawn the specialist via the O1 finalize boundary.
    #    Note: this is asyncio.create_task — fire-and-forget; Board.tick will
    #    drive the card to InReview when the subagent finalizes.
    asyncio.create_task(run_subagent(
        agent_id=role_id,
        task=task,
        registry=self._registry,                     # but the registry is filtered for the dispatched role only
        cwd=self._cwd,
        renderer=self._renderer,
        provider=self._provider,
        model=spec.model or self._default_model,
        gate=role_gate,                              # <-- O2-03 per-role gate
        cognition=self._cognition,
        node=child_node,                             # <-- O1 finalize boundary
        reserve=self._reserve,                       # <-- O1 reserved drain
    ))

    return rationale
```

**Why fire-and-forget asyncio.create_task:** the dispatch returns immediately so the EM's plan can dispatch multiple cards in one iteration (subject to `InProgress` WIP cap). Board.tick() observes when each card's node has finalized and moves it through `InReview` → `Done`/`Blocked` per O3 gates.

**Why the EM's tool exposes `dispatch_card(role_id, task, …)` and NOT raw `subagent_run(agent, task)`:** O2-03 SUMMARY line 56 said *"EM tool surface must not expose arbitrary `PermissionGate(...)` construction"*. By making `dispatch_card` the only public dispatch verb, the EM cannot bypass `gate_for_role` and cannot invoke `run_subagent` with a freshly-constructed permissive gate.

### Q8 — Misroute Audit Surface (what O6 reads)

Residual #4 (accepted): misroute caught at sign-off only. O5 must EMIT the data O6 will surface.

**Minimum data O6 needs to build a "misroute diff" view:**

1. **EM's claimed routing** — `RoutingRationale.chosen_role`, `RoutingRationale.candidates_considered`, `RoutingRationale.rationale_text`. Already covered by Q3.
2. **Reviewer-B's domain assessment** — O4's `ReviewerVerdict` has `verdict: Literal["pass","fail","block"]` and `notes: str` (per O3-SPEC REQ-7). Recommend O5 *also* requires O4 to emit a `domain_inferred: Optional[Literal["code","ai"]]` field on `ReviewerVerdict` — **flag as cross-phase coordination point** (O4 is still planned, not shipped, so this can land in O4 implementation rather than as an O3 schema change).

   - **Fallback if O4 owners refuse:** O5 emits a `node.domain_signals: list[DomainSignal]` attribute populated by Reviewer-B notes parsing (regex on the notes for `"AI"`, `"backend"`, `"frontend"`). Worse fidelity, no cross-phase change required. **Recommend the cleaner path.**
3. **Original ticket scaffolding vs. actual artifact** — `Ticket.worker_role`, `Ticket.domain`, `Ticket.acceptance_criteria` + `Card.artifact` (set by the worker on finalize). O6 diffs `Ticket.worker_role` vs. `Reviewer-B.domain_inferred`; a mismatch is a misroute candidate.
4. **Kill / rescope lineage** — `KillRecord`, `RescopeRecord`. O6 surfaces rescopes where the predecessor's `worker_role` ≠ successor's `worker_role` as "EM mid-flight misroute correction" (a legitimate, audit-noted action).
5. **Per-card outcome counts** — Done / Blocked / Killed counts at the root node. The EM's `finalize_run()` should emit a `RunFinal` summary on the root node:

   ```python
   @dataclass(frozen=True, slots=True)
   class RunFinal:
       root_id: str
       idea: str
       total_cards: int
       done_count: int
       blocked_count: int
       killed_count: int
       rescope_count: int
       em_iterations: int
       ts: str
   ```

   Persisted at `.voss/sessions/<root_id>/_run_final.json` (sibling of the per-node files, leading underscore to distinguish).

**Audit fields summary table** (what lives where, for O6's consumption):

| Field | Lives on | Emitted by | Read by |
|-------|----------|------------|---------|
| `RoutingRationale` | `node.routing_rationales[]` | `EMBoardHandle.dispatch_card` | O6 misroute diff |
| `KillRecord` | `node.kill_record` | `EMBoardHandle.kill_card` | O6 killed-card view |
| `RescopeRecord` | `node.rescope_record` (on successor) | `EMBoardHandle.rescope_card` | O6 lineage view |
| `Ticket` | `node.tickets[0]` | `EMBoardHandle.create_ticket` | O6 + Reviewer-A/B |
| `ReviewerVerdict.domain_inferred` | `node.transitions[*].verdict_snapshot` (O3) | O4 Reviewer-B | O6 misroute diff |
| `RunFinal` | `.voss/sessions/<root_id>/_run_final.json` | `EMBoardHandle.finalize_run` | O6 summary view |

---

## Validation Architecture (2-layer)

### Layer 1 — Pure unit tests (no O3/O4 implementation required)

**Approach: stub the O3 + O4 interfaces so O5 unit tests run BEFORE O3 ships.**

- `StubBoard` — implements the O3 `Board` shape O5 calls (`spawn_card`, `move`, `get_card`, `cards`, `_tick_once`). In-memory only. Tracks `node.transitions` as a list. No real session-tree integration.
- `StubManager` — implements `SessionTreeManager.get_node(node_id)`, `allocate_child(limit)`. Returns minimal `SessionTreeNode` shells.
- `DeterministicEMStub` — pure-Python implementation of the `em_plan(...)` interface. Constructor takes a `list[EMPlanResponse]`, yields them in order. **Matches the O3 `DeterministicReviewerStub` pattern (`voss/harness/board/stub.py`).**

  ```python
  # tests/harness/test_em_stub.py
  class DeterministicEMStub:
      def __init__(self, scripted: list[EMPlanResponse]) -> None:
          self._queue = list(scripted)

      async def plan(self, *, idea: str, snapshot: BoardSnapshot) -> EMPlanResponse:
          return self._queue.pop(0) if self._queue else EMPlanResponse(ops=[NoopOp(op="noop")])
  ```

**Unit test coverage (W3–W5):**

| Test ID | What it pins | OEM-N |
|---------|--------------|-------|
| `test_em_handle_rejects_unknown_role` | `EMBoardHandle.dispatch_card("phantom")` raises `EMCageViolation` | OEM-04 |
| `test_em_handle_rejects_budget_extend` | No method on handle accepts a budget delta; introspection check | OEM-04 |
| `test_em_handle_snapshot_is_read_only` | mutating `snapshot.cards[0]` does not affect board | OEM-04 |
| `test_create_ticket_binds_to_card` | `create_ticket` calls `board.spawn_card` and `node.tickets` gets one entry | OEM-01 |
| `test_dispatch_emits_routing_rationale` | dispatch appends a `RoutingRationale` to `node.routing_rationales` | OEM-02, OEM-07 |
| `test_kill_card_preserves_node` | `kill_card` finalizes node but `_write_node_file` still readable | OEM-03 |
| `test_rescope_links_lineage_both_ways` | `node[old].kill_record.successor_card_id == new_id`; `node[new].rescope_record.predecessor_card_id == old_id` | OEM-03 |
| `test_em_loop_terminates_on_all_done` | `em_loop` with scripted "create+dispatch+stub-pass" exits with all cards Done | OEM-06, OEM-10 |
| `test_em_loop_iteration_ceiling` | `max_iterations=3` forces `force_block_all`; all cards Blocked | OEM-06 |
| `test_em_plan_response_strict_extra_forbid` | Pydantic rejects `EMPlanResponse(ops=[{"op":"create_ticket","extend_budget":50000}])` at parse | OEM-05 |
| `test_misroute_signal_present_on_node` | After dispatch, `node.routing_rationales[0].chosen_role` + (mocked) `node.transitions[-1].verdict_snapshot["domain_inferred"]` both readable | OEM-09 |

**Test framework:** pytest, `asyncio_mode=auto` already configured in `pyproject.toml` (O4-01-PLAN line 149 confirms). Tests live at `tests/harness/test_em_*.py`. Reuse `tests/parser/examples/team_strawman.voss` to source a real `TeamConfig`.

**No live LLM calls in unit tests.** All EM LLM calls go through `DeterministicEMStub`. The real `em_plan` function gets exactly ONE test (`test_em_plan_calls_provider_complete_with_response_format`) that asserts the provider call shape — mocked `provider.complete` returning a canned `EMPlanResponse`.

### Layer 2 — Integration tests (once O3 + O4 ship)

Run only after O3-04 + O4-04 are green. Verify:

1. Full board run with real `Board`, real `DeterministicReviewerStub` (O3-shipped), `DeterministicEMStub`. Idea → Ticket → Dispatch → InReview → Done. Asserts on `node.transitions` count, `RunFinal` shape.
2. Critic-loop integration: a `DeterministicReviewerStub(verdict="fail")` for 3 rounds drives card to `Blocked(retry_ceiling)`. EM observes the Blocked status in next snapshot and emits a `RescopeRecord` op.
3. Misroute integration: dispatch a "code" ticket to `worker_role="ai"`; the reviewer-B stub returns `domain_inferred="code"` (mismatch). The mismatch is readable on `node.routing_rationales[-1].chosen_role` + `node.transitions[-1].verdict_snapshot`.

**No live LLM** even in integration. Use `voss_runtime.StubProvider` for `provider.complete` calls.

### Layer 3 (optional, not required for O5 acceptance) — Live e2e

A single live-LLM smoke test: run a tiny `team{}` block with a real provider (Anthropic key from `~/.voss/keys/`) and a 5-line idea. **Skipped in CI** unless `VOSS_LIVE_TEST=1`. Out of acceptance gate scope (lots of cost, slow). Only for hand-verification.

### Sampling rates

- **Per task commit:** `pytest tests/harness/test_em_*.py -q` (target < 10s)
- **Per wave merge:** `pytest tests/harness/ tests/voss/ -q` (target < 60s)
- **Phase gate:** Full `pytest -q` green; integration tests added in W5 against the merged O3/O4 codebase.

### Wave 0 Gaps

- `tests/harness/test_em_handle.py` — new
- `tests/harness/test_em_loop.py` — new
- `tests/harness/test_em_schema.py` — new (pydantic STRICT validation)
- `tests/harness/test_em_lineage.py` — new (kill/rescope/run_final)
- No new fixtures beyond `team_strawman.voss` reuse

---

## Planning Implications — Recommended Wave Breakdown

### W0 — Substrate Gate (no code, only verification)
**Goal:** Confirm O3 and O4 frozen interfaces match O5's assumptions before any O5 task lands.

- Verify `from voss.harness.board.machine import Board, Card` works.
- Verify `from voss.harness.board.verdict import ReviewerVerdict, Reviewer` works.
- Verify `Card` has fields `(node_id, column, risk_tier, retry_count, deadline, scope, artifact, eval_threshold)`.
- Verify `Reviewer.review(...)` signature (sync or async; if `Reviewer.review(card: Card)` not `(ticket: Ticket)`, raise an O3-amendment coordination request).
- Verify `SessionTreeManager.get_node` exists.
- Verify O4-A and O4-B are shipped or stubs are in place.
- **If ANY gate fails: STOP and surface the dependency drift in W0-SUMMARY.md.** O5 is hard-blocked on O3/O4.

### W1 — EM Data Model
**Goal:** All frozen value-objects in a new `voss/harness/board/em/` subpackage.

- `voss/harness/board/em/__init__.py` — public surface.
- `voss/harness/board/em/ticket.py` — `Ticket`, `Domain`, `WorkerRole`.
- `voss/harness/board/em/routing.py` — `RoutingRationale`.
- `voss/harness/board/em/lineage.py` — `KillRecord`, `RescopeRecord`, `RunFinal`.
- `voss/harness/board/em/errors.py` — `EMCageViolation`.
- Tests: `test_em_ticket.py`, `test_em_lineage.py` (kill/rescope pointer consistency).
- **Touches:** `voss/harness/session_tree.py` — additive `node.tickets`, `node.routing_rationales`, `node.kill_record`, `node.rescope_record` attributes; extend `_NODE_FIELDS`, `to_dict`, `_hydrate_node`. ALSO add `"killed"` to `EXIT_REASONS` in `voss/harness/session.py` (additive — same playbook as O3's `"timeout"` extension).
- No EM loop code yet.

### W2 — `EMBoardHandle` Facade
**Goal:** Cage-enforced verb surface over O3 Board.

- `voss/harness/board/em/handle.py` — `EMBoardHandle`, `BoardSnapshot`.
- Tests: cage-violation tests (`test_em_handle_rejects_*`), snapshot read-only tests, create_ticket binding tests.
- Uses `StubBoard` + `StubManager` (no real O3 dependency yet, so this wave can land BEFORE O3 ships if needed — gracefully degrades to "implementation-ready" status).
- **Does not** yet dispatch (no real `run_subagent` call); dispatch is W4.

### W3 — EM LLM Call + Schema + Stub
**Goal:** `em_plan(...)` + `EMPlanResponse` schema + `DeterministicEMStub`.

- `voss/harness/board/em/schema.py` — pydantic v2 STRICT models.
- `voss/harness/board/em/llm.py` — `em_plan(...)` function (mirrors `judge_run`).
- `voss/harness/board/em/stub.py` — `DeterministicEMStub` (mirrors O3 `DeterministicReviewerStub`).
- Tests: pydantic strict tests (extra fields rejected), one mocked-provider test for `em_plan` call shape.
- **No** new LLM provider code; reuses `voss_runtime.providers.base.ModelProvider`.

### W4 — EM Loop Driver + Dispatch Wiring
**Goal:** Loop reads idea → plans → dispatches → ticks → terminates.

- `voss/harness/board/em/loop.py` — `em_loop(...)` coroutine; iteration ceiling; `force_block_all` emergency drain.
- Wire `EMBoardHandle.dispatch_card` to `run_subagent(node=…, reserve=…)` (the O1 finalize boundary). Reuse `gate_for_role` + `filter_toolset_for_role` from O2-03.
- Tests: scripted-stub end-to-end (`test_em_loop_terminates_on_all_done`, `test_em_loop_iteration_ceiling`, critic-loop replay).
- **Touches `subagents.run_subagent`** if needed — but the current signature already accepts `gate: PermissionGate`, `node: SessionTreeNode | None`, `reserve: int = 0`, so no signature change. The new code in `EMBoardHandle.dispatch_card` *constructs* the per-role gate and passes it in.

### W5 — Acceptance + Integration (post O3/O4 merge)
**Goal:** Real Board + real Reviewer A/B (or A/B stubs from O4) end-to-end.

- Re-run W2–W4 tests against the real `voss.harness.board.machine.Board` (no stub).
- Integration test: full `team{}` strawman fixture → EM run with `DeterministicEMStub` + `DeterministicReviewerStub` → assert all cards Done.
- Misroute integration test: Reviewer-B returns `domain_inferred` mismatch; assert audit data is on the node.
- RunFinal persistence test: `.voss/sessions/<root_id>/_run_final.json` written; `_run_final.json` content matches expected counts.
- **No live LLM** in CI; live e2e smoke test gated on `VOSS_LIVE_TEST=1` (optional, off acceptance path).

**Total estimate:** ~5 waves, ~3-4 tasks each, similar to O3/O4 cadence.

---

## Module Layout (recommended)

```
voss/harness/board/em/             # NEW O5 subpackage; sibling to verdict.py, machine.py
├── __init__.py                    # public surface: EMBoardHandle, em_loop, Ticket, etc.
├── ticket.py                      # Ticket, Domain, WorkerRole
├── routing.py                     # RoutingRationale
├── lineage.py                     # KillRecord, RescopeRecord, RunFinal
├── errors.py                      # EMCageViolation
├── handle.py                      # EMBoardHandle + BoardSnapshot
├── schema.py                      # EMPlanResponse + all *Op pydantic models
├── llm.py                         # em_plan(...) function
├── stub.py                        # DeterministicEMStub for tests
└── loop.py                        # em_loop driver

tests/harness/
├── test_em_ticket.py
├── test_em_routing.py
├── test_em_lineage.py
├── test_em_handle.py              # cage violations + snapshot
├── test_em_schema.py              # pydantic STRICT
├── test_em_llm.py                 # mocked provider.complete
├── test_em_stub.py
├── test_em_loop.py                # end-to-end with stubs
└── test_em_misroute_signals.py    # OEM-09 audit emission
```

**Touched outside the subpackage:**
- `voss/harness/session.py` — add `"killed"` to `EXIT_REASONS` (additive).
- `voss/harness/session_tree.py` — additive `node.tickets`, `node.routing_rationales`, `node.kill_record`, `node.rescope_record`; extend `_NODE_FIELDS`, `to_dict`, `_hydrate_node`.
- `voss/harness/board/__init__.py` (O3-shipped) — re-export `em` submodule for convenience.

---

## Open Questions (RESOLVED)

| # | Question | Recommendation | Status |
|---|----------|---------------|--------|
| OQ-O5-1 | `Card` field gap — extend Card or wrap in Ticket? | **Wrap in `Ticket`.** Keeps O3's frozen Card minimal; O5 owns EM-authored scaffolding cleanly. | RESOLVED → Q2 |
| OQ-O5-2 | EM loop control — `voss_runtime.spawn`/`gather` vs harness scheduler? | **Harness scheduler over `Board.tick` + `run_subagent`.** spawn/gather silently swallows exceptions and bypasses the O1 finalize boundary. | RESOLVED → Q1 |
| OQ-O5-3 | Routing-rationale schema — free text or structured? | **Structured frozen dataclass** with `(id, card_id, chosen_role, candidates_considered, rationale_text, confidence_hint, ts)`. | RESOLVED → Q3 |
| OQ-O5-4 | Where do `KillRecord`/`RescopeRecord` live? | **On `SessionTreeNode` as additive attributes**, mirroring `node.transitions` and `node.retry_notes`. Never on `RunRecord` (preserves O1 SPEC-5). | RESOLVED → Q4 |
| OQ-O5-5 | EM LLM call — `run_turn` vs `provider.complete`? | **`provider.complete(response_format=EMPlanResponse, …)`** — mirrors `judge_run`; cheaper, more testable, no unnecessary tool loop. | RESOLVED → Q6 |
| OQ-O5-6 | How does the cage block EM from inventing roles or extending budget? | **`EMBoardHandle` facade** with deliberate method omission. EM never touches raw `Board`/`TeamConfig`/`SubagentRegistry`. | RESOLVED → Q5 |
| OQ-O5-7 | Reviewer Protocol signature — does it take `Card` or `Ticket`? | **Recommend O4 take `Ticket`** (or take `(card, ticket)` tuple). Surface this as a cross-phase coordination request to O4's planner before O4-02 lands. **Open coordination** — not a blocker if O5 lands after O4 since O5 can shim. | COORDINATION |
| OQ-O5-8 | `EXIT_REASONS` extension — `"killed"` needed for kill flow? | **Yes, additive.** Same playbook as O3 open question #5 (`"timeout"`). | RESOLVED → Q4 |
| OQ-O5-9 | Should `EMBoardHandle.dispatch_card` block until the subagent finishes, or fire-and-forget? | **Fire-and-forget `asyncio.create_task`.** Lets the EM dispatch multiple cards per iteration (subject to WIP cap); `Board.tick` drives the cards through terminal states. | RESOLVED → Q7 |
| OQ-O5-10 | Where does `RunFinal` live? | **`.voss/sessions/<root_id>/_run_final.json`** — leading underscore distinguishes from per-node files; root-node-scoped (one per run). | RESOLVED → Q8 |

**All 10 open questions resolved or surfaced as cross-phase coordination requests.** No unresolved ambiguity for the planner to negotiate at plan-time.

---

## Sources

### Primary (HIGH confidence — read source directly)
- `voss_runtime/agent.py:74–120` — `VossAgent.spawn`, `AgentHandle`, `gather` shapes.
- `voss_runtime/__init__.py` — public exports including `spawn`/`gather`/`AgentHandle`.
- `voss/harness/subagents.py` — `run_subagent` signature, finalize-boundary integration.
- `voss/harness/session_tree.py` — `SessionTreeNode`, `SessionTreeManager`, `mutate_envelope`, `finalize_node`, `_write_node_file`, audit-record pattern.
- `voss/harness/session.py` — `EXIT_REASONS`, `RunRecord` fixed-field invariant.
- `voss/harness/team.py` — `TeamConfig`, `gate_for_role`, `filter_toolset_for_role`.
- `voss/eval/judge.py` — `Verdict` pydantic shape + `provider.complete(response_format=Verdict)` pattern.
- `voss/harness/cognition_schemas.py` — pydantic v2 STRICT pattern (`extra="forbid"`).
- `voss/harness/agent.py:412,658,1395` — `run_turn` shape, `response_format=Plan` precedent.

### Secondary (MEDIUM confidence — read planning artifacts)
- `.planning/ORCHESTRATION-PLAN.md` §1–9 — O-track design, role table, cage invariants, decision log, residual risks.
- `.planning/ROADMAP.md` line 1570 — Phase O5 entry.
- `.planning/phases/O3-board-state-machine/O3-SPEC.md` — locked O3 requirements (9 reqs, Card shape, Reviewer Protocol, EXIT_REASONS gap).
- `.planning/phases/O3-board-state-machine/O3-CONTEXT.md` — module layout, transition-delta storage, get_node addition, EXIT_REASONS extension question.
- `.planning/phases/O3-board-state-machine/O3-01-PLAN.md`, `O3-02-PLAN.md` — Card definition (`scope`, `artifact`, `eval_threshold`), Reviewer Protocol signature, EXIT_REASONS additive playbook.
- `.planning/phases/O4-reviewer-ab-split/O4-CONTEXT.md`, `O4-RESEARCH.md`, `O4-01-PLAN.md` — Card field gap (lines 120, 191), Reviewer A/B implementation strategy, `judge_run`-as-online-gate reuse.
- `.planning/phases/O2-voss-team-spec-roster/O2-{01,02,03}-SUMMARY.md` — shipped `compile_team` + `gate_for_role` + `filter_toolset_for_role` APIs.
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-{01,02}-SUMMARY.md` — shipped `SessionTreeNode` + finalize boundary.

### Tertiary (LOW confidence — speculation flagged)
- None — every recommendation is grounded in shipped code or planned interfaces with named source.

---

## Metadata

**Confidence breakdown:**
- O1/O2 shipped surfaces (Q1, Q5, Q7): HIGH — read source.
- O3/O4 planned surfaces (Q2, Q4, Q5, Q6, Q8): MEDIUM — read SPEC + plans, not source (not yet executed).
- EM prompt content + routing-rationale wording (Q3, Q6 message format): LOW — no precedent. Owned by W3 implementation discovery.
- Pydantic STRICT pattern (Q6): HIGH — direct precedent in `cognition_schemas.py` and `judge.py`.

**Cross-phase coordination flags (planner must address):**
1. **O3↔O5 Reviewer signature.** O3-01-PLAN locks `Reviewer.review(card: object) -> ReviewerVerdict`. O5 wants `Ticket` to flow into the reviewer. Resolution: either O3 amends to `Reviewer.review(ticket: Ticket)` (need O3 SPEC amendment) OR O5 sets `ticket.card.artifact = ticket` so the reviewer reads ticket scaffolding via `card.artifact` (works but ugly). **Recommend O3 amendment when O5 plans against amended O3 — surface in W0 gate.**
2. **O4↔O5 `ReviewerVerdict.domain_inferred`.** O5's misroute audit needs B's domain assessment. O4 is unshipped — flag for O4 implementation to add this field. Fallback: O5 parses Reviewer-B notes (worse).
3. **`EXIT_REASONS` additions.** O3 wants `"timeout"`; O5 wants `"killed"`. Both additive, neither breaks redaction invariant. Land both in the W1 commit that touches `session.py`.

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (30 days — stable substrate; O3/O4 land in this window and may shift specifics)

---

*Phase: O5-engineering-manager-loop*
*Research authored: 2026-05-20*
*Next step: `/gsd-plan-phase O5` — produce O5-NN-PLAN.md files driven by O5-CONTEXT.md + this RESEARCH.md.*
