export type RunMode = 'Plan' | 'Edit' | 'Auto';
export type RunTarget = 'native' | 'terminal';

/**
 * Intake state captured by the RunCommandBar segmented controls. `budget` and
 * `scope` are optional because Auto mode gates on their presence; the assembler
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
 * start paths (terminal spawnAgent / native createSession) consume
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
 * every field (goal/mode/team/scope/budget/target) through unchanged
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
 */
export function validateAutoStart(
  state: Pick<RunIntakeState, 'mode'> &
    Partial<Pick<RunIntakeState, 'budget' | 'scope'>>,
): { ok: boolean; reason?: string } {
  if (state.mode !== 'Auto') return { ok: true };

  if (!state.budget) {
    return {
      ok: false,
      reason: 'Autopilot needs a budget before it can start.',
    };
  }
  if (!state.scope) {
    return {
      ok: false,
      reason: 'Autopilot needs a scope before it can start.',
    };
  }
  return { ok: true };
}
