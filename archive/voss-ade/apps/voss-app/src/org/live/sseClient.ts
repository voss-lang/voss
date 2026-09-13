import { createSignal } from 'solid-js';

import { ingestEvent } from '../attention/attentionQueue';
import { ingestSwarmEvent } from './swarmLive';
import type { AgentEvent } from '../../../../../sdk/typescript/src/client/sse';
import { subscribeSidecarEvents } from './sidecarClient';

export interface LiveOverlayEntry {
  budget?: { spent: number; remaining: number; limit: number; unit: string };
  status?: string;
  confidence?: number;
  gate?: { gate: string; decision: string };
}

const [liveOverlay, setLiveOverlay] = createSignal<Record<string, LiveOverlayEntry>>(
  {},
);

function mergeOverlay(key: string, patch: LiveOverlayEntry): void {
  setLiveOverlay((prev) => ({
    ...prev,
    [key]: { ...prev[key], ...patch },
  }));
}

export interface GraphPatchEvent {
  edgeType: 'message' | 'tool-call' | 'blocker';
  fromNodeId: string;
  toNodeId: string;
  source: string; // REQUIRED — "sse_event:<type>"
  timestamp: number;
}

const MAX_GRAPH_PATCHES = 200;
const [liveGraphPatches, setLiveGraphPatches] = createSignal<GraphPatchEvent[]>([]);

function pushGraphPatch(patch: GraphPatchEvent): void {
  setLiveGraphPatches((prev) => {
    const next = [...prev, patch];
    return next.length > MAX_GRAPH_PATCHES
      ? next.slice(next.length - MAX_GRAPH_PATCHES)
      : next;
  });
}

const BLOCKING_GATE_DECISIONS = new Set([
  'block',
  'blocked',
  'fail',
  'deny',
  'reject',
]);

function emitGraphPatch(ev: AgentEvent, cardId: string | undefined): void {
  const key = sessionKeyOf(ev) ?? cardId ?? 'unknown';
  let edgeType: GraphPatchEvent['edgeType'];
  let source: string;

  switch (ev.type) {
    case 'permission.updated':
      edgeType = 'tool-call';
      source = 'sse_event:permission.updated';
      break;
    case 'budget.updated':
      if (!(ev.limit > 0 && ev.spent >= ev.limit)) return; // only real crossings
      edgeType = 'message';
      source = 'sse_event:budget.updated';
      break;
    case 'gate.updated':
      if (!BLOCKING_GATE_DECISIONS.has(ev.decision)) return;
      edgeType = 'blocker';
      source = 'sse_event:gate.updated';
      break;
    default:
      return;
  }

  pushGraphPatch({
    edgeType,
    fromNodeId: key,
    toNodeId: key,
    source,
    timestamp: Date.now(),
  });
}


const [liveLabel, setLiveLabel] = createSignal<'live' | 'snapshot'>('snapshot');

const [liveHandles, setLiveHandles] = createSignal<Set<string>>(new Set());

function sessionKeyOf(ev: AgentEvent): string | undefined {
  const withCorrelation = ev as AgentEvent & {
    sessionID?: string;
    session_id?: string;
  };
  return withCorrelation.sessionID ?? withCorrelation.session_id;
}

function applyOverlay(ev: AgentEvent): void {
  const key = sessionKeyOf(ev);
  if (key === undefined) return;

  switch (ev.type) {
    case 'budget.updated':
      mergeOverlay(key, {
        budget: {
          spent: ev.spent,
          remaining: ev.remaining,
          limit: ev.limit,
          unit: ev.unit,
        },
        status: 'running',
      });
      break;
    case 'confidence.updated':
      mergeOverlay(key, { confidence: ev.score });
      break;
    case 'gate.updated':
      mergeOverlay(key, { gate: { gate: ev.gate, decision: ev.decision } });
      break;
    case 'session.idle':
      mergeOverlay(key, { status: 'idle' });
      break;
    default:
      break;
  }
}


export interface ConnectLiveStreamArgs {
  sidecarId?: string;
  sessionId: string;
  cardId?: string;
  onEvent?: (ev: AgentEvent) => void;
  onEnd?: () => void;
  stream?: AsyncIterable<AgentEvent>;
}

export interface LiveStreamHandle {
  abort(): void;
}

export function connectLiveStream(args: ConnectLiveStreamArgs): LiveStreamHandle {
  const ac = new AbortController();
  const stream =
    args.stream ??
    subscribeSidecarEvents(
      args.sidecarId ?? '',
      args.sessionId,
      ac.signal,
    );

  setLiveLabel('live');
  setLiveHandles((prev) => new Set([...prev, args.sessionId]));

  void (async () => {
    try {
      for await (const ev of stream) {
        if (ac.signal.aborted) break;
        ingestEvent(ev, args.cardId ? { cardId: args.cardId } : {});
        applyOverlay(ev);
        emitGraphPatch(ev, args.cardId);
        ingestSwarmEvent(ev);
        args.onEvent?.(ev);
      }
    } catch {
    } finally {
      let remaining = 0;
      setLiveHandles((prev) => {
        const s = new Set(prev);
        s.delete(args.sessionId);
        remaining = s.size;
        return s;
      });
      setLiveLabel(remaining > 0 ? 'live' : 'snapshot');
      args.onEnd?.();
    }
  })();

  return {
    abort(): void {
      ac.abort();
      let remaining = 0;
      setLiveHandles((prev) => {
        const s = new Set(prev);
        s.delete(args.sessionId);
        remaining = s.size;
        return s;
      });
      setLiveLabel(remaining > 0 ? 'live' : 'snapshot');
    },
  };
}

export { liveLabel, liveOverlay, liveHandles, liveGraphPatches };

export function __resetLiveStream(): void {
  setLiveOverlay({});
  setLiveLabel('snapshot');
  setLiveHandles(new Set<string>());
  setLiveGraphPatches([]);
}
