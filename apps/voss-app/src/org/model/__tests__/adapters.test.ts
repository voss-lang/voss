import { describe, it } from 'vitest';

// VCKP-01: pure adapter `buildModel(snapshot, liveAgents, budgets, bridge)` that
// uses cardsFromRunData as the spine and overlays live-plane fields by the
// id-bridge. The module ../adapters is built by a downstream V14 plan; these
// `it.todo` entries name the exact behavior that plan flips skip→active.
//
// IMPORTANT: do NOT import ../adapters at collection time (it does not exist
// yet) — that would throw before the suite can run. Downstream plans replace
// these todos with active `it(...)` bodies that import buildModel lazily.

describe('adapters.buildModel — VCKP-01 (downstream: ../adapters)', () => {
  // The merged model is keyed off the snapshot spine.
  it.todo(
    'buildModel returns one Card per non-root snapshot node (cardsFromRunData spine)',
  );

  // Snapshot fields survive untouched on each card.
  it.todo(
    'each merged Card carries snapshot fields id/title/column/role/risk/budget from cardsFromRunData',
  );

  // Live overlay is bridged in by paneId.
  it.todo(
    "buildModel overlays paneId='P1' onto card 'C1' via bridge.cardToPane (live-registry fixture agent on P1)",
  );

  // sessionNodeId defaults to the card id (snapshot: card id IS the node id).
  it.todo(
    "buildModel sets card.sessionNodeId = card id when no native session override (C1 -> 'C1')",
  );

  // liveBudget overlays from the budgets map by resolved paneId.
  it.todo(
    'buildModel overlays liveBudget onto a card from budgets[resolvedPaneId]',
  );

  // Purity contract: no Solid imports, fixture-testable like boardDerive.ts.
  it.todo('buildModel is pure (no Solid/produce; safe to call from fixtures)');
});
