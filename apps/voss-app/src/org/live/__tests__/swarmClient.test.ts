// V24 swarm surface — fetchSwarm issues the right authed GET and unwraps {swarm}.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchSwarm } from '../swarmClient';

const SWARM = {
  id: 'sw1',
  goal: 'ship',
  cwd: '/repo',
  roster: [{ name: 'coordinator', model: 'default', auth_pref: 'auto' }],
  tasks: [],
};

afterEach(() => vi.restoreAllMocks());

describe('fetchSwarm', () => {
  it('GETs /swarm/{id} with bearer auth and returns the swarm', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify({ v: 1, swarm: SWARM }), { status: 200 }));

    const out = await fetchSwarm('http://127.0.0.1:5001', 'tok', 'sw1');

    expect(out).toEqual(SWARM);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe('http://127.0.0.1:5001/swarm/sw1');
    expect((init as RequestInit).headers).toMatchObject({ Authorization: 'Bearer tok' });
  });

  it('throws on a non-OK response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('no', { status: 404 }));
    await expect(fetchSwarm('http://x', 't', 'missing')).rejects.toThrow(/404/);
  });
});
