---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 07
type: execute
wave: 5
depends_on: ["V14-01", "V14-03"]
files_modified:
  - apps/voss-app/src/org/swarmReconcile.ts
  - apps/voss-app/src/org/__tests__/swarmReconcile.test.ts
  - apps/voss-app/src/org/__tests__/fixtures/swarm-manifest.json
  - apps/voss-app/src/org/cockpit/CockpitShell.tsx
autonomous: true
requirements: [VCKP-07]
must_haves:
  truths:
    - "A test with a fixture manifest.json (2 agents) renders 2 roster rows + 2 board cards with columns matching each agent's status"
    - "GATED graceful-degrade: absence of .voss/swarm/ degrades to a no-swarm state with no error — never blocks the phase"
    - "Per-agent swarm status (pending/running/complete) maps to board columns; the swarm goal shows as the run idea"
    - "The reconciler is a pure adapter mirroring boardDerive null-tolerance"
  artifacts:
    - path: "apps/voss-app/src/org/swarmReconcile.ts"
      provides: "manifest -> roster rows + board cards adapter"
      contains: "export function"
    - path: "apps/voss-app/src/org/__tests__/swarmReconcile.test.ts"
      provides: "VCKP-07 swarm fixture test"
  key_links:
    - from: "apps/voss-app/src/org/swarmReconcile.ts"
      to: "apps/voss-app/src/org/boardDerive.ts"
      via: "cardsFromRunData column-mapping analog"
      pattern: "column"
---

<objective>
VCKP-07 (GATED on A13, best-effort): reconcile `.voss/swarm/manifest.json` agents into roster rows + board cards, mapping per-agent swarm status (pending/running/complete) to board columns, with the swarm goal as the run idea. Absent `.voss/swarm/` degrades to "no swarm" without error. Pure-adapter, fixture-verifiable now.

Purpose: Close G6 (swarm disconnected from the board model).
Output: pure swarmReconcile adapter, fixture manifest, test, optional wiring into CockpitShell roster section.
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
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md

<interfaces>
From apps/voss-app/src/org/boardDerive.ts:44-58: `cardsFromRunData` (manifest→cards adapter analog) + `deriveColumn` (status→column). Mirror the `if (!data) return []` null-tolerance (:46).
A13 `.voss/swarm/manifest.json`: agents with id/role/status (pending|running|complete) + swarm goal. Rust side exists: `write_swarm_files`/`watch_swarm_results` (lib.rs:603,635) + `voss://swarm-result-added` event. V14 only adapts the manifest into UI.
From apps/voss-app/src/org/model/normalized.ts (plan 01): `Card`, `Agent` types.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: swarmReconcile pure adapter + fixture + test</name>
  <files>apps/voss-app/src/org/swarmReconcile.ts, apps/voss-app/src/org/__tests__/swarmReconcile.test.ts, apps/voss-app/src/org/__tests__/fixtures/swarm-manifest.json</files>
  <behavior>
    - reconcileSwarm(manifest) with 2 agents returns 2 roster rows + 2 board cards; each card's column derives from the agent's status (pending→Queued/Backlog, running→In Progress, complete→Done — match the existing 6-column state machine).
    - reconcileSwarm(null) / reconcileSwarm(undefined) returns {rosterRows:[], cards:[]} with no throw (no-swarm degrade).
    - The swarm goal is surfaced as the run idea on the returned structure.
  </behavior>
  <read_first>
    - apps/voss-app/src/org/boardDerive.ts:21-58 (deriveColumn + cardsFromRunData null-tolerance to mirror)
    - .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md (manifest.json shape: agent id/role/status + goal)
    - apps/voss-app/src/org/model/normalized.ts (Card/Agent types from plan 01)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (swarmReconcile pattern)
  </read_first>
  <action>
    Create `swarmReconcile.ts` as a PURE module (no Solid imports, mirror boardDerive header). Export `reconcileSwarm(manifest): { rosterRows: Agent[]; cards: Card[]; idea?: string }` mapping manifest agents → roster rows + board cards, with a `swarmStatusToColumn(status)` helper mapping pending/running/complete onto the existing 6-column orchestrator state machine (reuse `deriveColumn`'s column vocabulary — do NOT invent new columns; custom columns are out of scope). Null/undefined manifest → empty result, no throw (no-swarm degrade). Create `fixtures/swarm-manifest.json` with 2 agents of differing status + a goal. Write `swarmReconcile.test.ts` covering the three behaviors.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/swarmReconcile.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - 2-agent manifest → 2 roster rows + 2 cards, columns matching status.
    - null manifest → empty result, no throw.
    - swarm goal surfaced as idea; no new board columns introduced.
    - `swarmReconcile.ts` imports nothing from solid-js (pure).
  </acceptance_criteria>
  <done>Manifest reconciles into roster + board cards by status; absent swarm degrades cleanly.</done>
</task>

<task type="auto">
  <name>Task 2: Wire swarm roster/cards into the cockpit (best-effort)</name>
  <files>apps/voss-app/src/org/cockpit/CockpitShell.tsx</files>
  <read_first>
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (plan 03 — roster/board regions)
    - apps/voss-app/src/org/swarmReconcile.ts (task 1)
    - apps/voss-app/src-tauri/src/lib.rs:603,635 (existing swarm file commands — read manifest if present)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (Roster IA discretion — sectioned single roster)
  </read_first>
  <action>
    In `CockpitShell.tsx`, when a `.voss/swarm/manifest.json` is present (read via an existing Tauri command or a guarded invoke), merge `reconcileSwarm(manifest)` output into the roster section (sectioned single roster per CONTEXT discretion) and the Board spine. When absent, render nothing extra (no-swarm degrade — no error banner). Default to the sectioned roster IA: Voss-native team · swarm · external terminal agents.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -E "Cockpit|swarmReconcile" || echo "clean" && npx vitest run src/org/__tests__</automated>
  </verify>
  <acceptance_criteria>
    - When a manifest fixture is present, swarm agents appear as roster rows + board cards.
    - Absent `.voss/swarm/` produces no error and no swarm section.
    - V11 + cockpit tests stay green.
  </acceptance_criteria>
  <done>Swarm agents reconcile into the cockpit when present; clean degrade when absent.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org` green; `npx tsc --noEmit` clean.
- swarmReconcile pure; no new columns; null-tolerant.
- V11 + cockpit tests unregressed.
</verification>

<success_criteria>
Swarm manifest agents render as roster rows + board cards by status when present; absence degrades to no-swarm without error; phase not blocked.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-07-SUMMARY.md` when done.
</output>
