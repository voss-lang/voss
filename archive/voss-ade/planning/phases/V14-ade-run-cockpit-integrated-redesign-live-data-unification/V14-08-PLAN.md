---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 08
type: execute
wave: 5
depends_on: ["V14-03", "V14-04"]
files_modified:
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/__tests__/liveReviewToggle.test.tsx
autonomous: true
requirements: [VCKP-08]
must_haves:
  truths:
    - "A test toggles Live<->Review on one run and asserts the selected run/card persists across the switch"
    - "The terminal grid state is unchanged after returning (no PTY regression) — the grid stays mounted via the display:none swap, never conditionally unmounted (Pitfall 3)"
    - "The toggle extends the existing orgViewOpen / ⌘⇧O mechanism; ⌘⇧O does not regress"
    - "The D-07 'Open in grid' button in the card drawer flips orgViewOpen and focuses the bound live pane (opt-in, never automatic)"
  artifacts:
    - path: "apps/voss-app/src/App.tsx"
      provides: "Live<->Review toggle extending orgViewOpen + handleLaunchAgent wired"
      contains: "orgViewOpen"
    - path: "apps/voss-app/src/__tests__/liveReviewToggle.test.tsx"
      provides: "VCKP-08 toggle-persistence test"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/org/selection.ts"
      via: "selected run/card persists across toggle"
      pattern: "selectedCardId"
---

<objective>
VCKP-08 Live Work ↔ Run Review toggle over the same selected run, preserving the terminal grid. Extend the existing `orgViewOpen` + `display:none` swap (NOT conditional mount — that kills PTY panes, Pitfall 3). Complete the `handleLaunchAgent` stub so launches actually spawn (passing cardId as sessionId — Bridge B). Wire the D-07 "Open in grid" button in the card drawer to flip `orgViewOpen` and focus the bound pane.

Purpose: One run, two modes, grid preserved. Closes the Live/Review distinction without PTY regression.
Output: extended toggle + completed handleLaunchAgent in App.tsx, D-07 Open-in-grid wiring, persistence test.
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
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md

<interfaces>
From apps/voss-app/src/App.tsx: `orgViewOpen` signal (:240), grid `display: orgViewOpen() ? 'none' : 'flex'` (:1183), cockpit `<Show when={orgViewOpen()}>` (:1263), the contract comment (:1262), ⌘⇧O toggle (:1008-1010), `handleLaunchAgent` stub (:268-272 — only splits a pane today), StatusBar `orgViewOpen` prop (:1283).
From apps/voss-app/src/pane/pty-ipc.ts:167-186: `spawnAgent({..., sessionId, paneId})`.
From apps/voss-app/src/org/model/bridge.ts (plan 02): `registerTerminalCard(paneId)` → cardId to pass as sessionId.
From apps/voss-app/src/org/selection.ts (plan 00): `selectedCardId`/`selectedRunId` persist across the toggle (already global).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend toggle (no PTY regression) + complete handleLaunchAgent</name>
  <files>apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx:240,268-272,1008-1010,1183,1261-1263 (orgViewOpen, stub, ⌘⇧O, display:none swap, contract comment)
    - apps/voss-app/src/pane/pty-ipc.ts:167-186 (spawnAgent)
    - apps/voss-app/src/org/model/bridge.ts (registerTerminalCard from plan 02)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (App.tsx entry: complete-the-stub + Live/Review Pitfall 3)
  </read_first>
  <action>
    In `App.tsx`: (1) Complete `handleLaunchAgent` (:268-272) — keep the pane split, then actually spawn the agent: mint the cardId via `registerTerminalCard(paneId)` and call `spawnAgent({cliBinary, cliArgs, taskPrompt, sessionId: cardId, paneId})` (Bridge B). (2) Treat the existing `orgViewOpen` swap as the Live (grid) ↔ Review (cockpit) toggle — the grid MUST stay mounted via `display:none` (never conditionally unmount — Pitfall 3); the `selectedCardId`/`selectedRunId` are already global so they persist across the swap automatically. Confirm the ⌘⇧O keybinding (:1008-1010) still toggles `orgViewOpen` and is unchanged. Do not move or unmount `GridRoot`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -E "App.tsx" || echo "clean" ; grep -n "display: orgViewOpen() ? 'none'" src/App.tsx && echo "swap intact" || echo "FAIL swap changed"</automated>
  </verify>
  <acceptance_criteria>
    - `handleLaunchAgent` now calls `spawnAgent` with the minted cardId as `sessionId` (no longer a pane-split-only stub).
    - The grid stays mounted via `display:none` (grep confirms the swap line intact); GridRoot is never conditionally unmounted.
    - ⌘⇧O still toggles orgViewOpen.
  </acceptance_criteria>
  <done>Launch stub completed (keystone Bridge B at launch); Live↔Review extends the display:none swap; grid preserved.</done>
</task>

<task type="auto">
  <name>Task 2: D-07 Open-in-grid wiring + toggle-persistence test</name>
  <files>apps/voss-app/src/App.tsx, apps/voss-app/src/__tests__/liveReviewToggle.test.tsx</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/CardDrawer.tsx (plan 03 — the Open-in-grid button placeholder to wire)
    - apps/voss-app/src/App.tsx:240,1263 (orgViewOpen flip target)
    - apps/voss-app/src/org/model/bridge.ts (resolveCard → paneId to focus)
    - apps/voss-app/src/__tests__ (existing App-level test style, if any) or apps/voss-app/src/org/__tests__/orgView.test.tsx
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-07 opt-in jump-to-grid)
  </read_first>
  <action>
    Wire the D-07 "Open in grid" button (placeholder from plan 03's CardDrawer) to call into App: flip `orgViewOpen(false)` (show grid) and focus the bound live pane via `resolveCard(selectedCardId()).paneId` (opt-in, never automatic). Create `liveReviewToggle.test.tsx`: select a run + card, toggle Live↔Review (flip `orgViewOpen` twice), assert `selectedRunId`/`selectedCardId` persist across the switch and that the grid container is never unmounted (assert the grid node remains in the DOM, only `display` changes). Mock Tauri invoke as the existing tests do.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/__tests__/liveReviewToggle.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Toggling Live↔Review preserves `selectedRunId`/`selectedCardId` (asserted in the test).
    - The grid node persists in the DOM across the toggle (display swap, not unmount).
    - "Open in grid" flips orgViewOpen and targets the bound paneId via resolveCard.
  </acceptance_criteria>
  <done>D-07 opt-in jump-to-grid wired; toggle persists selection and preserves the grid.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/__tests__ src/org` green; `npx tsc --noEmit` clean.
- display:none swap intact (no conditional unmount); ⌘⇧O unchanged.
- Existing grid + V11 tests unregressed.
</verification>

<success_criteria>
Live↔Review toggles over one run with persistent selection and zero terminal-grid regression; the launch stub is completed and binds the keystone at launch; D-07 Open-in-grid is opt-in.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-08-SUMMARY.md` when done.
</output>
