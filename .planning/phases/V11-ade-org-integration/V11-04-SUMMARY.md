---
phase: V11-ade-org-integration
plan: 04
subsystem: ui
tags: [solidjs, kanban, board-derivation, roster, pure-functions, fixtures]

# Dependency graph
requires:
  - phase: V11-01
    provides: SessionTreeNode/RunData types + golden fixtures (node-root/node-child/audit-report)
  - phase: V11-03
    provides: panel stub contract (props:{data:RunData|null; onCardSelect?; selectedCardId?}) + OrgViewShell host
provides:
  - boardDerive.ts — deriveColumn/deriveRisk/cardsFromRunData pure helpers (verified harness algorithm)
  - BoardPanel — 6-column Kanban with risk-tinted cards, budget micro-bar, click-to-select
  - RosterPanel — role rows with role-color dots + status badges
affects: [V11-07 (BlockedPanel reuses derivation), DiffPanel (receives selectedCardId from Board)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Board derivation extracted into pure boardDerive.ts, fixture-tested separately from render (column/risk/cards)"
    - "Columns render harness keys (data-col) with UI-SPEC display labels (Planned→Todo, InProgress→In Progress)"
    - "Card risk tint via layered linear-gradient over --bg-2; role pill via color-mix 20%"

key-files:
  created:
    - apps/voss-app/src/org/boardDerive.ts
    - apps/voss-app/src/org/__tests__/boardPanel.test.tsx
  modified:
    - apps/voss-app/src/org/panels/BoardPanel.tsx
    - apps/voss-app/src/org/panels/RosterPanel.tsx

key-decisions:
  - "Card per non-root node (parent_run_id !== null); root excluded"
  - "Card title = node.scope ?? node.id (no title field in schema)"
  - "Roster rows = audit.team_config.roster_ids ∪ distinct node roles, deduped; status from node terminal_state (done→done, no terminal→active, else idle)"
  - "Roster mono secondary shows role id (no per-role model in data)"

patterns-established:
  - "deriveColumn: last board.transition.to, then terminal override (done→Done, killed/timeout→Blocked), default Backlog"
  - "deriveRisk: first em.ticket.risk_tier, default med"

requirements-completed: [VADE-01, VADE-02]

# Metrics
duration: 14min
completed: 2026-06-07
---

# Phase V11 Plan 04: Roster + Board Panels Summary

**6-column Kanban board with fixture-verified column/risk derivation (last board.transition + terminal override; first em.ticket risk) + a team Roster panel — first structural org panels.**

## Performance

- **Duration:** ~14 min
- **Completed:** 2026-06-07
- **Tasks:** 3 (all auto; Task 1 TDD)
- **Files created:** 2 (boardDerive, test); **modified:** 2 (BoardPanel, RosterPanel)

## Accomplishments
- `boardDerive.ts` — `deriveColumn`/`deriveRisk` mirror the verified harness `_derive_column`/`_derive_risk`; `cardsFromRunData` (one card per non-root node, null-tolerant).
- `BoardPanel` — horizontal 6 columns (harness keys, UI display labels, `--org-col-*` colors, `(N)` counts), cards with id/title/role-pill/risk-badge/budget-bar (green<70/amber 70-90/red>90), risk tint, selected `--focus` ring, click → `onCardSelect`. ARIA list/listitem.
- `RosterPanel` — role rows (7px role-color dot, uppercase role label, mono secondary, status badge), ROSTER section header, empty-state copy.

## Files Created/Modified
- `src/org/boardDerive.ts` — pure derivation helpers + BoardCard interface
- `src/org/__tests__/boardPanel.test.tsx` — 5 derivation + 4 render tests
- `src/org/panels/BoardPanel.tsx` — filled from stub
- `src/org/panels/RosterPanel.tsx` — filled from stub

## Decisions Made
See `key-decisions` frontmatter. All within plan scope; derivation matches RESEARCH verified algorithm exactly.

## Deviations from Plan
None - plan executed as written. No new dependencies.

## Issues Encountered
None.

## Verification
- `npx vitest run` → **59 files, 585 tests passed** (boardPanel.test.tsx: 9 — column/risk/cards derivation incl. killed/timeout→Blocked override, 6-column render, card-in-derived-column, click→onCardSelect, null empty-state)
- `npx tsc --noEmit` → **exit 0**
- "No roster data" in RosterPanel; "Backlog" in BoardPanel

## Next Phase Readiness
- Board card selection (`onCardSelect`) flows to the shell's `selectedCardId` → DiffPanel (already wired in V11-03).
- `boardDerive` helpers available for BlockedPanel (Plan 07) blocked-column derivation.

---
*Phase: V11-ade-org-integration*
*Completed: 2026-06-07*
