import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import AgentLaunchModal from '../AgentLaunchModal';

// The modal reads/writes the real model-prefs source (appearance settings).
// Mock it so getCommittedAppearanceSettings() is deterministic ({} → built-in
// preset defaults) and saveDefaultModel → saveAppearanceSettings is observable.
const saveAppearanceSettings = vi.fn().mockResolvedValue(undefined);
vi.mock('../../../appearance/settings', () => ({
  loadAppearanceSettings: vi.fn().mockResolvedValue({}),
  saveAppearanceSettings: (...args: unknown[]) => saveAppearanceSettings(...args),
  getCommittedAppearanceSettings: vi.fn().mockReturnValue({}),
}));

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
  saveAppearanceSettings.mockClear();
});

const defaultProps = () => ({
  onDismiss: vi.fn(),
  onLaunch: vi.fn(),
});

function tabs(el: HTMLElement) {
  return Array.from(el.querySelectorAll('.modal-tab'));
}
function tabByLabel(el: HTMLElement, label: string) {
  return tabs(el).find((t) => t.textContent?.trim() === label) as HTMLElement;
}
function launchBtn(el: HTMLElement) {
  return el.querySelector('.modal-btn-primary') as HTMLButtonElement;
}

describe('AgentLaunchModal — presets', () => {
  it('renders the six sparse presets ending with Terminal (Voss/Custom removed)', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    const labels = tabs(el).map((t) => t.textContent?.trim());
    expect(labels).toEqual([
      'Claude',
      'Codex',
      'Gemini',
      'OpenCode',
      'Aider',
      'Terminal',
    ]);
    // Removed legacy presets must not appear.
    expect(labels).not.toContain('Voss');
    expect(labels).not.toContain('Custom');
    expect(labels).not.toContain('Antigravity');
  });

  it('Claude (verified-real) shows its default model label "Claude Code · sonnet"', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    // The model hint reflects the REAL persisted default (mocked {} → built-in 'sonnet').
    const hint = Array.from(el.querySelectorAll('.modal-hint')).find((h) =>
      h.textContent?.includes('Claude Code'),
    );
    expect(hint?.textContent).toContain('Claude Code · sonnet');
  });

  it('Claude surfaces opus/sonnet/haiku as segmented chips', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    const chips = Array.from(el.querySelectorAll('.modal-segmented__btn')).map((b) =>
      b.textContent?.trim(),
    );
    expect(chips).toContain('opus');
    expect(chips).toContain('sonnet');
    expect(chips).toContain('haiku');
  });

  it('non-verified CLIs (Codex/Gemini/OpenCode/Aider) show "uses its own default model"', () => {
    for (const label of ['Codex', 'Gemini', 'OpenCode', 'Aider']) {
      const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
      fireEvent.click(tabByLabel(el, label));
      const hint = Array.from(el.querySelectorAll('.modal-hint')).find((h) =>
        h.textContent?.includes('uses its own default model'),
      );
      expect(hint, `${label} default-model hint`).toBeTruthy();
      // No segmented model chips for the unverified CLIs — only a free-text override.
      const chipLabels = Array.from(el.querySelectorAll('.modal-segmented__btn')).map(
        (b) => b.textContent?.trim(),
      );
      expect(chipLabels).not.toContain('opus');
      dispose?.();
      dispose = undefined;
      document.body.innerHTML = '';
    }
  });
});

describe('AgentLaunchModal — launch wiring', () => {
  it('launching Claude emits the resolved command (claude + --model sonnet) and placement', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(launchBtn(el));
    expect(p.onLaunch).toHaveBeenCalledOnce();
    const cfg = p.onLaunch.mock.calls[0][0];
    expect(cfg.cliBinary).toBe('claude');
    expect(cfg.cliArgs).toContain('--model');
    expect(cfg.cliArgs).toContain('sonnet');
    // --model precedes its value.
    expect(cfg.cliArgs.indexOf('--model')).toBeLessThan(cfg.cliArgs.indexOf('sonnet'));
    expect(cfg.placement).toBe('right');
  });

  it('emitted Claude config carries the agent-roster marker fields (kind/managed/tier)', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(launchBtn(el));
    const cfg = p.onLaunch.mock.calls[0][0];
    // Source-1 roster inclusion requires kind:'agent' + a known cliBinary so
    // App.handleLaunchAgent writes agentConfigByPaneId (vs. the early terminal return).
    expect(cfg.kind).toBe('agent');
    expect(cfg.cliBinary).toBe('claude');
    expect(cfg.managed).toBe(false);
    expect(cfg).toHaveProperty('tier');
    expect(cfg).toHaveProperty('placement');
  });

  it('choosing a different placement is reflected in the emitted config', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const belowBtn = Array.from(el.querySelectorAll('.modal-segmented__btn')).find(
      (b) => b.textContent?.trim() === 'Below',
    ) as HTMLButtonElement;
    fireEvent.click(belowBtn);
    fireEvent.click(launchBtn(el));
    expect(p.onLaunch.mock.calls[0][0].placement).toBe('below');
  });

  it('selecting a Claude alternate injects that model and persists it', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const opusChip = Array.from(el.querySelectorAll('.modal-segmented__btn')).find(
      (b) => b.textContent?.trim() === 'opus',
    ) as HTMLButtonElement;
    fireEvent.click(opusChip);
    fireEvent.click(launchBtn(el));
    const cfg = p.onLaunch.mock.calls[0][0];
    expect(cfg.cliArgs).toContain('opus');
    expect(cfg.cliArgs).not.toContain('sonnet');
    // Persisted through saveDefaultModel → saveAppearanceSettings.
    expect(saveAppearanceSettings).toHaveBeenCalled();
  });

  it('Gemini emits the gemini binary with NO --model (uses CLI default)', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(tabByLabel(el, 'Gemini'));
    fireEvent.click(launchBtn(el));
    const cfg = p.onLaunch.mock.calls[0][0];
    expect(cfg.cliBinary).toBe('gemini');
    expect(cfg.cliArgs).not.toContain('--model');
    expect(cfg.kind).toBe('agent');
  });
});

describe('AgentLaunchModal — Terminal preset', () => {
  it('launches a plain shell config: kind=terminal, no binary/args/model', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(tabByLabel(el, 'Terminal'));
    fireEvent.click(launchBtn(el));
    expect(p.onLaunch).toHaveBeenCalledOnce();
    const cfg = p.onLaunch.mock.calls[0][0];
    expect(cfg.kind).toBe('terminal');
    expect(cfg.cliBinary).toBe('');
    expect(cfg.cliArgs).toEqual([]);
    expect(cfg.cliArgs).not.toContain('--model');
    // Terminal is never a managed external agent.
    expect(cfg.managed).toBe(false);
  });

  it('Terminal panel hides the model chips (no agent/model config)', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    fireEvent.click(tabByLabel(el, 'Terminal'));
    const chips = Array.from(el.querySelectorAll('.modal-segmented__btn')).map((b) =>
      b.textContent?.trim(),
    );
    // Placement chips remain; model alias chips are gone.
    expect(chips).not.toContain('opus');
    expect(chips).not.toContain('sonnet');
    expect(chips).not.toContain('haiku');
  });
});

describe('AgentLaunchModal — managed/tier honesty', () => {
  it('agent presets emit tier B (no fake tier A) for a non-hook CLI', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(launchBtn(el));
    expect(p.onLaunch.mock.calls[0][0].tier).toBe('B');
  });

  it('Terminal preset emits tier C', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(tabByLabel(el, 'Terminal'));
    fireEvent.click(launchBtn(el));
    expect(p.onLaunch.mock.calls[0][0].tier).toBe('C');
  });

  it('managed toggle shows advisory honesty copy (no per-tool management promise)', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    const copy = Array.from(el.querySelectorAll('.modal-hint'))
      .map((h) => h.textContent ?? '')
      .join(' ');
    expect(copy).toMatch(/External agent/i);
    expect(copy).toMatch(/uses your local/i);
    expect(copy).toMatch(/advisory scope/i);
    // Honesty: no claim of full/active management today.
    expect(copy).not.toMatch(/fully managed/i);
  });

  it('toggling managed flips the emitted managed flag to true', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    const sw = el.querySelector('.modal-switch') as HTMLElement;
    expect(sw).toBeTruthy();
    fireEvent.click(sw);
    fireEvent.click(launchBtn(el));
    expect(p.onLaunch.mock.calls[0][0].managed).toBe(true);
  });
});

describe('AgentLaunchModal — no config-heavy surface', () => {
  it('has NO raw-command input (the old Custom name/command fields are gone)', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    const placeholders = Array.from(el.querySelectorAll('input, textarea')).map((i) =>
      (i.getAttribute('placeholder') ?? '').toLowerCase(),
    );
    // No field invites a raw shell command / agent name.
    for (const ph of placeholders) {
      expect(ph).not.toMatch(/command to run|raw command|agent name|name your/);
    }
  });

  it('has NO explainer <p> paragraph in the dialog', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    expect(el.querySelectorAll('p')).toHaveLength(0);
  });
});

describe('AgentLaunchModal — keyboard + dismissal', () => {
  it('Escape calls onDismiss and NOT onLaunch', () => {
    const p = defaultProps();
    mount(() => <AgentLaunchModal {...p} />);
    fireEvent.keyDown(document.querySelector('.modal-backdrop')!, { key: 'Escape' });
    expect(p.onDismiss).toHaveBeenCalledOnce();
    expect(p.onLaunch).not.toHaveBeenCalled();
  });

  it('clicking the backdrop dismisses without launching', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(el.querySelector('.modal-backdrop')!);
    expect(p.onDismiss).toHaveBeenCalledOnce();
    expect(p.onLaunch).not.toHaveBeenCalled();
  });

  it('the × dismiss button dismisses without launching', () => {
    const p = defaultProps();
    const el = mount(() => <AgentLaunchModal {...p} />);
    fireEvent.click(el.querySelector('.modal-header__dismiss')!);
    expect(p.onDismiss).toHaveBeenCalledOnce();
    expect(p.onLaunch).not.toHaveBeenCalled();
  });

  it('Cmd/Ctrl+Enter triggers launch', () => {
    const p = defaultProps();
    mount(() => <AgentLaunchModal {...p} />);
    const backdrop = document.querySelector('.modal-backdrop')!;
    fireEvent.keyDown(backdrop, { key: 'Enter', metaKey: true });
    expect(p.onLaunch).toHaveBeenCalledOnce();
    fireEvent.keyDown(backdrop, { key: 'Enter', ctrlKey: true });
    expect(p.onLaunch).toHaveBeenCalledTimes(2);
  });
});

describe('AgentLaunchModal — accessibility', () => {
  it('exposes correct dialog ARIA attributes', () => {
    const el = mount(() => <AgentLaunchModal {...defaultProps()} />);
    const dialog = el.querySelector('[role="dialog"]');
    expect(dialog).toBeTruthy();
    expect(dialog!.getAttribute('aria-modal')).toBe('true');
    expect(dialog!.getAttribute('aria-labelledby')).toBe('modal-title');
  });
});
