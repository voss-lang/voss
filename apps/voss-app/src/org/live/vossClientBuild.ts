// V15-02 (VLIVE-02) — build the V13.1 TS client from the Plan-01 sidecar
// handshake and adapt it to the two injectable V14 seams. Pure factory: no
// signals, no side effects; App owns the lifecycle (one client per workspace).
//
// T-V15-03: the client is constructed ONLY via createVossClient, whose
// middleware sets `Authorization: Bearer <token>` on every request including
// the SSE GET — never a raw fetch/EventSource. T-V15-10: the token is carried
// in-memory for connectLiveStream; never log or persist it.

import {
  createVossClient,
  type VossClient,
} from '../../../../../sdk/typescript/src/client/rest';
import type { RunNativeClient } from '../cockpit/RunCommandBar';
import type { FollowUpClient } from '../feedbackWritePath';

export interface BuiltVossClient {
  client: VossClient;
  baseUrl: string;
  token: string;
  /** RunCommandBar seam — adapts rest.ts's bare-string createSession to the
   *  {id} shape the bar expects (Pitfall 1). */
  runNativeClient: RunNativeClient;
  /** Drawer follow-up seam (feedbackWritePath postMessage). */
  followUpClient: FollowUpClient;
}

export function buildVossClientFromHandshake(handshake: {
  port: number;
  token: string;
}): BuiltVossClient {
  const baseUrl = `http://127.0.0.1:${handshake.port}`;
  const client = createVossClient(baseUrl, handshake.token);

  return {
    client,
    baseUrl,
    token: handshake.token,
    runNativeClient: {
      // rest.ts createSession(cwd?) — the spec goal is NOT a cwd; omit the
      // arg so the session lands in the server's own spawn cwd (the
      // workspace, Plan 01). Pitfall 1: wrap the bare string id as {id}.
      createSession: async () => ({ id: await client.createSession() }),
    },
    followUpClient: {
      postMessage: (sessionId, text) => client.postMessage(sessionId, text),
    },
  };
}
