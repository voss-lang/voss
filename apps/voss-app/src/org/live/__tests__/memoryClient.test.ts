// VADE2-11 — fetchMemory issues the right authed GET and parses the response.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchMemory } from '../memoryClient';

const OK_BODY = { v: 1, summary: '# Memory', query: null, hits: [] };

afterEach(() => {
  vi.restoreAllMocks();
});

describe('fetchMemory', () => {
  it('GETs /memory with cwd + bearer auth, no query params when q absent', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify(OK_BODY), { status: 200 }));

    const out = await fetchMemory('http://127.0.0.1:5001', 'tok', '/repo');

    expect(out).toEqual(OK_BODY);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/memory?');
    expect(String(url)).toContain('cwd=%2Frepo');
    expect(String(url)).not.toContain('q=');
    expect((init as RequestInit).headers).toMatchObject({
      Authorization: 'Bearer tok',
    });
  });

  it('adds q + top_k when a query is given', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        new Response(
          JSON.stringify({ ...OK_BODY, query: 'rollout', hits: [] }),
          { status: 200 },
        ),
      );

    await fetchMemory('http://127.0.0.1:5001', 'tok', '/repo', 'rollout', 8);

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain('q=rollout');
    expect(url).toContain('top_k=8');
  });

  it('throws on a non-OK response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('nope', { status: 401 }),
    );
    await expect(
      fetchMemory('http://127.0.0.1:5001', 'tok', '/repo'),
    ).rejects.toThrow(/401/);
  });
});
