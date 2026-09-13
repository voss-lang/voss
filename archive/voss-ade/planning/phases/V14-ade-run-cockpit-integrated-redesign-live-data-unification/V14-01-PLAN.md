---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 01
type: execute
wave: 1
depends_on: ["V14-00"]
files_modified:
  - apps/voss-app/src/org/model/adapters.ts
  - apps/voss-app/src/org/model/__tests__/adapters.test.ts
  - apps/voss-app/src/org/__tests__/selection.test.tsx
autonomous: true
requirements: [VCKP-01]
must_haves:
  truths:
    - "A unit test feeds a golden RunData snapshot + a fake live-registry payload into the adapter and asserts ONE merged model where a card carries BOTH snapshot fields AND live-overlay fields (status, live budget, paneId)"
    - "The adapter is a pure function (no Solid imports, no produce/structuredClone) so it is fixture-testable like boardDerive.ts"
    - "Selecting a card via the selection store is observable by >=2 distinct surfaces in a component test"
    - "RunData and guards.ts are not edited (D-02 contract stays green); overlay lives only in the normalized model"
  artifacts:
    - path: "apps/voss-app/src/org/model/adapters.ts"
      provides: "snapshot->model + registry->model overlay (buildModel)"
      contains: "export function buildModel"
    - path: "apps/voss-app/src/org/model/__tests__/adapters.test.ts"
      provides: "VCKP-01 adapter merge test"
  key_links:
    - from: "apps/voss-app/src/org/model/adapters.ts"
      to: "apps/voss-app/src/org/boardDerive.ts"
      via: "cardsFromRunData spine reuse"
      pattern: "cardsFromRunData"
---

<objective>
VCKP-01 data layer: a pure adapter `buildModel(snapshot, liveAgents, budgets, bridge) → Run` that takes the snapshot `RunData` as the spine (via the existing `cardsFromRunData`) and overlays live registry/budget fields by card→pane. Plus a component test proving a single `selectedCard` action is observed by ≥2 surfaces. No layout change yet — pure data + selection.

Purpose: Unify the two disjoint data planes (G1) into one view model without touching the D-02-guarded snapshot. This is the foundation every cockpit region reads.
Output: `adapters.ts` (pure, fixture-tested), `adapters.test.ts` (green), `selection.test.tsx` (≥2-surface observation).
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
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-00-SUMMARY.md

<interfaces>
From apps/voss-app/src/org/boardDerive.ts: `cardsFromRunData(data: RunData | null): BoardCard[]` — spine; snapshot card `id` IS the `sessionNodeId` (uses `n.id`). `deriveColumn`, `deriveRisk`.
From apps/voss-app/src/pane/budgetRegistry.ts: `budgetByPaneId(): Record<string, BudgetEntry>` keyed by paneId; `BudgetEntry = BudgetState & { lastSeenMs }`, has `cost_usd`.
From apps/voss-app/src/org/model/normalized.ts (plan 00): `Run`, `Card`, `Agent` types.
From apps/voss-app/src/org/model/bridge.ts: NOT YET built (plan 02). For this plan, the adapter takes a minimal `bridge` param typed as `{ paneIdForCard(cardId: string): string | undefined }` — an interface the plan-02 bridge will satisfy. Do NOT import the bridge module here (avoid a cross-wave dependency); accept the resolver as a param.
AgentEntry (camelCase): `{ paneId, sessionId, cliBinary, cliArgs, cwd, status, lastSeen }` from `get_active_agents`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: buildModel pure adapter (snapshot spine + live overlay)</name>
  <files>apps/voss-app/src/org/model/adapters.ts, apps/voss-app/src/org/model/__tests__/adapters.test.ts</files>
  <behavior>
    - Given a golden RunData fixture + a fake AgentEntry[] + a budgets map + a bridge resolver mapping card C1→pane P1, buildModel returns a Run whose card C1 carries snapshot fields (title/role/risk/column from cardsFromRunData) AND overlay fields (paneId='P1', liveBudget from budgets['P1'].cost_usd, liveStatus derived from the registry/budget freshness).
    - A card with no bound pane gets no paneId/liveBudget but retains snapshot fields and sessionNodeId === its own id.
    - buildModel(null, [], {}, bridge) returns an empty-cards Run without throwing (null tolerance, mirror boardDerive).
  </behavior>
  <read_first>
    - apps/voss-app/src/org/boardDerive.ts:1-58 (pure-module header + cardsFromRunData spine to reuse)
    - apps/voss-app/src/pane/budgetRegistry.ts:10-39 (BudgetEntry shape + immutable-update discipline, NO produce)
    - apps/voss-app/src/org/model/normalized.ts (Run/Card/Agent types from plan 00)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (adapters.ts pattern: Pattern 1, buildModel skeleton, anti-pattern Pitfall 2)
    - apps/voss-app/src/org/__tests__/fixtures/live-registry.json + run fixtures (plan 00) for the test
  </read_first>
  <action>
    Create `src/org/model/adapters.ts` as a PURE module (header comment "No Solid imports, no produce/structuredClone" copied from boardDerive.ts). Export `buildModel(snapshot: RunData | null, liveAgents: AgentEntry[], budgets: Record<string, BudgetEntry>, bridge: { paneIdForCard(cardId: string): string | undefined }): Run`. Build cards via `cardsFromRunData(snapshot)` (the spine), then `.map` each card adding `sessionNodeId: card.id`, `paneId: bridge.paneIdForCard(card.id)`, `liveBudget: budgets[paneId ?? '']?.cost_usd`, and `liveStatus` derived from registry status / budget freshness. Hand-built immutable object literals only (Pitfall 5). Also export `registryToAgents(liveAgents, budgets): Agent[]` for the roster overlay. Do NOT import or edit `RunData`/`guards.ts`. Flip the plan-00 `adapters.test.ts` skipped assertions to active and add the three behaviors above.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/model/__tests__/adapters.test.ts && npx vitest run src/org/__tests__/guards.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - `adapters.test.ts` asserts a merged card carrying snapshot title/role/risk/column AND paneId='P1' + liveBudget — all from one `buildModel` call.
    - `adapters.ts` imports nothing from `solid-js` and uses no `produce`/`structuredClone` (grep gate: `grep -L "solid-js\|produce\|structuredClone" src/org/model/adapters.ts`).
    - `guards.test.ts` still green (D-02 unregressed).
  </acceptance_criteria>
  <done>buildModel merges both planes into one model; card carries snapshot+overlay; pure + fixture-tested; D-02 green.</done>
</task>

<task type="auto">
  <name>Task 2: Selection observed by >=2 surfaces (component test)</name>
  <files>apps/voss-app/src/org/__tests__/selection.test.tsx</files>
  <read_first>
    - apps/voss-app/src/org/selection.ts (plan 00 — selectedCardId signal)
    - apps/voss-app/src/org/__tests__/boardPanel.test.tsx (existing component-test render style with @solidjs/testing-library)
    - apps/voss-app/src/org/panels/BoardPanel.tsx:142-215 (onCardSelect/selectedCardId props)
  </read_first>
  <action>
    Create `selection.test.tsx`: render two trivial consumer components (or two `BoardPanel`-style stubs) that each read `selectedCardId()` from `src/org/selection.ts`. Call `setSelectedCardId('C1')` once and assert BOTH rendered surfaces reflect `C1` (the VCKP-01 acceptance: one action observed by ≥2 distinct surfaces). Use `@solidjs/testing-library` consistent with `boardPanel.test.tsx`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/selection.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Test sets `selectedCardId('C1')` once; two independent rendered surfaces both observe `C1`.
    - Test uses the global signal from `selection.ts`, not local state.
  </acceptance_criteria>
  <done>One selection action is observed by two surfaces; VCKP-01 selection acceptance met.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org` green; `npx tsc --noEmit` clean.
- adapters.ts is pure (no solid-js/produce/structuredClone).
- D-02 (`guards.test.ts`) and V11 panel tests unregressed.
</verification>

<success_criteria>
buildModel unifies snapshot + live registry into one model carrying both field sets; selection store observed by ≥2 surfaces; snapshot contract untouched.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-01-SUMMARY.md` when done.
</output>
