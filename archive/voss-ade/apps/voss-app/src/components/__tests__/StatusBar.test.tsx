// S3.8 status-bar capture dot: enrollment state from the sidecar plus the
// aggregate dropped-event count from observeQueueStats() (AC-S3-7).

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';

const observeApi = vi.hoisted(() => ({
  getObserveSettings: vi.fn(),
  queueStats: vi.fn(() => ({ queued: 0, dropped: 0 })),
}));

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(() => Promise.resolve(null)),
  Channel: class {
    onmessage: ((m: unknown) => void) | null = null;
  },
}));

vi.mock('../../org/live/sidecarClient', () => ({
  callSidecar: vi.fn(),
  getObserveSettings: observeApi.getObserveSettings,
}));

vi.mock('../../pane/observeClient', () => ({
  observeContextForWorkspace: async () => ({
    repositoryId: 'repo-1',
    worktreeId: 'wt-1',
  }),
  observeQueueStats: () => observeApi.queueStats(),
}));

import StatusBar from '../StatusBar';
import {
  __resetLiveServer,
  setLiveServer,
} from '../../org/live/liveServer';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}

async function settle(rounds = 10): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await new Promise((r) => setTimeout(r, 0));
  }
}

const ENROLLED = {
  enabled: true,
  capture: true,
  analysis: false,
  provider: null,
  disclosure: false,
  budget_usd: null,
  paused: false,
};

function mountStatusBar(): HTMLElement {
  return mount(() => (
    <StatusBar
      workspaceName={undefined}
      paneCount={1}
      focusedPaneId={undefined}
      gitBranch={undefined}
      contextPanelOpen={false}
      onToggleContextPanel={() => {}}
      agentCount={0}
      totalCost={0}
      onToggleSidebar={() => {}}
      orgViewOpen={false}
      onToggleOrgView={() => {}}
      attentionCount={0}
      attentionBlocking={false}
      onToggleAttention={() => {}}
    />
  ));
}

function dot(root: HTMLElement): HTMLElement | null {
  return root.querySelector('[aria-label="Observation capture"]');
}

beforeEach(() => {
  __resetLiveServer();
  observeApi.getObserveSettings.mockReset().mockResolvedValue({});
  observeApi.queueStats.mockReset().mockReturnValue({ queued: 0, dropped: 0 });
});

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

describe('StatusBar — observe capture dot (S3.8)', () => {
  it('renders no dot without a live server', async () => {
    const el = mountStatusBar();
    await settle();

    expect(dot(el)).toBeNull();
    expect(observeApi.getObserveSettings).not.toHaveBeenCalled();
  });

  it('renders no dot for an unenrolled repository', async () => {
    setLiveServer({ sidecarId: 'sc-1', cwd: '/ws' });
    const el = mountStatusBar();
    await settle();

    expect(observeApi.getObserveSettings).toHaveBeenCalledWith('sc-1');
    expect(dot(el)).toBeNull();
  });

  it('shows an active capture dot for an enrolled repository', async () => {
    observeApi.getObserveSettings.mockResolvedValue({ 'repo-1': ENROLLED });
    setLiveServer({ sidecarId: 'sc-1', cwd: '/ws' });
    const el = mountStatusBar();
    await settle();

    expect(dot(el)?.textContent).toContain('capturing');
    expect(dot(el)?.getAttribute('title')).toBe('Command capture active');
  });

  it('shows a paused dot when capture is paused', async () => {
    observeApi.getObserveSettings.mockResolvedValue({
      'repo-1': { ...ENROLLED, paused: true },
    });
    setLiveServer({ sidecarId: 'sc-1', cwd: '/ws' });
    const el = mountStatusBar();
    await settle();

    expect(dot(el)?.textContent).toContain('paused');
    expect(dot(el)?.getAttribute('title')).toBe('Command capture paused');
  });

  it('surfaces the dropped-event count from the client queue (AC-S3-7)', async () => {
    observeApi.getObserveSettings.mockResolvedValue({ 'repo-1': ENROLLED });
    observeApi.queueStats.mockReturnValue({ queued: 4, dropped: 3 });
    setLiveServer({ sidecarId: 'sc-1', cwd: '/ws' });
    const el = mountStatusBar();
    await settle();

    expect(dot(el)?.textContent).toContain('dropped 3');
    expect(dot(el)?.getAttribute('title')).toContain(
      '3 events dropped (sidecar unreachable)',
    );
  });
});
