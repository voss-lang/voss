import { describe, it, expect, vi, beforeEach } from 'vitest';

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
    constructor(public opts: unknown) {}
    open() {}
    loadAddon() {}
    write() {}
    refresh() {}
    focus() {}
    clear() {}
    dispose() {}
    onTitleChange() {}
    onBell() {}
    onData() {}
    registerLinkProvider() {}
    attachCustomKeyEventHandler() {}
  }
  const observeClient = {
    commandStarted: vi.fn(),
    commandFinished: vi.fn(),
  };
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
    observeClient,
    createObserveClient: vi.fn(() => observeClient),
    disposeObserveClient: vi.fn(),
    observeContextForWorkspace: vi.fn(),
    shellIntegrationEnabled: vi.fn(() => true),
    liveServer: vi.fn(() => ({ sidecarId: 'sc-1' })),
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
vi.mock('../observeClient', () => ({
  createObserveClient: h.createObserveClient,
  disposeObserveClient: h.disposeObserveClient,
  observeContextForWorkspace: h.observeContextForWorkspace,
}));
vi.mock('../../components/setup/shellIntegration', () => ({
  shellIntegrationEnabled: h.shellIntegrationEnabled,
}));
vi.mock('../../org/live/liveServer', () => ({
  liveServer: h.liveServer,
  setLiveServer: vi.fn(),
}));

import { createPaneSession, adoptPaneSession, spawnPaneSession } from '../paneSession';
import { destroyPaneSession, NOOP_SINK, __resetPaneSessions } from '../paneSessionRegistry';
import { DEFAULT_APPEARANCE_SETTINGS } from '../../appearance/types';

const SETTINGS = DEFAULT_APPEARANCE_SETTINGS;

function slot(): HTMLDivElement {
  const el = document.createElement('div');
  document.body.appendChild(el);
  return el;
}

beforeEach(() => {
  __resetPaneSessions();
  vi.clearAllMocks();
  h.invoke.mockResolvedValue('pty-1');
  h.shellIntegrationEnabled.mockReturnValue(true);
  h.channels.length = 0;
});

describe('paneSession — observe wiring for project panes', () => {
  it('forwards PTY command marks to the observe client and spawns with shell integration', async () => {
    const s = createPaneSession({
      paneId: 'p1',
      cwd: '/repo',
      workspacePath: '/repo',
      settings: SETTINGS,
    });
    adoptPaneSession(s, slot(), NOOP_SINK, () => true, SETTINGS);
    await spawnPaneSession(s);

    expect(h.createObserveClient).toHaveBeenCalledWith(
      expect.objectContaining({ paneId: 'p1', actor: 'developer' }),
    );
    const [cfg] = h.createObserveClient.mock.calls[0] as unknown as [
      { context: () => Promise<unknown>; sidecarId: () => string | null },
    ];
    expect(cfg.sidecarId()).toBe('sc-1');
    void cfg.context();
    expect(h.observeContextForWorkspace).toHaveBeenCalledWith('/repo', 'sc-1');
    expect(h.invoke).toHaveBeenCalledWith(
      'spawn_pty',
      expect.objectContaining({ shellIntegration: true }),
    );

    const ch = h.channels[h.channels.length - 1];
    ch.onmessage!({
      type: 'command_started',
      cmd_id: 'c1',
      argv_text: 'make test',
      cwd: '/repo',
      at: '2026-09-12T00:00:00Z',
    });
    ch.onmessage!({
      type: 'command_finished',
      cmd_id: 'c1',
      exit: 0,
      duration_ms: 5,
      output: [111, 107],
      truncated: false,
    });

    expect(h.observeClient.commandStarted).toHaveBeenCalledWith(
      expect.objectContaining({ cmd_id: 'c1', argv_text: 'make test' }),
    );
    expect(h.observeClient.commandFinished).toHaveBeenCalledWith(
      expect.objectContaining({ cmd_id: 'c1', exit: 0 }),
    );

    destroyPaneSession('p1');
    expect(h.disposeObserveClient).toHaveBeenCalledWith('p1');
  });

  it('project-less panes get no observe client and spawn without shell integration when disabled', async () => {
    h.shellIntegrationEnabled.mockReturnValue(false);
    const s = createPaneSession({ paneId: 'p2', cwd: '/tmp', settings: SETTINGS });
    adoptPaneSession(s, slot(), NOOP_SINK, () => true, SETTINGS);
    await spawnPaneSession(s);

    expect(h.createObserveClient).not.toHaveBeenCalled();
    expect(h.invoke).toHaveBeenCalledWith(
      'spawn_pty',
      expect.objectContaining({ shellIntegration: false }),
    );

    destroyPaneSession('p2');
    expect(h.disposeObserveClient).not.toHaveBeenCalled();
  });
});
