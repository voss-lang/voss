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

  id: string;
  kind: AttentionKind;
  cardId?: string;
  sessionNodeId?: string;

  summary: string;

  deepLink: DeepLink;

  tool?: string;
  args?: Record<string, unknown>;
  dimension?: string;
  affectedPath?: string;

  actions?: PermissionAction[];

  value?: number;
  limit?: number;
}

const [attentionQueue, setAttentionQueue] = createSignal<AttentionItem[]>([]);

function pushItem(item: AttentionItem): void {
  setAttentionQueue((prev) => {
    if (prev.some((existing) => existing.id === item.id)) return prev;
    return [...prev, item];
  });
}

export function resolveAttentionItem(id: string): void {
  setAttentionQueue((prev) => prev.filter((item) => item.id !== id));
}

function liveMaps() {
  return { cardToPane: cardToPane(), cardToSessionNode: cardToSessionNode() };
}

function cardIdForSession(sessionId: string): string {
  const map = cardToSessionNode();
  for (const cardId in map) {
    if (map[cardId] === sessionId) return cardId;
  }
  return sessionId; // snapshot/native: card id IS the session node id
}

export function permissionActionsFor(adopted: boolean): PermissionAction[] {
  return adopted ? [] : ['allow-once', 'allow-scoped', 'deny'];
}

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

  cardId?: string;

  adopted?: boolean;
}

export function ingestEvent(
  ev: AgentEvent,
  ctx: IngestContext = {},
): AttentionItem | null {
  switch (ev.type) {
    case 'permission.updated': {
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

export interface CliPreToolUsePayload {
  hook_event_name?: string; // "PreToolUse"
  tool_name: string;
  tool_input?: Record<string, unknown>;
  cwd?: string;
  session_id?: string;
  permission_request_id?: string;
}

export function normalizeCliPermission(
  raw: CliPreToolUsePayload,
): Extract<AgentEvent, { type: 'permission.updated' }> {
  const args: Record<string, unknown> = { ...(raw.tool_input ?? {}) };
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

export function __resetAttentionQueue(): void {
  setAttentionQueue([]);
}
