// Pure client-side replay reducer (D-05/D-06, powers VADE-10).
//
// Reconstructs board/card state at any step N by folding `board.transition`
// entries in order. No Solid imports, no invoke, no DOM. CRITICAL: never use
// `produce()` or `structuredClone()` here — board nodes may arrive as Solid
// store proxies and both throw DATA_CLONE_ERR on proxies (memory
// voss-app-solid-produce-no-structuredclone). Use plain spreads only.

import type { SessionTreeNode, BoardFrame, CardSnapshot } from './types';

/** The 6 canonical board columns, in display order. */
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

/** First `em.ticket.risk_tier` in a node, default "med". */
function deriveRisk(node: SessionTreeNode): string {
  for (const t of node.transitions) {
    if (t.kind === 'em.ticket') return t.risk_tier;
  }
  return 'med';
}

/** Flatten every node's `board.transition` entries into one ordered list. */
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

/**
 * Reconstruct the board at `step`: applies transitions 0..step inclusive, then
 * overrides any node whose terminal_state has been reached by `step`
 * (done → Done, killed/timeout → Blocked). Returns plain object literals.
 */
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

  // terminal_state override — only once `step` reaches a node's last transition
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
