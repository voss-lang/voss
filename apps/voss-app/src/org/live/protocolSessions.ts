import { createSignal } from 'solid-js';

import type { AgentEvent } from '../../../../../sdk/typescript/src/client/sse';
import {
  replyPermission,
  type PermissionChoice,
} from '../../../../../sdk/typescript/src/client/permission';
import { createVossClient } from '../../../../../sdk/typescript/src/client/rest';
import { connectLiveStream, type LiveStreamHandle } from './sseClient';
import { resolveAttentionItem } from '../attention/attentionQueue';

export type GateState =
  | { state: 'pending' }
  | { state: 'inflight'; choice: PermissionChoice }
  | { state: 'resolved'; choice: PermissionChoice };

export type ProtoBootState = 'booting' | 'live' | 'ended' | 'error';

export interface ProtocolSessionState {
  events: AgentEvent[];
  gateStates: Record<string, GateState>;
  bootState: ProtoBootState;
  errorMsg: string;

  died: boolean;
  sawCleanEnd: boolean;
  eventCount: number;

  endedReason: 'idle' | 'death' | null;
  conn: { baseUrl: string; token: string };
}

export const PROTO_CAP = 300;

export function trimOldest(list: AgentEvent[], cap: number): AgentEvent[] {
  if (list.length <= cap) return list;
  const out = [...list];
  let i = 0;
  while (out.length > cap && i < out.length) {
    const e = out[i];
    const pinnedTask = i === 0 && e.type === 'user';
    const pinnedPermission = e.type === 'permission.updated';
    if (pinnedTask || pinnedPermission) {
      i += 1;
      continue;
    }
    out.splice(i, 1);
  }
  return out;
}

const [protocolSessions, setProtocolSessions] = createSignal<
  Record<string, ProtocolSessionState>
>({});

const handles = new Map<string, LiveStreamHandle>();
const epochs = new Map<string, number>();

export function defaultProtocolState(conn: {
  baseUrl: string;
  token: string;
}): ProtocolSessionState {
  return {
    events: [],
    gateStates: {},
    bootState: 'booting',
    errorMsg: '',
    died: false,
    sawCleanEnd: false,
    eventCount: 0,
    endedReason: null,
    conn,
  };
}

function appendEvent(sessionId: string, epoch: number, ev: AgentEvent): void {
  if (epochs.get(sessionId) !== epoch) return; // stale stream
  setProtocolSessions((prev) => {
    const st = prev[sessionId];
    if (!st) return prev;
    const next: ProtocolSessionState = { ...st };
    next.eventCount = st.eventCount + 1;
    if (st.bootState === 'booting') next.bootState = 'live';
    if (ev.type === 'session.idle' || ev.type === 'final') {
      next.sawCleanEnd = true;
    }
    if (ev.type === 'session.idle') {
      next.endedReason = st.endedReason ?? 'idle';
    }
    next.events = trimOldest([...st.events, ev], PROTO_CAP);
    return { ...prev, [sessionId]: next };
  });
}

function streamEnded(sessionId: string, epoch: number): void {
  if (epochs.get(sessionId) !== epoch) return; // aborted by reconnect/destroy
  handles.delete(sessionId);
  setProtocolSessions((prev) => {
    const st = prev[sessionId];
    if (!st) return prev;
    const next: ProtocolSessionState = { ...st };
    if (st.bootState === 'booting' && st.eventCount === 0) {
      next.bootState = 'error';
      next.errorMsg = 'stream did not connect';
    } else {
      next.bootState = 'ended';
      if (!st.sawCleanEnd) {
        next.died = true;
        next.endedReason = 'death';
      } else {
        next.endedReason = st.endedReason ?? 'idle';
      }
    }
    return { ...prev, [sessionId]: next };
  });
}

function connect(
  sessionId: string,
  baseUrl: string,
  token: string,
  stream?: AsyncIterable<AgentEvent>,
): void {
  const epoch = (epochs.get(sessionId) ?? 0) + 1;
  epochs.set(sessionId, epoch);
  const handle = connectLiveStream({
    baseUrl,
    sessionId,
    token,
    cardId: sessionId, // Bridge A: the session id IS the cardId
    stream,
    onEvent: (ev) => appendEvent(sessionId, epoch, ev),
    onEnd: () => streamEnded(sessionId, epoch),
  });
  handles.set(sessionId, handle);
}

export function ensureProtocolStream(
  sessionId: string,
  baseUrl: string,
  token: string,
  stream?: AsyncIterable<AgentEvent>,
): void {
  setProtocolSessions((prev) =>
    prev[sessionId]
      ? prev
      : { ...prev, [sessionId]: defaultProtocolState({ baseUrl, token }) },
  );
  if (handles.has(sessionId)) return;
  connect(sessionId, baseUrl, token, stream);
}

export function reconnectProtocolStream(
  sessionId: string,
  baseUrl: string,
  token: string,
): void {
  handles.get(sessionId)?.abort();
  handles.delete(sessionId);
  setProtocolSessions((prev) => {
    const st = prev[sessionId] ?? defaultProtocolState({ baseUrl, token });
    return {
      ...prev,
      [sessionId]: {
        ...st,
        bootState: 'booting',
        errorMsg: '',
        died: false,
        sawCleanEnd: false,
        eventCount: 0,
        endedReason: null,
        conn: { baseUrl, token },
      },
    };
  });
  connect(sessionId, baseUrl, token);
}

export async function replyToProtocolGate(
  sessionId: string,
  id: string,
  choice: PermissionChoice,
): Promise<void> {
  const st = protocolSessions()[sessionId];
  if (!st) return;
  const current = st.gateStates[id];
  if (current && current.state !== 'pending') return; // in-flight/resolved
  const setGate = (g: GateState) =>
    setProtocolSessions((prev) => {
      const cur = prev[sessionId];
      if (!cur) return prev;
      return {
        ...prev,
        [sessionId]: {
          ...cur,
          gateStates: { ...cur.gateStates, [id]: g },
        },
      };
    });
  setGate({ state: 'inflight', choice });
  try {
    const client = createVossClient(st.conn.baseUrl, st.conn.token);
    await replyPermission(client, sessionId, { id, choice });
    setGate({ state: 'resolved', choice });
    resolveAttentionItem(`permission:${id}`);
  } catch {
    setGate({ state: 'pending' });
  }
}

export function destroyProtocolSession(sessionId: string): void {
  epochs.delete(sessionId); // fence the aborted stream's finally
  handles.get(sessionId)?.abort();
  handles.delete(sessionId);
  setProtocolSessions((prev) => {
    if (!(sessionId in prev)) return prev;
    const next = { ...prev };
    delete next[sessionId];
    return next;
  });
}

export { protocolSessions };

export function __resetProtocolSessions(): void {
  for (const [, h] of handles) h.abort();
  handles.clear();
  epochs.clear();
  setProtocolSessions({});
}
