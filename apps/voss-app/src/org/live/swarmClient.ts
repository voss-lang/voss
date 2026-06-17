// VADE2 (V24 swarm surface) — typed client for the V25 server-native swarm plane.
//
// Read-only snapshot of a swarm's authoritative state: GET /swarm/{id} →
// {v, swarm:{id, goal, cwd, roster:[Role], tasks:[Task]}}. This is the structure
// + task-state source of truth; live transitions ride the SSE bus (swarm.* events,
// handled in sseClient.ts / swarmLive.ts). The bearer token is the sole auth for
// the loopback server and rides the Authorization header only — never logged.

export interface SwarmRole {
  name: string;
  model: string;
  auth_pref: string;
}

export type SwarmTaskState = 'open' | 'assigned' | 'done';

export interface SwarmTask {
  id: string;
  goal: string;
  owned_files: string[];
  depends_on: string[];
  state: SwarmTaskState;
}

export interface SwarmSnapshot {
  id: string;
  goal: string;
  cwd: string;
  roster: SwarmRole[];
  tasks: SwarmTask[];
}

/**
 * Fetch a swarm's authoritative snapshot from the `voss serve` sidecar at
 * `baseUrl`. Throws on a non-OK response (404 = no such swarm).
 */
export async function fetchSwarm(
  baseUrl: string,
  token: string,
  swarmId: string,
): Promise<SwarmSnapshot> {
  const res = await fetch(`${baseUrl}/swarm/${encodeURIComponent(swarmId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`GET /swarm/${swarmId} failed: ${res.status}`);
  }
  const body = (await res.json()) as { v: number; swarm: SwarmSnapshot };
  return body.swarm;
}

/** One spawned roster session returned by POST /swarm (native roles only). */
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

/**
 * Create + spawn a swarm (POST /swarm). The server seeds the goal, builds the
 * default roster (coordinator + N builders + reviewer), spawns one in-process
 * session per native role (builders spawn-gated), and returns the swarm id + the
 * spawned sessions. The coordinator does NOT auto-run — the caller kicks it.
 */
export async function createSwarm(
  baseUrl: string,
  token: string,
  body: { goal: string; builders?: number; cwd?: string | null },
): Promise<CreateSwarmResult> {
  const res = await fetch(`${baseUrl}/swarm`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      goal: body.goal,
      builders: body.builders ?? 2,
      cwd: body.cwd ?? '.',
    }),
  });
  if (!res.ok) {
    throw new Error(`POST /swarm failed: ${res.status}`);
  }
  const out = (await res.json()) as { v: number; id: string; sessions: SpawnedSession[] };
  return { id: out.id, sessions: out.sessions ?? [] };
}