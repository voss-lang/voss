import { describe, it, expect, afterEach } from 'vitest';

import binding from '../../__tests__/fixtures/bridge-binding.json';
import {
  resolveCard,
  resolvePane,
  registerTerminalCard,
  registerNativeCard,
  paneIdForCard,
  cardToPane,
  cardToSessionNode,
  __resetBridgeMaps,
} from '../bridge';

// VCKP-02 keystone: the id-bridge. `resolveCard(maps, cardId) -> { paneId?,
// sessionNodeId? }` correlates the live plane (pane) and the snapshot plane
// (session node). Two mechanisms (A1, V14-00):
//   Bridge A (native): create-response sessionID IS the snapshot node id, stored
//     DIRECTLY into cardToSessionNode.
//   Bridge B (terminal): client-minted cardId mapped to paneId via cardToPane.
// registry.session_id is NEVER joined to SessionTreeNode.id directly (Pitfall 1).

// The module-level signal maps are GLOBAL — reset them after every test so
// register* state does not leak across tests.
afterEach(() => {
  __resetBridgeMaps();
});

describe('bridge.resolveCard — VCKP-02 (pure resolver)', () => {
  it('binding fixture encodes the canonical keystone case C1 -> P1 / N1', () => {
    expect(binding.cardToPane.C1).toBe('P1');
    expect(binding.cardToSessionNode.C1).toBe('N1');
    expect(binding.expected).toEqual({
      cardId: 'C1',
      paneId: 'P1',
      sessionNodeId: 'N1',
    });
  });

  // 1. The headline contract from the acceptance criteria + binding fixture.
  it("resolveCard({cardToPane:{C1:'P1'},cardToSessionNode:{C1:'N1'}}, 'C1') -> {paneId:'P1', sessionNodeId:'N1'}", () => {
    const maps = {
      cardToPane: binding.cardToPane,
      cardToSessionNode: binding.cardToSessionNode,
    };
    expect(resolveCard(maps, 'C1')).toEqual({
      paneId: 'P1',
      sessionNodeId: 'N1',
    });
  });

  // 2. Native snapshot fallback: card id IS the node id when cardToSessionNode
  //    has no entry.
  it('resolveCard falls back to sessionNodeId = cardId when cardToSessionNode has no entry', () => {
    const maps = { cardToPane: { C1: 'P1' }, cardToSessionNode: {} };
    expect(resolveCard(maps, 'C1')).toEqual({
      paneId: 'P1',
      sessionNodeId: 'C1', // snapshot card id IS the node id
    });
  });

  // 3. Click-fallback: a card present in NEITHER map resolves without throwing.
  it('resolveCard returns {paneId:undefined, sessionNodeId:cardId} for a card in neither map (no throw)', () => {
    const maps = { cardToPane: {}, cardToSessionNode: {} };
    let result: { paneId?: string; sessionNodeId?: string } | undefined;
    expect(() => {
      result = resolveCard(maps, 'C-unknown');
    }).not.toThrow();
    expect(result).toEqual({ paneId: undefined, sessionNodeId: 'C-unknown' });
  });

  it('resolvePane reverse-resolves paneId -> cardId, undefined when unbound', () => {
    const maps = {
      cardToPane: { C1: 'P1', C2: 'P2' },
      cardToSessionNode: {},
    };
    expect(resolvePane(maps, 'P2')).toBe('C2');
    expect(resolvePane(maps, 'P-nope')).toBeUndefined();
  });
});

describe('bridge register* — two-mechanism separation (Bridge A / Bridge B)', () => {
  // 4. Bridge B: registerTerminalCard mints a UUID cardId mapped to the pane.
  it('registerTerminalCard mints a UUID cardId, maps it to the pane, returns the cardId', () => {
    const paneId = 'P-terminal-1';
    const cardId = registerTerminalCard(paneId);

    // crypto.randomUUID shape: 8-4-4-4-12 hex (v4 UUID).
    expect(cardId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    // Stored in the live cardToPane signal; readable via paneIdForCard.
    expect(paneIdForCard(cardId)).toBe(paneId);
    expect(cardToPane()[cardId]).toBe(paneId);
    // Bridge B carries no session node.
    expect(cardToSessionNode()[cardId]).toBeUndefined();
  });

  // 5. Bridge A: registerNativeCard stores the create-response sessionID DIRECTLY
  //    per the A1 finding. Asserts the two mechanisms are SEPARATE — the native
  //    sessionID lands in cardToSessionNode only, never in cardToPane, and is
  //    never joined to a pane (registry.session_id NOT joined to node id —
  //    Pitfall 1).
  it('registerNativeCard stores create-response sessionID directly into cardToSessionNode (A1 finding)', () => {
    const cardId = 'C-native-1';
    const sessionID = '0139377ff590'; // 12-hex create-response id (= node id, A1)
    registerNativeCard(cardId, sessionID);

    expect(cardToSessionNode()[cardId]).toBe(sessionID);
    // Direct store: resolveCard via the live maps returns the sessionID verbatim.
    const maps = {
      cardToPane: cardToPane(),
      cardToSessionNode: cardToSessionNode(),
    };
    expect(resolveCard(maps, cardId).sessionNodeId).toBe(sessionID);
    // No pane was bound — Bridge A is pane-independent.
    expect(cardToPane()[cardId]).toBeUndefined();
    expect(resolveCard(maps, cardId).paneId).toBeUndefined();
  });

  it('the two mechanisms never cross: terminal cardId only in cardToPane, native cardId only in cardToSessionNode', () => {
    const terminalCardId = registerTerminalCard('P-cross');
    const nativeCardId = 'C-cross-native';
    registerNativeCard(nativeCardId, 'aabbccddeeff');

    // Bridge B id lives in cardToPane, absent from cardToSessionNode.
    expect(cardToPane()[terminalCardId]).toBe('P-cross');
    expect(cardToSessionNode()[terminalCardId]).toBeUndefined();

    // Bridge A id lives in cardToSessionNode, absent from cardToPane.
    expect(cardToSessionNode()[nativeCardId]).toBe('aabbccddeeff');
    expect(cardToPane()[nativeCardId]).toBeUndefined();

    // The native sessionID ('aabbccddeeff') is never used as a pane key, i.e.
    // registry.session_id is NOT joined to SessionTreeNode.id (Pitfall 1).
    expect(resolvePane(
      { cardToPane: cardToPane(), cardToSessionNode: cardToSessionNode() },
      'aabbccddeeff',
    )).toBeUndefined();
  });
});
