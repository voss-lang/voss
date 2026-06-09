import { describe, it, expect } from 'vitest';

import binding from '../../__tests__/fixtures/bridge-binding.json';

// VCKP-02: `resolveCard(maps, cardId) -> { paneId?, sessionNodeId? }`. The
// module ../bridge is built by a downstream V14 plan (plan 02, gated by the A1
// keystone). The `it.todo` entries name the exact resolveCard contract that
// plan flips skip→active.
//
// IMPORTANT: do NOT import ../bridge at collection time (it does not exist yet).
// Downstream plans replace these todos with active bodies importing resolveCard.
//
// The active test below pins the canonical fixture (C1↔P1↔N1) so the contract
// the downstream module must satisfy is locked in now.

describe('bridge.resolveCard — VCKP-02 (downstream: ../bridge)', () => {
  it('binding fixture encodes the canonical keystone case C1 -> P1 / N1', () => {
    expect(binding.cardToPane.C1).toBe('P1');
    expect(binding.cardToSessionNode.C1).toBe('N1');
    expect(binding.expected).toEqual({
      cardId: 'C1',
      paneId: 'P1',
      sessionNodeId: 'N1',
    });
  });

  // The headline contract from the acceptance criteria.
  it.todo(
    "resolveCard({cardToPane:{C1:'P1'},cardToSessionNode:{C1:'N1'}}, 'C1') -> {paneId:'P1', sessionNodeId:'N1'}",
  );

  // Native snapshot fallback: card id IS the node id when unmapped.
  it.todo(
    "resolveCard falls back to sessionNodeId = cardId when cardToSessionNode has no entry (C1 -> 'C1')",
  );

  // Terminal-agent case: pane present, no session node.
  it.todo(
    'resolveCard returns paneId only (sessionNodeId === cardId) for a terminal agent with no recorded session node',
  );

  // Unknown card resolves to undefined pane.
  it.todo(
    'resolveCard returns paneId undefined for a cardId absent from cardToPane',
  );
});
