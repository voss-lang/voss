# Phase O5: Engineering Manager Loop - Context

**Gathered:** 2026-05-17
**Status:** Seeded from `.planning/ORCHESTRATION-PLAN.md` — needs `/gsd-spec-phase` then `/gsd-plan-phase`
**Source of truth:** `.planning/ORCHESTRATION-PLAN.md` (§2 roles, §4 invariants, §7 residuals, §8 decisions)

<domain>
## Phase Boundary

O5 is the autonomous lead loop that ties O1–O4 together: an idea goes in, the board runs to Done, the human only signs off.

**In scope:**
- EM full-authority autonomous loop: human idea → tickets / AC / DoD (worker scaffolding, **not** the audit bar).
- Specialist **dispatch** from the O2 roster + a recorded `routing_rationale` per card.
- **Kill / re-scope** with preserved lineage (the data O6 foregrounds — where the bodies are buried).
- Board mutation bounded by the cage: EM cannot rewrite `ceiling`/`p`, cannot invent agents, cannot extend budget.

**Out of scope:** Board mechanics (O3). Reviewer internals (O4). The audit *surface* + calibration + forcing function (O6) — O5 must *emit* routing rationale + kill lineage as first-class records for O6 to surface.
</domain>

<decisions>
## Locked Decisions (from ORCHESTRATION-PLAN.md §8)

- **EM = LLM planner with full lead-engineer authority** (decisions #2, #3): create / kill / re-scope / reassign cards.
- **Human is final sign-off only** (decision #5) — autonomous to Done, no in-flight approvals.
- **Role metaphor** (decision #19): planner = Engineering Manager; workers = specialist Engineer roster.
- **Misroute handling = EM declares routing rationale, audited** (decision #20). Known accepted limitation: misroute is *not* caught in-flight — it surfaces at sign-off (residual #4).
- **AC/DoD are worker scaffolding, audit bar is the original idea** (decision #13) — the EM cannot grade its own homework.

### Claude's discretion (resolve at SPEC/plan)
- EM loop control structure (reuse `voss_runtime` `spawn`/`gather` vs. harness-driven scheduler).
- Card / ticket data model relative to the O1 session tree + O3 board state.
- Routing-rationale schema (free text vs. structured classification record).
</decisions>

## Dependencies
- Depends on: O1, O2, O3, O4.
- Blocks: O6.
- Carries residual risks: #3 (overloaded sign-off — O6 forcing function), #4 (misroute caught late — accepted).
