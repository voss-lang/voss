import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import {
  adoptAgent,
  inferRole,
  inferRisk,
  ADOPT_UNAVAILABLE_REASON,
} from '../../../org/adopt';
import {
  cardToPane,
  paneIdForCard,
  __resetBridgeMaps,
} from '../../../org/model/bridge';
import {
  registerPaneBudget,
  unregisterPaneBudget,
} from '../../../pane/budgetRegistry';
import AdoptAgentModal from '../AdoptAgentModal';

// V14-10 (VCKP-12): forward-only adopt logic + "Let Voss manage this agent"
// modal. The adopt-logic suite covers the five behaviors from Task 1; the modal
// suite (Task 2) asserts D-10 plain-language copy and D-11 no-overclaim.

const PANE = 'pane-adopt-1';

const baseInput = () => ({
  paneId: PANE,
  runId: 'run-7' as string | null,
  scope: 'src/',
  budget: 10,
  cliBinary: 'claude',
  harnessAdoptAvailable: true,
});

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
  __resetBridgeMaps();
  unregisterPaneBudget(PANE);
});

describe('adoptAgent — bind + audit + review (adopt logic)', () => {
  it('adopt binds a card to the pane via registerTerminalCard and applies budget+scope', () => {
    const res = adoptAgent(baseInput());
    if (res.disabled) throw new Error('expected a binding, got disabled');
    expect(res.cardId).toBeTruthy();
    // The bound card resolves back to the running pane (Bridge B).
    expect(paneIdForCard(res.cardId)).toBe(PANE);
    // No harness session exists — the session node id falls back to the card id.
    expect(res.sessionNodeId).toBe(res.cardId);
    expect(res.runId).toBe('run-7');
    expect(res.scope).toBe('src/');
    expect(res.budget).toBe(10);
  });

  it('adopt marks the audit node partial_lineage, requires review, and is ALWAYS tier C', () => {
    const res = adoptAgent(baseInput());
    if (res.disabled) throw new Error('expected a binding, got disabled');
    expect(res.auditNode.lineage).toBe('partial_lineage');
    expect(res.reviewRequired).toBe(true);
    expect(res.tier).toBe('C');
  });

  it('adopt cost baseline starts at adoption time — pre-adoption spend is excluded', () => {
    registerPaneBudget(PANE, {
      tokens_used: 1200,
      token_limit: null,
      cost_usd: 1.25,
      iteration: 3,
      model: 'sonnet',
    });
    const res = adoptAgent(baseInput());
    if (res.disabled) throw new Error('expected a binding, got disabled');
    // Baseline = the pane's spend at adoption; forward cost = current - baseline.
    expect(res.auditNode.costBaselineUsd).toBe(1.25);
  });

  it('adopt baseline is 0 for a pane with no recorded spend', () => {
    const res = adoptAgent(baseInput());
    if (res.disabled) throw new Error('expected a binding, got disabled');
    expect(res.auditNode.costBaselineUsd).toBe(0);
  });

  it('adopt with no harness write-path returns disabled-with-reason and binds NOTHING', () => {
    const res = adoptAgent({ ...baseInput(), harnessAdoptAvailable: false });
    expect(res.disabled).toBe(true);
    if (!res.disabled) throw new Error('expected disabled');
    expect(res.reason).toBe(ADOPT_UNAVAILABLE_REASON);
    expect(res.reason.length).toBeGreaterThan(0);
    // No fake affordance: no card was minted, no pane binding exists.
    expect(Object.keys(cardToPane())).toHaveLength(0);
  });
});

describe('inferRole / inferRisk — editable adopt defaults (D-12)', () => {
  it('adopt infers executor for known agent CLIs and user otherwise', () => {
    expect(inferRole('claude')).toBe('executor');
    expect(inferRole('codex')).toBe('executor');
    expect(inferRole('/usr/local/bin/aider')).toBe('executor');
    expect(inferRole('bash')).toBe('user');
    expect(inferRole('')).toBe('user');
  });

  it('adopt infers risk from scope+budget: both → low, one → med, neither → high', () => {
    expect(inferRisk({ scope: 'src/', budget: 10 })).toBe('low');
    expect(inferRisk({ scope: '', budget: 10 })).toBe('med');
    expect(inferRisk({ scope: 'src/', budget: 0 })).toBe('med');
    expect(inferRisk({ scope: '', budget: 0 })).toBe('high');
  });

  it('adopt result honors user-edited role/risk overrides (editable, not locked)', () => {
    const res = adoptAgent({ ...baseInput(), role: 'reviewer', risk: 'high' });
    if (res.disabled) throw new Error('expected a binding, got disabled');
    expect(res.role).toBe('reviewer');
    expect(res.risk).toBe('high');
  });

  it('adopt result defaults role/risk from inference when not edited', () => {
    const res = adoptAgent(baseInput());
    if (res.disabled) throw new Error('expected a binding, got disabled');
    expect(res.role).toBe('executor'); // claude → executor
    expect(res.risk).toBe('low'); // scoped + bounded → low
  });
});

// --- Modal (Task 2) ----------------------------------------------------------

const modalProps = () => ({
  paneId: PANE,
  cliBinary: 'claude',
  runId: 'run-7' as string | null,
  harnessAdoptAvailable: true,
  onDismiss: vi.fn(),
  onAdopt: vi.fn(),
});

function ctaBtn(el: HTMLElement) {
  return el.querySelector('.modal-btn-primary') as HTMLButtonElement;
}

function inputByPlaceholder(el: HTMLElement, fragment: string) {
  return Array.from(el.querySelectorAll('input')).find((i) =>
    (i.getAttribute('placeholder') ?? '').includes(fragment),
  ) as HTMLInputElement;
}

function segBtn(el: HTMLElement, label: string) {
  return Array.from(el.querySelectorAll('.modal-segmented__btn')).find(
    (b) => b.textContent?.trim() === label,
  ) as HTMLButtonElement;
}

/** Every user-visible string: rendered text + placeholder/aria-label/title attrs. */
function allCopy(el: HTMLElement): string {
  const attrs = Array.from(
    el.querySelectorAll('[placeholder],[aria-label],[title]'),
  )
    .flatMap((n) => [
      n.getAttribute('placeholder'),
      n.getAttribute('aria-label'),
      n.getAttribute('title'),
    ])
    .filter(Boolean)
    .join(' ');
  return `${el.textContent ?? ''} ${attrs}`;
}

describe('AdoptAgentModal — adopt copy is plain language (D-10)', () => {
  it('renders the D-10 title, sections, and "Hand to Voss" CTA', () => {
    const el = mount(() => <AdoptAgentModal {...modalProps()} />);
    expect(el.querySelector('#modal-title')?.textContent).toBe(
      'Let Voss manage this agent',
    );
    const text = el.textContent ?? '';
    expect(text).toContain('Add it to');
    expect(text).toContain('As the task');
    expect(text).toContain('Limits');
    expect(text).toContain('From now on, Voss will');
    expect(ctaBtn(el).textContent?.trim()).toBe('Hand to Voss');
  });

  it('adopt copy contains NONE of the internal-mechanics jargon terms', () => {
    const el = mount(() => <AdoptAgentModal {...modalProps()} />);
    const copy = allCopy(el);
    const forbidden = [
      /cage/i,
      /voss[- ]?native/i,
      /permission\s*gate/i,
      /session[- ]?tree/i,
      /partial[\s_-]?lineage/i,
      /\bpanes?\b/i,
    ];
    for (const re of forbidden) {
      expect(copy, `forbidden term ${re} found in modal copy`).not.toMatch(re);
    }
  });

  it('adopt copy makes NO per-tool-gate promise (tier C: budget-stop, never tool-gate)', () => {
    const el = mount(() => <AdoptAgentModal {...modalProps()} />);
    const copy = allCopy(el);
    const gating = [/\btools?\b/i, /\bblock(s|ed|ing)?\b/i, /approve each/i, /per[- ]tool/i];
    for (const re of gating) {
      expect(copy, `per-tool gating language ${re} found in modal copy`).not.toMatch(re);
    }
    // The honest promises ARE present: budget stop/warn + review-before-done.
    expect(copy).toMatch(/stop it at the limit/i);
    expect(copy).toMatch(/review the result/i);
  });

  it('adopt copy states forward-only honestly (pre-adoption work not counted)', () => {
    const el = mount(() => <AdoptAgentModal {...modalProps()} />);
    expect(el.textContent).toContain('Tracking starts now');
  });
});

describe('AdoptAgentModal — adopt action wiring', () => {
  it('"Hand to Voss" calls adoptAgent: bind + budget + scope + partial_lineage + review + tier C', () => {
    const p = modalProps();
    const el = mount(() => <AdoptAgentModal {...p} />);
    fireEvent.input(inputByPlaceholder(el, 'folder it should stay inside'), {
      target: { value: 'src/' },
    });
    fireEvent.click(ctaBtn(el));
    expect(p.onAdopt).toHaveBeenCalledOnce();
    const res = p.onAdopt.mock.calls[0][0];
    expect(res.disabled).toBe(false);
    expect(paneIdForCard(res.cardId)).toBe(PANE); // card bound to the running pane
    expect(res.budget).toBe(10); // default budget field applied
    expect(res.scope).toBe('src/');
    expect(res.auditNode.lineage).toBe('partial_lineage');
    expect(res.reviewRequired).toBe(true);
    expect(res.tier).toBe('C');
    expect(res.runId).toBe('run-7'); // default destination = current run
  });

  it('adopt role is pre-inferred from the CLI, visible, and editable (D-12)', () => {
    const p = modalProps();
    const el = mount(() => <AdoptAgentModal {...p} />);
    const roleInput = inputByPlaceholder(el, 'e.g. executor');
    expect(roleInput.value).toBe('executor'); // claude → executor, shown by default
    fireEvent.input(roleInput, { target: { value: 'reviewer' } });
    fireEvent.click(ctaBtn(el));
    expect(p.onAdopt.mock.calls[0][0].role).toBe('reviewer');
  });

  it('adopt risk is pre-inferred from scope/budget, visible, and editable (D-12)', () => {
    const p = modalProps();
    const el = mount(() => <AdoptAgentModal {...p} />);
    // Pre-inferred: budget 10 + empty scope → med is the active chip.
    expect(segBtn(el, 'med').className).toContain('modal-segmented__btn--active');
    fireEvent.click(segBtn(el, 'high'));
    fireEvent.click(ctaBtn(el));
    expect(p.onAdopt.mock.calls[0][0].risk).toBe('high');
  });

  it('adopt budget edits are applied to the result', () => {
    const p = modalProps();
    const el = mount(() => <AdoptAgentModal {...p} />);
    fireEvent.input(inputByPlaceholder(el, 'spending limit'), {
      target: { value: '25' },
    });
    fireEvent.click(ctaBtn(el));
    expect(p.onAdopt.mock.calls[0][0].budget).toBe(25);
  });

  it('choosing "A new run" adopts with runId null', () => {
    const p = modalProps();
    const el = mount(() => <AdoptAgentModal {...p} />);
    fireEvent.click(segBtn(el, 'A new run'));
    fireEvent.click(ctaBtn(el));
    expect(p.onAdopt.mock.calls[0][0].runId).toBeNull();
  });
});

describe('AdoptAgentModal — adopt disabled-with-reason (no fake affordance)', () => {
  it('renders the CTA disabled with a visible reason when no harness adopt path exists', () => {
    const p = { ...modalProps(), harnessAdoptAvailable: false };
    const el = mount(() => <AdoptAgentModal {...p} />);
    expect(ctaBtn(el).disabled).toBe(true);
    expect(el.textContent).toContain(ADOPT_UNAVAILABLE_REASON);
    fireEvent.click(ctaBtn(el));
    expect(p.onAdopt).not.toHaveBeenCalled();
    // Nothing was bound — no card minted.
    expect(Object.keys(cardToPane())).toHaveLength(0);
  });
});

describe('AdoptAgentModal — adopt keyboard + dismissal', () => {
  it('Escape dismisses without adopting', () => {
    const p = modalProps();
    mount(() => <AdoptAgentModal {...p} />);
    fireEvent.keyDown(document.querySelector('.modal-backdrop')!, { key: 'Escape' });
    expect(p.onDismiss).toHaveBeenCalledOnce();
    expect(p.onAdopt).not.toHaveBeenCalled();
  });

  it('Cmd/Ctrl+Enter hands to Voss', () => {
    const p = modalProps();
    mount(() => <AdoptAgentModal {...p} />);
    fireEvent.keyDown(document.querySelector('.modal-backdrop')!, {
      key: 'Enter',
      metaKey: true,
    });
    expect(p.onAdopt).toHaveBeenCalledOnce();
  });

  it('clicking the backdrop dismisses without adopting', () => {
    const p = modalProps();
    const el = mount(() => <AdoptAgentModal {...p} />);
    fireEvent.click(el.querySelector('.modal-backdrop')!);
    expect(p.onDismiss).toHaveBeenCalledOnce();
    expect(p.onAdopt).not.toHaveBeenCalled();
  });
});
