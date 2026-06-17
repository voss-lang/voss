// V24 Orchestra — command bar + quick actions + hint strip.
//
// Directs LIVE agents only (honest): targets are the assigned builder sessions
// known from swarm.assign (swarmAssignments: role ↔ sessionId). `@all` broadcasts
// to every live session; `@<role>` targets one. Send goes through the existing
// live write path (FollowUpClient.postMessage → POST /session/{id}/message). When
// nothing is live or there's no connection, the bar is disabled WITH A REASON —
// never a silent no-op, never a fake send. It does NOT start runs (⌘K composer
// owns that). Quick actions: Status report / Wrap up = canned broadcasts;
// Pause work has no server op yet → disabled-with-reason.

import { type Component, createMemo, createSignal, For, Show } from 'solid-js';
import { liveServer } from '../../org/live/liveServer';
import { swarmAssignments } from '../../org/live/swarmLive';

interface DirectTarget {
  label: string; // "@all" / "@builder-1"
  sessionIds: string[];
}

const STATUS_REPORT = 'Give a brief status report on your current task.';
const WRAP_UP = 'Wrap up your current work and summarize what is done.';

const SwarmCommandBar: Component = () => {
  const [text, setText] = createSignal('');
  const [target, setTarget] = createSignal('@all');
  const [note, setNote] = createSignal<string | null>(null);
  const [targetOpen, setTargetOpen] = createSignal(false);

  const assignments = () => Object.values(swarmAssignments());
  const followUp = () => liveServer()?.followUpClient;

  const targets = createMemo<DirectTarget[]>(() => {
    const all = assignments();
    const out: DirectTarget[] = [
      { label: '@all', sessionIds: all.map((a) => a.sessionId) },
    ];
    for (const a of all) {
      out.push({ label: `@${a.role}`, sessionIds: [a.sessionId] });
    }
    return out;
  });

  const liveCount = () => assignments().length;
  const connected = () => !!followUp();
  const disabledReason = (): string | null => {
    if (!connected()) return 'Not connected to a live Voss server.';
    if (liveCount() === 0) return 'No live agents to direct — start an orchestra.';
    return null;
  };
  const canSend = () => disabledReason() === null;

  /** Resolve the current "@target" selection to session ids. */
  function targetSessions(): string[] {
    return targets().find((t) => t.label === target())?.sessionIds ?? [];
  }

  async function broadcast(sessionIds: string[], body: string): Promise<void> {
    const fu = followUp();
    if (!fu || sessionIds.length === 0 || !body.trim()) return;
    await Promise.allSettled(sessionIds.map((id) => fu.postMessage(id, body.trim())));
  }

  async function onSend(): Promise<void> {
    const reason = disabledReason();
    if (reason) {
      setNote(reason);
      return;
    }
    // Parse a leading @token to override the dropdown target inline.
    let body = text();
    let ids = targetSessions();
    const m = body.match(/^@(\S+)\s+(.*)$/s);
    if (m) {
      const picked = targets().find((t) => t.label === `@${m[1]}`);
      if (picked) {
        ids = picked.sessionIds;
        body = m[2];
      }
    }
    if (!body.trim()) return;
    await broadcast(ids, body);
    setText('');
    setNote(null);
  }

  async function quick(kind: 'status' | 'wrap'): Promise<void> {
    const reason = disabledReason();
    if (reason) {
      setNote(reason);
      return;
    }
    const all = assignments().map((a) => a.sessionId);
    await broadcast(all, kind === 'status' ? STATUS_REPORT : WRAP_UP);
  }

  return (
    <div class="swarm-direct" role="group" aria-label="Direct the Orchestra">
      <div class="swarm-hint">
        <span class="swarm-hint__text">
          Click a chip to inspect · drag to pan · ⌘+wheel to zoom
        </span>
        <button
          type="button"
          class="swarm-quick"
          aria-label="Request a status report from all agents"
          disabled={!canSend()}
          onClick={() => void quick('status')}
        >
          Status report
        </button>
        <button
          type="button"
          class="swarm-quick"
          aria-label="Ask all agents to wrap up"
          disabled={!canSend()}
          onClick={() => void quick('wrap')}
        >
          Wrap up
        </button>
        <button
          type="button"
          class="swarm-quick"
          aria-label="Pause work (not supported yet)"
          disabled
          title="Pausing agents isn't supported yet."
        >
          Pause work
        </button>
      </div>

      <div class="swarm-bar">
        <div class="swarm-bar__target">
          <button
            type="button"
            class="swarm-bar__target-btn"
            aria-label="Choose direct target"
            aria-expanded={targetOpen() ? 'true' : 'false'}
            disabled={!canSend()}
            onClick={() => setTargetOpen((v) => !v)}
          >
            {target()} ▾
          </button>
          <Show when={targetOpen()}>
            <ul class="swarm-bar__menu" role="listbox" aria-label="Direct target">
              <For each={targets()}>
                {(t) => (
                  <li
                    role="option"
                    aria-selected={t.label === target() ? 'true' : 'false'}
                    class="swarm-bar__menu-item"
                    onClick={() => {
                      setTarget(t.label);
                      setTargetOpen(false);
                    }}
                  >
                    {t.label}
                  </li>
                )}
              </For>
            </ul>
          </Show>
        </div>

        <input
          class="swarm-bar__input"
          type="text"
          aria-label="Direct the Orchestra"
          placeholder={
            canSend()
              ? 'Direct the Orchestra…  (@ to target an agent)'
              : (disabledReason() ?? '')
          }
          disabled={!canSend()}
          value={text()}
          onInput={(e) => setText(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              void onSend();
            }
          }}
        />
        <button
          type="button"
          class="swarm-bar__send"
          aria-label="Send"
          disabled={!canSend()}
          onClick={() => void onSend()}
        >
          ➤
        </button>
      </div>

      <Show when={note()}>
        <p class="swarm-bar__note" role="alert">
          {note()}
        </p>
      </Show>
    </div>
  );
};

export default SwarmCommandBar;
