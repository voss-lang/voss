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

export function deriveRisk(node: SessionTreeNode): string {
  for (const t of node.transitions) {
    if (t.kind === 'em.ticket') return t.risk_tier;
  }
  return 'med';
}

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
