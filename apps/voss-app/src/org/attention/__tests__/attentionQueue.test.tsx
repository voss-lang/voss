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
  __resetAttentionQueue,
} from '../attentionQueue';

// VCKP-04 global AttentionQueue. The module-level queue + bridge maps are GLOBAL
// signals — reset both after every test so ingest/register state never leaks.
afterEach(() => {
  __resetAttentionQueue();
  __resetBridgeMaps();
});

// --- Fixtures ---------------------------------------------------------------

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

/** A run snapshot whose RunFinal carries a sign_off (signoff item source). */
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

// --- Test 1: three planes → exactly 3 deep-linked items ---------------------

describe('AttentionQueue — aggregator (permission + budget + sign-off)', () => {
  it('injecting permission + budget-threshold + sign-off yields exactly 3 items, each deep-linked via resolveCard', () => {
    // Bind a terminal card to a pane (Bridge B) — permission item deep-links to it.
    const permCardId = registerTerminalCard('PANE-A');
    // Bind a native card to a session (Bridge A) — budget item deep-links to it.
    const budgetSession = '0139377ff590';
    registerNativeCard('CARD-NATIVE', budgetSession);
    // Bind the snapshot root so the sign-off item deep-links too.
    registerNativeCard('ROOT1', 'ROOT1');

    ingestEvent(permissionEvent, { cardId: permCardId });
    ingestEvent(budgetThresholdEvent(budgetSession));
    ingestSnapshotDecisions(runDataWithSignOff());

    const items = attentionQueue();
    expect(items).toHaveLength(3);

    const byKind = Object.fromEntries(items.map((i) => [i.kind, i]));

    // permission → bound pane
    expect(byKind.permission.deepLink.paneId).toBe('PANE-A');

    // budget → bound session node (Bridge A: session id IS the node id)
    expect(byKind.budget.deepLink.sessionNodeId).toBe(budgetSession);

    // sign-off → bound root session node
    expect(byKind.signoff.deepLink.sessionNodeId).toBe('ROOT1');

    // every item carries a non-empty deep-link (paneId OR sessionNodeId)
    for (const item of items) {
      expect(
        item.deepLink.paneId !== undefined ||
          item.deepLink.sessionNodeId !== undefined,
      ).toBe(true);
    }
  });
});

// --- Test 2: permission item shape ------------------------------------------

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

// --- Test 3: dedup ----------------------------------------------------------

describe('AttentionQueue — dedup', () => {
  it('re-ingesting the same event id does not add a second item', () => {
    const cardId = registerTerminalCard('PANE-C');
    ingestEvent(permissionEvent, { cardId });
    ingestEvent(permissionEvent, { cardId }); // same id 'p1'

    expect(attentionQueue()).toHaveLength(1);
  });
});

// --- Test 4: VCKP-13b CLI permission-proxy routing --------------------------

describe('AttentionQueue — VCKP-13b CLI permission-proxy (best-effort)', () => {
  it('a simulated Claude Code PreToolUse-shaped payload routes through ingestEvent → permission item with tool + affectedPath', () => {
    const cardId = registerTerminalCard('PANE-CLI');

    // Raw Claude Code PreToolUse hook payload (cwd at top level, args in tool_input).
    const rawPreToolUse = {
      hook_event_name: 'PreToolUse',
      tool_name: 'Edit',
      tool_input: { file_path: '/proj/app.py', old_string: 'a', new_string: 'b' },
      cwd: '/proj',
      session_id: 'cli-sess-7',
      permission_request_id: 'cli-perm-7',
    };

    // Normalize to the permission event shape, then route through the SAME path.
    const ev = normalizeCliPermission(rawPreToolUse);
    ingestEvent(ev, { cardId });

    const items = attentionQueue();
    expect(items).toHaveLength(1);
    const item = items[0];
    expect(item.kind).toBe('permission');
    expect(item.tool).toBe('Edit');
    // affectedPath surfaces from tool_input.file_path (proxy routing proven).
    expect(item.affectedPath).toBe('/proj/app.py');
    // cwd folded into args for downstream consumers.
    expect(item.args?.cwd).toBe('/proj');
    expect(item.deepLink.paneId).toBe('PANE-CLI');
  });
});
