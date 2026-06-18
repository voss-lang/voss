# Phase BOS0: Product Thesis, ICP, and Wedge - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS0 produces two docs-first artifacts that anchor the v0.2 Behavioral OS milestone:
1. **Product brief** — boundary, ICP, buyer/user split, wedge, positioning (covers BOS-PROD-01..03).
2. **Design-partner discovery script** — the validation questions for first interviews.

This phase decides WHO the Behavioral OS is for and WHAT the first wedge is. It does **not** design the data schema (BOS3-5), governance (BOS6), web/desktop split detail (BOS7, BOS-PROD-04), or any implementation. No code.
</domain>

<decisions>
## Implementation Decisions

### ICP / First Beachhead
- **D-01:** First customer = **small multi-agent engineering teams (3-15 devs)** already running multiple coding agents (Claude Code / Codex / Voss). They feel real coordination pain and already generate the ADE/swarm events BOS needs to observe. Rejected: solo power-user (weak pull for a team control plane), devex/platform team at scale-up (long cycle, weaker wedge observability).

### Primary Wedge
- **D-02:** First recommendation surface = **delegation: task → agent/human**. Chosen because it is already modeled in the V25 server-native swarm assignment flow, making it the most directly observable decision today and the natural entry point before review-depth and validation-depth wedges. Review-depth = later (needs review-outcome data). Validation-depth = later (depends on CI/validation ingestion, BOS12).

### Buyer / User Split + Adoption Motion
- **D-03:** **EM / engineering lead = economic buyer.** Devs = daily users.
- **D-04:** Adoption motion = **devs already on the Voss ADE; the EM buys the control plane on top.** The brief assumes the team already uses Voss's ADE/swarm for agent work (existing product), so the EM buys BOS as the team-level layer over data devs *already* generate. **No new dev behavior is required for the wedge to work** — this resolves the tension between a top-down buyer and a dev-generated data substrate.

### External Positioning / Category
- **D-05:** External category = **"control plane for AI engineering teams."** Keep **"Behavioral OS"** as the internal / north-star term only.
- **D-06:** Explicit anti-positioning (the brief must state what BOS is NOT): NOT a Jira/Linear/Atlassian PM clone; NOT individual-developer surveillance, ranking, or productivity leaderboards.

### Discovery Script Intent
- **D-07:** Interviews validate **problem existence + current decision behavior FIRST** (Mom-Test style): do delegation/review/validation decisions actually hurt today, and how do teams make them now (what signals/data exist)? Confirm the problem before pitching the wedge. Wedge-resonance and willingness-to-pay questions come after, and must avoid leading the witness.
- **D-08:** Discovery interviewees = the ICP from D-01/D-03 — EMs/eng-leads of small multi-agent teams (buyer-side), with dev users probed for current delegation behavior.

### Claude's Discretion
- Product brief and discovery-script document structure/format (no template preference given).
- Exact discovery question wording and ordering, within the D-07 problem-first constraint.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product boundary & requirements
- `.planning/PROJECT.md` — locks the product boundary (team control plane, not PM clone), governance non-negotiables, web/desktop direction, heuristics-before-RL stance, and Out-of-Scope list.
- `.planning/REQUIREMENTS.md` §"Product Boundary" — BOS-PROD-01..03 (this phase) and BOS-PROD-04 (BOS7).
- `.planning/ROADMAP.md` §"BOS-prefixed phases: Behavioral OS Foundation" (lines ~113-140) — milestone stance, seed stance, build order, per-phase deliverables.

### Wedge / substrate context
- `.planning/seeds/SEED-001-coordination-bus.md` — planted context only; reframed as future external-agent CLI verbs over the existing server/SSE plane, NOT a parallel bus.
- V25 Server-Native Swarm Runtime — `.planning/ROADMAP.md` line ~109 (V25 entry) + `V25-SPEC.md`: the delegation wedge (D-02) is observed through V25's `swarm.assign` / task-ownership model. This is the first BOS event source.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- V25 server-native swarm runtime (SwarmStore, `swarm.assign`, per-task `ownedFiles`, PermissionGate) — the delegation wedge is a label/recommendation layer over events this already emits. Docs-first phase: no code reuse yet, but the brief's wedge claim depends on this substrate existing.

### Established Patterns
- Docs-first BOS track: every BOS phase produces a contract/spec before code. BOS0 sets the product framing all later BOS specs inherit.

### Integration Points
- None (docs-only). The product brief frames how the existing harness/server/ADE/swarm substrate becomes a team decision/outcome system; later phases (BOS3+) define the actual data contracts.
</code_context>

<specifics>
## Specific Ideas

- The brief's core tension and its resolution must be explicit: top-down EM buyer + dev-generated data substrate, reconciled by assuming the team is already on the Voss ADE (D-04).
- "Behavioral OS" is the north-star vision; "control plane for AI engineering teams" is the words used with design partners.
</specifics>

<deferred>
## Deferred Ideas

- Competitive set / detailed competitive analysis — can be folded into the brief if useful, but not a locked BOS0 decision.
- Pricing hypothesis / willingness-to-pay framing — discovery probes it after problem validation (D-07); not a BOS0 deliverable.
- Design-partner sourcing plan (where to find the first teams) — operational, outside the brief/script artifacts.
- Wedge success metric definition — belongs with outcome labels / reward spec (BOS5).
- Review-depth and validation-depth wedges — explicitly later wedges (D-02).
- Web vs desktop responsibility map — BOS-PROD-04 / BOS7.
</deferred>

---

*Phase: BOS0-product-thesis-icp-and-wedge*
*Context gathered: 2026-06-18*
