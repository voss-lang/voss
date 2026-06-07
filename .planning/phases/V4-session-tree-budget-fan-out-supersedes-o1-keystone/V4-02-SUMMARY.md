---
phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone
plan: 02
subsystem: harness
tags: [asyncio, budget, session-tree, subagents, finalize, spend-guard]

# Dependency graph
requires:
  - phase: V4-01
    provides: "SessionTreeNode scope/role nullable fields, allocate_child scope/role kwargs, EXIT_REASONS includes 'error'"
provides:
  - "Pre-emptive spend guard in run_subagent — refuses to begin a call when node.envelope spent >= limit"
  - "mutate_envelope spend wiring after run_turn (makes the guard live, not dead code)"
  - "All-reason finalize boundary: except asyncio.TimeoutError / except Exception / finally net"
  - "TestSpendGuard + TestAllReasonsFinalize coverage in tests/harness/test_session_tree.py"
affects: [V5, V6, V7, board, reviewers, EM-dispatch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-emptive budget guard = pure node-envelope read, no lock, no await between check and return (atomic under asyncio cooperative scheduling)"
    - "try/except(BudgetExceededError, asyncio.TimeoutError, Exception)/finally finalize boundary relying on finalize_node _finalized idempotence"

key-files:
  created: []
  modified:
    - voss/harness/subagents.py
    - tests/harness/test_session_tree.py

key-decisions:
  - "Token source for spend update confirmed: result.run.iteration_total_prompt_tokens + iteration_total_completion_tokens (RunRecord fields, defaults 0)"
  - "Exception path uses exit_reason='error' (added to EXIT_REASONS in V4-01); finally net also uses 'error' with final='<uncaught>'"
  - "asyncio.TimeoutError caught BEFORE Exception (TimeoutError is an Exception subclass in Py3.11+)"
  - "Guard finalizes exit_reason='budget' and returns '<halted: budget — envelope exhausted>'"

patterns-established:
  - "Spend wiring before soft-exit check: mutate_envelope(node, delta=-tokens_used) only when result.run is not None and tokens_used > 0"
  - "finally safety net: if node is not None and not node._finalized → finalize 'error' — guarantees no open node on any path"

requirements-completed: [VTREE-04, VTREE-07, VTREE-02]

# Metrics
duration: 12min
completed: 2026-06-06
---

# Phase V4-02: Budget Spend Guard + Spend Wiring + All-Reason Finalize Summary

**Pre-emptive spend guard in run_subagent backed by mutate_envelope spend wiring (the guard goes live) plus a try/except(Timeout,Exception)/finally finalize boundary so error/timeout/budget each emit exactly one sealed node.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-06-06
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- **Keystone guard (VTREE-04):** `run_subagent` now refuses to begin a call when `node.envelope["spent"] >= node.envelope["limit"]` — finalizes `exit_reason="budget"` and returns `<halted: budget — envelope exhausted>` BEFORE `async with scope:`. Pure node-envelope read, no lock, no await between check and return — atomic under asyncio. `run_turn` is provably never invoked past the envelope (`mock_turn.assert_not_called()`).
- **Spend wiring makes the guard live:** after `run_turn` returns on the normal path, `spent` is incremented by `result.run.iteration_total_prompt_tokens + iteration_total_completion_tokens` via `mutate_envelope(node, delta=-tokens_used)`. Without this the guard would be dead code (`spent` would never move). `result.run is None` → no spend update, no crash.
- **All-reason finalize (VTREE-07):** appended `except asyncio.TimeoutError` (→ timeout, re-raise), `except Exception as exc` (→ error, re-raise), and a `finally` net (→ error `<uncaught>` if still open). Existing `except BudgetExceededError` (→ budget) preserved unchanged. `finalize_node` idempotence (`_finalized`) prevents the `finally` from double-finalizing — the FIRST reason wins.
- **No-oversell regression (VTREE-02):** `TestConcurrency` + `TestBudgetFanOut` regress green unchanged; `allocate_child`'s `asyncio.Lock` untouched by this plan.

## Task Commits

Not committed — working tree left with changes in place per execution instructions.

1. **Task 1: Pre-emptive spend guard + post-run_turn spend wiring** (TDD)
2. **Task 2: All-reason finalize boundary (except TimeoutError / except Exception / finally)** (TDD)
3. **Task 3: No-oversell concurrency regression verification** (existing `TestConcurrency` already asserts `gather`-based no-oversell post-condition — no new test needed)

## Files Created/Modified
- `voss/harness/subagents.py` — added `import asyncio`; extended import to `finalize_node, mutate_envelope`; inserted pre-emptive guard after the `spec is None` early return; added spend update + `except asyncio.TimeoutError` + `except Exception` + `finally` net in `run_subagent`. **`run_subagent` signature unchanged.**
- `tests/harness/test_session_tree.py` — appended `TestSpendGuard` (4 tests: guard-blocks, spent-updated-after-call, no-run-record, soft-exit-budget) and `TestAllReasonsFinalize` (parametrized over all 8 EXIT_REASONS + timeout/error/budget-exception paths + no-double-finalize). Mocks `voss.harness.subagents.run_turn` with `AsyncMock` via `patch.object`. Existing classes untouched.

## Decisions Made
- **Token source confirmed in codebase** — `RunRecord.iteration_total_prompt_tokens` and `iteration_total_completion_tokens` (session.py lines 141–142, both `int = 0`). Spend = sum, guarded by `or 0` and `tokens_used > 0`.
- **Test `run.run` stand-in** — used `types.SimpleNamespace` rather than a full `RunRecord` to keep mocks minimal (only the three fields `run_subagent` reads).
- **BudgetExceededError construction** — its `__init__` requires kwargs `reason`, `limit`, `observed` (no positional message); test adjusted accordingly.

## Deviations from Plan

None of substance — plan executed as written. Two minor test-authoring corrections during Task 2:
- `BudgetExceededError(...)` needs keyword args `reason/limit/observed` (discovered at first test run); fixed in place.
- Used `SimpleNamespace` for the `TurnResult`/`RunRecord` stand-in instead of importing the real dataclasses (within plan's "minimal registry / follow conventions" discretion).

## DOCUMENTED V4 GAP — T-V4-14 (accepted, not fixed)

The `attach_subagent_tool` closure (`subagent_run` and `task` tools in `subagents.py`) calls `run_subagent` **WITHOUT** passing `node=`. Because the guard is `if node is not None and ...`, the tool-dispatched subagent path is **unguarded in V4** (same posture as O1). V4 proves the mechanism on the direct `run_subagent(node=...)` path only. Plumbing a `SessionTreeNode` through the tool closure is **V5/V7 integration work** (EM dispatch / board). This is the accepted disposition for STRIDE threat **T-V4-14** (Elevation of Privilege — tool-dispatched subagent_run bypasses guard).

## Issues Encountered
- `BudgetExceededError` constructor signature mismatch in test — resolved by passing required keyword args.

## Test Results
- `tests/harness/test_session_tree.py` — **34 passed** (TestSpendGuard + TestAllReasonsFinalize coexist green with all V4-01 classes).
- `tests/harness/test_session_redaction.py` — **8 passed, UNMODIFIED** (frozen-schema invariant intact; no SessionRecord/RunRecord/BudgetScope field changes).
- Broader subagent suite (recursion/smol/spec-extensions/multiagent) — green (2 expected xfail).
- `run_subagent` signature unchanged; `allocate_child` lock untouched (`git diff` lock-line check empty).

## Next Phase Readiness
- The budget cage mechanism is proven on the direct-node path. V5/V7 must plumb `node` through `attach_subagent_tool` to close T-V4-14.
- `killed`/`blocked` terminal emitters remain deferred to V5/V7 (mechanism already accepted by `finalize_node`).

---
*Phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone*
*Completed: 2026-06-06*
