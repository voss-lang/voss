import { createSignal } from 'solid-js';

import type {
  SessionInfo,
  VossClient,
} from '../../../../../sdk/typescript/src/client/rest';
import { registerNativeCard } from '../model/bridge';

const [serverSessions, setServerSessions] = createSignal<SessionInfo[]>([]);
const [sessionsLoading, setSessionsLoading] = createSignal(false);

export function sessionId(info: SessionInfo): string {
  return typeof info.id === 'string' ? info.id : '';
}

export function sessionTitle(info: SessionInfo): string {
  if (typeof info.title === 'string' && info.title.length > 0)
    return info.title;
  return sessionId(info);
}

export function sessionAgeLabel(info: SessionInfo): string {
  const ts =
    (info as Record<string, unknown>).updated_at ??
    (info as Record<string, unknown>).created_at;
  let ms: number | null = null;
  if (typeof ts === 'number') ms = ts > 1e12 ? ts : ts * 1000;
  else if (typeof ts === 'string') {
    const parsed = Date.parse(ts);
    if (!Number.isNaN(parsed)) ms = parsed;
  }
  if (ms === null) return '';
  const minutes = Math.floor(Math.max(0, Date.now() - ms) / 60_000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function sortNewestFirst(list: SessionInfo[]): SessionInfo[] {
  const ts = (info: SessionInfo): number | null => {
    const raw =
      (info as Record<string, unknown>).updated_at ??
      (info as Record<string, unknown>).created_at;
    if (typeof raw === 'number') return raw;
    if (typeof raw === 'string') {
      const parsed = Date.parse(raw);
      return Number.isNaN(parsed) ? null : parsed;
    }
    return null;
  };
  if (list.some((s) => ts(s) !== null)) {
    return [...list].sort((a, b) => (ts(b) ?? 0) - (ts(a) ?? 0));
  }
  return [...list].reverse();
}

export async function refreshSessions(client: SidecarVossClient): Promise<void> {
  setSessionsLoading(true);
  try {
    setServerSessions(sortNewestFirst(await client.listSessions()));
  } catch {
  } finally {
    setSessionsLoading(false);
  }
}

export interface AttachSessionArgs {
  cwd: string;
  sessionId: string;

  ensureClient: (
    cwd: string,
  ) => Promise<{ sidecarId: string; client: SidecarVossClient }>;

  openAttachedPane: (record: {
    sessionId: string;
    baseUrl: string;
    token: string;
    client: VossClient;
  }) => void;
}

export async function attachSession(args: AttachSessionArgs): Promise<void> {
  const { baseUrl, token, client } = await args.ensureClient(args.cwd);
  registerNativeCard(args.sessionId, args.sessionId);
  args.openAttachedPane({
    sessionId: args.sessionId,
    baseUrl,
    token,
    client,
  });
}

export { serverSessions, sessionsLoading };

export function __resetServerSessions(): void {
  setServerSessions([]);
  setSessionsLoading(false);
}
