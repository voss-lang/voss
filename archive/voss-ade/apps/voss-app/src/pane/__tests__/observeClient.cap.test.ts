import { describe, it, expect, vi, afterEach } from 'vitest';

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn().mockResolvedValue(null),
  Channel: class {},
}));

import { ObserveClient, type ObservePost } from '../observeClient';

const clients: ObserveClient[] = [];
afterEach(() => {
  for (const c of clients.splice(0)) c.dispose();
});

async function settle() {
  for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0));
}

describe('ObserveClient — tracked command cap', () => {
  it('evicts the oldest started command once 1000 are outstanding', async () => {
    const posted: string[] = [];
    const post: ObservePost = async (_sid, event) => {
      posted.push((event as { kind?: string; type?: string }).kind ?? String((event as { type?: string }).type));
    };
    const client = new ObserveClient({
      paneId: 'pane-cap',
      actor: 'developer',
      context: { repositoryId: 'repo-1', worktreeId: 'wt-1' },
      sidecarId: () => 'sc-1',
      post,
    });
    clients.push(client);

    for (let i = 0; i <= 1000; i++) {
      client.commandStarted({ cmd_id: `cmd-${i}`, argv_text: 'true', cwd: '/repo', at: 'now' });
    }
    await settle();
    const startedCount = posted.length;

    client.commandFinished({
      cmd_id: 'cmd-0',
      exit: 0,
      duration_ms: 1,
      output: new Uint8Array(),
      truncated: false,
    });
    await settle();
    expect(posted.length).toBe(startedCount);

    client.commandFinished({
      cmd_id: 'cmd-1000',
      exit: 0,
      duration_ms: 1,
      output: new Uint8Array(),
      truncated: false,
    });
    await settle();
    expect(posted.length).toBeGreaterThan(startedCount);
  });
});
