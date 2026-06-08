---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 05
type: execute
wave: 3
depends_on: ["V14-02", "V14-03"]
files_modified:
  - apps/voss-app/src/org/attention/attentionQueue.ts
  - apps/voss-app/src/org/attention/AttentionPanel.tsx
  - apps/voss-app/src/org/attention/__tests__/attentionQueue.test.tsx
  - apps/voss-app/src/App.tsx
autonomous: true
requirements: [VCKP-04]
must_haves:
  truths:
    - "A test injects a permission event, a budget-threshold event, and a sign-off-available event and asserts three queue items render, each with a working deep-link to its bound card/session via resolveCard"
    - "A permission item exposes allow-once / allow-scoped / deny actions and shows tool + args + dimension + affected path"
    - "Surface = StatusBar count pill + dockable queue panel (D-05); blocking items pulse the pill, they do not hard-modal the cockpit (D-06)"
    - "Per-pane permission prompts in the live grid are unchanged (this queue is the global aggregator, not a replacement)"
    - "For adopted external agents the queue copy does NOT promise per-tool gating (Pitfall 6 / tier C)"
  artifacts:
    - path: "apps/voss-app/src/org/attention/attentionQueue.ts"
      provides: "Aggregator signal (snapshot decisions + live events)"
      contains: "createSignal"
    - path: "apps/voss-app/src/org/attention/AttentionPanel.tsx"
      provides: "Dockable queue panel + StatusBar pill"
  key_links:
    - from: "apps/voss-app/src/org/attention/attentionQueue.ts"
      to: "apps/voss-app/src/org/model/bridge.ts"
      via: "resolveCard deep-link"
      pattern: "resolveCard"
---

<objective>
VCKP-04 global AttentionQueue (D-05/D-06). An aggregator signal sourced from snapshot decisions (Blocked column, sign-off, unsupported-claims) AND live SSE events (`permission.updated`, `gate.updated`, `budget.updated` threshold, `confidence.updated` below gate, `session.idle`, verification-failed). Each item deep-links to its card/session/evidence via `resolveCard`. Permission items show tool + args + dimension + affected path with allow-once/allow-scoped/deny. Surface = a StatusBar count pill (reusing the existing agent-pill pattern) + a dockable panel; blocking items pulse the pill (no hard modal).

Purpose: Close G3 (no global attention queue — stalls stay hidden).
Output: aggregator signal, AttentionPanel + StatusBar pill, test, StatusBar wiring in App.tsx.
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
@.planning/PROTOCOL.md

<interfaces>
From apps/voss-app/src/pane/budgetRegistry.ts:10-28: signal + dedup'd immutable update analog (NO produce).
From apps/voss-app/src/org/boardDerive.ts: `deriveColumn` → `'Blocked'` (snapshot blocked source).
From apps/voss-app/src/org/types.ts: `RunFinal.sign_off` (:99-116), `AuditReport.unsupported_claims` (:182).
From sdk/typescript/src/client/sse.ts:6: `AgentEvent` union — `permission.updated`/`gate.updated`/`budget.updated`/`confidence.updated`/`session.idle`, each with `sessionID`. PROTOCOL §6/§7: permission carries tool/args/dimension/affected-path.
From apps/voss-app/src/org/model/bridge.ts (plan 02): `resolveCard(maps, cardId)` for deep-links.
From apps/voss-app/src/App.tsx:1271-1302: StatusBar props (`agentCount`, `totalCost`, `orgViewOpen`) — pattern to extend with an attention pill.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: attentionQueue.ts aggregator signal</name>
  <files>apps/voss-app/src/org/attention/attentionQueue.ts, apps/voss-app/src/org/attention/__tests__/attentionQueue.test.tsx</files>
  <behavior>
    - ingestEvent(permissionEvent) adds {kind:'permission', cardId, sessionNodeId, tool, args, dimension, affectedPath, actions:['allow-once','allow-scoped','deny']}.
    - ingestEvent(budgetThresholdEvent) adds {kind:'budget', ...} with a deep-link.
    - ingestSnapshotDecisions(runData) adds sign-off-available items (from RunFinal.sign_off) and Blocked items.
    - Each item exposes a deepLink resolved via resolveCard → {paneId?, sessionNodeId?}.
    - Duplicate ingest of the same event id does not add a second item (dedup).
  </behavior>
  <read_first>
    - apps/voss-app/src/pane/budgetRegistry.ts:10-37 (signal + dedup immutable update)
    - apps/voss-app/src/org/model/bridge.ts (resolveCard from plan 02)
    - apps/voss-app/src/org/types.ts:99-116,182 (RunFinal.sign_off, unsupported_claims)
    - sdk/typescript/src/client/sse.ts:6 (AgentEvent union shape)
    - .planning/PROTOCOL.md §6/§7 (permission fields: tool/args/dimension/affected-path)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (attentionQueue pattern; Pitfall 6)
  </read_first>
  <action>
    Create `attentionQueue.ts`: a module-level `createSignal<AttentionItem[]>([])` with dedup'd immutable updates (mirror budgetRegistry, NO produce). Export `ingestEvent(ev: AgentEvent)` mapping each SSE event type to an `AttentionItem` (permission → tool/args/dimension/affectedPath + actions allow-once/allow-scoped/deny; budget-threshold; confidence-below-gate; session.idle; gate.updated), and `ingestSnapshotDecisions(runData)` mapping Blocked column + `RunFinal.sign_off` + `unsupported_claims` to items. Every item computes `deepLink` via `resolveCard`. For items tied to an adopted external agent, the copy/actions must NOT include per-tool gating language (Pitfall 6 — tier C). Write `attentionQueue.test.tsx` covering all five behaviors: inject permission + budget-threshold + sign-off → 3 items, each deep-linking; permission item exposes the three actions + fields; dedup holds.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/attention/__tests__/attentionQueue.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Injecting permission + budget-threshold + sign-off yields exactly 3 items, each with a resolveCard deep-link.
    - The permission item carries tool/args/dimension/affectedPath and actions allow-once/allow-scoped/deny.
    - Dedup: re-ingesting the same event id does not duplicate.
    - No `produce`/`structuredClone` in the module.
  </acceptance_criteria>
  <done>Aggregator merges both planes into one deep-linked queue; permission actions present; dedup works.</done>
</task>

<task type="auto">
  <name>Task 2: AttentionPanel + StatusBar pill (D-05/D-06) + App wiring</name>
  <files>apps/voss-app/src/org/attention/AttentionPanel.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx:1271-1302 (StatusBar mount + props — extend with the attention pill)
    - apps/voss-app/src/components/StatusBar.tsx (agent-count pill pattern to mirror)
    - apps/voss-app/src/org/attention/attentionQueue.ts (task 1 signal)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-05 pill+dockable panel, D-06 pulse-not-modal)
  </read_first>
  <action>
    Create `AttentionPanel.tsx`: a dockable (non-modal) panel listing queue items; each row shows its category, summary, and a deep-link action that focuses the bound card/session (via the `resolveCard` result). Permission rows render allow-once/allow-scoped/deny buttons. Add a StatusBar count pill (reuse the existing agent-pill markup/class) bound to the queue length; clicking it toggles the dockable panel (D-05). Blocking items (permission, sign-off-available) add a pulse class to the pill (D-06) — never a hard modal. Wire into `App.tsx` StatusBar alongside the existing agentCount/totalCost props. Do NOT touch the existing per-pane permission modal in the live grid (D-06 — unchanged). A12 tokens + a pulse animation that the reduced-motion gate in plan 12 will disable.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -E "AttentionPanel|App.tsx" || echo "clean"</automated>
  </verify>
  <acceptance_criteria>
    - StatusBar shows a count pill bound to queue length; clicking toggles the dockable AttentionPanel (non-modal).
    - Blocking items pulse the pill; no hard modal is introduced; the live-grid per-pane permission modal is untouched.
    - Permission rows expose allow-once/allow-scoped/deny; A12 tokens only.
  </acceptance_criteria>
  <done>Global queue surfaced via pill + dockable panel; blocking items pulse; live-grid modal unchanged.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org/attention` green; `npx tsc --noEmit` clean.
- Queue items deep-link via resolveCard; dedup holds.
- Existing per-pane permission modal + V11 tests unregressed.
</verification>

<success_criteria>
A global attention queue aggregates snapshot decisions + live events, deep-links each item, exposes permission actions, and surfaces as a pulsing StatusBar pill + dockable panel without hard-modaling.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-05-SUMMARY.md` when done.
</output>
