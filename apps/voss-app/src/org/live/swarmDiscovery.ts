// V24 swarm surface — discover the active swarm from the agent registry (V25-03).
//
// V25 deliberately has no app-side swarm launch and no list-swarms endpoint. But
// V25-03 added swarm_id/role/owned_files to agent_registry, surfaced on AgentEntry
// (camelCase swarmId/role/ownedFiles) via the existing `get_active_agents` command.
// So the active swarm is simply the swarm_id of any registered swarm agent. No new
// Tauri command needed — the registry IS the swarm index.

import { invoke } from '@tauri-apps/api/core';

// AgentEntry as serialized by agent_registry.rs (V25-03 added the swarm fields;
// the App.tsx interface predates them — declare the ones we need here).
interface RegistryAgent {
  sessionId: string;
  swarmId?: string | null;
  role?: string | null;
  ownedFiles?: string | null;
}

/**
 * Return the swarm_id of the most-recent registered swarm agent in the workspace,
 * or null if none is swarm-bound. Never throws (registry absence → null).
 */
export async function discoverActiveSwarmId(
  workspacePath: string | null,
): Promise<string | null> {
  const entries = await invoke<RegistryAgent[]>('get_active_agents', {
    workspacePath,
  }).catch(() => [] as RegistryAgent[]);
  for (const e of entries) {
    if (e.swarmId && e.swarmId.trim()) return e.swarmId;
  }
  return null;
}
