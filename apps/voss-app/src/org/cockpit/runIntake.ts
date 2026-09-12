export type RunMode = 'Plan' | 'Edit' | 'Auto';
export type RunTarget = 'native' | 'terminal';

export interface RunIntakeState {
  goal: string;
  mode: RunMode;
  team: string;
  scope?: string;
  budget?: number;
  target: RunTarget;
}

export interface RunSpec {
  goal: string;
  mode: RunMode;
  team: string;
  scope?: string;
  budget?: number;
  target: RunTarget;
}

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
