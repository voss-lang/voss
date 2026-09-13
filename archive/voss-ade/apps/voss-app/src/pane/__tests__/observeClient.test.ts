import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const h = vi.hoisted(() => ({
  invoke: vi.fn().mockResolvedValue(null),
  ChannelMock: class {
    onmessage: ((m: unknown) => void) | null = null;
  },
}));

vi.mock('@tauri-apps/api/core', () => ({
  invoke: h.invoke,
  Channel: h.ChannelMock,
}));

import {
  ObserveClient,
  createObserveClient,
  disposeObserveClient,
  observeContextForWorkspace,
  observeQueueStats,
  __resetObserveClients,
  OBSERVE_QUEUE_LIMIT,
  type ObserveEventEnvelope,
  type ObserveEvidence,
  type ObservePost,
} from '../observeClient';

const testClients: ObserveClient[] = [];
afterEach(() => {
  for (const client of testClients.splice(0)) client.dispose();
  __resetObserveClients();
});

const CTX = { repositoryId: 'repo-1', worktreeId: 'wt-1' };

function started(cmdId = 'cmd-1') {
  return {
    cmd_id: cmdId,
    argv_text: 'pnpm test',
    cwd: '/repo',
    at: '2026-09-06T18:00:00+00:00',
  };
}

function finished(cmdId = 'cmd-1', output = 'FAIL src/x.test.ts') {
  return {
    cmd_id: cmdId,
    exit: 1,
    duration_ms: 1200,
    output: new TextEncoder().encode(output),
    truncated: false,
  };
}

function makeClient(post: ObservePost) {
  const client = new ObserveClient({
    paneId: 'pane-1',
    actor: 'developer',
    context: CTX,
    sidecarId: () => 'sc-1',
    post,
  });
  testClients.push(client);
  return client;
}

type Posted = { sidecarId: string; event: ObserveEventEnvelope; evidence: ObserveEvidence[] };

function recordingPost(): { post: ObservePost; calls: Posted[] } {
  const calls: Posted[] = [];
  const post: ObservePost = async (sidecarId, event, evidence) => {
    calls.push({ sidecarId, event, evidence });
  };
  return { post, calls };
}

async function settle(rounds = 10): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await new Promise((r) => setTimeout(r, 0));
  }
}

beforeEach(() => {
  __resetObserveClients();
  h.invoke.mockClear();
});

describe('observeClient — envelope shape (observe/models.py)', () => {
  it('command.started carries the full BOS3 envelope with the adapter source_ref', async () => {
    const { post, calls } = recordingPost();
    makeClient(post).commandStarted(started());
    await settle();

    expect(calls.length).toBe(1);
    const { sidecarId, event, evidence } = calls[0];
    expect(sidecarId).toBe('sc-1');
    expect(evidence).toEqual([]);
    expect(event).toEqual({
      schema_version: 1,
      event_id: expect.stringMatching(/^[0-9a-f]{32}$/),
      category: 'command',
      event_type: 'command.started',
      event_time: '2026-09-06T18:00:00+00:00',
      ingest_time: null,
      trace_id: 'cmd-1',
      parent_event_id: null,
      caused_by: null,
      actor: 'developer',
      source_ref: { source: 'adapter', ref: 'pane-1' },
      external_identity_ref: null,
      repository_id: 'repo-1',
      worktree_id: 'wt-1',
      adapter_id: 'voss-pty',
      command_id: 'cmd-1',
      repository_state_id: 'unavailable',
      evidence_refs: [],
      payload: { argv: ['pnpm', 'test'], argv_text: 'pnpm test', cwd: '/repo' },
    });
  });

  it('command.completed carries exit/duration/truncated and output as evidence', async () => {
    const { post, calls } = recordingPost();
    const client = makeClient(post);
    client.commandStarted(started());
    client.commandFinished(finished());
    await settle();

    expect(calls.length).toBe(2);
    const { event, evidence } = calls[1];
    expect(event.event_type).toBe('command.completed');
    expect(event.payload).toEqual({
      argv: ['pnpm', 'test'],
      argv_text: 'pnpm test',
      cwd: '/repo',
      exit_code: 1,
      duration_ms: 1200,
      truncated: false,
    });
    expect(event.event_time).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/);
    expect(evidence.length).toBe(1);
    expect(evidence[0]).toEqual({
      kind: 'command_output',
      content: 'FAIL src/x.test.ts',
      truncated: false,
    });
    // evidence_refs stay empty on the wire — the route assigns ids itself.
    expect(event.evidence_refs).toEqual([]);
  });

  it('completed with empty output sends no evidence and empty evidence_refs', async () => {
    const { post, calls } = recordingPost();
    const client = makeClient(post);
    client.commandStarted(started());
    client.commandFinished({ ...finished(), output: new Uint8Array(0) });
    await settle();

    expect(calls[1].evidence).toEqual([]);
    expect(calls[1].event.evidence_refs).toEqual([]);
  });

  it('finished with an unknown cmd_id is skipped (no command identity)', async () => {
    const { post, calls } = recordingPost();
    makeClient(post).commandFinished(finished('cmd-ghost'));
    await settle();

    expect(calls.length).toBe(0);
  });
});

describe('observeClient — bounded drop-oldest queue (AC-S3-7 client half)', () => {
  it('fills to the limit and drops oldest, counting drops', async () => {
    const post: ObservePost = () => Promise.reject(new Error('sidecar down'));
    const client = makeClient(post);
    for (let i = 0; i < OBSERVE_QUEUE_LIMIT + 3; i++) {
      client.commandStarted(started(`cmd-${i}`));
    }
    await settle();

    expect(client.queueSize).toBe(OBSERVE_QUEUE_LIMIT);
    expect(client.droppedCount).toBe(3);
  });

  it('dropped events are the oldest: after recovery the survivors flush in order', async () => {
    let down = true;
    const { post, calls } = recordingPost();
    const guarded: ObservePost = async (sid, ev, e) => {
      if (down) throw new Error('sidecar down');
      return post(sid, ev, e);
    };
    const client = makeClient(guarded);
    for (let i = 0; i < OBSERVE_QUEUE_LIMIT + 1; i++) {
      client.commandStarted(started(`cmd-${i}`));
    }
    await settle();
    expect(client.droppedCount).toBe(1); // cmd-0 dropped as oldest

    down = false;
    client.commandStarted(started('cmd-last')); // evicts cmd-1, then flushes
    await settle();

    const ids = calls.map((c) => c.event.command_id);
    expect(client.droppedCount).toBe(2);
    expect(ids.length).toBe(OBSERVE_QUEUE_LIMIT);
    expect(ids[0]).toBe('cmd-2');
    expect(ids[ids.length - 1]).toBe('cmd-last');
    expect(client.queueSize).toBe(0);
  });

  it('a failing POST keeps the event queued and never rejects the caller', async () => {
    let attempts = 0;
    const post: ObservePost = () => {
      attempts += 1;
      return Promise.reject(new Error('down'));
    };
    const client = makeClient(post);
    expect(() => client.commandStarted(started())).not.toThrow();
    await settle();

    expect(client.queueSize).toBe(1);
    expect(attempts).toBe(1); // one attempt per flush, no hot retry loop
  });

  it('queues without a sidecar handle and flushes once one appears', async () => {
    const { post, calls } = recordingPost();
    let sidecarId: string | null = null;
    const client = new ObserveClient({
      paneId: 'pane-1',
      actor: 'developer',
      context: CTX,
      sidecarId: () => sidecarId,
      post,
    });
    client.commandStarted(started());
    await settle();
    expect(calls.length).toBe(0);
    expect(client.queueSize).toBe(1);

    sidecarId = 'sc-late';
    client.commandStarted(started('cmd-2'));
    await settle();
    expect(calls.map((c) => c.sidecarId)).toEqual(['sc-late', 'sc-late']);
    expect(calls.map((c) => c.event.command_id)).toEqual(['cmd-1', 'cmd-2']);
  });

  it('does not double-send while a POST is in flight', async () => {
    let release: (() => void) | null = null;
    const calls: string[] = [];
    const post: ObservePost = (_sid, ev) => {
      calls.push(ev.command_id);
      return new Promise<void>((r) => {
        release = r;
      });
    };
    const client = makeClient(post);
    client.commandStarted(started('cmd-1'));
    client.commandStarted(started('cmd-2'));
    await settle(2);

    expect(calls).toEqual(['cmd-1']); // second event waits for the first POST
    release!();
    await settle();
    expect(calls).toEqual(['cmd-1', 'cmd-2']);
  });
});

describe('observeClient — enrollment gating (AC-S3-8 client half)', () => {
  it('enrolling a rejected pane resumes capture on its next command', async () => {
    let enrolled = false;
    const calls: string[] = [];
    const client = makeClient(async (_id, event) => {
      calls.push(event.command_id);
      if (!enrolled) throw new Error('observe_rejected:not_enrolled');
    });
    client.commandStarted(started('before'));
    await settle();
    expect(client.queueSize).toBe(0);
    enrolled = true;
    client.commandStarted(started('after'));
    client.commandFinished(finished('after'));
    await settle();
    expect(calls).toEqual(['before', 'after', 'after']);
  });

  it('403 paused drops the event without caching — the next command retries', async () => {
    let attempts = 0;
    const { post, calls } = recordingPost();
    const guarded: ObservePost = async (sid, ev, e) => {
      attempts += 1;
      if (attempts === 1) throw new Error('observe_rejected:paused');
      return post(sid, ev, e);
    };
    const client = makeClient(guarded);
    client.commandStarted(started('cmd-1'));
    await settle();

    expect(client.queueSize).toBe(0);
    expect(client.droppedCount).toBe(0);

    client.commandStarted(started('cmd-2'));
    await settle();
    expect(calls.map((c) => c.event.command_id)).toEqual(['cmd-2']);
  });
});

describe('observeClient — registry + status-bar stats', () => {
  it('aggregates queued/dropped across panes and forgets disposed clients', async () => {
    const down: ObservePost = () => Promise.reject(new Error('down'));
    const cfg = (paneId: string) => ({
      paneId,
      actor: 'developer' as const,
      context: CTX,
      sidecarId: () => 'sc-1',
      post: down,
    });
    createObserveClient(cfg('p1')).commandStarted(started('a'));
    const two = createObserveClient(cfg('p2'));
    for (let i = 0; i < OBSERVE_QUEUE_LIMIT + 2; i++) {
      two.commandStarted(started(`b-${i}`));
    }
    await settle();

    expect(observeQueueStats()).toEqual({
      queued: OBSERVE_QUEUE_LIMIT + 1,
      dropped: 2,
    });

    disposeObserveClient('p2');
    expect(observeQueueStats()).toEqual({ queued: 1, dropped: 0 });
  });
});

describe('observeClient — workspace context + default transport', () => {
  it('uses canonical identity returned by the sidecar for any workspace path', async () => {
    h.invoke.mockResolvedValueOnce(CTX);
    expect(await observeContextForWorkspace('/repo/link/subdir', 'sc-1')).toEqual(CTX);
    expect(h.invoke).toHaveBeenCalledWith('call_voss_sidecar', {
      sidecarId: 'sc-1', operation: { kind: 'observe_context', cwd: '/repo/link/subdir' },
    });
  });

  it('default post routes through the sidecar proxy as an observe_event op', async () => {
    const client = new ObserveClient({
      paneId: 'pane-1',
      actor: 'developer',
      context: CTX,
      sidecarId: () => 'sc-1',
    });
    client.commandStarted(started());
    await settle();

    expect(h.invoke).toHaveBeenCalledWith('call_voss_sidecar', {
      sidecarId: 'sc-1',
      operation: {
        kind: 'observe_event',
        event: expect.objectContaining({
          event_type: 'command.started',
          adapter_id: 'voss-pty',
        }),
        evidence: [],
      },
    });
  });
});

it('retries the same event id after a lost response, without another command', async () => {
  vi.useFakeTimers();
  try {
    const ids: string[] = [];
    const client = makeClient(async (_id, event) => {
      ids.push(event.event_id);
      if (ids.length === 1) throw new Error('response lost');
    });
    client.commandStarted(started());
    await vi.advanceTimersByTimeAsync(1001);
    expect(ids).toHaveLength(2);
    expect(ids[1]).toBe(ids[0]);
    expect(client.queueSize).toBe(0);
  } finally { vi.useRealTimers(); }
});

it('an in-flight dropped item does not remove the next surviving event', async () => {
  let release!: () => void;
  const calls: string[] = [];
  const client = makeClient(async (_id, event) => {
    calls.push(event.command_id);
    if (calls.length === 1) await new Promise<void>((resolve) => { release = resolve; });
  });
  client.commandStarted(started('in-flight'));
  await settle();
  for (let i = 0; i < OBSERVE_QUEUE_LIMIT; i++) client.commandStarted(started(`next-${i}`));
  release();
  await settle();
  expect(calls[1]).toBe('next-0');
  expect(calls).toHaveLength(OBSERVE_QUEUE_LIMIT + 1);
});
