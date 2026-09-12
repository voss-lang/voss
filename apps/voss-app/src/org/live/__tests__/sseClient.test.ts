import { describe, it, expect, afterEach } from 'vitest';

import { mockSseStream } from './mockSseStream';
import {
  connectLiveStream,
  liveLabel,
  liveOverlay,
  liveHandles,
  __resetLiveStream,
} from '../sseClient';
import {
  attentionQueue,
  __resetAttentionQueue,
} from '../../attention/attentionQueue';
import { __resetBridgeMaps } from '../../model/bridge';
import type { AgentEvent } from '../../../../../../sdk/typescript/src/client/sse';

const SESSION = '0139377ff590';

async function flush(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => {
  __resetLiveStream();
  __resetAttentionQueue();
  __resetBridgeMaps();
});

describe('live SSE consumer — VCKP-06 (../sseClient)', () => {
  it('mockSseStream yields >=2 typed AgentEvents, each carrying sessionID', async () => {
    const events = [];
    for await (const ev of mockSseStream(SESSION)) {
      events.push(ev);
    }

    expect(events.length).toBeGreaterThanOrEqual(2);
    for (const ev of events) {
      expect(ev.sessionID).toBe(SESSION);
      if (ev.type === 'budget.updated' || ev.type === 'gate.updated') {
        expect(ev.session_id).toBe(SESSION);
      }
    }

    const types = events.map((e) => e.type);
    expect(types).toContain('budget.updated');
    expect(types).toContain('gate.updated');
  });

  it('drives mockSseStream into ingestEvent + the live overlay with no manual refresh, label -> live', async () => {
    const handle = connectLiveStream({
      baseUrl: 'http://localhost:0',
      sessionId: SESSION,
      token: 'tok',
      stream: mockSseStream(SESSION),
    });

    expect(liveLabel()).toBe('live');

    await flush();

    const entry = liveOverlay()[SESSION];
    expect(entry).toBeDefined();
    expect(entry.budget).toEqual({
      spent: 1200,
      remaining: 8800,
      limit: 10000,
      unit: 'tokens',
    });
    expect(entry.gate).toEqual({ gate: 'plan', decision: 'approved' });

    const gateItem = attentionQueue().find((i) => i.kind === 'gate');
    expect(gateItem).toBeDefined();
    expect(gateItem?.summary).toContain('plan');

    handle.abort();
  });

  it("defaults to 'snapshot' with no stream and never throws (graceful degrade)", () => {
    expect(liveLabel()).toBe('snapshot');
    expect(() => liveOverlay()).not.toThrow();
    expect(liveOverlay()).toEqual({});
  });

  it('a budget.updated event updates the budget overlay with no manual refresh', async () => {
    async function* oneBudget(): AsyncGenerator<AgentEvent & { sessionID: string }> {
      yield {
        type: 'budget.updated',
        session_id: SESSION,
        sessionID: SESSION,
        spent: 4200,
        remaining: 5800,
        limit: 10000,
        unit: 'tokens',
        v: 1,
      };
    }

    const handle = connectLiveStream({
      baseUrl: 'http://localhost:0',
      sessionId: SESSION,
      token: 'tok',
      stream: oneBudget(),
    });

    await flush();

    expect(liveOverlay()[SESSION]?.budget?.spent).toBe(4200);
    handle.abort();
  });

  it('AbortController teardown stops the stream cleanly and resets label -> snapshot', async () => {
    let delivered = 0;
    async function* infinite(): AsyncGenerator<AgentEvent & { sessionID: string }> {
      while (true) {
        delivered += 1;
        yield {
          type: 'budget.updated',
          session_id: SESSION,
          sessionID: SESSION,
          spent: delivered,
          remaining: 1,
          limit: 10,
          unit: 'tokens',
          v: 1,
        };
        await new Promise((r) => setTimeout(r, 1));
      }
    }

    const handle = connectLiveStream({
      baseUrl: 'http://localhost:0',
      sessionId: SESSION,
      token: 'tok',
      stream: infinite(),
    });

    expect(liveLabel()).toBe('live');
    await flush();
    handle.abort();

    expect(liveLabel()).toBe('snapshot');

    await new Promise((r) => setTimeout(r, 10));
    const settled = delivered;
    await new Promise((r) => setTimeout(r, 20));
    expect(delivered).toBe(settled);
  });
});

describe('live SSE consumer — V15-02 extensions (../sseClient)', () => {
  it('onEvent receives every event from an injected stream', async () => {
    const seen: AgentEvent[] = [];
    const handle = connectLiveStream({
      baseUrl: 'http://localhost:0',
      sessionId: SESSION,
      token: 'tok',
      stream: mockSseStream(SESSION),
      onEvent: (ev) => seen.push(ev),
    });

    await flush();

    expect(seen.length).toBeGreaterThanOrEqual(2);
    expect(seen.map((e) => e.type)).toEqual(
      expect.arrayContaining(['budget.updated', 'gate.updated']),
    );
    handle.abort();
  });

  it('a permission.updated event with a cardId yields a queue row with a defined cardId (Pitfall 3)', async () => {
    async function* onePermission(): AsyncGenerator<AgentEvent> {
      yield {
        type: 'permission.updated',
        id: 'perm-1',
        tool_name: 'bash',
        args: { cmd: 'ls' },
        dimension: 'execution',
        v: 1,
      } as unknown as AgentEvent;
    }

    const handle = connectLiveStream({
      baseUrl: 'http://localhost:0',
      sessionId: SESSION,
      token: 'tok',
      cardId: 'card-77',
      stream: onePermission(),
    });

    await flush();

    const row = attentionQueue().find((i) => i.kind === 'permission');
    expect(row).toBeDefined();
    expect(row?.cardId).toBe('card-77');
    handle.abort();
  });

  it('liveHandles contains the sessionId during the stream and is empty after completion', async () => {
    let release: (() => void) | undefined;
    async function* heldOpen(): AsyncGenerator<AgentEvent> {
      yield {
        type: 'budget.updated',
        session_id: SESSION,
        spent: 1,
        remaining: 9,
        limit: 10,
        unit: 'tokens',
        v: 1,
      } as unknown as AgentEvent;
      await new Promise<void>((r) => {
        release = r;
      });
    }

    connectLiveStream({
      baseUrl: 'http://localhost:0',
      sessionId: SESSION,
      token: 'tok',
      stream: heldOpen(),
    });

    await flush();
    expect(liveHandles().has(SESSION)).toBe(true);

    release?.();
    await flush();
    expect(liveHandles().size).toBe(0);
  });

  it('keeps liveLabel "live" while a sibling stream is still connected (multi-session swarm)', async () => {
    const SESSION_B = 'b0b0b0b0b0b0';
    let releaseB: (() => void) | undefined;
    async function* finite(): AsyncGenerator<AgentEvent> {
      yield {
        type: 'budget.updated',
        session_id: SESSION,
        spent: 1,
        remaining: 9,
        limit: 10,
        unit: 'tokens',
        v: 1,
      } as unknown as AgentEvent;
    }
    async function* heldOpen(): AsyncGenerator<AgentEvent> {
      yield {
        type: 'budget.updated',
        session_id: SESSION_B,
        spent: 1,
        remaining: 9,
        limit: 10,
        unit: 'tokens',
        v: 1,
      } as unknown as AgentEvent;
      await new Promise<void>((r) => {
        releaseB = r;
      });
    }

    connectLiveStream({ sessionId: SESSION, stream: finite() });
    connectLiveStream({ sessionId: SESSION_B, stream: heldOpen() });

    await flush();
    expect(liveHandles().has(SESSION)).toBe(false);
    expect(liveHandles().has(SESSION_B)).toBe(true);
    expect(liveLabel()).toBe('live');

    releaseB?.();
    await flush();
    expect(liveHandles().size).toBe(0);
    expect(liveLabel()).toBe('snapshot');
  });
});
