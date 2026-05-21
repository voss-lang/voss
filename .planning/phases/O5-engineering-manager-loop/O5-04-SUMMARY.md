---
phase: O5-engineering-manager-loop
plan: 04
status: complete
completed_at: 2026-05-20
commits: []
depends_on: [O5-02, O5-03]
requirements: [OEM-05, OEM-06]
---

# O5-04 Summary — EM Loop (Wave 4)

## Objective

Land `em_loop(...)` -- the autonomous lead-engineer coroutine that ties the EM data model (W1), board facade (W2), and LLM schema (W3) into a closed loop from idea to all-cards-terminal.

## Files changed

- `voss/harness/em/loop.py` -- **new** (136 lines): `_execute_plan(em_handle, plan) -> list[tuple[op, Exception]]` dispatcher routing each Op to its EMBoardHandle verb via isinstance chain; `async def em_loop(*, idea, em_handle, em_agent, roster_descriptions, max_iterations=50) -> RunFinal` plan-and-tick coroutine.
- `voss/harness/em/__init__.py` -- extended: re-exports `em_loop`.
- `tests/harness/em/test_em_loop.py` -- **new** (2 tests): happy-path idea-to-Done with DeterministicEMStub + fake subagent_runner, RunFinal count assertions.
- `tests/harness/em/test_em_loop_termination.py` -- **new** (3 tests): max_iterations ceiling with force_block_all, BudgetExceededError force-finalize, cage-violation-continue (audit-not-abort).
- `tests/harness/em/test_em_loop_dispatch_path.py` -- **new** (2 tests): dispatch reaches run_subagent with per-role gate, SubagentSpec never constructed.

## Test counts

| File | Tests |
|------|-------|
| `test_em_loop.py` | 2 |
| `test_em_loop_termination.py` | 3 |
| `test_em_loop_dispatch_path.py` | 2 |
| **Total (new)** | **7** |

## Key facts

- **Loop shape:** `while not em_handle.all_cards_terminal()` -> check max_iterations -> snapshot -> `await em_agent.plan(...)` -> `_execute_plan(handle, plan)` -> `await em_handle.tick()` -> iteration++.
- **Termination:** Three exit paths: (1) all cards in Done/Blocked, (2) max_iterations exhausted with force_block_all(reason="em_iteration_ceiling"), (3) BudgetExceededError caught with force_block_all(reason="budget").
- **Audit-not-abort:** EMCageViolation from any individual op in `_execute_plan` is caught, logged via `logger.warning`, and collected in a failures list. The loop continues to the next iteration. The EM sees its own rejections on the next snapshot.
- **_execute_plan isinstance dispatch:** Routes CreateTicketOp, SetACOp, SetDoDOp, DispatchCardOp, KillCardOp, RescopeCardOp to their handle verbs; NoopOp is a pass. List fields (acceptance_criteria, dod, candidates_considered) are joined/converted at the boundary.
- **em_iterations patching:** `em_loop` rebuilds the RunFinal via `dataclasses.replace(rf, em_iterations=iteration)` since `finalize_run()` returns em_iterations=0 by default. The frozen dataclass requires a replace, not mutation.
- **No SubagentSpec construction:** Loop and handle never construct SubagentSpec -- only call `registry.get(role_id)` (L-05 honored).

## Deviations from plan

- **No asyncio.Lock:** Plan called for an asyncio.Lock guarding state-machine transitions. The implementation omits it -- the loop is single-threaded (one em_loop coroutine per board) and the Lock would add complexity without benefit in the current architecture. If concurrent ticks are introduced later, the Lock can be added.
- **No EMLoop class:** Plan suggested an optional `class EMLoop` wrapper. Execution shipped only the procedural `em_loop` function -- simpler and sufficient for the test contract.
- **BudgetExceededError catch scope:** The catch wraps the entire plan+execute block, not just the dispatch path. This is broader than plan specified but ensures any budget exhaustion during ticket creation or rescope is also caught.

## Unchanged

- W1, W2, W3 source files -- no modifications.
- W1, W2, W3 tests -- all still green.

## Next

W5 lands integration tests + cross-phase coordination artifacts.
