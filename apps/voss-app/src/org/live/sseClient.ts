// VCKP-06 live SSE consumer (GATED on V13.1, best-effort). The FIRST SSE consumer
// in the org view. Consumes the V13.1 `subscribeToEvents` async-generator
// VERBATIM (never raw EventSource — that cannot set the `Authorization: Bearer`
// header, sse.ts:20) and routes each event into two sinks:
//   1. ingestEvent (attentionQueue) — surfaces permission/budget/gate/etc rows.
//   2. the module-level live overlay signal — latest budget/status/confidence/
//      gate per session, keyed by the event's session correlation key.
//
// Pitfall 4: the webview CANNOT start `voss serve` (the V13.1 launcher imports
// node:child_process — Node-only). This module ONLY consumes a stream; it never
// imports the launcher. When no live server/stream is available the cockpit
// degrades to snapshot + manual refresh — this never blocks the phase.
//
// liveLabel: a module-level 'live' | 'snapshot' signal. Set to 'live' while a
// stream is actively connected for the selected run; reset to 'snapshot' on
// end / abort / error / absence (the default).
//
// Mirrors budgetRegistry.ts / bridge.ts: module-level createSignal + IMMUTABLE
// spread updates (NO produce / NO structuredClone — Pitfall 5).

import { createSignal } from 'solid-js';

import { ingestEvent } from '../attention/attentionQueue';
import type { AgentEvent } from '../../../../../sdk/typescript/src/client/sse';
import { subscribeToEvents } from '../../../../../sdk/typescript/src/client/sse';

// --- Live overlay (session-keyed) --------------------------------------------

/**
 * The live-plane overlay the SSE stream drives, keyed by the session correlation
 * key. Mirrors the snapshot `Card` budget shape but is updated reactively from
 * the stream WITHOUT any manual snapshot refresh.
 */
export interface LiveOverlayEntry {
  budget?: { spent: number; remaining: number; limit: number; unit: string };
  status?: string;
  confidence?: number;
  gate?: { gate: string; decision: string };
}

const [liveOverlay, setLiveOverlay] = createSignal<Record<string, LiveOverlayEntry>>(
  {},
);

/** Immutable merge of one field-set into the overlay entry for `key`. */
function mergeOverlay(key: string, patch: LiveOverlayEntry): void {
  setLiveOverlay((prev) => ({
    ...prev,
    [key]: { ...prev[key], ...patch },
  }));
}

// --- live / snapshot label ----------------------------------------------------

const [liveLabel, setLiveLabel] = createSignal<'live' | 'snapshot'>('snapshot');

// Session-keyed live-handle set (V15-02): which sessionIds have an actively
// connected stream. Fixes the multi-session label problem — one stream ending
// must not read 'snapshot' while another session is still live. Immutable
// Set copies only (no produce/structuredClone — Pitfall 5).
const [liveHandles, setLiveHandles] = createSignal<Set<string>>(new Set());

// --- session correlation key --------------------------------------------------

/**
 * Read the session correlation key off an event. The plan-00 mock wraps events
 * as `AgentEvent & { sessionID }` (PROTOCOL §6 correlation key), while the raw
 * SDK union carries `session_id` (snake_case) on budget/gate/confidence/idle and
 * NOTHING on permission.updated. Prefer the correlation key that exists:
 * `sessionID`, falling back to `session_id`. Returns undefined when neither
 * exists (e.g. permission.updated — routed by ingest context, not by session).
 */
function sessionKeyOf(ev: AgentEvent): string | undefined {
  const withCorrelation = ev as AgentEvent & {
    sessionID?: string;
    session_id?: string;
  };
  return withCorrelation.sessionID ?? withCorrelation.session_id;
}

/**
 * Update the live overlay for one event, narrowed by `type` before reading any
 * type-specific field (the SDK union is NOT uniform — never assume a field).
 */
function applyOverlay(ev: AgentEvent): void {
  const key = sessionKeyOf(ev);
  if (key === undefined) return; // permission.updated has no session — overlay n/a

  switch (ev.type) {
    case 'budget.updated':
      mergeOverlay(key, {
        budget: {
          spent: ev.spent,
          remaining: ev.remaining,
          limit: ev.limit,
          unit: ev.unit,
        },
        status: 'running',
      });
      break;
    case 'confidence.updated':
      mergeOverlay(key, { confidence: ev.score });
      break;
    case 'gate.updated':
      mergeOverlay(key, { gate: { gate: ev.gate, decision: ev.decision } });
      break;
    case 'session.idle':
      mergeOverlay(key, { status: 'idle' });
      break;
    default:
      break;
  }
}

// --- connectLiveStream --------------------------------------------------------

export interface ConnectLiveStreamArgs {
  baseUrl: string;
  sessionId: string;
  token: string;
  /**
   * The card bound to this stream (Bridge A: the native session id IS the
   * cardId). Threaded into ingestEvent so permission.updated rows carry a
   * defined cardId (Pitfall 3 — the event itself has no session field).
   */
  cardId?: string;
  /**
   * Per-pane sink (V15-02): invoked for EVERY yielded event, after ingest +
   * overlay. Plan 03 points this at the ProtocolPane transcript.
   */
  onEvent?: (ev: AgentEvent) => void;
  /**
   * Test/mock injection: an async-iterable of AgentEvents to consume instead of
   * the real `subscribeToEvents` fetch. When omitted, the real SDK consumer is
   * used with the AbortController's signal.
   */
  stream?: AsyncIterable<AgentEvent>;
}

export interface LiveStreamHandle {
  /** Abort the stream cleanly: stops the for-await loop, resets liveLabel. */
  abort(): void;
}

/**
 * Connect a live SSE stream for the selected run. Consumes `subscribeToEvents`
 * (or an injected `stream`) inside a `for await`, routing each event into both
 * ingestEvent (attention queue) and the live overlay. Sets liveLabel to 'live'
 * while the stream is active and resets to 'snapshot' on end / abort / error.
 *
 * Returns a handle with `abort()` for clean teardown (no dangling generator).
 */
export function connectLiveStream(args: ConnectLiveStreamArgs): LiveStreamHandle {
  const ac = new AbortController();
  const stream =
    args.stream ??
    subscribeToEvents(args.baseUrl, args.sessionId, args.token, ac.signal);

  setLiveLabel('live');
  setLiveHandles((prev) => new Set([...prev, args.sessionId]));

  void (async () => {
    try {
      for await (const ev of stream) {
        if (ac.signal.aborted) break;
        ingestEvent(ev, args.cardId ? { cardId: args.cardId } : {});
        applyOverlay(ev);
        args.onEvent?.(ev);
      }
    } catch {
      // Aborted / ended / network error — degrade to snapshot, never throw.
    } finally {
      setLiveHandles((prev) => {
        const s = new Set(prev);
        s.delete(args.sessionId);
        return s;
      });
      setLiveLabel('snapshot');
    }
  })();

  return {
    abort(): void {
      ac.abort();
      setLiveLabel('snapshot');
    },
  };
}

export { liveLabel, liveOverlay, liveHandles };

/**
 * Test-only reset: clears the live overlay and resets the label to its default
 * 'snapshot'. Tests call this in afterEach so module-level live state does not
 * leak across tests (mirrors __resetBridgeMaps / __resetAttentionQueue).
 */
export function __resetLiveStream(): void {
  setLiveOverlay({});
  setLiveLabel('snapshot');
  setLiveHandles(new Set());
}
