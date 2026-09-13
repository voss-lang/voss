---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 00
type: execute
wave: 0
depends_on: []
files_modified:
  - apps/voss-app/src/org/model/normalized.ts
  - apps/voss-app/src/org/selection.ts
  - apps/voss-app/src/org/__tests__/fixtures/live-registry.json
  - apps/voss-app/src/org/__tests__/fixtures/bridge-binding.json
  - apps/voss-app/src/org/live/__tests__/mockSseStream.ts
  - apps/voss-app/src/org/model/__tests__/adapters.test.ts
  - apps/voss-app/src/org/model/__tests__/bridge.test.ts
  - apps/voss-app/src/org/live/__tests__/sseClient.test.ts
  - apps/voss-app/src/org/__tests__/keystone-a1.test.ts
autonomous: true
requirements: [VCKP-01, VCKP-02, VCKP-06]
must_haves:
  truths:
    - "A1 keystone is verified: the native create-response id, the harness sessionID, and the SessionTreeNode.id relationship is confirmed against a real or fixture .voss/sessions tree before any binding work"
    - "Normalized-model type stubs exist (Run/Card/Agent/SessionNode/Evidence/Decision) extending types.ts without editing RunData"
    - "Selection store skeleton exists as module-level Solid signals"
    - "Test scaffolds and fixtures (golden snapshot + fake live registry + binding fixture + mock SSE stream) exist and are referenced by failing/red placeholder tests"
  artifacts:
    - path: "apps/voss-app/src/org/model/normalized.ts"
      provides: "Normalized UI model type stubs"
      contains: "export interface Card"
    - path: "apps/voss-app/src/org/selection.ts"
      provides: "Global selection signals"
      contains: "selectedCardId"
    - path: "apps/voss-app/src/org/__tests__/keystone-a1.test.ts"
      provides: "A1 id-equivalence verification"
    - path: "apps/voss-app/src/org/live/__tests__/mockSseStream.ts"
      provides: "Mock SSE stream helper for VCKP-06 tests"
  key_links:
    - from: "apps/voss-app/src/org/model/normalized.ts"
      to: "apps/voss-app/src/org/types.ts"
      via: "type import / extension"
      pattern: "from.*['\"].*types['\"]"
---

<objective>
Wave 0 scaffold for V14. Lay down the normalized-model type stubs, the selection-store skeleton, all test fixtures (golden snapshot reuse + fake live registry + card↔pane↔node binding + mock SSE stream), and — critically — the A1 keystone verification that confirms how a native create-response id relates to the harness `sessionID` and the snapshot `SessionTreeNode.id`. The binding wave (VCKP-02, plan 02) MUST NOT start until A1 is resolved, because the bridge mechanism depends on which ids actually equal each other.

Purpose: De-risk the keystone (the make-or-break id-bridge) and create the test surface every downstream plan writes against. Nyquist: this plan creates the missing test files so later tasks have an `<automated>` target.
Output: `normalized.ts` stubs, `selection.ts`, fixtures, mock SSE helper, A1 verification test, and red placeholder tests for adapters/bridge/sse.
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
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md
@.planning/PROTOCOL.md

<interfaces>
From apps/voss-app/src/org/types.ts: `RunData`, `CardSnapshot`, `SessionTreeNode` (has `id`, `parent_run_id`, `role`, `scope`, `envelope{limit,spent}`), `AuditReport` (`unsupported_claims`), `RunFinal` (`sign_off`), `BoardFrame`. NO `Agent` type today; `CardSnapshot` has no `paneId`/`sessionNodeId`.
From crates/voss-app-core/src/agent_registry.rs (serialized camelCase): `AgentEntry { paneId, sessionId, cliBinary, cliArgs, cwd, status, lastSeen }`. PK is `pane_id`; `session_id` is app-supplied.
From sdk/typescript/src/client/sse.ts: `export type AgentEvent = components["schemas"]["EventEnvelope"]["event"]`; `export async function* subscribeToEvents(baseUrl, sessionId, token, signal): AsyncIterable<AgentEvent>`.
PROTOCOL §6 SSE union: `permission.updated`, `budget.updated`, `confidence.updated`, `gate.updated`, `session.idle`, `probable` — each carries `sessionID`. PROTOCOL §10/§11: `POST /session` mints `sessionID = uuid4().hex[:12]`, persists `.voss/sessions/<id>.json`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Normalized-model stubs + selection store skeleton</name>
  <files>apps/voss-app/src/org/model/normalized.ts, apps/voss-app/src/org/selection.ts</files>
  <read_first>
    - apps/voss-app/src/org/types.ts (the model being extended — DO NOT edit it; import from it)
    - apps/voss-app/src/org/orgStore.ts:11-20 (module-level `createSignal` global-signal pattern to mirror in selection.ts)
    - apps/voss-app/src/org/boardDerive.ts:1-3 (pure-module header convention)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md (Unified data model sketch + Keystone "What must be BUILT" items 1-2)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (selection.ts and normalized.ts pattern assignments)
  </read_first>
  <action>
    Create `src/org/model/normalized.ts` (pure type module, no Solid imports) declaring `Run`, `Card`, `Agent`, `SessionNode`, `Evidence`, `Decision` per the RESEARCH §4 sketch. `Card` extends the snapshot fields with optional live-overlay fields: `paneId?`, `sessionNodeId?`, `liveBudget?`, `liveStatus?`, plus existing snapshot fields (id, title, column, role, risk, scope, budget). `Agent` carries `id, role, provider, model, status, cardId?, sessionNodeId?, paneId?, budget{spent,limit}, permissionMode, capabilityTier?`. Import `RunData`/`SessionTreeNode` from `../types` — do NOT edit `types.ts` or `guards.ts` (D-02 contract; Pitfall 2). Per D-13, add a `CapabilityTier = 'A' | 'B' | 'C'` type for VCKP-13 tier on `Agent`.
    Create `src/org/selection.ts` mirroring `orgStore.ts` exactly: module-level `export const [selectedCardId, setSelectedCardId] = createSignal<string | null>(null)` and `export const [selectedRunId, setSelectedRunId] = createSignal<string | null>(null)`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -E "normalized.ts|selection.ts" || echo "no type errors in new files"</automated>
  </verify>
  <acceptance_criteria>
    - `normalized.ts` exports `Card`, `Agent`, `SessionNode`, `Run`, `Evidence`, `Decision`, `CapabilityTier`; `Card` has optional `paneId`/`sessionNodeId`; no edits to `types.ts`/`guards.ts`.
    - `selection.ts` exports `selectedCardId`/`setSelectedCardId`/`selectedRunId`/`setSelectedRunId` as module-level signals.
    - `npx tsc --noEmit` reports no new errors from these two files.
  </acceptance_criteria>
  <done>normalized.ts + selection.ts exist, typecheck clean, RunData/guards untouched.</done>
</task>

<task type="auto">
  <name>Task 2: A1 keystone verification + fixtures</name>
  <files>apps/voss-app/src/org/__tests__/keystone-a1.test.ts, apps/voss-app/src/org/__tests__/fixtures/live-registry.json, apps/voss-app/src/org/__tests__/fixtures/bridge-binding.json</files>
  <read_first>
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md (Keystone section, Assumptions Log A1, Open Questions 1)
    - .planning/PROTOCOL.md §6/§10/§11 (sessionID minting + .voss/sessions/<id>.json persistence)
    - apps/voss-app/src/org/__tests__/fixtures/node-root.json, node-child.json (existing snapshot node fixtures — SessionTreeNode.id is the filename stem)
    - apps/voss-app/src-tauri/src/lib.rs:1078-1119 (load_run reads <run_id>/<node>.json per node; node.id = filename stem)
    - crates/voss-app-core/src/agent_registry.rs:23-31 (AgentEntry shape for the fake live-registry fixture)
  </read_first>
  <action>
    Create `fixtures/live-registry.json` — a fake `AgentEntry[]` (camelCase) with at least one agent bound to pane `P1` (the live-plane payload for adapter/bridge tests). Create `fixtures/bridge-binding.json` — a fixture binding card `C1` ↔ pane `P1` ↔ node `N1` (the canonical keystone case from the acceptance criteria).
    Create `keystone-a1.test.ts` resolving RESEARCH Open-Q1/A1: inspect a real `.voss/sessions` tree if present under the repo (glob `**/.voss/sessions/*/`), else fall back to the existing snapshot node fixtures. Assert and DOCUMENT (via test description + an exported `A1_FINDING` constant string) the relationship between: (a) the run-directory name, (b) a node filename stem (`SessionTreeNode.id`), and (c) the PROTOCOL §11 `sessionID` format `uuid4().hex[:12]` (12-hex). The test must assert which id a native create-response equals — pinning the bridge convention: if create-response `id` === node `id`, Bridge A stores it directly into `cardToSessionNode`; if they differ, record that a second lookup is needed. This finding gates plan 02.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/keystone-a1.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - `keystone-a1.test.ts` passes and exports an `A1_FINDING` string stating the create-response-id ↔ node-id relationship (equal, or needs-second-lookup).
    - `fixtures/live-registry.json` parses as `AgentEntry[]` with an agent on pane `P1`.
    - `fixtures/bridge-binding.json` encodes card `C1` ↔ pane `P1` ↔ node `N1`.
    - The test asserts the 12-hex `sessionID` format from PROTOCOL §11.
  </acceptance_criteria>
  <done>A1 relationship is verified and documented in a passing test; binding fixtures exist; plan 02 can proceed knowing which bridge applies.</done>
</task>

<task type="auto">
  <name>Task 3: Red placeholder tests + mock SSE stream helper</name>
  <files>apps/voss-app/src/org/live/__tests__/mockSseStream.ts, apps/voss-app/src/org/model/__tests__/adapters.test.ts, apps/voss-app/src/org/model/__tests__/bridge.test.ts, apps/voss-app/src/org/live/__tests__/sseClient.test.ts</files>
  <read_first>
    - sdk/typescript/src/client/sse.ts (subscribeToEvents async-generator signature + AgentEvent type to mock)
    - apps/voss-app/src/org/boardDerive.ts:44-58 (cardsFromRunData — the spine the adapter test will assert against)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md (Validation Architecture → Wave 0 Gaps; Code Examples resolveCard contract)
    - apps/voss-app/src/org/__tests__/guards.test.ts (existing vitest test style to mirror)
  </read_first>
  <action>
    Create `mockSseStream.ts` — an async-generator helper yielding a scripted sequence of `AgentEvent` objects (a `budget.updated` and a `gate.updated`, each carrying a `sessionID`), shaped exactly like the SDK's `AgentEvent` union, so VCKP-06 tests can drive the cockpit without a real `voss serve` (Pitfall 4).
    Create three placeholder test files referencing the modules that downstream plans will build: `adapters.test.ts` (imports `buildModel` from `../adapters` — expects merged model carrying snapshot + overlay fields, VCKP-01), `bridge.test.ts` (imports `resolveCard` from `../bridge` — expects `resolveCard(maps,'C1') → {paneId:'P1', sessionNodeId:'N1'}` per the binding fixture, VCKP-02), `sseClient.test.ts` (imports the wrapper from `../../live/sseClient` — drives `mockSseStream` and expects a `live` label, VCKP-06). Mark the not-yet-implemented assertions with `it.todo` / `it.skip` so the suite is GREEN now but the test bodies and fixtures are ready (no false-green: the skipped tests name the exact expected behavior; downstream plans flip skip→active).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/live/__tests__/mockSseStream.ts src/org/model/__tests__ src/org/live/__tests__/sseClient.test.ts 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `mockSseStream.ts` is an async-generator yielding ≥2 typed `AgentEvent`s with `sessionID` fields.
    - `adapters.test.ts`, `bridge.test.ts`, `sseClient.test.ts` exist; suite runs green (todo/skip for unbuilt assertions, named precisely).
    - No test imports a module path that downstream plans will not create (paths match the RESEARCH project structure).
  </acceptance_criteria>
  <done>Mock SSE helper + three scaffolded test files exist; vitest green; downstream plans have concrete red→green targets.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org` green (skips allowed for unbuilt downstream behavior).
- `npx tsc --noEmit` clean for the new files.
- A1 finding documented in keystone-a1.test.ts (gates plan 02).
- `org/__tests__/guards.test.ts` and all existing V11 panel tests STILL green (D-02 unregressed).
</verification>

<success_criteria>
Normalized stubs + selection store exist; A1 keystone resolved and documented; fixtures + mock SSE helper + red placeholder tests in place; zero regression to D-02 / V11 tests.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-00-SUMMARY.md` when done. Record the A1 finding string verbatim — plan 02 reads it.
</output>
