import { afterEach, describe, expect, it, vi } from 'vitest';

import { invoke } from '@tauri-apps/api/core';
import { getObserveSettings, patchObserveSettings } from '../sidecarClient';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn(), Channel: class {} }));

const mockInvoke = vi.mocked(invoke);

const ENROLLMENT = {
  enabled: true,
  capture: true,
  analysis: false,
  provider: null,
  disclosure: true,
  budget_usd: null,
  paused: false,
};

afterEach(() => vi.clearAllMocks());

describe('getObserveSettings', () => {
  it('routes through the sidecar and unwraps the repositories map', async () => {
    mockInvoke.mockResolvedValueOnce({ repositories: { 'repo-1': ENROLLMENT } });
    const repos = await getObserveSettings('sc-1');

    expect(mockInvoke).toHaveBeenCalledWith('call_voss_sidecar', {
      sidecarId: 'sc-1',
      operation: { kind: 'observe_settings_get' },
    });
    expect(repos).toEqual({ 'repo-1': ENROLLMENT });
  });

  it('rejects a response without a repositories object', async () => {
    mockInvoke.mockResolvedValueOnce({ nope: 1 });
    await expect(getObserveSettings('sc-1')).rejects.toThrow(
      'invalid observe settings response',
    );
    mockInvoke.mockResolvedValueOnce(null);
    await expect(getObserveSettings('sc-1')).rejects.toThrow(
      'invalid observe settings response',
    );
  });
});

describe('patchObserveSettings', () => {
  it('sends the partial enrollment and returns the stored enrollment', async () => {
    mockInvoke.mockResolvedValueOnce({ enrollment: { ...ENROLLMENT, paused: true } });
    const out = await patchObserveSettings('sc-1', 'repo-1', { paused: true });

    expect(mockInvoke).toHaveBeenCalledWith('call_voss_sidecar', {
      sidecarId: 'sc-1',
      operation: {
        kind: 'observe_settings_patch',
        repository_id: 'repo-1',
        enrollment: { paused: true },
      },
    });
    expect(out.paused).toBe(true);
  });

  it('rejects a response without an enrollment object', async () => {
    mockInvoke.mockResolvedValueOnce({ enrollment: 'yes' });
    await expect(patchObserveSettings('sc-1', 'repo-1', {})).rejects.toThrow(
      'invalid observe settings response',
    );
  });
});
