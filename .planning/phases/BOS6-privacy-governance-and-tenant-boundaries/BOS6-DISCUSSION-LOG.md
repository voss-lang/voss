# Phase BOS6: Privacy, Governance, and Tenant Boundaries - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS6-privacy-governance-and-tenant-boundaries
**Areas discussed:** Autonomy bands & kill-switch, Privacy classes & tenant boundary, Anti-surveillance aggregation rule, Guardrail dashboards + scope boundary

---

## Autonomy Bands & Kill-Switch

| Option | Description | Selected |
|--------|-------------|----------|
| 4 bands + global & per-surface kill-switch, increase gated | suggest_only→approve_required→auto_with_post_review→full_auto; kill-switch both scopes; increase needs BOS15 eval + guardrail + approval | ✓ |
| 3 bands + global kill-switch only | suggest/approve/auto; single global kill-switch | |
| You decide | — | |

**User's choice:** 4 bands + global & per-surface kill-switch, increase gated (recommended)
**Notes:** Decrease/kill immediate + unilateral; increase gated (asymmetry intentional). Matches PROJECT.md §Safety.

---

## Privacy Classes & Tenant Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Tiered classes, private-by-default for code/prompts/sessions | team_shareable/team_private/never_leaves_local; code+prompts+sessions stay local unless promoted; only derived metadata + decision/outcome cross to Postgres; tenant = team | ✓ |
| Single team-scope, all team-visible | One boundary, everything team-visible | |
| You decide | — | |

**User's choice:** Tiered classes, private-by-default (recommended)
**Notes:** Rides BOS2 D-04/D-05 SQLite→Postgres boundary. Identity resolution → BOS12. No multi-tenant SaaS in v0.2.

---

## Anti-Surveillance Aggregation Rule

| Option | Description | Selected |
|--------|-------------|----------|
| Min-aggregation floor (k≥N) + no cross-individual reports; self-view allowed | Metric never reported for <N contributors; no ranking; self-view ok; stored≠cross-reported | ✓ |
| Aggregate-only, no individual data retained | Strictly aggregate; conflicts with BOS4 actor field + self-view | |
| You decide | — | |

**User's choice:** Min-aggregation floor + no cross-individual reports; self-view allowed (recommended)
**Notes:** Reconciled with BOS4 ledger actor field (stored for audit/training, never ranked). Value of N = open question.

---

## Guardrail Dashboards + Scope Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Define each guardrail + trip condition now; BOS6 owns dashboard, refs BOS5 metrics | 6 guardrails (fatigue, fairness, escaped defects, incidents, autonomy creep, reward hacking) each w/ measure + trip condition; BOS6=dashboard, BOS5=metrics, BOS15=gates | ✓ |
| Envelope + list now, thresholds deferred | Name 6 + dashboard exists; defer measurement/thresholds | |
| You decide | — | |

**User's choice:** Define each guardrail + trip condition now (recommended)
**Notes:** Explicit scope boundary BOS6/BOS5/BOS15 stated in spec.

---

## Claude's Discretion

- Governance-spec doc structure/format.
- Band-transition table wording.
- Data-class → handling matrix layout.
- Guardrail trip-condition phrasing (metric owned by BOS5).

## Deferred Ideas

- Value of N for the aggregation floor — open question.
- Data retention/deletion policy — flagged, undecided.
- RBAC: who flips kill-switch / changes bands — flagged, likely BOS7/later.
- Reward/guardrail metric definitions → BOS5.
- Offline-eval gate mechanics → BOS15.
- Event data classes detail → BOS3.
- Cross-source identity resolution → BOS12.
