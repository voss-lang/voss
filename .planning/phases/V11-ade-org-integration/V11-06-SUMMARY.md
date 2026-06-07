---
phase: V11-ade-org-integration
plan: 06
subsystem: ui
tags: [solidjs, audit, budget, scope, leak6, unsupported-claims, collapsible]

# Dependency graph
requires:
  - phase: V11-01
    provides: AuditReport/SessionTreeNode types + audit-report.json fixture
  - phase: V11-03
    provides: panel stub contract + OrgViewShell host
provides:
  - AuditPanel — audit sections + claims-vs-evidence + ⚑ unsupported flag + RESIDUAL RISK (leak6)
  - BudgetPanel — collapsible Per Root / Per Card / Per Agent with consumption bars + over-budget tint
  - ScopePanel — collapsible Per Role / Per Card scope tags + (inert) out-of-scope flag
affects: [V11-07, V11-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Collapsible section component (createSignal open) reused for Budget + Scope"
    - "Unsupported-claim driven by audit.unsupported_claims Set → ⚑ + tinted row + aria-label"
    - "Per-agent budget = envelopes summed by node.role"

key-files:
  created:
    - apps/voss-app/src/org/__tests__/auditPanel.test.tsx
  modified:
    - apps/voss-app/src/org/panels/AuditPanel.tsx
    - apps/voss-app/src/org/panels/BudgetPanel.tsx
    - apps/voss-app/src/org/panels/ScopePanel.tsx

key-decisions:
  - "Claims list derived from snapshot.cards (one row per card); evidence = unsupported if node_id in unsupported_claims else supported"
  - "Diffs/tests_evals NOT rendered (Pitfall 4 — always in sections_missing)"
  - "Scope shown as a single pill from node.scope string (no glob-splitting); out-of-scope flag inert (no persisted source)"
  - "Budget bar logic inlined (grid BudgetBar expects different prop shape)"

patterns-established:
  - "BudgetSection/ScopeSection: header (▾/▸ toggle, uppercase) + For rows, default expanded"

requirements-completed: [VADE-04, VADE-06, VADE-07]

# Metrics
duration: 13min
completed: 2026-06-07
---

# Phase V11 Plan 06: Audit + Budget + Scope Panels Summary

**Audit panel with claims-vs-evidence and the ⚑ unsupported-EM-claim flag + leak6 residual-risk, plus collapsible per-root/card/agent Budget and per-role/card Scope panels.**

## Performance

- **Duration:** ~13 min
- **Completed:** 2026-06-07
- **Tasks:** 3 (all auto)
- **Files created:** 1 (test); **modified:** 3 (Audit/Budget/Scope panels)

## Accomplishments
- `AuditPanel` — IDEA/PRINCIPLES/TEAM/SNAPSHOT/CLAIMS/RESIDUAL RISK sections; claims rows with supported/unsupported badge; unsupported nodes (in `unsupported_claims`) get a `⚑` (`--unsupported-flag`, `aria-label="Unsupported claim"`) + tinted row; leak6 status/evidence/mitigation rendered. Diffs/tests_evals omitted (Pitfall 4).
- `BudgetPanel` — collapsible Per Root / Per Card / Per Agent; each row name + allocation + 4px consumption bar (green<70/amber/red>90) + pct; over-budget (spent≥limit) tinted; section totals.
- `ScopePanel` — collapsible Per Role / Per Card; scope-string pill; data-driven out-of-scope ⚑ (currently inert per substrate).

## Files Created/Modified
- `src/org/__tests__/auditPanel.test.tsx` — 4 tests (sections, ⚑ flag, residual, null state)
- `src/org/panels/AuditPanel.tsx` — filled from stub
- `src/org/panels/BudgetPanel.tsx` — filled from stub
- `src/org/panels/ScopePanel.tsx` — filled from stub

## Decisions Made
See `key-decisions` frontmatter. All within plan scope.

## Deviations from Plan
None - plan executed as written. No new dependencies.

## Issues Encountered
None.

## Verification
- `npx vitest run` → **61 files, 596 tests passed** (auditPanel.test.tsx: 4 — summary sections, ⚑ unsupported flag + node id, RESIDUAL RISK/leak6, null empty-state)
- `./node_modules/.bin/tsc --noEmit` → **exit 0**
- "RESIDUAL RISK" in AuditPanel; "Per Root"+"Per Agent" in BudgetPanel; "Per Role"+"No scope data" in ScopePanel

## Next Phase Readiness
- All read-only data panels (Roster/Board/Tree/Verdict/Audit/Budget/Scope) now filled. Remaining: Blocked decision flow (Plan 07) + Diff/Replay (Plan 08).

---
*Phase: V11-ade-org-integration*
*Completed: 2026-06-07*
