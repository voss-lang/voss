---
phase: V24-ade-product-revamp-swarm-observability
plan: 04
subsystem: ui
tags: [solidjs, composer, dialog, run-intake, vitest, tdd, a11y]

# Dependency graph
requires:
  - phase: V24-03
    provides: TopChrome (currentSafetyMode + onOpenComposer props) + PortalRail (onOpenComposer)
  - phase: V14
    provides: runIntake.ts (assembleRunSpec, validateAutoStart, RunMode/RunTarget/RunIntakeState)
provides:
  - VossComposer modal "Ask Voss to…" intake reachable globally via ⌘K + portal-rail ask trigger
  - Progressive disclosure — ask + Read-only-default safety only; scope/agent/team/budget/context behind Advanced
  - safety label → RunMode mapping (Read only→Plan, Can edit→Edit, Autopilot→Auto) reusing assembleRunSpec + validateAutoStart
  - App: composerOpen signal + ⌘K toggle + currentSafetyMode chip source fed from created Task mode
affects: [V24-05 (mission control surfaces consume created Tasks), V24-06 (Swarm Map), future RunCommandBar retirement]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Global modal mounted at App root as a sibling of other modals; open state is an App signal"
    - "Progressive-disclosure intake: minimal default view + Advanced <Show> panel"
    - "Self-contained Tab focus-trap inside the dialog (no App-level inert plumbing)"
    - "Humane label → internal enum mapping at the UI boundary; assembler/identifiers unchanged"

key-files:
  created:
    - apps/voss-app/src/composer/VossComposer.tsx
    - apps/voss-app/src/composer/composer.css
    - apps/voss-app/src/composer/__tests__/VossComposer.test.tsx
  modified:
    - apps/voss-app/src/App.tsx

key-decisions:
  - "onCreated is minimal in App — records the new Task's RunMode for the TopChrome chip and closes; it does NOT itself dispatch a run. RunCommandBar remains the always-on runner this wave (plan's App wiring only asks to feed the chip)."
  - "Pitfall-7 'inert background' satisfied via a self-contained Tab focus-trap inside the dialog rather than an App-level inert attribute — matches existing modal conventions (AgentLaunchModal/NewWorkspacePicker don't inert siblings)."
  - "Native <dialog open> gated by <Show when={open}> (not showModal — jsdom-safe, controlled by prop)."
  - "Advanced 'agent target' maps to RunIntakeState.target (native='Voss run' / terminal='Terminal agent'); 'attach context' has no RunIntakeState slot — captured locally, not dispatched (included to honor 'attached context hidden until Advanced')."

patterns-established:
  - "Composer assembles + gates + emits onCreated(spec); host decides dispatch (decoupled intake)"
  - "⌘K global keydown added to onAppKey after the ⌘⇧O block; metaKey-only, guarded against ⌘1-9 / chord collisions"

requirements-completed: [VADE2-04]

# Metrics
duration: 6min
completed: 2026-06-15
---

# Phase V24-04: "Ask Voss to…" Composer Summary

**Global ⌘K modal `VossComposer` — progressive run intake that shows only the ask field + a Read-only-default safety control, hides scope/agent/team/budget/context behind Advanced, and reuses `runIntake.ts` (`assembleRunSpec` + `validateAutoStart`) with a humane safety→RunMode mapping.**

## Performance

- **Duration:** ~6 min
- **Tasks:** 2 (1 TDD test + 1 build/wire)
- **Files created:** 3 — **modified:** 1

## Accomplishments
- `VossComposer.tsx`: `<dialog aria-modal>` with title "❯ Ask Voss to…", ask textarea (aria-required, mono 13px), `Safety mode` select defaulting **"Read only"** (D-04), `Advanced ▸/▾` toggle (aria-expanded + aria-controls), `Create Task` CTA (disabled when ask empty). Advanced panel (`<Show>`): scope / agent target / team / budget / attach-context.
- Run-intake reuse: Create builds a `RunIntakeState` (safety→RunMode: Read only→Plan, Can edit→Edit, Autopilot→Auto), runs `validateAutoStart` (Autopilot blocked inline until budget+scope), then `assembleRunSpec` → `onCreated(spec)`.
- Focus/keyboard: focus lands on the ask textarea on open; Escape closes; ⌘Enter creates; bare Enter inserts a newline; a Tab focus-trap keeps focus inside the dialog (Pitfall 7).
- `composer.css`: centered modal (min 560 / max 720), `var(--bg-2)` panel, `var(--border-bright)`, rgba(0,0,0,0.4) backdrop dim; entrance animation wrapped in the A8 reduced-motion double-guard. Tokens only (no raw hex).
- App wiring: `composerOpen` signal; global **⌘K** toggle in `onAppKey`; `onOpenComposer` passed to `<TopChrome>` and `<PortalRail>`; `<VossComposer>` mounted at root; `currentSafetyMode` chip fed from the created Task's mode via `onCreated`.

## Task Commits

Not committed — per the repo's git-safety policy (no git writes without explicit request). All changes are in the working tree on branch `dev`.

1. **Task 1: VossComposer default-state test (RED)** — `VossComposer.test.tsx` (test)
2. **Task 2: Build VossComposer + wire App** — VossComposer/composer.css/App.tsx (feat)

## Files Created/Modified
- `src/composer/VossComposer.tsx` — global modal composer; assembleRunSpec reuse; safety→RunMode; Autopilot gate; focus-trap
- `src/composer/composer.css` — token-only modal styling; A8-guarded entrance
- `src/composer/__tests__/VossComposer.test.tsx` — default-state + Read-only-default + Advanced-disclosure + closed-state assertions
- `src/App.tsx` — composerOpen signal, ⌘K toggle, onOpenComposer→TopChrome/PortalRail, mounted composer, currentSafetyMode chip source

## Decisions Made
- **Minimal onCreated (chip-only):** the plan's App wiring asks only to "feed the created Task's safety mode into the TopChrome chip." The composer emits a fully-assembled `RunSpec`; App records its mode and closes. End-to-end harness dispatch stays with the always-on `RunCommandBar` this wave — avoids duplicating/diverging the terminal/native start path. Full RunCommandBar retirement + composer dispatch is a later wave.
- **Focus-trap over App-level inert:** implemented a Tab trap inside the dialog (self-contained), matching existing modal conventions that don't inert siblings. Satisfies the Pitfall-7 intent (Tab can't reach a focused xterm pane behind the overlay).
- **Field/state mapping:** scope→scope, agent target→`RunTarget`, team→team, budget→budget. `attach context` has no `RunIntakeState` slot — rendered (so it's "hidden until Advanced" per VADE2-04) but not dispatched.

## Deviations from Plan
Plan executed as written, with the two faithful clarifications above (minimal onCreated dispatch; focus-trap instead of literal `inert` attribute). No must_have requires end-to-end dispatch or a literal inert attribute; both intents (chip source, Tab containment) are met.

## Issues Encountered
None — test RED→GREEN on first build; tsc clean; full suite green.

## Verification
- `npm test -- VossComposer` → **5 passed**.
- `npx tsc --noEmit` → **0 errors** (composer/* + App.tsx clean).
- `grep assembleRunSpec src/composer/VossComposer.tsx` → **REUSES_INTAKE**.
- `npm test` (full suite) → **844 passed | 5 skipped, 0 failed** (92 files; +5 from V24-03's 839).
- No raw hex in composer files (rgba backdrop only); locked copy present ("Ask Voss to…" Unicode ellipsis, "Create Task", Read only/Can edit/Autopilot).

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- VADE2-04 acceptance met: global composer reachable from ⌘K + rail; default view = ask + Read-only safety only; scope/agent/team/budget/context behind Advanced; no Plan/Edit/Auto/runId by default.
- **Follow-ups:** wire `onCreated` to actually start the run via the existing terminal/native path (retire `RunCommandBar`); add an `RunIntakeState` slot if attach-context should be dispatched.

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15*
