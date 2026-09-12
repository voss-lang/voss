import { describe, it, expect, afterEach } from 'vitest';

import {
  registerNativeCard,
  registerTerminalCard,
  __resetBridgeMaps,
} from '../../model/bridge';
import type { RunData } from '../../types';
import type { AgentEvent } from '../../../../../../sdk/typescript/src/client/sse';
import {
  attentionQueue,
  ingestEvent,
  ingestSnapshotDecisions,
  normalizeCliPermission,
  resolveAttentionItem,
  __resetAttentionQueue,
} from '../attentionQueue';

afterEach(() => {
  __resetAttentionQueue();
  __resetBridgeMaps();
});

const permissionEvent: AgentEvent = {
  type: 'permission.updated',
  v: 1,
  id: 'p1',
  tool_name: 'fs_write',
  args: { path: '/repo/src/main.ts', content: '...' },
  dimension: 'tool',
};

function budgetThresholdEvent(sessionId: string): AgentEvent {
  return {
    type: 'budget.updated',
    v: 1,
    session_id: sessionId,
    unit: 'tokens',
    limit: 100,
    spent: 100, // spent ≥ limit → threshold crossed
    remaining: 0,
  };
}

function runDataWithSignOff(): RunData {
  return {
    run_id: 'R1',
    session_tree: { root_id: 'ROOT1', nodes: [] },
    review: {},
    audit: null,
    run_final: {
      kind: 'em.run_final',
      root_id: 'ROOT1',
      idea: 'ship it',
      total_cards: 1,
      done_count: 1,
      blocked_count: 0,
      killed_count: 0,
      rescope_count: 0,
      em_iterations: 1,
      ts: '2026-06-08T00:00:00Z',
      sign_off: { decision: 'approve', ts: '2026-06-08T00:00:00Z' },
    },
  };
}

describe('AttentionQueue — aggregator (permission + budget + sign-off)', () => {
  it('injecting permission + budget-threshold + sign-off yields exactly 3 items, each deep-linked via resolveCard', () => {
    const permCardId = registerTerminalCard('PANE-A');
    const budgetSession = '0139377ff590';
    registerNativeCard('CARD-NATIVE', budgetSession);
    registerNativeCard('ROOT1', 'ROOT1');

    ingestEvent(permissionEvent, { cardId: permCardId });
    ingestEvent(budgetThresholdEvent(budgetSession));
    ingestSnapshotDecisions(runDataWithSignOff());

    const items = attentionQueue();
    expect(items).toHaveLength(3);

    const byKind = Object.fromEntries(items.map((i) => [i.kind, i]));

    expect(byKind.permission.deepLink.paneId).toBe('PANE-A');

    expect(byKind.budget.deepLink.sessionNodeId).toBe(budgetSession);

    expect(byKind.signoff.deepLink.sessionNodeId).toBe('ROOT1');

    for (const item of items) {
      expect(
        item.deepLink.paneId !== undefined ||
          item.deepLink.sessionNodeId !== undefined,
      ).toBe(true);
    }
  });
});

describe('AttentionQueue — permission item shape', () => {
  it('exposes allow-once/allow-scoped/deny and carries tool + args + dimension + affectedPath', () => {
    const cardId = registerTerminalCard('PANE-B');
    ingestEvent(permissionEvent, { cardId });

    const item = attentionQueue()[0];
    expect(item.kind).toBe('permission');
    expect(item.actions).toEqual(['allow-once', 'allow-scoped', 'deny']);
    expect(item.tool).toBe('fs_write');
    expect(item.args).toEqual({ path: '/repo/src/main.ts', content: '...' });
    expect(item.dimension).toBe('tool');
    expect(item.affectedPath).toBe('/repo/src/main.ts');
  });

  it('Pitfall 6 / tier C: adopted external agent → NO per-tool gating actions', () => {
    const cardId = registerTerminalCard('PANE-ADOPTED');
    ingestEvent(permissionEvent, { cardId, adopted: true });

    const item = attentionQueue()[0];
    expect(item.actions).toEqual([]);
  });
});

describe('AttentionQueue — dedup', () => {
  it('re-ingesting the same event id does not add a second item', () => {
    const cardId = registerTerminalCard('PANE-C');
    ingestEvent(permissionEvent, { cardId });
    ingestEvent(permissionEvent, { cardId }); // same id 'p1'

    expect(attentionQueue()).toHaveLength(1);
  });
});

describe('AttentionQueue — VCKP-13b CLI permission-proxy (best-effort)', () => {
  it('a simulated Claude Code PreToolUse-shaped payload routes through ingestEvent → permission item with tool + affectedPath', () => {
    const cardId = registerTerminalCard('PANE-CLI');

    const rawPreToolUse = {
      hook_event_name: 'PreToolUse',
      tool_name: 'Edit',
      tool_input: { file_path: '/proj/app.py', old_string: 'a', new_string: 'b' },
      cwd: '/proj',
      session_id: 'cli-sess-7',
      permission_request_id: 'cli-perm-7',
    };

    const ev = normalizeCliPermission(rawPreToolUse);
    ingestEvent(ev, { cardId });

    const items = attentionQueue();
    expect(items).toHaveLength(1);
    const item = items[0];
    expect(item.kind).toBe('permission');
    expect(item.tool).toBe('Edit');
    expect(item.affectedPath).toBe('/proj/app.py');
    expect(item.args?.cwd).toBe('/proj');
    expect(item.deepLink.paneId).toBe('PANE-CLI');
  });
});

describe('AttentionQueue — resolveAttentionItem (V15-04)', () => {
  it('removes exactly the row with the prefixed permission id, leaving others intact', () => {
    ingestEvent(
      {
        type: 'permission.updated',
        v: 1,
        id: 'abc',
        tool_name: 'bash',
        args: {},
        dimension: 'tool',
      } as unknown as AgentEvent,
      { cardId: 'card-1' },
    );
    ingestEvent(
      {
        type: 'permission.updated',
        v: 1,
        id: 'def',
        tool_name: 'fs_edit',
        args: {},
        dimension: 'tool',
      } as unknown as AgentEvent,
      { cardId: 'card-1' },
    );
    expect(attentionQueue().length).toBe(2);

    resolveAttentionItem('permission:abc');

    const ids = attentionQueue().map((i) => i.id);
    expect(ids).toEqual(['permission:def']);
  });

  it('is a no-op for an unknown id', () => {
    resolveAttentionItem('permission:nope');
    expect(attentionQueue()).toEqual([]);
  });
});
