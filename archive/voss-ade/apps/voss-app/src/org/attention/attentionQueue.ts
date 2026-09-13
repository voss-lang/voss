import { createSignal } from 'solid-js';

import { resolveCard, cardToPane, cardToSessionNode } from '../model/bridge';
import { deriveColumn } from '../boardDerive';
import type { RunData } from '../types';
import type { AgentEvent } from '../../../../../sdk/typescript/src/client/sse';


export type AttentionKind =
  | 'permission'
  | 'budget'
  | 'confidence'
  | 'idle'
  | 'gate'
  | 'signoff'
  | 'blocked'
  | 'unsupported';

export type PermissionAction = 'allow-once' | 'allow-scoped' | 'deny';

export interface DeepLink {
  paneId?: string;
  sessionNodeId?: string;
}

export interface AttentionItem {
/** Stable dedup key. Re-ingesting the same id never adds a second item */
  id: string;
  kind: AttentionKind;
  cardId?: string;
  sessionNodeId?: string;
/** Human summary for the panel row */
  summary: string;
/** resolveCard result — focuses the bound card/session/evidence on click */
  deepLink: DeepLink;

  // permission-only fields
  tool?: string;
  args?: Record<string, unknown>;
  dimension?: string;
  affectedPath?: string;
/**
 * allow-once / allow-scoped / deny. EMPTY for adopted external agents
 * ( / tier C — no tool gating promise)
 */
  actions?: PermissionAction[];

  // budget / confidence numeric context
  value?: number;
  limit?: number;
}


const [attentionQueue, setAttentionQueue] = createSignal<AttentionItem[]>([]);

/**
 * Dedup'd immutable push. If an item with the same id already exists the queue
 * is returned UNCHANGED (no second item, no re-render). Otherwise a fresh array
 */
function pushItem(item: AttentionItem): void {
  setAttentionQueue((prev) => {
    if (prev.some((existing) => existing.id === item.id)) return prev;
    return [...prev, item];
  });
}

/**
 * 04 (-05): the inverse of pushItem — remove one row by id
 * (immutable filter). Permission rows use the prefixed id
 */
export function resolveAttentionItem(id: string): void {
  setAttentionQueue((prev) => prev.filter((item) => item.id !== id));
}

/** Current live bridge maps, read at ingest time (Bridge A/B correlation) */
function liveMaps() {
  return { cardToPane: cardToPane(), cardToSessionNode: cardToSessionNode() };
}

/**
 * Reverse-resolve a session id (`session_id` on the SSE event === the snapshot
 * node id for native runs, A1) back to its cardId via cardToSessionNode. Falls
 */
function cardIdForSession(sessionId: string): string {
  const map = cardToSessionNode();
  for (const cardId in map) {
    if (map[cardId] === sessionId) return cardId;
  }
  return sessionId; // snapshot/native: card id IS the session node id
}

/** Permission actions, honest about tier C: empty for adopted external agents */
export function permissionActionsFor(adopted: boolean): PermissionAction[] {
  return adopted ? [] : ['allow-once', 'allow-scoped', 'deny'];
}

/** Best-effort affected-path extraction from a permission tool's args */
function affectedPathFromArgs(
  args: Record<string, unknown> | undefined,
): string | undefined {
  if (!args) return undefined;
  for (const key of ['path', 'file_path', 'filePath', 'cwd', 'target']) {
    const v = args[key];
    if (typeof v === 'string' && v.length > 0) return v;
  }
  return undefined;
}


export interface IngestContext {
/**
 * cardId for events that carry no `session_id` (permission.updated has none
 * see 6). When omitted the permission item's id IS the cardId/dedup
 */
  cardId?: string;
/** Adopted external agent → suppress tool gating actions */
  adopted?: boolean;
}

/**
 * Map one SSE AgentEvent to an AttentionItem and enqueue it (dedup'd). Returns
 * the item, or null for event types the queue does not surface
 */
export function ingestEvent(
  ev: AgentEvent,
  ctx: IngestContext = {},
): AttentionItem | null {
  switch (ev.type) {
    case 'permission.updated': {
      // 6/§7: permission.updated = {id, tool_name, args, dimension}.
      // No session_id → the cardId comes from context (live grid binding).
      const args = ev.args as Record<string, unknown> | undefined;
      const cardId = ctx.cardId;
      const deepLink = cardId
        ? resolveCard(liveMaps(), cardId)
        : { paneId: undefined, sessionNodeId: undefined };
      const item: AttentionItem = {
        id: `permission:${ev.id}`,
        kind: 'permission',
        cardId,
        sessionNodeId: deepLink.sessionNodeId,
        summary: `Permission: ${ev.tool_name}`,
        deepLink,
        tool: ev.tool_name,
        args,
        dimension: ev.dimension,
        affectedPath: affectedPathFromArgs(args),
        actions: permissionActionsFor(ctx.adopted === true),
      };
      pushItem(item);
      return item;
    }

    case 'budget.updated': {
      // Threshold reached (spent ≥ limit). Honor only crossings.
      if (ev.limit <= 0 || ev.spent < ev.limit) return null;
      const cardId = cardIdForSession(ev.session_id);
      const deepLink = resolveCard(liveMaps(), cardId);
      const item: AttentionItem = {
        id: `budget:${ev.session_id}`,
        kind: 'budget',
        cardId,
        sessionNodeId: deepLink.sessionNodeId,
        summary: `Budget: ${ev.spent}/${ev.limit} ${ev.unit}`,
        deepLink,
        value: ev.spent,
        limit: ev.limit,
      };
      pushItem(item);
      return item;
    }

    case 'confidence.updated': {
      const cardId = cardIdForSession(ev.session_id);
      const deepLink = resolveCard(liveMaps(), cardId);
      const item: AttentionItem = {
        id: `confidence:${ev.session_id}:${ev.message_id ?? 'na'}`,
        kind: 'confidence',
        cardId,
        sessionNodeId: deepLink.sessionNodeId,
        summary: `Confidence below gate: ${ev.score}`,
        deepLink,
        value: ev.score,
      };
      pushItem(item);
      return item;
    }

    case 'gate.updated': {
      const cardId = cardIdForSession(ev.session_id);
      const deepLink = resolveCard(liveMaps(), cardId);
      const item: AttentionItem = {
        id: `gate:${ev.session_id}:${ev.gate}`,
        kind: 'gate',
        cardId,
        sessionNodeId: deepLink.sessionNodeId,
        summary: `Gate ${ev.gate}: ${ev.decision}`,
        deepLink,
      };
      pushItem(item);
      return item;
    }

    case 'session.idle': {
      const cardId = cardIdForSession(ev.session_id);
      const deepLink = resolveCard(liveMaps(), cardId);
      const item: AttentionItem = {
        id: `idle:${ev.session_id}`,
        kind: 'idle',
        cardId,
        sessionNodeId: deepLink.sessionNodeId,
        summary: 'Session idle — awaiting input',
        deepLink,
      };
      pushItem(item);
      return item;
    }

    default:
      return null;
  }
}


/**
 * Raw Claude Code `PreToolUse` hook payload shape (best-effort; the CLI's schema
 * may evolve — confirm at build). OpenCode's `permission` callback is shaped
 */
export interface CliPreToolUsePayload {
  hook_event_name?: string; // "PreToolUse"
  tool_name: string;
  tool_input?: Record<string, unknown>;
  cwd?: string;
  session_id?: string;
  permission_request_id?: string;
}

/**
 * Normalize a raw CLI hook payload into the SAME `permission.updated` event the
 * native server emits, so the proxy routes through ingestEvent with no separate
 */
export function normalizeCliPermission(
  raw: CliPreToolUsePayload,
): Extract<AgentEvent, { type: 'permission.updated' }> {
  const args: Record<string, unknown> = { ...(raw.tool_input ?? {}) };
  // PreToolUse carries cwd at the top level, not inside tool_input — fold it in
  // so affectedPathFromArgs can surface it.
  if (raw.cwd && args.cwd === undefined) args.cwd = raw.cwd;
  return {
    type: 'permission.updated',
    v: 1,
    id: raw.permission_request_id ?? raw.session_id ?? raw.tool_name,
    tool_name: raw.tool_name,
    args,
    dimension: 'tool',
  };
}


/**
 * Map a loaded run snapshot to AttentionItems
 * Blocked column (deriveColumn === 'Blocked') → blocked item
 */
export function ingestSnapshotDecisions(runData: RunData | null): void {
  if (!runData) return;
  const maps = liveMaps();

  for (const node of runData.session_tree.nodes) {
    if (node.parent_run_id === null) continue;
    if (deriveColumn(node) !== 'Blocked') continue;
    const deepLink = resolveCard(maps, node.id);
    pushItem({
      id: `blocked:${node.id}`,
      kind: 'blocked',
      cardId: node.id,
      sessionNodeId: deepLink.sessionNodeId,
      summary: `Blocked: ${node.scope ?? node.id}`,
      deepLink,
    });
  }

  const signOff = runData.run_final?.sign_off;
  if (signOff) {
    const rootId = runData.session_tree.root_id;
    const deepLink = resolveCard(maps, rootId);
    pushItem({
      id: `signoff:${runData.run_id}`,
      kind: 'signoff',
      cardId: rootId,
      sessionNodeId: deepLink.sessionNodeId,
      summary: `Sign-off available: ${signOff.decision}`,
      deepLink,
    });
  }

  const claims = runData.audit?.unsupported_claims ?? [];
  for (let i = 0; i < claims.length; i++) {
    const rootId = runData.session_tree.root_id;
    const deepLink = resolveCard(maps, rootId);
    pushItem({
      id: `unsupported:${runData.run_id}:${i}`,
      kind: 'unsupported',
      cardId: rootId,
      sessionNodeId: deepLink.sessionNodeId,
      summary: `Unsupported claim: ${claims[i]}`,
      deepLink,
    });
  }
}

export { attentionQueue };

/**
 * Test-only reset: clears the global queue. Tests call this in afterEach so
 * ingest state does not leak across tests (mirrors __resetBridgeMaps)
 */
export function __resetAttentionQueue(): void {
  setAttentionQueue([]);
}
