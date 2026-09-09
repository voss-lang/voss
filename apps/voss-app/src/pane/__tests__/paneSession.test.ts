import { describe, it, expect, vi, beforeEach } from 'vitest';

// Pane-session survival (grid-rearrange fix): the live session must outlive
// PaneComponent remounts (drag/swap/layout). These tests drive the registry +
// adoption lifecycle directly with mocked xterm/Tauri — the real xterm needs
// a measured DOM and canvas, neither of which jsdom provides.

const h = vi.hoisted(() => {
  const channels: Array<{ onmessage: ((m: unknown) => void) | null }> = [];
  class TerminalMock {
    options: Record<string, unknown> = {};
    rows = 24;
    cols = 80;
    buffer = {
      normal: { length: 0, getLine: () => null },
      active: { getLine: () => null },
    };
    disposed = false;
    openedInto: HTMLElement | null = null;
    private dataHandlers: ((d: string) => void)[] = [];
    constructor(public opts: unknown) {}
    open(el: HTMLElement) {
      this.openedInto = el;
    }
    loadAddon() {}
    write() {}
    refresh() {}
    focus() {}
    clear() {}
    dispose() {
      this.disposed = true;
    }
    onTitleChange() {}
    onBell() {}
    onData(fn: (d: string) => void) {
      this.dataHandlers.push(fn);
    }
    registerLinkProvider() {}
    attachCustomKeyEventHandler() {}
    emitData(d: string) {
      for (const fn of this.dataHandlers) fn(d);
    }
  }
  return {
    channels,
    invoke: vi.fn().mockResolvedValue('pty-1'),
    ChannelMock: class {
      onmessage: ((m: unknown) => void) | null = null;
      constructor() {
        channels.push(this);
      }
    },
    TerminalMock,
  };
});

vi.mock('@tauri-apps/api/core', () => ({
  invoke: h.invoke,
  Channel: h.ChannelMock,
}));
vi.mock('@xterm/xterm', () => ({ Terminal: h.TerminalMock }));
vi.mock('@xterm/addon-canvas', () => ({ CanvasAddon: class {} }));
vi.mock('@xterm/addon-fit', () => ({
  FitAddon: class {
    fit() {}
  },
}));
vi.mock('@xterm/addon-search', () => ({ SearchAddon: class {} }));
vi.mock('@xterm/addon-web-links', () => ({ WebLinksAddon: class {} }));

import {
  createPaneSession,
  adoptPaneSession,
  releasePaneSession,
  spawnPaneSession,
} from '../paneSession';
import {
  destroyPaneSession,
  getPaneSession,
  reapOrphanPaneSessions,
  registerPaneDestroyHook,
  NOOP_SINK,
  __resetPaneSessions,
  type PaneSink,
} from '../paneSessionRegistry';
import { procByPaneId } from '../procRegistry';
import { __resetObserveClients, observeQueueStats } from '../observeClient';
import { setLiveServer, __resetLiveServer } from '../../org/live/liveServer';
import { setShellIntegration } from '../../components/setup/shellIntegration';
import { DEFAULT_APPEARANCE_SETTINGS } from '../../appearance/types';

function makeSink(over: Partial<PaneSink> = {}): PaneSink {
  return { ...NOOP_SINK, ...over };
}

function slot(): HTMLDivElement {
  const el = document.createElement('div');
  document.body.appendChild(el);
  return el;
}

const keyHandler = () => true;
const SETTINGS = DEFAULT_APPEARANCE_SETTINGS;

beforeEach(() => {
  __resetPaneSessions();
  __resetObserveClients();
  __resetLiveServer();
  setShellIntegration(false);
  h.invoke.mockClear();
  h.invoke.mockResolvedValue('pty-1');
  h.channels.length = 0;
});

describe('paneSession — remount survives without kill/respawn', () => {
  it('release + re-adopt keeps the SAME terminal/transport: one spawn, zero kills', async () => {
    const s = createPaneSession({ paneId: 'p1', cwd: '/tmp', settings: SETTINGS });
    const a = slot();
    const t1 = adoptPaneSession(s, a, makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);

    const spawnCalls = h.invoke.mock.calls.filter(([cmd]) => cmd === 'spawn_pty');
    expect(spawnCalls.length).toBe(1);
    const termBefore = s.term;

    // Simulated remount (drag): old component releases, new one adopts.
    releasePaneSession(s, t1);
    expect(s.sink).toBe(NOOP_SINK);
    const b = slot();
    const dots: string[] = [];
    adoptPaneSession(s, b, makeSink({ setDot: (d) => dots.push(d) }), keyHandler, SETTINGS);

    expect(getPaneSession('p1')).toBe(s);
    expect(s.term).toBe(termBefore); // same Terminal identity
    expect(s.hostEl.parentElement).toBe(b); // host element moved, not rebuilt
    expect(
      h.invoke.mock.calls.filter(([cmd]) => cmd === 'pty_kill').length,
    ).toBe(0);
    expect(
      h.invoke.mock.calls.filter(([cmd]) => cmd === 'spawn_pty').length,
    ).toBe(1); // no respawn on adoption
  });

  it('a stale owner token release is a no-op after re-adoption (swap safety)', () => {
    const s = createPaneSession({ paneId: 'p1', settings: SETTINGS });
    const t1 = adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    const liveSink = makeSink();
    adoptPaneSession(s, slot(), liveSink, keyHandler, SETTINGS);

    releasePaneSession(s, t1); // stale — must not detach the new adopter
    expect(s.sink).toBe(liveSink);
    expect(s.hostEl.parentElement).not.toBeNull();
  });

  it('exit while detached hydrates the next adopter via canonical state', async () => {
    const s = createPaneSession({ paneId: 'p1', settings: SETTINGS });
    const t1 = adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);
    releasePaneSession(s, t1);

    // PTY exits while no component is mounted.
    h.channels[h.channels.length - 1].onmessage?.({ type: 'exit', code: 137 });
    expect(s.dot).toBe('exited');
    expect(s.lastExitCode).toBe(137);

    // The next adopter reads the canonical mirrors (PaneComponent hydrates
    // from s.dot/s.lastExitCode on mount) — assert they are current.
    const codes: (number | null)[] = [];
    adoptPaneSession(
      s,
      slot(),
      makeSink({ setExitCode: (c) => codes.push(c) }),
      keyHandler,
      SETTINGS,
    );
    expect(s.lastExitCode).toBe(137);
  });
});

describe('paneSession — explicit destruction paths', () => {
  it('destroyPaneSession kills, disposes, unregisters, and runs destroy hooks', async () => {
    const s = createPaneSession({ paneId: 'p1', settings: SETTINGS });
    adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);
    // Seed a registry entry the destroy must clear.
    h.channels[h.channels.length - 1].onmessage?.({
      type: 'fg_process',
      name: 'claude',
    });
    expect(procByPaneId()['p1']).toBe('claude');

    const hook = vi.fn();
    registerPaneDestroyHook('p1', hook);
    destroyPaneSession('p1');

    expect(
      h.invoke.mock.calls.filter(([cmd]) => cmd === 'pty_kill').length,
    ).toBe(1);
    expect((s.term as unknown as { disposed: boolean }).disposed).toBe(true);
    expect(getPaneSession('p1')).toBeUndefined();
    expect(procByPaneId()['p1']).toBeUndefined();
    expect(hook).toHaveBeenCalledTimes(1);
  });

  it('destroy hooks run even with no PTY session (native panes)', () => {
    const hook = vi.fn();
    registerPaneDestroyHook('native-pane', hook);
    destroyPaneSession('native-pane');
    expect(hook).toHaveBeenCalledTimes(1);
  });

  it('reapOrphanPaneSessions destroys exactly the dropped ids (diff-scoped)', () => {
    createPaneSession({ paneId: 'a', settings: SETTINGS });
    createPaneSession({ paneId: 'b', settings: SETTINGS });
    createPaneSession({ paneId: 'other-workspace', settings: SETTINGS });

    reapOrphanPaneSessions(['a', 'b'], ['b']);

    expect(getPaneSession('a')).toBeUndefined();
    expect(getPaneSession('b')).toBeDefined();
    expect(getPaneSession('other-workspace')).toBeDefined(); // never touched
  });
});

describe('paneSession — S3.3 observe forwarding', () => {
  function sidecarCalls() {
    return h.invoke.mock.calls
      .filter(([cmd]) => cmd === 'call_voss_sidecar')
      .map(([, args]) => args as { sidecarId: string; operation: { kind: string; event: { event_type: string; command_id: string; source_ref: { ref: string } } } });
  }

  it('forwards command_started/command_finished to the sidecar as observe events', async () => {
    setLiveServer({ sidecarId: 'sc-1' });
    const s = createPaneSession({
      paneId: 'p1',
      cwd: '/tmp',
      workspacePath: '/repo',
      settings: SETTINGS,
    });
    adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);

    const ch = h.channels[h.channels.length - 1];
    ch.onmessage?.({
      type: 'command_started',
      cmd_id: 'cmd-1',
      argv_text: 'pnpm test',
      cwd: '/repo',
      at: '2026-09-06T18:00:00+00:00',
    });
    ch.onmessage?.({
      type: 'command_finished',
      cmd_id: 'cmd-1',
      exit: 1,
      duration_ms: 42,
      output: Array.from(new TextEncoder().encode('boom')),
      truncated: false,
    });

    await vi.waitFor(() => expect(sidecarCalls().length).toBe(2));
    const [started, finished] = sidecarCalls();
    expect(started.sidecarId).toBe('sc-1');
    expect(started.operation.kind).toBe('observe_event');
    expect(started.operation.event.event_type).toBe('command.started');
    expect(started.operation.event.command_id).toBe('cmd-1');
    expect(started.operation.event.source_ref.ref).toBe('p1');
    expect(finished.operation.event.event_type).toBe('command.completed');
  });

  it('project-less panes (no workspacePath) never post observe events', async () => {
    setLiveServer({ sidecarId: 'sc-1' });
    const s = createPaneSession({ paneId: 'p1', settings: SETTINGS });
    adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);

    h.channels[h.channels.length - 1].onmessage?.({
      type: 'command_started',
      cmd_id: 'cmd-1',
      argv_text: 'ls',
      cwd: '/tmp',
      at: '2026-09-06T18:00:00+00:00',
    });
    await new Promise((r) => setTimeout(r, 20));

    expect(sidecarCalls().length).toBe(0);
    expect(observeQueueStats()).toEqual({ queued: 0, dropped: 0 });
  });

  it('queues while no sidecar is live instead of blocking the PTY path', async () => {
    const s = createPaneSession({
      paneId: 'p1',
      workspacePath: '/repo',
      settings: SETTINGS,
    });
    adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);

    h.channels[h.channels.length - 1].onmessage?.({
      type: 'command_started',
      cmd_id: 'cmd-1',
      argv_text: 'ls',
      cwd: '/repo',
      at: '2026-09-06T18:00:00+00:00',
    });
    await vi.waitFor(() => expect(observeQueueStats().queued).toBe(1));
    expect(sidecarCalls().length).toBe(0);
  });
});

describe('paneSession — S3.8 shell-integration opt-in', () => {
  function spawnArgs() {
    const call = h.invoke.mock.calls.find(([cmd]) => cmd === 'spawn_pty');
    return call?.[1] as { shellIntegration?: boolean } | undefined;
  }

  it('plain shell spawn passes shellIntegration: false by default', async () => {
    const s = createPaneSession({ paneId: 'p1', settings: SETTINGS });
    adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);
    expect(spawnArgs()?.shellIntegration).toBe(false);
  });

  it('opted-in toggle reaches the spawn_pty invoke as shellIntegration: true', async () => {
    setShellIntegration(true);
    const s = createPaneSession({ paneId: 'p1', settings: SETTINGS });
    adoptPaneSession(s, slot(), makeSink(), keyHandler, SETTINGS);
    await spawnPaneSession(s);
    expect(spawnArgs()?.shellIntegration).toBe(true);
  });
});
