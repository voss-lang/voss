# Phase O2: `.voss team{}` Spec + Specialist Roster - Context

**Gathered:** 2026-05-17
**Status:** Seeded from `.planning/ORCHESTRATION-PLAN.md` — needs `/gsd-spec-phase` then `/gsd-plan-phase`
**Source of truth:** `.planning/ORCHESTRATION-PLAN.md` (§2 roles, §5 strawman, §8 decisions)

<domain>
## Phase Boundary

O2 makes "harness owns execution, `.voss` expresses the team" concrete: a `team{}` block compiles to an enriched agent registry + specialist roster, with the cage declared in syntax above the EM.

**In scope:**
- `.voss team{}` block parser (`agent`, `roster`, `ceiling`, `p`, `board`, `ritual` blocks — strawman in ORCHESTRATION-PLAN.md §5).
- `SubagentSpec` extended: `model`, `mode`, `scope`, `budget`, `tools` per role (today it is only `id`/`description`/`role_prompt`).
- Specialist **roster**: backend / frontend / ui / ai, each with per-role scope + tool/permission profile (AI role gets `net`).
- `ceiling` (budget/scope/latency) and `p` (risk-tiered threshold policy) declared **above** the EM and **immutable** to it.
- Compile target: enriched `SubagentRegistry` consumed by the harness.

**Out of scope:** Board state machine execution (O3). Reviewer wiring (O4). EM dispatch logic (O5). The parser produces the registry + declared board/ritual config as data; O3+ execute it.
</domain>

<decisions>
## Locked Decisions (from ORCHESTRATION-PLAN.md §8)

- **Orchestrator lives in the harness, leverages `.voss`** (decision #1). `.voss` declares the team; harness executes.
- **EM selects from a declared roster; cannot invent agents** (decision #3 constraint). Arbitrary agent creation = unbounded, breaks the pre-declared scope/budget cage.
- **`ceiling`/`p` are EM-immutable** (invariant #3, decision #11). The cage is syntax — the EM can read but never rewrite them.
- **Specialization tightens scope for free**: per-role scope shrinks the global-union ceiling (decision #19).

### Claude's discretion (resolve at SPEC/plan)
- `team{}` grammar integration point in the existing `.voss` parser/grammar.
- Roster extensibility mechanism (fixed set vs. user-declared roles).
- How per-role `tools` maps onto existing permission/tool profiles.
</decisions>

## Dependencies
- Depends on: O1 (specs carry budget/scope that need the session tree).
- Blocks: O3, O4, O5, O6.
