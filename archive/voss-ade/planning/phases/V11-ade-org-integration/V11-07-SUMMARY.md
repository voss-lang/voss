---
phase: V11-ade-org-integration
plan: 07
subsystem: ui
tags: [solidjs, dialog, decision-flow, cli-write-path, diff, verification, one-write-path]

# Dependency graph
requires:
  - phase: V11-02
    provides: buildDecisionCommand/runDecision/refreshRun + run_decision command
  - phase: V11-03
    provides: panel stubs + shell selectedCardId plumbing
  - phase: V11-04
    provides: boardDerive.deriveColumn (blocked = derived column "Blocked")
provides:
  - DecisionDialog — exact CLI command preview, run_decision shell, inline result, 1500ms auto-close+refresh (D-07/D-08)
  - BlockedPanel — blocked-card list + Approve (CLI) / disabled Reject+Unblock
  - DiffPanel — a_verification surface + explicit "No diff recorded" state (Pitfall 4)
  - orgStore currentCwd/currentCliBinary signals (decision context for panels)
affects: [V11-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One-write-path: panels only call run_decision; test asserts no other write command"
    - "Exact-command guarantee: dialog shows buildDecisionCommand; runDecision builds args from buildDecisionArgs (same source)"
    - "Decision context (cwd/cliBinary) stashed in orgStore on loadRun so panels need not thread it through the shell"

key-files:
  created:
    - apps/voss-app/src/org/DecisionDialog.tsx
    - apps/voss-app/src/org/__tests__/blockedPanel.test.tsx
  modified:
    - apps/voss-app/src/org/panels/BlockedPanel.tsx
    - apps/voss-app/src/org/panels/DiffPanel.tsx
    - apps/voss-app/src/org/orgStore.ts

key-decisions:
  - "DEVIATION: added currentCwd/currentCliBinary signals to orgStore (Plan 02 file) — BlockedPanel needs cwd/cliBinary for the CLI shell but the shell routes panels with data only; minimal additive change, no behavior change to existing exports"
  - "Approve is the sole enabled action (only non-interactive write path); Reject/Unblock disabled with explanatory title (no invented harness behavior)"
  - "DiffPanel renders 'No diff recorded' as verified reality (Pitfall 4: raw diffs never persist) + a_verification as the real surface"
  - "Blocked reason = terminal_state.final (string) else last board.transition.outcome else fallback"

patterns-established:
  - "DecisionDialog: requestAnimationFrame visible enter, Escape/outside-click dismiss, executing-disabled Confirm, auto-close+refresh on success"

requirements-completed: [VADE-08, VADE-09]

# Metrics
duration: 18min
completed: 2026-06-07
---

# Phase V11 Plan 07: Blocked Decision Flow + Diff Drilldown Summary

**Decision confirmation dialog that previews the EXACT `voss audit … --approve` command and shells it via run_decision (sole write path, auto-refresh on success) + a Blocked-card panel + a Diff drilldown exposing the a_verification surface with the verified no-diff state.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-06-07
- **Tasks:** 3 (all auto)
- **Files created:** 2 (DecisionDialog, test); **modified:** 3 (BlockedPanel, DiffPanel, orgStore)

## Accomplishments
- `DecisionDialog` — `role=dialog`/`aria-modal`, 480px `--bg-3`, header `{Action}: {cardId}`, "Command to run:" `<pre>` with the exact `buildDecisionCommand` output (border-left `--focus`), Confirm → `runDecision` → inline ✓ Done/✗ Failed, 1500ms `setTimeout` → `onDismiss` + `refreshRun` (D-08), Escape/×/outside-click dismiss. Never writes to disk.
- `BlockedPanel` — blocked cards (derived column "Blocked"), 72px rows (red id, 2-line reason), Approve (enabled → dialog) / Reject + Unblock (disabled, explanatory title).
- `DiffPanel` — card picker, explicit "No diff recorded for this card." (Pitfall 4), VERIFICATION section from `a_verification` (PASS/FAIL/SKIP badge, test path, notes), "Select a card…" no-selection state.
- `orgStore` — `currentCwd`/`currentCliBinary` signals (set on loadRun) so panels can shell decisions.

## Files Created/Modified
- `src/org/DecisionDialog.tsx` — confirmation dialog (D-07/D-08)
- `src/org/panels/BlockedPanel.tsx` — filled from stub
- `src/org/panels/DiffPanel.tsx` — filled from stub
- `src/org/orgStore.ts` — +currentCwd/currentCliBinary (additive)
- `src/org/__tests__/blockedPanel.test.tsx` — 5 tests

## Decisions Made
See `key-decisions`. The orgStore addition is the only out-of-plan-files change; documented as a deviation below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing wiring] orgStore decision-context signals**
- **Found during:** Task 2 (BlockedPanel) — DecisionDialog requires cwd + cliBinary, but the V11-03 shell routes panels with `data` only and cannot be modified in this plan.
- **Fix:** Added additive `currentCwd`/`currentCliBinary` signals to orgStore, set inside `loadRun` (defaults `''` / `'voss'`). No change to existing exports/behavior.
- **Files modified:** src/org/orgStore.ts
- **Verification:** tsc clean; blockedPanel test confirms run_decision is shelled with the stored context; full suite 601 green.

---

**Total deviations:** 1 auto-fixed (missing wiring). **Impact:** Necessary for the CLI write path to function; no scope creep.

## Issues Encountered
- Test invoke mock typed for 1 arg but called with 2 (tsc TS2554) — added `_args?: unknown` to the mock signature.

## Verification
- `npx vitest run` → **62 files, 601 tests passed** (blockedPanel.test.tsx: 5 — lists blocked card, Reject/Unblock disabled, Approve opens dialog with exact `audit … --approve` command, Confirm shells ONLY run_decision/load_run (one-write-path), null empty-state)
- `./node_modules/.bin/tsc --noEmit` → **exit 0**
- "Command to run:"+"buildDecisionCommand"+"refreshRun" in DecisionDialog; "No blocked cards" in BlockedPanel; "No diff recorded for this card"+"a_verification" in DiffPanel

## Next Phase Readiness
- All 10 panels now functional except Replay polish; Plan 08 covers Replay (computeBoardAtStep already exists from Plan 01).

---
*Phase: V11-ade-org-integration*
*Completed: 2026-06-07*
