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

  it('resolveCard falls back to sessionNodeId = cardId when cardToSessionNode has no entry', () => {
    const maps = { cardToPane: { C1: 'P1' }, cardToSessionNode: {} };
    expect(resolveCard(maps, 'C1')).toEqual({
      paneId: 'P1',
      sessionNodeId: 'C1', // snapshot card id IS the node id
    });
  });

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
  it('registerTerminalCard mints a UUID cardId, maps it to the pane, returns the cardId', () => {
    const paneId = 'P-terminal-1';
    const cardId = registerTerminalCard(paneId);

    expect(cardId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    expect(paneIdForCard(cardId)).toBe(paneId);
    expect(cardToPane()[cardId]).toBe(paneId);
    expect(cardToSessionNode()[cardId]).toBeUndefined();
  });

  it('registerNativeCard stores create-response sessionID directly into cardToSessionNode (A1 finding)', () => {
    const cardId = 'C-native-1';
    const sessionID = '0139377ff590'; // 12-hex create-response id (= node id, A1)
    registerNativeCard(cardId, sessionID);

    expect(cardToSessionNode()[cardId]).toBe(sessionID);
    const maps = {
      cardToPane: cardToPane(),
      cardToSessionNode: cardToSessionNode(),
    };
    expect(resolveCard(maps, cardId).sessionNodeId).toBe(sessionID);
    expect(cardToPane()[cardId]).toBeUndefined();
    expect(resolveCard(maps, cardId).paneId).toBeUndefined();
  });

  it('the two mechanisms never cross: terminal cardId only in cardToPane, native cardId only in cardToSessionNode', () => {
    const terminalCardId = registerTerminalCard('P-cross');
    const nativeCardId = 'C-cross-native';
    registerNativeCard(nativeCardId, 'aabbccddeeff');

    expect(cardToPane()[terminalCardId]).toBe('P-cross');
    expect(cardToSessionNode()[terminalCardId]).toBeUndefined();

    expect(cardToSessionNode()[nativeCardId]).toBe('aabbccddeeff');
    expect(cardToPane()[nativeCardId]).toBeUndefined();

    expect(resolvePane(
      { cardToPane: cardToPane(), cardToSessionNode: cardToSessionNode() },
      'aabbccddeeff',
    )).toBeUndefined();
  });
});
