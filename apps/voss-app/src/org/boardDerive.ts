// Pure board-derivation helpers (VADE-02). Mirrors the verified harness
// `board/cli_view._derive_column` / `_derive_risk` algorithm exactly. No Solid
// imports, no produce/structuredClone — plain reads + object literals.

import type { RunData, SessionTreeNode } from './types';

export interface BoardCard {
  id: string;
  title: string;
  role: string | null;
  risk: string;
  column: string;
  spent: number;
  limit: number;
}

/**
 * Walk board.transition entries (last `.to` wins, default "Backlog"), then
 * apply the terminal_state override: done → "Done", timeout/killed → "Blocked".
 */
export function deriveColumn(node: SessionTreeNode): string {
  let column = 'Backlog';
  for (const t of node.transitions) {
    if (t.kind === 'board.transition') column = t.to;
  }
  const ts = node.terminal_state;
  if (ts) {
    if (ts.exit_reason === 'done') column = 'Done';
    else if (ts.exit_reason === 'timeout' || ts.exit_reason === 'killed') {
      column = 'Blocked';
    }
  }
  return column;
}

/** First em.ticket.risk_tier, default "med". */
export function deriveRisk(node: SessionTreeNode): string {
  for (const t of node.transitions) {
    if (t.kind === 'em.ticket') return t.risk_tier;
  }
  return 'med';
}

/** One card per non-root node (root = parent_run_id null). Null-tolerant. */
export function cardsFromRunData(data: RunData | null): BoardCard[] {
  if (!data) return [];
  return data.session_tree.nodes
    .filter((n) => n.parent_run_id !== null)
    .map((n) => ({
      id: n.id,
      title: n.scope ?? n.id,
      role: n.role,
      risk: deriveRisk(n),
      column: deriveColumn(n),
      spent: n.envelope.spent,
      limit: n.envelope.limit,
    }));
}
