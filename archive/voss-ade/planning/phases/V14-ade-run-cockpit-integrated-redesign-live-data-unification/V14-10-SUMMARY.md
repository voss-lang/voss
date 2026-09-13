---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 10
subsystem: ui
tags: [solid-js, modal, adopt, id-bridge, budget, audit, tier-c]

# Dependency graph
requires:
  - phase: V14-02
    provides: registerTerminalCard Bridge-B card↔pane binding + resolveCard fallback convention
  - phase: V14-05
    provides: cockpit/attention surfaces the adopted card flows into
provides:
  - Pure forward-only adopt logic (src/org/adopt.ts) — bind card via registerTerminalCard, advisory budget+scope, partial_lineage audit node baselined at adoption-time spend, reviewRequired, tier C always
  - inferRole(cliBinary) / inferRisk({scope,budget}) editable D-12 defaults (executor/user · low/med/high)
  - AdoptAgentModal — "Let Voss manage this agent" plain-language D-10 modal (Add it to / As the task / Limits / From now on, Voss will; CTA "Hand to Voss")
  - Disabled-with-reason fallback (shared ADOPT_UNAVAILABLE_REASON) when no harness adopt write-path exists
affects: [V14-11 managed-launch enforcement, V14-12, AttentionQueue adopted-agent copy]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Adopt is ALWAYS tier C (no retro-sandbox): result type literally pins tier:'C' so callers can't overstate control (D-11)"
    - "Forward-only cost: audit node stores costBaselineUsd = budgetByPaneId()[paneId].cost_usd at adoption; pre-adoption spend excluded by construction"
    - "Jargon-free copy enforced by test: grep-style DOM assertion over textContent+placeholder/aria-label/title against forbidden-term regexes"
    - "Pre-inferred-but-editable control: risk chip tracks inferRisk(scope,budget) reactively until riskTouched, then the user's pick wins (D-12)"

key-files:
  created:
    - apps/voss-app/src/org/adopt.ts
    - apps/voss-app/src/components/modal/AdoptAgentModal.tsx
    - apps/voss-app/src/components/modal/__tests__/adoptAgentModal.test.tsx
  modified: []

key-decisions:
  - "sessionNodeId = cardId for adopted terminal agents — no harness session exists; matches the resolveCard snapshot-fallback convention (Bridge B)"
  - "adoptAgent accepts optional role/risk overrides so modal edits flow through; defaults to inferRole/inferRisk (D-12 editable)"
  - "inferRole: known agent CLIs (claude/codex/gemini/opencode/aider) → executor, else → user (BoardPanel roleColor vocab); inferRisk: scope+budget → low, one → med, neither → high (harness risk_tier vocab)"
  - "ADOPT_UNAVAILABLE_REASON exported from adopt.ts so the logic and modal share one jargon-free disabled reason"
  - "Modal submit guards on harnessAdoptAvailable in the handler too (jsdom fires click on disabled buttons; belt-and-braces no-fake-affordance)"

patterns-established:
  - "Copy-rule testing: forbidden-jargon and no-per-tool-promise assertions live in the component test, so a future copy edit that reintroduces mechanics language fails CI"

requirements-completed: [VCKP-12]

# Metrics
duration: 8min
completed: 2026-06-09
---

# Phase V14 Plan 10: Adopt Running Agent ("Let Voss manage this agent") Summary

**Forward-only tier-C adopt flow: pure adopt.ts binds a running pane to a card via registerTerminalCard with advisory budget+scope, a partial_lineage audit node baselined at adoption-time spend, and review-before-done; AdoptAgentModal renders it in plain language with zero mechanics jargon and a disabled-with-reason fallback.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-09T18:15:30Z
- **Completed:** 2026-06-09T18:23:27Z
- **Tasks:** 2 (task 1 TDD)
- **Files modified:** 3 created

## Accomplishments
- `adoptAgent` (pure, no solid-js import): mints+binds a card via `registerTerminalCard(paneId)`, applies advisory budget+scope, returns `auditNode:{lineage:'partial_lineage', costBaselineUsd}` (pane spend at adoption — pre-adoption excluded), `reviewRequired:true`, `tier:'C'` always; `harnessAdoptAvailable:false` → `{disabled:true, reason}` with NOTHING bound.
- `inferRole`/`inferRisk` editable defaults (D-12) using repo vocab (executor/user; low/med/high).
- `AdoptAgentModal` copied from the AgentLaunchModal scaffold (backdrop/Esc/⌘↵/focus): D-10 sections "Add it to / As the task / Limits / From now on, Voss will", CTA "Hand to Voss"; outcomes-only copy (track spend · keep a record · warn/stop at the budget · review before done · "Tracking starts now"); role/risk pre-inferred, visible, editable.
- 22 tests: 9 adopt-logic + 13 modal, including grep-style DOM assertions that the rendered copy contains none of cage/Voss-native/PermissionGate/session-tree/partial lineage/pane and no "tool"/"block" per-tool-gating language.

## Task Commits

1. **Task 1: adopt.ts — pure adopt logic (TDD)** — `6742655` (test, RED) → `8260d2a` (feat, GREEN)
2. **Task 2: AdoptAgentModal — plain-language copy** — `4f36eba` (feat) — note: the workspace auto-commit watcher captured `AdoptAgentModal.tsx` + part of the test file mid-work as `c29bd3d`; `4f36eba` completes the same file set. Final tree content verified identical to authored files; suite re-run green post-commit.

## Files Created/Modified
- `apps/voss-app/src/org/adopt.ts` — pure forward-only adopt logic (bind/infer/partial_lineage/tier C/disabled-with-reason)
- `apps/voss-app/src/components/modal/AdoptAgentModal.tsx` — "Let Voss manage this agent" modal
- `apps/voss-app/src/components/modal/__tests__/adoptAgentModal.test.tsx` — 22 tests (logic + copy rules + wiring + disabled + keyboard)

## Decisions Made
See frontmatter key-decisions. Notables: `sessionNodeId` falls back to the minted `cardId` (no harness session for an adopted PTY agent — resolveCard convention); risk chip stays reactively inferred from scope/budget edits until explicitly touched.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Concurrent auto-commit watcher committed `AdoptAgentModal.tsx` mid-task as `c29bd3d` ("feat: implement AdoptAgentModal component...") before the task commit `4f36eba`. No content divergence — combined commits equal the authored files; verified via `git status` (clean) + full suite re-run (44/44) after.

## User Setup Required

None - no external service configuration required.

## Verification
- `npx vitest run src/components/modal/__tests__/adoptAgentModal.test.tsx` — 22/22 green.
- `npx vitest run src/components/modal` — 44/44 green (no AgentLaunchModal regression).
- `npx tsc --noEmit` — clean.
- `grep -c "from 'solid-js'" adopt.ts` → 0 (pure); tier C pinned in the result type.
- Forbidden jargon + per-tool-promise absence test-asserted in the DOM.

## Self-Check: PASSED

## Next Phase Readiness
- Adopt result shape (`AdoptResult`) ready for App/sidebar wiring (entry point that opens the modal per running pane) — not in this plan's files_modified; lands with cockpit/attention integration.
- V14-11 (managed launch enforcement) can contrast tier A/B at launch vs the always-C adopt established here.

---
*Phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification*
*Completed: 2026-06-09*
