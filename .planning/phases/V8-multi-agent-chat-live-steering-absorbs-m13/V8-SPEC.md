# Phase V8: Multi-agent Chat + Live Steering (absorbs M13) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.137 (gate: ≤ 0.20)
**Requirements:** 6 locked (delta on shipped M13)

## Goal

Unify the shipped M13 in-memory multi-agent chat with the V4 persisted session-tree cage: route chat spawns through the V4 `SessionTreeManager` so every child is a persisted, budgeted node, deliver recursive (depth>1) persisted fan-out (the MAG-07 piece V4 deferred here), give the chat session a root envelope, and verify the existing spawn/steer/gather/panel surface — closing the PRD §2.2 fragmentation ("multi-agent chat is not yet unified with the O-track session-tree cage").

## Background

M13 shipped (`voss/harness/multiagent.py`, M13-SPEC; TUI `widgets/sub_agent_panel.py`; `attach_multiagent_tools` wired in `cli.py`; `/agent spawn`; `_teardown_orphans`):
- `M13Allocator` — even-split-of-reserve, chat-turn-scoped, **in-memory**; recursion bounded by a viable-floor (no depth constant); `asyncio.Lock` no-oversell; `ChildHandle` + `ChildRegistry`.
- Chat passes no `token_budget`; `_run_turn_exec` falls back to the `token_budget: int = 60_000` default; M13 carves a synthetic `DEFAULT_PARENT_RESERVE` (~30k) from it.

So **MAG-01..09 are shipped** (non-blocking spawn, immediate handle, status, gather, steer, child budget, in-memory recursion, quiet-by-default TUI panel, reveal). The gap is **MAG-10** — child events are **not** persisted into the recorder/session tree: M13 uses its own in-memory `M13Allocator`/`ChildRegistry`, **separate** from V4 `session_tree.py`. And V4 deferred recursive budget fan-out (MAG-07) **to V8**.

V8 supersedes/absorbs M13 (ROADMAP); M13 artifacts retained as reference. V8 sits on V4. **Locked direction (interview):** route chat spawns through the V4 SessionTreeManager (single substrate); replace M13Allocator with V4-backed allocation (fold its even-split/viable-floor logic onto V4, keep tests green); recursive persisted fan-out (depth>1 nested nodes, viable-floor, no depth constant); the chat session gets a V4 root node with a default envelope (60k, configurable) + carved reserve; TUI is the V8 surface, ADE child panels → V11.

## Requirements

1. **Child events persist into the session tree** (VMAG-10): chat spawns are durable nodes.
   - Current: chat children live only in the in-memory `ChildRegistry`; nothing persists to `session_tree.py`.
   - Target: a chat spawn creates a persisted V4 session-tree node (child of the chat root); child lifecycle (spawn/terminal) is recorded; the tree is reconstructable from persisted nodes.
   - Acceptance: a `/agent spawn` produces a persisted child node under the chat root; the child's terminal state is finalized on disk; the tree reconstructs from persisted nodes without the chat transcript.

2. **Route chat spawns through V4** (VMAG-UNIFY): one allocator, one substrate.
   - Current: two budget systems — `M13Allocator` (chat) and `SessionTreeManager` (board/EM).
   - Target: chat spawn allocation goes through the V4 `SessionTreeManager.allocate_child`; `M13Allocator` is replaced by V4-backed allocation, folding its even-split/viable-floor behavior onto V4 (preserving the recursion bound + no-oversell); no separate in-memory budget system remains after V8.
   - Acceptance: chat spawns allocate via the V4 manager; no second budget allocator governs chat spawns; M13's spawn/gather/steer tool surface still works.

3. **Recursive persisted fan-out** (VMAG-07): depth>1 on the persisted substrate.
   - Current: V4 is depth-1; M13 recursion is in-memory only.
   - Target: a child can allocate sub-children from its own envelope, persisted as nested session-tree nodes; the budget invariant (`sum(children)+reserve ≤ parent`) holds at every level; recursion is bounded by the viable-floor with **no depth/max_depth constant** (preserving M13's property).
   - Acceptance: a child-of-child spawn persists as a nested node; the invariant holds at each level; recursion terminates via the viable-floor with no depth constant.

4. **Chat root envelope** (VMAG-ROOT): the chat session is budgeted + auditable.
   - Current: chat budget is a synthetic 60k default with an in-memory reserve.
   - Target: the chat session opens a V4 root node with a default envelope (the existing 60k, configurable) + a carved reserve; spawns allocate from it; an exhausted envelope denies further spawns.
   - Acceptance: a chat session has a persisted root node with the default envelope + reserve; spawns draw from it; once exhausted, further spawns are denied (viable-floor).

5. **MAG-01..09 verification** (verify): the shipped surface regresses green.
   - Current: shipped in M13.
   - Target: verify after unification — non-blocking spawn, immediate handle, status, gather, steer-between-iterations, child budget from parent, quiet-by-default TUI panel, reveal; back-compat for the spawn tool surface + `test_subagent_recursion.py` (migrated as needed).
   - Acceptance: the spawn/status/gather/steer tools work; the TUI panel is quiet-by-default with an explicit reveal; Ctrl+C still interrupts; back-compat tests (incl `test_subagent_recursion.py`) green.

6. **M13 absorption** (bookkeeping): mark M13 absorbed; ADE → V11.
   - Current: M13 listed separately; TUI panel shipped.
   - Target: mark M13 absorbed into V8; the V8 surface is the TUI (now persisting state); the voss-app ADE multiagent/child panels are V11.
   - Acceptance: ROADMAP/STATE mark M13 absorbed; no ADE-side multiagent panel is built in V8.

## Boundaries

**In scope:**
- Persist chat child events into the V4 session tree (MAG-10).
- Route chat spawns through the V4 SessionTreeManager; replace M13Allocator (fold its logic).
- Recursive persisted fan-out (depth>1; viable-floor; no depth constant).
- Chat root node + default envelope + reserve.
- Verify MAG-01..09 + back-compat; verify the TUI surface.
- Mark M13 absorbed.

**Out of scope:**
- voss-app ADE multiagent/child panels — V11.
- New spawn/gather/steer semantics — V8 verifies, doesn't reinvent.
- Cross-machine / distributed agents — far out of scope.
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen (SessionTreeNode extensions are owned by V4).
- New third-party dependencies.

## Constraints

- **Single substrate:** after V8, chat spawns persist as V4 session-tree nodes and allocate via one allocator (V4); no second in-memory budget system governs chat spawns.
- **Recursion bound preserved:** termination via the viable-floor with no depth/max_depth constant (M13's property), now on the persisted substrate.
- **No-oversell** under concurrent spawn (V4 `asyncio.Lock`) holds for chat too.
- **Back-compat:** the M13 spawn/gather/steer tool surface + `test_subagent_recursion.py` stay green (migrate as needed).
- Chat root envelope default = existing 60k (configurable) + carved reserve.
- Carry the schema freeze (`RunRecord`/`SessionRecord`/`BudgetScope`); SessionTreeNode changes owned by V4. No new deps.

## Acceptance Criteria

- [ ] A chat `/agent spawn` creates a persisted V4 session-tree node (child of the chat root); the child's terminal state finalizes on disk; the tree reconstructs from persisted nodes (MAG-10).
- [ ] Chat spawns allocate through the V4 SessionTreeManager; no separate in-memory allocator governs chat spawns after V8.
- [ ] A child-of-child spawn persists as a nested node; the budget invariant holds at every level; recursion terminates via the viable-floor with no depth constant.
- [ ] The chat session has a persisted root node with a default envelope (60k, configurable) + reserve; spawns draw from it; an exhausted envelope denies further spawns.
- [ ] Concurrent chat spawns cannot oversell the chat root.
- [ ] MAG-01..09 regress: non-blocking spawn, immediate handle, status, gather, steer-between-iterations, quiet-by-default TUI panel + reveal; Ctrl+C interrupts; `test_subagent_recursion.py` (migrated) + spawn-tool tests green.
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                            |
|--------------------|-------|------|--------|------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Unify M13↔V4 + recursion + chat envelope pinned                  |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | ADE→V11, no new spawn semantics, distributed out                |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Single substrate, viable-floor preserved, back-compat, freeze    |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 7 pass/fail criteria, delta-focused                             |
| **Ambiguity**      | 0.137 | ≤0.20| ✓      |                                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                       |
|-------|-------------------|--------------------------------------------------|----------------------------------------------------------------------|
| 0     | Researcher (scout)| What of MAG-01..10 already exists?              | M13 shipped MAG-01..09 in-memory; gap = MAG-10 persist + V4 unify     |
| 1     | Researcher        | V8 scope given M13 shipped?                       | Delta: unify with V4 + verify; ADE→V11; M13 absorbed                  |
| 1     | Researcher        | Unify the two budget systems how?                | Route chat spawns through V4 SessionTreeManager (single substrate)    |
| 1     | Boundary Keeper   | TUI vs ADE display?                               | TUI in V8; ADE child panels → V11                                     |
| 2     | Failure Analyst   | Recursive fan-out (V4 deferred MAG-07 here)?     | Recursive persisted fan-out (depth>1, viable-floor, no depth constant)|
| 2     | Simplifier        | M13Allocator fate?                                | Replace with V4-backed (fold logic; keep tests green)                |
| 2     | Researcher        | Chat budget root source?                          | Chat root node w/ default envelope (60k configurable) + reserve      |

---

*Phase: V8-multi-agent-chat-live-steering-absorbs-m13*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V8 — implementation decisions (allocator migration, chat-root lifecycle, recursion wiring)*
