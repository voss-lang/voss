import { registerTerminalCard } from './model/bridge';
import { budgetByPaneId } from '../pane/budgetRegistry';

export type AdoptRisk = 'low' | 'med' | 'high';

export interface AdoptInput {
  paneId: string;

  runId: string | null;

  scope: string;

  budget: number;
  cliBinary: string;

  harnessAdoptAvailable: boolean;

  role?: string;
  risk?: AdoptRisk;
}

export interface AdoptAuditNode {
  lineage: 'partial_lineage';

  costBaselineUsd: number;
}

export interface AdoptDisabled {
  disabled: true;
  reason: string;
}

export interface AdoptBinding {
  disabled: false;
  cardId: string;

  sessionNodeId: string;
  paneId: string;
  runId: string | null;
  role: string;
  risk: AdoptRisk;
  scope: string;
  budget: number;
  auditNode: AdoptAuditNode;
  reviewRequired: true;
  tier: 'C';
}

export type AdoptResult = AdoptDisabled | AdoptBinding;

export const ADOPT_UNAVAILABLE_REASON =
  "Voss can't manage this agent yet — this build has no way to follow its work. Nothing was changed.";

const AGENT_CLIS = new Set(['claude', 'codex', 'gemini', 'opencode', 'aider']);

export function inferRole(cliBinary: string): string {
  const name = cliBinary.trim().toLowerCase().split('/').pop() ?? '';
  return AGENT_CLIS.has(name) ? 'executor' : 'user';
}

export function inferRisk(input: { scope: string; budget: number }): AdoptRisk {
  const scoped = input.scope.trim().length > 0;
  const bounded = Number.isFinite(input.budget) && input.budget > 0;
  if (scoped && bounded) return 'low';
  if (!scoped && !bounded) return 'high';
  return 'med';
}

export function adoptAgent(input: AdoptInput): AdoptResult {
  if (!input.harnessAdoptAvailable) {
    return { disabled: true, reason: ADOPT_UNAVAILABLE_REASON };
  }

  const cardId = registerTerminalCard(input.paneId);
  const costBaselineUsd = budgetByPaneId()[input.paneId]?.cost_usd ?? 0;

  return {
    disabled: false,
    cardId,
    sessionNodeId: cardId,
    paneId: input.paneId,
    runId: input.runId,
    role: input.role ?? inferRole(input.cliBinary),
    risk: input.risk ?? inferRisk({ scope: input.scope, budget: input.budget }),
    scope: input.scope,
    budget: input.budget,
    auditNode: { lineage: 'partial_lineage', costBaselineUsd },
    reviewRequired: true,
    tier: 'C',
  };
}
