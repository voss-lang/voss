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
      roots.push(tn);
    }
  }
  return roots;
}
