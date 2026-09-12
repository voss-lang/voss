import { createSignal } from 'solid-js';

export interface SwarmAssignEvent {
  type: 'swarm.assign';
  eid?: string;
  swarm_id: string;
  task_id: string;
  session_id: string;
  owned_files: string[];
  role: string;
}
export interface SwarmWorkerDoneEvent {
  type: 'swarm.worker_done';
  eid?: string;
  swarm_id: string;
  task_id: string;
  session_id: string;
  summary?: string | null;
}
export interface SwarmGateEvent {
  type: 'swarm.gate';
  eid?: string;
  swarm_id: string;
  task_id: string;
  gate_type: string; // "ownership_denied" | "reviewer_reject"
  detail: string;
}
export interface SwarmNeedsOperatorEvent {
  type: 'swarm.needs_operator';
  eid?: string;
  swarm_id: string;
  task_id: string;
  session_id: string;
  tool_name: string;
  path?: string | null;
}
export interface SwarmCompleteEvent {
  type: 'swarm.complete';
  eid?: string;
  swarm_id: string;
  task_count: number;
  summary?: string | null;
}
export interface SwarmCandidateReadyEvent {
  type: 'swarm.candidate_ready';
  eid?: string;
  swarm_id: string;
  task_id: string;
  role: string;
  branch: string;
  worktree: string;
  head: string;
  summary?: string | null;
}
export interface SwarmCandidatesReadyEvent {
  type: 'swarm.candidates_ready';
  eid?: string;
  swarm_id: string;
  candidate_count: number;
}

export type SwarmEvent =
  | SwarmAssignEvent
  | SwarmWorkerDoneEvent
  | SwarmGateEvent
  | SwarmNeedsOperatorEvent
  | SwarmCandidateReadyEvent
  | SwarmCandidatesReadyEvent
  | SwarmCompleteEvent;

/** The binding the GET /swarm snapshot omits: which session/role owns a task */
export interface SwarmAssignment {
  taskId: string;
  sessionId: string;
  role: string;
  ownedFiles: string[];
}

/** A live swarm edge for the guarded pulse / EventTrace fallback. Honest source */
export interface SwarmLiveEdge {
  type: 'assign' | 'worker_done' | 'gate' | 'needs_operator' | 'candidate_ready';
  taskId: string;
  sessionId: string | null;
  source: string; // "sse_event:swarm.<type>"
  timestamp: number;
}

const MAX_LIVE_EDGES = 200;

const MAX_SEEN_EIDS = 1024;
const seenEids = new Set<string>();
const seenEidOrder: string[] = [];

// task_id → latest assignment (builder↔task binding).
const [swarmAssignments, setSwarmAssignments] = createSignal<
  Record<string, SwarmAssignment>
>({});
// task_id → open operator escalation (latest wins; cleared on that task's worker_done).
const [swarmOperatorNeeds, setSwarmOperatorNeeds] = createSignal<
  Record<string, SwarmNeedsOperatorEvent>
>({});
// task_id → latest gate outcome.
const [swarmGates, setSwarmGates] = createSignal<Record<string, SwarmGateEvent>>({});
// task_ids reported done via worker_done (snapshot state is authoritative; this is liveness).
const [swarmDone, setSwarmDone] = createSignal<Set<string>>(new Set());
// swarm_id → completion (task_count + summary) once swarm.complete arrives.
const [swarmComplete, setSwarmComplete] = createSignal<
  Record<string, SwarmCompleteEvent>
>({});
// task_id → immutable CLI candidate awaiting explicit review/integration.
const [swarmCandidateReady, setSwarmCandidateReady] = createSignal<
  Record<string, SwarmCandidateReadyEvent>
>({});
// swarm_id → aggregate signal that one or more candidates remain unintegrated.
const [swarmCandidatesReady, setSwarmCandidatesReady] = createSignal<
  Record<string, SwarmCandidatesReadyEvent>
>({});
// bounded ring of recent live edges (for pulse + EventTrace parity).
const [swarmLiveEdges, setSwarmLiveEdges] = createSignal<SwarmLiveEdge[]>([]);
const [swarmEventSeq, setSwarmEventSeq] = createSignal(0);
const [activeSwarmId, setActiveSwarmId] = createSignal<string | null>(null);

function pushLiveEdge(edge: SwarmLiveEdge): void {
  setSwarmLiveEdges((prev) => {
    const next = [...prev, edge];
    return next.length > MAX_LIVE_EDGES
      ? next.slice(next.length - MAX_LIVE_EDGES)
      : next;
  });
}

function isSwarmEvent(ev: unknown): ev is SwarmEvent {
  return (
    typeof ev === 'object' &&
    ev !== null &&
    typeof (ev as { type?: unknown }).type === 'string' &&
    (ev as { type: string }).type.startsWith('swarm.')
  );
}

/**
 * Route one SSE event into the live swarm store. No-op for non-swarm events, so
 * sseClient can call it unconditionally in its for-await loop. `ts` is injectable
 */
export function ingestSwarmEvent(ev: unknown, ts: number = Date.now()): void {
  if (!isSwarmEvent(ev)) return;

  // Drop broadcast duplicates: the same logical event reaches us once per swarm
  // member. Skip BEFORE any state mutation (seq bump, edge push) so a 4-member
  // swarm doesn't quadruple the live ring or fire 4 redundant snapshot refetches.
  const eid = ev.eid;
  if (eid) {
    if (seenEids.has(eid)) return;
    seenEids.add(eid);
    seenEidOrder.push(eid);
    if (seenEidOrder.length > MAX_SEEN_EIDS) {
      const evicted = seenEidOrder.shift();
      if (evicted !== undefined) seenEids.delete(evicted);
    }
  }

  setSwarmEventSeq((n) => n + 1);

  switch (ev.type) {
    case 'swarm.assign':
      setSwarmAssignments((prev) => ({
        ...prev,
        [ev.task_id]: {
          taskId: ev.task_id,
          sessionId: ev.session_id,
          role: ev.role,
          ownedFiles: ev.owned_files ?? [],
        },
      }));
      pushLiveEdge({
        type: 'assign',
        taskId: ev.task_id,
        sessionId: ev.session_id,
        source: 'sse_event:swarm.assign',
        timestamp: ts,
      });
      break;
    case 'swarm.worker_done':
      setSwarmDone((prev) => new Set([...prev, ev.task_id]));
      // A finished task resolves any operator escalation it raised — the server
      // resolves the block over the permission channel (no swarm.* clear event),
      // so worker_done is the honest signal to drop the stale alert. Without
      // this the swarm map shows an "Operator" alert forever after the gate is
      // answered.
      setSwarmOperatorNeeds((prev) => {
        if (!(ev.task_id in prev)) return prev;
        const next = { ...prev };
        delete next[ev.task_id];
        return next;
      });
      pushLiveEdge({
        type: 'worker_done',
        taskId: ev.task_id,
        sessionId: ev.session_id,
        source: 'sse_event:swarm.worker_done',
        timestamp: ts,
      });
      break;
    case 'swarm.gate':
      setSwarmGates((prev) => ({ ...prev, [ev.task_id]: ev }));
      pushLiveEdge({
        type: 'gate',
        taskId: ev.task_id,
        sessionId: null,
        source: 'sse_event:swarm.gate',
        timestamp: ts,
      });
      break;
    case 'swarm.needs_operator':
      setSwarmOperatorNeeds((prev) => ({ ...prev, [ev.task_id]: ev }));
      pushLiveEdge({
        type: 'needs_operator',
        taskId: ev.task_id,
        sessionId: ev.session_id,
        source: 'sse_event:swarm.needs_operator',
        timestamp: ts,
      });
      break;
    case 'swarm.candidate_ready':
      setSwarmCandidateReady((prev) => ({ ...prev, [ev.task_id]: ev }));
      pushLiveEdge({
        type: 'candidate_ready',
        taskId: ev.task_id,
        sessionId: null,
        source: 'sse_event:swarm.candidate_ready',
        timestamp: ts,
      });
      break;
    case 'swarm.candidates_ready':
      setSwarmCandidatesReady((prev) => ({ ...prev, [ev.swarm_id]: ev }));
      break;
    case 'swarm.complete':
      setSwarmComplete((prev) => ({ ...prev, [ev.swarm_id]: ev }));
      break;
    default:
      break;
  }
}

export {
  swarmAssignments,
  swarmOperatorNeeds,
  swarmGates,
  swarmDone,
  swarmComplete,
  swarmCandidateReady,
  swarmCandidatesReady,
  swarmLiveEdges,
  swarmEventSeq,
  activeSwarmId,
  setActiveSwarmId,
};

/** Test-only reset (mirrors __resetLiveStream) */
export function __resetSwarmLive(): void {
  setSwarmAssignments({});
  setSwarmOperatorNeeds({});
  setSwarmGates({});
  setSwarmDone(new Set<string>());
  setSwarmComplete({});
  setSwarmCandidateReady({});
  setSwarmCandidatesReady({});
  setSwarmLiveEdges([]);
  setSwarmEventSeq(0);
  setActiveSwarmId(null);
  seenEids.clear();
  seenEidOrder.length = 0;
}
