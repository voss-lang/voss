# Phase O3: Board State Machine + Gated Transitions - Context

**Gathered:** 2026-05-17
**Status:** Seeded from `.planning/ORCHESTRATION-PLAN.md` — needs `/gsd-spec-phase` then `/gsd-plan-phase`
**Source of truth:** `.planning/ORCHESTRATION-PLAN.md` (§3 board, §4 invariants, §8 decisions)

<domain>
## Phase Boundary

O3 builds the Kanban board **as the orchestrator state machine** — not a UI metaphor. Columns + per-column WIP + gated transitions.

**In scope:**
- Columns: `Backlog → Planned → InProgress → InReview → Blocked → Done`.
- **Per-column WIP** (e.g. `InProgress:3`, `InReview:2`) — surfaces bottlenecks, backpressures reviewer cost for free.
- Gate predicates (consume O1 budget + O4 reviewer verdict):
  - `InProgress→InReview`: `conf(B.fast) ≥ p ∧ scope.ok ∧ budget.ok`
  - `InReview→Done (code)`: `conf(B.strong) ≥ p ∧ tests.pass ∧ scope.clean`
  - `InReview→Done (ai)`: `conf(B.strong) ≥ p ∧ eval.score ≥ t ∧ scope.clean`
  - `any→Blocked`: budget ∨ confidence floor ∨ scope ∨ retry-ceiling ∨ timeout
- **Confidence gate fires only on artifact transitions** (decision #4 refinement) — no-artifact transitions gate on budget+scope only.
- Critic loop: reject → InProgress, reviewer notes to card episodic; bound = retry ceiling (≈3) **AND** budget, first hit → Blocked.
- Column/card timeout → Blocked (liveness, breaks WIP deadlock).

**Out of scope:** Reviewer A/B internals (O4 — O3 consumes the verdict interface). EM board mutation (O5). Audit surfacing (O6). The `→Done` deterministic source (tests vs. eval) is *invoked* here but *authored* by Reviewer-A in O4.
</domain>

<decisions>
## Locked Decisions (from ORCHESTRATION-PLAN.md §8)

- **→Done is double-gated, two independent sources** (decisions #8, #21). Reviewer-B cannot ship work failing A-authored objective checks. AI cards swap deterministic tests for an eval harness so the second source survives where slop is hardest to see.
- **Per-column WIP, not single concurrency cap** (decision #12). The complexity is the product.
- **Critic loop = ceiling AND budget** (decision #10), notes accumulate so retries don't repeat.
- **Tiered reviewer** (decision #9) is safe *because* →Done is double-gated with the strong model — the cost-saving and safety choices interlock.

### Claude's discretion (resolve at SPEC/plan)
- Board persistence model (where card state lives relative to the O1 session tree).
- Risk formula for `p` evaluation inputs (scope × budget × core-file-touch).
- Timeout values / whether timeout is wall-clock, budget, or both.
</decisions>

## Dependencies
- Depends on: O1 (budget/session tree), O2 (board config + roster).
- Blocks: O4, O5, O6.
