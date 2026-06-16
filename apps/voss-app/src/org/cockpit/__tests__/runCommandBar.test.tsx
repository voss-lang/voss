import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import {
  assembleRunSpec,
  validateAutoStart,
  type RunIntakeState,
  type RunSpec,
} from '../runIntake';

// RunCommandBar imports `@tauri-apps/api/core` for its default terminal launcher.
// The start-path tests inject mocks, so `invoke` is never called — stub it so the
// module import resolves under jsdom.
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import RunCommandBar from '../RunCommandBar';
import {
  cardToPane,
  cardToSessionNode,
  __resetBridgeMaps,
} from '../../model/bridge';

describe('runIntake — validate + assemble (pure)', () => {
  it('assembleRunSpec carries all intake fields into the spec', () => {
    const state: RunIntakeState = {
      goal: 'Refactor auth',
      mode: 'Auto',
      team: 'core',
      scope: 'tests/**',
      budget: 5,
      target: 'native',
    };
    const spec = assembleRunSpec(state);
    expect(spec).toEqual({
      goal: 'Refactor auth',
      mode: 'Auto',
      team: 'core',
      scope: 'tests/**',
      budget: 5,
      target: 'native',
    });
  });

  describe('validate', () => {
    it('blocks Auto with missing budget (reason mentions budget and Autopilot)', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: undefined,
        scope: 'x',
      });
      expect(result.ok).toBe(false);
      expect(result.reason).toMatch(/budget/i);
      expect(result.reason).toMatch(/Autopilot/i);
    });

    it('blocks Auto with missing scope (reason mentions scope and Autopilot)', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: 5,
        scope: undefined,
      });
      expect(result.ok).toBe(false);
      expect(result.reason).toMatch(/scope/i);
      expect(result.reason).toMatch(/Autopilot/i);
    });

    it('allows Auto when both budget and scope are present', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: 5,
        scope: 'tests/**',
      });
      expect(result).toEqual({ ok: true });
    });

    it('never blocks Plan/Edit regardless of budget/scope', () => {
      expect(validateAutoStart({ mode: 'Edit' })).toEqual({ ok: true });
      expect(
        validateAutoStart({ mode: 'Plan', budget: undefined, scope: undefined }),
      ).toEqual({ ok: true });
      expect(
        validateAutoStart({ mode: 'Edit', budget: undefined, scope: undefined }),
      ).toEqual({ ok: true });
    });
  });
});

// ---------------------------------------------------------------------------
// Start-path tests (sibling suite — `-t "validate"` still selects only the pure
// validator suite above). Exercise the rendered RunCommandBar's two start paths
// (Bridge B terminal / Bridge A native) and the Auto-block visible reason.
// ---------------------------------------------------------------------------

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
  // bridge.ts maps are module-level (global) signals — reset to prevent
  // register* state leaking across tests.
  __resetBridgeMaps();
});

const byLabel = (root: HTMLElement, label: string): HTMLElement =>
  root.querySelector(`[aria-label="${label}"]`) as HTMLElement;

const clickSegment = (root: HTMLElement, label: string, text: string): void => {
  const group = byLabel(root, label);
  const btn = [...group.querySelectorAll('button')].find(
    (b) => b.textContent?.trim() === text,
  ) as HTMLButtonElement;
  btn.click();
};

const setInput = (el: HTMLElement, value: string): void => {
  const input = el as HTMLInputElement;
  input.value = value;
  input.dispatchEvent(new Event('input', { bubbles: true }));
};

const setSelect = (el: HTMLElement, value: string): void => {
  const sel = el as HTMLSelectElement;
  sel.value = value;
  sel.dispatchEvent(new Event('change', { bubbles: true }));
};

const openDetails = (root: HTMLElement): void => {
  const btn = [...root.querySelectorAll('button')].find((b) =>
    b.textContent?.trim().startsWith('Details'),
  ) as HTMLButtonElement;
  btn.click();
};

describe('vocabulary contract (D-11)', () => {
  it('does not expose Plan/Edit/Auto as button labels', () => {
    const root = mount(() => (
      <RunCommandBar cwd="/tmp/proj" cliBinary="voss" spawnAgent={async () => {}} />
    ));
    const buttonLabels = [...root.querySelectorAll('button')].map((b) =>
      b.textContent?.trim(),
    );
    expect(buttonLabels).not.toContain('Plan');
    expect(buttonLabels).not.toContain('Edit');
    expect(buttonLabels).not.toContain('Auto');
  });

  it('shows humane safety labels with Read only as the default', () => {
    const root = mount(() => (
      <RunCommandBar cwd="/tmp/proj" cliBinary="voss" spawnAgent={async () => {}} />
    ));
    const barCopy = root.textContent ?? '';
    expect(barCopy).toMatch(/Read only/);
    const safety = byLabel(root, 'Safety mode') as HTMLSelectElement;
    expect(safety.value).toBe('Read only');
  });
  it('uses the intent-first goal placeholder', () => {
    const root = mount(() => (
      <RunCommandBar cwd="/tmp/proj" cliBinary="voss" spawnAgent={async () => {}} />
    ));
    const goal = byLabel(root, 'Task goal') as HTMLInputElement;
    expect(goal.getAttribute('placeholder')).toBe('What should Voss work on?');
  });
});

describe('start paths', () => {
  it('terminal start: spawnAgent gets minted cardId as sessionId + mode/team/scope/budget', async () => {
    const spawnAgent = vi.fn().mockResolvedValue(undefined);
    const root = mount(() => (
      <RunCommandBar
        cwd="/tmp/proj"
        cliBinary="claude"
        spawnAgent={spawnAgent}
        resolvePaneId={() => 'pane-42'}
      />
    ));

    setInput(byLabel(root, 'Task goal'), 'Refactor auth');
    setInput(byLabel(root, 'Scope'), 'tests/**');
    openDetails(root);
    setInput(byLabel(root, 'Budget'), '5');
    // team select: 'core'
    setSelect(byLabel(root, 'Team'), 'core');
    // Can edit safety + terminal target.
    setSelect(byLabel(root, 'Safety mode'), 'Can edit');
    clickSegment(root, 'Run target', 'Terminal agent');

    (byLabel(root, 'Start Task') as HTMLButtonElement).click();
    await Promise.resolve();
    await Promise.resolve();

    expect(spawnAgent).toHaveBeenCalledTimes(1);
    const payload = spawnAgent.mock.calls[0][0];
    expect(payload.paneId).toBe('pane-42');

    // The minted cardId is passed as sessionId AND bound to the pane (Bridge B).
    const cardId = payload.sessionId;
    expect(typeof cardId).toBe('string');
    expect(cardToPane()[cardId]).toBe('pane-42');

    // Intake context (mode/team/scope/budget) rides through in cliArgs.
    const args: string[] = payload.cliArgs;
    expect(args).toEqual(
      expect.arrayContaining([
        '--mode',
        'Edit',
        '--team',
        'core',
        '--scope',
        'tests/**',
        '--budget',
        '5',
      ]),
    );
    expect(payload.taskPrompt).toBe('Refactor auth');
    expect(payload.cliBinary).toBe('claude');
  });

  it('native start: mock createSession gets the assembled spec; id stored via registerNativeCard', async () => {
    let received: RunSpec | undefined;
    const client = {
      createSession: vi.fn((spec: RunSpec) => {
        received = spec;
        return Promise.resolve({ id: 'sess-abc123' });
      }),
    };
    const root = mount(() => (
      <RunCommandBar cwd="/tmp/proj" cliBinary="voss" client={client} />
    ));

    setInput(byLabel(root, 'Task goal'), 'Ship it');

    (byLabel(root, 'Start Task') as HTMLButtonElement).click();
    await Promise.resolve();
    await Promise.resolve();

    expect(client.createSession).toHaveBeenCalledTimes(1);
    expect(received).toMatchObject({
      goal: 'Ship it',
      target: 'native',
      mode: 'Plan',
    });

    // Bridge A: returned id stored (card id === session node id, A1 finding).
    expect(cardToSessionNode()['sess-abc123']).toBe('sess-abc123');
  });

  it('Autopilot with missing budget/scope shows a visible reason and calls NO start path', async () => {
    const spawnAgent = vi.fn();
    const client = { createSession: vi.fn() };
    const root = mount(() => (
      <RunCommandBar
        cwd="/tmp/proj"
        cliBinary="claude"
        spawnAgent={spawnAgent}
        client={client}
      />
    ));

    setInput(byLabel(root, 'Task goal'), 'Auto run');
    setSelect(byLabel(root, 'Safety mode'), 'Autopilot'); // no budget, no scope

    (byLabel(root, 'Start Task') as HTMLButtonElement).click();
    await Promise.resolve();
    await Promise.resolve();

    // Visible inline reason (disabled-with-reason discipline).
    const reason = root.querySelector('.run-bar__reason') as HTMLElement;
    expect(reason).toBeTruthy();
    expect(reason.textContent).toMatch(/budget|scope/i);

    // No start path invoked.
    expect(spawnAgent).not.toHaveBeenCalled();
    expect(client.createSession).not.toHaveBeenCalled();
  });
});
