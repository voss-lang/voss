import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => {
  const channels: Array<{ onmessage: ((m: unknown) => void) | null }> = [];
  return {
    channels,
    invoke: vi.fn().mockResolvedValue('sess-1'),
    ChannelMock: class {
      onmessage: ((m: unknown) => void) | null = null;
      constructor() {
        channels.push(this);
      }
    },
  };
});

vi.mock('@tauri-apps/api/core', () => ({
  invoke: h.invoke,
  Channel: h.ChannelMock,
}));

import { PtyTransport } from '../pty-ipc';

beforeEach(() => {
  h.invoke.mockClear();
  h.channels.length = 0;
});

function lastChannel() {
  return h.channels[h.channels.length - 1];
}

describe('PtyTransport — shell-integration command marks', () => {
  it('forwards command_started and command_finished to the option callbacks', () => {
    const started: unknown[] = [];
    const finished: unknown[] = [];
    new PtyTransport({
      write: () => {},
      onCommandStarted: (ev) => started.push(ev),
      onCommandFinished: (ev) => finished.push(ev),
    });
    const ch = lastChannel();
    ch.onmessage!({
      type: 'command_started',
      cmd_id: 'c1',
      argv_text: 'ls -la',
      cwd: '/repo',
      at: '2026-09-12T00:00:00Z',
    });
    ch.onmessage!({
      type: 'command_finished',
      cmd_id: 'c1',
      exit: 0,
      duration_ms: 12,
      output: [104, 105],
      truncated: false,
    });

    expect(started).toEqual([
      { cmd_id: 'c1', argv_text: 'ls -la', cwd: '/repo', at: '2026-09-12T00:00:00Z' },
    ]);
    expect(finished).toHaveLength(1);
    const fin = finished[0] as { output: Uint8Array; exit: number; truncated: boolean };
    expect(fin.output).toBeInstanceOf(Uint8Array);
    expect(Array.from(fin.output)).toEqual([104, 105]);
    expect(fin.exit).toBe(0);
    expect(fin.truncated).toBe(false);
  });

  it('ignores command marks when no callbacks are registered', () => {
    new PtyTransport({ write: () => {} });
    const ch = lastChannel();
    expect(() =>
      ch.onmessage!({ type: 'command_started', cmd_id: 'c1', argv_text: '', cwd: '', at: '' }),
    ).not.toThrow();
    expect(() =>
      ch.onmessage!({
        type: 'command_finished',
        cmd_id: 'c1',
        exit: 1,
        duration_ms: 0,
        output: [],
        truncated: true,
      }),
    ).not.toThrow();
  });

  it('spawn passes shellIntegration through and defaults it to false', async () => {
    const t = new PtyTransport({ write: () => {} });
    await t.spawn({ rows: 24, cols: 80, cwd: '/repo', shellIntegration: true });
    expect(h.invoke).toHaveBeenLastCalledWith(
      'spawn_pty',
      expect.objectContaining({ cwd: '/repo', shellIntegration: true }),
    );

    await t.spawn({ rows: 24, cols: 80 });
    expect(h.invoke).toHaveBeenLastCalledWith(
      'spawn_pty',
      expect.objectContaining({ shellIntegration: false }),
    );
  });
});
