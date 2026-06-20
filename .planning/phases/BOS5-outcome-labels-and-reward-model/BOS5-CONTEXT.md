# Phase BOS5: Outcome Labels and Reward Model - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS5 produces ONE docs-first artifact: the **outcome/reward spec** contract. It covers
BOS-DATA-03 (the seven categorical outcome labels) and BOS-DATA-04 (reward + guardrail metrics, and
bad-proxy detection), defined *before* any learning system is introduced.

It defines: how raw BOS3 events become outcome labels, the label/measure schema shape,
how outcomes attach to entities and join to decisions, the reward model structure
(objectives, weights, timing), and the reward-hacking/guardrail metric contract.

It does **NOT** define: the event schema (BOS3), the decision ledger (BOS4), the
heuristic policies that produce recommendations (BOS13/14), offline evaluation /
policy-promotion gates (BOS15), the RL lab (BOS16), or governance/behavioral guardrails
beyond reward/outcome quality (BOS6 BOS-GOV-04, BOS17 BOS-BEH-02). No code, no migrations
— contract + rationale only.

**Carried forward (locked elsewhere — NOT re-discussed):**
- Outcome labels join to decisions by `decision_id` **after the fact**, never inline at
  decision time (BOS4 D-04 — the hard no-leakage guard).
- Outcomes = **separate later append-only events**, bitemporal (`event_time` +
  `ingest_time`), with as-of feature reconstruction (BOS3 D-02).
- Store = SQLite local-first, point-in-time-correct (BOS2 D-04).
- Contract mechanism = sibling JSON Schema under `contracts/` feeding the existing CI
  drift gate, extending the V13.1 artifact (BOS2 D-06).
- Language = TypeScript owns shared contracts (BOS-ARCH-02).
- Governance = team-level, explainable, human override, no individual ranking, no reward
  hacking (PROJECT.md Constraints §Trust/§Safety).
- No learned policy increases autonomy / reduces review / skips validation without offline
  eval + guardrail checks + human approval (PROJECT.md §Safety).
</domain>

<decisions>
## Implementation Decisions

### Label Assignment Mechanics (BOS-DATA-03)
- **D-01:** **Deterministic derivation rules.** Outcome labels are produced by declarative,
  reproducible rules mapping BOS3 events → labels (e.g. revert event → `revert`, failed CI →
  `failed_validation`). No human-in-the-loop labeling; rules are auditable and replayable,
  consistent with append-only as-of reconstruction. (Rejected: labeling-functions / weak
  supervision — heavier to spec/version; human-confirmed — slow, adds review burden;
  hybrid — unnecessary given deterministic rules suffice for now.)
- **D-02:** **Observation windows + revisable labels.** Each label type declares an
  observation window (e.g. a merge is `clean` only after N defect-free days). Labels are
  append-only events that can be **superseded** by a later label as outcomes mature
  (clean merge → escaped defect → incident). The as-of join always uses what was known at
  decision time, so revision never leaks future knowledge. (Rejected: provisional→final
  state machine — heavier; fixed-window single-final — loses early signal + very-late reverts.)
- **D-03:** **Labels anchor to the entity, join to decisions.** An outcome label attaches to
  the BOS3 entity it is observed on (task / PR / correlation id). Decisions join to it via
  their entity refs + as-of pointer, so ONE outcome can inform MANY decisions
  (delegation, review depth, validation depth on the same PR). Outcomes stay
  observation-faithful; credit assignment is a reward-model concern (see D-08). (Rejected:
  label directly on `decision_id` — forces premature credit assignment + duplicates outcomes
  across co-located decisions.)

### Label Schema Shape (BOS-DATA-03)
- **D-04:** **Two families — categorical labels + continuous measures.** Categorical outcome
  labels (a closed enum: clean merge, rework, revert, failed validation, escaped defect,
  incident, human override) PLUS continuous **outcome measures** (cycle time, with room for
  others). Each is its own typed outcome record. Honors that cycle time is a metric, not a
  category; mirrors the discriminated-union style in `contracts/events.schema.json`.
- **D-05:** **Multi-label, append-only over the entity lifecycle.** An entity accumulates
  multiple categorical label events over time, each timestamped + revisable per D-02. The
  reward model decides how to combine them. No information loss — the clean→defect→incident
  progression is preserved as signal. (Rejected: single dominant label — discards progression;
  one-label-per-dimension — requires defining dimensions now.)
- **D-06:** **Optional severity on relevant labels.** Labels where magnitude matters
  (incident, escaped defect, rework) carry an OPTIONAL graded severity field; others stay
  flat. Lets reward/guardrails weight a sev1 incident ≠ sev3. (Rejected: flat-only — loses
  magnitude; severity-as-separate-measures — more measures to define for little gain.)

### Reward Model Structure (BOS-DATA-04)
- **D-07:** **Multi-objective vector + named scalarization.** Reward is a **vector** of named
  objectives (e.g. throughput, quality, rework-cost, flow). A **named, explicit scalarization
  function** combines them when a single number is needed. Keeps tradeoffs legible
  (governance: explainable), avoids hiding them in one opaque number, and lets BOS15 offline
  eval compare scalarizations. (Rejected: single scalar — bakes in weights, hard to explain;
  vector-only-no-scalarization — leaves BOS-DATA-04 incomplete.)
- **D-08:** **Versioned team-level weights, per decision_type.** Scalarization weights are
  explicit **team-level** config (no individual ranking), **versioned alongside policy
  versions**, and may differ per `decision_type` (task_to_agent weights ≠ review_depth
  weights). Every reward is reproducible from (objective vector + named weight-set version).
  This is also where credit weighting across the many decisions a single outcome touches (D-03)
  is expressed. (Rejected: fixed default weights — every team inherits same tradeoffs;
  defer weights — under-specifies BOS-DATA-04.)
- **D-09:** **Reward as-of horizons + recomputable.** Reward is computed against an outcome
  **horizon** and is itself **revisable**: a provisional reward at a short horizon, recomputed
  as late outcomes land (append-only, never mutating the original decision). The spec declares
  the standard horizon(s). Matches the revisable-label model (D-02) and the no-leakage guard;
  BOS15 eval can pick a horizon. (Rejected: single final reward at fixed horizon — discards
  early signal, mishandles very-late outcomes; explicit time-discounting — adds a tuning knob
  that can mask severe late incidents.)

### Guardrails & Bad-Proxy Detection (BOS-DATA-04)
- **D-10:** **Paired guardrail metrics (tension pairs).** Reward-hacking / Goodhart detection
  is specified as **named counter-metrics in tension with reward objectives** — e.g. if
  cycle-time↓ (rewarded) while escaped-defects↑ or rework↑, flag gaming. Each reward objective
  gets ≥1 counter-metric. Concrete, explainable, directly catches Goodhart; feeds BOS-GOV-04
  dashboards + BOS15 gates. (Rejected: statistical drift/anomaly monitors alone — vaguer to
  spec now, needs a data baseline; both — more than needed this phase, drift hook deferred.)
- **D-11:** **Classify each guardrail: hard gate vs dashboard.** Every guardrail metric is
  tagged either **hard-gate** (a breach blocks autonomy increase / policy promotion, enforced
  in BOS15) or **dashboard/monitor** (surfaced to BOS-GOV-04, no auto-block). BOS5 defines the
  metric + threshold *shape* + role; BOS15 wires the actual gate. Honors PROJECT.md §Safety
  without BOS5 owning enforcement mechanics. (Rejected: dashboards-only — weakens "guardrail
  metrics before learning"; defer roles entirely — minimal, leaves BOS-DATA-04 thin.)
- **D-12:** **BOS5 owns reward/outcome guardrails ONLY.** BOS5 specifies reward-hacking +
  outcome-quality guardrails (the tension pairs; escaped-defect / incident / rework counters).
  Fairness, autonomy-creep, and fatigue/nudge guardrails are **referenced as consumers** of
  these metrics but defined in BOS6 (BOS-GOV-04) / BOS17 (BOS-BEH-02). Clean phase boundary,
  no scope creep. (Rejected: full guardrail catalog — pulls BOS6/BOS17 scope forward;
  registry stub — more structure than needed now.)

### Claude's Discretion
- Outcome/reward spec doc structure/format. Per BOS2 D-06 the authoritative form is a JSON
  Schema under `contracts/` (sibling to `events.schema.json`); supporting prose/tables are
  discretionary.
- Exact field names within the categorical label enum, the measures family, the reward
  objective vector, the weight-set record, and the guardrail-metric record.
- Concrete default observation-window lengths and reward horizon value(s) — recommended to
  propose sensible defaults; exact numbers are discretionary and tunable.
- The exact named objective set in the reward vector (D-07) and the named scalarization
  function form — recommend throughput / quality / rework-cost / flow as a starting set.
- Schema versioning notation — mirror PROTOCOL.md's `v` + migration-note convention (as BOS3/BOS4 did).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & product/governance constraints
- `.planning/REQUIREMENTS.md` — **BOS-DATA-03** (line ~27, outcome labels) and **BOS-DATA-04**
  (line ~28, reward + guardrail metrics) — the target requirements. Related: BOS-DATA-05 (BOS15
  offline eval consumes these), BOS-GOV-04 (line ~80, guardrail dashboards — downstream consumer),
  BOS-RL-02 (BOS15 guardrail gates).
- `.planning/PROJECT.md` — Constraints §Data (point-in-time correct, no outcome leakage),
  §Trust (team-level, explainable, no individual ranking, no reward hacking), §Safety (no
  autonomy increase / review reduction / validation skip without offline eval + guardrails +
  human approval). Goals line ~39 (outcome labels + reward/guardrail before online learning).
- `.planning/ROADMAP.md` — BOS5 row (line ~20) + BOS3–BOS6 "data and trust substrate"
  build-order note (~line 121, 141).

### Upstream BOS locks (this phase builds on)
- `.planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md` — D-02 (append-only
  bitemporal, outcomes as separate later events, as-of reconstruction — the structural basis
  for D-02/D-09 here), D-04 (stable entity IDs + correlation id — the anchor for D-03).
- `.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md` — D-04 (outcome labels join
  by `decision_id` after the fact, never inline — the no-leakage contract BOS5 must satisfy),
  D-03 (frozen feature snapshot / self-contained training row), D-02 (`decision_type` set that
  D-08's per-type weights key off).
- `.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md` — D-04 (SQLite
  local store), D-06 (sibling JSON Schema in `contracts/` + drift gate, extend V13.1).

### Existing contract substrate (the form the outcome/reward schema takes)
- `contracts/events.schema.json` — existing discriminated-union JSON Schema; the
  categorical-vs-measures families (D-04) and outcome-event records mirror this pattern.
  BOS3 event schema, BOS4 decision ledger, and this BOS5 outcome/reward schema are siblings here.
- `contracts/openapi.json` — the committed V13.1 contract artifact; the CI drift gate the
  outcome/reward schema joins.

### Downstream consumers (referenced, NOT defined here — D-12)
- BOS6 governance / BOS-GOV-04 guardrail dashboards — consume the guardrail metrics (D-10/D-11).
- BOS13/BOS14 heuristic policies — produce decisions whose rewards are computed via D-07/D-08.
- BOS15 offline eval / policy-promotion gates — wire D-11 hard-gate guardrails and pick reward
  horizons (D-09).
- BOS17 behavioral guardrails (BOS-BEH-02) — fatigue/fairness, separate from reward guardrails.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`contracts/events.schema.json` discriminated-union pattern** — D-04's categorical-labels +
  continuous-measures families and the typed outcome-event records follow the same
  pydantic-`Field(discriminator=...)` → JSON Schema → codegen pattern already used for the
  runtime event union and (per BOS4) the decision ledger.
- **V13.1 contract artifact + CI drift gate** (BOS2 D-06) — the outcome/reward schema joins
  this rather than introducing new contract tooling.

### Established Patterns
- **Docs-first BOS track** — contract before code. BOS5's outcome/reward contract is inherited
  by the policy phases (BOS13/14) that earn rewards and the eval phase (BOS15) that gates on
  guardrails and reward horizons.
- **Append-only + point-in-time correctness** — D-02/D-05/D-09 (revisable labels + recomputable
  rewards as append-only events) extend BOS3 D-02 and the BOS2 D-04/D-05 store model; no
  in-place mutation, no future leakage.
- **`v` + migration-note versioning** (PROTOCOL.md convention, adopted by BOS3/BOS4) — adopt
  for the outcome/reward schema.

### Integration Points
- None executed (docs-only). The contract frames how outcome labels are derived from BOS3
  events (D-01), attached to entities and joined to BOS4 decisions (D-03), composed into
  rewards (D-07/D-08/D-09), and monitored for gaming (D-10/D-11/D-12).
</code_context>

<specifics>
## Specific Ideas

- **Outcomes mature and revise** — the clean-merge → escaped-defect → incident progression
  (D-02/D-05) is treated as first-class signal, not an error to correct. Append-only label
  events + observation windows make late reverts/incidents land without mutating history.
- **Tension pairs are the anti-Goodhart core** (D-10) — every rewarded objective gets a named
  counter-metric so "cycle-time down but rework/escaped-defects up" is caught structurally, not
  noticed by accident. This is the BOS-DATA-04 "bad-proxy detection" requirement made concrete.
- **Reward is reproducible and revisable** (D-08/D-09) — (objective vector + named weight-set
  version + horizon) fully reconstructs any reward; provisional rewards recompute as outcomes
  mature, never editing the original decision row.
- **Entity-anchored outcomes, decision-side credit** (D-03/D-08) — keep observation faithful;
  push the "which decision deserves credit" question into the reward model where weights/versions
  make it explainable.
</specifics>

<deferred>
## Deferred Ideas

- **Concrete guardrail enforcement / policy-promotion gates** — BOS5 defines metric + threshold
  shape + gate-vs-dashboard role (D-11); the actual gating mechanism is BOS15 (BOS-RL-02).
- **Fairness, autonomy-creep, fatigue/nudge guardrails** — BOS6 (BOS-GOV-04) / BOS17 (BOS-BEH-02).
  BOS5 owns reward/outcome guardrails only (D-12).
- **Statistical drift / anomaly monitors** for proxy-vs-ground-truth divergence — possible later
  addition on top of the tension-pair guardrails (D-10); not specified this phase.
- **Field-level labels for external sources** (review / CI / validation / deploy / incident as
  external integrations) — depend on BOS12 ingestion filling BOS3's reserved external slots;
  BOS5 specifies the label/measure semantics, BOS12 fills the source field detail.
- **Reference/golden-label dataset + eval harness** that consumes outcomes and rewards — BOS15.
- **Actual reward weight VALUES and tuning** (vs the versioned config shape D-08 defines) —
  set per team and refined in BOS13/14/15.

### Reviewed Todos (not folded)
None — no phase-matched todos surfaced for BOS5.

</deferred>

---

*Phase: BOS5-outcome-labels-and-reward-model*
*Context gathered: 2026-06-18*
