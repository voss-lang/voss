import type { AgentEvent } from '../../../../../../sdk/typescript/src/client/sse';

export type MockAgentEvent = AgentEvent & { sessionID: string };

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
