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
// T-V15-05: ALL event text renders via Solid text bindings ({…}) — never
// innerHTML. Pitfall 4: transcript signals are LOCAL per pane instance.
// The permission gate here is a pinned placeholder; Plan 04 makes it live.

import { createEffect, createMemo, createSignal, For, onCleanup, onMount, Show, Switch, Match } from 'solid-js';
import type { AgentEvent } from '../../../../sdk/typescript/src/client/sse';
import { connectLiveStream } from '../org/live/sseClient';
import './ProtocolPane.css';

export interface ProtocolPaneProps {
  sessionId: string;
  baseUrl: string;
  token: string;
  /** Called when the session reports idle (Plans 04/05 fill the ended UX). */
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
  | { kind: 'permission'; toolName: string; args: unknown; dimension: string }
  | { kind: 'generic'; type: string; summary: string };

interface ToolEvent {
  name: string;
  state: 'pending' | 'ok' | 'error';
  summary: string;
  args?: Record<string, unknown>;
  result?: string;
}

export default function ProtocolPane(props: ProtocolPaneProps) {
  // LOCAL per-pane signals — never module-level (Pitfall 4).
  const [events, setEvents] = createSignal<AgentEvent[]>([]);
  const [expanded, setExpanded] = createSignal<Set<number>>(new Set());

  const appendEvent = (ev: AgentEvent) => {
    setEvents((prev) => trimOldest([...prev, ev], CAP));
    if (ev.type === 'session.idle') props.onEnded?.();
  };

  onMount(() => {
    const handle = connectLiveStream({
      baseUrl: props.baseUrl,
      sessionId: props.sessionId,
      token: props.token,
      cardId: props.sessionId, // Bridge A: the session id IS the cardId
      stream: props.stream,
      onEvent: appendEvent,
    });
    onCleanup(() => handle.abort());
  });

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
      class="protocol-pane"
      ref={scrollRef}
      onScroll={onScroll}
      role="log"
      aria-label="Run transcript"
    >
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
                return (
                  <div class="proto-permission-gate">
                    <div class="proto-permission-gate__label">
                      ⚠ needs your approval · {r.dimension}
                    </div>
                    <div class="proto-permission-gate__args">
                      {r.toolName}: {JSON.stringify(r.args ?? {})}
                    </div>
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
    </div>
  );
}
