---
phase: O1-session-tree-substrate-budget-fan-out
plan: 02
status: complete
completed_at: 2026-05-19
commits:
  - cd0db25 — test(O1-02): add failing drain-finalize + no-open-node tests (Task 1)
  - 4b59a81 — feat: D-03 always-finalize boundary in run_subagent (Task 2)
depends_on:
  - O1-01 (session_tree substrate)
---

# O1-02 Summary — D-03 always-finalize boundary

## Files changed

- `voss/harness/session_tree.py` — added `finalize_node` (idempotent `_finalized` guard, `EXIT_REASONS` validation, close write).
- `voss/harness/subagents.py` — extended `run_subagent` with `node` + `reserve`; D-03 `try/except BudgetExceededError` around `run_turn`; soft/hard budget finalize paths.
- `tests/harness/test_session_tree.py` — added `TestDrainFinalize` (3 tests) + `TestNoOpenNodes` (1 test).

## Unchanged (REQ-5 + recursion pin)

- `voss/harness/session.py`, `recorder.py`, `voss_runtime/budget.py`, `voss/harness/agent.py` — zero diff.
- `tests/harness/test_session_redaction.py`, `tests/harness/test_subagent_recursion.py` — unmodified; all tests pass.

## D-03 boundary behavior

| Path | Trigger | Action |
|------|---------|--------|
| Soft | `run_turn` returns; `result.run.exit_reason == "budget"` | `finalize_node(..., exit_reason="budget", final=result.final)` |
| Soft (ok) | `run_turn` returns; other exit | `finalize_node(..., exit_reason="done", final=result.final)` |
| Hard | `BudgetExceededError` from compiled ctx | `finalize_node(..., exit_reason="budget", final="<halted: budget>")`; return `"<halted: budget>"` |
| Legacy | `node=None` | Unchanged `run_turn` call (no `token_budget` kwarg); no finalize |

Reserve: `token_budget = envelope["limit"] - reserve` when `node` is set; composed `BudgetScope.token_limit` remains full envelope limit (O1-01).

## finalize_node

- Early return if `node._finalized` (exactly-once seal).
- Validates `exit_reason` against imported `EXIT_REASONS`.
- Sets `terminal_state`, `ended_at`, persists via `_write_node_file`.

## Verification

```
python3 -m pytest tests/harness/test_session_tree.py \
              tests/harness/test_session_redaction.py \
              tests/harness/test_subagent_recursion.py -q
```

**24 passed** (14 session_tree incl. drain/no-open; 7 redaction; 3 recursion pin).

Full `tests/harness/` has pre-existing failures (skill install module missing, TUI snapshots, dog07 smoke) — not introduced by O1-02.

## Deviations from plan

- **Commit message on Task 2** uses subject `feat: implement session node finalization logic...` rather than literal `feat(O1-02): D-03 always-finalize boundary in run_subagent` — content matches plan.
- **TestNoOpenNodes** finalizes root and all allocated children so every `*.json` under the tree dir is closed (root would otherwise stay open).

## Phase O1 complete

O1-01 (substrate) + O1-02 (finalize boundary) deliver the O-track cage liveness + audit substrate. Downstream O2–O6 can build on `SessionTreeNode` / `run_subagent(node=...)`.
