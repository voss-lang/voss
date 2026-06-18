// V24 swarm surface — no-fake-signal guard for the V25-plane derive.
//
// Every edge must carry a KNOWN_PLANE_SOURCE; a roster with no live signals
// yields only the declared structural edges (coordinator→role, source
// snapshot:roster) and never an inferred one.

import { describe, it, expect } from 'vitest';
import { deriveSwarmPlane, KNOWN_PLANE_SOURCE } from '../swarmPlaneDerive';
import type { SwarmSnapshot } from '../../../org/live/swarmClient';
import type { SwarmAssignment, SwarmGateEvent, SwarmNeedsOperatorEvent } from '../../../org/live/swarmLive';

function snapshot(over: Partial<SwarmSnapshot> = {}): SwarmSnapshot {
  return {
    id: 'sw1',
    goal: 'Ship the thing',
    cwd: '/repo',
    roster: [
      { name: 'coordinator', model: 'default', auth_pref: 'auto' },
      { name: 'builder-1', model: 'default', auth_pref: 'auto' },
      { name: 'builder-2', model: 'codex', auth_pref: 'auto' },
      { name: 'reviewer', model: 'default', auth_pref: 'auto' },
    ],
    tasks: [
      { id: 't1', goal: 'DIAG-A: direct-loop', owned_files: ['a.py'], depends_on: [], state: 'assigned' },
      { id: 't2', goal: 'DIAG-B: server alt-mode', owned_files: ['b.py'], depends_on: ['t1'], state: 'open' },
    ],
    ...over,
  };
}

const noLive = {
  assignments: {} as Record<string, SwarmAssignment>,
  gates: {} as Record<string, SwarmGateEvent>,
  operatorNeeds: {} as Record<string, SwarmNeedsOperatorEvent>,
};

describe('deriveSwarmPlane — honesty', () => {
  it('null/empty snapshot → empty graph, never throws', () => {
    expect(deriveSwarmPlane({ snapshot: null, ...noLive })).toEqual({ nodes: [], edges: [] });
    expect(
      deriveSwarmPlane({ snapshot: snapshot({ roster: [] }), ...noLive }),
    ).toEqual({ nodes: [], edges: [] });
  });

  it('roster-only run: coordinator hub + role chips, only structural roster edges', () => {
    const g = deriveSwarmPlane({ snapshot: snapshot(), ...noLive });
    const obj = g.nodes.find((n) => n.type === 'objective');
    expect(obj?.role).toBe('coordinator');
    expect(obj?.work).toBe('Ship the thing');
    // 1 coordinator + 2 builders + 1 reviewer
    expect(g.nodes.filter((n) => n.type === 'agent')).toHaveLength(3);
    // builder chips carry NO work line without an assignment (honest '—')
    expect(g.nodes.find((n) => n.role === 'builder-1')?.work).toBeUndefined();
    // every edge is coordinator→role, sourced from the declared roster
    expect(g.edges.every((e) => e.from === obj!.id)).toBe(true);
    expect(g.edges.every((e) => e.source === 'snapshot:roster')).toBe(true);
  });

  it('every edge carries a KNOWN_PLANE_SOURCE (full live run)', () => {
    const assignments: Record<string, SwarmAssignment> = {
      t1: { taskId: 't1', sessionId: 's-b1', role: 'builder-1', ownedFiles: ['a.py'] },
      t2: { taskId: 't2', sessionId: 's-b2', role: 'builder-2', ownedFiles: ['b.py'] },
    };
    const gates: Record<string, SwarmGateEvent> = {
      t2: { type: 'swarm.gate', swarm_id: 'sw1', task_id: 't2', gate_type: 'reviewer_reject', detail: 'no' },
    };
    const operatorNeeds: Record<string, SwarmNeedsOperatorEvent> = {
      t1: { type: 'swarm.needs_operator', swarm_id: 'sw1', task_id: 't1', session_id: 's-b1', tool_name: 'fs_write', path: 'c.py' },
    };
    const g = deriveSwarmPlane({ snapshot: snapshot(), assignments, gates, operatorNeeds });

    expect(g.edges.length).toBeGreaterThan(0);
    expect(g.edges.every((e) => typeof e.source === 'string' && e.source.length > 0)).toBe(true);
    expect(g.edges.every((e) => KNOWN_PLANE_SOURCE.test(e.source))).toBe(true);

    // assigned builder carries its real Task.goal as the work line
    expect(g.nodes.find((n) => n.role === 'builder-1')?.work).toBe('DIAG-A: direct-loop');
    // assignment upgrades the coordinator→builder edge source to the live event
    expect(g.edges.find((e) => e.id === 'edge:assign:builder-1')?.source).toBe('sse_event:swarm.assign');
    // operator escalation surfaces an alert node + blocker edge
    expect(g.nodes.some((n) => n.type === 'alert' && n.role === 'operator')).toBe(true);
  });

  it('never infers a dependency edge when an endpoint task is unassigned', () => {
    // t2 depends_on t1; only t2 assigned → no builder node for t1's owner → no dep edge
    const assignments: Record<string, SwarmAssignment> = {
      t2: { taskId: 't2', sessionId: 's-b2', role: 'builder-2', ownedFiles: ['b.py'] },
    };
    const g = deriveSwarmPlane({ snapshot: snapshot(), assignments, gates: {}, operatorNeeds: {} });
    expect(g.edges.find((e) => e.id.startsWith('edge:dep:'))).toBeUndefined();
  });
});
