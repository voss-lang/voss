# Phase BOS9: Recommendation Review Surface - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS9 produces the **recommendation review surface spec** (BOS-REC-01..03): a docs-first
UI/contract specification for how recommendations are reviewed and acted on. It defines
(a) the **output/view contract** for delegation, review-depth, validation-depth, and
escalation recommendations, (b) the **approve / override / dismiss / do-nothing** action
model and how each writes back, (c) what each recommendation must **display** (rationale,
confidence, policy version) and where training-signal logging lives, and (d) how the
surface reflects **autonomy bands + kill-switch** and interaction states.

This phase is a **presentation + view-contract layer over BOS4**, honoring BOS6 governance
and BOS7's dual-target placement. It is **spec only — no code, no UI implementation.** It
does NOT: re-define the decision-ledger schema (BOS4 owns it — BOS9 references/views it);
define the policies that PRODUCE recommendations (BOS13 delegation, BOS14 review/validation);
define governance policy itself (BOS6); define outcome labels/reward (BOS5); or build the
desktop/web apps (BOS9 specs the contract both render).
</domain>

<decisions>
## Implementation Decisions

### REC-03 Output Contract ↔ BOS4 Ledger
- **D-01:** **View over BOS4 + display-only fields — no payload duplication.** The REC-03
  output contract REFERENCES BOS4's existing `decision_type` payloads (`task_to_agent` =
  delegation, `review_depth`, `validation_depth`, `escalation`) and adds only
  presentation-layer fields (display rationale, confidence, autonomy band, available
  actions). It does NOT redefine or copy the 4 payloads. Rejected: new standalone contract
  (duplicates payloads, drift risk vs ledger); extend-BOS4-in-place (mixes UI concerns into
  the training-signal ledger).
- **D-02:** **One generic recommendation-view envelope wrapping a typed payload ref.** A
  single view envelope (display fields + available actions + band + confidence) carries a
  typed reference to ANY BOS4 `decision_type` payload — one shape renders all 4 recommendation
  types, mirroring BOS4's discriminated-union style. Rejected: per-type view contracts (4
  shapes to maintain, drift vs BOS4 union); leaving it fully to discretion (the envelope
  decision is load-bearing enough to lock).

### REC-01 Action Model & Write-Back
- **D-03:** **Each surface action writes a BOS4 `human_verdict` record — no new action store.**
  approve / override / dismiss / do-nothing each persist a BOS4 verdict (actor id + timestamp
  + `actual_action`), per BOS4 D-05. The surface is a write-path INTO the existing ledger, not
  a parallel log. This preserves BOS4 D-06 override-as-signal. Rejected: a separate BOS9 UI
  action log (splits the audit trail, breaks override-as-signal capture).
- **D-04:** **Four distinct verdict semantics — accept / counter / decline / no-op.**
  - `approve` = take the recommended action as-is (`actual_action` = `recommended_action`).
  - `override` = take a DIFFERENT action (`actual_action` ≠ `recommended_action`) — this
    divergence is the high-value learning signal (BOS4 D-06).
  - `dismiss` = decline/clear the recommendation without acting now (reject this rec).
  - `do-nothing` = affirmatively choose to take no action (the right move is to do nothing;
    esp. for `no_action` recommendations).
  - All four set `actual_action` explicitly. Rejected: collapsing dismiss into do-nothing
    (loses the signal difference between "reject this rec" and "doing nothing is correct").

### REC-02 Display & Confidence
- **D-05:** **Mandatory display: rationale + policy version + autonomy band + qualitative
  confidence.** Each recommendation shows a human-readable rationale (from BOS4), the policy
  version, the current autonomy band, and confidence as a QUALITATIVE band (e.g. low/med/high)
  with an optional `abstain`. **No numeric confidence score** — avoids false precision over an
  early heuristic and avoids engagement-metric/nudge framing (BOS6 ban). Rejected: numeric
  0–1/% confidence (invites over-trust + score-chasing); rationale-only (under-serves REC-02's
  confidence requirement).
- **D-06:** **Training-signal logging is owned by BOS4; BOS9 only triggers it.** The training
  signal IS the BOS4 verdict record (frozen feature snapshot + override-as-signal, BOS4
  D-03/D-06). BOS9 defines NO new telemetry/interaction log — acting on the surface triggers
  the BOS4 write. The spec cites this boundary explicitly. Rejected: a BOS9 per-recommendation
  interaction/telemetry log (duplicates BOS4, edges into engagement telemetry BOS6 bans).

### Autonomy Band Reflection (BOS6 tie-in)
- **D-07:** **Autonomy band drives the available action set per recommendation.**
  - `suggest_only` = view-only (no write action).
  - `approve_required` = approve / override / dismiss / do-nothing all active.
  - `auto_with_post_review` = already-applied + an override/undo window.
  - `full_auto` = log-only / audit view.
  - The global + per-surface **kill-switch** (BOS6 D-02) forces all affected recommendations
    to a safe state (suggest_only/off). Rejected: show-band-but-all-actions-always-enabled
    (contradicts BOS6 band semantics).
- **D-08:** **Human override is always-reversible, even in `full_auto`; spec includes
  interaction states.** Even an auto-applied recommendation keeps a post-hoc override/flag
  path (which writes an override verdict = signal) — this satisfies BOS6 "human override
  always." Deliverable shape = view contract + verdict-action semantics + band→action-availability
  matrix + **interaction states** (review queue, empty, loading, stale/invalidated
  recommendation, post-kill-switch). Per BOS7 D-03 the SAME contract renders to BOTH targets:
  **desktop = my-scope** (the user's own recommendations), **web = team-scope** (team queue).
  Rejected: contract-only with states deferred (D-08 keeps states in scope so the surface is
  fully specified before implementation).

### Claude's Discretion
- Schema representation format — recommend the view envelope as a sibling JSON Schema under
  `contracts/` (consistent with BOS4 D-02 / BOS2 D-06 drift-gated contracts) PLUS prose +
  the band→action matrix + state descriptions. Final file layout = planner/researcher discretion.
- Exact display-field names + the qualitative confidence band value set (within D-05).
- Exact interaction-state list beyond the named ones (within D-08).
- Whether bulk/batch verdicts on the team queue are in scope (lean default: single-item; note
  as a candidate, don't pre-build).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & requirements
- `.planning/ROADMAP.md` BOS phase table (~line 24: BOS9 = "Recommendation Review Surface",
  deliverable "UI/contract spec") + BOS rollup (~line 158) + coverage row (~line 2705:
  BOS-REC-01..03 = 3 reqs).
- `.planning/REQUIREMENTS.md` lines 43–45 (BOS-REC-01 four actions; BOS-REC-02
  rationale/confidence/policy-version/training-signal logging; BOS-REC-03 output contracts for
  delegation/review-depth/validation-depth/escalation) + line 250 (coverage row).
- `.planning/PROJECT.md` — Constraints §Trust (explainable, human override always, no individual
  ranking), Out-of-Scope (no nudge-engagement optimization).

### Locked upstream context (carry-forward — DO read, do not contradict)
- `.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md` — **load-bearing.** D-02 (the
  4 decision_type payloads BOS9 views), D-05 (`recommended_action`/`human_verdict ∈
  {approve,override,dismiss,do-nothing}`/`actual_action`), D-03 (frozen feature snapshot +
  rationale), D-06 (override-as-signal). BOS9 D-01/D-03/D-06 sit directly on these — DO NOT
  redefine the ledger.
- `.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-CONTEXT.md` — D-01 (4
  autonomy bands), D-02 (global + per-surface kill-switch), D-03 (override always / increase
  gated), hard bans (no nudge-engagement optimization, no individual ranking). BOS9 D-05/D-07/D-08
  honor these.
- `.planning/phases/BOS7-web-control-plane-boundary/BOS7-CONTEXT.md` — D-03 (ONE BOS9 output
  contract renders desktop my-scope + web team-scope, no logic duplication). BOS9 D-08 implements
  the dual-target requirement.
- `.planning/phases/BOS8-team-project-and-work-model/BOS8-CONTEXT.md` — recommendations act on
  BOS8 work items (task/PR/agent-run etc.); the view envelope references work-item entities via
  BOS4's entity refs.
- `.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md` — outcomes join to
  decisions by `decision_id` after the fact; NOT shown as a pre-action signal on the surface
  (no-leakage).

### Existing contract substrate (the form the view contract takes)
- `contracts/events.schema.json` + the BOS4 decision-ledger schema (sibling under `contracts/`)
  — the discriminated-union JSON Schema style D-02's envelope mirrors; the V13.1 drift gate the
  view contract should join (`contracts/openapi.json`).

### Existing surface (reality the contract renders into)
- `apps/voss-app` PortalShell Review tab (V24, per BOS7) — the desktop my-scope render target for D-08.

### Forward dependencies BOS9 constrains / depends on (reference, don't design)
- BOS13 (delegation) / BOS14 (review/validation) policies — PRODUCE the recommendations BOS9 renders.
- BOS15 offline eval — gates autonomy-band increases (BOS6 D-03) the surface reflects.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- BOS4 decision-ledger schema (sibling `contracts/` JSON Schema) — BOS9's view envelope references
  its `decision_type` payloads + verdict fields rather than redefining them (D-01/D-02/D-03).
- `contracts/events.schema.json` discriminated-union pattern — the envelope+typed-ref shape (D-02)
  mirrors it; codegen/drift-gate friendly.
- `apps/voss-app` PortalShell Review tab (V24) — desktop my-scope render target (D-08).

### Established Patterns
- Docs-first BOS track: contract before code. BOS9 artifact = UI/contract spec (view contract +
  action semantics + band→action matrix + interaction states).
- View-over-ledger: BOS9 is a derived presentation layer; BOS4 stays the system of record for
  decisions + verdicts (D-01/D-06).
- Privacy/trust by placement: dual-target rendering rides BOS7 D-03; no new telemetry rides BOS6 ban.

### Integration Points
- BOS9 view contract is consumed by the future desktop Review tab + web team queue (both render the
  single contract per BOS7 D-03). Surface actions write back to the BOS4 ledger. No runtime built here.
</code_context>

<specifics>
## Specific Ideas

- BOS9 is a **view over BOS4**, not a second source of truth — the load-bearing line. The output
  contract references the 4 BOS4 payloads via one generic envelope (D-01/D-02); verdicts write to
  BOS4 (D-03); the training signal is the BOS4 record (D-06).
- The four verdicts are kept semantically distinct (accept/counter/decline/no-op, D-04) precisely so
  the override and do-nothing signals stay learnable — collapsing them would destroy signal.
- Qualitative confidence + no numeric score (D-05) and no interaction telemetry (D-06) are deliberate
  anti-nudge / anti-false-precision choices tracing to BOS6 — state them as constraints, not defaults.
- "Human override always-reversible even in full_auto" (D-08) is the reconciliation of BOS6's
  override-always rule with auto bands — must be explicit so full_auto doesn't read as irreversible.

</specifics>

<deferred>
## Deferred Ideas

- The delegation / review-depth / validation-depth policies that PRODUCE recommendations — BOS13/BOS14.
- Outcome label display / post-hoc outcome join on the surface — BOS5 joins by `decision_id` after the
  fact; not a pre-action signal (no-leakage).
- Governance policy detail (band definitions, kill-switch RBAC: who may flip it) — BOS6 (+ a later
  RBAC phase); BOS9 reflects bands, doesn't set them.
- Bulk/batch verdicts on the team queue — candidate, lean default single-item, not pre-built (D-08 discretion).
- Stale-recommendation invalidation mechanics (how a rec is marked stale when underlying state changes)
  — named as an interaction state in D-08; deeper mechanics may surface in implementation.
- Actually building the desktop Review tab / web team queue — future implementation phase; BOS9 is the
  contract+UX spec only.
- Schema representation / physical contract file layout — Claude's discretion (recommend sibling
  `contracts/` JSON Schema joining the V13.1 drift gate).

### Reviewed Todos (not folded)
None — no todo cross-reference matches surfaced for this phase.

</deferred>

---

*Phase: BOS9-recommendation-review-surface*
*Context gathered: 2026-06-19*
