---
phase: V24-ade-product-revamp-swarm-observability
plan: 05
subsystem: ui
tags: [solidjs, mission-control, board, status-grouping, deep-link, vitest, tdd]

# Dependency graph
requires:
  - phase: V24-02
    provides: PortalShell canvas-swap host + placeholder Match arms for overview/tasks/agents
  - phase: V14
    provides: boardDerive (cardsFromRunData/deriveColumn), org/selection, attentionQueue, bridge, adoptionRegistry, orgStore
provides:
  - OverviewSurface / TasksSurface / AgentsSurface mission-control surfaces mounted in PortalShell
  - Status-grouped Task list (ACTIVE/BLOCKED/REVIEWING/DONE/ADOPTED/TERMINAL AGENT) from cardsFromRunData + groupForCard
  - Row deep-link to grid (bridge paneId) or review drawer via org/selection
  - Blocked-row inline attention action row (no modal), sourced from attentionQueue
  - Agent roster grouped by role with role-colored dot + cost
affects: [V24-06 (Swarm Map shares the same data source + selection deep-link)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Prop-less surfaces read module-level orgStore/selection/attention signals (no prop threading)"
    - "Display-layer status group taxonomy over deriveColumn keys (code keys unchanged, D-09)"
    - "Shared TaskRow/GROUPS/groupCards exported from the hub surface and reused by the roll-up"
    - "Honest-signal grouping: TERMINAL AGENT = bridge pane-bound cards, ADOPTED = adoption registry; no fabricated columns"

key-files:
  created:
    - apps/voss-app/src/surfaces/tasks/TasksSurface.tsx
    - apps/voss-app/src/surfaces/overview/OverviewSurface.tsx
    - apps/voss-app/src/surfaces/agents/AgentsSurface.tsx
    - apps/voss-app/src/surfaces/surfaces.css
    - apps/voss-app/src/surfaces/tasks/__tests__/TasksSurface.test.tsx
    - apps/voss-app/src/__tests__/portalDeepLink.test.tsx
  modified:
    - apps/voss-app/src/portal/PortalShell.tsx

key-decisions:
  - "BoardCard has no paneId field — the row deep link resolves it via paneIdForCard(card.id) (bridge cardToPane). pane-bound → requestOpenInGrid; else → requestOpenInReview(card.id)."
  - "TERMINAL AGENT and ADOPTED groups are derived from real registries (bridge paneId + adoptionByPaneId), not from deriveColumn — they populate only when that data exists; fixtures exercise the four column-derived groups."
  - "AgentsSurface omits model/elapsed — SessionTreeNode carries neither; showing them would be a fabricated column (honest-signal). Shows role-colored dot + name + cost."
  - "Surfaces are prop-less and read the shared orgStore signals; they do NOT trigger their own load this wave (existing paths populate runData; otherwise the empty state shows)."

patterns-established:
  - "Mission-control surface shell: 40px header + grouped 32px rows + reused .org-spinner/.org-error-state + locked empty copy"
  - "Self-contained TaskRow with its own inline-attention expand state (reusable across surfaces)"

requirements-completed: [VADE2-05]

# Metrics
duration: 12min
completed: 2026-06-15
---

# Phase V24-05: Mission-Control Surfaces Summary

**Overview / Tasks / Agents surfaces present managed work as a Linear-like status system — `cardsFromRunData` + `deriveColumn` grouped into ACTIVE/BLOCKED/REVIEWING/DONE/ADOPTED/TERMINAL AGENT, rows deep-link to grid/review via `org/selection`, and blocked rows expand an inline attention action (no modal).**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2 (1 TDD test + 1 build/wire)
- **Files created:** 6 — **modified:** 1

## Accomplishments
- `TasksSurface.tsx` (hub): `cards = cardsFromRunData(runData())` grouped by `groupForCard` into the six-group taxonomy; group headers use the `.cockpit-sect` ALL-CAPS Poppins pattern; zero-item groups hidden; locked empty state ("No active Tasks" / "Use ⌘K to ask Voss to start one."). Each row is a `<button aria-label="Open Task: …">` with status dot + focal Task name + role/cost metadata. Exports `GROUPS`/`groupCards`/`TaskRow` for reuse.
- Deep link: `paneIdForCard(card.id)` → `requestOpenInGrid(paneId)` when pane-bound, else `requestOpenInReview(card.id)`.
- Inline attention: a blocked row with a matching `attentionQueue()` item renders a `!` badge that expands a 44px inline action row (summary + "Review →") — not a modal.
- `OverviewSurface.tsx`: per-group count roll-up chips + ACTIVE/BLOCKED expanded (reuses `TaskRow`).
- `AgentsSurface.tsx`: roster grouped by role; role-colored `var(--role-*)` dot, focal agent name, cost (mono tabular-nums); deep-link rows; empty state "No agents running" / "Create a Task to deploy agents."
- `surfaces.css`: 40px header / 28px group header / 32px row / hover `--bg-2` / attention tint — tokens only.
- `PortalShell.tsx`: the overview/tasks/agents placeholder Match arms now mount the three real surfaces.

## Task Commits

Not committed — per the repo's git-safety policy (no git writes without explicit request). All changes are in the working tree on branch `dev`.

1. **Task 1: status-grouping + deep-link tests (RED)** — TasksSurface.test.tsx, portalDeepLink.test.tsx (test)
2. **Task 2: build surfaces + PortalShell wiring** — TasksSurface/OverviewSurface/AgentsSurface/surfaces.css/PortalShell.tsx (feat)

## Files Created/Modified
- `src/surfaces/tasks/TasksSurface.tsx` — status-grouped Task list + deep-link rows + inline attention; exports GROUPS/groupCards/TaskRow
- `src/surfaces/overview/OverviewSurface.tsx` — count roll-up + expanded ACTIVE/BLOCKED
- `src/surfaces/agents/AgentsSurface.tsx` — agent roster grouped by role
- `src/surfaces/surfaces.css` — token-only mission-control styling
- `src/surfaces/tasks/__tests__/TasksSurface.test.tsx` — fixture status-grouping + null-tolerant empty
- `src/__tests__/portalDeepLink.test.tsx` — row click → requestOpenInGrid (paneId) / requestOpenInReview (cardId)
- `src/portal/PortalShell.tsx` — mounts the three real surfaces

## Decisions Made
- **paneId resolution:** `BoardCard` carries no paneId; the deep link resolves it from the live id-bridge (`paneIdForCard`). This is also how TERMINAL AGENT/ADOPTED grouping is derived (pane-bound → terminal; pane in `adoptionByPaneId` → adopted), keeping every group an honest signal.
- **No fabricated agent columns:** model/elapsed are not on `SessionTreeNode`, so AgentsSurface shows only what exists (role/name/cost).
- **Prop-less, read-only surfaces:** they render the shared `orgStore` signals and don't own a load path this wave (existing OrgViewShell/cockpit populate `runData`; otherwise the empty state shows). Surface-driven load is a later concern.

## Deviations from Plan
Plan executed as written. Clarifications: the deep-link paneId comes from the bridge (BoardCard has no paneId field); ADOPTED/TERMINAL AGENT groups are real-registry-derived (populate when that data exists — fixtures exercise the four column-derived groups); agent model/elapsed omitted (not in the data shape). No must_have requires a paneId field, populated adopted/terminal fixtures, or model/elapsed.

## Issues Encountered
None — both test files RED→GREEN; tsc clean; full suite green.

## Verification
- `npm test -- TasksSurface` → **4 passed**; `npm test -- portalDeepLink` → **2 passed**.
- `npx tsc --noEmit` → **0 errors** (surfaces/* + PortalShell clean).
- `npm test` (full suite) → **850 passed | 5 skipped, 0 failed** (94 files; +6 from V24-04's 844).
- No raw hex in `src/surfaces/`; no user-facing "Runs" copy; key_links present (`cardsFromRunData`, `requestOpenInGrid/Review`); PortalShell mounts the three surfaces.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- VADE2-05 acceptance met: fixtures spanning each status group correctly; blocked attention action is actionable inline; row deep links open the corresponding pane/drawer.
- **V24-06 hook:** Swarm Map reuses the same `runData`/selection data source and the deep-link contract established here.
- **Follow-ups:** trigger a surface-driven `enumerateRuns`/`loadRun` when navigating to a surface with no loaded run; populate ADOPTED/TERMINAL groups end-to-end once adoption/terminal flows feed the bridge.

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15*
