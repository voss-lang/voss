import { invoke } from '@tauri-apps/api/core';
import type { DecisionResult } from './types';

export type DecisionAction = 'approve';

export function buildDecisionArgs(_action: DecisionAction, runId: string): string[] {
  return ['audit', runId, '--approve'];
}

export function buildDecisionCommand(
  _action: DecisionAction,
  runId: string,
  cwd: string,
): string {
  return `voss audit ${runId} --cwd ${cwd} --approve`;
}

export async function runDecision(
  cliBinary: string,
  cwd: string,
  action: DecisionAction,
  runId: string,
): Promise<DecisionResult> {
  return invoke<DecisionResult>('run_decision', {
    cliBinary,
    cwd,
    args: buildDecisionArgs(action, runId),
  });
}
