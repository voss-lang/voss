---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 04
type: summary
wave: 3
status: complete
depends_on: ["V14-02", "V14-03"]
requirements: [VCKP-03]
---

# V14-04 Summary — VCKP-03 RunCommandBar (always-on intake)

Status: **COMPLETE**. src/org: 76 passed | 4 todo | 0 fail. tsc clean. Quick-Launch (D-04) untouched.

## Artifacts

Task 1 (pure intake):
- `src/org/cockpit/runIntake.ts` — PURE (no Solid imports). Types: `RunMode='Plan'|'Edit'|'Auto'`, `RunTarget='native'|'terminal'`, `RunIntakeState{goal,mode,team,scope?,budget?,target}`, `RunSpec` (same shape).
  - `assembleRunSpec(state): RunSpec` — carries all fields.
  - `validateAutoStart(state): {ok,reason?}` — Auto+no-budget → "Auto mode needs a budget before it can start."; Auto+no-scope → "Auto mode needs a scope before it can start." (budget checked first when both missing); Plan/Edit → always ok.

Task 2 (component + dual start + mount):
- `src/org/cockpit/RunCommandBar.tsx` — always-on top strip (D-03). Controls: goal input, VISIBLE modal-segmented Mode (Plan/Edit/Auto — never placeholder), team select, scope chip, budget chip, context-attach toggle, EXPLICIT modal-segmented target (Voss-native / Terminal agent). Inline `.run-bar__reason` role=alert for Auto-block.
  - Start: `assembleRunSpec` → `validateAutoStart` gate (blocks + visible reason, no start path on fail) → terminal: `registerTerminalCard(paneId)` mints cardId, `spawnAgent({...,sessionId:cardId,paneId})` Bridge B (mode/team/scope/budget in cliArgs, goal as taskPrompt); native: `client.createSession(spec)` → `registerNativeCard(response.id, response.id)` Bridge A (create-response id IS node id per A1).
  - Injectable: `client?: RunNativeClient` (mock for test; native path disabled-with-reason "server gated" when absent), `spawnAgent?: SpawnAgentFn` (defaults to invoke('spawn_agent') wrapper), `resolvePaneId?: ()=>string`.
  - A12 tokens only; reuses modal-segmented classes; no new --xxx.
- `src/org/cockpit/runCommandBar.css` — strip styling, A12 tokens.
- `src/org/cockpit/CockpitShell.tsx` — `<RunCommandBar cwd cliBinary/>` mounted above .cockpit-body (always-on, regardless of selection/mode).
- `src/org/cockpit/__tests__/runCommandBar.test.tsx` — 8 tests: `describe('validate')` 5 (Task 1) + `describe('start paths')` 3 (terminal cardId-as-sessionId + payload; native createSession+registerNativeCard; Auto-block no-call). afterEach __resetBridgeMaps.

## Decisions / deviations (for downstream)

- **paneId for terminal start:** cockpit bar has no bound pane → `resolvePaneId` prop defaults to `crypto.randomUUID()` (fresh pane per run; mirrors PaneComponent using props.id). registerTerminalCard(paneId) → cardToPane[cardId]=paneId, cardId passed as spawn_agent sessionId.
- **Native client shape:** real SDK is `createSession(cwd?)→Promise<string>`, but plan specified injectable `{createSession(spec):Promise<{id}>}`. Followed PLAN's mock contract (type `RunNativeClient`); real-server wiring deferred (V13.1 gated). **When the gated server lands, reconcile the createSession signature.**
- **Config→CLI encoding:** mode/team/scope/budget passed as `--mode/--team/--scope/--budget` cliArgs; goal as taskPrompt (mirrors AgentLaunchModal buildConfig intent).
- **Note:** RunCommandBar.tsx/css + CockpitShell mount were already present in commit b23bb43 (prior partial run), byte-identical to regenerated output; only the test file's start-path suite was net-new this run. No functional discrepancy.

## Verification
- `npx vitest run src/org/cockpit/__tests__/runCommandBar.test.tsx` → 8 passed.
- `-t "validate"` → 5 passed | 3 skipped (selector still isolates validator suite).
- `npx vitest run src/org` → 15 files, 76 passed | 4 todo | 0 fail.
- `npx tsc --noEmit` → clean.
- AgentLaunchModal / Quick-Launch unedited (D-04 intact).
