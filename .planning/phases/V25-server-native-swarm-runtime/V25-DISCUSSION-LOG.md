# Phase V25: Server-Native Swarm Runtime — Discussion Log

**Date:** 2026-06-17
**Mode:** discuss (default)
**SPEC:** loaded (11 requirements locked) — discussion limited to HOW

> Human-reference audit log. Not consumed by downstream agents (they read CONTEXT.md + SPEC.md).

## Areas Discussed

### 1. Coordinator shape
- **Options:** full ServerSession agent · one-shot orchestrator call (A13 D-03) · server orchestrator no-LLM
- **Selected:** Full ServerSession agent → **D-01**
- **Note:** Reverses A13 D-03. Coordinator = first-class session that seeds tasks, emits `swarm.assign`, re-plans mid-run.

### 2. V24 Swarm Map feed
- **Options:** dedicated swarm event stream · fit existing RunData/registry · both
- **Selected:** Dedicated `swarm.*` event stream; `swarmReconcile` consumes directly → **D-03**
- **Note:** Honest-signal by construction. Small V24 follow-up flagged (deferred).

### 3. Audit layer / A13-01 reuse
- **Options:** new JSONL log + A13 manifest as derived view · reuse A13 schema as-is · JSONL only, retire A13 files
- **Selected:** New append-only `events/*.jsonl` as truth; A13 manifest/tasks/results = derived snapshot → **D-04**
- **Note:** A13-01 Rust/TS writers demoted to snapshot rendering, not deleted.

### 4. Role-prompt templates
- **Options:** harness templates + BridgeSwarm playbook seed · generated into `.voss/swarm/prompts/` · minimal inline
- **Selected:** Versioned harness templates (`voss/harness/swarm/prompts/`), coordinator seeded from BridgeSwarm playbook → **D-05**

## Carried Forward (not re-asked)
- A13 D-02 single-coordinator (not P2P), D-12 max-6-concurrent cap — reused
- A13 D-20 soft scope → REVERSED by VSWARM-05 (hard gate enforcement)
- V24 honest-signal rule (render only real events)

## Claude's Discretion (handed to planner)
- Ownership-policy injection mechanics (SPEC pins "reuse project-policy layer")
- Event envelope schema (constrained by append-only + swarmReconcile consumption)
- Spawn-gate `waiting` mechanics (new session state vs lazy creation)

## Deferred Ideas
- V24 `swarmReconcile` swarm-event consumer (→ V24 backlog)
- voss-app swarm spawn UI / roster sidebar (→ V24/voss-app)
- Coordinator decomposition-quality evals (→ E-track)
- V25 ↔ V5/V7 cage convergence (later, not this phase)

---

*Phase: V25-server-native-swarm-runtime*
*Discussion logged: 2026-06-17*
