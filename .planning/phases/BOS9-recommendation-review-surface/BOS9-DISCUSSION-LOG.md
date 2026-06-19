# Phase BOS9: Recommendation Review Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** BOS9-recommendation-review-surface
**Areas discussed:** Contract vs BOS4 boundary, Action write-back, Display + confidence, Autonomy band reflection

---

## Contract vs BOS4 Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| View over BOS4 + display fields | References BOS4 4 payloads + adds presentation fields; no duplication | ✓ |
| New standalone contract | Own schema independent of BOS4; duplicates payloads, drift risk | |
| Extend BOS4 in place | Add UI fields into ledger record; mixes UI into training-signal ledger | |

**User's choice:** View over BOS4 + display fields. Locked as D-01.

### Follow-up: view shape

| Option | Description | Selected |
|--------|-------------|----------|
| One generic envelope + typed ref | Single view envelope wrapping any BOS4 decision_type payload; mirrors union | ✓ |
| Per-type view contracts | Distinct view per type; 4 shapes, drift risk | |
| You decide | Defer to planner | |

**User's choice:** One generic envelope + typed ref. Locked as D-02.

---

## Action Write-Back

| Option | Description | Selected |
|--------|-------------|----------|
| Each action writes a BOS4 verdict | approve/override/dismiss/do-nothing each write human_verdict; no new store | ✓ |
| New surface action log | Own UI-action log separate from BOS4; splits audit, breaks override-as-signal | |

**User's choice:** Each action writes a BOS4 verdict. Locked as D-03.

### Follow-up: verdict semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Accept / counter / decline / no-op | approve=as-is; override=different (signal); dismiss=decline-clear; do-nothing=affirmative no-op; all set actual_action | ✓ |
| Collapse dismiss into do-nothing | One action; loses signal difference | |
| You decide | Defer to planner | |

**User's choice:** Accept/counter/decline/no-op. Locked as D-04.

---

## Display + Confidence

| Option | Description | Selected |
|--------|-------------|----------|
| Rationale + band + qualitative confidence | rationale + policy version + autonomy band + low/med/high (+abstain); no numeric | ✓ |
| Rationale + numeric confidence score | numeric 0–1/%; over-trust + nudge framing | |
| Rationale only, confidence optional | require rationale + version; confidence optional until BOS13+ | |

**User's choice:** Rationale + band + qualitative confidence. Locked as D-05.

### Follow-up: training-signal logging boundary

| Option | Description | Selected |
|--------|-------------|----------|
| BOS4 owns it; BOS9 triggers | Signal = BOS4 verdict record; BOS9 defines no new logging | ✓ |
| BOS9 defines a logging contract | Own interaction/telemetry log; duplicates BOS4, risks engagement telemetry | |

**User's choice:** BOS4 owns it; BOS9 triggers. Locked as D-06.

---

## Autonomy Band Reflection

| Option | Description | Selected |
|--------|-------------|----------|
| Band drives available actions | suggest_only view-only / approve_required all / auto_with_post_review applied+override-window / full_auto log-only; kill-switch forces safe | ✓ |
| Show band, actions always available | label only, all actions enabled; contradicts BOS6 | |
| You decide | Defer to planner | |

**User's choice:** Band drives available actions. Locked as D-07.

### Follow-up: override-always reconciliation + deliverable shape

| Option | Description | Selected |
|--------|-------------|----------|
| Always-reversible + states in spec | full_auto still human-reversible (post-hoc override=signal); spec = view contract + verdict semantics + band→action matrix + interaction states; dual-target per BOS7 D-03 | ✓ |
| Contract-only, states deferred | output/view + action + band only; states to a later UI phase | |
| You decide | Defer to planner | |

**User's choice:** Always-reversible + states in spec. Locked as D-08.

---

## Claude's Discretion

- Schema representation (recommend sibling `contracts/` JSON Schema joining V13.1 drift gate + prose + matrix + state descriptions).
- Display-field names + qualitative confidence band value set.
- Exact interaction-state list beyond the named ones.
- Whether bulk/batch verdicts on team queue are in scope (lean single-item default).

## Deferred Ideas

- Policies that produce recommendations — BOS13/BOS14.
- Outcome display / post-hoc outcome join — BOS5 (no-leakage, not a pre-action signal).
- Governance policy detail + kill-switch RBAC — BOS6 / later RBAC phase.
- Bulk/batch verdicts — candidate, not pre-built.
- Stale-recommendation invalidation mechanics — surfaces in implementation.
- Building the actual desktop Review tab / web team queue — future implementation phase.
- Physical contract file layout — discretion.
