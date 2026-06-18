// V24 swarm surface — pure derivation from the V25 server-native swarm plane.
//
// Supersedes the board-derived approximation (swarmMapDerive.ts) for real swarm
// runs. Same HONESTY constraint: every node/edge traces to a real signal —
//   - snapshot:roster      GET /swarm/{id} roster (the declared swarm structure)
//   - snapshot:task        GET /swarm/{id} task state
//   - snapshot:depends_on  GET /swarm/{id} task.depends_on
//   - sse_event:swarm.*    a live swarm event (assign/gate/needs_operator/worker_done)
// Missing signals stay undefined / become placeholders; edges are never inferred
// from mere co-presence (roster membership is a DECLARED relationship, not
// co-presence). No Solid imports, no produce — fixture-testable.

import type { SwarmNode, SwarmEdge, SwarmGraph } from './swarmMapDerive';
import type { SwarmSnapshot } from '../../org/live/swarmClient';
import type {
  SwarmAssignment,
  SwarmGateEvent,
  SwarmNeedsOperatorEvent,
} from '../../org/live/swarmLive';

/** The accepted plane source prefixes — the no-fake-signal guard asserts these. */
export const KNOWN_PLANE_SOURCE = /^(snapshot:(roster|task|depends_on)|sse_event:swarm\.)/;

export interface SwarmPlaneInput {
  snapshot: SwarmSnapshot | null;
  /** task_id → live assignment (builder↔task binding from swarm.assign). */
  assignments: Record<string, SwarmAssignment>;
  /** task_id → latest gate outcome (swarm.gate). */
  gates: Record<string, SwarmGateEvent>;
  /** task_id → open operator escalation (swarm.needs_operator). */
  operatorNeeds: Record<string, SwarmNeedsOperatorEvent>;
}

const isCoordinator = (name: string) => /^coord/i.test(name);
const isBuilder = (name: string) => /^build/i.test(name);
const isReviewer = (name: string) => /^review/i.test(name);

function roleTag(name: string): string {
  if (isCoordinator(name)) return 'CONTROLLER';
  if (isBuilder(name)) return 'BUILD';
  if (isReviewer(name)) return 'REVIEW';
  return name.toUpperCase();
}

function displayName(name: string, ordinal?: number): string {
  if (isCoordinator(name)) return 'Coordinator';
  if (isBuilder(name)) return ordinal != null ? `Builder ${ordinal}` : 'Builder';
  if (isReviewer(name)) return ordinal != null ? `Reviewer ${ordinal}` : 'Reviewer';
  return name;
}

/**
 * Derive the swarm graph from the V25 swarm plane. Null/empty snapshot →
 * { nodes: [], edges: [] } (never throws). Every node/edge carries a real source.
 */
export function deriveSwarmPlane(input: SwarmPlaneInput): SwarmGraph {
  const { snapshot, assignments, gates, operatorNeeds } = input;
  const nodes: SwarmNode[] = [];
  const edges: SwarmEdge[] = [];
  if (snapshot == null || snapshot.roster.length === 0) {
    return { nodes, edges };
  }

  const swarmId = snapshot.id;
  const taskById = new Map(snapshot.tasks.map((t) => [t.id, t]));
  // role-name → assignment (the live builder↔task binding is keyed by task; index by role).
  const assignByRole = new Map<string, SwarmAssignment>();
  for (const a of Object.values(assignments)) assignByRole.set(a.role, a);

  const objId = `obj:${swarmId}`;
  const nodeIds = new Set<string>();
  const add = (n: SwarmNode) => {
    nodes.push(n);
    nodeIds.add(n.id);
  };
  const addEdge = (e: SwarmEdge) => {
    if (!nodeIds.has(e.from) || !nodeIds.has(e.to)) return; // no dangling edges
    edges.push(e);
  };

  // --- Center: coordinator (objective). Always present so the graph has a hub. ---
  const coordRole = snapshot.roster.find((r) => isCoordinator(r.name));
  add({
    id: objId,
    type: 'objective',
    runId: swarmId,
    label: snapshot.goal || 'Coordinator',
    role: 'coordinator',
    work: snapshot.goal || undefined,
    model: coordRole?.model && coordRole.model !== 'default' ? coordRole.model : undefined,
    status: 'controller',
  });

  // --- Orbit: builders + reviewer (+ any other non-coordinator role). ---
  let builderN = 0;
  let reviewerN = 0;
  for (const role of snapshot.roster) {
    if (isCoordinator(role.name)) continue;
    const ordinal = isBuilder(role.name)
      ? ++builderN
      : isReviewer(role.name)
        ? ++reviewerN
        : undefined;
    const assignment = assignByRole.get(role.name);
    const task = assignment ? taskById.get(assignment.taskId) : undefined;
    const id = `agent:${swarmId}:${role.name}`;
    add({
      id,
      type: 'agent',
      runId: swarmId,
      label: displayName(role.name, ordinal),
      role: role.name,
      work: task?.goal,
      ordinal,
      model: role.model && role.model !== 'default' ? role.model : undefined,
      sessionId: assignment?.sessionId,
      ownedFiles: task?.owned_files ?? assignment?.ownedFiles,
      status: task?.state ?? (isReviewer(role.name) ? 'reviewer' : 'waiting'),
    });

    // coordinator → role edge. Assigned builders carry a live source; otherwise
    // the roster membership (a declared swarm-structure signal) is the source.
    addEdge({
      id: `edge:assign:${role.name}`,
      from: objId,
      to: id,
      type: isReviewer(role.name) ? 'review' : 'delegation',
      source: assignment ? 'sse_event:swarm.assign' : 'snapshot:roster',
    });
  }

  // --- depends_on between assigned tasks → edge between their builder chips. ---
  for (const task of snapshot.tasks) {
    for (const dep of task.depends_on) {
      const aFrom = Object.values(assignments).find((a) => a.taskId === dep);
      const aTo = Object.values(assignments).find((a) => a.taskId === task.id);
      if (!aFrom || !aTo) continue;
      addEdge({
        id: `edge:dep:${dep}->${task.id}`,
        from: `agent:${swarmId}:${aFrom.role}`,
        to: `agent:${swarmId}:${aTo.role}`,
        type: 'message',
        source: 'snapshot:depends_on',
      });
    }
  }

  // --- Operator escalation → alert node + blocker edge from the blocked builder. ---
  const opNeeds = Object.values(operatorNeeds);
  if (opNeeds.length > 0) {
    const opId = `alert:operator:${swarmId}`;
    const first = opNeeds[0];
    add({
      id: opId,
      type: 'alert',
      runId: swarmId,
      label: 'Operator',
      role: 'operator',
      work: first.path ? `${first.tool_name} → ${first.path}` : first.tool_name,
      status: 'needs-operator',
    });
    for (const need of opNeeds) {
      const a = assignments[need.task_id];
      const from = a ? `agent:${swarmId}:${a.role}` : objId;
      addEdge({
        id: `edge:op:${need.task_id}`,
        from,
        to: opId,
        type: 'blocker',
        source: 'sse_event:swarm.needs_operator',
      });
    }
  }

  // --- Reviewer-reject gates → blocker edge coordinator → the rejected builder. ---
  for (const gate of Object.values(gates)) {
    if (gate.gate_type !== 'reviewer_reject') continue;
    const a = assignments[gate.task_id];
    if (!a) continue;
    addEdge({
      id: `edge:gate:${gate.task_id}`,
      from: objId,
      to: `agent:${swarmId}:${a.role}`,
      type: 'blocker',
      source: 'sse_event:swarm.gate',
    });
  }

  return { nodes, edges };
}

export { roleTag, displayName };
