// VCKP-03 — RunCommandBar (D-03): an always-on top intake strip mounted above
// the 4-region cockpit grid. It is the universal run-intake keystone (closes
// G2): one bar that starts BOTH run types from the same captured context.
//
// Intake: goal/command input · mode segmented control (Plan/Edit/Auto — mode is
// ALWAYS visible as segmented buttons, NEVER hidden in placeholder text) · team
// selector · scope chip · budget chip · context-attach · an EXPLICIT
// Voss-native vs terminal-agent target indicator (visible segmented control,
// not placeholder).
//
// Two start paths (config-assembly mirrors AgentLaunchModal.buildConfig):
//   Bridge B (terminal): registerTerminalCard(paneId) mints the cardId, then
//     spawnAgent({..., sessionId: cardId, paneId}) — the cardId rides through as
//     the spawn_agent `sessionId` arg (zero Rust change). mode/team/scope/budget
//     are encoded into cliArgs so the launch carries the full intake context.
//   Bridge A (native): the injected V13.1 client's createSession(spec) returns
//     {id}; registerNativeCard(id, id) stores it (the create-response id IS the
//     snapshot node id — A1 finding). The client is GATED/mock in V14: when no
//     client is injected the native path is a disabled-with-reason no-op.
//
// Auto gating follows the decisionActions disabled-with-reason discipline: an
// Auto start missing budget OR scope renders the reason INLINE and calls NO
// start path (never a silent no-op).
//
// Styling: A12 tokens only (var(--bg-*), var(--accent-*), var(--border),
// var(--font-mono)); V14 chunk A restyles the strip to the cockpit mockup
// `.cmdbar` look (goal container with ▸ prefix, key:value chips, .seg
// segmented controls, focus-filled Start) via own run-bar__* classes in
// runCommandBar.css. No new --xxx tokens.

import { type Component, createSignal, For, Show } from 'solid-js';
import { invoke } from '@tauri-apps/api/core';
import './runCommandBar.css';
import {
  assembleRunSpec,
  validateAutoStart,
  type RunMode,
  type RunSpec,
  type RunTarget,
} from './runIntake';
import { registerTerminalCard, registerNativeCard } from '../model/bridge';

/** Minimal V13.1-client surface RunCommandBar consumes (mock-injectable). */
export interface RunNativeClient {
  createSession(spec: RunSpec): Promise<{ id: string }>;
}

/**
 * Default terminal launcher: invokes the existing `spawn_agent` Tauri command
 * directly with the minted cardId as the `sessionId` arg (Bridge B). Mirrors
 * pty-ipc.ts `spawnAgent` payload shape so the launch is wired identically to
 * the pane path. Injectable so the test can assert the call without a real PTY.
 */
export type SpawnAgentFn = (o: {
  cliBinary: string;
  cliArgs: string[];
  taskPrompt: string;
  sessionId: string;
  paneId: string;
  cwd?: string;
}) => Promise<unknown>;

const defaultSpawnAgent: SpawnAgentFn = (o) =>
  invoke('spawn_agent', {
    cliBinary: o.cliBinary,
    cliArgs: o.cliArgs,
    sessionId: o.sessionId,
    paneId: o.paneId,
    cwd: o.cwd,
  });

export interface RunCommandBarProps {
  cwd: string;
  cliBinary: string;
  /** Native (Voss harness) client — GATED/mock in V14. Native path is a
   *  disabled-with-reason no-op when undefined. */
  client?: RunNativeClient;
  /** Terminal launch fn (Bridge B). Defaults to a direct spawn_agent invoke. */
  spawnAgent?: SpawnAgentFn;
  /** Pane id for the terminal launch. The cockpit has no active pane bound to
   *  the bar, so a fresh pane id is minted per run by default (mirrors
   *  PaneComponent using props.id as paneId). */
  resolvePaneId?: () => string;
}

const MODES: RunMode[] = ['Plan', 'Edit', 'Auto'];
// D-10 copy rule: internal-mechanics vocabulary (incl. "Voss-native") never
// surfaces in UI strings — the native target reads "Voss run".
const TARGETS: { id: RunTarget; label: string }[] = [
  { id: 'native', label: 'Voss run' },
  { id: 'terminal', label: 'Terminal agent' },
];
const TEAMS = ['solo', 'core', 'review'];

/**
 * Encode the intake context into CLI args so the terminal launch carries
 * mode/team/scope/budget (mirrors AgentLaunchModal.buildConfig arg assembly).
 */
function intakeCliArgs(spec: RunSpec): string[] {
  const args: string[] = ['--mode', spec.mode, '--team', spec.team];
  if (spec.scope) args.push('--scope', spec.scope);
  if (spec.budget != null) args.push('--budget', String(spec.budget));
  return args;
}

const RunCommandBar: Component<RunCommandBarProps> = (props) => {
  const [goal, setGoal] = createSignal('');
  const [mode, setMode] = createSignal<RunMode>('Plan');
  const [team, setTeam] = createSignal<string>('solo');
  const [scope, setScope] = createSignal('');
  const [budget, setBudget] = createSignal('');
  const [target, setTarget] = createSignal<RunTarget>('native');
  const [contextAttached, setContextAttached] = createSignal(false);
  const [blockReason, setBlockReason] = createSignal<string | null>(null);
  // 6b: transient post-launch confirmation — the bar must acknowledge a
  // successful start, not only failures.
  const [startedMsg, setStartedMsg] = createSignal<string | null>(null);
  let startedTimer: ReturnType<typeof setTimeout> | undefined;
  const flashStarted = (msg: string) => {
    setStartedMsg(msg);
    clearTimeout(startedTimer);
    startedTimer = setTimeout(() => setStartedMsg(null), 2000);
  };

  const currentSpec = (): RunSpec => {
    const b = budget().trim();
    return assembleRunSpec({
      goal: goal().trim(),
      mode: mode(),
      team: team(),
      scope: scope().trim() || undefined,
      budget: b ? Number(b) : undefined,
      target: target(),
    });
  };

  const handleStart = async () => {
    setBlockReason(null);
    const spec = currentSpec();

    // Auto gating — disabled-with-reason discipline (decisionActions.ts:1-11).
    const gate = validateAutoStart(spec);
    if (!gate.ok) {
      setBlockReason(gate.reason ?? 'Cannot start.');
      return; // NO start path is invoked.
    }

    if (spec.target === 'terminal') {
      // Bridge B: mint cardId, pass it through as the spawn_agent sessionId arg.
      const paneId = (props.resolvePaneId ?? (() => crypto.randomUUID()))();
      const cardId = registerTerminalCard(paneId);
      const spawn = props.spawnAgent ?? defaultSpawnAgent;
      await spawn({
        cliBinary: props.cliBinary,
        cliArgs: intakeCliArgs(spec),
        taskPrompt: spec.goal,
        sessionId: cardId,
        paneId,
        cwd: props.cwd,
      });
      flashStarted('Run started');
      return;
    }

    // Native (Bridge A) — gated/mock in V14. D-10: plain language, no
    // internal-mechanics vocabulary in the reason string.
    if (!props.client) {
      setBlockReason('Voss runs need the Voss server — not available in this build.');
      return;
    }
    const response = await props.client.createSession(spec);
    // A1 finding: the create-response id IS the snapshot node id.
    registerNativeCard(response.id, response.id);
    flashStarted('Run started');
  };

  return (
    <div class="run-command-bar" role="region" aria-label="Run intake">
      {/* Goal — rounded container with the ▸ prefix (mockup .goal). */}
      <div class="run-bar__goal">
        <span class="run-bar__goal-icon" aria-hidden="true">
          ▸
        </span>
        <input
          class="run-bar__goal-input"
          placeholder="Describe the run goal…"
          value={goal()}
          onInput={(e) => setGoal(e.currentTarget.value)}
          aria-label="Run goal"
        />
      </div>

      {/* Mode — visible segmented control, never placeholder. */}
      <div class="run-bar__group" aria-label="Mode">
        <div class="run-bar__seg">
          <For each={MODES}>
            {(m) => (
              <button
                class={`run-bar__seg-btn${mode() === m ? ' run-bar__seg-btn--active' : ''}`}
                onClick={() => setMode(m)}
              >
                {m}
              </button>
            )}
          </For>
        </div>
      </div>

      {/* Team — key:value chip (mockup .chip), value stays a select. */}
      <label class="run-bar__chip">
        <span class="run-bar__chip-key">team</span>
        <select
          class="run-bar__team"
          value={team()}
          onChange={(e) => setTeam(e.currentTarget.value)}
          aria-label="Team"
        >
          <For each={TEAMS}>{(t) => <option value={t}>{t}</option>}</For>
        </select>
      </label>

      {/* Scope — key:value chip, value stays an editable input. */}
      <label class="run-bar__chip">
        <span class="run-bar__chip-key">scope</span>
        <input
          class="run-bar__chip-input run-bar__chip-input--scope"
          placeholder="e.g. tests/**"
          value={scope()}
          onInput={(e) => setScope(e.currentTarget.value)}
          aria-label="Scope"
        />
      </label>

      {/* Budget — key:value chip, value stays an editable input. */}
      <label class="run-bar__chip">
        <span class="run-bar__chip-key">budget</span>
        <input
          class="run-bar__chip-input run-bar__chip-input--budget"
          type="number"
          min="0"
          placeholder="$"
          value={budget()}
          onInput={(e) => setBudget(e.currentTarget.value)}
          aria-label="Budget"
        />
      </label>

      {/* Context-attach */}
      <button
        class={`run-bar__attach${contextAttached() ? ' run-bar__attach--on' : ''}`}
        onClick={() => setContextAttached((v) => !v)}
        aria-pressed={contextAttached()}
        aria-label="Attach context"
      >
        {contextAttached() ? '✓ ctx' : '+ ctx'}
      </button>

      {/* Explicit target indicator — visible segmented control. The native
          'Voss run' segment carries the mockup .chip.native accent when
          active (focus-tinted ring + focus text). */}
      <div class="run-bar__group" aria-label="Run target">
        <div class="run-bar__seg">
          <For each={TARGETS}>
            {(t) => (
              <button
                class={`run-bar__seg-btn${t.id === 'native' ? ' run-bar__seg-btn--native' : ''}${target() === t.id ? ' run-bar__seg-btn--active' : ''}`}
                onClick={() => setTarget(t.id)}
              >
                {t.label}
              </button>
            )}
          </For>
        </div>
      </div>

      <button
        class="run-bar__start"
        onClick={() => void handleStart()}
        aria-label="Start run"
      >
        Start ⏎
      </button>

      {/* Inline disabled-with-reason (Auto gate / gated native). */}
      <Show when={blockReason()}>
        <span class="run-bar__reason" role="alert">
          {blockReason()}
        </span>
      </Show>

      {/* 6b: transient success confirmation. */}
      <Show when={startedMsg()}>
        <span class="run-bar__started" role="status">
          {startedMsg()}
        </span>
      </Show>
    </div>
  );
};

export default RunCommandBar;
