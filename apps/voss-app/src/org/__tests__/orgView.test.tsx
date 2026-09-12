import { describe, it, expect, vi, afterEach } from 'vitest';
import { createSignal, Show } from 'solid-js';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(() => Promise.resolve([])),
}));

import OrgViewShell from '../OrgViewShell';
import StatusBar from '../../components/StatusBar';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

function Harness() {
  const [open, setOpen] = createSignal(false);
  return (
    <div>
      <div data-testid="grid" style={{ display: open() ? 'none' : 'flex' }}>
        GRID
      </div>
      <Show when={open()}>
        <OrgViewShell cwd="/tmp" cliBinary="voss" onClose={() => setOpen(false)} />
      </Show>
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
        orgViewOpen={open()}
        onToggleOrgView={() => setOpen((p) => !p)}
        attentionCount={0}
        attentionBlocking={false}
        onToggleAttention={() => {}}
      />
    </div>
  );
}

function orgButton(root: HTMLElement): HTMLButtonElement {
  const btn = [...root.querySelectorAll('button')].find(
    (b) => b.textContent?.trim() === 'Org',
  );
  if (!btn) throw new Error('Org button not found');
  return btn as HTMLButtonElement;
}

describe('VADE-VIEW — Org/Run view toggle', () => {
  it('renders the grid and an inactive StatusBar Org button initially', () => {
    const root = mount(() => <Harness />);
    const grid = root.querySelector('[data-testid="grid"]') as HTMLElement;
    expect(grid).toBeTruthy();
    expect(grid.style.display).toBe('flex');
    expect(root.querySelector('[role="region"]')).toBeNull(); // shell not mounted
    expect(orgButton(root).style.color).toContain('--fg-3');
  });

  it('toggling Org mounts the cockpit but KEEPS the grid mounted (display:none)', () => {
    const root = mount(() => <Harness />);
    orgButton(root).click();

    const grid = root.querySelector('[data-testid="grid"]') as HTMLElement;
    expect(grid).toBeTruthy();
    expect(grid.style.display).toBe('none');

    const shell = root.querySelector('[role="region"]');
    expect(shell).toBeTruthy();
    expect(shell?.getAttribute('aria-label')).toBe('Run cockpit');
    expect(root.querySelectorAll('[role="tab"]').length).toBe(0);

    expect(orgButton(root).style.color).toContain('--focus');
  });

  it('the cockpit renders its four regions, not a tab bar (V14 D-01)', () => {
    const root = mount(() => <Harness />);
    orgButton(root).click();
    const regionLabels = [
      ...root.querySelectorAll('[aria-label]'),
    ]
      .map((el) => el.getAttribute('aria-label'))
      .filter((l): l is string =>
        ['Board spine', 'Card detail', 'Timeline and replay', 'Gate bar'].includes(
          l ?? '',
        ),
      );
    expect(new Set(regionLabels)).toEqual(
      new Set(['Board spine', 'Card detail', 'Timeline and replay', 'Gate bar']),
    );
    expect(root.querySelectorAll('[role="tab"]').length).toBe(0);
  });
});
