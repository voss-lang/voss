import { describe, it, expect, vi } from 'vitest';

// Tauri mock — reducer makes no invoke calls, but keep the import chain inert.
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import { computeBoardAtStep, CANONICAL_COLUMNS } from '../replayReducer';
import type { SessionTreeNode } from '../types';
import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';

// node-child carries 4 board.transition entries (the only ones across nodes):
//   step 0: Backlog→Planned   step 1: Planned→InProgress
//   step 2: InProgress→InReview   step 3: InReview→Done
const NODES = [nodeRoot, nodeChild] as unknown as SessionTreeNode[];
const CHILD_ID = nodeChild.id;
const FINAL_STEP = 3;

function clone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x)) as T;
}

describe('replayReducer — VADE-10 board/card reconstruction', () => {
  it('step 0 yields all 6 canonical columns; card sits in the column implied by the 0th transition', () => {
    const frame = computeBoardAtStep(NODES, 0);
    for (const col of CANONICAL_COLUMNS) {
      expect(frame.columns[col]).toBeInstanceOf(Array);
    }
    expect(Object.keys(frame.columns).sort()).toEqual([...CANONICAL_COLUMNS].sort());
    // 0th transition is Backlog→Planned, so the card is in Planned, not Backlog.
    expect(frame.columns.Backlog).toHaveLength(0);
    expect(frame.columns.Planned.map((c) => c.id)).toContain(CHILD_ID);
  });

  it('advances the card to InProgress at the step of its Backlog→…→InProgress transition', () => {
    const frame = computeBoardAtStep(NODES, 1);
    expect(frame.columns.InProgress.map((c) => c.id)).toContain(CHILD_ID);
    // and it has left earlier columns
    expect(frame.columns.Planned).toHaveLength(0);
  });

  it('at the final step a node with terminal_state "done" is in Done', () => {
    const frame = computeBoardAtStep(NODES, FINAL_STEP);
    const card = frame.columns.Done.find((c) => c.id === CHILD_ID);
    expect(card).toBeDefined();
    expect(card?.status).toBe('Done');
    expect(card?.risk).toBe('high'); // first em.ticket.risk_tier
  });

  it('terminal_state "killed" / "timeout" overrides the card into Blocked at the final step', () => {
    const killed = clone(nodeChild);
    killed.terminal_state.exit_reason = 'killed';
    const frame = computeBoardAtStep([killed] as unknown as SessionTreeNode[], FINAL_STEP);
    expect(frame.columns.Blocked.map((c) => c.id)).toContain(CHILD_ID);
    expect(frame.columns.Done).toHaveLength(0);
  });

  it('eventLabel describes the transition at the current step', () => {
    expect(computeBoardAtStep(NODES, 1).eventLabel).toBe(`${CHILD_ID} → InProgress`);
    expect(computeBoardAtStep(NODES, FINAL_STEP).eventLabel).toBe(`${CHILD_ID} → Done`);
  });

  it('never mutates input nodes and returns plain object literals', () => {
    const before = clone(NODES);
    const frame = computeBoardAtStep(NODES, FINAL_STEP);
    expect(NODES).toEqual(before); // inputs untouched
    // plain literals — round-trips through JSON without loss/throw
    expect(() => JSON.stringify(frame)).not.toThrow();
    expect(clone(frame)).toEqual(frame);
  });
});
