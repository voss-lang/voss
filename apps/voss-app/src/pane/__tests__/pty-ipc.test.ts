import { describe, it, expect, vi, beforeEach } from 'vitest';

// --- Mock @tauri-apps/api/core ----------------------------------------------
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

import {
  PtyTransport,
  HIGH_WATERMARK,
  LOW_WATERMARK,
  type PtyEvent,
} from '../pty-ipc';

// --- Controllable requestAnimationFrame -------------------------------------
let rafQueue: FrameRequestCallback[] = [];
beforeEach(() => {
  rafQueue = [];
  h.invoke.mockClear();
  h.channels.length = 0;
  globalThis.requestAnimationFrame = ((cb: FrameRequestCallback) => {
    rafQueue.push(cb);
    return rafQueue.length;
  }) as typeof requestAnimationFrame;
});
function flushRaf() {
  const q = rafQueue;
  rafQueue = [];
  for (const cb of q) cb(0);
}
function lastChannel() {
  return h.channels[h.channels.length - 1];
}
function dataEvent(len: number): PtyEvent {
  return { type: 'data', bytes: new Array(len).fill(65) };
}

describe('PtyTransport — D-02 coalescing + watermark', () => {
  it('coalesces N data events in one frame into exactly ONE write', () => {
    const writes: Uint8Array[] = [];
    const t = new PtyTransport({ write: (d) => writes.push(d) });
    void t;
    const ch = lastChannel();
    ch.onmessage!(dataEvent(3));
    ch.onmessage!(dataEvent(4));
    ch.onmessage!(dataEvent(5));
    expect(writes.length).toBe(0); // not written until the frame fires
    flushRaf();
    expect(writes.length).toBe(1); // exactly one merged write
    expect(writes[0].length).toBe(12); // 3 + 4 + 5 merged
  });

  it('pushing > HIGH_WATERMARK bytes (write cb not invoked) triggers pty_pause', async () => {
    const t = new PtyTransport({ write: () => {} }); // cb intentionally NOT called
    await t.spawn({ rows: 24, cols: 80 }); // sessionId required for backpressure
    const ch = lastChannel();
    ch.onmessage!(dataEvent(HIGH_WATERMARK + 1));
    flushRaf();
    expect(h.invoke).toHaveBeenCalledWith('pty_pause', { sessionId: 'sess-1' });
  });

  it('draining below LOW_WATERMARK via the write callback triggers pty_resume', async () => {
    let savedCb: (() => void) | undefined;
    const t = new PtyTransport({
      write: (_d, cb) => {
        savedCb = cb;
      },
    });
    await t.spawn({ rows: 24, cols: 80 });
    const ch = lastChannel();
    // Fill above HIGH so a pause is in flight, then drain via the cb.
    ch.onmessage!(dataEvent(HIGH_WATERMARK + LOW_WATERMARK));
    flushRaf();
    expect(savedCb).toBeTypeOf('function');
    savedCb!(); // merged write completed → watermark → 0 (< LOW)
    expect(h.invoke).toHaveBeenCalledWith('pty_resume', { sessionId: 'sess-1' });
  });
});
