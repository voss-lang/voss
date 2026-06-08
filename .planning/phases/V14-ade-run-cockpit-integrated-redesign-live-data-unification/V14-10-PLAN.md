---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 10
type: execute
wave: 6
depends_on: ["V14-02", "V14-05"]
files_modified:
  - apps/voss-app/src/components/modal/AdoptAgentModal.tsx
  - apps/voss-app/src/org/adopt.ts
  - apps/voss-app/src/components/modal/__tests__/adoptAgentModal.test.tsx
autonomous: true
requirements: [VCKP-12]
must_haves:
  truths:
    - "Adopting a running pane creates/links a card bound to that pane's session, applies budget + scope, starts a transcript-audit node marked partial_lineage, and enforces review-before-done"
    - "Pre-adoption events are absent from its budget/audit (forward-only, D-11)"
    - "The modal copy contains NO internal-mechanics jargon (cage/Voss-native/PermissionGate/session-tree/partial lineage/pane) and makes NO per-tool-gate promise for external agents (D-10/D-11, tier C)"
    - "Role/risk are pre-inferred (risk from scope/budget, role from CLI) but editable and visible by default (D-12)"
    - "Where no harness adopt write-path exists, the action renders disabled-with-reason (no fake affordance)"
  artifacts:
    - path: "apps/voss-app/src/components/modal/AdoptAgentModal.tsx"
      provides: "'Let Voss manage this agent' adopt modal"
      contains: "Hand to Voss"
    - path: "apps/voss-app/src/org/adopt.ts"
      provides: "Pure adopt logic: bind card, infer role/risk, mark partial_lineage"
  key_links:
    - from: "apps/voss-app/src/org/adopt.ts"
      to: "apps/voss-app/src/org/model/bridge.ts"
      via: "registerTerminalCard binds the running pane to a new card"
      pattern: "registerTerminalCard"
---

<objective>
VCKP-12 (D-10/D-11/D-12): the "Let Voss manage this agent" adopt flow. Take a running ad-hoc terminal agent under run management, forward-only: bind a card to its pane (tier C — observe-only), apply advisory budget + scope, start a transcript-audit node marked `partial_lineage`, enforce review-before-done. Plain-language copy stating outcomes, never mechanics; no per-tool-gate promise for external agents. Role/risk pre-inferred + editable. Disabled-with-reason where no harness adopt path exists.

Purpose: The hinge — bring ad-hoc work under management without overstating control.
Output: AdoptAgentModal, pure adopt logic, test.
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
From apps/voss-app/src/components/modal/AgentLaunchModal.tsx:94-97,158-188: modal scaffold (backdrop/focus/Esc/⌘↵) to copy.
From apps/voss-app/src/org/model/bridge.ts (plan 02): `registerTerminalCard(paneId)` mints a cardId + binds the running pane → adopt creates the card binding.
From apps/voss-app/src/pane/budgetRegistry.ts: `budgetByPaneId()` — cost from now (forward-only baseline).
From apps/voss-app/src/org/decisionActions.ts:1-11: disabled-with-reason honesty (no fake affordance).
From normalized.ts: `CapabilityTier` — adopt is ALWAYS tier C (D-11).
D-10 sections: "Add it to / As the task / Limits / From now on, Voss will"; CTA "Hand to Voss".
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: adopt.ts — pure adopt logic (bind, infer, partial_lineage)</name>
  <files>apps/voss-app/src/org/adopt.ts, apps/voss-app/src/components/modal/__tests__/adoptAgentModal.test.tsx</files>
  <behavior>
    - adoptAgent({paneId, runId, scope, budget, cliBinary}) returns {cardId, sessionNodeId, auditNode:{lineage:'partial_lineage'}, reviewRequired:true, tier:'C'}.
    - The bound card uses registerTerminalCard(paneId) to mint the cardId.
    - inferRole(cliBinary) and inferRisk({scope, budget}) return editable defaults.
    - The transcript-audit node's cost baseline starts at adoption time (a pre-adoption cost is excluded).
    - When no harness adopt write-path is available (a passed capability flag is false), adoptAgent returns {disabled:true, reason:<string>} instead of binding (no fake affordance).
  </behavior>
  <read_first>
    - apps/voss-app/src/org/model/bridge.ts (registerTerminalCard from plan 02)
    - apps/voss-app/src/pane/budgetRegistry.ts (budgetByPaneId baseline)
    - apps/voss-app/src/org/decisionActions.ts:1-11 (disabled-with-reason)
    - apps/voss-app/src/org/boardDerive.ts:1-3 (pure-module header)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-11 forward-only/partial_lineage, D-12 role/risk)
  </read_first>
  <action>
    Create `adopt.ts` as a PURE module: `adoptAgent(input)` binds the running pane to a new card via `registerTerminalCard`, applies advisory budget+scope, produces an audit node marked `partial_lineage` with a cost baseline at adoption time (pre-adoption excluded), sets `reviewRequired:true`, and stamps `tier:'C'` (always — no retro-sandbox, D-11). Provide `inferRole(cliBinary)` + `inferRisk({scope,budget})` returning editable defaults (D-12). If a `harnessAdoptAvailable` flag is false, return a disabled-with-reason result (no binding). Note: `partial_lineage` is an internal field name — it must NOT surface in UI copy. Write `adoptAgentModal.test.tsx` covering the five behaviors (modal test added in task 2).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/components/modal/__tests__/adoptAgentModal.test.tsx -t "adopt"</automated>
  </verify>
  <acceptance_criteria>
    - adoptAgent binds a card to the pane, applies budget+scope, marks the audit node `partial_lineage`, sets reviewRequired + tier C.
    - Pre-adoption cost is excluded from the baseline.
    - No-harness-path → disabled-with-reason result (no binding).
    - `adopt.ts` is pure (no solid-js import).
  </acceptance_criteria>
  <done>Forward-only adopt logic binds + audits + reviews at tier C; honest disabled fallback.</done>
</task>

<task type="auto">
  <name>Task 2: AdoptAgentModal — plain-language copy, no jargon, no per-tool promise</name>
  <files>apps/voss-app/src/components/modal/AdoptAgentModal.tsx, apps/voss-app/src/components/modal/__tests__/adoptAgentModal.test.tsx</files>
  <read_first>
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx:158-188 (modal scaffold to copy)
    - apps/voss-app/src/org/adopt.ts (task 1)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (AdoptAgentModal pattern; copy rule; Pitfall 6)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-10 sections/CTA/copy rule, D-12)
  </read_first>
  <action>
    Create `AdoptAgentModal.tsx` copying the modal scaffold. Title "Let Voss manage this agent"; sections "Add it to" (current/new run) · "As the task" (role/risk pre-inferred + editable, D-12) · "Limits" (budget + advisory scope) · "From now on, Voss will" (track cost · record a transcript audit · monitor budget stop/warn · require review before done — outcomes, NOT mechanics). CTA "Hand to Voss" calls `adoptAgent`. Copy rule (D-10/D-11): NO `cage`/`Voss-native`/`PermissionGate`/`session-tree`/`partial lineage`/`pane` strings; NO per-tool-gate promise (tier C — budget-stop, not tool-gate; Pitfall 6). Where `harnessAdoptAvailable` is false, render the CTA disabled-with-reason. Add the modal tests: assert the rendered copy contains none of the forbidden jargon terms (grep-style DOM assertion) and no "tool"/"block" per-tool gating language; assert adopt calls bind+budget+scope+partial_lineage+review; assert disabled-with-reason when no harness path.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/components/modal/__tests__/adoptAgentModal.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Rendered modal copy contains none of: cage, Voss-native, PermissionGate, session-tree, partial lineage, pane (asserted in test).
    - No per-tool-gate promise for external agents (no "approve each tool"/"block tool" language).
    - CTA "Hand to Voss" triggers adoptAgent; disabled-with-reason when no harness path.
    - Role/risk shown pre-inferred + editable.
  </acceptance_criteria>
  <done>Plain-language tier-C adopt modal; no jargon, no overstated control; honest disabled fallback.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/components/modal` green; `npx tsc --noEmit` clean.
- Forbidden jargon absent from UI copy (test-asserted).
- adopt.ts pure; tier C always.
</verification>

<success_criteria>
Adopt binds a running pane forward-only (card + advisory budget/scope + partial_lineage audit + review-before-done) at tier C, with plain-language copy that never overstates control and degrades to disabled-with-reason where no harness path exists.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-10-SUMMARY.md` when done.
</output>
