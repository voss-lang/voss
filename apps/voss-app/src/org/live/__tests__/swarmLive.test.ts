// V24 swarm surface — swarm.* SSE ingestion into the live store.

import { afterEach, describe, expect, it } from 'vitest';
import {
  ingestSwarmEvent,
  swarmAssignments,
  swarmGates,
  swarmOperatorNeeds,
  swarmComplete,
  swarmLiveEdges,
  __resetSwarmLive,
} from '../swarmLive';

afterEach(() => __resetSwarmLive());

describe('ingestSwarmEvent', () => {
  it('ignores non-swarm events', () => {
    ingestSwarmEvent({ type: 'budget.updated', spent: 1 });
    ingestSwarmEvent(null);
    ingestSwarmEvent({ nope: true });
    expect(Object.keys(swarmAssignments())).toHaveLength(0);
    expect(swarmLiveEdges()).toHaveLength(0);
  });

  it('records assign as the builder↔task binding + a live edge', () => {
    ingestSwarmEvent(
      {
        type: 'swarm.assign',
        swarm_id: 'sw1',
        task_id: 't1',
        session_id: 's-b1',
        owned_files: ['a.py'],
        role: 'builder-1',
      },
      1000,
    );
    expect(swarmAssignments().t1).toEqual({
      taskId: 't1',
      sessionId: 's-b1',
      role: 'builder-1',
      ownedFiles: ['a.py'],
    });
    expect(swarmLiveEdges()).toHaveLength(1);
    expect(swarmLiveEdges()[0]).toMatchObject({
      type: 'assign',
      source: 'sse_event:swarm.assign',
      timestamp: 1000,
    });
  });

  it('records gate, needs_operator, and complete', () => {
    ingestSwarmEvent({ type: 'swarm.gate', swarm_id: 'sw1', task_id: 't2', gate_type: 'reviewer_reject', detail: 'no' });
    ingestSwarmEvent({ type: 'swarm.needs_operator', swarm_id: 'sw1', task_id: 't1', session_id: 's-b1', tool_name: 'fs_write', path: 'c.py' });
    ingestSwarmEvent({ type: 'swarm.complete', swarm_id: 'sw1', task_count: 2, summary: 'done' });

    expect(swarmGates().t2?.gate_type).toBe('reviewer_reject');
    expect(swarmOperatorNeeds().t1?.path).toBe('c.py');
    expect(swarmComplete().sw1?.task_count).toBe(2);
  });

  it('bounds the live-edge ring', () => {
    for (let i = 0; i < 250; i++) {
      ingestSwarmEvent(
        { type: 'swarm.assign', swarm_id: 'sw1', task_id: `t${i}`, session_id: `s${i}`, owned_files: [], role: `r${i}` },
        i,
      );
    }
    expect(swarmLiveEdges().length).toBeLessThanOrEqual(200);
  });
});
