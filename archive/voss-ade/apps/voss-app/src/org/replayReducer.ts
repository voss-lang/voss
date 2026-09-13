import type { SessionTreeNode, BoardFrame, CardSnapshot } from './types';

export const CANONICAL_COLUMNS = [
  'Backlog',
  'Planned',
  'InProgress',
  'InReview',
  'Blocked',
  'Done',
] as const;

interface CollectedTransition {
  nodeId: string;
  from: string;
  to: string;
  role: string | null;
  risk: string;
  budget: { limit: number; spent: number };
  label: string;
}

function deriveRisk(node: SessionTreeNode): string {
  for (const t of node.transitions) {
    if (t.kind === 'em.ticket') return t.risk_tier;
  }
  return 'med';
}

function collectBoardTransitions(nodes: SessionTreeNode[]): CollectedTransition[] {
  const out: CollectedTransition[] = [];
  for (const node of nodes) {
    const risk = deriveRisk(node);
    for (const t of node.transitions) {
      if (t.kind !== 'board.transition') continue;
      out.push({
        nodeId: node.id,
        from: t.from,
        to: t.to,
        role: node.role,
        risk,
        budget: { limit: node.envelope.limit, spent: node.envelope.spent },
        label: `${node.id} → ${t.to}`,
      });
    }
  }
  return out;
}

function emptyColumns(): Record<string, CardSnapshot[]> {
  const cols: Record<string, CardSnapshot[]> = {};
  for (const c of CANONICAL_COLUMNS) cols[c] = [];
  return cols;
}

export function computeBoardAtStep(
  nodes: SessionTreeNode[],
  step: number,
): BoardFrame {
  const all = collectBoardTransitions(nodes);
  const sliced = all.slice(0, step + 1);
  const columns = emptyColumns();

  for (const t of sliced) {
    const fromCol = columns[t.from];
    if (fromCol) columns[t.from] = fromCol.filter((c) => c.id !== t.nodeId);
    const snap: CardSnapshot = {
      id: t.nodeId,
      role: t.role,
      risk: t.risk,
      status: t.to,
      budget: { ...t.budget },
    };
    columns[t.to] = [...(columns[t.to] ?? []), snap];
  }

  for (const node of nodes) {
    const ts = node.terminal_state;
    if (!ts) continue;
    let lastIdx = -1;
    for (let i = 0; i < all.length; i++) {
      if (all[i].nodeId === node.id) lastIdx = i;
    }
    if (lastIdx === -1 || step < lastIdx) continue;
    const target =
      ts.exit_reason === 'done'
        ? 'Done'
        : ts.exit_reason === 'timeout' || ts.exit_reason === 'killed'
          ? 'Blocked'
          : null;
    if (!target) continue;
    let moved: CardSnapshot | undefined;
    for (const col of CANONICAL_COLUMNS) {
      const idx = columns[col].findIndex((c) => c.id === node.id);
      if (idx < 0) continue;
      moved = columns[col][idx];
      columns[col] = columns[col].filter((c) => c.id !== node.id);
      break;
    }
    if (moved) {
      columns[target] = [...columns[target], { ...moved, status: target }];
    }
  }

  return { columns, step, eventLabel: all[step]?.label ?? '' };
}
