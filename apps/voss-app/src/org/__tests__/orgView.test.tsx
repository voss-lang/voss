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

  it('toggling Org mounts the shell but KEEPS the grid mounted (display:none)', () => {
    const root = mount(() => <Harness />);
    orgButton(root).click();

    // Grid node persists in the DOM, just hidden — proves no PTY unmount (Pitfall 6).
    const grid = root.querySelector('[data-testid="grid"]') as HTMLElement;
    expect(grid).toBeTruthy();
    expect(grid.style.display).toBe('none');

    // OrgViewShell mounted with its region role + 10-tab tablist.
    const shell = root.querySelector('[role="region"]');
    expect(shell).toBeTruthy();
    expect(shell?.getAttribute('aria-label')).toBe('Org/Run view');
    expect(root.querySelectorAll('[role="tab"]').length).toBe(10);

    // Org button now in active styling.
    expect(orgButton(root).style.color).toContain('--focus');
  });

  it('the 10 tab labels match the UI-SPEC exactly', () => {
    const root = mount(() => <Harness />);
    orgButton(root).click();
    const labels = [...root.querySelectorAll('[role="tab"]')].map((t) =>
      t.textContent?.trim(),
    );
    expect(labels).toEqual([
      'Roster',
      'Board',
      'Tree',
      'Audit',
      'Verdict',
      'Budget',
      'Scope',
      'Diff',
      'Blocked',
      'Replay',
    ]);
  });
});
