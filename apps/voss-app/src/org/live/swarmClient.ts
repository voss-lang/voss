import { callSidecar } from './sidecarClient';

export interface SwarmRole {
  name: string;
  model: string;
  auth_pref: string;
}

export type SwarmTaskState = 'open' | 'assigned' | 'candidate_ready' | 'done';

export interface SwarmTask {
  id: string;
  goal: string;
  owned_files: string[];
  depends_on: string[];
  state: SwarmTaskState;
  candidate_branch?: string | null;
  candidate_worktree?: string | null;
  candidate_head?: string | null;
}

export interface SwarmSnapshot {
  id: string;
  goal: string;
  cwd: string;
  roster: SwarmRole[];
  tasks: SwarmTask[];
}

export async function fetchSwarm(
  sidecarId: string,
  swarmId: string,
): Promise<SwarmSnapshot> {
  const body = await callSidecar<{ v: number; swarm: SwarmSnapshot }>(sidecarId, {
    kind: 'get_swarm',
    swarm_id: swarmId,
  });
  return body.swarm;
}

export interface SpawnedSession {
  session_id?: string; // present for native (in-process) roles
  role: string;
  model?: string;
  agent?: string;
  pending?: boolean; // non-native CLI role recorded but not spawned here
}

export interface CreateSwarmResult {
  id: string;
  sessions: SpawnedSession[];
}

export interface RoleSpecBody {
  name: string;

  agent: string;

  model: string;
}

export async function createSwarm(
  sidecarId: string,
  body: {
    goal: string;
    builders?: number;
    cwd?: string | null;
    roster?: RoleSpecBody[];
  },
): Promise<CreateSwarmResult> {
  const out = await callSidecar<{
    v: number;
    id: string;
    sessions: SpawnedSession[];
  }>(sidecarId, {
    kind: 'create_swarm',
    goal: body.goal,
    builders: body.builders ?? 2,
    ...(body.roster && body.roster.length > 0
      ? { roster: body.roster as unknown as Array<Record<string, unknown>> }
      : {}),
  });
  return { id: out.id, sessions: out.sessions ?? [] };
}

export async function runSwarm(
  sidecarId: string,
  swarmId: string,
): Promise<void> {
  await callSidecar(sidecarId, {
    kind: 'run_swarm',
    swarm_id: swarmId,
  });
}
