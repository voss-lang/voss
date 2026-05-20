---
phase: O5-engineering-manager-loop
plan: 02
type: tdd
wave: 2
depends_on:
  - O5-01
files_modified:
  - voss/harness/em/handle.py
  - voss/harness/em/protocols.py
  - voss/harness/em/__init__.py
  - tests/harness/em/test_em_handle.py
  - tests/harness/em/test_em_handle_cage.py
  - tests/harness/em/test_em_handle_dispatch.py
  - tests/harness/em/conftest.py
autonomous: true
requirements:
  - OEM-02
  - OEM-06
  - OEM-07
  - OEM-08
must_haves:
  truths:
    - "EMBoardHandle is the ONLY surface the EM's plan ops touch; raw Board / TeamConfig / SubagentRegistry are never exposed"
    - "Cage invariant 1: ceiling writes raise EMCageViolation('ceiling is EM-immutable')"
    - "Cage invariant 2: dispatch to a role NOT in TeamConfig.roster_ids raises EMCageViolation"
    - "Cage invariant 3: budget extension is unreachable (handle has no set_budget/extend_budget method; introspection check)"
    - "Cage invariant 4 (kill of a Done card): rejected with EMCageViolation"
    - "Per-role gate derived via gate_for_role(spec, base_gate); per-role toolset via filter_toolset_for_role(spec, base_toolset) — handle never widens"
    - "BoardSnapshot is a read-only value object; mutating snapshot.cards has no effect on the live board"
    - "Kill flow appends KillRecord to the node and calls finalize_node(exit_reason='killed'); the node JSON stays on disk"
    - "Rescope flow appends KillRecord to the predecessor node AND RescopeRecord to the successor node; bidirectional pointers consistent"
    - "Dispatch emits a RoutingRationale onto the child node BEFORE the subagent fires (audit-survives-crash invariant)"
    - "Every EM-emitted record uses kind='em.*'; never 'board.*' (L-02)"
    - "O3 Board is mocked via a typed Protocol seeded from O3-SPEC §7 — no import from voss.harness.board.*"
  artifacts:
    - path: "voss/harness/em/protocols.py"
      provides: "BoardProtocol, RecorderProtocol — typed mocks for O3 surface"
      contains: "class BoardProtocol"
    - path: "voss/harness/em/handle.py"
      provides: "EMBoardHandle facade + BoardSnapshot"
      contains: "class EMBoardHandle"
    - path: "tests/harness/em/test_em_handle.py"
      provides: "happy-path verb coverage (create_ticket / set_ac / set_dod / snapshot)"
    - path: "tests/harness/em/test_em_handle_cage.py"
      provides: "cage-invariant refusal coverage (1-4)"
    - path: "tests/harness/em/test_em_handle_dispatch.py"
      provides: "dispatch path: routing rationale emission, gate_for_role plumb, no SubagentSpec construction"
    - path: "tests/harness/em/conftest.py"
      provides: "shared StubBoard / StubRecorder / TeamConfig fixtures"
  key_links:
    - from: "voss/harness/em/handle.py"
      to: "voss/harness/em/tickets.py"
      via: "constructs RoutingRationale / KillRecord / RescopeRecord on every mutation"
      pattern: "from \\.tickets import"
    - from: "voss/harness/em/handle.py"
      to: "voss/harness/team.py"
      via: "calls gate_for_role + filter_toolset_for_role on dispatch"
      pattern: "from voss\\.harness\\.team import (gate_for_role|filter_toolset_for_role)"
    - from: "voss/harness/em/handle.py"
      to: "voss/harness/em/errors.py"
      via: "raises EMCageViolation on every illegal verb"
      pattern: "raise EMCageViolation"
---

<objective>
Land EMBoardHandle — the cage-bounded facade that is the EM's ONLY board API.
The handle exposes legal verbs (create_ticket / set_ac / set_dod /
dispatch_card / kill_card / rescope_card / snapshot / tick / finalize_run) and
refuses everything else with typed EMCageViolation errors. Cage invariants 1–3
from ORCHESTRATION-PLAN §4 are tested via direct illegal-call attempts;
invariant 4 (audit-bar) lives on the W4 loop's responsibility but the handle
emits the routing-rationale record W4 will preserve.

W2 cannot import from voss/harness/board/* (O3 not yet shipped). It defines
a `BoardProtocol` typed against O3-SPEC §7 and runs against a StubBoard in
conftest.py. W4 will swap to the live Board when O3 lands; the handle
signature does not change.

Purpose: Cage by API surface area (not by trust). Method omission is the
enforcement — set_ceiling / set_p / extend_budget / register_agent simply
do not exist on the handle, so the EM cannot reach them through ANY tool
call. The introspection test asserts this.

Output: 2 new modules (handle.py + protocols.py), one __init__.py update,
4 test files covering happy path / cage refusals / dispatch wiring / shared
fixtures.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/O5-engineering-manager-loop/O5-CONTEXT.md
@.planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md
@.planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md
@.planning/phases/O5-engineering-manager-loop/O5-00-SUMMARY.md
@.planning/phases/O5-engineering-manager-loop/O5-01-SUMMARY.md
@.planning/phases/O3-board-state-machine/O3-SPEC.md
@.planning/phases/O3-board-state-machine/O3-CONTEXT.md
@voss/harness/em/tickets.py
@voss/harness/em/errors.py
@voss/harness/team.py
@voss/harness/edit_scope.py
@voss/harness/session_tree.py
@voss/harness/subagents.py

<interfaces>
<!-- O3 frozen-on-paper Card shape (mock against this; do NOT import) -->

From O3-SPEC.md REQ-1 + O3-02-PLAN (FROZEN, not live):
```
@dataclass(frozen=True, slots=True)
class Card:
    node_id: str
    column: Column      # Literal[Backlog|Planned|InProgress|InReview|Blocked|Done]
    risk_tier: RiskTier # Literal[low|med|high]
    retry_count: int
    deadline: float
    scope: TeamRoleScope | None = None
    artifact: object | None = None
    eval_threshold: float = 1.0
```

From O3-SPEC.md REQ-7 (FROZEN, not live):
```
@dataclass(frozen=True)
class ReviewerVerdict:
    conf: float
    source: Literal["A","B"]
    tier: Literal["fast","strong"]
    verdict: Literal["pass","fail","block"]
    notes: str
    evidence_refs: tuple[str, ...]
```

<!-- O1 live (use real imports) -->

From voss/harness/session_tree.py:
  SessionTreeNode (LIVE) — for child node allocation in dispatch
  SessionTreeManager (LIVE) — allocate_child(limit)
  finalize_node(node, *, exit_reason, final, cwd) (LIVE)

<!-- O2 live (use real imports) -->

From voss/harness/team.py:
  TeamConfig (LIVE, frozen+slots) — .ceiling, .roster_ids (frozenset[str])
  gate_for_role(spec, base_gate) -> PermissionGate (LIVE)
  filter_toolset_for_role(spec, base_toolset) -> dict (LIVE)
  TeamRoleScope.is_contained_in(other) -> bool (LIVE)

From voss/harness/subagents.py:
  SubagentSpec (LIVE) — frozen dataclass
  SubagentRegistry (LIVE) — registry.get(id), registry.ids()
  run_subagent(*, agent_id, task, registry, cwd, renderer, provider, model,
    gate, cognition=None, node=None, reserve=0) -> str (LIVE)

<!-- W1-shipped -->

From voss/harness/em/tickets.py (W1 GREEN):
  Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal

From voss/harness/em/errors.py (W1 GREEN):
  EMCageViolation(op, reason)
</interfaces>

<facade_surface>
EMBoardHandle public methods (the legal EM verb set):

  READ:
    snapshot() -> BoardSnapshot          # read-only view; mutation futile
    all_cards_terminal() -> bool

  WRITE — ticket lifecycle:
    create_ticket(*, original_idea, acceptance_criteria, dod, worker_role,
                   domain="code", risk_tier="med") -> Ticket
    set_ac(card_id, acceptance_criteria) -> Ticket
    set_dod(card_id, dod) -> Ticket

  WRITE — board mutation:
    dispatch_card(*, card_id, role_id, task, rationale_text,
                   candidates_considered, confidence_hint=None) -> RoutingRationale
    kill_card(card_id, rationale_text) -> KillRecord
    rescope_card(*, card_id, new_worker_role, new_scope=None,
                  new_acceptance, rationale_text) -> RescopeRecord

  DRIVER:
    async tick() -> None                  # delegates to Board._tick_once
    force_block_all(reason) -> None       # harness-only, NOT EM-callable
    finalize_run() -> RunFinal

  DELIBERATELY ABSENT (cage by omission):
    NO set_ceiling, NO set_p, NO set_budget, NO extend_budget,
    NO register_role, NO mutate_team_config, NO direct _board / _registry
    / _team_config exposure.

Cage refusals (every illegal call raises EMCageViolation(op=..., reason=...)):
  - dispatch_card(role_id NOT in team_config.roster_ids)
  - dispatch_card(card_id with column NOT in {Planned, InProgress})
  - kill_card(card_id with column == "Done")
  - rescope_card(card_id with column == "Done")
  - rescope_card(new_scope outside ceiling.scope) — uses TeamRoleScope.is_contained_in
  - create_ticket(worker_role NOT in team_config.roster_ids)
</facade_surface>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: RED — BoardProtocol + cage-refusal + dispatch test scaffolds</name>
  <files>tests/harness/em/conftest.py, tests/harness/em/test_em_handle.py, tests/harness/em/test_em_handle_cage.py, tests/harness/em/test_em_handle_dispatch.py</files>
  <read_first>
    - voss/harness/em/tickets.py (W1 frozen records — the return types)
    - voss/harness/em/errors.py (W1 EMCageViolation)
    - voss/harness/team.py lines 87-150 (gate_for_role + filter_toolset_for_role)
    - voss/harness/subagents.py (run_subagent signature, SubagentRegistry)
    - voss/harness/session_tree.py (SessionTreeManager.allocate_child, finalize_node)
    - voss/harness/edit_scope.py lines 89-107 (allows_write — facade refusal precedent)
    - .planning/phases/O3-board-state-machine/O3-SPEC.md REQ-1 + REQ-7 (Card + ReviewerVerdict shapes for mock)
    - .planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md §Q5, §Q7
    - .planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md §"voss/harness/em/handle.py"
    - tests/harness/em/test_em_tickets.py (W1 pattern — pytest style)
  </read_first>
  <behavior>
    conftest.py provides fixtures that every handle test reuses:
      - `stub_board`: a minimal in-memory Board satisfying `BoardProtocol`
        (TBD in Task 2). Methods: spawn_card(node_id, column, risk_tier,
        deadline, scope) -> Card; get_card(card_id) -> Card | None;
        move(card, *, to) -> None; cards() -> tuple[Card,...];
        _tick_once(*, now) -> None. Card is a tiny frozen dataclass mirror
        of O3-SPEC REQ-1 living in conftest.py (NOT in production code).
      - `stub_recorder`: a SessionTreeManager seeded with a root node
        (tmp_path-rooted; real SessionTreeManager from O1 — not a stub).
      - `tiny_team_config`: builds a TeamConfig via compile_team using the
        existing tests/parser/examples/team_strawman.voss fixture; roster_ids
        ⊇ {"backend","frontend","ai"}.
      - `base_gate`: PermissionGate(mode="auto", auto_yes=True, …).
      - `make_handle`: factory taking the four above + a SubagentRegistry,
        returning EMBoardHandle. Used by every test.

    test_em_handle.py — happy path:
      - create_ticket returns a Ticket whose fields match the args;
        Ticket persisted somewhere observable (the StubBoard exposes a
        `tickets_by_card_id` dict for tests).
      - create_ticket with worker_role="backend" succeeds; with
        worker_role="phantom" raises EMCageViolation(op="create_ticket").
      - set_ac / set_dod returns a fresh Ticket with replaced fields;
        the prior Ticket is unchanged (frozen-replace, not in-place).
      - snapshot() returns BoardSnapshot whose .cards is a tuple (immutable);
        attempting `snapshot.cards.append(...)` raises AttributeError;
        mutating .cards[0] is impossible because Card is frozen.
      - all_cards_terminal() is True when every card column ∈ {Done, Blocked}.
      - tick() awaits and calls stub_board._tick_once exactly once.

    test_em_handle_cage.py — cage invariants 1–4:
      - INVARIANT 1: introspection — `dir(handle)` contains NONE of
        {set_ceiling, set_p, set_budget, extend_budget, register_role,
        register_agent, mutate_team_config}; getattr for any of those
        raises AttributeError.
      - INVARIANT 1b: handle does not expose `_board`, `_team_config`,
        `_registry`, `_manager` as anything other than underscore-prefixed
        (no plain alias). Test asserts these are not in `dir()` (they exist
        as instance attrs but Python's underscore convention is the cage
        signal; assert they don't appear in __all__/dir() filtered to
        non-underscore names).
      - INVARIANT 2: dispatch_card(role_id="phantom") raises
        EMCageViolation; exc.op == "dispatch_card"; exc.reason contains
        the legal-roster list.
      - INVARIANT 2b: create_ticket(worker_role="phantom") raises
        EMCageViolation; exc.op == "create_ticket".
      - INVARIANT 3: budget cannot be extended — no method takes a budget
        delta; introspection check + an explicit attempt
        `with pytest.raises(AttributeError): handle.extend_budget(50000)`.
      - INVARIANT 4 (column gate): kill_card on a card with column="Done"
        raises EMCageViolation(op="kill_card", reason contains "Done");
        rescope_card on a Done card likewise.
      - INVARIANT 5 (scope): rescope_card with new_scope outside
        ceiling.scope raises EMCageViolation; uses TeamRoleScope literal
        outside the strawman ceiling.

    test_em_handle_dispatch.py — dispatch wiring:
      - dispatch_card emits exactly one RoutingRationale via the child
        node's append surface (the W1 attribute strategy — see Task 2
        action below for where the rationale lands).
      - The emitted RoutingRationale.chosen_role == role_id;
        candidates_considered == tuple supplied; confidence_hint round-trips.
      - dispatch_card derives the per-role gate by calling
        team.gate_for_role(spec, base_gate); use a monkeypatch + a sentinel
        to assert gate_for_role was called once with the resolved spec.
      - dispatch_card derives the per-role toolset by calling
        team.filter_toolset_for_role(spec, base_toolset); same sentinel
        approach.
      - Handle does NOT construct any SubagentSpec; assert via
        monkeypatch on SubagentSpec.__init__ that it is never called inside
        the handle code path.
      - Handle does NOT call SubagentRegistry.register; same monkeypatch
        approach.
      - RoutingRationale is emitted BEFORE the run_subagent call fires;
        test injects a run_subagent stub that records call order and
        asserts the rationale exists on the node before the stub runs.
      - Kill flow (kill_card) appends a KillRecord to the node-side attr
        AND calls finalize_node(exit_reason="killed", …). The node JSON
        file at .voss/sessions/<root_id>/<node_id>.json STILL EXISTS after
        kill (L-04 append-not-delete).
      - Rescope flow (rescope_card) ALSO appends KillRecord to predecessor
        + RescopeRecord to a freshly-allocated successor child node;
        successor.lineage_parent_id == predecessor_card_id; predecessor's
        KillRecord.successor_card_id == successor.id (bidirectional).

    All tests RED today (handle.py doesn't exist). Confirm collection
    succeeds via the existing conftest infrastructure.
  </behavior>
  <action>
    Write four new files under tests/harness/em/. The conftest.py is shared
    by all three test files. Mock O3 Board via a small frozen-dataclass
    Card living in conftest.py + a StubBoard class satisfying BoardProtocol
    (define BoardProtocol locally in the test file or import it from
    voss.harness.em.protocols if Task 2 has already defined it — use a
    forward import; the import failure is part of the RED state).

    For monkeypatch sentinels on team.gate_for_role / filter_toolset_for_role
    / SubagentSpec.__init__ / SubagentRegistry.register, use
    `monkeypatch.setattr(voss.harness.team, "gate_for_role", sentinel_wrap)`
    where sentinel_wrap records the call and forwards to the real function.

    Run pytest; expect ImportError on voss.harness.em.handle and
    voss.harness.em.protocols, plus AssertionError for any tests that try
    to construct EMBoardHandle.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/test_em_handle.py tests/harness/em/test_em_handle_cage.py tests/harness/em/test_em_handle_dispatch.py -x -q --tb=short 2>&amp;1 | tee /tmp/o5-02-red.log; grep -qE "(ModuleNotFoundError|ImportError|AssertionError)" /tmp/o5-02-red.log &amp;&amp; echo EM_HANDLE_RED_OK</automated>
  </verify>
  <acceptance_criteria>
    - 4 new test files under tests/harness/em/ collect successfully.
    - Tests fail with ImportError on voss.harness.em.handle / protocols (the modules don't exist yet).
    - Existing tests/harness/em/ (W1) tests still pass.
  </acceptance_criteria>
  <done>RED tests committed.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: GREEN — implement EMBoardHandle + BoardProtocol</name>
  <files>voss/harness/em/protocols.py, voss/harness/em/handle.py, voss/harness/em/__init__.py</files>
  <read_first>
    - voss/harness/em/tickets.py (W1 records)
    - voss/harness/em/errors.py (W1 EMCageViolation)
    - voss/harness/team.py lines 87-185 (gate_for_role, filter_toolset_for_role, TeamRoleScope.is_contained_in)
    - voss/harness/subagents.py (SubagentRegistry.get, run_subagent signature)
    - voss/harness/session_tree.py (SessionTreeManager.allocate_child, finalize_node, _write_node_file)
    - voss/harness/edit_scope.py lines 89-107 (allows_write — facade refusal style)
    - tests/harness/em/conftest.py (the contract: BoardProtocol surface to satisfy)
    - tests/harness/em/test_em_handle*.py (Task 1 contracts)
  </read_first>
  <behavior>
    The implementation makes every Task 1 RED test pass. Constraints:

    - voss/harness/em/protocols.py: define `BoardProtocol(Protocol)` typed
      against O3-SPEC §7. Methods: `spawn_card(...)`, `get_card(...)`,
      `move(...)`, `cards()`, `_tick_once(*, now)`. Also define
      `Column = Literal["Backlog","Planned","InProgress","InReview","Blocked","Done"]`
      and a `CardProtocol(Protocol)` for the card shape (so handle.py type-checks
      against the protocol, not a concrete Card).

    - voss/harness/em/handle.py: define `BoardSnapshot` (frozen+slots) and
      `EMBoardHandle`. The handle constructor takes board: BoardProtocol,
      registry: SubagentRegistry, team_config: TeamConfig, manager:
      SessionTreeManager, base_gate: PermissionGate, cwd: Path, plus a
      `subagent_runner` injection (defaults to subagents.run_subagent) so
      tests can swap it.

    - The legal verbs each:
      - Validate cage invariants BEFORE any state mutation. The order is
        always: (a) cage check (raise EMCageViolation early), (b) emit
        audit record, (c) mutate state. Audit-survives-crash: the record
        lands first.
      - kill_card calls finalize_node(node, exit_reason="killed",
        final="<em-killed>", cwd=cwd) — uses the W1-shipped "killed"
        EXIT_REASONS member.
      - rescope_card: internally calls kill_card on the predecessor THEN
        allocates a new child via manager.allocate_child(limit=…) AND
        emits a RescopeRecord on the successor node. Bidirectional pointers
        set via dataclasses.replace on the predecessor's KillRecord
        (because frozen).
      - dispatch_card: routing-rationale-first; allocate the per-role
        gate via team.gate_for_role(spec, base_gate); per-role toolset
        via team.filter_toolset_for_role(spec, base_toolset); finally
        invoke `self._subagent_runner(agent_id=role_id, task=task,
        registry=registry, cwd=cwd, renderer=…, provider=…, model=…,
        gate=role_gate, cognition=None, node=child_node, reserve=…)`.
        Uses asyncio.create_task for fire-and-forget per RESEARCH Q7.

    - Where audit records live on the node:
      - Per RESEARCH Q3+Q4, the W1 ticket plan does NOT extend
        SessionTreeNode with `routing_rationales` / `kill_record` /
        `rescope_record` attributes (W1 stayed pure-data). W2 SHOULD NOT
        mutate SessionTreeNode shape — it would couple the facade to O1
        schema. Instead, the handle maintains an in-memory side-table
        `self._node_audit: dict[node_id, NodeAudit]` where NodeAudit is a
        small dataclass holding `routing_rationales: list[RoutingRationale]`,
        `kill_record: KillRecord | None`, `rescope_record: RescopeRecord | None`.
        The audit is persisted via the existing `_write_node_file` path by
        embedding the audit dict in the SessionTreeNode JSON envelope under
        a new top-level key when finalize_node is called. (For W2, the
        test asserts the in-memory side-table; W5 integration confirms the
        on-disk shape.)
      - This is intentional: the handle owns the audit; the SessionTreeNode
        keeps its O1-shaped fields. If a later phase decides to promote the
        audit fields onto SessionTreeNode directly, the handle's
        `_node_audit` becomes a simple proxy and the test contract holds.

    - Cage by omission: introspection MUST show no public method named
      set_ceiling / set_p / set_budget / extend_budget / register_role /
      register_agent / mutate_team_config. Underscore-prefixed attrs may
      exist (`_board`, `_team_config`, `_registry`, `_manager`,
      `_node_audit`, `_subagent_runner`, `_base_gate`) — that's the
      established Python privacy convention used elsewhere in harness.

    - voss/harness/em/__init__.py: extend the W1 __all__ to also export
      `EMBoardHandle`, `BoardSnapshot`, `BoardProtocol`, `CardProtocol`,
      `Column`. Re-exports come after the existing tickets/errors imports.

    Run pytest until all Task 1 RED tests flip GREEN.

    Run the W1 test suite to confirm zero regression:
      .venv/bin/python -m pytest tests/harness/em/ -x -q
  </behavior>
  <action>
    Implement the three files per the behavior contract:

    1. `voss/harness/em/protocols.py` — Protocols and Column literal.

    2. `voss/harness/em/handle.py` — EMBoardHandle class + BoardSnapshot
       frozen dataclass + the internal NodeAudit dataclass for the side
       table.

    3. `voss/harness/em/__init__.py` — Extend __all__ + imports.

    Iterate until every test green. Confirm cage-invariant introspection
    test passes (the prohibited method set is exhaustively checked).

    Document the audit-on-side-table decision in the SUMMARY (it differs
    from RESEARCH Q3 which assumed the audit went on the node directly;
    the side-table approach preserves O1 SPEC-5 strict-additive blast
    radius and lets W5 confirm the persistence shape).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/ -x -q --tb=short &amp;&amp; .venv/bin/python -c "from voss.harness.em import EMBoardHandle, BoardSnapshot, BoardProtocol; import inspect; methods = {m for m in dir(EMBoardHandle) if not m.startswith('_')}; forbidden = {'set_ceiling','set_p','set_budget','extend_budget','register_role','register_agent','mutate_team_config'}; assert methods.isdisjoint(forbidden), f'cage breach: {methods &amp; forbidden}'; legal = {'snapshot','all_cards_terminal','create_ticket','set_ac','set_dod','dispatch_card','kill_card','rescope_card','tick','force_block_all','finalize_run'}; assert legal &lt;= methods, f'missing legal verbs: {legal - methods}'; print('cage ok')" &amp;&amp; echo EM_HANDLE_OK</automated>
  </verify>
  <acceptance_criteria>
    - All Task 1 RED tests now GREEN.
    - W1 tests still GREEN (zero regression).
    - EMBoardHandle introspection: legal verbs present, forbidden verbs absent.
    - dispatch_card path uses gate_for_role + filter_toolset_for_role (asserted via monkeypatch sentinel).
    - dispatch_card path never calls SubagentSpec(...) or SubagentRegistry.register.
    - kill_card calls finalize_node(exit_reason="killed", …) using the W1-shipped EXIT_REASONS member.
    - rescope_card produces bidirectional KillRecord↔RescopeRecord pointers.
    - tests/harness/test_session_redaction.py still passes (W1 invariant preserved).
  </acceptance_criteria>
  <done>All tests GREEN; commit references OEM-02, OEM-06, OEM-07, OEM-08.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| EM LLM ↔ EMBoardHandle | LLM-generated plan ops cross this boundary; the handle is the only legitimate execution surface. |
| EMBoardHandle ↔ raw Board / TeamConfig / SubagentRegistry | Cage; the handle must never re-expose these. |
| dispatch_card ↔ run_subagent (gate plumbing) | Per-role gate / toolset derived via O2 helpers; widening here would breach the per-role cage. |
| kill / rescope ↔ session-tree node JSON on disk | Append-not-delete contract; deletion would breach Leak-3 (planner avoidance). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O5-01 | Tampering / Elevation | EM rewrites ceiling/p | mitigate | EMBoardHandle has no set_ceiling/set_p method; introspection test fails the build if a setter is ever added. |
| T-O5-02 | Spoofing | EM dispatches to a non-roster agent | mitigate | dispatch_card validates role_id ∈ team_config.roster_ids; EMCageViolation otherwise; tests cover the negative path. |
| T-O5-03 | Elevation | EM widens its per-role gate via run_subagent | mitigate | dispatch_card derives gate via gate_for_role (cap-not-expand) and toolset via filter_toolset_for_role; handle never accepts a caller-supplied gate. |
| T-O5-04 | Tampering | kill / rescope deletes the session-tree node | mitigate | kill_card uses finalize_node (seals, never deletes); rescope_card allocates a NEW child via manager.allocate_child; predecessor JSON stays on disk; test reads it after the op. |
| T-O5-05 | Repudiation | dispatch runs without an audit record | mitigate | RoutingRationale emitted BEFORE run_subagent fires; test injects a slow subagent stub and asserts the rationale exists on the side-table before the subagent runs. |
| T-O5-06 | Tampering | O3 Card field gap silently bypassed | mitigate | Handle exposes Ticket (W1) — never raw Card; W5 integration verifies the wrapper bridges the gap. |
</threat_model>

<verification>
.venv/bin/python -m pytest tests/harness/em/ -x -q && .venv/bin/python -c "from voss.harness.em import EMBoardHandle, BoardSnapshot, BoardProtocol; pub = {m for m in dir(EMBoardHandle) if not m.startswith('_')}; assert {'snapshot','create_ticket','dispatch_card','kill_card','rescope_card','tick','finalize_run'} <= pub; assert pub.isdisjoint({'set_ceiling','set_p','set_budget','extend_budget','register_role','register_agent'})" && echo EM_HANDLE_OK
</verification>

<success_criteria>
- voss/harness/em/handle.py + protocols.py ship.
- EMBoardHandle exposes the legal verb set and no others (introspection test enforces).
- Cage invariants 1–4 + scope-containment refusal covered by 6+ negative tests.
- Dispatch path proven to call gate_for_role + filter_toolset_for_role; never constructs SubagentSpec.
- Kill/rescope emit bidirectional records; the predecessor session-tree-node JSON remains readable after the op.
- All tests green; W1 tests still green.
- Closes with the unique tag EM_HANDLE_OK.
</success_criteria>

<output>
Create `.planning/phases/O5-engineering-manager-loop/O5-02-SUMMARY.md` when done.
Include a §Audit-On-Side-Table Decision section explaining the deviation from
RESEARCH Q3 (audit attrs on node) — preserves O1 SPEC-5 strict-additive.
</output>
