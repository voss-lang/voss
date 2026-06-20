# Voss

## What This Is

Voss is an **agent engineering organization layer** and emerging **Behavioral OS for engineering teams**. The desktop ADE and harness give developers bounded, inspectable, replayable AI coding work; the Behavioral OS track turns that activity into a shared team control plane for delegation, review depth, validation, outcomes, and eventually learned policy recommendations.

The near-term product is still local-first and developer-owned. The v0.2 foundation work decides how the existing harness, server plane, desktop ADE, and server-native swarm become the data substrate for a future web control plane and team workflow suite.

## Core Value

An engineering team can route AI-assisted work through bounded, reviewable execution and convert the outcomes into a trustworthy decision dataset for better delegation, review, validation, and flow.

## Current Milestone: v0.2 Behavioral OS Foundation

**Goal:** Establish the product, technical, data, and governance foundation for a Behavioral OS that sits above Voss's ADE/swarm runtime and can later expand into an engineering-team project management suite.

**Target features:**
- BOS product thesis, ICP, wedge, and phase prefixing.
- Legacy planning audit so stale v0.1/v0.1.1 docs are indexed before any archive/removal.
- Monorepo and stack architecture for desktop ADE, web control plane, backend/event ledger, and Python RL/eval lab.
- Engineering event schema, decision ledger, outcome labels, and guardrails for delegation/review/flow recommendations.
- Swarm integration requirements: BOS consumes the existing server/SSE swarm plane and `SEED-001`, not a parallel coordination bus.
- Initial roadmap from BOS0 through BOS18 with docs-first phases before implementation.
- BOSI implementation track that turns BOS contracts into runtime behavior in narrow, testable slices.

## Requirements

### Validated

- Voss already has a local harness/server/ADE substrate with persisted sessions, permission gates, audit surfaces, memory/recall, multi-agent organization primitives, and a server-native swarm runtime track.

### Active

- [ ] Define the Behavioral OS product boundary: ADE execution node plus shared team control plane, not a generic PM clone.
- [ ] Decide web-vs-desktop responsibility: desktop remains the local execution/ADE node; web owns shared team state, dataset review, and management workflows when introduced.
- [ ] Define a BOS phase prefix and roadmap that is explicit enough to avoid compressing product, data, governance, RL, and PM-suite expansion into one oversized phase.
- [ ] Audit old planning docs before archiving or deletion; preserve historical V/M/A/F/E/V-track context where it still constrains BOS.
- [ ] Specify an engineering event schema covering tasks, PRs, sessions, swarm events, review, CI, validation, deploy, and incident outcomes.
- [ ] Specify a decision ledger for recommendation actions: task-to-agent, autonomy band, review depth, validation depth, escalation, and do-nothing.
- [ ] Specify outcome labels and reward/guardrail metrics before any online learning.
- [ ] Specify governance defaults: team-level reporting, human override, no individual ranking, no nudge engagement optimization, and no autonomy increase without offline eval.
- [ ] Specify the monorepo stack evolution needed for a future web app, backend/event store, shared contracts, desktop client, and Python RL/eval services.
- [ ] Map the current server-native swarm runtime into BOS as the first local ADE event source.
- [ ] Reframe `SEED-001` as an external-agent surface over the existing server plane, not a new coordination substrate.
- [ ] Implement the first BOSI runtime slice: project existing session/run/swarm records into BOS event-schema records without changing the source writers.

### Out of Scope

- Production RL or autonomous policy execution in this milestone - start with schemas, logs, heuristics, and offline-eval design.
- Replacing Jira/Linear/Atlassian in v0.2 - define the path, but do not build a full PM suite yet.
- Cloud sync, accounts, billing, multi-tenant SaaS, or enterprise admin in this milestone - design boundaries only.
- Individual-developer rankings, raw activity scoring, keystroke telemetry, or productivity leaderboards - incompatible with the trust model.
- A parallel coordination bus for external agents - BOS must use the existing harness server/SSE/swarm plane.
- Deleting old planning docs without an audit/archive index - too much project context is encoded in historical tracks.

## Context

- **Existing substrate:** Voss already has the harness server, SSE event union, session trees, budget/scope controls, audit surfaces, memory/recall, voss-app desktop ADE, and a V25 server-native swarm runtime track.
- **Swarm impact:** Current swarm architecture already provides server-side state, task ownership, assignment, operator gates, worker completion, and audit files. BOS should observe and label those events rather than create new coordination infrastructure.
- **Planted seed:** `SEED-001-coordination-bus` remains relevant as a future external-agent CLI surface, but only as a thin client over the existing server plane.
- **Product direction:** The Behavioral OS should land first as a narrow recommendation/data layer over AI-assisted engineering work, then expand toward engineering-team workflow management after the decision/outcome corpus exists.
- **Learning direction:** The pragmatic v1 is not a foundation model or online RL. It is a point-in-time-correct event store, decision ledger, heuristic policies, approve/override UI, outcome labeling, and offline evaluation. Bandits/RL follow only after enough logged decisions exist.

## Constraints

- **Trust:** Team-level defaults, explainable recommendations, human override, and auditability are non-negotiable.
- **Stack:** Preserve the existing monorepo shape and Voss runtime before introducing web/backend/RL services; new stack decisions must be justified in BOS architecture docs first.
- **Data:** Features must be point-in-time correct; outcomes cannot leak into the state used to make the original recommendation.
- **Swarm:** BOS integrates with the existing server/SSE swarm plane. `.voss/swarm/` remains audit/shared host record, not the runtime bus.
- **Desktop/Web split:** Desktop remains local execution and ADE. Web, if built, is the team control plane and dataset/recommendation review surface.
- **Safety:** No learned policy can increase autonomy, reduce review, or skip validation without offline eval, guardrail checks, and human approval.
- **Git safety:** BOS foundation phases are docs-only; BOSI phases may change code when the plan explicitly targets implementation. Git write actions still require Ben's explicit approval.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| v0.2 uses `BOS` phase prefixes | Behavioral OS work is distinct from harness, ADE, V-track org runtime, and eval tracks | Active |
| Start docs-first | The product, stack, data, and governance choices are not yet stable enough for implementation | Active |
| Add `BOSI` implementation phases | BOS contracts alone do not ship behavior; implementation needs separate, code-backed phases | Active |
| Web is the shared control plane; desktop is the local ADE node | Team workflow state needs shared access; code execution and agent panes stay local-first | Pending validation |
| Swarm is the first BOS event source | V25 already models multi-agent task assignment, ownership, gates, and completion | Active |
| `SEED-001` wraps the server plane | Voss has a daemon/SSE bus, so a second file bus would fragment coordination | Active |
| Heuristics and offline eval come before RL | Logged outcomes and counterfactual evaluation are prerequisites for safe learning | Active |
| Governance is part of the foundation | Behavioral products fail if trust, surveillance boundaries, and guardrails are bolted on later | Active |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone**:
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-18 after v0.2 Behavioral OS Foundation milestone start*
