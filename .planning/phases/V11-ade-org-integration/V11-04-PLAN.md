---
phase: V11-ade-org-integration
plan: 04
type: execute
wave: 3
depends_on: ["01", "03"]
files_modified:
  - apps/voss-app/src/org/panels/RosterPanel.tsx
  - apps/voss-app/src/org/panels/BoardPanel.tsx
  - apps/voss-app/src/org/boardDerive.ts
  - apps/voss-app/src/org/__tests__/boardPanel.test.tsx
autonomous: true
requirements: [VADE-01, VADE-02]
must_haves:
  truths:
    - "The Roster panel renders team roles/agents with role-color dots and status badges from RunData"
    - "The Board panel renders the canonical 6 columns with cards showing id/title/role/risk/budget"
    - "Each card's column + risk are derived per the verified harness algorithm (last board.transition, terminal override; first em.ticket risk)"
    - "Clicking a card selects it (focus ring) and reports the card id to the shell"
  artifacts:
    - path: "apps/voss-app/src/org/boardDerive.ts"
      provides: "deriveColumn / deriveRisk / cardsFromRunData pure helpers"
      exports: ["cardsFromRunData", "deriveColumn", "deriveRisk"]
    - path: "apps/voss-app/src/org/panels/BoardPanel.tsx"
      provides: "6-column Kanban rendering with risk-tinted cards + budget micro-bar"
      contains: "Backlog"
  key_links:
    - from: "apps/voss-app/src/org/panels/BoardPanel.tsx"
      to: "apps/voss-app/src/org/boardDerive.ts"
      via: "cardsFromRunData(props.data)"
      pattern: "cardsFromRunData"
---

<objective>
Fill the Roster (VADE-01) and Board (VADE-02) panel stubs. Board derivation (column + risk) is extracted into a pure, tested `boardDerive.ts` so the 6-column algorithm is verified against fixtures, mirroring the harness `cli_view._derive_column/_derive_risk` logic exactly.

Purpose: Wave 3 (parallel) — first structural panels; owns only its own panel files (no shell conflict).
Output: RosterPanel.tsx, BoardPanel.tsx, boardDerive.ts, boardPanel.test.tsx.
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
@.planning/phases/V11-ade-org-integration/V11-03-SUMMARY.md

<interfaces>
<!-- Panel contract: export default function XPanel(props: { data: RunData | null; onCardSelect?; selectedCardId? }) -->
<!-- RunData.session_tree.nodes: SessionTreeNode[]; RunData.run_final: RunFinal|null; RunData.audit: AuditReport|null -->
<!-- Column derivation (VERIFIED, RESEARCH.md): walk board.transition in order, last .to wins (default Backlog), -->
<!--   then terminal_state.exit_reason override (timeout/killed → Blocked, done → Done). -->
<!-- Risk derivation: first em.ticket.risk_tier, default "med". -->
<!-- 6 canonical columns: Backlog, Planned, InProgress, InReview, Blocked, Done. UI order: Backlog/Todo/In Progress/In Review/Done/Blocked -->
<!--   (column header DISPLAY names per UI-SPEC; "Planned" harness value maps to --org-col-todo). -->
<!-- Budget per node: envelope { limit, spent }. Roster source: audit.team_config.roster_ids + node roles. -->
<!-- Card colors: risk tint --card-risk-{low,med,high}; budget bar --accent-green<70 --accent-amber 70-90 --accent-red>90; selected 1px --focus. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: boardDerive.ts pure helpers + boardPanel test scaffold</name>
  <files>apps/voss-app/src/org/boardDerive.ts, apps/voss-app/src/org/__tests__/boardPanel.test.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md ("Column derivation" + "Risk derivation" verified algorithms; "Board Column Mapping" — Planned↔Todo label note + A3 assumption)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/__tests__/boardPanel.test.tsx" mount/fixture pattern; "src/org/replayReducer.ts" pure-function discipline)
    - apps/voss-app/src/org/types.ts, apps/voss-app/src/org/__tests__/fixtures/node-child.json (transitions to derive against)
  </read_first>
  <behavior>
    - deriveColumn(node) returns the last board.transition.to; with terminal_state.exit_reason "done" → "Done", "killed"/"timeout" → "Blocked"; no transitions → "Backlog"
    - deriveRisk(node) returns the first em.ticket.risk_tier; "med" when absent
    - cardsFromRunData(data) returns one card per non-root node with {id, title, role, risk, column, spent, limit}; tolerates data===null → []
  </behavior>
  <action>
    Implement `boardDerive.ts` as pure functions (no Solid imports): `deriveColumn(node: SessionTreeNode): string` and `deriveRisk(node: SessionTreeNode): string` matching the VERIFIED harness algorithm exactly, and `cardsFromRunData(data: RunData | null): BoardCard[]` (define a local `BoardCard` interface or reuse CardSnapshot from types). Use plain object literals; no produce/structuredClone. In `boardPanel.test.tsx`: `vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))`, import fixtures, assemble a `FIXTURE_RUN_DATA: RunData`, and assert the 3 behaviors above. This file also hosts the BoardPanel render test added in Task 2 — scaffold its describe block now (it may start with the derivation assertions and gain render assertions in Task 2).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/boardPanel.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>boardDerive helpers pass the column/risk/cards behavior tests against fixtures; null-tolerant; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 2: BoardPanel — 6 columns, risk-tinted cards, budget bar, selection</name>
  <files>apps/voss-app/src/org/panels/BoardPanel.tsx, apps/voss-app/src/org/__tests__/boardPanel.test.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 2: Board" — column header, card anatomy, risk badge, budget micro-bar, selected card, empty column/state copy)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/panels/BoardPanel.tsx" — column For loop, budget color thresholds, risk tint)
    - apps/voss-app/src/grid/BudgetBar.tsx (budget bar color thresholds <70/70-90/>90)
    - apps/voss-app/src/org/boardDerive.ts (Task 1)
  </read_first>
  <action>
    Implement BoardPanel: horizontal flex of the 6 columns in UI order (display headers Backlog/Todo/In Progress/In Review/Done/Blocked, each colored via `--org-col-*`, with `(N)` count). Render `cardsFromRunData(props.data)` grouped by derived column. Card (min 64px, `--bg-2` + risk tint, `1px solid --border`, no border-radius): card id (mono `--fg-3`), title (Inter 12px 2-line clamp), role pill, risk badge, budget micro-bar (4px, thresholds <70 green / 70-90 amber / >90 red from spent/limit). Selected card (`selectedCardId` prop match) → `1px solid --focus` + box-shadow. Click calls `props.onCardSelect?.(card.id)`. Empty column → "No cards"; null data → "No board data for this run." per Copywriting Contract. Card `role="listitem"` inside `role="list"` columns (UI-SPEC Accessibility; cards are display divs, not buttons). Add render assertions to boardPanel.test.tsx: mount with FIXTURE_RUN_DATA → assert 6 column headers present, assert a card appears in its derived column, assert clicking a card fires onCardSelect with the card id.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/boardPanel.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>BoardPanel renders 6 columns + cards from fixtures; selection fires onCardSelect; budget/risk styling via tokens; render tests green; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 3: RosterPanel — roles, role-color dots, status badges</name>
  <files>apps/voss-app/src/org/panels/RosterPanel.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 1: Roster" — row anatomy, role-color dot, status badges, section header, empty state)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/panels/RosterPanel.tsx" → AgentSidebar analog)
    - apps/voss-app/src/components/sidebar/AgentSidebar.tsx (row + badge analog)
    - apps/voss-app/src/org/types.ts (RunData.audit.team_config.roster_ids + node roles)
  </read_first>
  <action>
    Implement RosterPanel: derive roster rows from `props.data.audit?.team_config.roster_ids` plus distinct `role` values across `session_tree.nodes` (dedupe). Each 36px row: role-color dot (7px, `--role-*` by role), role label (Inter 11px 500 uppercase `--fg-1`), agent/model (mono `--fg-2`), right status badge (active/idle/done pill per UI-SPEC colors — derive status from node terminal_state: finalized done → done, no terminal → active, else idle). Section header "ROSTER" uppercase `--fg-3` letter-spacing 0.08em. Null/empty → "No roster data for this run." Use only CSS-var colors. Map known role keys to `--role-planner/executor/reviewer/watcher/user`; unknown roles fall back to `--role-executor`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q "No roster data" src/org/panels/RosterPanel.tsx</automated>
  </verify>
  <done>RosterPanel renders role rows with role-color dots + status badges from RunData; empty state present; tsc clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| RunData → render | already-validated typed data (guard ran in orgStore); panels are read-only |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-09 | Tampering | board column misderivation hides Blocked cards | mitigate | boardDerive matches verified harness algorithm; fixture test asserts terminal override → Blocked/Done |
| T-V11-10 | Denial of Service | render crash on missing audit/role fields | accept | panels null-tolerant (optional chaining + empty-state); fixtures cover absent fields |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run src/org/__tests__/boardPanel.test.tsx && npx tsc --noEmit` green.
- BoardPanel renders all 6 columns (grep "Backlog" + render test).
</verification>

<success_criteria>
- Roster + Board panels render correct data for a persisted run (VADE-01/02).
- Board shows the 6 columns; column/risk derivation matches the harness (fixture-tested).
- Card selection wired to the shell; no new dependencies.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-04-SUMMARY.md` when done.
</output>
