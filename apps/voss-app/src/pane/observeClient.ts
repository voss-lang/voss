// Fire-and-forget by contract (AC-S3-7): a down sidecar fills a bounded
// drop-oldest queue and the PTY path never blocks.

import { callSidecar } from '../org/live/sidecarClient';

export const OBSERVE_ADAPTER_ID = 'voss-pty';
export const OBSERVE_QUEUE_LIMIT = 200;
// Started commands join finished events on cmd_id (CommandFinished carries no
// argv_text/cwd); the map is bounded so a long-lived pane never grows it.
const MAX_TRACKED_COMMANDS = 1000;

export type ObserveActor = 'developer' | 'voss' | 'external' | 'unknown';

export interface ObserveCommandStarted {
  cmd_id: string;
  argv_text: string;
  cwd: string;
  at: string;
}

export interface ObserveCommandFinished {
  cmd_id: string;
  exit: number;
  duration_ms: number;
  output: Uint8Array;
  truncated: boolean;
}

export interface ObserveContext {
  repositoryId: string;
  worktreeId: string;
}

interface CommandPayload {
  argv: string[];
  argv_text: string;
  cwd: string;
  exit_code?: number;
  duration_ms?: number;
  truncated?: boolean;
}

/** Mirrors `_ObserveBase` + the per-type payload in observe/models.py. */
export interface ObserveEventEnvelope {
  schema_version: 1;
  event_id: string;
  category: 'command';
  event_type: 'command.started' | 'command.completed';
  event_time: string;
  ingest_time: null;
  trace_id: string;
  parent_event_id: null;
  caused_by: null;
  actor: ObserveActor;
  source_ref: { source: 'adapter'; ref: string };
  external_identity_ref: null;
  repository_id: string;
  worktree_id: string;
  adapter_id: typeof OBSERVE_ADAPTER_ID;
  command_id: string;
  repository_state_id: string;
  evidence_refs: string[];
  payload: CommandPayload;
}

/** Captured output rides beside the envelope as plain text; the route redacts
 *  it and assigns evidence ids (`{event_id}-ev{N}`) into evidence_refs. */
export interface ObserveEvidence {
  kind: 'command_output';
  content: string;
  truncated: boolean;
}

export type ObservePost = (
  sidecarId: string,
  event: ObserveEventEnvelope,
  evidence: ObserveEvidence[],
) => Promise<unknown>;

export interface ObserveClientConfig {
  paneId: string;
  actor: ObserveActor;
  context: ObserveContext | Promise<ObserveContext> | (() => Promise<ObserveContext>);
  sidecarId: () => string | null;
  post?: ObservePost;
}

// The Rust sidecar proxy owns the bearer token; a 403 comes back as
// "observe_rejected:<reason>" (see send_observe_event in src-tauri).
const defaultPost: ObservePost = (sidecarId, event, evidence) =>
  callSidecar(sidecarId, { kind: 'observe_event', event, evidence });

const REJECTION_RE = /^observe_rejected:(\w+)$/;

function rejectionReason(err: unknown): string | null {
  const msg = err instanceof Error ? err.message : String(err);
  return REJECTION_RE.exec(msg)?.[1] ?? null;
}

type QueuedEvent = { eventId: string } & (
  | { kind: 'started'; ev: ObserveCommandStarted }
  | {
      kind: 'finished';
      ev: ObserveCommandFinished;
      argv_text: string;
      cwd: string;
      at: string;
    });

function splitArgv(text: string): string[] {
  return text.split(/\s+/).filter((w) => w.length > 0);
}

function nowIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, '+00:00');
}

const utf8 = new TextDecoder();

function buildEnvelope(
  cfg: ObserveClientConfig,
  ctx: ObserveContext,
  item: QueuedEvent,
): { event: ObserveEventEnvelope; evidence: ObserveEvidence[] } {
  const evidence: ObserveEvidence[] = [];
  if (item.kind === 'finished' && item.ev.output.length > 0) {
    evidence.push({
      kind: 'command_output',
      content: utf8.decode(item.ev.output),
      truncated: item.ev.truncated,
    });
  }
  const payload: CommandPayload = {
    argv: splitArgv(item.kind === 'started' ? item.ev.argv_text : item.argv_text),
    argv_text: item.kind === 'started' ? item.ev.argv_text : item.argv_text,
    cwd: item.kind === 'started' ? item.ev.cwd : item.cwd,
  };
  if (item.kind === 'finished') {
    payload.exit_code = item.ev.exit;
    payload.duration_ms = item.ev.duration_ms;
    payload.truncated = item.ev.truncated;
  }
  return {
    event: {
      schema_version: 1,
      event_id: item.eventId,
      category: 'command',
      event_type: item.kind === 'started' ? 'command.started' : 'command.completed',
      event_time: item.kind === 'started' ? item.ev.at : item.at,
      ingest_time: null,
      trace_id: item.ev.cmd_id,
      parent_event_id: null,
      caused_by: null,
      actor: cfg.actor,
      source_ref: { source: 'adapter', ref: cfg.paneId },
      external_identity_ref: null,
      repository_id: ctx.repositoryId,
      worktree_id: ctx.worktreeId,
      adapter_id: OBSERVE_ADAPTER_ID,
      command_id: item.ev.cmd_id,
      // The sidecar resolves Git state at ingest.
      repository_state_id: 'unavailable',
      evidence_refs: [],
      payload,
    },
    evidence,
  };
}

export class ObserveClient {
  private readonly cfg: ObserveClientConfig;
  private readonly post: ObservePost;
  private queue: QueuedEvent[] = [];
  private commands = new Map<string, { argv_text: string; cwd: string }>();
  private dropped = 0;
  private flushing = false;
  private ctx: ObserveContext | null = null;
  private retry: ReturnType<typeof setTimeout> | undefined;
  private disposed = false;

  constructor(cfg: ObserveClientConfig) {
    this.cfg = cfg;
    this.post = cfg.post ?? defaultPost;
  }

  get droppedCount(): number {
    return this.dropped;
  }

  get queueSize(): number {
    return this.queue.length;
  }

  commandStarted(ev: ObserveCommandStarted): void {
    if (this.disposed) return;
    if (this.commands.size >= MAX_TRACKED_COMMANDS) {
      const oldest = this.commands.keys().next().value;
      if (oldest !== undefined) this.commands.delete(oldest);
    }
    this.commands.set(ev.cmd_id, { argv_text: ev.argv_text, cwd: ev.cwd });
    this.enqueue({ kind: 'started', ev, eventId: crypto.randomUUID().replaceAll('-', '') });
  }

  commandFinished(ev: ObserveCommandFinished): void {
    if (this.disposed) return;
    const startedCmd = this.commands.get(ev.cmd_id);
    this.commands.delete(ev.cmd_id);
    // The reader only emits finished for a started command; an unknown cmd_id
    // (evicted above) has no identity to build the required payload from.
    if (!startedCmd) return;
    this.enqueue({
      kind: 'finished',
      eventId: crypto.randomUUID().replaceAll('-', ''),
      ev,
      argv_text: startedCmd.argv_text,
      cwd: startedCmd.cwd,
      at: nowIso(),
    });
  }

  private enqueue(item: QueuedEvent): void {
    if (this.queue.length >= OBSERVE_QUEUE_LIMIT) {
      this.queue.shift();
      this.dropped += 1;
    }
    this.queue.push(item);
    void this.flush();
  }

  private async flush(): Promise<void> {
    if (this.flushing || this.disposed) return;
    clearTimeout(this.retry);
    this.flushing = true;
    try {
      const sidecarId = this.cfg.sidecarId();
      if (!sidecarId) return;
      this.ctx ??= await (typeof this.cfg.context === 'function' ? this.cfg.context() : this.cfg.context);
      while (this.queue.length > 0 && !this.disposed) {
        const item = this.queue[0];
        const { event, evidence } = buildEnvelope(this.cfg, this.ctx, item);
        try {
          await this.post(sidecarId, event, evidence);
        } catch (err) {
          const reason = rejectionReason(err);
          if (reason !== null) {
            this.queue = [];
            this.commands.clear();
          }
          break;
        }
        if (this.queue[0] === item) this.queue.shift();
      }
    } catch {
      // Context resolution failed — events stay queued for the next flush.
    } finally {
      this.flushing = false;
      if (this.queue.length > 0 && !this.disposed) {
        this.retry = setTimeout(() => void this.flush(), 1000);
      }
    }
  }

  dispose(): void {
    this.disposed = true;
    clearTimeout(this.retry);
    this.queue = [];
    this.commands.clear();
  }
}

/** Resolve identity through the same Git discovery used by CLI enrollment. */
export async function observeContextForWorkspace(
  workspacePath: string,
  sidecarId: string,
): Promise<ObserveContext> {
  return callSidecar<ObserveContext>(sidecarId, { kind: 'observe_context', cwd: workspacePath });
}

const clients = new Map<string, ObserveClient>();

export function createObserveClient(cfg: ObserveClientConfig): ObserveClient {
  const client = new ObserveClient(cfg);
  clients.set(cfg.paneId, client);
  return client;
}

export function disposeObserveClient(paneId: string): void {
  clients.get(paneId)?.dispose();
  clients.delete(paneId);
}

/** Aggregate queue stats across panes for the status-bar tooltip. */
export function observeQueueStats(): { queued: number; dropped: number } {
  let queued = 0;
  let dropped = 0;
  for (const c of clients.values()) {
    queued += c.queueSize;
    dropped += c.droppedCount;
  }
  return { queued, dropped };
}

/** Test-only reset. */
export function __resetObserveClients(): void {
  for (const client of clients.values()) client.dispose();
  clients.clear();
}
