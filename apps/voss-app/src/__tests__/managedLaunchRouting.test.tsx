// VCKP-13 / V14-11 Task 4 — the managed toggle does REAL enforcement routing.
//
// Closes the BLOCKER class T-V14-07: a UI "managed" switch that routes to the
// unsandboxed spawn is a security control that does nothing. Asserted here at
// the transport seam with the REAL PtyTransport (mocked Tauri invoke), plus the
// PaneComponent.doSpawn branch and App.handleLaunchAgent tier-recording
// replicated verbatim (the liveReviewToggle.test.tsx harness convention —
// App.test.tsx mocks GridRoot and can't observe spawns).

import { describe, it, expect, vi, afterEach } from 'vitest';

const h = vi.hoisted(() => {
  const channels: Array<{ onmessage: ((m: unknown) => void) | null }> = [];
  return {
    channels,
    ChannelMock: class {
      onmessage: ((m: unknown) => void) | null = null;
      constructor() {
        channels.push(this);
      }
    },
    invoke: vi.fn(),
  };
});

vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => h.invoke(...args),
  Channel: h.ChannelMock,
}));

import { PtyTransport, type AgentConfig } from '../pane/pty-ipc';
import { resolveTier, hookCapableCli } from '../org/capabilityTier';
import { registerTerminalCard, __resetBridgeMaps } from '../org/model/bridge';

function freshTransport(extra?: Partial<ConstructorParameters<typeof PtyTransport>[0]>) {
  return new PtyTransport({ write: (_d, cb) => cb?.(), ...extra });
}

/** Default invoke behavior: spawn commands resolve their documented shapes. */
function armInvoke() {
  h.invoke.mockImplementation(async (cmd: unknown) => {
    if (cmd === 'spawn_managed_agent') {
      return { pty_id: 'pty-managed-1', tier: 'B', sandboxed: true };
    }
    if (cmd === 'spawn_agent') return 'pty-plain-1';
    return undefined;
  });
}

function callsTo(cmd: string) {
  return h.invoke.mock.calls.filter((c) => c[0] === cmd);
}

afterEach(() => {
  h.invoke.mockReset();
  h.channels.length = 0;
  __resetBridgeMaps();
});

/**
 * Verbatim replication of the PaneComponent.doSpawn branch (the seam that
 * issues the actual invoke): managed config → spawnManagedAgent with
 * scope+tier; otherwise the unchanged spawnAgent path.
 */
async function routeDoSpawn(
  transport: PtyTransport,
  agentConfig: AgentConfig,
  paneId: string,
): Promise<void> {
  if (agentConfig.managed) {
    await transport.spawnManagedAgent({
      rows: 24,
      cols: 80,
      paneId,
      ...agentConfig,
      scope: agentConfig.scope ?? '',
      tier: agentConfig.tier ?? 'B',
    });
  } else {
    await transport.spawnAgent({ rows: 24, cols: 80, paneId, ...agentConfig });
  }
}

describe('VCKP-13 — managed launch routes to spawn_managed_agent', () => {
  it('managed:true invokes spawn_managed_agent carrying scope (and NOT spawn_agent)', async () => {
    armInvoke();
    const cardId = registerTerminalCard('pane-m');
    const cfg: AgentConfig = {
      cliBinary: 'claude',
      cliArgs: ['--model', 'sonnet'],
      sessionId: cardId,
      managed: true,
      scope: '/repo/tests',
      tier: 'B',
    };

    await routeDoSpawn(freshTransport(), cfg, 'pane-m');

    const managedCalls = callsTo('spawn_managed_agent');
    expect(managedCalls).toHaveLength(1);
    const payload = managedCalls[0][1] as Record<string, unknown>;
    expect(payload.scope).toBe('/repo/tests');
    expect(payload.tier).toBe('B');
    expect(payload.cliBinary).toBe('claude');
    expect(payload.sessionId).toBe(cardId); // Bridge B passthrough preserved
    expect(callsTo('spawn_agent')).toHaveLength(0); // NOT the unsandboxed spawn
  });

  it('managed:false invokes spawn_agent with NO scope (unmanaged path unchanged)', async () => {
    armInvoke();
    const cfg: AgentConfig = {
      cliBinary: 'claude',
      cliArgs: [],
      sessionId: 'card-u',
      managed: false,
    };

    await routeDoSpawn(freshTransport(), cfg, 'pane-u');

    const plainCalls = callsTo('spawn_agent');
    expect(plainCalls).toHaveLength(1);
    const payload = plainCalls[0][1] as Record<string, unknown>;
    expect(payload).not.toHaveProperty('scope');
    expect(callsTo('spawn_managed_agent')).toHaveLength(0);
  });

  it('absent managed flag also routes to spawn_agent (back-compat default)', async () => {
    armInvoke();
    const cfg: AgentConfig = { cliBinary: 'gemini', cliArgs: [], sessionId: 'card-g' };
    await routeDoSpawn(freshTransport(), cfg, 'pane-g');
    expect(callsTo('spawn_agent')).toHaveLength(1);
    expect(callsTo('spawn_managed_agent')).toHaveLength(0);
  });
});

/**
 * Verbatim replication of App.handleLaunchAgent's tier recording: the tier
 * written into the pane config MUST come from resolveTier for the command
 * actually invoked — never the modal's static value.
 */
function recordedTierFor(config: { cliBinary: string; managed?: boolean }) {
  return resolveTier({
    cli: config.cliBinary,
    managed: config.managed === true,
    hookCapable: hookCapableCli(config.cliBinary),
    adopted: false,
  });
}

describe('VCKP-13 — recorded tier reflects the command actually invoked', () => {
  it('managed launch records the resolveTier result (B today — proxy not shipped, no fake A)', () => {
    expect(recordedTierFor({ cliBinary: 'claude', managed: true })).toBe('B');
    expect(recordedTierFor({ cliBinary: 'gemini', managed: true })).toBe('B');
  });

  it('unmanaged launch records tier C (observe-only) — never a managed tier on an unmanaged spawn', () => {
    expect(recordedTierFor({ cliBinary: 'claude', managed: false })).toBe('C');
    expect(recordedTierFor({ cliBinary: 'claude' })).toBe('C');
  });
});

describe('VCKP-13 — budget-kill terminates the pane at the limit', () => {
  it('a budget_update at/over the limit triggers pty_kill (and reports the kill)', async () => {
    armInvoke();
    const onBudgetKill = vi.fn();
    const transport = freshTransport({ budgetKillLimitUsd: 5, onBudgetKill });
    const cfg: AgentConfig = {
      cliBinary: 'claude',
      cliArgs: [],
      sessionId: 'card-b',
      managed: true,
      scope: '/repo',
      tier: 'B',
    };
    await routeDoSpawn(transport, cfg, 'pane-b');

    const ch = h.channels[h.channels.length - 1];
    // Below the limit: no kill.
    ch.onmessage!({
      type: 'budget_update',
      tokens_used: 10,
      token_limit: null,
      cost_usd: 4.99,
      iteration: 1,
      model: 'sonnet',
    });
    expect(callsTo('pty_kill')).toHaveLength(0);

    // At the limit: killed via the existing pty_kill path.
    ch.onmessage!({
      type: 'budget_update',
      tokens_used: 20,
      token_limit: null,
      cost_usd: 5.0,
      iteration: 2,
      model: 'sonnet',
    });
    expect(callsTo('pty_kill')).toHaveLength(1);
    expect(onBudgetKill).toHaveBeenCalledWith(5.0);
  });

  it('no budgetKillLimitUsd → budget_update never kills (existing behavior unchanged)', async () => {
    armInvoke();
    const transport = freshTransport();
    await routeDoSpawn(
      transport,
      { cliBinary: 'claude', cliArgs: [], sessionId: 'c' },
      'pane-x',
    );
    const ch = h.channels[h.channels.length - 1];
    ch.onmessage!({
      type: 'budget_update',
      tokens_used: 999,
      token_limit: null,
      cost_usd: 9999,
      iteration: 9,
      model: 'sonnet',
    });
    expect(callsTo('pty_kill')).toHaveLength(0);
  });
});
