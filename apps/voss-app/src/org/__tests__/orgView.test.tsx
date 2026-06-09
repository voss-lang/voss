import { describe, it, expect, vi, afterEach } from 'vitest';
import { createSignal, Show } from 'solid-js';
import { render } from 'solid-js/web';

// invoke resolves to [] so OrgViewShell.onMount → enumerateRuns() is inert.
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

// Harness reproducing App.tsx's display-toggle structure: the grid area is
// hidden via display:none (NOT unmounted) when the Org view is active.
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

    // Grid node persists in the DOM, just hidden — proves no PTY unmount (Pitfall 6).
    const grid = root.querySelector('[data-testid="grid"]') as HTMLElement;
    expect(grid).toBeTruthy();
    expect(grid.style.display).toBe('none');

    // V14 D-01: the tab shell is gone — OrgViewShell now mounts the 4-region
    // Run cockpit. Assert the cockpit region + that NO tablist survives.
    const shell = root.querySelector('[role="region"]');
    expect(shell).toBeTruthy();
    expect(shell?.getAttribute('aria-label')).toBe('Run cockpit');
    expect(root.querySelectorAll('[role="tab"]').length).toBe(0);

    // Org button now in active styling.
    expect(orgButton(root).style.color).toContain('--focus');
  });

  it('the cockpit renders its four regions, not a tab bar (V14 D-01)', () => {
    const root = mount(() => <Harness />);
    orgButton(root).click();
    // The cockpit composes four labelled regions from one shell; the old
    // ORG_TABS tab switcher is removed (D-01/D-02 — no legacy tab escape hatch).
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
