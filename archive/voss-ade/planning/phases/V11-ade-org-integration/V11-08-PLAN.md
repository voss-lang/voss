---
phase: V11-ade-org-integration
plan: 08
type: execute
wave: 4
depends_on: ["01", "03", "04"]
files_modified:
  - apps/voss-app/src/org/panels/ReplayPanel.tsx
  - apps/voss-app/src/org/__tests__/replayPanel.test.tsx
autonomous: true
requirements: [VADE-10]
must_haves:
  truths:
    - "The Replay panel steps forward/back through the run's persisted transitions"
    - "At each step the board snapshot reflects board/card state computed by the client-side reducer"
    - "Back is disabled at step 0; Forward is disabled at the final step; a Step N/M counter shows position"
    - "A notice states that audit/verdict/budget/scope panels show final-run state only (D-06)"
    - "The replay board is read-only (cards non-interactive)"
  artifacts:
    - path: "apps/voss-app/src/org/panels/ReplayPanel.tsx"
      provides: "Step scrubber + reducer-driven board snapshot (VADE-10)"
      contains: "Step"
  key_links:
    - from: "apps/voss-app/src/org/panels/ReplayPanel.tsx"
      to: "apps/voss-app/src/org/replayReducer.ts"
      via: "computeBoardAtStep(plainNodes, step)"
      pattern: "computeBoardAtStep"
---

<objective>
Fill the Replay panel stub (VADE-10): forward/back step scrubbing over the run's persisted transitions, with the board snapshot at each step computed by the Plan-01 client-side reducer (D-05/D-06 — board/card state only). Other panels remain final-snapshot; a notice states this. The replay board is read-only.

Purpose: Wave 4 — final panel; depends on the reducer (Plan 01) and the board layout (Plan 04). Owns only its own files.
Output: ReplayPanel.tsx, replayPanel.test.tsx.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V11-ade-org-integration/V11-SPEC.md
@.planning/phases/V11-ade-org-integration/V11-UI-SPEC.md
@.planning/phases/V11-ade-org-integration/V11-PATTERNS.md
@.planning/phases/V11-ade-org-integration/V11-01-SUMMARY.md
@.planning/phases/V11-ade-org-integration/V11-04-SUMMARY.md

<interfaces>
<!-- replayReducer (Plan 01): computeBoardAtStep(nodes: SessionTreeNode[], step: number): BoardFrame -->
<!--   BoardFrame { columns: Record<string,CardSnapshot[]>, step, eventLabel }. -->
<!-- Total step count M = number of board.transition entries across all nodes (the reducer's ordered list length). -->
<!-- MUST pass PLAIN nodes to the reducer: const plain = JSON.parse(JSON.stringify(runData().session_tree.nodes)) — -->
<!--   never the Solid store proxy directly (Pitfall 3: DATA_CLONE_ERR / produce-proxy). -->
<!-- UI-SPEC Panel 10 (Replay): controls bar 32px (‹ Back / Step N/M / › Forward / event label / active step dot --focus); -->
<!--   board snapshot area reuses Board layout but NON-INTERACTIVE + REPLAY watermark; -->
<!--   other-panels notice "Audit, Verdict, Budget, and Scope panels show final-run state only."; -->
<!--   empty "No transition history for this run. Replay requires persisted transitions."; -->
<!--   Back aria-label="Previous step", Forward aria-label="Next step", aria-disabled at bounds. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: ReplayPanel — scrubber + reducer-driven board snapshot + tests</name>
  <files>apps/voss-app/src/org/panels/ReplayPanel.tsx, apps/voss-app/src/org/__tests__/replayPanel.test.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 10: Replay" — controls bar, board snapshot, REPLAY watermark, other-panels notice, empty state, accessibility)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/panels/ReplayPanel.tsx" — No Analog; createSignal(step) + Back/Forward; "Produce/proxy hand-clone" shared pattern)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md (Pitfall 3 produce/proxy; D-05/D-06 board-only)
    - apps/voss-app/src/org/replayReducer.ts (computeBoardAtStep) + apps/voss-app/src/org/panels/BoardPanel.tsx (board layout to mirror, read-only)
  </read_first>
  <behavior>
    - At step 0, Back is disabled (aria-disabled true); the board snapshot matches computeBoardAtStep(nodes, 0)
    - Forward advances the step counter and re-renders the board at the new step; at the final step Forward is disabled
    - The step counter shows "Step N / M" with M = total transition count
    - When there are no board.transition entries, the empty state "No transition history for this run." renders and no controls are active
    - The board snapshot is read-only (cards are non-interactive — no onCardSelect wiring)
  </behavior>
  <action>
    Implement `ReplayPanel(props: { data: RunData | null })`. Compute `plainNodes = JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []))` (Pitfall 3 — strip proxies; NEVER pass the store proxy or use produce/structuredClone). Compute total steps M from the reducer's transition list length (call a helper or derive from computeBoardAtStep metadata; if needed expose a small `countSteps(nodes)` in the panel). `createSignal(step)` starting at 0. Controls bar (32px, `--bg-1`): `‹` Back (`aria-label="Previous step"`, disabled+`aria-disabled` at step 0), `Step N / M` counter (min-width 64px centered), `›` Forward (`aria-label="Next step"`, disabled at M-1), the active step dot (`--focus`), and the current frame's `eventLabel` (truncated, flex:1). Board snapshot area: render `computeBoardAtStep(plainNodes, step())` using the same 6-column layout as BoardPanel but READ-ONLY (no cursor:pointer, no onCardSelect, no focus ring) with a `REPLAY` watermark top-right. Above the board, the 24px notice row: "Audit, Verdict, Budget, and Scope panels show final-run state only." Empty (M===0) → "No transition history for this run. Replay requires persisted transitions." In replayPanel.test.tsx (`vi.mock` Tauri), import fixtures, assemble RunData, mount → assert Back disabled at step 0, click Forward → assert the counter and board update, assert the final-state notice text renders, assert an empty-transitions RunData shows the empty state.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/replayPanel.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>ReplayPanel scrubs forward/back with bounds-disabled buttons, renders the reducer board snapshot per step, shows the final-state notice + REPLAY watermark + empty state; passes plain (non-proxy) nodes to the reducer; tests green; tsc clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| store proxy → reducer | Solid store values are Proxies; must be plain-cloned before the pure reducer |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-18 | Denial of Service | DATA_CLONE_ERR from passing store proxy to reducer | mitigate | JSON.parse(JSON.stringify(nodes)) before computeBoardAtStep; never produce/structuredClone (Pitfall 3) |
| T-V11-19 | Tampering | step out of bounds → undefined board frame | mitigate | Back/Forward disabled at bounds (step 0 / M-1); reducer clamps slice; empty-state test covers M===0 |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run src/org/__tests__/replayPanel.test.tsx && npx tsc --noEmit` green.
- ReplayPanel passes plain-cloned nodes (grep "JSON.parse(JSON.stringify") and uses computeBoardAtStep.
</verification>

<success_criteria>
- Replay steps forward/back through persisted transitions, board/card state correct per step (VADE-10).
- Bounds-disabled controls + step counter + final-state notice + read-only board + empty state.
- No produce/structuredClone on store data; no new dependencies.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-08-SUMMARY.md` when done.
</output>
