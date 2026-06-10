import { describe, it, expect, vi, afterEach } from 'vitest';

import { invoke } from '@tauri-apps/api/core';
import { startVossServe } from '../sidecarClient';

// V15-01: the frontend sidecar wrapper is a thin typed invoke — it forwards
// the cwd to the `start_voss_serve` Tauri command, returns the {port, token}
// handshake verbatim, and never logs the token (T-V15-10).

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

const mockInvoke = vi.mocked(invoke);

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe('startVossServe — V15-01 sidecar invoke wrapper', () => {
  it("calls invoke('start_voss_serve', { cwd }) and returns the {port, token} handshake", async () => {
    mockInvoke.mockResolvedValueOnce({ port: 50123, token: 'secret-tok' });

    const handshake = await startVossServe('/some/cwd');

    expect(mockInvoke).toHaveBeenCalledTimes(1);
    expect(mockInvoke).toHaveBeenCalledWith('start_voss_serve', {
      cwd: '/some/cwd',
    });
    expect(handshake).toEqual({ port: 50123, token: 'secret-tok' });
  });

  it('propagates command errors (no swallow, no fallback handshake)', async () => {
    mockInvoke.mockRejectedValueOnce('workspace path does not exist');

    await expect(startVossServe('/missing')).rejects.toBe(
      'workspace path does not exist',
    );
  });

  it('never logs the token (T-V15-10)', async () => {
    const spies = (['log', 'info', 'warn', 'error', 'debug'] as const).map(
      (level) => vi.spyOn(console, level).mockImplementation(() => {}),
    );

    mockInvoke.mockResolvedValueOnce({ port: 50123, token: 'secret-tok' });
    const handshake = await startVossServe('/some/cwd');
    expect(handshake.token).toBe('secret-tok');

    for (const spy of spies) {
      for (const call of spy.mock.calls) {
        expect(JSON.stringify(call)).not.toContain('secret-tok');
      }
    }
  });
});
