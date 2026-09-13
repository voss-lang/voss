import { invoke } from '@tauri-apps/api/core';

interface RegistryAgent {
  sessionId: string;
  swarmId?: string | null;
  role?: string | null;
  ownedFiles?: string | null;
}

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
