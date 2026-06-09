// Pure run-intake assembler + Auto-mode validator (VCKP-03). Mirrors the
// `AgentLaunchModal.buildConfig` config-assembly pattern: build a typed spec
// from segmented-control state. No Solid imports, no produce/structuredClone —
// plain reads + object literals — so the validator/assembler are fixture-tested
// directly (boardDerive.ts convention).
//
// Auto-mode gating follows the disabled-with-reason discipline
// (decisionActions.ts:1-11): a blocked Auto-start returns a human reason string,
// never a silent no-op.

export type RunMode = 'Plan' | 'Edit' | 'Auto';
export type RunTarget = 'native' | 'terminal';

/**
 * Intake state captured by the RunCommandBar segmented controls. `budget` and
 * `scope` are optional because Auto mode gates on their presence; the assembler
 * carries them through regardless.
 */
export interface RunIntakeState {
  goal: string;
  mode: RunMode;
  team: string;
  scope?: string;
  budget?: number;
  target: RunTarget;
}

/**
 * Assembled, typed run spec carrying ALL intake fields. This is the object the
 * start paths (terminal spawnAgent / native createSession) consume.
 */
export interface RunSpec {
  goal: string;
  mode: RunMode;
  team: string;
  scope?: string;
  budget?: number;
  target: RunTarget;
}

/**
 * Pure config assembler: build the typed RunSpec from intake state. Carries
 * every field (goal/mode/team/scope/budget/target) through unchanged.
 */
export function assembleRunSpec(state: RunIntakeState): RunSpec {
  return {
    goal: state.goal,
    mode: state.mode,
    team: state.team,
    scope: state.scope,
    budget: state.budget,
    target: state.target,
  };
}

/**
 * Auto-mode gating. Plan/Edit are never blocked. Auto requires BOTH a budget
 * and a scope present; missing either returns `ok:false` with a human reason
 * naming the specific missing field. When both are missing the budget check
 * runs first (deterministic).
 */
export function validateAutoStart(
  state: Pick<RunIntakeState, 'mode'> &
    Partial<Pick<RunIntakeState, 'budget' | 'scope'>>,
): { ok: boolean; reason?: string } {
  if (state.mode !== 'Auto') return { ok: true };

  if (!state.budget) {
    return {
      ok: false,
      reason: 'Auto mode needs a budget before it can start.',
    };
  }
  if (!state.scope) {
    return {
      ok: false,
      reason: 'Auto mode needs a scope before it can start.',
    };
  }
  return { ok: true };
}
