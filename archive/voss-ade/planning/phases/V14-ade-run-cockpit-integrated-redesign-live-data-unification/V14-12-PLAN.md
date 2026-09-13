---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 12
type: execute
wave: 7
depends_on: ["V14-03", "V14-04", "V14-05"]
files_modified:
  - apps/voss-app/src/org/feedbackWritePath.ts
  - apps/voss-app/src/org/__tests__/feedbackWritePath.test.ts
  - apps/voss-app/src/org/cockpit/CardDrawer.tsx
  - apps/voss-app/src/org/cockpit/cockpitStyles.css
  - apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx
  - apps/voss-app/scripts/token-grep-gate.mjs
autonomous: false
requirements: [VCKP-09, VCKP-10]
must_haves:
  truths:
    - "Where a write path exists (native session, POST message via V13.1), a comment dispatches a follow-up to the correct sessionNodeId; where it does not (snapshot card), the affordance renders disabled-with-reason (no silent no-op)"
    - "Keyboard focus traverses Board -> detail drawer -> timeline in order"
    - "A grep/lint gate asserts no new theme tokens were introduced (A12 Ignite tokens only)"
    - "A reduced-motion media query disables cockpit animations (including the AttentionQueue pulse)"
    - "Budget/cost/confidence render in monospace numerics"
  artifacts:
    - path: "apps/voss-app/src/org/feedbackWritePath.ts"
      provides: "Feedback dispatch (native write path) + disabled-with-reason resolver"
    - path: "apps/voss-app/scripts/token-grep-gate.mjs"
      provides: "A12 token-only enforcement gate"
    - path: "apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx"
      provides: "VCKP-10 keyboard/reduced-motion test"
  key_links:
    - from: "apps/voss-app/src/org/feedbackWritePath.ts"
      to: "apps/voss-app/src/org/model/bridge.ts"
      via: "route follow-up to resolveCard's sessionNodeId"
      pattern: "sessionNodeId"
---

<objective>
VCKP-09 (GATED, best-effort) feedback write-path + VCKP-10 dense/a11y pass + the phase-final human-verify checkpoint. Inline comment routes a follow-up to the bound session where the protocol exposes a write path (native `POST message` via V13.1), else disabled-with-reason. Plus: keyboard nav Board→drawer→timeline, A12-token grep gate, reduced-motion disabling cockpit animation, monospace numerics. Ends with the human-verify checkpoint for Tauri-runtime visuals (macOS WebDriver blocked).

Purpose: Close G7 (no feedback loop) best-effort + the operational/a11y polish, then verify the cockpit live.
Output: feedback dispatcher + test, a11y test + token gate + reduced-motion CSS, human-verify checkpoint.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-SPEC.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md

<interfaces>
From apps/voss-app/src/org/decisionActions.ts:1-11: disabled-with-reason discipline (the only write path today: `voss audit <id> --approve`).
PROTOCOL §5: `POST /session/:id/message` exists for NATIVE sessions only — the only follow-up write candidate. Snapshot cards have no write path → disabled-with-reason.
From apps/voss-app/src/org/model/bridge.ts (plan 02): `resolveCard(maps, cardId).sessionNodeId` — the dispatch target.
From apps/voss-app/src/themes/bundled/voss-ignite.json: the A12 token set the grep gate validates against.
From apps/voss-app/src/org/panels/BoardPanel.tsx:76: `var(--font-mono)` monospace numerics pattern.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: feedbackWritePath.ts — native dispatch + disabled-with-reason</name>
  <files>apps/voss-app/src/org/feedbackWritePath.ts, apps/voss-app/src/org/__tests__/feedbackWritePath.test.ts, apps/voss-app/src/org/cockpit/CardDrawer.tsx</files>
  <behavior>
    - dispatchFollowUp({cardId, comment, client}) for a card with a native sessionNodeId calls the V13.1 client POST message with the correct sessionNodeId and the comment.
    - For a snapshot-only card (no native write path), dispatchFollowUp returns {disabled:true, reason:<string>} and dispatches nothing (no silent no-op).
    - The resolver uses resolveCard to get the sessionNodeId.
  </behavior>
  <read_first>
    - apps/voss-app/src/org/decisionActions.ts:1-11 (disabled-with-reason)
    - apps/voss-app/src/org/model/bridge.ts (resolveCard from plan 02)
    - .planning/PROTOCOL.md §5 (POST /session/:id/message — native only)
    - apps/voss-app/src/org/cockpit/CardDrawer.tsx (plan 03 — where the comment affordance renders)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md (Open Question 2 — default to disabled-with-reason)
  </read_first>
  <action>
    Create `feedbackWritePath.ts` (pure aside from the injected client): `dispatchFollowUp({cardId, comment, client, hasNativePath})` → when `hasNativePath` and `resolveCard(cardId).sessionNodeId` is a native id, call `client.postMessage(sessionNodeId, comment)` (V13.1, mock-injectable); else return `{disabled:true, reason:'...'}` (no dispatch). Wire an inline comment affordance into `CardDrawer.tsx` that renders disabled-with-reason for snapshot cards and active for native sessions. Write `feedbackWritePath.test.ts` covering: native dispatch hits the right sessionNodeId; snapshot card → disabled-with-reason, no dispatch.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/feedbackWritePath.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - Native card → `client.postMessage` called with the correct sessionNodeId + comment.
    - Snapshot card → disabled-with-reason, no dispatch (no silent no-op).
    - Drawer renders the affordance disabled for snapshot, active for native.
  </acceptance_criteria>
  <done>Feedback routes to the bound native session where possible; honest disabled fallback otherwise.</done>
</task>

<task type="auto">
  <name>Task 2: a11y/dense pass — keyboard nav, reduced-motion, token grep gate</name>
  <files>apps/voss-app/src/org/cockpit/cockpitStyles.css, apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx, apps/voss-app/scripts/token-grep-gate.mjs</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (plan 03 — focus order targets)
    - apps/voss-app/src/org/panels/BoardPanel.tsx:16-48,76 (A12 token usage + var(--font-mono))
    - apps/voss-app/src/themes/bundled/voss-ignite.json (the allowed token set)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (A12 token-only styling; token grep gate)
    - .planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md (Ignite tokens)
  </read_first>
  <action>
    In `cockpitStyles.css`: add keyboard-focus order (tabindex/roving-tabindex) so focus traverses Board → detail drawer → timeline; add a `@media (prefers-reduced-motion: reduce)` block disabling all cockpit animations including the AttentionQueue pulse; ensure budget/cost/confidence use `var(--font-mono)`; verify state colors meet contrast (A12 accent tokens). Create `scripts/token-grep-gate.mjs`: parse `voss-ignite.json` for the allowed `--xxx` token names, grep all `src/org/cockpit/*.css` + new cockpit components for `--` custom properties, and exit non-zero if any token NOT in the A12 set is introduced (filter comment lines, e.g. `grep -v '^#'`/strip CSS comments, to avoid header prose self-invalidating the gate). Create `a11y.test.tsx`: assert focus order Board→drawer→timeline (drive Tab via testing-library), and assert that under a mocked `prefers-reduced-motion` the pulse/animation classes are disabled.
  </action>
  <verify>
    <automated>cd apps/voss-app && node scripts/token-grep-gate.mjs && npx vitest run src/org/cockpit/__tests__/a11y.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - `token-grep-gate.mjs` exits 0 (no new tokens) and exits non-zero if a foreign `--xxx` is added.
    - a11y test asserts focus order Board→drawer→timeline.
    - Reduced-motion media query disables cockpit animation (test-asserted).
    - Budget/cost/confidence use `var(--font-mono)`.
  </acceptance_criteria>
  <done>Cockpit is keyboard-navigable, reduced-motion-honoring, A12-token-pure with monospace numerics.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Phase-final human verification (Tauri-runtime visuals)</name>
  <action>
    All automated checks (vitest + cargo + token gate) are green; this task is the human verification of Tauri-runtime visuals that cannot run headless on macOS (WebDriver blocked). Present the verification steps below to the operator and pause for approval. Do not auto-advance — `gate="blocking"`.
  </action>
  <what-built>
    The full V14 cockpit: RunCommandBar intake (always-on strip), 4-region cockpit (Board + drawer + timeline + gate bar) driven by one selection, AttentionQueue pill + dockable panel, Live↔Review toggle preserving the grid, sparse quick-launch + adopt modals, managed-launch tier surface, live/snapshot label. All unit/component/cargo tests are green; these checks cover the Tauri-runtime visuals that cannot run headless on macOS.
  </what-built>
  <how-to-verify>
    1. `cd apps/voss-app && npm run tauri dev` (or the project's dev command).
    2. Press ⌘⇧O → the cockpit opens (no tab bar; Board spine + drawer + timeline + gate bar).
    3. Click a board card → the drawer shows its content, the timeline scrolls to its node, the gate bar reflects its envelope — all from one click.
    4. Toggle Live↔Review (⌘⇧O) twice → the selected card persists and the terminal grid scrollback is unchanged after returning.
    5. Open Quick-Launch → confirm preset cards with default model, NO raw-command field, NO explainer; ⌘↵ launches, Esc cancels.
    6. Open "Let Voss manage this agent" on a running agent → confirm plain-language copy (no cage/PermissionGate/pane jargon), no per-tool-gate promise, role/risk editable.
    7. Confirm the AttentionQueue pill appears in the StatusBar and pulses on a blocking item without hard-modaling.
    8. Toggle OS reduced-motion → confirm the pulse/animation stops.
  </how-to-verify>
  <verify>
    <human-check>Operator confirms steps 1-8 pass in the running Tauri app.</human-check>
  </verify>
  <acceptance_criteria>
    - Operator confirms one click drives all four cockpit regions.
    - Live↔Review preserves selection + grid scrollback.
    - Quick-launch is sparse (no raw-command/explainer); adopt copy carries no jargon/per-tool promise.
    - Reduced-motion stops the pulse.
  </acceptance_criteria>
  <resume-signal>Type "approved" or describe issues to fix.</resume-signal>
  <done>Operator-approved Tauri-runtime verification of the V14 cockpit.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org && node scripts/token-grep-gate.mjs` green; `npx tsc --noEmit` clean.
- Full suite: `npx vitest run` + `cargo test -p voss-app-core` green; V11 `org/__tests__/*` + grid tests unregressed (D-02, ⌘⇧O).
- Human-verify checkpoint approved.
</verification>

<success_criteria>
Feedback routes to native sessions (else disabled-with-reason); the cockpit is keyboard-navigable, reduced-motion-honoring, and A12-token-pure; the phase-final human verification of Tauri-runtime visuals passes.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-12-SUMMARY.md` when done.
</output>
