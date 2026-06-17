// V24 swarm surface — launchSwarm orchestration: create → activate → stream → kick.

import { afterEach, describe, expect, it, vi } from 'vitest';

const createSwarm = vi.fn();
const connectLiveStream = vi.fn((_args?: unknown) => ({ abort: vi.fn() }));

vi.mock('../swarmClient', () => ({
  createSwarm: (baseUrl: string, token: string, body: unknown) =>
    createSwarm(baseUrl, token, body),
}));
vi.mock('../sseClient', () => ({
  connectLiveStream: (args: unknown) => connectLiveStream(args),
}));

import { launchSwarm } from '../swarmLaunch';
import { activeSwarmId, __resetSwarmLive } from '../swarmLive';

afterEach(() => {
  __resetSwarmLive();
  createSwarm.mockReset();
  connectLiveStream.mockReset();
});

describe('launchSwarm', () => {
  it('creates the swarm, marks it active, streams native sessions, kicks the coordinator', async () => {
    createSwarm.mockResolvedValue({
      id: 'sw9',
      sessions: [
        { session_id: 's-co', role: 'coordinator' },
        { session_id: 's-b1', role: 'builder-1' },
        { role: 'cli-builder', pending: true }, // non-native: no session_id
      ],
    });
    const postMessage = vi.fn().mockResolvedValue(undefined);
    const srv = { baseUrl: 'http://x', token: 't', cwd: '/repo', followUpClient: { postMessage } };

    const id = await launchSwarm(srv, { goal: 'ship it', builders: 2 });

    expect(id).toBe('sw9');
    expect(activeSwarmId()).toBe('sw9');
    expect(createSwarm).toHaveBeenCalledWith('http://x', 't', {
      goal: 'ship it',
      builders: 2,
      cwd: '/repo',
    });
    // streams only the 2 native sessions (pending CLI role skipped)
    expect(connectLiveStream).toHaveBeenCalledTimes(2);
    // coordinator kicked with the goal
    expect(postMessage).toHaveBeenCalledWith('s-co', 'ship it');
  });

  it('propagates a creation failure (e.g. no credentials)', async () => {
    createSwarm.mockRejectedValue(new Error('POST /swarm failed: 400'));
    const srv = { baseUrl: 'http://x', token: 't', cwd: '/repo' };
    await expect(launchSwarm(srv, { goal: 'g', builders: 2 })).rejects.toThrow(/400/);
    expect(activeSwarmId()).toBeNull();
  });
});
