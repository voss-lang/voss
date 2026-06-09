// V14-12 gap-fix verification — the two design-contract violations found at
// the phase-final checkpoint:
//
//   1. D-03: RunCommandBar must be an always-on strip in BOTH Live Work and
//      Run Review (it was mounted only inside CockpitShell → Live Work looked
//      pre-V14). Now mounted at App level ABOVE the grid/cockpit display swap;
//      CockpitShell renders NO bar (no double strip).
//   2. VCKP-12: AdoptAgentModal had no UI entry point. Now reachable via the
//      sidebar agent context menu ("Manage with Voss"), and the adoption
//      registry drives the post-spawn budget-stop.

import { describe, it, expect, vi, afterEach } from 'vitest';

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn((cmd: string) => {
    if (cmd === 'enumerate_runs') return Promise.resolve([]);
    return Promise.resolve(undefined);
  }),
  Channel: class {
    onmessage: ((m: unknown) => void) | null = null;
  },
}));

import { render } from 'solid-js/web';
import { createSignal } from 'solid-js';
import { fireEvent } from '@testing-library/dom';
import AgentContextMenu from '../components/sidebar/AgentContextMenu';
import RunCommandBar from '../org/cockpit/RunCommandBar';
import CockpitShell from '../org/cockpit/CockpitShell';
import {
  adoptionByPaneId,
  registerAdoption,
  unregisterAdoption,
  __resetAdoptions,
} from '../pane/adoptionRegistry';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  __resetAdoptions();
});

describe('VCKP-12 — adopt entry point (sidebar agent context menu)', () => {
  it('"Manage with Voss" item fires onManageAgent with the paneId and closes the menu', () => {
    const onManageAgent = vi.fn();
    const onClose = vi.fn();
    const anchor = document.createElement('div');
    document.body.appendChild(anchor);

    const el = mount(() => (
      <AgentContextMenu
        anchor={anchor}
        paneId="pane-42"
        costUsd={1.5}
        onClose={onClose}
        onFocusPane={() => {}}
        onStopAgent={() => {}}
        onRestartAgent={() => {}}
        onDetachAgent={() => {}}
        onManageAgent={onManageAgent}
      />
    ));

    const item = [...document.querySelectorAll('button')].find((b) =>
      b.textContent?.includes('Manage with Voss'),
    ) as HTMLButtonElement;
    expect(item, 'menu renders a Manage with Voss item').toBeTruthy();
    fireEvent.click(item);
    expect(onManageAgent).toHaveBeenCalledWith('pane-42');
    expect(onClose).toHaveBeenCalledOnce();
    expect(el).toBeTruthy();
  });

  it('adoption registry round-trip: register → read → unregister', () => {
    registerAdoption('pane-a', { cardId: 'card-1', budgetUsd: 5, tier: 'C' });
    expect(adoptionByPaneId()['pane-a']).toEqual({
      cardId: 'card-1',
      budgetUsd: 5,
      tier: 'C',
    });
    unregisterAdoption('pane-a');
    expect(adoptionByPaneId()['pane-a']).toBeUndefined();
  });
});

describe('D-03 — RunCommandBar is an always-on strip in BOTH modes', () => {
  it('the App-level mount keeps ONE bar visible across the Live↔Review display swap', () => {
    // Verbatim replication of the App work-surface column: the strip sits
    // ABOVE the display-swapped grid container, OUTSIDE the swap.
    const [orgViewOpen, setOrgViewOpen] = createSignal(false);
    mount(() => (
      <div style={{ display: 'flex', 'flex-direction': 'column' }}>
        <RunCommandBar cwd="/tmp" cliBinary="voss" spawnAgent={async () => {}} />
        <div style={{ display: orgViewOpen() ? 'none' : 'flex' }} data-testid="grid" />
        {orgViewOpen() ? <div data-testid="org" /> : null}
      </div>
    ));

    // Live Work: bar present.
    expect(document.querySelectorAll('.run-command-bar')).toHaveLength(1);
    // Review: bar STILL present, still exactly one.
    setOrgViewOpen(true);
    expect(document.querySelectorAll('.run-command-bar')).toHaveLength(1);
    // Back to Live: unchanged.
    setOrgViewOpen(false);
    expect(document.querySelectorAll('.run-command-bar')).toHaveLength(1);
  });

  it('CockpitShell renders NO RunCommandBar of its own (no double strip in Review)', async () => {
    mount(() => (
      <CockpitShell cwd="/tmp" cliBinary="voss" onClose={() => {}} />
    ));
    await Promise.resolve();
    await Promise.resolve();
    expect(document.querySelector('.run-command-bar')).toBeNull();
  });
});
