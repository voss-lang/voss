// Pure tree builder (VADE-03): flat SessionTreeNode[] → rooted parent→child
// structure via parent_run_id. No Solid imports, no produce/structuredClone.
// Each node is attached to exactly one parent (or root), so cycles/orphans
// cannot cause a node to be visited twice during the single build pass.

import type { SessionTreeNode } from './types';

export type TreeNode = SessionTreeNode & { children: TreeNode[] };

export function buildTree(nodes: SessionTreeNode[]): TreeNode[] {
  const byId = new Map<string, TreeNode>();
  for (const n of nodes) byId.set(n.id, { ...n, children: [] });

  const roots: TreeNode[] = [];
  for (const n of nodes) {
    const tn = byId.get(n.id)!;
    const pid = n.parent_run_id;
    const parent = pid !== null ? byId.get(pid) : undefined;
    if (parent && parent !== tn) {
      parent.children.push(tn);
    } else {
      // parent_run_id null (true root) OR unknown parent (orphan) → root level
      roots.push(tn);
    }
  }
  return roots;
}
