---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 03
type: execute
wave: 2
depends_on: ["V14-00", "V14-01"]
files_modified:
  - apps/voss-app/src/org/cockpit/CockpitShell.tsx
  - apps/voss-app/src/org/cockpit/CardDrawer.tsx
  - apps/voss-app/src/org/cockpit/GateBar.tsx
  - apps/voss-app/src/org/cockpit/cockpitStyles.css
  - apps/voss-app/src/org/cockpit/__tests__/cockpit.test.tsx
  - apps/voss-app/src/org/OrgViewShell.tsx
autonomous: true
requirements: [VCKP-05]
must_haves:
  truths:
    - "Selecting card C1 once highlights C1 in the Board, shows C1 content in the detail drawer, scrolls the timeline rail to C1's node, and reflects C1's envelope in the gate bar — all from a single selection action"
    - "The cockpit is the single Run Review surface: the OrgViewShell ORG_TABS/activeTab tab switcher is removed (D-01); no legacy tab escape hatch (D-02)"
    - "All 10 existing panel components are reused verbatim as drawer/rail sections, not rewritten (D-02 reuse-not-rewrite)"
    - "The detail drawer is persistent with a defined no-selection empty state (D-08)"
    - "The grid and the existing ⌘⇧O toggle do not regress; existing V11 panel tests stay green"
  artifacts:
    - path: "apps/voss-app/src/org/cockpit/CockpitShell.tsx"
      provides: "4-region cockpit replacing the tab shell"
      contains: "BoardPanel"
    - path: "apps/voss-app/src/org/cockpit/CardDrawer.tsx"
      provides: "Detail drawer composing existing panel bodies"
    - path: "apps/voss-app/src/org/cockpit/GateBar.tsx"
      provides: "Bottom gate bar (budget/confidence/scope)"
  key_links:
    - from: "apps/voss-app/src/org/cockpit/CockpitShell.tsx"
      to: "apps/voss-app/src/org/selection.ts"
      via: "global selectedCardId drives all 4 regions"
      pattern: "selectedCardId"
---

<objective>
VCKP-05 integrated cockpit layout (D-01/D-02/D-07/D-08). Replace the `OrgViewShell` tab shell with a four-region cockpit: Board spine (BoardPanel, compact cards) + persistent Card detail drawer (composes Audit/Verdict/Diff/Scope/Budget/Blocked bodies) + Timeline/replay rail (SessionTreePanel + ReplayPanel) + bottom GateBar. One global `selectedCardId` drives all four regions. Panels are reused verbatim. The old tab switcher is removed — cockpit is the single Run Review surface.

Purpose: Close G4 (tabs → cockpit). One selection drives everything.
Output: CockpitShell, CardDrawer, GateBar, cockpit CSS (A12 tokens only), cockpit.test.tsx, and OrgViewShell stripped of its tab bar (logic lifted into CockpitShell).
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
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md

<interfaces>
From apps/voss-app/src/org/OrgViewShell.tsx: run-load `onMount` (:74-80), run-picker `pickRun` (:107-110), keydown/click cleanup (:82-103), loading/error `<Show>` (:184-209) — LIFT verbatim into CockpitShell. Panel prop wiring (:211-248): `<BoardPanel data={data()} onCardSelect={...} selectedCardId={...}/>`, `<AuditPanel data/>`, `<VerdictPanel data/>`, `<DiffPanel data selectedCardId onCardSelect/>`, `<ScopePanel data/>`, `<BudgetPanel data/>`, `<BlockedPanel data/>`, `<SessionTreePanel data/>`, `<ReplayPanel data/>`, `<RosterPanel data/>`. REMOVE: `ORG_TABS` (:45-56), `activeTab` (:68), tab bar (:168-181), per-tab `<Show>` (:211-248).
From apps/voss-app/src/org/selection.ts (plan 00): global `selectedCardId`/`setSelectedCardId`.
From apps/voss-app/src/org/orgStore.ts: `runData()`, `loading()`, `loadError()`, `currentRunId()`.
From apps/voss-app/src/org/panels/BoardPanel.tsx:24-30: `budgetColor(pct)` token coloring; :76 `var(--font-mono)`; :149-155 empty-state `<Show fallback>` idiom.
From apps/voss-app/src/org/types.ts: `SessionTreeNode.envelope {limit, spent}` for the gate bar.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: CockpitShell — 4-region layout, lift load/picker, remove tabs</name>
  <files>apps/voss-app/src/org/cockpit/CockpitShell.tsx, apps/voss-app/src/org/cockpit/cockpitStyles.css, apps/voss-app/src/org/OrgViewShell.tsx</files>
  <read_first>
    - apps/voss-app/src/org/OrgViewShell.tsx (the file being recomposed — lift load/picker, drop tabs)
    - apps/voss-app/src/org/selection.ts (global selection)
    - apps/voss-app/src/org/panels/BoardPanel.tsx:142-215 (Board spine props)
    - apps/voss-app/src/org/orgStyles.css (A12 token usage to mirror in cockpitStyles.css)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (CockpitShell pattern: LIFT/REMOVE/REPLACE-WITH lists; A12 token-only styling)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-01, D-02, D-08)
  </read_first>
  <action>
    Create `src/org/cockpit/CockpitShell.tsx`. LIFT verbatim from OrgViewShell: the `onMount` most-recent-run auto-load, `pickRun`/`pickerOpen` run-picker, document keydown/click cleanup, and loading/error `<Show>` wrappers. Drop the tab machinery entirely. Render a CSS-grid 4-region layout: Board spine column (`<BoardPanel data={runData()} onCardSelect={setSelectedCardId} selectedCardId={selectedCardId()} />`), a persistent `<CardDrawer />` (task 2), a timeline rail (`<SessionTreePanel data={runData()} />` + `<ReplayPanel data={runData()} />`), and a bottom `<GateBar />` (task 3). Selection comes from `src/org/selection.ts` (global). Create `cockpitStyles.css` using ONLY A12 Ignite tokens (`var(--bg-*)`, `var(--accent-*)`, `var(--font-mono)`) — no new `--xxx` custom properties. Then edit `OrgViewShell.tsx`: remove `ORG_TABS`, `activeTab`, the tab bar, and the per-tab `<Show>` switch (D-01/D-02). Make `OrgViewShell` render `<CockpitShell />` (or have App.tsx mount CockpitShell directly — pick the lower-churn path and note it in the summary). No legacy tab fallback (D-02).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -E "Cockpit|OrgView" || echo "no type errors" ; grep -rn "ORG_TABS\|activeTab" src/org/OrgViewShell.tsx && echo "FAIL tabs remain" || echo "tabs removed"</automated>
  </verify>
  <acceptance_criteria>
    - `CockpitShell.tsx` renders Board + drawer + timeline rail + gate bar, all reading global `selectedCardId`.
    - `OrgViewShell.tsx` no longer contains `ORG_TABS` or `activeTab` (grep returns nothing).
    - `cockpitStyles.css` introduces no new `--xxx` custom property (only consumes A12 tokens).
    - `npx tsc --noEmit` clean.
  </acceptance_criteria>
  <done>Tab shell removed; 4-region cockpit renders; panels reused verbatim; A12 tokens only.</done>
</task>

<task type="auto">
  <name>Task 2: CardDrawer (compose panel bodies, persistent + empty state) + GateBar</name>
  <files>apps/voss-app/src/org/cockpit/CardDrawer.tsx, apps/voss-app/src/org/cockpit/GateBar.tsx</files>
  <read_first>
    - apps/voss-app/src/org/OrgViewShell.tsx:211-248 (exact panel prop signatures to reuse in the drawer)
    - apps/voss-app/src/org/panels/BoardPanel.tsx:24-30,127-135,149-155 (budgetColor, budget bar, empty-state Show idiom)
    - apps/voss-app/src/org/types.ts (SessionTreeNode.envelope; AuditReport.unsupported_claims; per-card confidence is LIVE only, not snapshot)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (CardDrawer + GateBar patterns; D-07 pane-peek, D-08 empty state)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-07, D-08)
  </read_first>
  <action>
    Create `CardDrawer.tsx`: a persistent drawer that, when `selectedCardId()` is set, composes the existing panel bodies as sections — `<AuditPanel data/>`, `<VerdictPanel data/>`, `<DiffPanel data selectedCardId onCardSelect/>`, `<ScopePanel data/>`, `<BudgetPanel data/>`, `<BlockedPanel data/>` — reusing the EXACT prop signatures from OrgViewShell (D-02 reuse-not-rewrite). Provide a no-selection empty state (D-08) via the `<Show fallback>` idiom. Stub the D-07 read-only pane-peek region + an "Open in grid" button placeholder (the actual `orgViewOpen` flip is wired in plan 08); render the button disabled-with-reason if no bound pane. Create `GateBar.tsx`: bottom bar reflecting the selected card's `envelope {limit, spent}` with `budgetColor(pct)` thresholds (copy from BoardPanel:24-30), scope chip, and an unsupported-claims count (from `AuditReport.unsupported_claims`). Per-card confidence renders ONLY from a live overlay field, never from RunData (per-card field constraint). Monospace numerics via `var(--font-mono)`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -E "CardDrawer|GateBar" || echo "no type errors"</automated>
  </verify>
  <acceptance_criteria>
    - `CardDrawer` reuses the existing panel components verbatim (imports from `../panels/*`), shows an empty state when no card selected.
    - `GateBar` colors budget via the copied `budgetColor` thresholds and shows scope + unsupported-claims; per-card confidence is sourced only from a live field.
    - No panel internals rewritten (drawer imports panels, does not redefine them).
  </acceptance_criteria>
  <done>Drawer composes existing panels with empty state; gate bar reflects the selected card's envelope; D-02/D-07/D-08 honored.</done>
</task>

<task type="auto">
  <name>Task 3: Cockpit single-selection component test</name>
  <files>apps/voss-app/src/org/cockpit/__tests__/cockpit.test.tsx</files>
  <read_first>
    - apps/voss-app/src/org/__tests__/orgView.test.tsx (existing shell component-test style)
    - apps/voss-app/src/org/__tests__/fixtures/* (run fixtures incl. node-child.json for C1's node)
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (task 1 — the unit under test)
  </read_first>
  <action>
    Create `cockpit.test.tsx`: render `CockpitShell` with a fixture run containing card `C1`. Trigger a single selection (`setSelectedCardId('C1')` or a Board card click) and assert ALL FOUR regions respond from that one action: Board highlights `C1`, the detail drawer shows `C1` content, the timeline rail references `C1`'s node, and the gate bar reflects `C1`'s envelope. Also assert no regression marker: the test mocks Tauri `invoke` so `load_run` returns the fixture (mirror orgView.test.tsx mocking). Keep the existing V11 panel tests untouched.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/cockpit/__tests__/cockpit.test.tsx && npx vitest run src/org/__tests__</automated>
  </verify>
  <acceptance_criteria>
    - One selection action drives Board + drawer + timeline + gate bar in the test.
    - Existing `src/org/__tests__/*` (V11 panels, guards) stay green.
  </acceptance_criteria>
  <done>VCKP-05 single-selection acceptance proven; V11 tests unregressed.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org` green; `npx tsc --noEmit` clean.
- No `ORG_TABS`/`activeTab` remain in OrgViewShell.
- cockpitStyles.css adds no new theme tokens (A12 only).
- V11 panel + guards tests unregressed (D-02).
</verification>

<success_criteria>
One selection drives all four cockpit regions; tab shell removed; panels reused verbatim; A12 tokens only; grid/⌘⇧O untouched (toggle wiring lands in plan 08).
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-03-SUMMARY.md` when done. Note whether OrgViewShell wraps CockpitShell or App.tsx mounts it directly.
</output>
