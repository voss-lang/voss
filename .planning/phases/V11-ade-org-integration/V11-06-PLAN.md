---
phase: V11-ade-org-integration
plan: 06
type: execute
wave: 3
depends_on: ["01", "03"]
files_modified:
  - apps/voss-app/src/org/panels/AuditPanel.tsx
  - apps/voss-app/src/org/panels/BudgetPanel.tsx
  - apps/voss-app/src/org/panels/ScopePanel.tsx
  - apps/voss-app/src/org/__tests__/auditPanel.test.tsx
autonomous: true
requirements: [VADE-04, VADE-06, VADE-07]
must_haves:
  truths:
    - "The Audit panel renders the audit JSON sections, claims with evidence badges, and the residual-risk section"
    - "Unsupported EM claims are visibly flagged with a ⚑ glyph and a tinted row"
    - "The Budget panel shows allocation/consumption per root, per card, and per agent"
    - "The Scope panel shows scope per role and per card, flagging out-of-scope cards"
  artifacts:
    - path: "apps/voss-app/src/org/panels/AuditPanel.tsx"
      provides: "Audit sections + claims-vs-evidence + unsupported flag + residual-risk"
      contains: "RESIDUAL RISK"
    - path: "apps/voss-app/src/org/panels/BudgetPanel.tsx"
      provides: "Per-root/card/agent budget rows with consumption bars"
      contains: "Per Root"
  key_links:
    - from: "apps/voss-app/src/org/panels/AuditPanel.tsx"
      to: "RunData.audit.unsupported_claims"
      via: "flag rendering when claim node in unsupported_claims"
      pattern: "unsupported_claims"
---

<objective>
Fill the Audit (VADE-04), Budget (VADE-06), and Scope (VADE-07) panel stubs. The Audit panel renders the V9 audit JSON sections, claims-vs-evidence with the unsupported-EM-claim flag, and the residual-risk (leak6) section — the unsupported-flag behavior is fixture-tested. Budget and Scope render per root/card/agent and per role/card.

Purpose: Wave 3 (parallel) — owns only its own panel files (no shell conflict with Plans 04/05).
Output: AuditPanel.tsx, BudgetPanel.tsx, ScopePanel.tsx, auditPanel.test.tsx.
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
<!-- RunData.audit: AuditReport (VERIFIED RESEARCH.md): -->
<!--   { run_id, idea, principles[[k,t]], team_config{source,roster_ids[]}, -->
<!--     snapshot{ root_id, nodes[], cards[{node_id,column,risk_tier,...}], kills[], rescopes[], routings[], -->
<!--       verdicts[], liveness[], leak6{status,evidence,mitigation_present}, run_final|null }, -->
<!--     review_sidecars{...}, run_final|null, signoff_ack|null, calibration, -->
<!--     sections_missing:["diff_summary","tests_evals"], unsupported_claims:[<node_id>,...] } -->
<!-- Unsupported claim: a node whose id is in audit.unsupported_claims (em.ticket but no review evidence). -->
<!-- Residual risk = snapshot.leak6 {status, evidence, mitigation_present}. -->
<!-- Budget: per node envelope{limit,spent}; per-root = root node envelope; per-card = card nodes; per-agent = group by role. -->
<!-- Scope: node.scope (glob string|null) per role/card; out-of-scope flag = display indicator (data may be absent → no flag). -->
<!-- UI-SPEC Panel 4 (Audit): section header uppercase --fg-3; claim row; evidence badge supported green/partial amber/unsupported red; -->
<!--   unsupported row adds ⚑ (U+2691) --unsupported-flag + rgba(232,123,123,0.06) bg + aria-label="Unsupported claim"; RESIDUAL RISK section. -->
<!-- UI-SPEC Panel 6 (Budget): collapsible Per Root/Per Card/Per Agent; row name+alloc+4px bar(<70/70-90/>90)+pct; over-budget tint. -->
<!-- UI-SPEC Panel 7 (Scope): collapsible Per Role/Per Card; scope tag pills; ⚑ out-of-scope aria-label="Out of scope". -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: AuditPanel — sections, claims-vs-evidence, unsupported flag, residual risk + test</name>
  <files>apps/voss-app/src/org/panels/AuditPanel.tsx, apps/voss-app/src/org/__tests__/auditPanel.test.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 4: Audit" — section anatomy, claims list, unsupported flag, residual risk, empty state)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md ("voss audit --format json Output" — AuditReport fields; unsupported_claims; leak6; Pitfall 4 sections_missing — diff data does NOT exist)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md (boardPanel.test.tsx mount/fixture pattern)
    - apps/voss-app/src/org/__tests__/fixtures/audit-report.json
  </read_first>
  <action>
    Implement AuditPanel from `props.data?.audit`. Render audit sections (idea, principles, team_config, and the snapshot summary — cards/kills/rescopes/routings counts) as labeled sections (uppercase `--fg-3` headers, letter-spacing 0.08em). Render a claims-vs-evidence list: derive one claim row per node referenced in `snapshot.routings`/`cards`; an evidence badge (supported green / partial amber / unsupported red) where a node id present in `audit.unsupported_claims` is "unsupported". For unsupported rows, prepend a `⚑` (U+2691) glyph colored `--unsupported-flag` with `aria-label="Unsupported claim"` and tint the row `rgba(232,123,123,0.06)`. Render a "RESIDUAL RISK" section from `snapshot.leak6` (status + evidence + mitigation_present). Do NOT attempt to render diffs/tests_evals (Pitfall 4: always in sections_missing). Null/empty → "No audit data for this run." In auditPanel.test.tsx (`vi.mock` Tauri, import audit-report.json), mount with a RunData carrying the fixture audit → assert a section header renders, assert the unsupported-claim node row shows the ⚑ flag (query aria-label="Unsupported claim"), assert the RESIDUAL RISK section renders.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/auditPanel.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>AuditPanel renders sections + claims + the ⚑ unsupported flag + residual-risk; render test asserts the flag and residual section; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 2: BudgetPanel — per root / card / agent allocation + consumption</name>
  <files>apps/voss-app/src/org/panels/BudgetPanel.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 6: Budget" — collapsible sections, budget row, consumption bar thresholds, over-budget highlight, empty state)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/panels/BudgetPanel.tsx" → BudgetBar analog)
    - apps/voss-app/src/grid/BudgetBar.tsx (bar color thresholds + pct calc)
    - apps/voss-app/src/org/types.ts (SessionTreeNode.envelope, node.role)
  </read_first>
  <action>
    Implement BudgetPanel with three collapsible sections (default expanded): "Per Root" (the root node envelope), "Per Card" (each non-root node envelope), "Per Agent" (envelopes summed by `role`). Each section header (32px, ▾/▸ toggle, uppercase `--fg-3`) shows total allocated/consumed (mono `--fg-2`). Each 28px row: name (Inter 12px `--fg-1`), allocation (mono), a 4px consumption bar (spent/limit; <70 green / 70-90 amber / >90 red), pct used (mono). Over-budget row (spent ≥ limit) → row bg `rgba(232,123,123,0.06)`. `createSignal` for per-section collapse. Null/empty → "No budget data for this run." Reuse the BudgetBar threshold logic (extract inline; do not import the grid component which expects a different prop shape).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q "Per Root" src/org/panels/BudgetPanel.tsx && grep -q "Per Agent" src/org/panels/BudgetPanel.tsx</automated>
  </verify>
  <done>BudgetPanel renders per-root/card/agent rows with consumption bars + over-budget highlight; collapsible; empty state; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 3: ScopePanel — scope per role / per card + out-of-scope flag</name>
  <files>apps/voss-app/src/org/panels/ScopePanel.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 7: Scope" — collapsible Per Role/Per Card, scope tag pills, out-of-scope flag aria-label, empty state)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md (SessionTreeNode.scope glob field; scope from role)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("ScopePanel" → ContextPanel analog)
    - apps/voss-app/src/org/types.ts (node.scope, node.role)
  </read_first>
  <action>
    Implement ScopePanel with two collapsible sections "Per Role" (scope globs grouped by role) and "Per Card" (per non-root node scope). Each 28px row: role/card name (Inter 12px `--fg-1`), scope items as comma-or-pill tags (Inter 11px 500 `--fg-2`, 3px radius, `--bg-3` bg, 4px padding) parsed from `node.scope` (a glob string; split sensibly or show as one pill). If a card has an out-of-scope indicator available (none persists in the V2-V7 substrate — so default to no flag), render a `⚑` `--accent-red` with `aria-label="Out of scope"` only when that data exists; otherwise omit. Null/empty → "No scope data for this run." Add a brief code comment noting that out-of-scope detection has no persisted source in the current substrate (consistent with RESEARCH), so the flag is data-driven and currently inert.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q "No scope data" src/org/panels/ScopePanel.tsx && grep -q "Per Role" src/org/panels/ScopePanel.tsx</automated>
  </verify>
  <done>ScopePanel renders per-role/per-card scope tags with collapsible sections + data-driven out-of-scope flag + empty state; tsc clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| RunData.audit → render | validated typed data; read-only |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-13 | Repudiation | unsupported EM claim not flagged (audit integrity gap) | mitigate | unsupported_claims drives ⚑ flag; auditPanel test asserts flag presence (VADE-04 acceptance) |
| T-V11-14 | Denial of Service | render crash on absent leak6/scope fields | accept | optional chaining + empty states; fixtures cover absent fields |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run src/org/__tests__/auditPanel.test.tsx && npx tsc --noEmit` green.
- AuditPanel contains "RESIDUAL RISK"; BudgetPanel contains "Per Root"+"Per Agent" (grep).
</verification>

<success_criteria>
- Audit panel renders sections + unsupported-claim flag + residual-risk (VADE-04, fixture-tested).
- Budget viz per root/card/agent (VADE-06); scope viz per role/card (VADE-07).
- No new dependencies.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-06-SUMMARY.md` when done.
</output>
