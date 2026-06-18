# Phase BOS0: Product Thesis, ICP, and Wedge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS0-product-thesis-icp-and-wedge
**Areas discussed:** ICP / first beachhead, Primary wedge, Buyer/user + motion, Discovery script intent, Adoption-tension resolution, Positioning/category

---

## ICP / First Beachhead

| Option | Description | Selected |
|--------|-------------|----------|
| Small multi-agent eng team (3-15) | Teams already running multiple coding agents; real team-control-plane buyer + they generate ADE/swarm events | ✓ |
| Solo / power-user dev | Closest to today's product; weak pull for a team control plane | |
| Devex / platform team at scale-up | Strong buyer but long cycle, weaker wedge observability | |

**User's choice:** Small multi-agent eng team (3-15)
**Notes:** Recommended option; aligns with "team control plane" framing and the data-substrate dependency.

---

## Primary Wedge

| Option | Description | Selected |
|--------|-------------|----------|
| Delegation: task → agent/human | Already modeled in V25 swarm assignment; most observable today; natural entry decision | ✓ |
| Review-depth | Highest trust pain, but needs review-outcome data harder to observe early | |
| Validation-depth | Depends on CI/validation ingestion (BOS12) not yet built | |

**User's choice:** Delegation
**Notes:** Recommended; directly observable through V25 `swarm.assign`.

---

## Buyer / User + Motion

| Option | Description | Selected |
|--------|-------------|----------|
| Dev-led → lead becomes buyer | Bottoms-up dev adoption, EM converts to buyer (was the recommended option) | |
| Top-down: EM/lead buys | Eng-lead buys for team, ICs use; faster monetization | ✓ |
| You decide | Infer motion from ICP + wedge | |

**User's choice:** Top-down: EM/lead buys
**Notes:** Diverged from the recommendation (dev-led). Created a tension with the dev-generated data substrate — resolved below.

---

## Discovery Script Intent

| Option | Description | Selected |
|--------|-------------|----------|
| Problem + current decision behavior | Mom-Test: validate the problem & how teams decide today before pitching | ✓ |
| Wedge resonance | Lead by testing the specific recommendation; risks leading-the-witness | |
| Willingness to adopt/pay | Probe budget/authority first; premature before problem confirmed | |

**User's choice:** Problem + current decision behavior
**Notes:** Recommended; willingness-to-pay deferred to later in the interview sequence.

---

## Adoption-Tension Resolution (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Devs already on Voss ADE; EM buys control plane on top | Assume existing ADE usage; EM buys the team layer over data devs already generate; no new dev behavior | ✓ |
| EM mandates ADE adoption as part of purchase | Cleaner sale, bets on mandated dev-tool adoption | |
| Land via dev champions, expand to EM purchase | Hybrid; de-risks data dependency but contradicts pure top-down | |

**User's choice:** Devs already on Voss ADE; EM buys the control plane on top
**Notes:** Resolves the top-down-buyer vs dev-generated-substrate tension. Brief must state this assumption explicitly.

---

## Positioning / Category (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| "Control plane for AI engineering teams" | External framing; keep "Behavioral OS" internal; NOT a PM clone, NOT individual surveillance | ✓ |
| "Behavioral OS" as external category | Distinctive but unproven category language; risks confusing design partners | |
| AI-agent delegation/management copilot | Narrowest; hugs the wedge but undersells the ambition | |

**User's choice:** "Control plane for AI engineering teams" (external); "Behavioral OS" (internal north-star)
**Notes:** Anti-positioning required in the brief: not Jira/Linear/Atlassian, not individual ranking/surveillance.

---

## Claude's Discretion

- Product brief and discovery-script document structure/format.
- Exact discovery question wording/ordering within the problem-first constraint.

## Deferred Ideas

- Competitive analysis depth, pricing hypothesis, design-partner sourcing plan, wedge success metric (→ BOS5), review/validation wedges (later), web/desktop map (BOS-PROD-04 / BOS7).
