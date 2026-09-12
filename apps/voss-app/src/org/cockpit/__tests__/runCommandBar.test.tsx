import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import {
  assembleRunSpec,
  validateAutoStart,
  type RunIntakeState,
  type RunSpec,
} from '../runIntake';

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
    it('blocks Auto with missing budget (reason mentions budget)', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: undefined,
        scope: 'x',
      });
      expect(result.ok).toBe(false);
      expect(result.reason).toMatch(/budget/i);
    });

    it('blocks Auto with missing scope (reason mentions scope)', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: 5,
        scope: undefined,
      });
      expect(result.ok).toBe(false);
      expect(result.reason).toMatch(/scope/i);
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
      expect(validateAutoStart({ mode: 'Plan' })).toEqual({ ok: true });
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

    setInput(byLabel(root, 'Run goal'), 'Refactor auth');
    setInput(byLabel(root, 'Scope'), 'tests/**');
    setInput(byLabel(root, 'Budget'), '5');
    setSelect(byLabel(root, 'Team'), 'core');
    setSelect(byLabel(root, 'Safety mode'), 'Can edit');
    clickSegment(root, 'Run target', 'Terminal agent');

    (byLabel(root, 'Start run') as HTMLButtonElement).click();
    await Promise.resolve();
    await Promise.resolve();

    expect(spawnAgent).toHaveBeenCalledTimes(1);
    const payload = spawnAgent.mock.calls[0][0];
    expect(payload.paneId).toBe('pane-42');

    const cardId = payload.sessionId;
    expect(typeof cardId).toBe('string');
    expect(cardToPane()[cardId]).toBe('pane-42');

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

    setInput(byLabel(root, 'Run goal'), 'Ship it');
    clickSegment(root, 'Run target', 'Voss run');

    (byLabel(root, 'Start run') as HTMLButtonElement).click();
    await Promise.resolve();
    await Promise.resolve();

    expect(client.createSession).toHaveBeenCalledTimes(1);
    expect(received).toMatchObject({
      goal: 'Ship it',
      target: 'native',
      mode: 'Plan',
    });

    expect(cardToSessionNode()['sess-abc123']).toBe('sess-abc123');
  });

  it('Auto with missing budget/scope shows a visible reason and calls NO start path', async () => {
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

    setInput(byLabel(root, 'Run goal'), 'Auto run');
    clickSegment(root, 'Mode', 'Auto'); // no budget, no scope

    (byLabel(root, 'Start run') as HTMLButtonElement).click();
    await Promise.resolve();
    await Promise.resolve();

    const reason = root.querySelector('.run-bar__reason') as HTMLElement;
    expect(reason).toBeTruthy();
    expect(reason.textContent).toMatch(/budget|scope/i);

    expect(spawnAgent).not.toHaveBeenCalled();
    expect(client.createSession).not.toHaveBeenCalled();
  });
});
