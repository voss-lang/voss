---
phase: O5-engineering-manager-loop
plan: 04
type: tdd
wave: 4
depends_on:
  - O5-02
  - O5-03
files_modified:
  - voss/harness/em/loop.py
  - voss/harness/em/__init__.py
  - tests/harness/em/test_em_loop.py
  - tests/harness/em/test_em_loop_termination.py
  - tests/harness/em/test_em_loop_dispatch_path.py
autonomous: true
requirements:
  - OEM-05
  - OEM-06
must_haves:
  truths:
    - "em_loop is a single async coroutine — read snapshot, call em_agent.plan(), execute_plan via handle, await tick — bounded by max_iterations"
    - "Loop terminates iff every card column ∈ {Done, Blocked} OR max_iterations exhausted"
    - "On max_iterations exhaustion, force_block_all(reason='em_iteration_ceiling') is called"
    - "EM-LLM responses go through DeterministicEMStub in every test — zero live LLM calls"
    - "Loop dispatches via handle.dispatch_card → ultimately calls run_subagent(node=child, reserve=…) with the per-role gate (cage invariant 3)"
    - "EMCageViolation raised by the handle is logged and the loop continues (audit-not-abort principle, PATTERNS analog 'single-boundary always-finalize')"
    - "BudgetExceededError from any child finalizes the loop with force_block_all(reason='budget')"
    - "RunFinal emitted on termination — counts done / blocked / killed / rescope / em_iterations"
    - "asyncio.Lock guards state-machine transitions; released before any LLM/run_subagent await (PATTERNS shared-pattern)"
  artifacts:
    - path: "voss/harness/em/loop.py"
      provides: "em_loop coroutine + EMRunResult + EMLoop driver class"
      contains: "async def em_loop"
    - path: "tests/harness/em/test_em_loop.py"
      provides: "happy-path: scripted-stub idea → ticket → dispatch → tick → Done"
    - path: "tests/harness/em/test_em_loop_termination.py"
      provides: "max_iterations ceiling + force_block_all + cage-violation continue + BudgetExceededError force-finalize"
    - path: "tests/harness/em/test_em_loop_dispatch_path.py"
      provides: "dispatch reaches run_subagent with per-role gate; no SubagentSpec construction in loop"
  key_links:
    - from: "voss/harness/em/loop.py"
      to: "voss/harness/em/handle.py"
      via: "EMBoardHandle facade is the loop's only board surface"
      pattern: "EMBoardHandle"
    - from: "voss/harness/em/loop.py"
      to: "voss/harness/em/stub.py"
      via: "tests inject DeterministicEMStub as em_agent"
      pattern: "DeterministicEMStub"
    - from: "voss/harness/em/loop.py"
      to: "voss/harness/em/schema.py"
      via: "executes EMPlanResponse.ops via handle verbs"
      pattern: "EMPlanResponse"
---

<objective>
Land `em_loop(...)` — the autonomous lead-engineer coroutine that ties O1
substrate + O2 roster + O3 board (mocked here, real in W5) + O4 reviewers
(mocked here) into a closed loop from idea → all-cards-terminal.

The loop is a plan-and-tick cycle: snapshot the board, call the EM agent
(LLM or stub) for one EMPlanResponse, execute every op via EMBoardHandle,
await one Board.tick(), repeat until terminal. RESEARCH Q1 surveys both
voss_runtime.spawn/gather and the harness-scheduler approach; the locked
decision is the harness scheduler (single chokepoint, no double scheduler,
testable synchronous tick).

Purpose: This wave makes the EM autonomous. Cage invariants are preserved
because every op goes through W2 EMBoardHandle (which itself goes through
W2's facade refusals + W1's frozen records). The loop's own responsibility
is liveness — every card reaches Done or Blocked in finite iterations.

Output: One new module (loop.py), one __init__.py update, 3 test files.
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
@.planning/phases/O5-engineering-manager-loop/O5-02-SUMMARY.md
@.planning/phases/O5-engineering-manager-loop/O5-03-SUMMARY.md
@voss/harness/em/tickets.py
@voss/harness/em/handle.py
@voss/harness/em/schema.py
@voss/harness/em/stub.py
@voss/harness/em/errors.py
@voss/harness/subagents.py
@voss/harness/session_tree.py

<interfaces>
<!-- W1/W2/W3 in-tree -->

From voss/harness/em/handle.py (W2 GREEN):
  EMBoardHandle.snapshot() -> BoardSnapshot
  EMBoardHandle.all_cards_terminal() -> bool
  EMBoardHandle.create_ticket / set_ac / set_dod / dispatch_card / kill_card /
    rescope_card / tick (async) / force_block_all / finalize_run

From voss/harness/em/schema.py (W3 GREEN):
  EMPlanResponse, EMOp union (CreateTicketOp | DispatchCardOp | KillCardOp |
    RescopeCardOp | SetACOp | SetDoDOp | NoopOp)

From voss/harness/em/stub.py (W3 GREEN):
  DeterministicEMStub.plan(*, idea, snapshot, ...) -> EMPlanResponse

<!-- Live substrate -->

From voss_runtime.exceptions:
  BudgetExceededError (raised by O1 substrate when an envelope drains)
</interfaces>

<loop_shape>
Per RESEARCH Q1:

```python
async def em_loop(
    *,
    idea: str,
    em_handle: EMBoardHandle,
    em_agent,                                  # has async plan(*, idea, snapshot, ...) -> EMPlanResponse
    roster_descriptions: dict[str, str],       # for snapshot rendering
    max_iterations: int = 50,
) -> RunFinal:
    iteration = 0
    while not em_handle.all_cards_terminal():
        if iteration >= max_iterations:
            em_handle.force_block_all(reason="em_iteration_ceiling")
            break
        snapshot = em_handle.snapshot()
        try:
            plan = await em_agent.plan(
                idea=idea, snapshot=snapshot,
                roster_descriptions=roster_descriptions,
            )
            _execute_plan(em_handle, plan)     # iterate ops; route to handle verbs
        except EMCageViolation:
            # audit-not-abort: log via the snapshot, continue
            pass
        except BudgetExceededError:
            em_handle.force_block_all(reason="budget")
            break
        await em_handle.tick()
        iteration += 1
    return em_handle.finalize_run()
```

_execute_plan(handle, plan) routes each Op kind to its handle verb:
  - CreateTicketOp → handle.create_ticket(...)
  - SetACOp → handle.set_ac(...)
  - SetDoDOp → handle.set_dod(...)
  - DispatchCardOp → handle.dispatch_card(...)
  - KillCardOp → handle.kill_card(...)
  - RescopeCardOp → handle.rescope_card(...)
  - NoopOp → pass

Each op call is wrapped in `try/except EMCageViolation: log+continue` so a
single rejected op does not abort the iteration. The EM sees its own
rejections on the next snapshot via the in-handle audit side-table (W2).
</loop_shape>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: RED — em_loop happy-path + termination + dispatch test scaffolds</name>
  <files>tests/harness/em/test_em_loop.py, tests/harness/em/test_em_loop_termination.py, tests/harness/em/test_em_loop_dispatch_path.py</files>
  <read_first>
    - voss/harness/em/handle.py (W2 facade surface)
    - voss/harness/em/schema.py (W3 op shapes)
    - voss/harness/em/stub.py (W3 DeterministicEMStub)
    - tests/harness/em/conftest.py (W2 fixtures — stub_board, stub_recorder, tiny_team_config, base_gate, make_handle)
    - .planning/phases/O5-engineering-manager-loop/O5-RESEARCH.md §Q1
    - .planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md §"voss/harness/em/loop.py"
  </read_first>
  <behavior>
    test_em_loop.py — happy path:
      - Build a DeterministicEMStub with a 2-iteration script:
        iter 1 → CreateTicketOp(worker_role="backend") + DispatchCardOp
        iter 2 → NoopOp
      - Inject a fake subagent_runner that, when called, immediately
        finalizes the child node and marks the StubBoard's card column
        as "Done".
      - Run `await em_loop(idea="x", em_handle=handle, em_agent=stub,
        roster_descriptions={"backend":"…"}, max_iterations=10)`.
      - Assert: returned RunFinal has total_cards=1, done_count=1,
        blocked_count=0, killed_count=0, em_iterations<=10.
      - Assert: stub.calls has 2 entries (loop made 2 plan calls before
        termination).
      - Assert: handle.snapshot().cards now contains exactly one card
        with column="Done".

    test_em_loop_termination.py — termination invariants:
      - max_iterations=3 with a stub that emits NoopOp forever and a board
        with one Planned card: loop exits after iteration 3 via
        force_block_all(reason="em_iteration_ceiling"). RunFinal shows
        blocked_count=1, em_iterations=3.
      - Stub raises BudgetExceededError on iteration 2: loop catches and
        force_block_alls with reason="budget"; RunFinal blocked_count==
        total_cards.
      - When handle.dispatch_card raises EMCageViolation (because the
        stub emits a DispatchCardOp with role_id="phantom"), the loop
        does NOT abort — it continues to the next iteration. Assert the
        stub.calls count proves iteration progression.
      - The audit side-table on the handle still records the cage violation
        for downstream surfacing (test reads handle._node_audit or the
        equivalent W2-shipped surface).

    test_em_loop_dispatch_path.py — dispatch reaches run_subagent:
      - Monkeypatch voss.harness.subagents.run_subagent to a sentinel that
        records every kwarg.
      - Stub emits CreateTicketOp + DispatchCardOp(role_id="backend",
        task="t", rationale_text="r", candidates_considered=["backend",
        "frontend"], confidence_hint=0.8).
      - After one loop iteration, the sentinel has been called exactly
        once with kwargs containing: agent_id="backend", task="t",
        registry=<the registry>, node=<a SessionTreeNode>, reserve=<int>,
        gate=<a PermissionGate from gate_for_role>.
      - The PermissionGate passed in is NOT the raw base_gate — it's the
        capped role-specific one (assert via a sentinel wrap on
        team.gate_for_role).
      - Loop NEVER constructs SubagentSpec (monkeypatch on
        SubagentSpec.__init__ records zero calls).

    All RED today (loop.py doesn't exist).
  </behavior>
  <action>
    Write three new test files leveraging the W2 conftest.py fixtures. For
    the fake subagent_runner injection, use the make_handle factory's
    subagent_runner kwarg (W2 added this for tests). For the monkeypatch
    of run_subagent in test_em_loop_dispatch_path.py, use
    `monkeypatch.setattr(voss.harness.subagents, "run_subagent",
    sentinel)`.

    Run pytest; expect ImportError on voss.harness.em.loop.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/test_em_loop.py tests/harness/em/test_em_loop_termination.py tests/harness/em/test_em_loop_dispatch_path.py -x -q --tb=short 2>&amp;1 | tee /tmp/o5-04-red.log; grep -qE "(ModuleNotFoundError|ImportError)" /tmp/o5-04-red.log &amp;&amp; echo EM_LOOP_RED_OK</automated>
  </verify>
  <acceptance_criteria>
    - 3 new test files collect.
    - Tests fail on ImportError of voss.harness.em.loop.
    - W1, W2, W3 tests still green.
  </acceptance_criteria>
  <done>RED tests committed.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: GREEN — implement em_loop + _execute_plan dispatcher</name>
  <files>voss/harness/em/loop.py, voss/harness/em/__init__.py</files>
  <read_first>
    - voss/harness/em/handle.py (W2 — every public verb signature)
    - voss/harness/em/schema.py (W3 — EMOp union members)
    - voss/harness/em/stub.py (W3 — stub interface contract)
    - voss/harness/em/errors.py (W1 — EMCageViolation)
    - voss/harness/em/tickets.py (W1 — RunFinal shape)
    - voss/harness/subagents.py (run_subagent — dispatch terminus)
    - voss/harness/session_tree.py (BudgetAllocationError / BudgetCapRaiseError)
    - voss_runtime/exceptions.py (BudgetExceededError)
    - tests/harness/em/test_em_loop*.py (Task 1 contracts)
  </read_first>
  <behavior>
    Implementation constraints:

    - `voss/harness/em/loop.py` exports:
      - `async def em_loop(*, idea, em_handle, em_agent, roster_descriptions,
        max_iterations=50) -> RunFinal` — the public coroutine.
      - `def _execute_plan(em_handle, plan: EMPlanResponse) -> None` —
        private dispatcher iterating plan.ops and routing each to its
        handle verb. EMCageViolations from any single op are caught and
        logged via a return-list of (op, exception) pairs (the caller
        loop ignores them but the W5 integration test can read them).
      - Optionally a thin `class EMLoop` wrapper (constructor takes the
        same args; `async def run()` calls `em_loop(...)`). PATTERNS §
        "voss/harness/em/loop.py" recommends a class for state ownership
        even though the procedural function is enough for testing.

    - Op dispatch table (match-style):
      - CreateTicketOp → em_handle.create_ticket(
          original_idea=op.original_idea, acceptance_criteria=op.acceptance_criteria,
          dod=op.dod, worker_role=op.worker_role, domain=op.domain,
          risk_tier=op.risk_tier)
      - SetACOp → em_handle.set_ac(op.card_id, op.acceptance_criteria)
      - SetDoDOp → em_handle.set_dod(op.card_id, op.dod)
      - DispatchCardOp → em_handle.dispatch_card(
          card_id=op.card_id, role_id=op.role_id, task=op.task,
          rationale_text=op.rationale_text,
          candidates_considered=op.candidates_considered,
          confidence_hint=op.confidence_hint)
      - KillCardOp → em_handle.kill_card(op.card_id, op.rationale_text)
      - RescopeCardOp → em_handle.rescope_card(
          card_id=op.card_id, new_worker_role=op.new_worker_role,
          new_scope=op.new_scope, new_acceptance=op.new_acceptance,
          rationale_text=op.rationale_text)
      - NoopOp → pass

    - Loop guard:
      - asyncio.Lock guarding state-machine transitions (snapshot →
        execute → tick is atomic w.r.t. concurrent callers; the lock is
        RELEASED before the `await em_agent.plan(...)` LLM call to avoid
        holding the lock during model latency — PATTERNS shared pattern).
      - Iteration counter increments AFTER tick (so max_iterations=N
        executes N plan-and-tick cycles).
      - BudgetExceededError handler: force_block_all(reason="budget")
        + break. The exception is captured but not re-raised.
      - Generic Exception is NOT caught — surfaces to the caller (a true
        bug, not a cage violation). Per PATTERNS shared-pattern:
        typed-ParseError catch for normal paths, bare-except only for the
        terminate finalize path; the loop's exit-from-budget IS the
        finalize boundary so the bare-except is appropriate THERE only.

    - voss/harness/em/__init__.py: extend __all__ with `em_loop`,
      `_execute_plan` (underscore prefix excluded), and `EMLoop`.

    - Audit copy in any log messages must not contain L2 vocab.

    Iterate to GREEN. Run the full em/ suite to verify no regression.
  </behavior>
  <action>
    Implement loop.py per the behavior contract. Use a structural-match
    (`match op:` or `isinstance` chain) for op dispatch — pydantic v2's
    discriminated union returns the concrete subclass, so isinstance is
    safe.

    Confirm via the dispatch_path test that the loop never constructs
    SubagentSpec and the gate passed to run_subagent comes from
    gate_for_role.

    Run the full em/ test suite to verify all RED scaffolds turn GREEN.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; .venv/bin/python -m pytest tests/harness/em/ -x -q --tb=short &amp;&amp; .venv/bin/python -c "from voss.harness.em import em_loop, EMBoardHandle, DeterministicEMStub, EMPlanResponse, NoopOp; import inspect; assert inspect.iscoroutinefunction(em_loop); print('loop ok')" &amp;&amp; echo EM_LOOP_OK</automated>
  </verify>
  <acceptance_criteria>
    - All Task 1 RED tests GREEN; W1/W2/W3 still GREEN.
    - em_loop is a coroutine function; signature matches the loop_shape contract.
    - Termination invariants hold: terminal-cards exit, max_iterations exit, BudgetExceededError exit.
    - EMCageViolation does NOT abort the loop (audit-not-abort).
    - Dispatch path proven to call run_subagent with the role-capped gate.
    - SubagentSpec.__init__ is never called from loop or handle code paths.
    - asyncio.Lock is acquired around state-machine transitions but released before LLM await.
  </acceptance_criteria>
  <done>All tests GREEN; commit references OEM-05, OEM-06.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| EM plan ops ↔ EMBoardHandle verbs | The loop is the executor of LLM-emitted ops; every op crosses this boundary one at a time. |
| EMCageViolation ↔ loop continuation | A rejected op must not abort the loop; the audit must record the rejection for O6. |
| BudgetExceededError ↔ force_block_all | Liveness invariant — every spawned card reaches a terminal state. |
| LLM latency ↔ asyncio.Lock | Holding the lock during model calls would deadlock concurrent ticks. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O5-03 | Elevation | Loop bypasses gate_for_role / passes raw base_gate to run_subagent | mitigate | Loop never touches run_subagent directly; goes through handle.dispatch_card. Test asserts the gate passed is NOT base_gate. |
| T-O5-Loop-01 | Denial of service | Stub returns infinite NoopOps; loop runs forever | mitigate | max_iterations ceiling + force_block_all. Default 50; tunable. |
| T-O5-Loop-02 | Denial of service | Lock held during LLM await; concurrent tick deadlocks | mitigate | Lock released before plan(...) await per PATTERNS shared-pattern. |
| T-O5-Loop-03 | Tampering | Loop catches generic Exception and silently continues, hiding bugs | mitigate | Only ParseError (in em_plan) and BudgetExceededError (in loop) are sentinel-caught; everything else surfaces. |
| T-O5-Loop-04 | Repudiation | Cage violation is silently swallowed | mitigate | _execute_plan returns the list of (op, exception) failures; W2 audit side-table records the violation for O6. |
| T-O5-Loop-05 | Information disclosure | Iteration ceiling reason exposes L2 vocab | mitigate | reason="em_iteration_ceiling" — no model/cost/token/provider strings. |
</threat_model>

<verification>
.venv/bin/python -m pytest tests/harness/em/ -x -q && .venv/bin/python -c "from voss.harness.em import em_loop, EMBoardHandle, DeterministicEMStub; import inspect; assert inspect.iscoroutinefunction(em_loop); sig = inspect.signature(em_loop); assert {'idea','em_handle','em_agent','roster_descriptions','max_iterations'} <= set(sig.parameters)" && echo EM_LOOP_OK
</verification>

<success_criteria>
- voss/harness/em/loop.py ships with em_loop coroutine + _execute_plan dispatcher.
- Loop tests cover happy path, max_iterations, BudgetExceededError, cage-violation-continue, dispatch-reaches-run_subagent.
- Loop never constructs SubagentSpec; never bypasses gate_for_role.
- All em/ tests green.
- Closes with the unique tag EM_LOOP_OK.
</success_criteria>

<output>
Create `.planning/phases/O5-engineering-manager-loop/O5-04-SUMMARY.md` when done.
</output>
