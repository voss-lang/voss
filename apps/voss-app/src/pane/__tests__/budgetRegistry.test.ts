import { describe, it, expect, afterEach } from 'vitest';
import {
  budgetByPaneId,
  registerPaneBudget,
  unregisterPaneBudget,
} from '../budgetRegistry';

// budgetRegistry is module-level state — clean up after each test
afterEach(() => {
  // Unregister all keys to reset state
  for (const key of Object.keys(budgetByPaneId())) {
    unregisterPaneBudget(key);
  }
});

const mockBudget = (cost = 0.5) => ({
  tokens_used: 1000,
  token_limit: 100000,
  cost_usd: cost,
  iteration: 1,
  model: 'claude-sonnet-4-20250514',
});

describe('budgetRegistry', () => {
  it('registerPaneBudget adds entry with lastSeenMs', () => {
    registerPaneBudget('pane-1', mockBudget());
    const entry = budgetByPaneId()['pane-1'];
    expect(entry).toBeDefined();
    expect(entry!.cost_usd).toBe(0.5);
    expect(entry!.lastSeenMs).toBeGreaterThan(0);
  });

  it('unregisterPaneBudget removes entry', () => {
    registerPaneBudget('pane-2', mockBudget());
    expect(budgetByPaneId()['pane-2']).toBeDefined();
    unregisterPaneBudget('pane-2');
    expect(budgetByPaneId()['pane-2']).toBeUndefined();
  });

  it('unregisterPaneBudget is no-op for absent key', () => {
    const before = budgetByPaneId();
    unregisterPaneBudget('nonexistent');
    expect(budgetByPaneId()).toBe(before); // same reference = no update
  });

  it('registerPaneBudget updates existing entry', () => {
    registerPaneBudget('pane-3', mockBudget(0.25));
    registerPaneBudget('pane-3', mockBudget(1.50));
    expect(budgetByPaneId()['pane-3']!.cost_usd).toBe(1.50);
  });
});
