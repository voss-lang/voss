import { type Component, createMemo, createSignal, For, Show } from 'solid-js';
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

export interface RunNativeClient {
  createSession(spec: RunSpec): Promise<{ id: string }>;
}

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

export interface DispatchDeps {
  cliBinary: string;
  cwd?: string;

  client?: RunNativeClient;
  spawnAgent?: SpawnAgentFn;
  resolvePaneId?: () => string;
}

export async function dispatchRunSpec(
  spec: RunSpec,
  deps: DispatchDeps,
): Promise<void> {
  if (spec.target === 'terminal') {
    const paneId = (deps.resolvePaneId ?? (() => crypto.randomUUID()))();
    const cardId = registerTerminalCard(paneId);
    const spawn = deps.spawnAgent ?? defaultSpawnAgent;
    await spawn({
      cliBinary: deps.cliBinary,
      cliArgs: intakeCliArgs(spec),
      taskPrompt: spec.goal,
      sessionId: cardId,
      paneId,
      cwd: deps.cwd,
    });
    return;
  }
  if (!deps.client) {
    throw new Error(
      'Voss runs need the Voss server — not available in this build.',
    );
  }
  const response = await deps.client.createSession(spec);
  registerNativeCard(response.id, response.id);
}

export interface RunCommandBarProps {
  cwd: string;
  cliBinary: string;

  client?: RunNativeClient;

  spawnAgent?: SpawnAgentFn;

  resolvePaneId?: () => string;
}

type SafetyMode = 'Read only' | 'Can edit' | 'Autopilot';

const SAFETY_MODES: SafetyMode[] = ['Read only', 'Can edit', 'Autopilot'];

const SAFETY_TO_RUNMODE: Record<SafetyMode, RunMode> = {
  'Read only': 'Plan',
  'Can edit': 'Edit',
  Autopilot: 'Auto',
};

const SAFETY_CLASS: Record<SafetyMode, string> = {
  'Read only': 'run-bar__safety--read-only',
  'Can edit': 'run-bar__safety--can-edit',
  Autopilot: 'run-bar__safety--autopilot',
};

const TARGETS: { id: RunTarget; label: string }[] = [
  { id: 'native', label: 'Voss run' },
  { id: 'terminal', label: 'Terminal agent' },
];
const TEAMS = ['solo', 'core', 'review'];

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
    // V15-02: the injected client may lazily spawn the sidecar — a failed
    // spawn/createSession surfaces through the SAME block-reason path (never
    // an unhandled rejection; the gate above stays — T-V15-04).
    let response: { id: string };
    try {
      response = await props.client.createSession(spec);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setBlockReason(`Could not start the Voss run: ${msg}`);
      return;
    }
    // A1 finding: the create-response id IS the snapshot node id.
    registerNativeCard(response.id, response.id);
    flashStarted('Run started');
  };

  return (
    <div class="run-command-bar" role="region" aria-label="Task intake">
      {}
      <div class="run-bar__row run-bar__row--goal">
        <div class="run-bar__goal">
          <span class="run-bar__goal-icon" aria-hidden="true">
            ▸
          </span>
          <input
            class="run-bar__goal-input"
            placeholder="What should Voss work on?"
            value={goal()}
            onInput={(e) => setGoal(e.currentTarget.value)}
            aria-label="Task goal"
          />
        </div>
      </div>

      {}
      <div class="run-bar__row run-bar__row--controls">
        <label class="run-bar__scope">
          <span class="run-bar__scope-prefix">In</span>
          <input
            class="run-bar__scope-input"
            placeholder="e.g. tests}
      <Show when={detailsOpen()}>
        <div id="run-bar-details-panel" class="run-bar__details">
          <label class="run-bar__detail-field">
            <span class="run-bar__detail-key">team</span>
            <select
              class="run-bar__detail-select"
              value={team()}
              onChange={(e) => setTeam(e.currentTarget.value)}
              aria-label="Team"
            >
              <For each={TEAMS}>{(t) => <option value={t}>{t}</option>}</For>
            </select>
          </label>

          <label class="run-bar__detail-field">
            <span class="run-bar__detail-key">budget</span>
            <input
              class="run-bar__detail-input run-bar__detail-input--budget"
              type="number"
              min="0"
              placeholder="$"
              value={budget()}
              onInput={(e) => setBudget(e.currentTarget.value)}
              aria-label="Budget"
            />
          </label>

          <div class="run-bar__group" aria-label="Run target">
            <div class="run-bar__seg">
              <For each={targetOptions()}>
                {(t) => (
                  <button
                    type="button"
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
            type="button"
            class={`run-bar__attach${contextAttached() ? ' run-bar__attach--on' : ''}`}
            onClick={() => setContextAttached((v) => !v)}
            aria-pressed={contextAttached()}
            aria-label="Attach context"
          >
            {contextAttached() ? '✓ ctx' : '+ ctx'}
          </button>
        </div>
      </Show>

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
