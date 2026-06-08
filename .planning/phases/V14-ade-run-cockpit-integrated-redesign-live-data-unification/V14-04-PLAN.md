---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 04
type: execute
wave: 3
depends_on: ["V14-02", "V14-03"]
files_modified:
  - apps/voss-app/src/org/cockpit/RunCommandBar.tsx
  - apps/voss-app/src/org/cockpit/runIntake.ts
  - apps/voss-app/src/org/cockpit/__tests__/runCommandBar.test.tsx
  - apps/voss-app/src/org/cockpit/CockpitShell.tsx
autonomous: true
requirements: [VCKP-03]
must_haves:
  truths:
    - "A test starts a terminal-agent run from the bar and asserts the existing launch path (spawnAgent) is invoked with mode/team/scope/budget, with the minted cardId passed as the sessionId arg (Bridge B)"
    - "A fixture/mock-client test starts a Voss-native run and asserts a protocol session-create call with the assembled spec; the returned id is stored via registerNativeCard (Bridge A)"
    - "An Auto-mode start with no budget OR no scope is blocked with a visible reason (never a silent no-op)"
    - "The bar is an always-on top strip present in both modes (D-03); the run target (Voss-native vs terminal-agent) is an explicit indicator, mode is never hidden in placeholder text"
  artifacts:
    - path: "apps/voss-app/src/org/cockpit/RunCommandBar.tsx"
      provides: "Run intake strip (goal/mode/team/scope/budget/target)"
      contains: "RunCommandBar"
    - path: "apps/voss-app/src/org/cockpit/runIntake.ts"
      provides: "Pure config assembler + Auto-mode validation"
  key_links:
    - from: "apps/voss-app/src/org/cockpit/RunCommandBar.tsx"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "spawnAgent terminal launch with cardId as sessionId"
      pattern: "spawnAgent"
---

<objective>
VCKP-03 RunCommandBar (D-03): an always-on top intake strip — goal/command input · mode segmented control (Plan/Edit/Auto) · team selector · scope chip · budget chip · context attach · explicit Voss-native vs terminal-agent indicator. It starts BOTH: terminal-agent via the existing PTY/CLI path (`spawnAgent`, passing the minted `cardId` as `sessionId` — Bridge B), and Voss-native via mock protocol session-create (storing the returned id via Bridge A). Auto mode cannot start without visible budget AND scope.

Purpose: Close G2 (no universal run-intake). Wire the keystone at the launch boundary.
Output: RunCommandBar component, pure runIntake assembler/validator, test, mounted in CockpitShell.
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
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-02-SUMMARY.md

<interfaces>
From apps/voss-app/src/components/modal/AgentLaunchModal.tsx:99-152: `buildConfig()` config-assembly pattern; :218-229 `modal-segmented`/`modal-segmented__btn--active` segmented-control markup to reuse.
From apps/voss-app/src/pane/pty-ipc.ts:167-186: `spawnAgent({cliBinary, cliArgs, taskPrompt, sessionId, paneId})` → `invoke('spawn_agent', ...)` — terminal start path.
From apps/voss-app/src/org/model/bridge.ts (plan 02): `registerTerminalCard(paneId): string` (mint cardId, pass as sessionId), `registerNativeCard(cardId, sessionID)`.
From sdk/typescript (V13.1, GATED): `createVossClient().createSession(spec) → {id}` — mock in V14 (real-server deferred). Inject the client as a prop/param so the test can supply a mock.
From apps/voss-app/src/org/decisionActions.ts:1-11: disabled-with-reason discipline (never silent no-op) for the Auto-block.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: runIntake.ts — pure config assembler + Auto-mode validation</name>
  <files>apps/voss-app/src/org/cockpit/runIntake.ts, apps/voss-app/src/org/cockpit/__tests__/runCommandBar.test.tsx</files>
  <behavior>
    - assembleRunSpec({goal, mode:'Auto', team, scope, budget, target}) returns a typed spec object carrying all fields.
    - validateAutoStart({mode:'Auto', budget: undefined, scope: 'x'}) returns {ok:false, reason:<string mentioning budget>}.
    - validateAutoStart({mode:'Auto', budget:5, scope: undefined}) returns {ok:false, reason:<string mentioning scope>}.
    - validateAutoStart({mode:'Auto', budget:5, scope:'tests/**'}) returns {ok:true}.
    - validateAutoStart for Plan/Edit mode returns {ok:true} regardless of budget/scope.
  </behavior>
  <read_first>
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx:99-152 (buildConfig analog)
    - apps/voss-app/src/org/decisionActions.ts:1-11 (disabled-with-reason discipline)
    - apps/voss-app/src/org/boardDerive.ts:1-3 (pure-module header convention)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (RunCommandBar pattern: config-assembly, validation rule)
  </read_first>
  <action>
    Create `runIntake.ts` as a PURE module (no Solid imports): `assembleRunSpec(state) → RunSpec` and `validateAutoStart(state) → {ok: boolean; reason?: string}`. The validator enforces the Auto-mode rule: Auto requires both budget AND scope present; missing either returns `ok:false` with a human reason string. Create `runCommandBar.test.tsx` and cover the five behaviors above plus (in task 2) the start-path assertions. Keep the validator pure so it is fixture-tested directly.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/cockpit/__tests__/runCommandBar.test.tsx -t "validate"</automated>
  </verify>
  <acceptance_criteria>
    - `validateAutoStart` blocks Auto with missing budget or scope, each with a distinct reason string.
    - Plan/Edit modes are never blocked by the validator.
    - `runIntake.ts` imports nothing from solid-js (pure).
  </acceptance_criteria>
  <done>Auto-mode gating is pure and tested; config assembler returns the full spec.</done>
</task>

<task type="auto">
  <name>Task 2: RunCommandBar component + dual start paths + mount</name>
  <files>apps/voss-app/src/org/cockpit/RunCommandBar.tsx, apps/voss-app/src/org/cockpit/__tests__/runCommandBar.test.tsx, apps/voss-app/src/org/cockpit/CockpitShell.tsx</files>
  <read_first>
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx:197-250 (segmented control + CLI list markup to reuse)
    - apps/voss-app/src/pane/pty-ipc.ts:167-186 (spawnAgent terminal path)
    - apps/voss-app/src/org/model/bridge.ts (registerTerminalCard / registerNativeCard from plan 02)
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (plan 03 — mount the bar as the always-on top strip)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-03, D-04 coexist with Quick-Launch)
  </read_first>
  <action>
    Create `RunCommandBar.tsx`: an always-on top strip (D-03) with goal input, a `modal-segmented` mode control (Plan/Edit/Auto — mode visible, never in placeholder), team selector, scope chip, budget chip, context-attach, and an explicit Voss-native vs terminal-agent target indicator. On start: for terminal target, call `registerTerminalCard(paneId)` to mint the cardId, then `spawnAgent({..., sessionId: cardId, paneId})` (Bridge B) with the assembled mode/team/scope/budget. For native target, call the injected V13.1 client's `createSession(spec)` (mock-injectable for the test), then `registerNativeCard(cardId, response.id)` (Bridge A). Block Auto-start via `validateAutoStart`, rendering the reason inline (disabled-with-reason, decisionActions discipline). Mount `<RunCommandBar />` at the top of `CockpitShell` (above the 4-region grid). Add the two start-path tests to `runCommandBar.test.tsx`: terminal start asserts `spawnAgent` called with cardId-as-sessionId + mode/team/scope/budget; native start asserts the mock `createSession` called with the spec and `registerNativeCard` stores the id; Auto-block asserts the visible reason. Style with A12 tokens only.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/cockpit/__tests__/runCommandBar.test.tsx && npx tsc --noEmit 2>&1 | grep -E "RunCommandBar|runIntake" || echo "clean"</automated>
  </verify>
  <acceptance_criteria>
    - Terminal start test asserts `spawnAgent` invoked with the minted cardId as `sessionId` and the mode/team/scope/budget payload.
    - Native start test asserts the mock `createSession` called with the assembled spec and the returned id stored via `registerNativeCard`.
    - Auto with missing budget/scope shows a visible reason and does NOT call any start path.
    - Mode segmented control is visible (not placeholder); RunCommandBar mounted in CockpitShell; A12 tokens only.
  </acceptance_criteria>
  <done>RunCommandBar starts both run types, wires the keystone at launch, blocks Auto without budget/scope; always-on strip mounted.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/org/cockpit` green; `npx tsc --noEmit` clean.
- spawnAgent receives cardId as sessionId (Bridge B); native start stores id via Bridge A.
- Quick-Launch (D-04) untouched.
</verification>

<success_criteria>
RunCommandBar starts terminal + native runs with full intake context, enforces Auto budget/scope gating with a visible reason, and is an always-on top strip mounted in the cockpit.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-04-SUMMARY.md` when done.
</output>
