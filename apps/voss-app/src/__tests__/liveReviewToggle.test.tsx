import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { createSignal, createEffect } from 'solid-js';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import {
  selectedCardId,
  setSelectedCardId,
  selectedRunId,
  setSelectedRunId,
  openInGridRequest,
  setOpenInGridRequest,
  requestOpenInGrid,
} from '../org/selection';
import {
  cardToPane,
  registerTerminalCard,
  __resetBridgeMaps,
} from '../org/model/bridge';
import CardDrawer from '../org/cockpit/CardDrawer';
import type { AgentConfig } from '../pane/pty-ipc';
import type { GridController } from '../grid/GridRoot';

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
  setSelectedCardId(null);
  setSelectedRunId(null);
  setOpenInGridRequest(null);
  __resetBridgeMaps();
  vi.restoreAllMocks();
});

describe('VCKP-08 — selection persists across the Live/Review toggle', () => {
  it('selectedRunId + selectedCardId survive a Live->Review->Live round-trip', () => {
    const [orgViewOpen, setOrgViewOpen] = createSignal(false); // false = Live (grid)

    setSelectedRunId('run-7');
    setSelectedCardId('card-99');

    setOrgViewOpen((p) => !p); // Live -> Review
    expect(orgViewOpen()).toBe(true);
    setOrgViewOpen((p) => !p); // Review -> Live
    expect(orgViewOpen()).toBe(false);

    expect(selectedRunId()).toBe('run-7');
    expect(selectedCardId()).toBe('card-99');
  });
});

describe('VCKP-08 — grid container stays mounted across the toggle', () => {
  it('the grid node is the same element reference; only inline display flips', () => {
    const [orgViewOpen, setOrgViewOpen] = createSignal(false);

    const root = mount(() => (
      <div
        data-testid="grid-host"
        style={{ display: orgViewOpen() ? 'none' : 'flex' }}
      >
        <div data-testid="grid-root">grid</div>
      </div>
    ));

    const before = root.querySelector('[data-testid="grid-host"]') as HTMLElement;
    const gridBefore = root.querySelector('[data-testid="grid-root"]');
    expect(before.style.display).toBe('flex'); // Live

    setOrgViewOpen(true); // > Review
    const duringReview = root.querySelector('[data-testid="grid-host"]') as HTMLElement;
    expect(duringReview).toBe(before); // same element reference not remounted
    expect(duringReview.style.display).toBe('none');
    expect(root.querySelector('[data-testid="grid-root"]')).toBe(gridBefore);

    setOrgViewOpen(false); // > Live
    const after = root.querySelector('[data-testid="grid-host"]') as HTMLElement;
    expect(after).toBe(before); // still the same node across the full round-trip
    expect(after.style.display).toBe('flex');
    expect(root.querySelector('[data-testid="grid-root"]')).toBe(gridBefore);
  });
});

describe('VCKP-08 — open-in-grid (D-07)', () => {
  it("CardDrawer 'Open in grid' button publishes the bound pane onto openInGridRequest", () => {
    const cardId = registerTerminalCard('pane-77');
    expect(cardToPane()[cardId]).toBe('pane-77');
    setSelectedCardId(cardId);

    const root = mount(() => <CardDrawer data={null} />);

    const btn = [...root.querySelectorAll('button')].find(
      (b) => b.textContent?.trim() === 'Open in grid',
    ) as HTMLButtonElement;
    expect(btn).toBeTruthy();
    expect(btn.disabled).toBe(false); // enabled because a live pane is bound

    btn.click();

    expect(openInGridRequest()).toBe('pane-77');
  });

  it('the App-side effect flips orgViewOpen->false, focuses the pane, and clears the request', () => {
    const focusPaneById = vi.fn();
    const ctrl = { focusPaneById } as unknown as GridController;

    const [orgViewOpen, setOrgViewOpen] = createSignal(true); // start in Review

    dispose = render(() => {
      createEffect(() => {
        const paneId = openInGridRequest();
        if (!paneId) return;
        setOrgViewOpen(false);
        ctrl.focusPaneById(paneId);
        setOpenInGridRequest(null);
      });
      return null as never;
    }, document.createElement('div'));

    expect(orgViewOpen()).toBe(true);
    expect(focusPaneById).not.toHaveBeenCalled();

    requestOpenInGrid('pane-31');

    expect(orgViewOpen()).toBe(false); // jumped back to the grid (Live)
    expect(focusPaneById).toHaveBeenCalledTimes(1);
    expect(focusPaneById).toHaveBeenCalledWith('pane-31');
    expect(openInGridRequest()).toBeNull(); // consumed so it can't re-fire
  });
});

function wireAgentLaunch(
  ctrl: Pick<GridController, 'splitFocused' | 'snapshot'>,
  config: { cliBinary: string; cliArgs: string[]; taskPrompt: string },
  setAgentConfigByPaneId: (paneId: string, cfg: AgentConfig) => void,
): { newId: string; cardId: string; cfg: AgentConfig } | null {
  const before = ctrl.snapshot().focusedId;
  ctrl.splitFocused('H');
  const newId = ctrl.snapshot().focusedId;
  if (newId === before) return null; // guard: split rejected abort

  const cardId = registerTerminalCard(newId);
  const cfg: AgentConfig = {
    cliBinary: config.cliBinary,
    cliArgs: config.cliArgs,
    sessionId: cardId,
  };
  setAgentConfigByPaneId(newId, cfg);
  return { newId, cardId, cfg };
}

describe('VCKP-08 — spawn wiring mints a cardId and carries it as sessionId (Bridge B)', () => {
  it('mints a cardId, binds it to the new pane, and writes it as AgentConfig.sessionId', () => {
    let focusedId = 'pane-old';
    const ctrl = {
      splitFocused: vi.fn(() => {
        focusedId = 'pane-new'; // split succeeds -> focus moves to the new pane
      }),
      snapshot: vi.fn(() => ({ root: {} as never, focusedId })),
    };
    const configByPane: Record<string, AgentConfig> = {};

    const out = wireAgentLaunch(
      ctrl,
      { cliBinary: 'claude', cliArgs: ['--mode', 'Edit'], taskPrompt: 'Refactor auth' },
      (paneId, cfg) => {
        configByPane[paneId] = cfg;
      },
    );

    expect(out).not.toBeNull();
    expect(ctrl.splitFocused).toHaveBeenCalledWith('H');
    expect(out!.newId).toBe('pane-new');

    expect(typeof out!.cardId).toBe('string');
    expect(cardToPane()[out!.cardId]).toBe('pane-new');

    expect(configByPane['pane-new']).toBeDefined();
    expect(configByPane['pane-new'].sessionId).toBe(out!.cardId);
    expect(configByPane['pane-new'].cliBinary).toBe('claude');
    expect(configByPane['pane-new'].cliArgs).toEqual(['--mode', 'Edit']);
  });

  it('GRD-05 guard: a rejected split mints NO cardId and writes NO config', () => {
    const ctrl = {
      splitFocused: vi.fn(), // no-op: focusedId unchanged (min-size rejection)
      snapshot: vi.fn(() => ({ root: {} as never, focusedId: 'pane-stuck' })),
    };
    const configByPane: Record<string, AgentConfig> = {};

    const out = wireAgentLaunch(
      ctrl,
      { cliBinary: 'claude', cliArgs: [], taskPrompt: 'x' },
      (paneId, cfg) => {
        configByPane[paneId] = cfg;
      },
    );

    expect(out).toBeNull(); // aborted
    expect(Object.keys(cardToPane())).toHaveLength(0); // no register* leakage
    expect(Object.keys(configByPane)).toHaveLength(0);
  });
});
