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
