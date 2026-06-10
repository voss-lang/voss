import { describe, it, expect, vi, afterEach } from 'vitest';

import { createVossClient } from '../../../../../../sdk/typescript/src/client/rest';
import { buildVossClientFromHandshake } from '../vossClientBuild';

// V15-02 (VLIVE-02): the factory builds the V13.1 client from the Plan-01
// {port, token} handshake and adapts it to the two injectable V14 seams:
// RunCommandBar's RunNativeClient (createSession returns a bare STRING from
// rest.ts — Pitfall 1 — the seam expects {id}) and the drawer's FollowUpClient.

vi.mock('../../../../../../sdk/typescript/src/client/rest', () => ({
  createVossClient: vi.fn(),
}));

const mockCreateVossClient = vi.mocked(createVossClient);

function mockSdkClient() {
  return {
    createSession: vi.fn().mockResolvedValue('sess-abc123'),
    postMessage: vi.fn().mockResolvedValue({ status: 'accepted' }),
  } as unknown as ReturnType<typeof createVossClient>;
}

afterEach(() => {
  vi.clearAllMocks();
});

describe('buildVossClientFromHandshake — V15-02', () => {
  it('builds the client against http://127.0.0.1:<port> with the handshake token', () => {
    const sdk = mockSdkClient();
    mockCreateVossClient.mockReturnValueOnce(sdk);

    const built = buildVossClientFromHandshake({ port: 50123, token: 'tok-1' });

    expect(mockCreateVossClient).toHaveBeenCalledWith(
      'http://127.0.0.1:50123',
      'tok-1',
    );
    expect(built.baseUrl).toBe('http://127.0.0.1:50123');
    expect(built.token).toBe('tok-1');
    expect(built.client).toBe(sdk);
  });

  it('runNativeClient.createSession wraps the bare string id as { id } (Pitfall 1)', async () => {
    const sdk = mockSdkClient();
    mockCreateVossClient.mockReturnValueOnce(sdk);

    const built = buildVossClientFromHandshake({ port: 50123, token: 'tok-1' });
    const result = await built.runNativeClient.createSession({
      goal: 'fix the bug',
      mode: 'Plan',
      team: 'solo',
      target: 'native',
    });

    expect(result).toEqual({ id: 'sess-abc123' });
    // rest.ts createSession(cwd?) — the goal is NOT a cwd; the session is
    // created in the server's own spawn cwd (the workspace, Plan 01).
    expect(sdk.createSession).toHaveBeenCalledWith();
  });

  it('followUpClient.postMessage delegates to client.postMessage', async () => {
    const sdk = mockSdkClient();
    mockCreateVossClient.mockReturnValueOnce(sdk);

    const built = buildVossClientFromHandshake({ port: 50123, token: 'tok-1' });
    await built.followUpClient.postMessage('sess-abc123', 'looks wrong, retry');

    expect(sdk.postMessage).toHaveBeenCalledWith(
      'sess-abc123',
      'looks wrong, retry',
    );
  });
});
