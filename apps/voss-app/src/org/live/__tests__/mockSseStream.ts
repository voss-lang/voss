// Mock SSE stream helper (V14 VCKP-06, Pitfall 4). An async-generator that
// yields a scripted sequence of `AgentEvent` objects so the cockpit's live
// wiring (sseClient) can be driven WITHOUT a real `voss serve` — the webview
// cannot spawn the server (Node-only launcher), only consume the stream.
//
// Each event is shaped exactly like the SDK's `AgentEvent` union (the field the
// generated OpenAPI types call `session_id`) AND additionally carries the
// PROTOCOL §6 correlation field name `sessionID` so downstream code can match
// events to a card/session by either spelling. The type below is the SDK union
// intersected with the explicit `sessionID` correlation field.

import type { AgentEvent } from '../../../../../../sdk/typescript/src/client/sse';

/** An AgentEvent that also carries the PROTOCOL §6 `sessionID` correlation key. */
export type MockAgentEvent = AgentEvent & { sessionID: string };

/**
 * Yield a scripted budget.updated → gate.updated sequence for one session.
 * Both events carry `session_id` (SDK union field) and `sessionID` (PROTOCOL
 * §6 correlation key) so VCKP-06 tests can match on either.
 *
 * @param sessionID the 12-hex harness session id to stamp on every event
 */
export async function* mockSseStream(
  sessionID = '0139377ff590',
): AsyncGenerator<MockAgentEvent> {
  yield {
    type: 'budget.updated',
    session_id: sessionID,
    sessionID,
    spent: 1200,
    remaining: 8800,
    limit: 10000,
    unit: 'tokens',
    v: 1,
  };

  yield {
    type: 'gate.updated',
    session_id: sessionID,
    sessionID,
    gate: 'plan',
    decision: 'approved',
    v: 1,
  };
}
