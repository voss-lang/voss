---
phase: V11-ade-org-integration
plan: 05
type: execute
wave: 3
depends_on: ["01", "03"]
files_modified:
  - apps/voss-app/src/org/panels/SessionTreePanel.tsx
  - apps/voss-app/src/org/panels/VerdictPanel.tsx
  - apps/voss-app/src/org/treeBuild.ts
  - apps/voss-app/src/org/__tests__/sessionTree.test.tsx
autonomous: true
requirements: [VADE-03, VADE-05]
must_haves:
  truths:
    - "The Session-tree panel renders a navigable parent→child hierarchy with expand/collapse and node selection"
    - "Selecting a node shows its light metadata (id, role, budget-used, status, parent id)"
    - "The Verdict panel shows Reviewer-A and Reviewer-B in two visually-separated half-panes"
    - "A and B verdict labels/confidence/domain render from the .review.json sidecar data"
  artifacts:
    - path: "apps/voss-app/src/org/treeBuild.ts"
      provides: "buildTree: flat nodes[] → rooted parent→child structure"
      exports: ["buildTree"]
    - path: "apps/voss-app/src/org/panels/VerdictPanel.tsx"
      provides: "Two-column A/B verdict rendering"
      contains: "REVIEWER A"
  key_links:
    - from: "apps/voss-app/src/org/panels/SessionTreePanel.tsx"
      to: "apps/voss-app/src/org/treeBuild.ts"
      via: "buildTree(props.data.session_tree.nodes)"
      pattern: "buildTree"
---

<objective>
Fill the Session-tree (VADE-03) and Reviewer-verdict (VADE-05) panel stubs. The tree structure is built by a pure, tested `treeBuild.ts` (flat nodes → parent→child via `parent_run_id`). The Verdict panel renders Reviewer-A and Reviewer-B as two separated half-panes from the `.review.json` sidecar data.

Purpose: Wave 3 (parallel) — owns only its own panel files (no shell conflict with Plans 04/06).
Output: SessionTreePanel.tsx, VerdictPanel.tsx, treeBuild.ts, sessionTree.test.tsx.
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
<!-- RunData.session_tree.nodes: SessionTreeNode[] (id, root_id, parent_run_id|null, envelope{limit,spent}, terminal_state, role). -->
<!-- RunData.review: Record<node_id, ReviewSidecar> where ReviewSidecar = {a_verification|null, b_verdict|null, final_outcome}. -->
<!--   a_verification {result, test_path_or_rubric, notes}; b_verdict {verdict, conf, tier, domain_inferred, notes, evidence_refs[]}. -->
<!-- UI-SPEC Panel 3: tree node 28px, 16px indent/level, ▸/▾ toggle, ● leaf, status dot, cost right; selected --focus-soft + 2px --focus left bar; -->
<!--   metadata area 72px below tree. role=tree, treeitem, aria-expanded. -->
<!-- UI-SPEC Panel 5: two half-panes; REVIEWER A header --role-reviewer; REVIEWER B header --accent-magenta (distinguish sources); -->
<!--   verdict label PASS green / FAIL|BLOCK red / DEFER amber; conf + domain mono; per-half empty "No {Reviewer A/B} verdict for this run." -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: treeBuild.ts + sessionTree test</name>
  <files>apps/voss-app/src/org/treeBuild.ts, apps/voss-app/src/org/__tests__/sessionTree.test.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md ("SessionTreeNode JSON" — parent_run_id null = root; export_tree {root_id, nodes})
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/panels/SessionTreePanel.tsx" — No Analog; recursive For + indentation; "replayReducer.ts" pure discipline)
    - apps/voss-app/src/org/types.ts, fixtures node-root.json + node-child.json
  </read_first>
  <behavior>
    - buildTree(nodes) returns root nodes (parent_run_id null) each with a children[] array linked by parent_run_id
    - buildTree handles the root + one child fixture → 1 root with 1 child
    - buildTree tolerates an empty array → []; orphan nodes (unknown parent) are not lost (attached at root level)
  </behavior>
  <action>
    Implement `buildTree(nodes: SessionTreeNode[]): TreeNode[]` (TreeNode = SessionTreeNode & { children: TreeNode[] }) as a pure function: index nodes by id, attach each to its `parent_run_id` parent's children, collect parent_run_id===null (and orphans) as roots. No produce/structuredClone — build plain objects. In `sessionTree.test.tsx` (`vi.mock` Tauri), assert the 3 behaviors against fixtures. This test file also hosts the SessionTreePanel render test from Task 2 — scaffold the describe block.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/sessionTree.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>buildTree passes the hierarchy/empty/orphan behavior tests; pure; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 2: SessionTreePanel — navigable tree + node metadata</name>
  <files>apps/voss-app/src/org/panels/SessionTreePanel.tsx, apps/voss-app/src/org/__tests__/sessionTree.test.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 3: Session Tree" — node row, indent, toggle glyphs, status dot, metadata area, empty state, accessibility role=tree/treeitem)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/panels/SessionTreePanel.tsx" — recursive indentation, createSignal selected node)
    - apps/voss-app/src/org/treeBuild.ts (Task 1)
  </read_first>
  <action>
    Implement SessionTreePanel: `buildTree(props.data?.session_tree.nodes ?? [])`, render recursively with 16px indent per level. Each 28px node row: ▸/▾ expand toggle (expandable) or ● leaf dot, session id (mono 20-char ellipsis), role badge, status dot (done green / in-review amber / error|blocked red / idle `--fg-3`), cost right (mono, from envelope.spent). `createSignal` for expanded set + selected node id. Selected row → `--focus-soft` bg + 2px `--focus` left bar. Below the tree: a 72px metadata area (`--bg-1`) showing the selected node's id, role, budget-used (spent/limit), status, parent id. `role="tree"`, nodes `role="treeitem"` with `aria-expanded`. Null/empty → "No session tree data for this run." Add render assertions to sessionTree.test.tsx: mount with fixture RunData → assert the root node renders, expand reveals the child, selecting a node shows its metadata.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/sessionTree.test.tsx && npx tsc --noEmit</automated>
  </verify>
  <done>SessionTreePanel renders a navigable tree, expand/collapse + selection + metadata work; render tests green; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 3: VerdictPanel — Reviewer-A and Reviewer-B separated</name>
  <files>apps/voss-app/src/org/panels/VerdictPanel.tsx</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-UI-SPEC.md ("Panel 5: Verdict" — two half-panes, A header --role-reviewer, B header --accent-magenta, verdict label colors, conf/domain, per-half empty state)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md (".review.json Sidecar" — a_verification / b_verdict shapes; review keyed by node_id)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("VerdictPanel" → ContextPanel analog)
    - apps/voss-app/src/org/types.ts (ReviewSidecar)
  </read_first>
  <action>
    Implement VerdictPanel as two side-by-side half-panes separated by `1px solid --border`, each independently scrollable (VADE-05 acceptance: A and B visually separated). Left header "REVIEWER A" (`--role-reviewer`), right header "REVIEWER B" (`--accent-magenta`). Aggregate verdicts across `props.data.review` entries (or, if a card is selected upstream later, this panel shows all; keep it showing all review sidecars listed by node id). For each sidecar: left half renders `a_verification` (result label colored PASS green / FAIL|BLOCK red / DEFER amber, test_path_or_rubric mono, notes pre-wrap); right half renders `b_verdict` (verdict label same color rule, `conf: 0.xx` mono, `domain: <x>` mono, notes pre-wrap). When a half has no data → "No Reviewer A verdict for this run." / "No Reviewer B verdict for this run." Use only CSS-var colors. Section labels uppercase letter-spacing 0.08em.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q "REVIEWER A" src/org/panels/VerdictPanel.tsx && grep -q "REVIEWER B" src/org/panels/VerdictPanel.tsx</automated>
  </verify>
  <done>VerdictPanel renders A and B in separate half-panes with distinct header colors + verdict/conf/domain from sidecars; per-half empty states; tsc clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| RunData → render | validated typed data; read-only panels |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-11 | Denial of Service | cyclic/orphan parent_run_id → infinite tree recursion | mitigate | buildTree indexes by id and attaches once; orphans go to root; no node visited twice; test covers orphan case |
| T-V11-12 | Information Disclosure | A/B verdicts rendered into the same pane (spec violation) | mitigate | two distinct half-panes with distinct header colors (VADE-05); grep asserts both headers present |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run src/org/__tests__/sessionTree.test.tsx && npx tsc --noEmit` green.
- VerdictPanel contains both "REVIEWER A" and "REVIEWER B" (grep).
</verification>

<success_criteria>
- Session-tree panel navigable (expand/collapse + select + metadata) (VADE-03).
- Reviewer A and B visually separated (VADE-05).
- treeBuild fixture-tested; no new dependencies.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-05-SUMMARY.md` when done.
</output>
