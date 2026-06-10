import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';

// V15-04: the live permission gate replies through the SDK — mock it so the
// gate tests assert the POST contract without a server.
vi.mock('../../../../../sdk/typescript/src/client/permission', () => ({
  replyPermission: vi.fn(),
}));
// V15-04: the spawn-failure Retry re-invokes startVossServe — mock the Tauri
// wrapper so no command is issued under jsdom.
vi.mock('../../org/live/sidecarClient', () => ({
  startVossServe: vi.fn(),
}));

import ProtocolPane from '../ProtocolPane';
import type { AgentEvent } from '../../../../../sdk/typescript/src/client/sse';
import { replyPermission } from '../../../../../sdk/typescript/src/client/permission';
import { startVossServe } from '../../org/live/sidecarClient';
import {
  attentionQueue,
  __resetAttentionQueue,
} from '../../org/attention/attentionQueue';
import { __resetLiveStream } from '../../org/live/sseClient';
import { __resetBridgeMaps } from '../../org/model/bridge';

const mockReply = vi.mocked(replyPermission);
const mockStartServe = vi.mocked(startVossServe);

// V15-03 (VLIVE-04): the structured protocol pane renders the §6 union as DOM
// per the UI-SPEC — dedicated rows for user/tool/plan/stream/final/thinking,
// a generic fallback for everything else (nothing silently dropped), D-07
// collapsed tool lines with click-expand, and the D-08 capped/pinned transcript.
// The stream is injected (Pitfall 4 — the webview only consumes).

function ev(payload: Record<string, unknown>): AgentEvent {
  return { v: 1, ...payload } as unknown as AgentEvent;
}

async function* scripted(events: AgentEvent[]): AsyncGenerator<AgentEvent> {
  for (const e of events) yield e;
}

const flush = () => new Promise((r) => setTimeout(r, 0));

let disposers: (() => void)[] = [];

function mount(stream: AsyncIterable<AgentEvent>): HTMLElement {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const dispose = render(
    () => (
      <ProtocolPane
        sessionId="sess-1"
        baseUrl="http://localhost:0"
        token="tok"
        stream={stream}
      />
    ),
    container,
  );
  disposers.push(() => {
    dispose();
    container.remove();
  });
  return container;
}

afterEach(() => {
  for (const d of disposers) d();
  disposers = [];
  vi.clearAllMocks();
  __resetLiveStream();
  __resetAttentionQueue();
  __resetBridgeMaps();
});

const PERMISSION_EVENT = () =>
  ev({
    type: 'permission.updated',
    id: 'perm-1',
    tool_name: 'bash',
    args: { cmd: 'rm -rf build', path: 'src/auth' },
    dimension: 'tool',
  });

function gateButtons(c: HTMLElement): HTMLButtonElement[] {
  return Array.from(c.querySelectorAll<HTMLButtonElement>('.proto-pgbtn'));
}

describe('ProtocolPane — dedicated rows (UI-SPEC §2)', () => {
  it('renders the user event as the task header', async () => {
    const c = mount(scripted([ev({ type: 'user', task: 'Fix the auth bug' })]));
    await flush();

    const hdr = c.querySelector('.proto-task-hdr');
    expect(hdr).not.toBeNull();
    expect(hdr?.querySelector('.proto-task-hdr__text')?.textContent).toBe(
      'Fix the auth bug',
    );
  });

  it('renders a tool event collapsed (no excerpt) and expands on click (D-07)', async () => {
    const c = mount(
      scripted([
        ev({
          type: 'tool',
          name: 'fs_edit',
          state: 'ok',
          summary: 'src/auth.ts +34 −2',
          args: { path: 'src/auth.ts' },
        }),
      ]),
    );
    await flush();

    const row = c.querySelector('.proto-tool-row');
    expect(row).not.toBeNull();
    expect(row?.textContent).toContain('fs_edit');
    expect(row?.textContent).toContain('src/auth.ts +34 −2');
    // Collapsed default: no expanded body, no args excerpt visible.
    expect(c.querySelector('.proto-tool-row--expanded')).toBeNull();
    expect(c.querySelector('.proto-tool-row__expanded-body')).toBeNull();

    (row as HTMLElement).dispatchEvent(
      new MouseEvent('click', { bubbles: true }),
    );
    await flush();

    expect(c.querySelector('.proto-tool-row--expanded')).not.toBeNull();
    const body = c.querySelector('.proto-tool-row__expanded-body');
    expect(body).not.toBeNull();
    expect(body?.textContent).toContain('path');
  });

  it('renders a plan event as a prose row', async () => {
    const c = mount(
      scripted([
        ev({
          type: 'plan',
          steps: [
            { name: 'read the failing test', args: {} },
            { name: 'patch the auth middleware', args: {} },
          ],
          confidence: 0.55,
        }),
      ]),
    );
    await flush();

    const row = c.querySelector('.proto-plan-row');
    expect(row).not.toBeNull();
    expect(row?.textContent).toContain('patch the auth middleware');
    // confidence < 0.7 renders the badge
    expect(c.querySelector('.proto-plan-conf')?.textContent).toContain('0.55');
  });

  it('coalesces stream.delta into one block and settles on finalize (D-09)', async () => {
    const c = mount(
      scripted([
        ev({ type: 'stream.delta', text: 'Looking at ' }),
        ev({ type: 'stream.delta', text: 'the failing test…' }),
        ev({ type: 'stream.finalize', role: 'assistant' }),
      ]),
    );
    await flush();

    const blocks = c.querySelectorAll('.proto-stream-block');
    expect(blocks.length).toBe(1);
    expect(blocks[0].textContent).toContain('Looking at the failing test…');
    expect(blocks[0].classList.contains('proto-stream-block--settled')).toBe(
      true,
    );
    expect(c.querySelector('.proto-stream-cursor')).toBeNull();
  });

  it('renders a final event with conf/cost meta', async () => {
    const c = mount(
      scripted([
        ev({ type: 'final', text: 'Done.', confidence: 0.92, cost_usd: 0.0312 }),
      ]),
    );
    await flush();

    const row = c.querySelector('.proto-final-row');
    expect(row).not.toBeNull();
    expect(row?.querySelector('.proto-final-row__text')?.textContent).toBe(
      'Done.',
    );
    expect(row?.querySelector('.proto-final-row__meta')?.textContent).toContain(
      '0.92',
    );
  });

  it('renders a thinking event as an italic dim row', async () => {
    const c = mount(scripted([ev({ type: 'thinking', label: 'planning' })]));
    await flush();

    expect(c.querySelector('.proto-thinking-row')?.textContent).toContain(
      'planning',
    );
  });
});

describe('ProtocolPane — generic fallback + no silent drop', () => {
  it('renders an out-of-set member (cognition_loaded) as exactly one generic row', async () => {
    const c = mount(
      scripted([
        ev({
          type: 'cognition_loaded',
          architecture_tokens: 1200,
          constraints_count: 4,
          decisions_loaded: 9,
          plans_loaded: 2,
        }),
      ]),
    );
    await flush();

    const rows = c.querySelectorAll('.proto-generic-row');
    expect(rows.length).toBe(1);
    expect(rows[0].textContent).toContain('cognition_loaded');
  });

  it('drops nothing: row count === event count for a no-coalescing sequence', async () => {
    const c = mount(
      scripted([
        ev({ type: 'user', task: 'task' }),
        ev({ type: 'thinking', label: 'l' }),
        ev({ type: 'tool', name: 't', state: 'pending', summary: 's', args: {} }),
        ev({ type: 'cognition_loaded', architecture_tokens: 1 }),
        ev({ type: 'warning', message: 'careful' }),
      ]),
    );
    await flush();

    const rows = c.querySelectorAll(
      '.proto-task-hdr, .proto-thinking-row, .proto-tool-row, .proto-generic-row',
    );
    expect(rows.length).toBe(5);
  });

  it('renders permission.updated as a pinned placeholder gate row', async () => {
    const c = mount(
      scripted([
        ev({
          type: 'permission.updated',
          id: 'perm-1',
          tool_name: 'bash',
          args: { cmd: 'rm -rf build' },
          dimension: 'tool',
        }),
      ]),
    );
    await flush();

    const gate = c.querySelector('.proto-permission-gate');
    expect(gate).not.toBeNull();
    expect(gate?.textContent).toContain('bash');
  });
});

describe('ProtocolPane — live permission gate (V15-04, VLIVE-05)', () => {
  it('renders the inline gate AND the queue row simultaneously', async () => {
    const c = mount(scripted([PERMISSION_EVENT()]));
    await flush();

    expect(c.querySelector('.proto-permission-gate')).not.toBeNull();
    const btns = gateButtons(c);
    expect(btns.map((b) => b.textContent?.trim())).toEqual([
      'Deny',
      'Allow once',
      expect.stringContaining('Allow for'),
    ]);
    // Dual surface: ingestEvent enqueued the row with the prefixed id.
    expect(attentionQueue().map((i) => i.id)).toContain('permission:perm-1');
  });

  it('Allow once posts {id, choice:"a"} once, resolves the gate, clears the queue row', async () => {
    mockReply.mockResolvedValueOnce(undefined);
    const c = mount(scripted([PERMISSION_EVENT()]));
    await flush();

    const allowOnce = gateButtons(c)[1];
    allowOnce.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flush();
    await flush();

    expect(mockReply).toHaveBeenCalledTimes(1);
    expect(mockReply).toHaveBeenCalledWith(expect.anything(), 'sess-1', {
      id: 'perm-1',
      choice: 'a',
    });
    const gate = c.querySelector('.proto-permission-gate');
    expect(gate?.classList.contains('proto-permission-gate--resolved')).toBe(
      true,
    );
    expect(gate?.textContent).toContain('allowed once');
    // Queue row cleared by the SAME prefixed id (T-V15-11).
    expect(
      attentionQueue().find((i) => i.id === 'permission:perm-1'),
    ).toBeUndefined();
  });

  it('Deny maps to "d" and Allow for scope maps to "A"', async () => {
    mockReply.mockResolvedValue(undefined);
    const c = mount(scripted([PERMISSION_EVENT()]));
    await flush();
    gateButtons(c)[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flush();
    expect(mockReply).toHaveBeenLastCalledWith(expect.anything(), 'sess-1', {
      id: 'perm-1',
      choice: 'd',
    });

    const c2 = mount(scripted([PERMISSION_EVENT()]));
    await flush();
    gateButtons(c2)[2].dispatchEvent(
      new MouseEvent('click', { bubbles: true }),
    );
    await flush();
    expect(mockReply).toHaveBeenLastCalledWith(expect.anything(), 'sess-1', {
      id: 'perm-1',
      choice: 'A',
    });
  });

  it('a rejected reply re-enables the buttons and keeps the queue row (no optimistic grant)', async () => {
    mockReply.mockRejectedValueOnce(new Error('403'));
    const c = mount(scripted([PERMISSION_EVENT()]));
    await flush();

    gateButtons(c)[1].dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await flush();
    await flush();

    const gate = c.querySelector('.proto-permission-gate');
    expect(gate?.classList.contains('proto-permission-gate--resolved')).toBe(
      false,
    );
    for (const b of gateButtons(c)) expect(b.disabled).toBe(false);
    expect(attentionQueue().map((i) => i.id)).toContain('permission:perm-1');
  });
});

describe('ProtocolPane — D-08 cap with pins', () => {
  it('a >300-event flood trims oldest non-pinned rows; task header + permission survive', async () => {
    const events: AgentEvent[] = [
      ev({ type: 'user', task: 'THE TASK' }),
      ev({
        type: 'permission.updated',
        id: 'perm-keep',
        tool_name: 'bash',
        args: {},
        dimension: 'tool',
      }),
    ];
    for (let i = 0; i < 340; i++) {
      events.push(ev({ type: 'thinking', label: `step-${i}` }));
    }
    const c = mount(scripted(events));
    await flush();
    await flush();

    // Pins survive the flood.
    expect(c.querySelector('.proto-task-hdr__text')?.textContent).toBe(
      'THE TASK',
    );
    expect(c.querySelector('.proto-permission-gate')).not.toBeNull();
    // The earliest non-pinned row was trimmed; the newest survives.
    expect(c.textContent).not.toContain('step-0');
    expect(c.textContent).toContain('step-339');
    // Cap holds (#rows bounded by CAP).
    const thinkingRows = c.querySelectorAll('.proto-thinking-row');
    expect(thinkingRows.length).toBeLessThanOrEqual(300);
  });
});
