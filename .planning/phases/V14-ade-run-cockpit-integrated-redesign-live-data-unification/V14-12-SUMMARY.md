---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 12
subsystem: ui
tags: [solid-js, feedback, a11y, reduced-motion, token-gate, mockup-parity, seatbelt, serde]

# Dependency graph
requires:
  - phase: V14-03
    provides: CardDrawer the comment affordance + curated drawer recomposition land in
  - phase: V14-04
    provides: RunCommandBar (restyled + re-mounted at App level here)
  - phase: V14-05
    provides: cockpit shell recomposed to mockup geometry here
provides:
  - VCKP-09 feedback write-path — feedbackWritePath.ts (native POST-message dispatch via injectable V13.1 client; snapshot cards disabled-with-reason) + drawer comment affordance
  - VCKP-10 a11y/dense pass — keyboard traversal (5 tabbable cockpit regions + focus rings), prefers-reduced-motion kill switch, A12 token-grep gate (scripts/token-grep-gate.mjs, negative-proofed), monospace numerics
  - Mockup visual parity (operator-driven scope expansion): chunks A/B/C recomposing shell chrome, Run Review cockpit, and Live Work chrome to the recovered .planning/sketches/V14-*.html contract
  - D-03 contract fix: RunCommandBar mounted at App level in BOTH modes; VCKP-12 contract fix: AdoptAgentModal wired (sidebar context-menu "Manage with Voss") + adoptionRegistry budget-stop
  - AgentEntry camelCase IPC fix (serde rename_all + contract test) unblocking project open/restore
affects: [structured-pane-rendering seed (.planning/notes/seed-structured-pane-rendering.md), V13.1 live-wiring wave]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Token gate as CI-style script: parse ignite cssVars + index.css definitions → grep cockpit/attention for foreign --xxx (declaration-position regex avoids BEM --modifier false positives)"
    - "CSS header comments must never contain `*/` mid-text (--bg-*/--fg-* glob prose terminated the block comment and broke the tailwind transform; vitest never runs that plugin)"
    - "IPC casing contract locked by Rust serde test (AgentEntry camelCase) — frontend interfaces are the source of truth"
    - "Mockups recovered from git (9363c2f^) → .planning/sketches/ are the canonical V14 visual contract; restyle work maps mockup hex → A12 tokens, 9/10px → 11px floor, off-scale spacing → 4px grid"

key-files:
  created:
    - apps/voss-app/src/org/feedbackWritePath.ts
    - apps/voss-app/src/org/__tests__/feedbackWritePath.test.ts
    - apps/voss-app/scripts/token-grep-gate.mjs
    - apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx
    - apps/voss-app/src/org/cockpit/TimelineRail.tsx
    - apps/voss-app/src/org/cockpit/CockpitSidebar.tsx
    - apps/voss-app/src/components/BoardSummaryStrip.tsx
    - apps/voss-app/src/pane/adoptionRegistry.ts
    - apps/voss-app/src/__tests__/adoptEntryWiring.test.tsx
    - .planning/sketches/V14-cockpit-mockup.html
    - .planning/sketches/V14-livework-mockup.html
    - .planning/sketches/V14-spawn-modals-mockup.html
  modified:
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx
    - apps/voss-app/src/org/cockpit/CardDrawer.tsx
    - apps/voss-app/src/org/cockpit/GateBar.tsx
    - apps/voss-app/src/org/cockpit/RunCommandBar.tsx
    - apps/voss-app/src/org/cockpit/cockpitStyles.css
    - apps/voss-app/src/org/cockpit/runCommandBar.css
    - apps/voss-app/src/org/panels/BoardPanel.tsx
    - apps/voss-app/src/org/attention/AttentionPanel.tsx
    - apps/voss-app/src/org/attention/attentionPanel.css
    - apps/voss-app/src/components/titlebar/Titlebar.tsx
    - apps/voss-app/src/components/StatusBar.tsx
    - apps/voss-app/src/components/sidebar/AgentSidebar.tsx
    - apps/voss-app/src/components/sidebar/AgentContextMenu.tsx
    - apps/voss-app/src/pane/PaneComponent.tsx
    - apps/voss-app/src/App.tsx
    - apps/voss-app/src/org/selection.ts
    - crates/voss-app-core/src/agent_registry.rs

key-decisions:
  - "Operator: V14 plans built behavior-correct but not the approved mockup look — mockups recovered from git 9363c2f^ became the canonical visual contract; parity delivered as 3 subagent chunks (A shell / B Run Review / C Live Work) inside this plan's close-out"
  - "Reject stays disabled-with-reason in the drawer (decisionActions one-write-path: only voss audit --approve exists)"
  - "Honest-data rule for parity work: every mockup element without a real signal skipped + reported (no $ on unitless envelopes, no acceptance criteria until the harness persists them, no fabricated streaming/blocked states, no fake budget %)"
  - "AdoptAgentModal entry = sidebar agent context menu; adoption budget-stop reads adoptionRegistry per budget_update (adoption happens post-spawn, can't be frozen into transport opts)"

patterns-established:
  - "Visual-parity chunking: subagent per surface with the mockup as read-first contract + hard constraint block (tokens/type/spacing/copy/honesty) + full-suite gates"

requirements-completed: [VCKP-09, VCKP-10]

# Metrics
duration: ~3h (incl. operator-driven parity scope expansion)
completed: 2026-06-09
---

# Phase V14 Plan 12: Feedback Write-Path + A11y Pass + Phase-Final Verification Summary

**VCKP-09 native feedback dispatch with disabled-with-reason fallback, VCKP-10 keyboard/reduced-motion/token-gate/mono pass, then the operator-driven mockup-parity recomposition (chunks A/B/C against the git-recovered V14 mockups) and the phase-final human verification — approved.**

## Performance

- **Duration:** ~3h wall (tasks 1-2 ~25min; checkpoint surfaced contract gaps → UI review → 3 parity chunks → 2 runtime fixes)
- **Started:** 2026-06-09T18:54:00Z
- **Completed:** 2026-06-09T21:26:31Z (operator approval)
- **Tasks:** 3 (2 auto + 1 blocking human-verify)
- **Files modified:** ~30 across app + 1 Rust crate

## Accomplishments
- `feedbackWritePath.ts`: `dispatchFollowUp` routes a comment to the bound NATIVE session via injectable `client.postMessage(sessionNodeId, …)` (resolveCard; registered-native-only — the snapshot fallback id is not a write target); snapshot/no-client → `FOLLOWUP_DISABLED_REASON`, nothing dispatched. Drawer affordance active/disabled accordingly. 7 tests.
- VCKP-10: 5 tabbable cockpit regions in DOM order w/ `:focus-visible` rings; `prefers-reduced-motion` kill covering `.org-view-shell *` + attention pulse + spinner; `token-grep-gate.mjs` (exit-1 negative-proofed, BEM-modifier-safe); budget/cost/confidence mono.
- **Checkpoint round 1 found the phase looked pre-V14** → root-caused: approved mockups deleted as throwaway with only decisions (not layout) captured; recovered all three from `9363c2f^` into `.planning/sketches/`; UI audit scored 14/24 with 11 priority fixes (all applied); then 3 parity chunks recomposed shell chrome, the Run Review cockpit (sidebar 252px | run header + rich board + horizontal timeline | drawer 372px | gate bars), and Live Work chrome (summary strip, pane role chrome, statusbar budget, attention polish).
- Contract gaps closed: D-03 RunCommandBar now App-level in BOTH modes (test: one bar across the display swap); VCKP-12 adopt flow reachable ("Manage with Voss" context-menu) with adoptionRegistry-driven budget-stop.
- 2 runtime fixes the suite couldn't catch: CSS header comments containing `--bg-*/` terminated block comments early → tailwind transform failure (escaped; vitest doesn't run the plugin); Rust `AgentEntry` snake_case IPC → undefined fields → `proc.toLowerCase` crash killing project open/restore (serde `rename_all = "camelCase"` + contract test; latent until a registry row existed at boot).

## Task Commits

1. **Task 1 (TDD): feedback write-path** — `b100815` (test RED) → `9c1e5f4` (feat GREEN)
2. **Task 2: a11y/token/reduced-motion** — `d224928` (watcher) + `6b11112` + `4908202`
3. **Task 3 checkpoint remediation:** gaps `ad08779`/`fbe9821` · UI-review fixes `4c27e85`/`f0fe889` · mockup recovery `f5242c1` · chunk A `5a1370e` · chunk B `a257eaf`/`226dd7a`/`2dbe0f2` · chunk C `c933722`→`38ad218` · css comment fix `edcc6b8` · AgentEntry casing `7121162`

## Decisions Made
See frontmatter. Notable: the parity work was executed inside this plan's checkpoint loop (operator chose incremental subagent chunks over a new GSD phase).

## Deviations from Plan

### Auto-fixed / operator-directed additions

**1. [Rule 4 → operator-approved] Mockup-parity recomposition (chunks A/B/C)**
- **Found during:** Task 3 human-verify — "looks nothing like the UI design/contract we agreed upon."
- **Issue:** V14 plans encoded decisions (D-01..13) but not the mockups' composition; mockups had been deleted.
- **Fix:** Recovered mockups from git; UI audit (V14-UI-REVIEW.md, 14/24); 11 priority fixes; 3 parity chunks via subagents with token/type/spacing/copy/honesty constraints.
- **Verification:** 736/736 suite, tsc, token gate green after each chunk; operator approved in-app.

**2. [Rule 1 - Bug] CSS comment `*/` early-termination broke the tailwind transform** — fixed `edcc6b8`; app-level failure invisible to vitest.

**3. [Rule 1 - Bug] AgentEntry IPC casing crash on project open/restore** — fixed `7121162` + Rust contract test; diagnosed via webview console + Playwright repro with stubbed Tauri internals.

**Total deviations:** 1 operator-approved scope expansion + 2 runtime bugs fixed. **Impact:** the phase now matches the approved visual contract; two latent app-killers removed.

## Issues Encountered
- Concurrent auto-commit watcher captured most chunk work mid-flight (per project convention) — content verified via git log; canonical chunk messages added where the tree allowed.
- Chunk-C subagent died on session limit mid-investigation (no writes lost); respawned clean.

## User Setup Required

None.

## Verification
- `npx vitest run` — 736/736 (80 files); `npx tsc --noEmit` clean; `node scripts/token-grep-gate.mjs` OK (+ negative proof).
- `cargo test -p voss-app-core` — 143 incl. sandbox denial + AgentEntry camelCase contract.
- Human-verify checkpoint: **operator approved 2026-06-09** (Live Work + Run Review walked in the running Tauri app).

## Self-Check: PASSED

## Next Phase Readiness
- **V14 phase complete (13/13 plans).** Cockpit + Live Work match the recovered mockup contract on real data.
- Seed captured: `.planning/notes/seed-structured-pane-rendering.md` — Voss-native structured pane content (protocol-event rendering + inline permission gate), the one mockup element gated on the live SSE plane.
- VCKP-13b permission proxy + live `voss serve` wiring remain the post-V14/V13.1 frontier.

---
*Phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification*
*Completed: 2026-06-09*
