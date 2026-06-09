import { describe, it, expect } from 'vitest';

import { mockSseStream } from './mockSseStream';

// VCKP-06: the live SSE client wrapper `../../live/sseClient` wraps V13.1
// `subscribeToEvents`, feature-detects a live server, falls back to snapshot,
// and exposes a 'live' | 'snapshot' label. That module is built by a downstream
// V14 plan; the `it.todo` entries name the exact behavior that plan flips
// skip→active.
//
// IMPORTANT: do NOT import ../../live/sseClient at collection time (it does not
// exist yet). The active tests below drive the mock stream (which DOES exist) so
// VCKP-06's consumer path has a concrete, runnable fixture today.

describe('live SSE consumer — VCKP-06 (downstream: ../../live/sseClient)', () => {
  it('mockSseStream yields >=2 typed AgentEvents, each carrying sessionID', async () => {
    const events = [];
    for await (const ev of mockSseStream('0139377ff590')) {
      events.push(ev);
    }

    expect(events.length).toBeGreaterThanOrEqual(2);
    for (const ev of events) {
      // PROTOCOL §6 correlation key — present on every event.
      expect(ev.sessionID).toBe('0139377ff590');
      // SDK union field — present on the budget/gate members we yield.
      if (ev.type === 'budget.updated' || ev.type === 'gate.updated') {
        expect(ev.session_id).toBe('0139377ff590');
      }
    }

    const types = events.map((e) => e.type);
    expect(types).toContain('budget.updated');
    expect(types).toContain('gate.updated');
  });

  // The wrapper consumes subscribeToEvents and surfaces budget overlays.
  it.todo(
    'sseClient drives mockSseStream and applies budget.updated overlay to the bound card without a snapshot refresh',
  );

  // The live/snapshot label.
  it.todo(
    "sseClient reports label 'live' while a stream is active for the selected run",
  );

  // Fallback path.
  it.todo(
    "sseClient reports label 'snapshot' when no live server is feature-detected",
  );

  // Correlation: events route by sessionID to the matching card.
  it.todo(
    'sseClient routes events to the card whose sessionNodeId matches the event sessionID',
  );
});
