---
phase: V11-ade-org-integration
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - apps/voss-app/src/org/types.ts
  - apps/voss-app/src/org/guards.ts
  - apps/voss-app/src/org/replayReducer.ts
  - apps/voss-app/src/org/__tests__/guards.test.ts
  - apps/voss-app/src/org/__tests__/replayReducer.test.ts
  - apps/voss-app/src/org/__tests__/fixtures/node-root.json
  - apps/voss-app/src/org/__tests__/fixtures/node-child.json
  - apps/voss-app/src/org/__tests__/fixtures/review-sidecar.json
  - apps/voss-app/src/org/__tests__/fixtures/run-final.json
  - apps/voss-app/src/org/__tests__/fixtures/audit-report.json
autonomous: true
requirements: [VADE-02, VADE-10]
must_haves:
  truths:
    - "Hand-authored TS contract types exist for every CLI-JSON shape V11 consumes, with a V13.1-REPLACE marker"
    - "A runtime validation guard rejects malformed RunData at the Tauri boundary with an explicit error"
    - "A pure replay reducer reconstructs board/card state at any step N from transitions[]"
    - "Golden JSON fixtures captured from the verified V4-V9 schemas drive reducer + guard tests"
  artifacts:
    - path: "apps/voss-app/src/org/types.ts"
      provides: "RunData + all sub-type interfaces (D-02)"
      contains: "V13.1-REPLACE"
    - path: "apps/voss-app/src/org/guards.ts"
      provides: "Runtime validation of load_run output"
      exports: ["isRunData", "assertRunData"]
    - path: "apps/voss-app/src/org/replayReducer.ts"
      provides: "computeBoardAtStep pure reducer (D-05/D-06)"
      exports: ["computeBoardAtStep"]
    - path: "apps/voss-app/src/org/__tests__/fixtures/node-child.json"
      provides: "Golden child node with board.transition entries"
      contains: "board.transition"
  key_links:
    - from: "apps/voss-app/src/org/replayReducer.ts"
      to: "apps/voss-app/src/org/types.ts"
      via: "import type SessionTreeNode, BoardFrame, CardSnapshot"
      pattern: "import type.*types"
    - from: "apps/voss-app/src/org/__tests__/replayReducer.test.ts"
      to: "apps/voss-app/src/org/replayReducer.ts"
      via: "computeBoardAtStep called with fixture nodes"
      pattern: "computeBoardAtStep"
---

<objective>
Establish the V11 contract foundation: hand-authored TS types for every CLI-JSON shape (D-02), a runtime validation guard at the Tauri boundary (drift → explicit error), the pure client-side replay reducer (D-05/D-06), and golden JSON fixtures authored from the RESEARCH-verified schemas. Everything downstream (Rust commands, store, panels) imports these types; the reducer powers VADE-10.

Purpose: Wave 0 — defines the contracts the rest of the phase builds against, and closes the VALIDATION.md Wave 0 fixture/type/reducer gaps so panel tests are fixture-driven from day one.
Output: `src/org/types.ts`, `src/org/guards.ts`, `src/org/replayReducer.ts`, 5 golden fixtures, 2 test files.
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
@.planning/phases/V11-ade-org-integration/V11-RESEARCH.md
@.planning/phases/V11-ade-org-integration/V11-PATTERNS.md
@.planning/phases/V11-ade-org-integration/V11-VALIDATION.md

<interfaces>
<!-- VERIFIED upstream JSON contracts (RESEARCH.md "Upstream JSON Contracts"). -->
<!-- These shapes are authoritative; types.ts must match them exactly. -->

SessionTreeNode (<root_id>/<node_id>.json):
  id, root_id, parent_run_id (string|null),
  envelope { limit, spent },
  terminal_state { exit_reason: "done"|"timeout"|"killed"|"error", final } | null,
  created_at, ended_at (string|null),
  transitions[] (union of board.transition | em.ticket | em.routing | em.kill | em.rescope | em.run_final),
  scope (string|null), role (string|null)

board.transition: { kind:"board.transition", from, to, outcome,
  verdict_snapshot { conf, source:"A"|"B", tier, verdict:"pass"|"fail"|"block",
    notes, evidence_refs[], domain_inferred } | null }
em.ticket: { kind:"em.ticket", risk_tier:"low"|"med"|"high", ... }
em.routing: { kind:"em.routing", id, card_id, chosen_role, candidates_considered[], rationale_text, ts }
em.kill: { kind:"em.kill", killed_node_id, rationale_text, evidence_refs[], killed_at }
em.rescope: { kind:"em.rescope", predecessor_card_id, successor_card_id, diff_summary, rationale_text, rescoped_at }

RunFinal (run-final.json): { root_id, idea, total_cards, done_count, blocked_count,
  killed_count, rescope_count, em_iterations, ts, kind:"em.run_final",
  sign_off { decision:"approve"|"reject", ts } | absent }

ReviewSidecar (<node_id>.review.json): { a_verification { result, test_path_or_rubric, notes }|null,
  b_verdict { verdict, conf, tier, domain_inferred, notes, evidence_refs[] }|null,
  final_outcome:"pass"|"fail"|"block"|"?" }

AuditReport (voss audit --format json): { run_id, idea, principles[[k,t]], team_config{source,roster_ids[]},
  snapshot{ root_id, nodes[], cards[{node_id,column,risk_tier,retry_count,is_killed}], kills[], rescopes[],
    routings[], verdicts[], liveness[], leak6{status,evidence,mitigation_present}, run_final|null },
  review_sidecars{ <node_id>: ReviewSidecar }, run_final|null, signoff_ack|null, calibration,
  sections_missing:["diff_summary","tests_evals"], unsupported_claims[<node_id>] }

Canonical 6 board columns: Backlog, Planned, InProgress, InReview, Blocked, Done.
Column derivation: walk board.transition in order (last .to wins, default Backlog),
  then terminal_state.exit_reason override (timeout/killed → Blocked, done → Done).
Risk derivation: first em.ticket.risk_tier, default "med".
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author golden JSON fixtures from verified schemas</name>
  <files>apps/voss-app/src/org/__tests__/fixtures/node-root.json, apps/voss-app/src/org/__tests__/fixtures/node-child.json, apps/voss-app/src/org/__tests__/fixtures/review-sidecar.json, apps/voss-app/src/org/__tests__/fixtures/run-final.json, apps/voss-app/src/org/__tests__/fixtures/audit-report.json</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md ("Upstream JSON Contracts" sections 1-7 — exact field shapes)
    - .planning/phases/V11-ade-org-integration/V11-VALIDATION.md ("Fixture Strategy" — which fixture drives which requirement)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("No Analog Found" — fixtures authored from RESEARCH contracts; no real .voss/sessions subdirs exist in dev env)
  </read_first>
  <action>
    Create 5 golden JSON fixtures matching the VERIFIED schemas in the interfaces block. `node-root.json`: a root SessionTreeNode (parent_run_id null, role null/"user", envelope limit 500000 spent ~30000, an em.ticket transition with risk_tier "med", an em.routing transition). `node-child.json`: a child node (parent_run_id = root id, role "backend", an em.ticket risk_tier "high", then a sequence of board.transition entries Backlog→Planned→InProgress→InReview→Done with verdict_snapshot on the InReview→Done one). Author transitions so the reducer test has deterministic step counts. `review-sidecar.json`: one ReviewSidecar with both a_verification (result "pass", test_path_or_rubric "tests/foo_test.py") and b_verdict (verdict "pass", conf 0.84, domain_inferred "code"), final_outcome "pass". `run-final.json`: a RunFinal (total_cards 3, done_count 2, blocked_count 1, with a sign_off). `audit-report.json`: an AuditReport with snapshot.cards (3 cards incl one column "Blocked"), sections_missing ["diff_summary","tests_evals"], unsupported_claims with one node_id, a leak6 residual-risk object, review_sidecars keyed by node_id. Keep ids as 12-char hex strings. These are the authoritative test corpus for all downstream panel tests.
  </action>
  <verify>
    <automated>cd apps/voss-app && node -e "['node-root','node-child','review-sidecar','run-final','audit-report'].forEach(f=>{const j=require('./src/org/__tests__/fixtures/'+f+'.json');if(!j)throw new Error(f)})" && grep -q '"board.transition"' src/org/__tests__/fixtures/node-child.json && grep -q 'diff_summary' src/org/__tests__/fixtures/audit-report.json</automated>
  </verify>
  <done>All 5 fixtures are valid JSON, node-child.json contains board.transition entries, audit-report.json contains sections_missing with diff_summary.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Author types.ts + runtime guards with parse-failure test</name>
  <files>apps/voss-app/src/org/types.ts, apps/voss-app/src/org/guards.ts, apps/voss-app/src/org/__tests__/guards.test.ts</files>
  <read_first>
    - apps/voss-app/src/swarm/swarmTypes.ts (analog: pure type/interface file, no imports, no logic)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/types.ts" section — V13.1 marker text + interface list)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md ("Upstream JSON Contracts" — field shapes for every interface)
    - apps/voss-app/src/grid/__tests__/a6-acceptance.test.tsx (vi.mock Tauri pattern)
  </read_first>
  <behavior>
    - isRunData(obj) returns true for the assembled fixture RunData
    - isRunData(obj) returns false when run_id is missing or session_tree.nodes is not an array
    - assertRunData throws an Error with a message naming the missing/wrong field when given malformed input (D-02: drift surfaces as explicit error, not silent render miss)
  </behavior>
  <action>
    In `types.ts`: put the exact marker `// V13.1-REPLACE: hand-authored stopgap — replace with codegen contract snapshot when Phase V13.1 TypeScript Local Client SDK lands.` at the top (per D-02 + PATTERNS). Define pure interfaces matching the interfaces block: `SessionTreeNode`, `BoardTransition` (discriminated union on `kind`: `board.transition`|`em.ticket`|`em.routing`|`em.kill`|`em.rescope`|`em.run_final`), `VerdictSnapshot`, `RunFinal`, `ReviewSidecar`, `AVerification`, `BVerdict`, `AuditReport`, `AuditSnapshot`, `AuditCard`, `RunEntry` (run_id, mtime_secs, has_run_final), `DecisionResult` (success, stdout, stderr, exit_code), and the aggregate `RunData` (run_id, session_tree {root_id, nodes: SessionTreeNode[]}, review: Record<string,ReviewSidecar>, audit: AuditReport|null, run_final: RunFinal|null). Also define `BoardFrame` (columns: Record<string,CardSnapshot[]>, step, eventLabel) and `CardSnapshot` (id, role, risk, status, budget) for the reducer. No `produce`/store imports; no side effects. In `guards.ts`: export `isRunData(o: unknown): o is RunData` (structural checks: run_id is string, session_tree.nodes is array) and `assertRunData(o: unknown): RunData` (throws `Error` naming the failing field). This guard is the boundary D-02 requires. In `guards.test.ts`: write the 3 behavior tests above using the fixtures from Task 1 to assemble a valid RunData and deliberately-broken variants.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/guards.test.ts && npx tsc --noEmit</automated>
  </verify>
  <done>types.ts compiles with the V13.1-REPLACE marker present; guards.test.ts passes including the parse-failure (drift→error) assertion; tsc --noEmit clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Author replayReducer.ts (pure board/card reconstruction) + tests</name>
  <files>apps/voss-app/src/org/replayReducer.ts, apps/voss-app/src/org/__tests__/replayReducer.test.ts</files>
  <read_first>
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/replayReducer.ts" section — pure-function pattern, no produce/structuredClone)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md ("Pattern 4: Replay Reducer" + Pitfall 3 produce/proxy caveat + column/risk derivation)
    - apps/voss-app/src/grid/tree.ts (analog: pure utility functions)
    - apps/voss-app/src/grid/__tests__/a6-acceptance.test.tsx (vi.mock + describe-per-requirement pattern)
  </read_first>
  <behavior>
    - computeBoardAtStep(nodes, 0) places all cards in Backlog (or the column implied by the 0th transition); columns object always has all 6 canonical keys
    - computeBoardAtStep advances a card to InProgress at the step where its Backlog→...→InProgress board.transition occurs
    - At the final step, a card whose node has terminal_state.exit_reason "done" is in Done; "killed"/"timeout" → Blocked
    - The returned BoardFrame.eventLabel describes the transition at the current step
    - Reducer never mutates input nodes and returns plain object literals (no produce drafts, no structuredClone)
  </behavior>
  <action>
    Implement `computeBoardAtStep(nodes: SessionTreeNode[], step: number): BoardFrame` per D-05/D-06 (board/card state only). Collect all `board.transition` entries across all nodes into a single ordered list (preserve node-then-transition order); slice to `step+1`; fold into a `columns` record initialized with all 6 canonical keys (Backlog, Planned, InProgress, InReview, Blocked, Done) as empty arrays. For each applied transition, remove the card from its `from` column and add a `CardSnapshot` to its `to` column. Derive risk from the node's first `em.ticket.risk_tier` (default "med"); derive role from node.role. Apply `terminal_state.exit_reason` override only when `step` reaches the end of that node's transitions (done→Done, timeout/killed→Blocked). MUST use plain object spreads and `JSON.parse(JSON.stringify(...))` for any deep clone — NEVER `produce()` or `structuredClone()` (Pitfall 3: DATA_CLONE_ERR). Set `eventLabel` from the current transition (e.g. `"<card-id> → InProgress"`). In the test file, `vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))` at top, import the Task-1 fixtures, and assert the behaviors above against deterministic fixture step counts.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/replayReducer.test.ts && npx tsc --noEmit</automated>
  </verify>
  <done>replayReducer.test.ts passes all behavior assertions; reducer uses no produce/structuredClone (grep confirms); tsc --noEmit clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI-JSON → app (deserialized via invoke) | `load_run` returns JSON deserialized to plain JS; types are assumed but unverified until guards run |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-01 | Tampering | types.ts contract vs real CLI JSON drift | mitigate | guards.ts `assertRunData` rejects malformed RunData with explicit error (D-02); parse-failure test enforces it |
| T-V11-02 | Denial of Service | replayReducer on malformed/huge transitions[] | accept | reducer is pure + bounded by transitions count; fixtures cover empty/missing cases; no recursion |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages introduced this plan (RESEARCH Package Legitimacy Audit: empty) — nothing to install |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run src/org/__tests__/ && npx tsc --noEmit` green.
- types.ts contains the V13.1-REPLACE marker (grep).
- replayReducer.ts contains no `produce(` and no `structuredClone(` (grep -v '^//' | grep -c).
</verification>

<success_criteria>
- All 5 golden fixtures valid and schema-faithful.
- types.ts + guards.ts compile; drift surfaces as an explicit error (parse-failure test green).
- Pure replay reducer reconstructs board/card state at step N for VADE-10; tests green.
- No new dependencies.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-01-SUMMARY.md` when done.
</output>
