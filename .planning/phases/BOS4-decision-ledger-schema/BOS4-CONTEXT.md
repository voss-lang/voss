# Phase BOS4: Decision Ledger Runtime - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning
**Supersedes:** the 2026-06-18 "Decision Ledger Schema" context (schema shipped; this is the runtime reframe per ROADMAP 2026-06-20).

<domain>
## Phase Boundary

BOS4 now delivers the **decision ledger RUNTIME**: code that writes decision
records (conforming to the already-shipped `contracts/decision-ledger.schema.json`)
from real runtime gates and operator choices, into a local append-only ledger.

**Already shipped, NOT re-built here (locked inputs):**
- `contracts/decision-ledger.schema.json` — the authoritative decision record
  contract (6 `decision_type`s, envelope with `decision_id`, `as_of`,
  `feature_snapshot`, `entity_ref`, `autonomy_band`, `recommended_action`,
  `human_verdict`, `actual_action`, `rationale`, `payload`). Decisions D-01..D-08
  from the schema-era context remain in force.
- `BOS4-DECISION-LEDGER.md` — the rationale doc.

**This phase delivers:** a Python runtime writer + gate wiring that emits decision
records at decision time, for the decision types that have a real runtime producer
TODAY. Covers **BOS-DATA-02** (runtime half).

**Out of scope (explicit):** the heuristic policy that produces recommendations
(BOS9/BOS13/BOS14), outcome labels/rewards (BOS5), the BOS3 event schema itself,
cross-source identity resolution (BOS12), and the four decision types with no
runtime producer yet (`autonomy_band`, `review_depth`, `validation_depth`,
`escalation`) — schema-only until their producers land.
</domain>

<decisions>
## Implementation Decisions

### Capture Architecture
- **D-R01:** **Inline emission at gates.** Decision records are written by calling
  the decision ledger directly at the moment a gate/operator decision happens
  (swarm assignment, permission verdict) — NOT reconstructed by after-the-fact
  projection. This is the only way to faithfully freeze `as_of` +
  `feature_snapshot` at decision time (schema D-03 point-in-time correctness).
  This is a deliberate divergence from BOS3's pure-projection layer
  (`bos_events.py`): BOS4 emission is inline because decisions, unlike observed
  events, carry the exact state they were made against.

### Decision-Type Coverage (this phase)
- **D-R02:** **Wire only the types with a real runtime producer now.** Two types
  get live emission:
  - `task_to_agent` — from the swarm assignment path (`swarm.assign` /
    `swarm_runtime` role↔task pairing).
  - human-verdict-bearing records — from `PermissionGate` when a human actually
    answers a prompt.
  The other four types (`autonomy_band`, `review_depth`, `validation_depth`,
  `escalation`) stay schema-only — no stubs, no placeholder rows — until their
  producers exist (BOS9+). `no_action` is written on an explicit operator
  dismiss / do-nothing (see D-R03).

### Recommendation Framing (pre-BOS9)
- **D-R03:** **Operator-only records; `recommended_action` = `{}` (empty).** No
  heuristic policy produces a recommendation until BOS9, so records written now
  capture the actual operator/gate choice with an EMPTY `recommended_action`
  object and `rationale` describing the gate. (Schema-reconciled: the contract
  requires `recommended_action` present as `type:object` with no nulls — so
  "no recommendation yet" is `{}`, NOT `null`.) When BOS9 lands a policy, it fills `recommended_action` and
  the override-as-signal (divergence between recommended and actual) becomes
  meaningful. A permission **deny** → `human_verdict.verdict = dismiss`; an
  explicit do-nothing → a `no_action` record.

### PermissionGate → Decision Mapping
- **D-R04:** **Only human-prompted verdicts become decision records.** A decision
  is written ONLY when a prompt is actually shown to a human and they answer.
  Auto-allows (rule `allow`, `mode=auto`, safe non-mutating) remain BOS3 events
  only — they are not human decisions. Verdict mapping (pre-BOS9, no recommendation
  to diverge from): allow once / allow always → `approve`; deny → `dismiss`.
  `override` is reserved for when a recommendation exists to diverge from (BOS9+);
  `do_nothing` maps to the `no_action` path. `human_verdict` carries
  `{verdict, actor_id, verdict_at}` per the schema.

### Point-in-Time Pointer
- **D-R05:** **`as_of` = tail of the BOS3 event ledger at decision time.** At
  emission, read the tail of `.voss/bos/events.jsonl` and set `as_of` to the last
  appended BOS `event_id`, plus the active session `trace_id`. If the event
  ledger is empty, `as_of` is `{}` (empty object — schema requires `type:object`,
  no nulls; the inner tail-read returns None → `build_as_of` yields `{}`). This gives a real, immutable
  point-in-time reference into the BOS3 substrate (honors schema D-01/D-03/D-07).

### Feature Snapshot
- **D-R06:** **Minimal-real gate context, not empty, not fabricated.** Capture
  what the gate actually has at decision time:
  - `task_to_agent` → `{goal, roster (role names), available_models, cwd}`
  - permission verdict → `{tool_name, is_mutating, mode, signature, diff_summary}`
  `feature_snapshot` keeps `additionalProperties: true` so BOS9 can add real
  policy features later without a schema change. No fabricated policy/feature
  vectors now.

### Storage & Module Shape
- **D-R07:** **Separate `.voss/bos/decisions.jsonl` + new `voss/harness/bos_decisions.py`.**
  A separate append-only ledger (schema D-01), sibling to `.voss/bos/events.jsonl`.
  Follow the BOS3 `bos_ledger.py` pattern exactly: portalocker exclusive lock,
  dedup by `decision_id` (not `event_id`), torn-trailing-line tolerance on replay,
  `0o600` perms. New module holds both the record builders (for the wired types)
  and the append/replay writer.

### Carried Forward (locked elsewhere — NOT re-discussed)
- Schema D-01..D-08 (the decision record contract) — locked by
  `contracts/decision-ledger.schema.json` + `BOS4-DECISION-LEDGER.md`.
- Store = SQLite/JSONL local-first, point-in-time-correct, offline (BOS2 D-04);
  the BOS3 runtime uses a local JSONL ledger and BOS4 mirrors it.
- Governance = team-level, explainable, human override, no individual ranking
  (PROJECT.md Constraints). Human verdict is the override authority.
- No outcome leakage: outcome labels join by `decision_id` LATER (BOS5);
  never written into a decision record at decision time (schema D-04).

### Claude's Discretion
- Exact builder function signatures and internal naming in `bos_decisions.py`.
- Whether the writer reuses/generalizes BOS3's `BosEventLedger` internals or
  duplicates the small lock/dedup/replay loop (user accepted the new-module
  lock; sharing the lock primitive is an implementation detail for the planner).
- Exact `entity_ref` field population from the swarm/session context at the gate.
- Test layout (mirroring `tests/harness/test_bos_event_ledger.py`).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The locked contract (build TO this — do not change it)
- `contracts/decision-ledger.schema.json` — authoritative decision record schema;
  every emitted record MUST validate against it (BOS4-01, shipped).
- `.planning/phases/BOS4-decision-ledger-schema/BOS4-DECISION-LEDGER.md` —
  rationale doc; schema D-01..D-08, no-leakage guard, override-as-signal, open
  question on amendment policy.

### Requirements & product/governance constraints
- `.planning/REQUIREMENTS.md` — **BOS-DATA-02** (line ~31; status line ~249
  "Active; schema exists, runtime work next"). BOS-DATA-03..05 (BOS5 outcomes,
  joined later by `decision_id`).
- `.planning/PROJECT.md` — Constraints §Data (point-in-time correctness, no
  outcome leakage), §Trust (human override, explainable, no individual ranking).
- `.planning/ROADMAP.md` — BOS4 row ("Decision Ledger Runtime", line ~18 / ~146);
  BOS-track "Carry-forward implementation facts" note (line ~131+) and runtime
  stance (BOS builds over the existing harness/server/swarm plane).

### Carry-forward runtime pattern (mirror this)
- `voss/harness/bos_ledger.py` — BOS3 append-only JSONL ledger; the exact
  portalocker + dedup + torn-line + `0o600` pattern BOS4's writer mirrors.
- `voss/harness/bos_events.py` — BOS3 pure projection layer (envelope shape,
  `trace_id`/`event_id` conventions BOS4's `as_of` pointer references).
- `tests/harness/test_bos_event_ledger.py`, `tests/harness/test_bos_event_projection.py`
  — regression-gate style to mirror for BOS4 tests.

### Runtime gates being wired
- `voss/harness/permissions.py` — `PermissionGate` (`check`/`_check_impl`,
  `needs_prompt`, `_prompt`, verdict surface); D-R04 maps human-prompted answers
  to `human_verdict`.
- `voss/harness/swarm_runtime.py` — role↔task pairing / assignment; D-R02 source
  for `task_to_agent` records. Related: `swarm.assign` projection in
  `bos_events.py`.

### Architecture (carried-forward locks)
- `.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-CONTEXT.md` — D-04
  (local store), D-06 (sibling contracts/ + drift gate).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`voss/harness/bos_ledger.py` (`BosEventLedger`)**: the append-only JSONL
  writer pattern (portalocker exclusive non-blocking lock w/ 10s timeout,
  dedup-by-id read under the same lock, torn-line-tolerant replay, `0o600`).
  BOS4's `bos_decisions.py` writer is this pattern with `decision_id` as the
  dedup key and `.voss/bos/decisions.jsonl` as the path.
- **`contracts/decision-ledger.schema.json`**: the shipped target contract;
  records are built to validate against it.

### Established Patterns
- **Local append-only ledger under `.voss/bos/`**: events (BOS3) and decisions
  (BOS4) are sibling JSONL ledgers, both local-first and offline.
- **Inline emission vs pure projection**: BOS3 is pure projection (read-only over
  source logs). BOS4 deliberately breaks from this (D-R01) — decisions are emitted
  inline at the gate to freeze point-in-time state. This distinction must be
  explicit in the code so the two layers don't get conflated.

### Integration Points
- `PermissionGate` answer path → emit a verdict-bearing decision record (only on
  human-answered prompts, D-R04).
- Swarm assignment path (`swarm_runtime` / `swarm.assign`) → emit a
  `task_to_agent` decision record (D-R02).
- `as_of` reads the tail of the BOS3 `.voss/bos/events.jsonl` at emission (D-R05).
</code_context>

<specifics>
## Specific Ideas

- Every emitted record must be a **self-contained, validate-able** decision row:
  passes `contracts/decision-ledger.schema.json`, carries a real `as_of` pointer
  and a minimal-real `feature_snapshot` (D-R05/D-R06).
- **Honest emptiness**: `recommended_action` is null and the four no-producer
  decision types are simply absent — no placeholder/fake rows. The ledger reflects
  exactly what the runtime actually decides today.
- The inline-emission break from BOS3 projection (D-R01) is the keystone — call
  it out clearly in code and the plan so the purity boundary isn't accidentally
  re-imposed.
</specifics>

<deferred>
## Deferred Ideas

- **`autonomy_band`, `review_depth`, `validation_depth`, `escalation` emission** —
  no runtime producer until the heuristic/policy phases (BOS9 recommendation
  review surface; BOS13/14 offline-eval/learning lab). Schema-only for now.
- **`recommended_action` population + true override-as-signal** — needs a policy
  that recommends (BOS9). Until then `recommended_action` is null and every
  human verdict is `approve`/`dismiss`, never `override`.
- **Outcome label join** — BOS5 (BOS-DATA-03..05), joined by `decision_id` after
  the fact; never inline (schema D-04).
- **Ledger correction/amendment policy beyond append-only** — open question
  carried from `BOS4-DECISION-LEDGER.md` §Open Questions; not decided here.
- **Cross-source identity resolution** for `entity_ref` — BOS12. BOS4 populates
  only the local entity-ref shape from swarm/session context.
- **Generalizing BOS3's ledger primitive** into a shared lock/dedup util — fine
  to do if the planner sees clean reuse, but not required (D-R07 locks a new
  module; sharing internals is discretionary).

### Reviewed Todos (not folded)
None — no phase-matched todos surfaced for BOS4.
</deferred>

---

*Phase: BOS4-decision-ledger-schema (scope: Decision Ledger Runtime)*
*Context gathered: 2026-06-20*
</content>
</invoke>
