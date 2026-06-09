// V14-10 "Let Voss manage this agent" adopt logic (VCKP-12, D-10/D-11/D-12).
//
// Forward-only adoption of a running ad-hoc terminal agent: bind a card to its
// pane via the id-bridge (Bridge B), apply an ADVISORY budget + scope, start a
// transcript-audit node marked `partial_lineage` whose cost baseline is the
// pane's spend at adoption time (pre-adoption activity excluded), and require
// review-before-done. Tier is ALWAYS 'C' (observe-only): a live PID cannot be
// retro-sandboxed, so adoption never promises per-tool gating (D-11).
//
// `partial_lineage` is an INTERNAL field name — it must never surface in UI
// copy (D-10).
//
// Pure module: no solid-js import, no produce/structuredClone — bridge/budget
// signal access goes through their exported module functions only.

import { registerTerminalCard } from './model/bridge';
import { budgetByPaneId } from '../pane/budgetRegistry';

export type AdoptRisk = 'low' | 'med' | 'high';

export interface AdoptInput {
  paneId: string;
  /** Existing run to add the agent to, or null → a new run. */
  runId: string | null;
  /** Advisory scope (folder/glob the agent is asked to stay within). */
  scope: string;
  /** Advisory budget limit in USD (forward spend only). */
  budget: number;
  cliBinary: string;
  /** False when this build exposes no harness adopt write-path. */
  harnessAdoptAvailable: boolean;
  /** User-edited overrides (D-12); default to inferRole / inferRisk. */
  role?: string;
  risk?: AdoptRisk;
}

export interface AdoptAuditNode {
  lineage: 'partial_lineage';
  /** Pane spend (USD) at adoption time — pre-adoption cost is excluded. */
  costBaselineUsd: number;
}

export interface AdoptDisabled {
  disabled: true;
  reason: string;
}

export interface AdoptBinding {
  disabled: false;
  cardId: string;
  /** No harness session exists for an adopted terminal agent — falls back to the card id (resolveCard convention). */
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

/** Plain-language, jargon-free (D-10) — surfaces verbatim in the modal. */
export const ADOPT_UNAVAILABLE_REASON =
  "Voss can't manage this agent yet — this build has no way to follow its work. Nothing was changed.";

const AGENT_CLIS = new Set(['claude', 'codex', 'gemini', 'opencode', 'aider']);

/** D-12: role pre-inferred from the CLI binary (editable default). */
export function inferRole(cliBinary: string): string {
  const name = cliBinary.trim().toLowerCase().split('/').pop() ?? '';
  return AGENT_CLIS.has(name) ? 'executor' : 'user';
}

/** D-12: risk pre-inferred from scope+budget (editable default). */
export function inferRisk(input: { scope: string; budget: number }): AdoptRisk {
  const scoped = input.scope.trim().length > 0;
  const bounded = Number.isFinite(input.budget) && input.budget > 0;
  if (scoped && bounded) return 'low';
  if (!scoped && !bounded) return 'high';
  return 'med';
}

/**
 * Adopt a running pane forward-only. Mints + binds a card (Bridge B), applies
 * advisory budget+scope, starts a `partial_lineage` audit node baselined at
 * adoption-time spend, and enforces review-before-done at tier C. When no
 * harness adopt write-path exists, returns disabled-with-reason WITHOUT
 * binding anything (no fake affordance — decisionActions.ts discipline).
 */
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
