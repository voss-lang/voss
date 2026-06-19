# Phase BOS5: Outcome Labels and Reward Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS5-outcome-labels-and-reward-model
**Areas discussed:** Label assignment mechanics, Label schema shape, Reward model structure, Guardrails & bad-proxy detection

---

## Label Assignment Mechanics

### Q1: How does a raw BOS3 event become an outcome label?

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic derivation rules | Declarative rules mapping BOS3 events → labels; reproducible, auditable, no human in loop | ✓ |
| Labeling functions (programmatic) | Named functions combining multiple signals + thresholds (weak-supervision style) | |
| Human-confirmed labels | Rules propose, human confirms before training-grade | |
| Hybrid: rules + human for ambiguous | Rules for unambiguous, human for judgment calls | |

**User's choice:** Deterministic derivation rules → D-01

### Q2: How does the spec handle label timing/finality (maturation)?

| Option | Description | Selected |
|--------|-------------|----------|
| Observation windows + revisable labels | Per-type window; append-only labels superseded by later labels; as-of join uses what was known | ✓ |
| Provisional → final state machine | Status field + transition rules per type | |
| Fixed windows, single final label | Wait fixed period, emit one immutable label | |

**User's choice:** Observation windows + revisable labels → D-02

### Q3: What does an outcome label attach to (attribution)?

| Option | Description | Selected |
|--------|-------------|----------|
| Label on entity, joined to decisions | Label anchors to BOS3 entity; decisions join via entity refs + as-of; one outcome → many decisions | ✓ |
| Label directly on decision_id | Outcome written against a specific decision_id (1:1) | |
| Both: entity-anchored + decision links | Anchored to entity, carries explicit decision links | |

**User's choice:** Label on entity, joined to decisions → D-03

---

## Label Schema Shape

### Q1: How is the heterogeneous 8-label set modeled?

| Option | Description | Selected |
|--------|-------------|----------|
| Two families: categorical + measures | Closed categorical enum PLUS continuous measures (cycle time); each a typed record | ✓ |
| One enum, cycle time as attribute | Single label enum; cycle time a numeric field | |
| Everything as typed outcome events | Fully discriminated outcome-event union, one payload per kind | |

**User's choice:** Two families: categorical + measures → D-04

### Q2: Can one entity carry multiple categorical labels?

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-label, append-only over time | Entity accumulates multiple timestamped/revisable label events; reward model combines | ✓ |
| Single dominant label | Collapse to one worst/final label per entity | |
| One label per category dimension | At most one per orthogonal dimension | |

**User's choice:** Multi-label, append-only over time → D-05

### Q3: Do categorical labels carry severity/grading?

| Option | Description | Selected |
|--------|-------------|----------|
| Optional severity on relevant labels | Incident / escaped defect / rework carry optional graded severity; rest flat | ✓ |
| Flat labels only | Presence/absence; severity out of scope | |
| Severity as separate measures | Magnitude captured as continuous measures instead | |

**User's choice:** Optional severity on relevant labels → D-06

---

## Reward Model Structure

### Q1: How does the reward model compose labels/measures?

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-objective vector + named scalarization | Vector of named objectives + explicit named scalarization when one number needed | ✓ |
| Single scalar reward | One number via fixed formula | |
| Vector only, no scalarization yet | Spec vector, defer scalarization to policy/eval phases | |

**User's choice:** Multi-objective vector + named scalarization → D-07

### Q2: Where do scalarization weights live, and are they per-decision-type?

| Option | Description | Selected |
|--------|-------------|----------|
| Versioned team config, per-decision-type | Team-level, versioned with policy, may differ per decision_type; reward reproducible from (vector + weight-set version) | ✓ |
| Fixed default weights in the contract | One canonical weight set, no variation | |
| Defer weights entirely | Objectives + scalarization shape only | |

**User's choice:** Versioned team config, per-decision-type → D-08

### Q3: How are delayed/maturing outcomes treated in reward?

| Option | Description | Selected |
|--------|-------------|----------|
| Reward as-of horizons + recomputable | Provisional reward at short horizon, recomputed (append-only) as late outcomes land | ✓ |
| Single final reward at fixed horizon | Wait one fixed horizon, emit one reward | |
| Explicit time-discounting factor | Decay so later outcomes count less | |

**User's choice:** Reward as-of horizons + recomputable → D-09

---

## Guardrails & Bad-Proxy Detection

### Q1: How is bad-proxy / reward-hacking (Goodhart) detection defined?

| Option | Description | Selected |
|--------|-------------|----------|
| Paired guardrail metrics (tension pairs) | Named counter-metrics in tension with reward objectives; each objective gets ≥1 counter | ✓ |
| Statistical drift/anomaly monitors | Watch proxy-vs-ground-truth distribution drift | |
| Both: tension pairs + drift monitors | Counter-metrics now + drift hook later | |

**User's choice:** Paired guardrail metrics (tension pairs) → D-10

### Q2: What is each guardrail's enforcement role?

| Option | Description | Selected |
|--------|-------------|----------|
| Classify each: hard gate vs dashboard | Tag hard-gate (blocks autonomy/promotion in BOS15) vs dashboard; BOS5 defines metric+threshold+role | ✓ |
| All guardrails are dashboards only | Visibility only; gating deferred | |
| Define metrics, defer roles entirely | Spec metrics, defer classification | |

**User's choice:** Classify each: hard gate vs dashboard → D-11

### Q3: Which guardrails does BOS5 own vs reference?

| Option | Description | Selected |
|--------|-------------|----------|
| BOS5 owns reward/outcome guardrails only | Tension pairs + outcome-quality counters; fairness/autonomy-creep/fatigue referenced (BOS6/BOS17) | ✓ |
| BOS5 defines the full guardrail catalog | All guardrails including fairness + autonomy-creep + fatigue | |
| BOS5 owns reward guardrails + a registry stub | Reward guardrails + extensible registry shape for BOS6/BOS17 | |

**User's choice:** BOS5 owns reward/outcome guardrails only → D-12

---

## Claude's Discretion

- Outcome/reward spec doc structure/format (authoritative form = JSON Schema in `contracts/`).
- Exact field names across label enum, measures family, reward objective vector, weight-set record, guardrail-metric record.
- Default observation-window lengths + reward horizon value(s).
- The named reward objective set + scalarization function form.
- Schema versioning notation (mirror PROTOCOL.md `v` + migration-note).

## Deferred Ideas

- Concrete guardrail enforcement / policy-promotion gates → BOS15 (BOS-RL-02).
- Fairness, autonomy-creep, fatigue/nudge guardrails → BOS6 (BOS-GOV-04) / BOS17 (BOS-BEH-02).
- Statistical drift / anomaly monitors on top of tension pairs → later.
- Field-level labels for external sources (review/CI/validation/deploy/incident) → BOS12 ingestion.
- Reference/golden-label dataset + eval harness → BOS15.
- Actual reward weight VALUES + tuning (vs the config shape D-08 defines) → BOS13/14/15.
