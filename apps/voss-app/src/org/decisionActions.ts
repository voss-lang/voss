import { invoke } from '@tauri-apps/api/core';
import type { DecisionResult } from './types';

export type DecisionAction = 'approve';

/** The real CLI argv for a decision (the verified `--approve` write path) */
export function buildDecisionArgs(_action: DecisionAction, runId: string): string[] {
  return ['audit', runId, '--approve'];
}

/** The literal command string shown in the confirmation dialog */
export function buildDecisionCommand(
  _action: DecisionAction,
  runId: string,
  cwd: string,
): string {
  return `voss audit ${runId} --cwd ${cwd} --approve`;
}

/** Shell the decision via the Rust `run_decision` command ( capture) */
export async function runDecision(
  _cliBinary: string,
  _cwd: string,
  action: DecisionAction,
  runId: string,
): Promise<DecisionResult> {
  return invoke<DecisionResult>('run_decision', {
    args: buildDecisionArgs(action, runId),
  });
}
