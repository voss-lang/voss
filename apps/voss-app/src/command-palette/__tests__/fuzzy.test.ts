import { describe, it, expect } from 'vitest';
import { scoreCommand, rankCommandItems } from '../fuzzy';

/**
 * A7-01 Task 1 — fuzzy scoring tests.
 *
 * Verifies case-insensitive substring matching, recency boost,
 * ranking order, and edge cases.
 */

describe('scoreCommand', () => {
  it('case-insensitive substring match scores ≥ 0', () => {
    expect(scoreCommand('split', 'Split Right', false)).toBeGreaterThanOrEqual(0);
    expect(scoreCommand('SPLIT', 'Split Right', false)).toBeGreaterThanOrEqual(0);
    expect(scoreCommand('right', 'Split Right', false)).toBeGreaterThanOrEqual(0);
  });

  it('no match scores -1', () => {
    expect(scoreCommand('zoom', 'Split Right', false)).toBe(-1);
  });

  it('prefix match scores higher than mid-string match', () => {
    const prefix = scoreCommand('split', 'Split Right', false);
    const mid = scoreCommand('right', 'Split Right', false);
    expect(prefix).toBeGreaterThan(mid);
  });

  it('recent commands get a deterministic score boost', () => {
    const normal = scoreCommand('split', 'Split Right', false);
    const recent = scoreCommand('split', 'Split Right', true);
    expect(recent).toBeGreaterThan(normal);
    expect(recent - normal).toBe(100); // RECENCY_BOOST = 100
  });

  it('empty query returns 0 for non-recent, boost for recent', () => {
    expect(scoreCommand('', 'Split Right', false)).toBe(0);
    expect(scoreCommand('', 'Split Right', true)).toBe(100);
  });
});

describe('rankCommandItems', () => {
  const items = [
    { id: 'pane.splitRight', label: 'Split Right' },
    { id: 'pane.splitBelow', label: 'Split Below' },
    { id: 'pane.close', label: 'Close Pane' },
    { id: 'layout.cycle', label: 'Cycle Layout' },
  ];

  it('ranks matching items by score descending', () => {
    const ranked = rankCommandItems('split', items, new Set());
    expect(ranked).toHaveLength(2);
    expect(ranked[0].id).toBe('pane.splitRight');
    expect(ranked[1].id).toBe('pane.splitBelow');
  });

  it('excludes non-matching items', () => {
    const ranked = rankCommandItems('zoom', items, new Set());
    expect(ranked).toHaveLength(0);
  });

  it('recency boost promotes recent commands', () => {
    const ranked = rankCommandItems('', items, new Set(['pane.close']));
    // pane.close is recent → boosted to top
    expect(ranked[0].id).toBe('pane.close');
  });

  it('empty query returns all items (recent first)', () => {
    const ranked = rankCommandItems('', items, new Set(['layout.cycle']));
    expect(ranked).toHaveLength(4);
    expect(ranked[0].id).toBe('layout.cycle');
  });

  it('case-insensitive match works across all items', () => {
    const ranked = rankCommandItems('CLOSE', items, new Set());
    expect(ranked).toHaveLength(1);
    expect(ranked[0].id).toBe('pane.close');
  });
});
