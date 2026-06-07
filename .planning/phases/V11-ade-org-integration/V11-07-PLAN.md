---
phase: V11-ade-org-integration
plan: 07
type: execute
wave: 4
depends_on: ["02", "03"]
files_modified:
  - apps/voss-app/src/org/panels/DiffPanel.tsx
  - apps/voss-app/src/org/panels/BlockedPanel.tsx
  - apps/voss-app/src/org/DecisionDialog.tsx
  - apps/voss-app/src/org/__tests__/blockedPanel.test.tsx
autonomous: true
requirements: [VADE-08, VADE-09]
must_haves:
  truths:
    - "The Diff panel shows a selected card's verification surface (a_verification) and an explicit 'no diff recorded' empty state"
    - "The Blocked panel lists blocked cards with reasons"
    - "A decision action opens a confirmation dialog showing the EXACT CLI command before shelling"
    - "Confirming shells the voss CLI via run_decision, shows inline success/failure, and auto-refreshes the run"
    - "The app never writes run decisions directly — the CLI is the sole write path"
  artifacts:
    - path: "apps/voss-app/src/org/DecisionDialog.tsx"
      provides: "Confirmation dialog: exact CLI command preview + execute + inline result + auto-close/refresh (D-07/D-08)"
      contains: "Command to run:"
    - path: "apps/voss-app/src/org/panels/BlockedPanel.tsx"
      provides: "Blocked-card list + decision action buttons"
      contains: "No blocked cards"
  key_links:
    - from: "apps/voss-app/src/org/DecisionDialog.tsx"
      to: "decisionActions runDecision (Plan 02)"
      via: "invoke run_decision then refreshRun"
      pattern: "runDecision|refreshRun"
    - from: "apps/voss-app/src/org/panels/DiffPanel.tsx"
      to: "RunData.review[cardId].a_verification"
      via: "render verification surface"
      pattern: "a_verification"
---

<objective>
Fill the Diff drilldown (VADE-08) and Blocked-card decision flow (VADE-09) stubs. The Diff panel renders the per-card verification surface — `a_verification` from the `.review.json` sidecar — and makes the "no diff recorded" empty state explicit (raw diffs do NOT persist in the V2-V7 substrate; this is the verified reality, not a v1 simplification). The Blocked panel lists blocked cards and triggers a confirmation dialog (D-07) that previews the EXACT CLI command and shells it via `run_decision` (D-08) — the CLI is the sole write path.

Purpose: Wave 4 — decision flow + drilldown; owns only its own files.
Output: DiffPanel.tsx, BlockedPanel.tsx, DecisionDialog.tsx, blockedPanel.test.tsx.
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
@.planning/phases/V11-ade-org-integration/V11-02-SUMMARY.md
@.planning/phases/V11-ade-org-integration/V11-03-SUMMARY.md

<interfaces>
<!-- decisionActions (Plan 02): buildDecisionCommand(action, runId, cwd) → "voss audit <runId> --cwd <cwd> --approve"; -->
<!--   runDecision(cliBinary, cwd, action, runId) → Promise<DecisionResult{success,stdout,stderr,exit_code}>. -->
<!-- orgStore (Plan 02): runData, refreshRun(cwd, cliBinary), currentRunId. -->
<!-- VERIFIED decision reality (cli.py): the ONLY non-interactive run-level write path is `voss audit <run_id> --approve`. -->
<!--   No `approve/reject/unblock <card>` command exists; team-run sign-off is interactive. -->
<!--   → 'approve' is the actionable decision; reject/unblock render disabled with an explanatory tooltip (no app-side write; one-write-path preserved). -->
<!-- VADE-08 reality (RESEARCH Pitfall 4): raw diff text NEVER persists (sections_missing always has diff_summary). -->
<!--   The per-card verification surface = review[cardId].a_verification {result, test_path_or_rubric, notes}. -->
<!-- UI-SPEC Panel 8 (Diff): card picker; diff view (cyan add / red remove / context); VERIFICATION section; -->
<!--   "Select a card to view its diff." / "No diff recorded for this card." -->
<!-- UI-SPEC Panel 9 (Blocked): blocked card rows (id red, reason 2-line, Approve/Reject/Unblock buttons); empty "No blocked cards in this run." -->
<!-- UI-SPEC Decision dialog: --bg-3, 480px, header "{Action}: {card_id}", CLI preview block "Command to run:" border-left 2px --focus, -->
<!--   result area ✓ Done/✗ Failed, footer Keep Viewing + Confirm; auto-close 1500ms + load_run refresh on success; Escape/×; role=dialog aria-modal. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: DecisionDialog — exact CLI preview + execute + inline result + auto-refresh</name>
  <files>apps/voss-app/src/org/DecisionDialog.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 9 → Decision confirmation dialog" — header, CLI preview block, result area, footer, auto-close, accessibility)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/panels/BlockedPanel.tsx" — dialog skeleton, focus trap, Escape, opacity enter, auto-close-after-success effect)
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx + modal.css (dialog analog: backdrop, focus trap, requestAnimationFrame visible)
    - apps/voss-app/src/org/decisionActions.ts + orgStore.ts (Plan 02: buildDecisionCommand, runDecision, refreshRun)
  </read_first>
  <action>
    Implement `DecisionDialog(props: { action: DecisionAction; runId: string; cardId: string; cwd: string; cliBinary: string; onDismiss: () => void })`. `role="dialog"` `aria-modal="true"` `aria-labelledby` → title id; `--bg-3`, 480px, backdrop `rgba(0,0,0,0.6)`, opacity+scale enter via `requestAnimationFrame(setVisible)` + reduced-motion override. Header (48px): title `{Action}: {cardId}` (Poppins 16px) + `×` dismiss (`aria-label="Close dialog"`). CLI preview block: label "Command to run:" + a `<pre>` showing `buildDecisionCommand(action, runId, cwd)` — the EXACT literal command (D-07), border-left 2px `--focus`. Result area (hidden until execution): on success `✓ Done` + first 200 chars stdout; on failure `✗ Failed` + stderr. Footer: "Keep Viewing" (dismiss) + "Confirm" (disabled+opacity 0.5 while executing). Confirm handler: set executing, `await runDecision(cliBinary, cwd, action, runId)`, store result; on `result.success` start a 1500ms `setTimeout` that calls `onDismiss()` AND `refreshRun(cwd, cliBinary)` (D-08 auto-refresh), cleaned up via `onCleanup`. Focus trap + Escape-to-dismiss + outside-click dismiss. The dialog NEVER writes to disk — it only calls runDecision which shells the CLI (one-write-path invariant).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q "Command to run:" src/org/DecisionDialog.tsx && grep -q "buildDecisionCommand" src/org/DecisionDialog.tsx && grep -q "refreshRun" src/org/DecisionDialog.tsx</automated>
  </verify>
  <done>DecisionDialog shows the exact CLI command before execution, shells via runDecision, shows inline result, auto-closes+refreshes on success; ARIA + focus trap present; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 2: BlockedPanel — blocked-card list + decision actions + test</name>
  <files>apps/voss-app/src/org/panels/BlockedPanel.tsx, apps/voss-app/src/org/__tests__/blockedPanel.test.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 9: Blocked" — blocked card list, action buttons Approve/Reject/Unblock, empty state, hover)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md (boardPanel.test.tsx mount pattern; BlockedPanel → AgentLaunchModal analog)
    - apps/voss-app/src/org/boardDerive.ts (deriveColumn — a card is blocked when its derived column is "Blocked")
    - apps/voss-app/src/org/DecisionDialog.tsx (Task 1)
  </read_first>
  <action>
    Implement BlockedPanel: derive blocked cards from `props.data` — nodes whose derived column is "Blocked" (reuse boardDerive.deriveColumn; if Plan 04's boardDerive is unavailable in this wave, inline the same verified derivation). Each 72px row: card id (mono `--accent-red`), blocked reason (Inter 12px 2-line clamp — from terminal_state.final or last transition outcome), right-aligned action buttons: `Approve` (`--accent-green`, ENABLED — maps to the real `voss audit --approve`), `Reject` and `Unblock` (rendered DISABLED with `title`/`aria-disabled` explaining "No non-interactive CLI command exists yet — use the harness sign-off" — this honors the SPEC one-write-path constraint without inventing harness behavior). Clicking Approve opens `DecisionDialog` with action 'approve', the run id (`currentRunId()` / `props.data.run_id`), and the card id. Empty → "No blocked cards in this run." In blockedPanel.test.tsx (`vi.mock` Tauri — make `invoke` resolve a DecisionResult): mount with a RunData whose fixture has a Blocked card → assert the blocked row renders, assert clicking Approve opens the dialog showing the literal command containing "audit" and "--approve", and assert no app-side write occurs (only `invoke('run_decision', ...)` is called — assert the invoke mock was called with 'run_decision' and never with a file-write command).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/blockedPanel.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>BlockedPanel lists blocked cards + reasons; Approve opens the dialog with the exact CLI command; test asserts run_decision is the only write path; empty state present; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 3: DiffPanel — verification surface + explicit no-diff state</name>
  <files>apps/voss-app/src/org/panels/DiffPanel.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 8: Diff + Verification Drilldown" — card picker, diff view, verification result, no-selection + no-diff states)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md (Pitfall 4 + "sections_missing" — raw diffs never persist; a_verification is the per-card verification surface)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("DiffPanel" → ContextPanel analog)
    - apps/voss-app/src/org/types.ts (ReviewSidecar.a_verification)
  </read_first>
  <action>
    Implement `DiffPanel(props: { data: RunData | null; selectedCardId?: string })`. Card picker at top (Inter label "Card:" + card id button + ▾) listing cards from review keys / nodes; honors `selectedCardId` from the shell (set when a board card is clicked). For the selected card: look up `props.data.review[cardId]`. Since raw diff text does NOT persist (Pitfall 4 — verified), render the VERIFICATION section as the primary surface: outcome badge from `a_verification.result` (PASS green / FAIL red / SKIP `--fg-3`), `test_path_or_rubric` (mono), notes (pre-wrap). Where a card has an `a_verification` but no diff (always the case in this substrate), the diff view area shows the explicit "No diff recorded for this card." state (UI-SPEC) — this is the verified reality, NOT a placeholder. When no card is selected → "Select a card to view its diff." Add a code comment citing RESEARCH Pitfall 4 so future readers know the no-diff state is by-design. Use only CSS-var colors.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q "No diff recorded for this card" src/org/panels/DiffPanel.tsx && grep -q "a_verification" src/org/panels/DiffPanel.tsx</automated>
  </verify>
  <done>DiffPanel renders the a_verification verification surface + the explicit no-diff empty state + no-selection state; tsc clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| decision action → CLI | the sole write path; user confirms the exact command before execution |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-15 | Elevation of Privilege | app writes run decisions directly bypassing CLI | mitigate | BlockedPanel/DecisionDialog only call run_decision (shells CLI); test asserts invoke('run_decision') is the only write call (VADE-09 acceptance) |
| T-V11-16 | Spoofing | dialog shows a different command than what executes | mitigate | DecisionDialog displays buildDecisionCommand and runDecision builds args from the same buildDecisionArgs (D-07 exact-command guarantee) |
| T-V11-17 | Information Disclosure | stale run state after a decision | mitigate | D-08 auto-refresh: refreshRun called after successful decision |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run src/org/__tests__/blockedPanel.test.tsx && npx tsc --noEmit` green.
- DecisionDialog shows "Command to run:" + the exact command; DiffPanel shows the explicit no-diff state (grep).
</verification>

<success_criteria>
- Diff drilldown shows the a_verification surface + explicit no-diff state (VADE-08, honoring the verified substrate reality).
- Blocked-card panel lists cards; decision action shells the CLI with the exact previewed command + auto-refresh (VADE-09).
- CLI is the sole write path (test-asserted); reject/unblock disabled-with-explanation (no invented harness behavior).
- No new dependencies.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-07-SUMMARY.md` when done.
</output>
