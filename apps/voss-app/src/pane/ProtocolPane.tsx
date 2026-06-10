// V15-03 (VLIVE-04) — Structured Protocol Pane body. Renders the PROTOCOL §6
// event union as DOM per the V15-UI-SPEC: dedicated rows for user / tool /
// plan / stream.delta+finalize / final / thinking / permission.updated, and a
// generic fallback row for every other member — nothing is silently dropped.
//
// D-07: tool lines are collapsed one-liners; click expands args/result.
// D-08: the transcript is capped (CAP=300) trim-oldest; the first `user`
//       (task header) and permission.updated rows are pinned.
// D-09: consecutive stream.delta events grow ONE block with a pulse cursor;
//       stream.finalize settles it. Sticky-bottom autoscroll unless the user
//       scrolled up >20px.
//
// T-V15-05: ALL event text renders via Solid text bindings ({…}) — no raw
// HTML injection. Pitfall 4: transcript signals are LOCAL per pane instance.
// The permission gate here is a pinned placeholder; Plan 04 makes it live.

import { createEffect, createMemo, createSignal, For, onCleanup, onMount, Show, Switch, Match } from 'solid-js';
import type { AgentEvent } from '../../../../sdk/typescript/src/client/sse';
import {
  replyPermission,
  type PermissionChoice,
} from '../../../../sdk/typescript/src/client/permission';
import { createVossClient } from '../../../../sdk/typescript/src/client/rest';
import {
  connectLiveStream,
  liveHandles,
  type LiveStreamHandle,
} from '../org/live/sseClient';
import { resolveAttentionItem } from '../org/attention/attentionQueue';
import { startVossServe } from '../org/live/sidecarClient';
import ExitBanner from './ExitBanner';
import './ProtocolPane.css';

export interface ProtocolPaneProps {
  sessionId: string;
  baseUrl: string;
  token: string;
  /** Workspace cwd — the D-12 "Retry start" re-invokes startVossServe(cwd). */
  cwd?: string;
  /** Called when the session ends (clean idle or server death — D-11). */
  onEnded?: () => void;
  /** Test/mock injection — forwarded to connectLiveStream (Pitfall 4). */
  stream?: AsyncIterable<AgentEvent>;
}

const CAP = 300;

/**
 * D-08 trim: drop oldest entries until length ≤ cap, never trimming the
 * task header (a `user` event sitting at index 0) or any `permission.updated`.
 * Pure; input untouched.
 */
export function trimOldest(list: AgentEvent[], cap: number): AgentEvent[] {
  if (list.length <= cap) return list;
  const out = [...list];
  let i = 0;
  while (out.length > cap && i < out.length) {
    const e = out[i];
    const pinnedTask = i === 0 && e.type === 'user';
    const pinnedPermission = e.type === 'permission.updated';
    if (pinnedTask || pinnedPermission) {
      i += 1;
      continue;
    }
    out.splice(i, 1);
  }
  return out;
}

/** Generic-row summary: first present text-like field, else truncated JSON.
 *  `probable` shows its probability % ahead of the text (UI-SPEC §2g). */
function genericSummary(ev: AgentEvent): string {
  const r = ev as unknown as Record<string, unknown>;
  const pct =
    ev.type === 'probable' && typeof r.probability === 'number'
      ? `${Math.round((r.probability as number) * 100)}% `
      : '';
  for (const key of ['message', 'label', 'task', 'text'] as const) {
    if (typeof r[key] === 'string') return pct + (r[key] as string);
  }
  return pct + JSON.stringify(r).slice(0, 80);
}

const AMBER_TYPES = new Set([
  'warning',
  'probable',
  'cognition_overflow',
  'principles_overflow',
]);

function genericPrefix(type: string): string | null {
  if (type === 'warning') return '[warn]';
  if (type === 'cognition_overflow' || type === 'principles_overflow')
    return '[overflow]';
  return null;
}

// Transcript row descriptors — rebuilt per memo run from the event list, so
// local mutation during construction is safe (never signal state).
type Row =
  | { kind: 'task'; text: string }
  | { kind: 'tool'; ev: ToolEvent; idx: number }
  | { kind: 'plan'; text: string; confidence?: number }
  | { kind: 'stream'; text: string; settled: boolean }
  | { kind: 'final'; text: string; confidence?: number; costUsd?: number }
  | { kind: 'thinking'; label: string }
  | {
      kind: 'permission';
      id: string;
      toolName: string;
      args: unknown;
      dimension: string;
    }
  | { kind: 'generic'; type: string; summary: string };

interface ToolEvent {
  name: string;
  state: 'pending' | 'ok' | 'error';
  summary: string;
  args?: Record<string, unknown>;
  result?: string;
}

type GateState =
  | { state: 'pending' }
  | { state: 'inflight'; choice: PermissionChoice }
  | { state: 'resolved'; choice: PermissionChoice };

const RESOLVED_LABEL: Record<string, string> = {
  d: 'denied',
  a: 'allowed once',
  A: 'allowed for scope',
};

/** Allow-for-scope label: first path-looking string in args, else "session". */
function scopeLabel(args: unknown): string {
  if (args && typeof args === 'object') {
    for (const v of Object.values(args as Record<string, unknown>)) {
      if (typeof v === 'string' && v.includes('/')) return v;
    }
  }
  return 'session';
}

export default function ProtocolPane(props: ProtocolPaneProps) {
  // LOCAL per-pane signals — never module-level (Pitfall 4).
  const [events, setEvents] = createSignal<AgentEvent[]>([]);
  const [expanded, setExpanded] = createSignal<Set<number>>(new Set());
  // V15-04 gate state per permission id ('pending' default).
  const [gateStates, setGateStates] = createSignal<Record<string, GateState>>(
    {},
  );

  // V15-04 lifecycle (D-10/D-11/D-12): boot placeholder until the first
  // event, spawn-error with retry, honest ended state on stream death.
  const [bootState, setBootState] = createSignal<
    'booting' | 'live' | 'ended' | 'error'
  >('booting');
  const [elapsed, setElapsed] = createSignal(0);
  const [errorMsg, setErrorMsg] = createSignal('');
  const [died, setDied] = createSignal(false); // server death (≠ clean idle)
  let sawCleanEnd = false;
  let eventCount = 0;

  // The live connection (retry can rebind to a fresh handshake).
  const [conn, setConn] = createSignal({
    baseUrl: props.baseUrl,
    token: props.token,
  });

  // The reply client is built from the pane's own handshake fields — Bearer
  // middleware on every request (T-V15-03); constructed per reply (cheap).
  const replyClient = () => createVossClient(conn().baseUrl, conn().token);

  /** One reply loop for both surfaces: POST first, clear ONLY on success
   *  (never optimistic — T-V15-07); the queue clear uses the identical
   *  `permission:${id}` prefixed id (T-V15-11). */
  const replyToGate = async (id: string, choice: PermissionChoice) => {
    const current = gateStates()[id];
    if (current && current.state !== 'pending') return; // in-flight/resolved
    setGateStates((prev) => ({ ...prev, [id]: { state: 'inflight', choice } }));
    try {
      await replyPermission(replyClient(), props.sessionId, { id, choice });
      setGateStates((prev) => ({
        ...prev,
        [id]: { state: 'resolved', choice },
      }));
      resolveAttentionItem(`permission:${id}`);
    } catch {
      // Failed POST: both surfaces stay pending; buttons re-enable.
      setGateStates((prev) => ({ ...prev, [id]: { state: 'pending' } }));
    }
  };

  const appendEvent = (ev: AgentEvent) => {
    eventCount += 1;
    if (bootState() === 'booting') setBootState('live'); // first event = connected (D-10)
    if (ev.type === 'session.idle' || ev.type === 'final') sawCleanEnd = true;
    setEvents((prev) => trimOldest([...prev, ev], CAP));
    if (ev.type === 'session.idle') props.onEnded?.();
  };

  let handle: LiveStreamHandle | undefined;
  const connect = (
    baseUrl: string,
    token: string,
    stream?: AsyncIterable<AgentEvent>,
  ) => {
    handle?.abort();
    setConn({ baseUrl, token });
    handle = connectLiveStream({
      baseUrl,
      sessionId: props.sessionId,
      token,
      cardId: props.sessionId, // Bridge A: the session id IS the cardId
      stream,
      onEvent: appendEvent,
    });
  };

  onMount(() => {
    connect(props.baseUrl, props.token, props.stream);
    const tick = setInterval(() => {
      if (bootState() === 'booting') setElapsed((n) => n + 1);
    }, 1000);
    onCleanup(() => {
      clearInterval(tick);
      handle?.abort();
    });
  });

  // Stream-end detection: this session leaves the liveHandles set when its
  // for-await ends (clean or death). Zero events while booting = the stream
  // never connected → spawn/connect failure (D-12); otherwise ended (D-11) —
  // death (no final/session.idle seen) flips write affordances via onEnded.
  let wasConnected = false;
  createEffect(() => {
    const connected = liveHandles().has(props.sessionId);
    if (connected) {
      wasConnected = true;
      return;
    }
    if (!wasConnected) return;
    wasConnected = false;
    if (bootState() === 'booting' && eventCount === 0) {
      setErrorMsg('stream did not connect');
      setBootState('error');
      return;
    }
    setBootState('ended');
    if (!sawCleanEnd) {
      setDied(true);
      props.onEnded?.();
    }
  });

  // D-12: Retry start — re-invoke the sidecar spawn and rebind the stream to
  // the fresh handshake. No auto-restart anywhere; this is user-initiated.
  const retryStart = async () => {
    setBootState('booting');
    setElapsed(0);
    setDied(false);
    try {
      const h = await startVossServe(props.cwd ?? '');
      connect(`http://127.0.0.1:${h.port}`, h.token);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setBootState('error');
    }
  };

  // Coalesce the event list into row descriptors (D-09 stream blocks).
  const rows = createMemo<Row[]>(() => {
    const out: Row[] = [];
    events().forEach((ev, idx) => {
      const e = ev as unknown as Record<string, unknown>;
      switch (ev.type) {
        case 'user':
          out.push({ kind: 'task', text: String(e.task ?? '') });
          break;
        case 'tool':
          out.push({ kind: 'tool', ev: e as unknown as ToolEvent, idx });
          break;
        case 'plan': {
          // §6 plan = {steps: [{name, args}], confidence} — render step names
          // as prose lines (the UI-SPEC prose block).
          const steps = Array.isArray(e.steps) ? (e.steps as { name?: string }[]) : [];
          const text =
            steps.map((s, i) => `${i + 1}. ${s.name ?? ''}`).join('\n') ||
            String(e.text ?? '');
          out.push({
            kind: 'plan',
            text,
            confidence: typeof e.confidence === 'number' ? e.confidence : undefined,
          });
          break;
        }
        case 'stream.delta': {
          const last = out[out.length - 1];
          if (last && last.kind === 'stream' && !last.settled) {
            last.text += String(e.text ?? '');
          } else {
            out.push({ kind: 'stream', text: String(e.text ?? ''), settled: false });
          }
          break;
        }
        case 'stream.finalize': {
          for (let i = out.length - 1; i >= 0; i--) {
            const r = out[i];
            if (r.kind === 'stream' && !r.settled) {
              r.settled = true;
              break;
            }
          }
          break;
        }
        case 'final':
          out.push({
            kind: 'final',
            text: String(e.text ?? ''),
            confidence: typeof e.confidence === 'number' ? e.confidence : undefined,
            costUsd: typeof e.cost_usd === 'number' ? e.cost_usd : undefined,
          });
          break;
        case 'thinking':
          out.push({ kind: 'thinking', label: String(e.label ?? '') });
          break;
        case 'permission.updated':
          out.push({
            kind: 'permission',
            id: String(e.id ?? ''),
            toolName: String(e.tool_name ?? ''),
            args: e.args,
            dimension: String(e.dimension ?? 'tool'),
          });
          break;
        default:
          out.push({ kind: 'generic', type: ev.type, summary: genericSummary(ev) });
          break;
      }
    });
    return out;
  });

  // D-09 sticky-bottom autoscroll: pinned while the user is within 20px of
  // the bottom; scrolling up disables, returning re-enables.
  let scrollRef: HTMLDivElement | undefined;
  let stick = true;
  const onScroll = () => {
    if (!scrollRef) return;
    stick =
      scrollRef.scrollHeight - scrollRef.scrollTop - scrollRef.clientHeight <=
      20;
  };
  createEffect(() => {
    rows();
    if (stick && scrollRef) scrollRef.scrollTop = scrollRef.scrollHeight;
  });

  const toggleExpanded = (idx: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });

  const toolGlyphClass = (state: string) =>
    `proto-tool-row__glyph proto-tool-row__glyph--${state}`;
  const toolStateMark = (state: string) =>
    state === 'ok' ? '✓' : state === 'error' ? '✗' : '…';

  /** Expanded tool body text: args key:value lines + result excerpt (~20 lines). */
  const toolExpandedText = (t: ToolEvent): string => {
    const lines: string[] = [];
    for (const [k, v] of Object.entries(t.args ?? {})) {
      lines.push(`${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`);
    }
    if (typeof t.result === 'string' && t.result.length > 0) {
      const resultLines = t.result.split('\n');
      lines.push('', ...resultLines.slice(0, 20));
      if (resultLines.length > 20) lines.push('… (truncated)');
    }
    return lines.join('\n');
  };

  return (
    <div
      class={`protocol-pane${died() ? ' pane--proto-ended' : ''}`}
      ref={scrollRef}
      onScroll={onScroll}
      role="log"
      aria-label="Run transcript"
    >
      {/* D-10 boot placeholder — until the first event arrives. */}
      <Show when={bootState() === 'booting'}>
        <div class="proto-boot">
          <div class="proto-boot__label">Starting…</div>
          <div class="proto-boot__elapsed">{elapsed()}s</div>
          <Show when={elapsed() >= 5}>
            <div class="proto-boot__sub">Cold start takes up to 60s</div>
          </Show>
        </div>
      </Show>

      {/* D-12 spawn-failure — stderr tail + user-initiated retry. */}
      <Show when={bootState() === 'error'}>
        <div class="proto-spawn-error">
          <div class="proto-spawn-error__heading">
            Could not start — {errorMsg().split('\n')[0]}
          </div>
          <div class="proto-spawn-error__stderr">{errorMsg()}</div>
          <button
            type="button"
            class="proto-spawn-error__retry"
            onClick={() => void retryStart()}
          >
            Retry start
          </button>
        </div>
      </Show>

      <For each={rows()}>
        {(row) => (
          <Switch>
            <Match when={row.kind === 'task'}>
              <div class="proto-task-hdr">
                <span class="proto-task-hdr__glyph" aria-hidden="true">
                  ▸
                </span>
                <span class="proto-task-hdr__text">
                  {(row as Extract<Row, { kind: 'task' }>).text}
                </span>
              </div>
            </Match>

            <Match when={row.kind === 'tool'}>
              {(() => {
                const r = row as Extract<Row, { kind: 'tool' }>;
                const isOpen = () => expanded().has(r.idx);
                return (
                  <div
                    class={`proto-tool-row${isOpen() ? ' proto-tool-row--expanded' : ''}`}
                    onClick={() => toggleExpanded(r.idx)}
                  >
                    <div class="proto-tool-row__line">
                      <span class={toolGlyphClass(r.ev.state)} aria-hidden="true">
                        ⏺
                      </span>
                      <span class="proto-tool-row__name">{r.ev.name}</span>
                      <span class="proto-tool-row__summary">{r.ev.summary}</span>
                      <span
                        class={`proto-tool-row__state proto-tool-row__state--${r.ev.state}`}
                      >
                        {toolStateMark(r.ev.state)}
                      </span>
                      <span class="proto-tool-row__chevron" aria-hidden="true">
                        ›
                      </span>
                    </div>
                    <Show when={isOpen()}>
                      <div class="proto-tool-row__expanded-body">
                        {toolExpandedText(r.ev)}
                      </div>
                    </Show>
                  </div>
                );
              })()}
            </Match>

            <Match when={row.kind === 'plan'}>
              {(() => {
                const r = row as Extract<Row, { kind: 'plan' }>;
                return (
                  <div class="proto-plan-row">
                    {r.text}
                    <Show when={r.confidence !== undefined}>
                      <span
                        class={`proto-plan-conf${(r.confidence ?? 1) < 0.7 ? ' proto-plan-conf--low' : ''}`}
                      >
                        conf {r.confidence}
                      </span>
                    </Show>
                  </div>
                );
              })()}
            </Match>

            <Match when={row.kind === 'stream'}>
              {(() => {
                const r = row as Extract<Row, { kind: 'stream' }>;
                return (
                  <div
                    class={`proto-stream-block${r.settled ? ' proto-stream-block--settled' : ''}`}
                  >
                    {r.text}
                    <Show when={!r.settled}>
                      <span class="proto-stream-cursor" aria-hidden="true" />
                    </Show>
                  </div>
                );
              })()}
            </Match>

            <Match when={row.kind === 'final'}>
              {(() => {
                const r = row as Extract<Row, { kind: 'final' }>;
                return (
                  <div class="proto-final-row">
                    <div class="proto-final-row__text">{r.text}</div>
                    <Show when={r.confidence !== undefined || r.costUsd !== undefined}>
                      <div class="proto-final-row__meta">
                        {r.confidence !== undefined ? `conf ${r.confidence}` : ''}
                        {r.confidence !== undefined && r.costUsd !== undefined
                          ? ' · '
                          : ''}
                        {r.costUsd !== undefined
                          ? `$${r.costUsd.toFixed(4)}`
                          : ''}
                      </div>
                    </Show>
                  </div>
                );
              })()}
            </Match>

            <Match when={row.kind === 'thinking'}>
              <div class="proto-thinking-row">
                … {(row as Extract<Row, { kind: 'thinking' }>).label}
              </div>
            </Match>

            <Match when={row.kind === 'permission'}>
              {(() => {
                const r = row as Extract<Row, { kind: 'permission' }>;
                const gate = () =>
                  gateStates()[r.id] ?? ({ state: 'pending' } as GateState);
                const inflight = () => gate().state === 'inflight';
                const resolved = () => gate().state === 'resolved';
                const resolvedChoice = () => {
                  const g = gate();
                  return g.state === 'resolved' ? g.choice : undefined;
                };
                return (
                  <div
                    class={`proto-permission-gate${resolved() ? ' proto-permission-gate--resolved' : ''}`}
                  >
                    <div class="proto-permission-gate__label">
                      ⚠ needs your approval · {r.dimension}
                    </div>
                    <div class="proto-permission-gate__args">
                      {r.toolName}: {JSON.stringify(r.args ?? {})}
                    </div>
                    <Show
                      when={!resolved()}
                      fallback={
                        <div class="proto-permission-gate__resolved-label">
                          {RESOLVED_LABEL[resolvedChoice() ?? 'a']}
                        </div>
                      }
                    >
                      <div class="proto-permission-gate__btns">
                        <button
                          type="button"
                          class="proto-pgbtn proto-pgbtn--deny"
                          disabled={inflight()}
                          onClick={() => void replyToGate(r.id, 'd')}
                        >
                          Deny
                        </button>
                        <button
                          type="button"
                          class="proto-pgbtn"
                          disabled={inflight()}
                          onClick={() => void replyToGate(r.id, 'a')}
                        >
                          Allow once
                        </button>
                        <button
                          type="button"
                          class="proto-pgbtn proto-pgbtn--allow-scope"
                          disabled={inflight()}
                          onClick={() => void replyToGate(r.id, 'A')}
                        >
                          Allow for {scopeLabel(r.args)}
                        </button>
                      </div>
                    </Show>
                  </div>
                );
              })()}
            </Match>

            <Match when={row.kind === 'generic'}>
              {(() => {
                const r = row as Extract<Row, { kind: 'generic' }>;
                const prefix = genericPrefix(r.type);
                return (
                  <div class="proto-generic-row">
                    <span
                      class={`proto-generic-row__type${AMBER_TYPES.has(r.type) ? ' proto-generic-row__type--amber' : ''}`}
                    >
                      {prefix ? `${prefix} ` : ''}
                      {r.type}
                    </span>
                    <span class="proto-generic-row__summary">{r.summary}</span>
                  </div>
                );
              })()}
            </Match>
          </Switch>
        )}
      </For>

      {/* D-11 ended row — inline in transcript flow (scrolls with it); no
          Restart for server death (the NEXT run respawns fresh). */}
      <Show when={bootState() === 'ended'}>
        <div class="proto-ended-row">
          <ExitBanner
            exitCode={died() ? 1 : 0}
            message="[session ended]"
            showRestart={false}
            onRestart={() => {}}
          />
        </div>
      </Show>
    </div>
  );
}
