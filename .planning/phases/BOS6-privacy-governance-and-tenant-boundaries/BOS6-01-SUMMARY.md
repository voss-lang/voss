---
phase: BOS6-privacy-governance-and-tenant-boundaries
plan: 01
subsystem: governance
tags: [bos, governance, privacy, autonomy, guardrails]

requires:
  - phase: BOS2-monorepo-and-stack-architecture
    provides: SQLite local store, shared Postgres projection, and local-to-shared boundary decisions
  - phase: BOS4-decision-ledger-schema
    provides: decision ledger actor/verdict fields and autonomy_band field
provides:
  - BOS6 governance and trust contract for BOS-GOV-01..04
  - Anti-surveillance reporting rule with minimum aggregation and no cross-ranking
  - Autonomy bands, kill-switch model, privacy tiers, tenant boundary, and guardrail dashboards
affects: [BOS9, BOS13, BOS14, BOS15, BOS7, BOS12]

tech-stack:
  added: []
  patterns: [docs-first governance contract, policy-only enforcement boundary]

key-files:
  created:
    - .planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-GOVERNANCE-SPEC.md
  modified: []

key-decisions:
  - "BOS6 is policy-only: it defines governance boundaries, not code, schemas, metrics, or eval mechanics."
  - "Team-level reporting is structurally constrained by minimum aggregation, no cross-ranking, self-view, and stored != cross-reported."
  - "Autonomy increases require BOS15 offline eval, guardrail check, and human approval; decreases and kills are immediate."
  - "Code, prompts, and agent-session transcripts default to never_leaves_local and stay local unless explicitly promoted."

patterns-established:
  - "Open questions are surfaced without invented values for N, retention/deletion, or kill-switch/autonomy RBAC."
  - "BOS6 references BOS3, BOS5, BOS12, and BOS15 as boundaries without defining their artifacts."

requirements-completed: [BOS-GOV-01, BOS-GOV-02, BOS-GOV-03, BOS-GOV-04]

duration: not captured
completed: 2026-06-20
---

# Phase BOS6 Plan 01: Privacy, Governance, and Tenant Boundaries Summary

**Governance policy contract for BOS trust, privacy, autonomy, tenant isolation, and guardrail dashboards.**

## Performance

- **Duration:** Not captured; this inline execution did not record a pre-work start timestamp.
- **Started:** Not captured.
- **Completed:** 2026-06-20T17:58:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `BOS6-GOVERNANCE-SPEC.md` with the four required governance pillars: trust/anti-surveillance, autonomy/override, privacy/tenant, and guardrails.
- Added `## Open Questions` with exactly the three undecided items from context: `N`, retention/deletion, and kill-switch/autonomy-band RBAC.
- Added cross-phase boundary citations for BOS3, BOS5, BOS12, and BOS15, plus downstream-consumer notes for BOS9, BOS13/BOS14, and BOS15.

## Task Commits

No git commits were created because project instructions prohibit git write actions unless Ben explicitly asks and confirms the exact action.

## Files Created/Modified

- `.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-GOVERNANCE-SPEC.md` - BOS6 governance and trust contract.
- `.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-01-SUMMARY.md` - Execution summary for this plan.

## Decisions Made

None - followed the locked BOS6 context and plan as specified.

## Deviations from Plan

No content deviations from the plan. Operational deviation: task and metadata commits were skipped to honor the repository instruction that no git write action may run without explicit confirmation.

**Total deviations:** 0 auto-fixed content deviations.
**Impact on plan:** None for the docs deliverable; git history closeout remains uncommitted by instruction.

## Issues Encountered

The home-level GSD execute-phase workflow path referenced by the skill was absent, so execution used the repo-local `.claude/get-shit-done/workflows/execute-plan.md`, the checked-in plan, and the locked BOS6 context.

## User Setup Required

None - no external service configuration required.

## Verification

Docs-only phase; no test command exists. Verification was performed by read-back and grep checks against the plan acceptance criteria:

- All four autonomy bands are present: `suggest_only`, `approve_required`, `auto_with_post_review`, `full_auto`.
- Dual kill-switch scope is present: global and per-surface.
- Gated-increase and immediate-decrease/kill asymmetry is present.
- All three privacy tiers are present: `team_shareable`, `team_private`, `never_leaves_local`.
- Code, prompts, and agent-session transcripts are private-by-default and local unless explicitly promoted.
- Minimum aggregation floor, self-view, no cross-ranking, and `stored != cross-reported` are present.
- BOS4 actor/verdict attribution is reconciled with anti-surveillance reporting.
- All six guardrails are present with trip/alert conditions.
- `## Open Questions` lists `N`, retention/deletion, and RBAC as undecided.
- BOS3, BOS5, BOS12, and BOS15 are cited as referenced boundaries, not defined by BOS6.

## Next Phase Readiness

BOS6 is ready for human review against `BOS6-CONTEXT.md`. Downstream BOS9, BOS13/BOS14, and BOS15 can consume the governance contract after review.

---
*Phase: BOS6-privacy-governance-and-tenant-boundaries*
*Completed: 2026-06-20*
