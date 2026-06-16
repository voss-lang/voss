// V24-06 (VADE2-06) — pure Swarm Map derivation.
//
// The Swarm Map's single hardest constraint is HONESTY: every node and edge
// must trace to a real signal (RunData / board+session tree / audit-review /
// attention queue). Missing signals render as placeholder nodes or are omitted —
// nothing is synthesized. Every edge carries a non-empty `source` string and the
// derive NEVER infers an edge from mere co-presence (Pitfall 2).
//
// Discipline mirrors boardDerive.ts: no Solid imports, no produce/structuredClone,
// plain reads + object literals, null guard first — so the function is
// fixture-tested directly and the no-fake-signal guard is load-bearing.

import { cardsFromRunData, deriveColumn } from '../../org/boardDerive';
import type { RunData } from '../../org/types';
import type { LiveOverlayEntry } from '../../org/live/sseClient';
import type { AttentionItem } from '../../org/attention/attentionQueue';

export interface SwarmNode {
  id: string;
  type: 'objective' | 'agent' | 'work' | 'artifact' | 'alert' | 'placeholder';
  runId: string;
  label: string;
  status?: string;
}

export interface SwarmEdge {
  id: string;
  from: string;
  to: string;
  type: 'delegation' | 'message' | 'tool-call' | 'file-edit' | 'review' | 'blocker';
  /** REQUIRED — a real source. The no-fake-signal guard asserts this is set. */
  source: string;
}

export interface SwarmRun {
  runData: RunData | null;
  liveOverlay: Record<string, LiveOverlayEntry>;
}

export interface SwarmGraph {
  nodes: SwarmNode[];
  edges: SwarmEdge[];
}

const objId = (runId: string) => `obj:${runId}`;
const agentId = (runId: string, role: string) => `agent:${runId}:${role}`;
const workId = (nodeId: string) => `work:${nodeId}`;
const artifactId = (runId: string, key: string) => `artifact:${runId}:${key}`;
const alertId = (itemId: string) => `alert:${itemId}`;

/**
 * Derive the Swarm Map graph from real signals only.
 *
 * - null/empty runs → { nodes: [], edges: [] } (never throws).
 * - null runData for a run → a single objective placeholder node, zero edges.
 * - every edge is constructed with an explicit, real `source` and only when
 *   both endpoints exist — no dangling edges, no co-presence inference.
 */
export function deriveSwarmGraph(
  runs: SwarmRun[],
  attentionItems: AttentionItem[],
): SwarmGraph {
  if (!runs || runs.length === 0) return { nodes: [], edges: [] };

  const nodes: SwarmNode[] = [];
  const edges: SwarmEdge[] = [];
  const nodeIds = new Set<string>();
  // node-id (session/card id) → runId, for resolving which run an alert belongs to.
  const cardRunIndex = new Map<string, string>();

  const addNode = (node: SwarmNode) => {
    nodes.push(node);
    nodeIds.add(node.id);
  };
  const addEdge = (edge: SwarmEdge) => {
    if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) return;
    edges.push(edge);
  };

  runs.forEach((run, i) => {
    const data = run.runData;
    const runId = data?.run_id ?? `run-${i}`;

    // --- null runData → honest objective placeholder only ---
    if (!data) {
      addNode({
        id: `placeholder:${runId}`,
        type: 'placeholder',
        runId,
        label: '—',
      });
      return;
    }

    // --- objective (center) — show the idea, never the raw run id (D-09) ---
    const idea = data.audit?.idea ?? data.run_final?.idea;
    addNode({
      id: objId(runId),
      type: 'objective',
      runId,
      label: idea ?? runId,
    });

    // --- agent nodes: one per UNIQUE role present on the session tree ---
    const roles = new Set<string>();
    for (const node of data.session_tree.nodes) {
      if (node.role !== null) roles.add(node.role);
    }
    for (const role of roles) {
      addNode({ id: agentId(runId, role), type: 'agent', runId, label: role });
    }
    // Missing-agent slot → honest placeholder (never a fabricated agent).
    if (roles.size === 0) {
      addNode({
        id: `placeholder:${runId}:agent`,
        type: 'placeholder',
        runId,
        label: '—',
      });
    }

    // --- work nodes: one per non-root card ---
    const cards = cardsFromRunData(data);
    for (const card of cards) {
      cardRunIndex.set(card.id, runId);
      addNode({
        id: workId(card.id),
        type: 'work',
        runId,
        label: card.title,
        status: card.column,
      });
    }

    // --- artifact nodes: audit review-sidecars with a real a_verification ---
    const sidecars = data.audit?.review_sidecars ?? {};
    for (const key in sidecars) {
      const ver = sidecars[key]?.a_verification;
      if (ver && ver.test_path_or_rubric) {
        addNode({
          id: artifactId(runId, key),
          type: 'artifact',
          runId,
          label: ver.test_path_or_rubric,
        });
      }
    }

    // --- edges from real transitions (NEVER co-presence) ---
    for (const node of data.session_tree.nodes) {
      for (const t of node.transitions) {
        // delegation: an explicit routing decision routed this card to a role.
        if (t.kind === 'em.routing') {
          addEdge({
            id: `delegation:${t.id}`,
            from: agentId(runId, t.chosen_role),
            to: workId(t.card_id),
            type: 'delegation',
            source: 'board_transition:em.routing',
          });
        }
        // review: a board transition carrying a real verdict snapshot.
        if (t.kind === 'board.transition' && t.verdict_snapshot !== null) {
          addEdge({
            id: `review:${node.id}`,
            from: objId(runId),
            to: workId(node.id),
            type: 'review',
            source: 'board_transition:verdict_snapshot',
          });
        }
      }
      // blocker: derived column Blocked or a killed terminal state.
      const blocked =
        deriveColumn(node) === 'Blocked' ||
        node.terminal_state?.exit_reason === 'killed';
      if (blocked && node.parent_run_id !== null) {
        addEdge({
          id: `blocker:${node.id}`,
          from: objId(runId),
          to: workId(node.id),
          type: 'blocker',
          source: 'board_transition:blocked',
        });
      }
    }

    // file-edit: a real audit a_verification artifact for a card.
    for (const key in sidecars) {
      const ver = sidecars[key]?.a_verification;
      if (ver && ver.test_path_or_rubric) {
        addEdge({
          id: `file-edit:${runId}:${key}`,
          from: nodeIds.has(workId(key)) ? workId(key) : objId(runId),
          to: artifactId(runId, key),
          type: 'file-edit',
          source: 'audit_artifact:a_verification',
        });
      }
    }
  });

  // --- alert nodes + edges: real attention-queue items only ---
  const firstRunId = runs[0].runData?.run_id ?? 'run-0';
  for (const item of attentionItems) {
    if (item.kind !== 'permission' && item.kind !== 'budget' && item.kind !== 'blocked') {
      continue;
    }
    const runId =
      (item.cardId && cardRunIndex.get(item.cardId)) ??
      (item.sessionNodeId && cardRunIndex.get(item.sessionNodeId)) ??
      firstRunId;
    addNode({
      id: alertId(item.id),
      type: 'alert',
      runId,
      label: item.summary,
      status: item.kind,
    });
    const edgeType =
      item.kind === 'permission'
        ? 'tool-call'
        : item.kind === 'budget'
          ? 'message'
          : 'blocker';
    const source =
      item.kind === 'permission'
        ? 'sse_event:permission.updated'
        : item.kind === 'budget'
          ? 'sse_event:budget.updated'
          : 'board_transition:blocked';
    addEdge({
      id: `alert:${item.id}`,
      from: objId(runId),
      to: alertId(item.id),
      type: edgeType,
      source,
    });
  }

  return { nodes, edges };
}
