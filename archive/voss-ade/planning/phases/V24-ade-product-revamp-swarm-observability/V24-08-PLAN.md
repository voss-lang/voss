---
phase: V24-ade-product-revamp-swarm-observability
plan: 08
type: execute
wave: 5
depends_on: ["V24-04", "V24-06", "V24-07"]
files_modified:
  - apps/voss-app/src/__tests__/portalA11y.test.tsx
  - apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md
autonomous: false
requirements: [VADE2-08]
must_haves:
  truths:
    - "The full apps/voss-app vitest suite is green (existing grid/pane/terminal tests stay green as the L1 baseline)"
    - "The no-fake-signal guard, canvas-swap, composer, status-grouping, deep-link, live-edge, reduced-motion, and replay tests all pass"
    - "Portal/composer/swarm a11y (roles, focus rings, reduced-motion) is verified by automated checks"
    - "A documented manual terminal-first checklist is committed and passes (open/split/focus/run/custom-CLI/project-less/persist — all without Voss credentials)"
  artifacts:
    - path: "apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md"
      provides: "Documented L1 manual checklist + visual screenshot-review steps + Tauri pan/zoom smoke"
      contains: "terminal-first"
    - path: "apps/voss-app/src/__tests__/portalA11y.test.tsx"
      provides: "Automated a11y assertions: portal tablist roles, composer dialog, deep-link button aria-labels"
      contains: "role=\"tablist\""
  key_links:
    - from: "apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md"
      to: "L1 credibility constraint"
      via: "manual checklist is the named L1 acceptance gate"
      pattern: "without Voss"
---

<objective>
Prove the V24 revamp rather than assume it (VADE2-08). Run and lock the full
validation pass: the full vitest suite green (existing grid/pane/terminal tests
stay green as the terminal-first baseline), all V24 Wave-0 tests green (no-fake-
signal guard, canvas-swap, composer, status grouping, deep link, live edge,
reduced-motion CSS guard, replay), automated a11y assertions for portal/composer/
deep-link, and a committed, documented manual terminal-first checklist that the
operator runs and signs off (the named L1 acceptance gate — user chose manual
over automated regression). Visual screenshot review and the Tauri pan/zoom smoke
are documented as manual steps in the checklist.

Purpose: This is the gate before `/gsd-verify-work`. It is the single place that
confirms the two product-failure conditions are absent and L1 credibility is intact.

Output: `portalA11y.test.tsx` (automated a11y) and `V24-TERMINAL-FIRST-CHECKLIST.md`
(manual L1 + visual + Tauri smoke), plus a green full-suite run.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-VALIDATION.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md
@apps/voss-app/PRODUCT.md

<interfaces>
<!-- Verified from codebase 2026-06-14. -->
Test commands (VALIDATION.md §Test Infrastructure):
  Full suite:   cd apps/voss-app && npm test
  Module:       cd apps/voss-app && npm test -- <module>
  E2E:          cd apps/voss-app && npm run test:e2e

V24 Wave-0 test modules to confirm GREEN:
  swarmPortal, TopChrome, VossComposer, TasksSurface, portalDeepLink,
  swarmMapDerive, SwarmMap, swarmLive, swarmA11y, ReplayScrubber

a11y assertion analogs:
  apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx (roles + readFileSync source assertion)
  Portal roles authored in V24-02 PortalRail: role="tablist"/role="tab"/aria-selected; tabpanel on canvas.
  Composer dialog authored in V24-04: <dialog aria-modal="true" aria-label>.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author automated portal/composer/deep-link a11y test + run full regression</name>
  <files>apps/voss-app/src/__tests__/portalA11y.test.tsx</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx (roles + readFileSync assertion analog — copy structure)
    - apps/voss-app/src/portal/PortalRail.tsx (role="tablist"/"tab"/aria-selected to assert)
    - apps/voss-app/src/composer/VossComposer.tsx (dialog aria-modal/aria-label to assert)
    - apps/voss-app/src/surfaces/tasks/TasksSurface.tsx (row <button aria-label="Open Task: …"> to assert)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-VALIDATION.md (full per-requirement map + manual-only table)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Accessibility — the contract being verified)
  </read_first>
  <action>
    Write `portalA11y.test.tsx` using the standard tauri-mock harness asserting the cross-surface a11y contract:
    (a) PortalRail renders `role="tablist"` with `role="tab"` items carrying `aria-selected` and `aria-label`;
    (b) VossComposer renders a `<dialog aria-modal="true">` with an `aria-label` and an `aria-label="Safety mode"`
    control; (c) mission-control rows are `<button>` elements with `aria-label="Open Task: …"` (not anchors);
    (d) the reduced-motion contract holds via a `readFileSync` assertion that `swarmMap.css` has no `animation:`
    outside the reduced-motion guard (re-assert here as a phase-gate, complementary to swarmA11y).
    Then run the FULL vitest suite and confirm green, explicitly confirming the 10 V24 modules plus the existing
    grid/pane/terminal suites pass. If any pre-existing test is red, record it in the SUMMARY as out-of-scope
    baseline (do not fix unrelated failures) but every V24-authored test MUST be green.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- portalA11y 2>&1 | tail -12; npm test 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `portalA11y.test.tsx` asserts portal tablist/tab roles, composer dialog aria-modal+label, and `<button aria-label="Open Task: …">` rows.
    - The reduced-motion CSS source assertion re-passes at the phase gate.
    - `npm test` full suite is green; all 10 V24 modules (swarmPortal, TopChrome, VossComposer, TasksSurface, portalDeepLink, swarmMapDerive, SwarmMap, swarmLive, swarmA11y, ReplayScrubber) pass.
    - Existing grid/pane/terminal unit tests remain green (terminal-first baseline intact).
    - Any unrelated pre-existing red test is documented as out-of-scope, not silently masked.
  </acceptance_criteria>
  <done>Automated a11y + full regression green; all V24 tests pass; terminal baseline intact.</done>
</task>

<task type="auto">
  <name>Task 2: Write the documented manual terminal-first + visual + Tauri checklist</name>
  <files>apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md</files>
  <read_first>
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-VALIDATION.md (§Manual-Only Verifications — the three manual checks + instructions)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md (VADE2-08 acceptance — the L1 checklist contents)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Copywriting — vocabulary to screenshot-verify present/absent)
    - apps/voss-app/PRODUCT.md (the two product-failure conditions to verify absent)
  </read_first>
  <action>
    Create `apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md` documenting three checkable sections with explicit
    pass/fail boxes:
    1. "Terminal-First (L1) Checklist" — with NO project and NO Voss credentials: open the app, open a terminal,
       split (⌘D right / ⌘⇧D below), focus panes, run an arbitrary shell command, launch a custom CLI agent in a
       pane, use the app project-less, and confirm session persists across a reload. Each step is a checkbox; the
       header states all must pass without Voss credentials (the named L1 gate).
    2. "Product Vocabulary / No-Raw-Labels Visual Review" — screenshot-review the default chrome + each surface;
       confirm NO raw labels visible (no fanout/pipeline/swarm/watchers presets in chrome, no Plan/Edit/Auto
       toggle, no raw runId); confirm locked vocabulary present (Tasks, Swarm Map, Read only/Can edit/Autopilot,
       Create Task). Explicitly check the two product-failure conditions are absent.
    3. "Swarm Map Tauri Smoke (live build)" — on a real Tauri build with ≥1 run: open Swarm Map, drag-pan and
       zoom, confirm no native-scroll conflict; toggle reduced motion and confirm animations cease + the Event
       Trace list is shown; scrub a completed run and confirm graph state tracks the scrubber.
    Leave the sign-off line for the operator. This file is the durable record VADE2-08 requires.
  </action>
  <verify>
    <automated>cd apps/voss-app && test -f V24-TERMINAL-FIRST-CHECKLIST.md && grep -qi "without Voss" V24-TERMINAL-FIRST-CHECKLIST.md && grep -qi "reduced motion" V24-TERMINAL-FIRST-CHECKLIST.md && grep -q "Swarm Map" V24-TERMINAL-FIRST-CHECKLIST.md && echo CHECKLIST_OK</automated>
  </verify>
  <acceptance_criteria>
    - `V24-TERMINAL-FIRST-CHECKLIST.md` exists with the three sections (L1 terminal-first, vocabulary/visual review, Tauri swarm smoke).
    - The L1 section states all steps must pass without Voss credentials and covers open/split/focus/run/custom-CLI/project-less/persist.
    - The visual section enumerates the absent raw labels and present locked vocabulary, and the two product-failure conditions.
    - The Tauri section covers pan/zoom, reduced-motion fallback, and replay scrub.
    - The grep gate prints `CHECKLIST_OK`.
  </acceptance_criteria>
  <done>The manual L1 + visual + Tauri checklist is committed and ready for operator sign-off.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Operator runs the manual terminal-first + visual + Tauri checklist</name>
  <what-built>
    A documented manual checklist (`apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md`) plus a fully green
    automated suite. The portal shell, quiet chrome, composer, mission-control surfaces, and live/replay
    Swarm Map are all implemented and unit-verified. This checkpoint is the experiential L1 gate that
    cannot be automated (user's explicit choice).
  </what-built>
  <how-to-verify>
    1. Build/run the Tauri app: `cd apps/voss-app && npm run tauri dev` (or the project's run command).
    2. Open `apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md` and work through all three sections.
    3. Terminal-First: with no project + no Voss credentials, open a terminal, split (⌘D / ⌘⇧D), focus,
       run an arbitrary command, launch a custom CLI agent, use project-less, reload and confirm session persists.
    4. Visual: confirm the default chrome shows NO fanout/pipeline/swarm/watchers presets and NO Plan/Edit/Auto
       toggle; confirm "Tasks", "Swarm Map", and "Read only/Can edit/Autopilot" appear; confirm no raw runId is shown.
    5. Swarm Map (Tauri): open with ≥1 run; pan/zoom (no native-scroll conflict); toggle reduced motion and confirm
       animations cease + Event Trace list shows; scrub a completed run and confirm the graph tracks the scrubber.
    6. Tick each box in the checklist file and add the sign-off line.
  </how-to-verify>
  <resume-signal>Type "approved" (and commit the ticked checklist), or describe the failing steps to address.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator → live Tauri app | The manual checklist exercises real terminal/PTY + Swarm Map on the actual webview. |
| L1 credibility | The integrity boundary that the whole phase protects: the app must work as a terminal without Voss. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-08-T1 | Tampering (regression integrity) | full test suite | mitigate | The phase gate requires the full vitest suite green incl. existing grid/pane/terminal tests — catches V24 regressions to the terminal-first baseline before sign-off. |
| T-V24-08-V | Verification integrity | manual checklist | mitigate | L1 credibility is verified experientially by a human (no Voss credentials) — the user's chosen named gate; documented + signed off, not assumed. The no-fake-signal guard (V24-06) is re-confirmed green here. |
| T-V24-08-SC | Tampering | npm/pip/cargo installs | mitigate | No package installs in this plan. RESEARCH §Package Legitimacy Audit confirms zero new deps across V24 (d3-force optional, not added). Verified by `git diff package.json` showing no new dependencies. Legitimacy checkpoint N/A (no [ASSUMED]/[SUS] packages). |

No HIGH-severity threats. The supply-chain row is N/A by construction (no installs in V24).
</threat_model>

<verification>
- `npm test` full suite green, including all 10 V24 modules and existing grid/pane/terminal tests.
- `npm test -- portalA11y` GREEN.
- `V24-TERMINAL-FIRST-CHECKLIST.md` committed; operator sign-off captured.
- `git diff apps/voss-app/package.json` shows no new dependencies (zero supply-chain surface for V24).
</verification>

<success_criteria>
The manual terminal-first checklist passes and is documented; existing grid/pane/terminal unit tests stay green;
the no-fake-signal guard passes; deep-link, a11y/reduced-motion, visual, and focused Tauri/Rust/TS checks pass
(VADE2-08 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-08-SUMMARY.md` when done.
</output>
