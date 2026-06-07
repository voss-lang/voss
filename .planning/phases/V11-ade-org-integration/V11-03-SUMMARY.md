---
phase: V11-ade-org-integration
plan: 03
subsystem: ui
tags: [solidjs, tauri, css-tokens, view-shell, tablist, accessibility, voss-ignite]

# Dependency graph
requires:
  - phase: V11-01
    provides: RunData/CardSnapshot types + computeBoardAtStep reducer
  - phase: V11-02
    provides: orgStore signals + loadRun/enumerateRuns/refreshRun wrappers
provides:
  - OrgViewShell — header (← Grid / run-picker / ↻ Refresh) + 10-tab tablist + routed panel area + loading/error states + auto-load most-recent (D-04)
  - orgStyles.css — V11 org tokens (scoped to .org-view-shell) + .org-* component CSS + reduced-motion block
  - 10 panel stub files (Roster/Board/Tree/Audit/Verdict/Budget/Scope/Diff/Blocked/Replay) implementing the panel contract
  - App.tsx ⌘⇧O toggle via display:none (grid stays mounted) + OrgViewShell mount
  - StatusBar Org button (left region, active/inactive styling)
affects: [V11-04, V11-05, V11-06, V11-07, all panel-fill plans]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "View toggle via display:none on grid area + Show on OrgViewShell sibling — PTY panes survive (Pitfall 6)"
    - "Interface-first stubs: 10 panels created with the (props:{data:RunData|null}) contract so downstream plans fill them without touching the shell (zero shared-file conflict)"
    - "V11 tokens scoped to .org-view-shell, not global :root (PATTERNS Theme Note)"
    - "Panel routing: Show-per-tab passing data={runData()}; Board↔Diff linked via selectedCardId signal"

key-files:
  created:
    - apps/voss-app/src/org/OrgViewShell.tsx
    - apps/voss-app/src/org/orgStyles.css
    - apps/voss-app/src/org/panels/{Roster,Board,SessionTree,Audit,Verdict,Budget,Scope,Diff,Blocked,Replay}Panel.tsx
    - apps/voss-app/src/org/__tests__/orgView.test.tsx
  modified:
    - apps/voss-app/src/App.tsx
    - apps/voss-app/src/components/StatusBar.tsx

key-decisions:
  - "cliBinary passed as literal 'voss' (no single configured voss-path exists; matches is_voss_cli_binary, runtime PATH refinement deferred)"
  - "Run-picker status shows has_run_final ? 'final' : 'active'; mtime via new Date(secs*1000).toLocaleString()"
  - "View-toggle test uses a focused Harness reproducing App's display-toggle (full App render impractical) + real StatusBar/OrgViewShell"

patterns-established:
  - "Stub panel pattern: Show fallback empty-state copy, props.data consumed in when"
  - "OrgViewShell ARIA: role=region/tablist/tab/tabpanel/listbox/option per UI-SPEC"

requirements-completed: [VADE-02]

# Metrics
duration: 22min
completed: 2026-06-07
---

# Phase V11 Plan 03: Org/Run View Shell Summary

**⌘⇧O Org/Run view (display:none toggle keeps the grid mounted) hosting a 10-tab panel shell with run-picker, auto-load-most-recent, and view-level loading/error states — plus 10 interface-first panel stubs.**

## Performance

- **Duration:** ~22 min
- **Completed:** 2026-06-07
- **Tasks:** 3 (all auto)
- **Files created:** 13 (shell, CSS, 10 stubs, test); **modified:** 2 (App.tsx, StatusBar.tsx)

## Accomplishments
- `OrgViewShell` — 28px header (← Grid / `Run: <id12> ▾` picker / ↻ Refresh spin-while-loading), 36px 10-tab tablist (exact UI-SPEC labels), routed panel area, centered spinner + "Run not found" error state, `onMount` auto-loads newest run (D-04), run-picker closes on Escape/outside-click.
- `orgStyles.css` — all V11 tokens (`--org-col-*`, `--card-risk-*`, `--unsupported-flag`) scoped to `.org-view-shell`, `.org-*` component classes, `@keyframes spin`, reduced-motion override.
- 10 panel stubs, each typed against `RunData`, rendering its UI-SPEC empty-state copy (Board/Diff also accept `onCardSelect`/`selectedCardId`).
- App.tsx: `⌘⇧O` handler, grid area `display: orgViewOpen() ? 'none' : 'flex'` (grid stays mounted), `<OrgViewShell>` sibling.
- StatusBar: left-region `Org` button with active (`--focus`/orange) vs inactive (`--fg-3`) styling.

## Files Created/Modified
- `src/org/OrgViewShell.tsx` — shell + run-picker + tablist + routing + states
- `src/org/orgStyles.css` — V11 tokens + .org-* CSS + reduced-motion
- `src/org/panels/*.tsx` — 10 stubs
- `src/org/__tests__/orgView.test.tsx` — toggle/grid-persistence/tab-label tests
- `src/App.tsx` — signal + ⌘⇧O + display toggle + shell mount + StatusBar props
- `src/components/StatusBar.tsx` — Org button + 2 new props

## Decisions Made
See `key-decisions` frontmatter. All within plan scope.

## Deviations from Plan
None - plan executed as written. No new dependencies.

## Issues Encountered
- `createMemo` import was unused in OrgViewShell (noUnusedLocals) — removed.
- Stub `props.data` would be flagged unused if rendered statically — consumed via `Show when={props.data}` (sensible stub, downstream-fillable).

## Verification
- `npx vitest run` → **58 files, 576 tests passed** (orgView.test.tsx: 3 — grid persists with display:none on toggle, 10 exact tab labels, active/inactive Org button)
- `npx tsc --noEmit` → **exit 0**
- `--org-col-blocked` in orgStyles.css; 10 panel stubs; `role="tablist"` + "Run not found" in OrgViewShell; `OrgViewShell` wired in App.tsx

## Next Phase Readiness
- Shell + stubs ready: downstream plans fill each panel without touching the shell (interface-first contract).
- Board↔Diff card-selection plumbing (`selectedCardId`) already wired through the shell.
- Pitfall 6 mitigated and test-proven (grid node persists under display:none).

---
*Phase: V11-ade-org-integration*
*Completed: 2026-06-07*
