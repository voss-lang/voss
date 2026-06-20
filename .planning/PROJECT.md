# Voss

## What This Is

Voss is an **agent engineering organization layer** and emerging **Behavioral OS for engineering teams**. The desktop ADE and harness give developers bounded, inspectable, replayable AI coding work; the Behavioral OS track turns that activity into a shared team control plane for delegation, review depth, validation, outcomes, and eventually learned policy recommendations.

The near-term product is still local-first and developer-owned. The v0.2 foundation work decides how the existing harness, server plane, desktop ADE, and server-native swarm become the data substrate for a future web control plane and team workflow suite.

## Core Value

An engineering team can route AI-assisted work through bounded, reviewable execution and convert the outcomes into a trustworthy decision dataset for better delegation, review, validation, and flow.

## Current Milestone: v0.2 Behavioral OS Runtime Foundation

**Goal:** Convert the Behavioral OS contracts and source artifacts into one executable local-runtime foundation phase over Voss's ADE/swarm runtime.

**Target features:**
- One active BOSR phase replacing the BOS0-BOS18 plus BOSI split.
- Preserve BOS0-BOS9 and BOSI1 knowledge as source material, not active phase sprawl.
- Local BOS event ledger over the existing harness/session/swarm substrate.
- Decision and outcome capture for delegation, review depth, validation depth, escalation, and no-action decisions.
- Shadow-mode heuristic recommendations before any learned policy or autonomy increase.
- Control-plane read model for desktop/web consumption without syncing raw code or prompts by default.

## Requirements

### Validated

- Voss already has a local harness/server/ADE substrate with persisted sessions, permission gates, audit surfaces, memory/recall, multi-agent organization primitives, and a server-native swarm runtime track.
- BOSI1 implemented a pure BOS event projection layer from existing `SessionRecord`, `RunRecord`, and swarm JSONL events.
- BOSR-02 added a local append-only BOS event ledger at `.voss/bos/events.jsonl` with duplicate-safe replay.

### Active

- [x] Reconcile BOS0-BOS18 and BOSI1-BOSI6 into one BOSR phase with discussion, research, and a finite executable plan set.
- [x] Persist projected BOS events in a local append-only ledger with replay/as-at reads.
- [ ] Record decision and outcome rows from runtime gates/reviews without outcome leakage into decision-time features.
- [ ] Generate shadow-mode recommendations for delegation, review depth, validation depth, and escalation using heuristic policies only.
- [ ] Expose a local read model for desktop/web control-plane surfaces while preserving private-by-default local content boundaries.
- [ ] Keep external PM/CI/deploy/incident ingestion, online learning, LEM work, multi-tenant SaaS, and PM-suite expansion out of BOSR.

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
- **Stack:** Preserve the existing monorepo shape and Voss runtime before introducing web/backend/RL services; new stack decisions must be justified in BOSR context/research first.
- **Data:** Features must be point-in-time correct; outcomes cannot leak into the state used to make the original recommendation.
- **Swarm:** BOS integrates with the existing server/SSE swarm plane. `.voss/swarm/` remains audit/shared host record, not the runtime bus.
- **Desktop/Web split:** Desktop remains local execution and ADE. Web, if built, is the team control plane and dataset/recommendation review surface.
- **Safety:** No learned policy can increase autonomy, reduce review, or skip validation without offline eval, guardrail checks, and human approval.
- **Git safety:** BOSR phases may change code when the plan explicitly targets implementation. Git write actions still require Ben's explicit approval.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Reset to `BOSR` | BOS0-BOS18 plus BOSI created too much plan-only sprawl; one executable phase keeps the knowledge and restores normal GSD flow | Active |
| Supersede docs-first split | BOS contract artifacts remain source material, but the active milestone must now ship runtime behavior | Active |
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
*Last updated: 2026-06-20 after BOSR consolidation reset*
