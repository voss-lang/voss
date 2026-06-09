import { describe, it, expect } from 'vitest';

import { reconcileSwarm } from '../swarmReconcile';
import manifest from './fixtures/swarm-manifest.json';

const VALID_COLUMNS = [
  'Backlog',
  'Planned',
  'InProgress',
  'InReview',
  'Done',
  'Blocked',
];

describe('reconcileSwarm', () => {
  it('maps agents to roster rows and cards with derived columns', () => {
    const result = reconcileSwarm(manifest);
    expect(result.rosterRows.length).toBe(2);
    expect(result.cards.length).toBe(2);
    expect(result.cards[0].column).toBe('InProgress'); // agent-1 running
    expect(result.cards[1].column).toBe('Done'); // agent-2 complete
  });

  it('is null-tolerant and never throws', () => {
    expect(reconcileSwarm(null)).toEqual({ rosterRows: [], cards: [] });
    expect(reconcileSwarm(undefined)).toEqual({ rosterRows: [], cards: [] });
  });

  it('surfaces the manifest goal as idea', () => {
    const result = reconcileSwarm(manifest);
    expect(result.idea).toBe('Refactor auth module and add tests');
  });

  it('only emits existing board columns (no new columns)', () => {
    const result = reconcileSwarm(manifest);
    for (const card of result.cards) {
      expect(VALID_COLUMNS).toContain(card.column);
    }
  });
});
